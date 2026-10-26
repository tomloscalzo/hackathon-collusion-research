package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.agents.llm.Condition;
import io.github.tomloscalzo.collusion.agents.llm.LlmGame;
import io.github.tomloscalzo.collusion.agents.llm.LlmSettings;
import io.github.tomloscalzo.collusion.agents.llm.QuestionPlan;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.MockRequest;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * C13.3 (proposal F1, gotcha 18; R2/R3): in-game question calls after each round, plain-text replies, each seat's own
 * last 10 answers shown back in its own later talk, quote and question prompts only. Canary answers: an answer appears
 * only in its own seat's prompts, only after the round it was given in, and never once it has left the 10-answer window;
 * with questions off nothing changes; the question keys never shift a game or talk key.
 */
class InGameQuestionsTest {
    static final LlmSettings S = new LlmSettings("openai-compatible", "mock-model-1", 0.7, 300);
    static final Pattern KEY = Pattern.compile("(talk|game|question)\\|(?:confidant\\|fed\\|)?[^|]+\\|s\\d+\\|([^|]+)\\|r(\\d+)\\|.*");
    static final Pattern CANARY = Pattern.compile("CANARY-(llm\\d)-r(\\d+)-END");
    static final String QUESTION_OPTIONS = "{\"history_cap\":10,\"question\":\"confidant\",\"question_mode\":\"fed\"}";

    /** Talk: one message, then done; quotes 2.09; every question answered with the seat-and-round canary. */
    static final class Rec implements LlmClient {
        final List<LlmRequest> requests = new ArrayList<>();
        final Function<LlmRequest, String> answer;

        Rec(Function<LlmRequest, String> answer) {
            this.answer = answer;
        }

        @Override
        public LlmResponse complete(LlmRequest r) {
            requests.add(r);
            Matcher m = KEY.matcher(r.drawKey());
            assertThat(m.matches()).as(r.drawKey()).isTrue();
            String text = switch (m.group(1)) {
                case "talk" -> r.drawKey().contains("|t0|") || r.drawKey().contains("|t1|") || r.drawKey().contains("|t2|")
                        ? "{\"message\": \"Hold 2.09?\", \"done\": false}" : "{\"message\": \"\", \"done\": true}";
                case "question" -> answer.apply(r);
                default -> "{\"quote\": 2.09, \"plan\": \"hold\", \"rationale\": \"why-" + m.group(2) + "\"}";
            };
            boolean cut = text.startsWith("!len:"); // a reply cut at the token limit
            return new LlmResponse(cut ? text.substring(5) : text, 10, 10, 0L, false, CanonicalRequest.sha256(r),
                    cut ? "length" : "stop", r.thinking() == Boolean.TRUE ? "reasoning-" + r.drawKey() : null, null);
        }
    }

    static String canary(LlmRequest r) {
        Matcher m = KEY.matcher(r.drawKey());
        m.matches();
        return "I matched them. CANARY-" + m.group(2) + "-r" + m.group(3) + "-END";
    }

    static GameConfig longGame(Path dir, int rounds) throws Exception {
        return GameConfigLoader.load(Path.of(AdversarialMocksI2Test.scenario(dir, "n3-known" + rounds, 3,
                "    type: known\n    periods: " + rounds + "\n", "OFF")));
    }

    static List<QuestionPlan.Entry> questions() {
        return TrialTexts.questions(QUESTION_OPTIONS);
    }

    static Rec play(GameConfig cfg, boolean talk, List<QuestionPlan.Entry> q, Function<LlmRequest, String> answer) {
        Rec rec = new Rec(answer);
        LlmGame.run(cfg, 3, S, Condition.neutral(), 0, rec, null, java.util.Set.of(), true, null, talk,
                LlmGame.Extras.NONE.withQuestions(q));
        return rec;
    }

    static String prompt(LlmRequest r) {
        StringBuilder b = new StringBuilder(r.system());
        r.turns().forEach(t -> b.append("\n").append(t.content()));
        return b.toString();
    }

    @Test
    void aCanaryAppearsOnlyInItsOwnSeatsLaterPromptsWithinTheTenAnswerWindow(@TempDir Path dir) throws Exception {
        for (boolean talk : new boolean[] {true, false}) {
            Rec rec = play(longGame(dir, 14), talk, questions(), InGameQuestionsTest::canary);
            int questionsAsked = 0;
            for (LlmRequest r : rec.requests) {
                Matcher k = KEY.matcher(r.drawKey());
                k.matches();
                String seat = k.group(2);
                int round = Integer.parseInt(k.group(3));
                boolean question = k.group(1).equals("question");
                questionsAsked += question ? 1 : 0;
                List<Integer> seen = new ArrayList<>();
                Matcher c = CANARY.matcher(prompt(r));
                while (c.find()) {
                    assertThat(c.group(1)).as("another seat's answer in " + r.drawKey()).isEqualTo(seat);
                    seen.add(Integer.parseInt(c.group(2)));
                }
                // talk and quote calls of round t show the answers after rounds t-10 .. t-1; the question after round t the
                // answers after rounds t-10 .. t-1 (its own is not yet given)
                List<Integer> expected = new ArrayList<>();
                int newest = round - 1;
                for (int x = Math.max(1, newest - 9); x <= newest; x++) {
                    expected.add(x);
                }
                assertThat(seen).as(r.drawKey()).isEqualTo(expected);
                assertThat(seen.size()).isLessThanOrEqualTo(10);
                if (question) {
                    assertThat(r.responseSchema()).isNull();
                    assertThat(r.turns()).hasSize(1);
                    assertThat(r.turns().get(0).content()).startsWith("Round " + round + " has ended.")
                            .contains("A question: What would you tell a trusted confidant").endsWith("Reply in plain text.")
                            .contains("Your reply this round: quote 2.09. Your rationale: \"why-" + seat + "\"");
                }
            }
            assertThat(questionsAsked).isEqualTo(14 * 3);
            // round 14 still shows exactly rounds 4..13; round 12 drops round 1
            assertThat(rec.requests.stream().filter(r -> r.drawKey().startsWith("game|") && r.drawKey().contains("|llm1|r14|"))
                    .findFirst().orElseThrow().turns().get(0).content()).doesNotContain("CANARY-llm1-r3-END")
                    .contains("CANARY-llm1-r4-END").contains("CANARY-llm1-r13-END")
                    .contains("Your answers (oldest first; at most the last 10 are shown):");
        }
    }

    @Test
    void withQuestionsOffNothingChangesAndQuestionKeysNeverShiftGameOrTalkKeys(@TempDir Path dir) throws Exception {
        GameConfig cfg = longGame(dir, 5);
        Rec off = play(cfg, true, List.of(), InGameQuestionsTest::canary);
        Rec on = play(cfg, true, questions(), InGameQuestionsTest::canary);
        assertThat(off.requests).noneMatch(r -> r.drawKey().startsWith("question|"));
        List<LlmRequest> onGame = on.requests.stream().filter(r -> !r.drawKey().startsWith("question|")).toList();
        assertThat(onGame.stream().map(LlmRequest::drawKey).toList())
                .isEqualTo(off.requests.stream().map(LlmRequest::drawKey).toList());
        // round 1 has no answers yet: its prompts are byte-identical; later ones differ only by the own-answers block
        for (int i = 0; i < onGame.size(); i++) {
            LlmRequest a = off.requests.get(i);
            LlmRequest b = onGame.get(i);
            if (a.drawKey().contains("|r1|")) {
                assertThat(CanonicalRequest.sha256(b)).isEqualTo(CanonicalRequest.sha256(a));
            } else {
                assertThat(b.system()).isEqualTo(a.system());
                assertThat(b.turns().get(0).content().replaceAll("(?s)\n+After earlier rounds you were asked: .*?-END\"(?=\n\n|\n[A-Z])", ""))
                        .as(b.drawKey()).isEqualTo(a.turns().get(0).content());
            }
        }
        // every call has its own request hash
        assertThat(on.requests.stream().map(CanonicalRequest::sha256).distinct().count()).isEqualTo(on.requests.size());
    }

    @Test
    void refusedTruncatedOrEmptyAnswersAreLoggedButNotFedBack(@TempDir Path dir) throws Exception {
        GameConfig cfg = longGame(dir, 4);
        Rec rec = play(cfg, true, questions(), r -> r.drawKey().contains("|r1|") ? "I'm sorry, but I can't help with that."
                : r.drawKey().contains("|r2|") ? "<think>going on and on" : r.drawKey().contains("|r3|") ? "" : canary(r));
        for (LlmRequest r : rec.requests) {
            assertThat(prompt(r)).doesNotContain("can't help with that").doesNotContain("going on and on")
                    .doesNotContain("After earlier rounds you were asked");
        }
    }

    @Test
    void withThinkingOnReasoningCutOrRefusalShapedAnswersAreNeverFedBackAndAreFlagged(@TempDir Path dir) throws Exception {
        GameConfig cfg = longGame(dir, 6);
        LlmSettings on = new LlmSettings("openai-compatible", "mock-model-1", 0.6, 300, true, 0.95, 20);
        Rec rec = new Rec(r -> r.drawKey().contains("|r1|") ? "<think>SECRET-REASONING</think>I held my price."
                : r.drawKey().contains("|r2|") ? "!len:a partial answer SECRET-CUT"
                : r.drawKey().contains("|r3|") ? "!len:I'm sorry, but I can't help with that. SECRET-CUT2"
                : r.drawKey().contains("|r4|") ? "<THINK>SECRET-OPEN" : canary(r));
        Path ev = dir.resolve("events.jsonl");
        io.github.tomloscalzo.collusion.trial.EventsWriter w = new io.github.tomloscalzo.collusion.trial.EventsWriter(ev);
        LlmGame.run(cfg, 3, on, Condition.neutral(), 0, rec, null, java.util.Set.of(), true, w, true,
                LlmGame.Extras.NONE.withQuestions(questions()));
        for (LlmRequest r : rec.requests) {
            assertThat(prompt(r)).as(r.drawKey()).doesNotContain("SECRET").doesNotContain("reasoning-");
        }
        // by round 6 the only answer fed back is the one after round 5 (rounds 1-4 were withheld)
        assertThat(rec.requests.stream().filter(r -> r.drawKey().startsWith("game|") && r.drawKey().contains("|llm1|r6|"))
                .findFirst().orElseThrow().turns().get(0).content()).contains("CANARY-llm1-r5-END")
                .doesNotContain("After round 1:").doesNotContain("After round 4:");
        List<JsonNode> qs = new ArrayList<>();
        for (String l : Files.readAllLines(ev)) {
            JsonNode e = Canonical.MAPPER.readTree(l);
            if (e.get("kind").asText().equals("question") && e.get("seat").asText().equals("llm1")) {
                qs.add(e);
            }
        }
        assertThat(qs.get(0).get("refusal_kind").asText()).isEqualTo("TRUNCATED");     // a closed think in the answer
        assertThat(qs.get(0).get("truncated_thinking").asBoolean()).isTrue();
        assertThat(qs.get(1).get("refusal_kind").asText()).isEqualTo("TRUNCATED");     // cut at the limit
        assertThat(qs.get(1).get("truncated").asBoolean()).isTrue();
        assertThat(qs.get(1).get("truncated_thinking").asBoolean()).isTrue();
        assertThat(qs.get(2).get("refusal_kind").asText()).isEqualTo("TRUNCATED");     // a refusal shape cut at the limit
        assertThat(qs.get(2).has("refusal_pattern")).isFalse();
        assertThat(qs.get(3).get("truncated_thinking").asBoolean()).isTrue();          // an opened think, any case
        assertThat(qs.get(4).get("outcome").asText()).isEqualTo("OK");
        assertThat(qs.get(4).get("reasoning").asText()).startsWith("reasoning-question|");
    }

    @Test
    void theReservationCountsTheQuestionsAndTheAnswersEveryLaterCallCarries() {
        GameConfig cfg = GameConfigLoader.loadResource("scenarios/n3-group.yaml");
        LlmSettings q = new LlmSettings("openai-compatible", "m", 0.7, 400);
        int rounds = cfg.scenario().time().maxRounds();
        long one = LlmCommands.questionEstimate(cfg, q, Condition.neutral(), 0, 1, true, 1);
        // at least: per seat and round, the question's reply and the ten answers in the question, 8 talk and 2 quote calls
        assertThat(one).isGreaterThanOrEqualTo(3L * rounds * (400 + 11L * 10 * 400));
        assertThat(LlmCommands.questionEstimate(cfg, q, Condition.neutral(), 0, 1, true, 2)).isGreaterThan(one);
        assertThat(LlmCommands.questionEstimate(cfg, q, Condition.neutral(), 0, 1, false, 1)).isLessThan(one);
    }

    @Test
    void theCommandLineAsksLogsRecordsReplaysAndTheTablesHoldTheAnswers(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("q.jsonl");
        Path trial = dir.resolve("root").resolve("r2").resolve("t");
        List<MockRequest> reqs;
        Function<MockRequest, Reply> f = r -> {
            if (r.user().startsWith("question|")) {
                return Reply.text("Answer of " + r.user().split("\\|")[5] + " after " + r.user().split("\\|")[6])
                        .withReasoning("private thought " + r.callIndex(), 4);
            }
            return Reply.text(r.user().startsWith("talk|") ? (r.lastUser().contains("You have sent 0 of")
                    ? "{\"message\": \"Hold 2.09?\", \"done\": false}" : "{\"message\": \"\", \"done\": true}")
                    : "{\"quote\": 2.09, \"plan\": \"hold\", \"rationale\": \"why\"}");
        };
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(f))) {
            LlmCommands.run(TrialDirCliTest.o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "model", "mock-model-1",
                    "seed", "2", "out", out.toString(), "multi-seat", "on", "talk", "on", "trial-dir", trial.toString(),
                    "analysis-script", "../tools/analysis.py", "code-commit", "abc1234", "base-url", s.baseUrl(),
                    "condition-texts", "all:private_chat", "options", QUESTION_OPTIONS, "max-tokens-question", "222"));
            reqs = s.requests();
        }
        int rounds = Canonical.MAPPER.readTree(Files.readAllLines(out).get(0)).get("rounds").size();
        List<MockRequest> qs = reqs.stream().filter(r -> r.user().startsWith("question|")).toList();
        assertThat(qs).hasSize(3 * rounds);
        for (MockRequest q : qs) {
            JsonNode b = Canonical.MAPPER.readTree(q.rawBody());
            assertThat(b.has("response_format")).isFalse();
            assertThat(b.get("max_tokens").asInt()).isEqualTo(222);
            assertThat(q.user()).matches("question\\|confidant\\|fed\\|n3-group\\|s2\\|llm\\d\\|r\\d+\\|a0");
        }
        assertThat(reqs).noneMatch(r -> r.rawBody().contains("private thought")); // reasoning never fed back
        List<JsonNode> ev = TrialDirCliTest.events(trial).stream().filter(e -> e.get("kind").asText().equals("question")).toList();
        assertThat(ev).hasSize(3 * rounds);
        JsonNode e = ev.get(0);
        assertThat(e.get("name").asText()).isEqualTo("confidant");
        assertThat(e.get("mode").asText()).isEqualTo("fed");
        assertThat(e.get("outcome").asText()).isEqualTo("OK");
        assertThat(e.get("parsed").get("message").asText()).startsWith("Answer of llm");
        assertThat(e.get("reasoning").asText()).startsWith("private thought");
        JsonNode p = Canonical.MAPPER.readTree(Files.readString(trial.resolve("params.json")));
        assertThat(p.get("draw_keys").toString()).contains("question|<name>|fed|");
        assertThat(Files.readAllLines(Path.of(out + ".calls.jsonl"))).filteredOn(l -> l.contains("\"kind\":\"question\""))
                .hasSize(3 * rounds);
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
        SeatsIntegrationI1Test.schemaCheck(out, Path.of(out + ".calls.jsonl"));
        Path tools = AdversarialMocksI2Test.tools();
        assumeTrue(tools != null, "tools/trial not found");
        TrialDirCliTest.python(tools.resolve("collect.py").toString(), dir.resolve("root").toString(),
                dir.resolve("tables").toString());
        assertThat(Files.readAllLines(dir.resolve("tables/questions.csv"))).hasSize(1 + 3 * rounds);
    }

    @Test
    void questionOptionsAreCheckedAndThePostGamePassIsNotPlayedInAGame() {
        assertThatThrownBy(() -> TrialTexts.questions("{\"question\":\"confidant\",\"question_mode\":\"post\"}"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrialTexts.questions("{\"question\":\"confidant\",\"history_cap\":5}"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrialTexts.questions("{\"question\":\"private_chat\"}"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(TrialTexts.questions("{\"round_reminder\":\"compliance_reminder\"}")).isEmpty();
        GameConfig cfg = GameConfigLoader.loadResource("scenarios/n3-group.yaml");
        assertThatThrownBy(() -> LlmGame.run(cfg, 3, S, Condition.neutral(), 0, new Rec(r -> "x"), null, java.util.Set.of(),
                false, null, false, LlmGame.Extras.NONE.withQuestions(questions()))).isInstanceOf(IllegalArgumentException.class);
    }
}
