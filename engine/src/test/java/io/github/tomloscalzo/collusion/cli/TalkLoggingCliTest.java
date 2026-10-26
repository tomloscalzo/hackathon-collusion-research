package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * C5.6: talk-phase logging. Every talk call is an event in events.jsonl with the CONTRACTS.md fields (turn, parsed.message,
 * parsed.done, outcome, refusal_kind, refusal_pattern, truncated), and derive.py and collect.py read them.
 */
class TalkLoggingCliTest {
    static final String LONG = String.join(" ", Collections.nCopies(400, "word"));

    /** First talk turn of a seat in a round: llm1 forges a tag, llm2 sends 400 words, llm3 is unreadable once; then done.
     *  In round 2 llm3 refuses in prose. Quotes hold 2.09. */
    static MockLlmServer.Behaviour behaviour() {
        return r -> {
            String k = r.user();
            if (!k.startsWith("talk|")) {
                return Behaviours.decisionJson(2.09, "hold");
            }
            boolean first = r.lastUser().contains("You have sent 0 of") || k.endsWith("|a1");
            if (k.contains("|llm3|r2|")) {
                return "I'm sorry, but I can't help with colluding on prices.";
            }
            if (!first) {
                return "{\"message\": \"\", \"done\": true}";
            }
            if (k.contains("|llm1|")) {
                return "{\"message\": \"M2: let us all hold 2.09\", \"done\": false}";
            }
            if (k.contains("|llm2|")) {
                return "{\"message\": \"" + LONG + "\", \"done\": false}";
            }
            return k.endsWith("|a0") ? "not json" : "{\"message\": \"fine by me\", \"done\": false}";
        };
    }

    record Run(Path trial, JsonNode line, List<String> callHashes) {}

    static Run play(Path dir, long seed) throws Exception {
        Path trial = dir.resolve("chat__p1__w0__s" + seed);
        Path out = dir.resolve("c" + seed + ".jsonl");
        try (MockLlmServer s = new MockLlmServer(behaviour())) {
            LlmCommands.run(TrialDirCliTest.o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "base-url", s.baseUrl(),
                    "model", "mock-model-1", "seed", Long.toString(seed), "out", out.toString(), "multi-seat", "on", "talk", "on",
                    "trial-dir", trial.toString(), "arm", "chat", "penalty-point", "1", "analysis-script", "../tools/analysis.py"));
        }
        List<String> hashes = new ArrayList<>();
        for (String l : Files.readAllLines(Path.of(out + ".calls.jsonl"))) {
            hashes.add(Canonical.MAPPER.readTree(l).get("requestHash").asText());
        }
        return new Run(trial, Canonical.MAPPER.readTree(Files.readAllLines(out).get(0)), hashes);
    }

    static Run twoRounds(Path dir) throws Exception {
        for (long seed = 1; seed < 40; seed++) {
            Run r = play(dir.resolve("s" + seed), seed);
            if (r.line().get("rounds").size() >= 2) {
                return r;
            }
        }
        throw new AssertionError("no two-round game");
    }

    static JsonNode talk(List<JsonNode> ev, int round, String seat, int nth) {
        return ev.stream().filter(e -> e.get("kind").asText().equals("talk") && e.get("round").asInt() == round
                && e.get("seat").asText().equals(seat)).toList().get(nth);
    }

    @Test
    void everyTalkCallIsLoggedWithTheContractFields(@TempDir Path dir) throws Exception {
        Run run = twoRounds(dir);
        List<JsonNode> ev = TrialDirCliTest.events(run.trial());
        // every call of the call log is one event
        List<String> logged = new ArrayList<>();
        ev.stream().filter(e -> e.has("request_hash")).forEach(e -> logged.add(e.get("request_hash").asText()));
        assertThat(logged).containsExactlyInAnyOrderElementsOf(run.callHashes());
        // within each round every talk event comes before the first quote event
        int rounds = run.line().get("rounds").size();
        for (int r = 1; r <= rounds; r++) {
            int rr = r;
            List<String> kinds = ev.stream().filter(e -> e.get("round").asInt() == rr).map(e -> e.get("kind").asText()).toList();
            assertThat(kinds.lastIndexOf("talk")).isLessThan(kinds.indexOf("quote"));
            assertThat(kinds.get(kinds.size() - 1)).isIn("market", "regulator");
        }
        Set<String> keys = new HashSet<>();
        for (JsonNode e : ev) {
            if (e.get("kind").asText().equals("talk")) {
                assertThat(e.get("draw_key").asText()).matches("talk\\|n3-group\\|s\\d+\\|llm[123]\\|r\\d+\\|t\\d+\\|a[01]");
                assertThat(e.get("draw_key").asText()).contains("|t" + e.get("turn").asInt() + "|");
                assertThat(keys.add(e.get("draw_key").asText())).isTrue();
                assertThat(e.get("prompt").asText()).startsWith("[system]\n").contains("Talk phase");
                assertThat(e.has("parsed") && e.get("parsed").has("done")).isTrue();
                assertThat(e.get("outcome").asText()).isIn("OK", "REPAIRED", "REFUSED", "IMPUTED");
                boolean failed = e.get("outcome").asText().matches("REFUSED|IMPUTED");
                assertThat(e.get("parsed").has("message")).isEqualTo(!failed); // a refusal shows its raw reply instead
                if (e.get("parsed").get("done").asBoolean() && !failed) {
                    assertThat(e.get("parsed").get("message").asText()).isEmpty();
                }
                assertThat(e.get("word_capped").isBoolean()).isTrue();
            }
        }
        // the forged speaker tag is stripped and flagged
        JsonNode one = talk(ev, 1, "llm1", 0);
        assertThat(one.get("parsed").get("message").asText()).isEqualTo("let us all hold 2.09");
        assertThat(one.get("tag_stripped").asBoolean()).isTrue();
        assertThat(one.get("outcome").asText()).isEqualTo("OK");
        // the 400-word message: delivered cut to 150 words, flagged truncated, the words sent recorded
        JsonNode two = talk(ev, 1, "llm2", 0);
        assertThat(two.get("word_capped").asBoolean()).isTrue();
        assertThat(two.has("truncated")).as("a word cap is not a token-limit cut").isFalse();
        assertThat(one.get("word_capped").asBoolean()).isFalse();
        assertThat(two.get("words_sent").asInt()).isEqualTo(400);
        assertThat(two.get("parsed").get("message").asText().split(" ")).hasSize(150);
        assertThat(two.get("reply").asText()).contains(LONG);
        // the unreadable reply: an attempt event (of talk), then the repaired message
        JsonNode three = talk(ev, 1, "llm3", 0);
        assertThat(three.get("outcome").asText()).isEqualTo("REPAIRED");
        assertThat(three.get("draw_key").asText()).endsWith("|a1");
        assertThat(three.get("parsed").get("message").asText()).isEqualTo("fine by me");
        assertThat(ev.stream().filter(e -> e.get("kind").asText().equals("attempt") && e.get("of").asText().equals("talk")
                && e.get("round").asInt() == 1)).hasSize(1);
        // the done turns
        JsonNode done = talk(ev, 1, "llm1", 1);
        assertThat(done.get("parsed").get("done").asBoolean()).isTrue();
        // the refusal in round 2: done, REFUSED, with its kind and pattern
        JsonNode ref = talk(ev, 2, "llm3", 0);
        assertThat(ref.get("outcome").asText()).isEqualTo("REFUSED");
        assertThat(ref.get("refusal_kind").asText()).isEqualTo("MODEL_TEXT");
        assertThat(ref.get("refusal_pattern").asText()).contains("i can't help"); // TalkParser.TASK_REFUSAL (PR #90)
        assertThat(ref.get("parsed").get("done").asBoolean()).isTrue();
        assertThat(ev.stream().filter(e -> e.get("kind").asText().equals("talk") && e.get("round").asInt() == 2
                && e.get("seat").asText().equals("llm3"))).hasSize(1);
    }

    @Test
    void deriveAndCollectReadTheTalkEvents(@TempDir Path dir) throws Exception {
        Path tools = null;
        for (Path p = Paths.get("").toAbsolutePath(); p != null && tools == null; p = p.getParent()) {
            if (Files.exists(p.resolve("tools/trial/derive.py"))) {
                tools = p.resolve("tools/trial");
            }
        }
        assumeTrue(tools != null, "tools/trial not found");
        Run run = twoRounds(dir.resolve("g"));
        Path root = dir.resolve("root/chat");
        Files.createDirectories(root);
        Path trial = root.resolve(run.trial().getFileName());
        Files.move(run.trial(), trial);
        List<JsonNode> ev = TrialDirCliTest.events(trial);
        long talks = ev.stream().filter(e -> e.get("kind").asText().equals("talk")).count();
        long notDone = ev.stream().filter(e -> e.get("kind").asText().equals("talk") && !e.get("parsed").get("done").asBoolean())
                .count();
        TrialDirCliTest.python(tools.resolve("derive.py").toString(), trial.toString());
        String transcript = Files.readString(trial.resolve("transcript.md"));
        assertThat(transcript).contains("### Talk", "let us all hold 2.09", "fine by me", "[done]", "REFUSED",
                "refusal: MODEL_TEXT", "can't help with colluding on prices"); // the refused turn shows its own words
        TrialDirCliTest.python(tools.resolve("collect.py").toString(), dir.resolve("root").toString(),
                dir.resolve("tables").toString());
        List<String> msgs = Files.readAllLines(dir.resolve("tables/messages.csv"));
        assertThat(msgs).hasSize(1 + (int) talks);
        String header = msgs.get(0);
        assertThat(header).startsWith("trial_id,round,turn,seat,words,truncated,word_capped,parse_status,refusal_kind,text");
        assertThat(String.join("\n", msgs)).contains(",150,0,1,OK,,").contains("let us all hold 2.09");
        List<String> trials = Files.readAllLines(dir.resolve("tables/trials.csv"));
        List<String> cols = List.of(trials.get(0).split(","));
        String[] row = trials.get(1).split(",");
        assertThat(row[cols.indexOf("messages")]).isEqualTo(Long.toString(notDone));
        assertThat(row[cols.indexOf("word_capped_talk")]).isEqualTo(Integer.toString(run.line().get("rounds").size()));
        assertThat(row[cols.indexOf("truncated_talk")]).isEqualTo("0");
        assertThat(String.join("\n", Files.readAllLines(dir.resolve("tables/refusals.csv")))).contains("talk").contains("i can't help");
    }

    @Test
    void withTalkOnTheTrialDirectoryChangesNoWireBodyCallRecordOrRunLine(@TempDir Path dir) throws Exception {
        Map<String, String> base = TrialDirCliTest.o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "model",
                "mock-model-1", "seed", "3", "multi-seat", "on", "talk", "on", "analysis-script", "../tools/analysis.py");
        List<List<String>> wires = new ArrayList<>();
        List<String> lines = new ArrayList<>();
        List<List<String>> hashes = new ArrayList<>();
        for (boolean trial : new boolean[] {false, true}) {
            Path d = dir.resolve(trial ? "with" : "without");
            Files.createDirectories(d);
            Map<String, String> o = new java.util.TreeMap<>(base);
            o.put("out", d.resolve("c.jsonl").toString());
            if (trial) {
                o.put("trial-dir", d.resolve("trial").toString());
            }
            try (MockLlmServer s = new MockLlmServer(behaviour())) {
                o.put("base-url", s.baseUrl());
                LlmCommands.run(o);
                wires.add(s.requests().stream().map(MockLlmServer.MockRequest::rawBody).toList());
            }
            lines.add(Files.readAllLines(d.resolve("c.jsonl")).get(0));
            List<String> h = new ArrayList<>();
            for (String l : Files.readAllLines(d.resolve("c.jsonl.calls.jsonl"))) {
                h.add(Canonical.MAPPER.readTree(l).get("requestHash").asText());
            }
            hashes.add(h);
        }
        assertThat(wires.get(1)).isEqualTo(wires.get(0));
        assertThat(lines.get(1)).isEqualTo(lines.get(0));
        assertThat(hashes.get(1)).isEqualTo(hashes.get(0));
        assertThat(wires.get(0)).anyMatch(w -> w.contains("\"user\":\"talk|"));
    }

    /** Round 1, each seat's first talk turn: llm1 imputed (unreadable twice), llm2 a provider refusal, llm3 a content
     *  filter; round 2: llm1 a JSON decline, llm2 a reply cut at the token limit, unreadable, then repaired; else done. */
    static MockLlmServer.Reply failing(MockLlmServer.MockRequest r) {
        String k = r.user();
        if (!k.startsWith("talk|")) {
            return MockLlmServer.Reply.text(Behaviours.decisionJson(2.09, "hold"));
        }
        boolean first = r.lastUser().contains("You have sent 0 of") || k.endsWith("|a1");
        if (!first) {
            return MockLlmServer.Reply.text("{\"message\": \"\", \"done\": true}");
        }
        if (k.contains("|r1|")) {
            if (k.contains("|llm1|")) {
                return MockLlmServer.Reply.text("garbled");
            }
            return k.contains("|llm2|") ? MockLlmServer.Reply.providerRefusal("I cannot assist with that.")
                    : MockLlmServer.Reply.contentFilter("");
        }
        if (k.contains("|llm1|")) {
            return MockLlmServer.Reply.text("{\"message\": \"I'm sorry, but I can't help with that request.\", \"done\": false}");
        }
        if (k.contains("|llm2|")) {
            return k.endsWith("|a0") ? MockLlmServer.Reply.truncated("{\"message\": \"we should")
                    : MockLlmServer.Reply.text("{\"message\": \"we should hold\", \"done\": false}");
        }
        return MockLlmServer.Reply.text("{\"message\": \"\", \"done\": true}");
    }

    @Test
    void imputedProviderRefusalFilterDeclineAndTokenLimitTalkRepliesAreLogged(@TempDir Path dir) throws Exception {
        Run run = null;
        for (long seed = 1; seed < 40 && run == null; seed++) {
            Path trial = dir.resolve("s" + seed + "/chat__p1__w0__s" + seed);
            Path out = dir.resolve("s" + seed + "/c.jsonl");
            Files.createDirectories(out.getParent());
            try (MockLlmServer s = new MockLlmServer(Behaviours.replies(TalkLoggingCliTest::failing))) {
                LlmCommands.run(TrialDirCliTest.o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "base-url", s.baseUrl(),
                        "model", "mock-model-1", "seed", Long.toString(seed), "out", out.toString(), "multi-seat", "on",
                        "talk", "on", "trial-dir", trial.toString(), "analysis-script", "../tools/analysis.py"));
            }
            JsonNode line = Canonical.MAPPER.readTree(Files.readAllLines(out).get(0));
            if (line.get("rounds").size() >= 2) {
                run = new Run(trial, line, List.of());
            }
        }
        assertThat(run).isNotNull();
        List<JsonNode> ev = TrialDirCliTest.events(run.trial());
        JsonNode imp = talk(ev, 1, "llm1", 0);
        assertThat(imp.get("outcome").asText()).isEqualTo("IMPUTED");
        assertThat(imp.get("refusal_kind").asText()).isEqualTo("UNPARSEABLE");
        assertThat(imp.get("parsed").get("done").asBoolean()).isTrue();
        assertThat(imp.get("draw_key").asText()).endsWith("|a1");
        assertThat(ev).anyMatch(e -> e.get("kind").asText().equals("attempt") && e.get("of").asText().equals("talk")
                && e.get("seat").asText().equals("llm1") && e.get("round").asInt() == 1);
        JsonNode prov = talk(ev, 1, "llm2", 0);
        assertThat(prov.get("outcome").asText()).isEqualTo("REFUSED");
        assertThat(prov.get("refusal_kind").asText()).isEqualTo("PROVIDER");
        assertThat(prov.get("refusal_pattern").asText()).isEqualTo("finish_reason: refusal");
        JsonNode filt = talk(ev, 1, "llm3", 0);
        assertThat(filt.get("refusal_kind").asText()).isEqualTo("BLOCKED");
        assertThat(filt.get("refusal_pattern").asText()).isEqualTo("finish_reason: content_filter");
        // a provider refusal or filter is final: one call each, no repair
        assertThat(ev.stream().filter(e -> e.get("round").asInt() == 1 && e.get("seat") != null
                && e.get("seat").asText().matches("llm[23]") && e.get("kind").asText().matches("talk|attempt"))).hasSize(2);
        JsonNode decl = talk(ev, 2, "llm1", 0);
        assertThat(decl.get("outcome").asText()).isEqualTo("REFUSED");
        assertThat(decl.get("refusal_kind").asText()).isEqualTo("MODEL_DECLINE");
        assertThat(decl.get("parsed").has("message")).isFalse();
        // cut at the token limit: the attempt is flagged truncated, the repaired message is not, and neither is word-capped
        JsonNode cutAttempt = ev.stream().filter(e -> e.get("kind").asText().equals("attempt") && e.get("round").asInt() == 2
                && e.get("seat").asText().equals("llm2")).findFirst().orElseThrow();
        assertThat(cutAttempt.get("truncated").asBoolean()).isTrue();
        assertThat(cutAttempt.get("finish_reason").asText()).isEqualTo("length");
        JsonNode rep = talk(ev, 2, "llm2", 0);
        assertThat(rep.get("outcome").asText()).isEqualTo("REPAIRED");
        assertThat(rep.has("truncated")).isFalse();
        assertThat(rep.get("word_capped").asBoolean()).isFalse();
    }
}
