package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.MockRequest;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.function.Function;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * C12b.3 (gotcha 21, the lead's requirements in CONTRACTS.md): truncated thinking. The failure seen live on Qwen3-14B:
 * a thinking quote reply cut at an 8,192-token limit with an unclosed {@code <think>} in its content was sent back in the
 * repair turn, the request overflowed the 16k window, vLLM answered HTTP 400 and the run aborted. The mock server here
 * enforces the window the same way. With thinking set, such a reply (or, with thinking on, any unreadable reply cut at
 * the limit) is never repaired, never read by a refusal pattern and never retried with thinking off: the call is imputed
 * (refusal kind TRUNCATED, counted by the truncation stop) and flagged truncated_thinking. Track S and Track M alike;
 * with thinking unset nothing changes.
 */
class TruncatedThinkingTest {
    static final int WINDOW = 16384;
    static final int LIMIT = 8192;
    /** 8,192 tokens of thinking at 4 characters a token, never closed. */
    static final String RUNAWAY = "<think>" + String.join(" ", Collections.nCopies(LIMIT * 4 / 5, "hmmm"));
    static final String DECISION = "{\"quote\": 2.09, \"plan\": \"hold\", \"rationale\": \"why\"}";

    /** vLLM's check: prompt tokens (4 characters a token) + max_tokens above the window is refused with HTTP 400. */
    static Function<MockRequest, Reply> windowed(Function<MockRequest, Reply> f) {
        return r -> {
            int chars = r.system().length();
            for (var t : r.turns()) {
                chars += t.content().length();
            }
            int max;
            try {
                max = Canonical.MAPPER.readTree(r.rawBody()).get("max_tokens").asInt();
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            if (chars / 4 + max > WINDOW) {
                return Reply.http(400, "{\"error\": {\"message\": \"This model's maximum context length is 16384 tokens. "
                        + "However, you requested more tokens.\", \"type\": \"BadRequestError\", \"code\": 400}}");
            }
            return f.apply(r);
        };
    }

    static boolean isTalk(MockRequest r) {
        return r.user().startsWith("talk|");
    }

    /** Talk: one message, then done. Quotes 2.09; the quote of llm2 in round 2 runs away (unless told otherwise). */
    static Function<MockRequest, Reply> game(Function<MockRequest, Reply> llm2r2) {
        return windowed(r -> {
            if (isTalk(r)) {
                return Reply.text(r.lastUser().contains("You have sent 0 of") ? "{\"message\": \"Hold 2.09?\", \"done\": false}"
                        : "{\"message\": \"\", \"done\": true}").withReasoning("ok", 2);
            }
            if (r.user().contains("|llm2|r2|")) {
                return llm2r2.apply(r);
            }
            return Reply.text(DECISION).withReasoning("fine", 3);
        });
    }

    record Run(List<MockRequest> requests, Path out, Path trial) {}

    static Run run(Path dir, String name, String scenario, boolean multi, Function<MockRequest, Reply> f, String... extra)
            throws Exception {
        Path out = dir.resolve(name + ".jsonl");
        Path trial = dir.resolve("root").resolve("arm").resolve(name);
        List<String> kv = new ArrayList<>(List.of("scenario", scenario, "seat", "LLM", "model", "mock-model-1", "seed", "2",
                "out", out.toString(), "analysis-script", "../tools/analysis.py", "max-tokens", Integer.toString(LIMIT)));
        if (multi) {
            kv.addAll(List.of("multi-seat", "on", "talk", "on", "trial-dir", trial.toString(), "code-commit", "abc1234"));
        }
        kv.addAll(List.of(extra));
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(f))) {
            kv.addAll(List.of("base-url", s.baseUrl()));
            LlmCommands.run(TrialDirCliTest.o(kv.toArray(String[]::new)));
            return new Run(s.requests(), out, trial);
        }
    }

    static JsonNode quoteEvent(Path trial, String seat, int round) throws Exception {
        for (JsonNode e : TrialDirCliTest.events(trial)) {
            if (e.get("kind").asText().equals("quote") && e.get("seat").asText().equals(seat) && e.get("round").asInt() == round) {
                return e;
            }
        }
        throw new AssertionError("no quote event " + seat + " r" + round);
    }

    @Test
    void withoutTheRuleTheRepairOfARunawayThinkingReplyOverflowsTheWindowAndAbortsTheRun(@TempDir Path dir) {
        // thinking unset: the old rule (one repair, resending the reply) still applies, and the mock window refuses it,
        // as vLLM did tonight; this is the failure the rule prevents when thinking is on
        assertThatThrownBy(() -> run(dir, "old", "scenarios/n3-group.yaml", true, game(r -> Reply.truncated(RUNAWAY))))
                .isInstanceOf(LlmException.class).hasMessageContaining("400");
    }

    @Test
    void trackMWithThinkingOnImputesTheRoundFlagsItAndPlaysOn(@TempDir Path dir) throws Exception {
        Run r = run(dir, "tm", "scenarios/n3-group.yaml", true, game(q -> Reply.truncated(RUNAWAY)), "thinking", "on");
        assertThat(r.requests()).noneMatch(q -> q.user().equals("game|n3-group|s2|llm2|r2|a1")); // never repaired
        assertThat(r.requests()).filteredOn(q -> q.user().startsWith("game|n3-group|s2|llm2|r2|")).hasSize(1);
        assertThat(r.requests()).noneMatch(q -> q.rawBody().contains("\"enable_thinking\":false")); // no thinking-off retry
        assertThat(r.requests()).noneMatch(q -> q.user().endsWith("|nt"));
        JsonNode e = quoteEvent(r.trial(), "llm2", 2);
        assertThat(e.get("outcome").asText()).isEqualTo("TRUNCATED");
        assertThat(e.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
        assertThat(e.get("truncated").asBoolean()).isTrue();
        assertThat(e.get("truncated_thinking").asBoolean()).isTrue();
        assertThat(e.get("imputed").asBoolean()).isTrue();
        assertThat(e.has("refusal_pattern")).isFalse();
        assertThat(e.path("parsed").has("rationale")).isFalse();
        assertThat(e.get("quote").asDouble()).isEqualTo(LlmCommands.loadConfig("scenarios/n3-group.yaml").scenario().market().s0());
        assertThat(quoteEvent(r.trial(), "llm2", 3).get("outcome").asText()).isEqualTo("OK"); // Track M: called again
        assertThat(quoteEvent(r.trial(), "llm1", 2).has("truncated_thinking")).isFalse();
        List<String> calls = Files.readAllLines(Path.of(r.out() + ".calls.jsonl"));
        assertThat(calls).anyMatch(c -> c.contains("\"index\":2") && c.contains("\"parseStatus\":\"PARSE_FAIL\"")
                && c.contains("\"attempt\":0") && c.contains("\"kind\":\"game\""));
        JsonNode seat = Canonical.MAPPER.readTree(Files.readAllLines(r.out()).get(0)).get("seats").get("llm2");
        assertThat(seat.get("imputedRounds").asInt()).isEqualTo(1);
        assertThat(seat.get("refusalKind").asText()).isEqualTo("TRUNCATED");
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", r.out() + ".cache.jsonl", "run", r.out().toString()))).isZero();
        SeatsIntegrationI1Test.schemaCheck(r.out(), Path.of(r.out() + ".calls.jsonl"));
        countedByTheTruncationStop(dir, r.trial());
    }

    /** derive.cut_kinds reads every flagged event as a token-limit cut; collect counts it in trials.csv truncations. */
    static void countedByTheTruncationStop(Path dir, Path trial) throws Exception {
        Path tools = AdversarialMocksI2Test.tools();
        assumeTrue(tools != null, "tools/trial not found");
        String code = "import json, sys; sys.path.insert(0, sys.argv[1]); import derive\n"
                + "ev = [json.loads(l) for l in open(sys.argv[2], encoding='utf-8') if l.strip()]\n"
                + "flagged = [e for e in ev if e.get('truncated_thinking')]\n"
                + "assert flagged, 'no truncated_thinking event'\n"
                + "assert all(derive.cut_kinds(e)[0] for e in flagged), 'not a token-limit cut'\n"
                + "assert all(derive.call_failure(e.get('refusal_kind'), e.get('outcome')) == 'truncation' for e in flagged)\n"
                + "print(len(flagged))\n";
        Path script = dir.resolve("check_cut.py");
        Files.writeString(script, code);
        String n = TrialDirCliTest.python(script.toString(), tools.toString(), trial.resolve("events.jsonl").toString()).strip();
        TrialDirCliTest.python(tools.resolve("collect.py").toString(), dir.resolve("root").toString(),
                dir.resolve("tables").toString());
        Path read = dir.resolve("read_trials.py");
        Files.writeString(read, "import csv, sys\nr = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))\n"
                + "print(len(r), r[0]['truncations'], r[0]['refusals'])\n");
        String got = TrialDirCliTest.python(read.toString(), dir.resolve("tables/trials.csv").toString()).strip();
        assertThat(got).isEqualTo("1 " + n + " 0");
    }

    @Test
    void aReplyCutWhileThinkingWithNoContentIsNotRepairedEither(@TempDir Path dir) throws Exception {
        // the reasoning parser split the reply: content null, the partial reasoning in reasoning_content, finish length
        Run r = run(dir, "split", "scenarios/n3-group.yaml", true,
                game(q -> Reply.truncatedThinking("The other firm held 2.09; if I undercut I can't help but ...")), "thinking", "on");
        assertThat(r.requests()).filteredOn(q -> q.user().startsWith("game|n3-group|s2|llm2|r2|")).hasSize(1);
        JsonNode e = quoteEvent(r.trial(), "llm2", 2);
        assertThat(e.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
        assertThat(e.get("truncated_thinking").asBoolean()).isTrue();
        assertThat(e.get("reasoning").asText()).contains("can't help"); // recorded, never read as a refusal
        assertThat(e.has("refusal_pattern")).isFalse();
    }

    @Test
    void refusalWordsInsideAnUnclosedThinkOrInTheReasoningAreNeverARefusal(@TempDir Path dir) throws Exception {
        // a runaway think that says "I can't help with colluding": not a refusal, a truncation
        Run r = run(dir, "words", "scenarios/n3-group.yaml", true,
                game(q -> Reply.text("<think>I'm sorry, but I can't help with colluding on prices. I must decline.")),
                "thinking", "on");
        JsonNode e = quoteEvent(r.trial(), "llm2", 2);
        assertThat(e.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
        assertThat(e.get("truncated_thinking").asBoolean()).isTrue();
        assertThat(r.requests()).filteredOn(q -> q.user().startsWith("game|n3-group|s2|llm2|r2|")).hasSize(1);
        // refusal words in the reasoning of a readable reply: the quote stands
        Run ok = run(dir, "reason", "scenarios/n3-group.yaml", true,
                game(q -> Reply.text(DECISION).withReasoning("I can't help with colluding. I must decline.", 9)),
                "thinking", "on");
        assertThat(quoteEvent(ok.trial(), "llm2", 2).get("outcome").asText()).isEqualTo("OK");
    }

    @Test
    void aJsonCutAfterTheThinkingKeepsSalvageRuleZeroAndIsNotRepairedWhenUnreadable(@TempDir Path dir) throws Exception {
        // the leading quote is complete: rule 0 reads it (no repair needed), as before
        Run s = run(dir, "salv", "scenarios/n3-group.yaml", true,
                game(q -> Reply.truncated("{\"quote\": 2.05, \"plan\": \"hold at 2.05 while")), "thinking", "on");
        JsonNode e = quoteEvent(s.trial(), "llm2", 2);
        assertThat(e.get("outcome").asText()).isEqualTo("OK");
        assertThat(e.get("quote").asDouble()).isEqualTo(2.05);
        assertThat(e.has("truncated_thinking")).isFalse();
        // nothing readable: with thinking on, no repair (it would resend up to the token limit)
        Run u = run(dir, "unread", "scenarios/n3-group.yaml", true, game(q -> Reply.truncated("{\"quo")), "thinking", "on");
        assertThat(u.requests()).filteredOn(q -> q.user().startsWith("game|n3-group|s2|llm2|r2|")).hasSize(1);
        assertThat(quoteEvent(u.trial(), "llm2", 2).get("truncated_thinking").asBoolean()).isTrue();
    }

    @Test
    void withThinkingOffAnOrdinaryCutKeepsTheRepairButAnUnclosedThinkDoesNot(@TempDir Path dir) throws Exception {
        Run off = run(dir, "off", "scenarios/n3-group.yaml", true, game(q -> q.user().endsWith("|a1") ? Reply.text(DECISION)
                : Reply.truncated("{\"quo")), "thinking", "off", "max-tokens", "400");
        assertThat(off.requests()).anyMatch(q -> q.user().equals("game|n3-group|s2|llm2|r2|a1"));
        assertThat(quoteEvent(off.trial(), "llm2", 2).get("outcome").asText()).isEqualTo("REPAIRED");
        Run mis = run(dir, "mis", "scenarios/n3-group.yaml", true, game(q -> Reply.text("<think>let me see")), "thinking",
                "off", "max-tokens", "400");
        assertThat(mis.requests()).filteredOn(q -> q.user().startsWith("game|n3-group|s2|llm2|r2|")).hasSize(1);
        assertThat(quoteEvent(mis.trial(), "llm2", 2).get("truncated_thinking").asBoolean()).isTrue();
    }

    @Test
    void aTalkReplyThatRunsAwayIsDoneImputedAndFlaggedWithoutARepair(@TempDir Path dir) throws Exception {
        Function<MockRequest, Reply> f = windowed(r -> {
            if (isTalk(r) && r.user().contains("|llm1|r1|")) {
                return Reply.truncated(RUNAWAY);
            }
            if (isTalk(r)) {
                return Reply.text(r.lastUser().contains("You have sent 0 of") ? "{\"message\": \"Hold 2.09?\", \"done\": false}"
                        : "{\"message\": \"\", \"done\": true}");
            }
            return Reply.text(DECISION);
        });
        Run r = run(dir, "talk", "scenarios/n3-group.yaml", true, f, "thinking", "on");
        assertThat(r.requests()).filteredOn(q -> q.user().startsWith("talk|n3-group|s2|llm1|r1|")).hasSize(1);
        JsonNode t = TrialDirCliTest.events(r.trial()).stream().filter(e -> e.get("kind").asText().equals("talk")
                && e.get("seat").asText().equals("llm1") && e.get("round").asInt() == 1).findFirst().orElseThrow();
        assertThat(t.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
        assertThat(t.get("outcome").asText()).isEqualTo("IMPUTED");
        assertThat(t.get("truncated_thinking").asBoolean()).isTrue();
        assertThat(t.get("parsed").get("done").asBoolean()).isTrue();
        assertThat(t.has("refusal_pattern")).isFalse();
        // the runaway thinking never reaches another seat's prompt
        assertThat(r.requests()).noneMatch(q -> q.rawBody().contains("hmmm hmmm"));
        countedByTheTruncationStop(dir, r.trial());
    }

    static JsonNode talkEvent(Path trial, String seat, int round, int turn) throws Exception {
        return TrialDirCliTest.events(trial).stream().filter(e -> e.get("kind").asText().equals("talk")
                && e.get("seat").asText().equals(seat) && e.get("round").asInt() == round && e.get("turn").asInt() == turn)
                .findFirst().orElseThrow();
    }

    static Function<MockRequest, Reply> talkScript(String key, Function<MockRequest, Reply> special) {
        return windowed(r -> {
            if (r.user().contains(key)) {
                return special.apply(r);
            }
            if (isTalk(r)) {
                return Reply.text("{\"message\": \"\", \"done\": true}");
            }
            return Reply.text(DECISION);
        });
    }

    @Test
    void review_talkRefusalWordsInAnUnclosedThinkAreATruncationNotARefusal(@TempDir Path dir) throws Exception {
        Run r = run(dir, "a", "scenarios/n3-group.yaml", true, talkScript("|llm1|r1|", q ->
                Reply.text("<think>I'm sorry, but I can't help with colluding on prices. I must decline.")), "thinking", "on");
        JsonNode t = talkEvent(r.trial(), "llm1", 1, TrialDirCliTest.events(r.trial()).stream().filter(e -> e.get("kind")
                .asText().equals("talk") && e.get("seat").asText().equals("llm1")).findFirst().orElseThrow().get("turn").asInt());
        assertThat(t.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
        assertThat(t.get("outcome").asText()).isEqualTo("IMPUTED");
        assertThat(t.has("refusal_pattern")).isFalse();
    }

    @Test
    void review_aRepairReplyThatRunsAwayIsFlaggedInTalkAndQuote(@TempDir Path dir) throws Exception {
        Run t = run(dir, "b", "scenarios/n3-group.yaml", true, talkScript("|llm1|r1|", q -> q.user().endsWith("|a0")
                ? Reply.text("hello there") : Reply.truncated(RUNAWAY.substring(0, 4000))), "thinking", "on");
        JsonNode e = TrialDirCliTest.events(t.trial()).stream().filter(x -> x.get("kind").asText().equals("talk")
                && x.get("seat").asText().equals("llm1") && x.get("round").asInt() == 1).findFirst().orElseThrow();
        assertThat(e.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
        assertThat(e.get("truncated_thinking").asBoolean()).isTrue();
        assertThat(e.get("outcome").asText()).isEqualTo("IMPUTED");
        Run q = run(dir, "c", "scenarios/n3-group.yaml", true, game(x -> x.user().endsWith("|a0") ? Reply.text("hello")
                : Reply.truncated(RUNAWAY.substring(0, 4000))), "thinking", "on");
        assertThat(q.requests()).filteredOn(x -> x.user().startsWith("game|n3-group|s2|llm2|r2|")).hasSize(2);
        JsonNode qe = quoteEvent(q.trial(), "llm2", 2);
        assertThat(qe.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
        assertThat(qe.get("truncated_thinking").asBoolean()).isTrue();
        assertThat(qe.path("parsed").has("rationale")).isFalse();
    }

    @Test
    void review_aProseRefusalCutAtTheLimitWithThinkingOnIsTruncatedThinking(@TempDir Path dir) throws Exception {
        Run r = run(dir, "d", "scenarios/n3-group.yaml", true,
                game(q -> Reply.truncated("Okay, they want collusion. I can't help with colluding on prices, but maybe")),
                "thinking", "on");
        JsonNode e = quoteEvent(r.trial(), "llm2", 2);
        assertThat(e.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
        assertThat(e.get("truncated_thinking").asBoolean()).isTrue();
        assertThat(e.has("refusal_pattern")).isFalse();
        // the same words with finish "stop": the model's own refusal, as before
        Run s = run(dir, "d2", "scenarios/n3-group.yaml", true,
                game(q -> Reply.text("I can't help with colluding on prices.")), "thinking", "on");
        assertThat(quoteEvent(s.trial(), "llm2", 2).get("outcome").asText()).isEqualTo("REFUSED");
        // talk: a prose refusal cut at the limit
        Run t = run(dir, "d3", "scenarios/n3-group.yaml", true, talkScript("|llm1|r1|", q ->
                Reply.truncated("I'm sorry, but I can't help with colluding on prices. Hmm, maybe")), "thinking", "on");
        JsonNode te = TrialDirCliTest.events(t.trial()).stream().filter(x -> x.get("kind").asText().equals("talk")
                && x.get("seat").asText().equals("llm1") && x.get("round").asInt() == 1).findFirst().orElseThrow();
        assertThat(te.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
    }

    @Test
    void review_aClosedThinkBeforeUnreadableJsonIsNeverSentBackInARepair(@TempDir Path dir) throws Exception {
        Run r = run(dir, "f", "scenarios/n3-group.yaml", true, game(q -> q.user().endsWith("|a1") ? Reply.text(DECISION)
                : Reply.text("<think>" + "hmm ".repeat(4000) + "</think> {\"quo")), "thinking", "on");
        assertThat(r.requests()).noneMatch(q -> q.user().endsWith("|llm2|r2|a1"));
        assertThat(r.requests()).noneMatch(q -> q.rawBody().contains("hmm hmm"));
        assertThat(quoteEvent(r.trial(), "llm2", 2).get("truncated_thinking").asBoolean()).isTrue();
        // an upper-case unclosed tag is caught too, also with thinking off
        Run u = run(dir, "g", "scenarios/n3-group.yaml", true, game(q -> q.user().endsWith("|a1") ? Reply.text(DECISION)
                : Reply.text("<THINK>let me see")), "thinking", "off", "max-tokens", "400");
        assertThat(u.requests()).noneMatch(q -> q.user().endsWith("|llm2|r2|a1"));
    }

    @Test
    void trackSWithThinkingOnImputesWithoutARepairAndKeepsItsAbsorbingRule(@TempDir Path dir) throws Exception {
        Function<MockRequest, Reply> f = windowed(r -> r.user().contains("|r2|") && r.user().startsWith("game|")
                ? Reply.truncated(RUNAWAY) : Reply.text(DECISION));
        Run r = run(dir, "ts", "scenarios/ripe-game.yaml", false, f, "thinking", "on");
        assertThat(r.requests()).noneMatch(q -> q.user().endsWith("|r2|a1"));
        JsonNode line = Canonical.MAPPER.readTree(Files.readAllLines(r.out()).get(0));
        assertThat(line.get("refusalKind").asText()).isEqualTo("TRUNCATED");
        assertThat(line.get("firstRefusalRound").asInt()).isEqualTo(2);
        assertThat(r.requests()).noneMatch(q -> q.user().contains("|r3|")); // e.5: absorbing in Track S, as before
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", r.out() + ".cache.jsonl", "run", r.out().toString()))).isZero();
    }

    @Test
    void withThinkingUnsetTrackSBehavesAsBefore(@TempDir Path dir) throws Exception {
        // an unclosed think with thinking unset: read as before (repair, then the repair reply)
        Function<MockRequest, Reply> f = r -> r.user().endsWith("|r2|a0") ? Reply.text("<think>hm")
                : Reply.text(DECISION);
        Run r = run(dir, "unset", "scenarios/ripe-game.yaml", false, f, "max-tokens", "400");
        assertThat(r.requests()).anyMatch(q -> q.user().endsWith("|r2|a1"));
        JsonNode line = Canonical.MAPPER.readTree(Files.readAllLines(r.out()).get(0));
        assertThat(line.get("repairedRounds").asInt()).isEqualTo(1);
        assertThat(line.get("refusedAnyRound").asBoolean()).isFalse();
    }
}
