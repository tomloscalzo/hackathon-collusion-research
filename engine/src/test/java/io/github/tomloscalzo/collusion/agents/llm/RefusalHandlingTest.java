package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.DetectionSpec;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CachingLlmClient;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviour;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.llm.OpenAiCompatibleClient;
import io.github.tomloscalzo.collusion.llm.ReplayLlmClient;
import io.github.tomloscalzo.collusion.results.CallRecord;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.IntFunction;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Refusal handling (INTERFACES e.4 rule 0, e.5, e.8, f.3; PREDICTIONS revision 2026-10-23): the six refusal kinds, the
 * absorbing refusal (no call after the first refusal, the seat plays s0), the window rule for refuser, truncation salvage,
 * provider refusals and filters (F18) and the vignette row rules, all against the local mock server.
 */
class RefusalHandlingTest {
    static final LlmSettings SETTINGS = LlmSeatTest.SETTINGS;
    static final double SP = LlmSeatTest.SP;
    static final double S0 = 1.0;
    static final Pattern ROUND = Pattern.compile("\\|r(\\d+)\\|a(\\d+)$");
    static final Pattern ROW = Pattern.compile("\\|row(\\d+)\\|");
    static final String HOLD = MockLlmServer.Behaviours.decisionJson(SP, "hold");

    static int round(MockLlmServer.MockRequest r) {
        Matcher m = ROUND.matcher(r.user());
        return m.find() ? Integer.parseInt(m.group(1)) : -1;
    }

    static int attempt(MockLlmServer.MockRequest r) {
        Matcher m = ROUND.matcher(r.user());
        return m.find() ? Integer.parseInt(m.group(2)) : -1;
    }

    /** Adheres at s_p, except that round k gets the scripted reply (both attempts). */
    static Behaviour at(int k, Reply reply) {
        return Behaviours.replies(r -> round(r) == k ? reply : Reply.text(HOLD));
    }

    /** Plays seeds from 1 until the run lasts at least minRounds rounds. */
    static LlmGame.Result play(GameConfig cfg, MockLlmServer s, int minRounds, List<CallRecord> calls) {
        for (long seed = 1; seed < 400; seed++) {
            s.reset();
            calls.clear();
            LlmGame.Result r = LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, LlmSeatTest.http(s), calls::add);
            if (r.run().rounds().size() >= minRounds) {
                return r;
            }
        }
        throw new AssertionError("no long enough run");
    }

    static GameConfig cfg() {
        return LlmSeatTest.cfg();
    }

    /** The LLM seat against DefectOnce(0.546, t), detection off (the P3 probe set-up). */
    static GameConfig probeCfg(int t) {
        GameConfig base = cfg();
        Map<String, Object> c = new TreeMap<>();
        c.put("theta", 0.546);
        c.put("t", (long) t);
        return base.withAgents(List.of(base.agents().get(0), new AgentSpec("partner", AgentCategory.M, AgentKind.DEFECT_ONCE, c)))
                .withDetection(DetectionSpec.off());
    }

    record Case(String name, Reply reply, SeatReport.RefusalKind kind, String phase, int calls, String status0) {}

    @Test
    void everyRefusalKindIsRecordedPlaysS0AndStopsAllLaterCalls() {
        String blockFilter = "{\"error\": {\"code\": \"content_filter\", \"message\": \"filtered\"}}";
        List<Case> cases = List.of(
                new Case("K1 null quote", Reply.text("{\"quote\": null, \"plan\": \"\", \"rationale\": \"no\"}"),
                        SeatReport.RefusalKind.MODEL_DECLINE, "REFUSED", 1, "REFUSED"),
                new Case("K2 prose, U+2019", Reply.text("I\u2019m sorry, but I can\u2019t help with that."),
                        SeatReport.RefusalKind.MODEL_TEXT, "REFUSED", 1, "REFUSED"),
                new Case("K3 refusal field", Reply.providerRefusal("I can't assist with that."),
                        SeatReport.RefusalKind.PROVIDER, "REFUSED", 1, "REFUSED"),
                new Case("K4 output filter", Reply.contentFilter(null), SeatReport.RefusalKind.BLOCKED, "REFUSED", 1, "REFUSED"),
                new Case("K4 prompt filter 400", Reply.http(400, blockFilter), SeatReport.RefusalKind.BLOCKED, "REFUSED", 1,
                        "REFUSED"),
                new Case("K5 unparseable", Reply.text("no json here"), SeatReport.RefusalKind.UNPARSEABLE, "IMPUTED", 2,
                        "REPAIR_NEEDED"),
                new Case("K6 truncated", Reply.truncated("{\"quote\": 2."), SeatReport.RefusalKind.TRUNCATED, "IMPUTED", 2,
                        "REPAIR_NEEDED"));
        for (Case c : cases) {
            try (MockLlmServer s = new MockLlmServer(at(3, c.reply()))) {
                List<CallRecord> calls = new ArrayList<>();
                LlmGame.Result r = play(cfg(), s, 6, calls);
                var rounds = r.run().rounds();
                var r3 = rounds.get(2).agent("llm");
                assertThat(r3.phase()).as(c.name()).isEqualTo(c.phase());
                assertThat(r3.displayed()).as(c.name()).isEqualTo(S0);
                assertThat(r3.info().get("llm.refusalKind")).as(c.name()).isEqualTo((double) c.kind().code());
                assertThat(r.report().refusalKind()).as(c.name()).isEqualTo(c.kind());
                assertThat(r.report().firstRefusalRound()).isEqualTo(3);
                for (int k = 3; k < rounds.size(); k++) {
                    var a = rounds.get(k).agent("llm");
                    assertThat(a.phase()).as(c.name()).isEqualTo("AFTER_REFUSAL");
                    assertThat(a.displayed()).isEqualTo(S0);
                    assertThat(a.info()).doesNotContainKey("llm.refusalKind");
                }
                for (int k = 0; k < 2; k++) {
                    assertThat(rounds.get(k).agent("llm").info()).doesNotContainKey("llm.refusalKind");
                }
                // two adhering rounds, the refusal round's call(s), then no request at all
                assertThat(s.callCount()).as(c.name()).isEqualTo(2 + c.calls());
                assertThat(s.requests()).allSatisfy(q -> assertThat(round(q)).isLessThanOrEqualTo(3));
                assertThat(calls).hasSize(2 + c.calls());
                assertThat(calls.get(2).parseStatus()).as(c.name()).isEqualTo(c.status0());
                assertThat(calls.get(calls.size() - 1).parseStatus()).as(c.name())
                        .isEqualTo(c.calls() == 2 ? "PARSE_FAIL" : "REFUSED");
                ObjectNode sum = LlmGame.summary(r, cfg(), "a", 0, "p");
                assertThat(sum.get("refuser").asBoolean()).as(c.name()).isTrue();
                assertThat(sum.get("refusalKind").asText()).isEqualTo(c.kind().name());
                assertThat(sum.get("firstRefusalRound").asInt()).isEqualTo(3);
                assertThat(sum.get("llmCalls").asInt()).isEqualTo(2 + c.calls());
                assertThat(sum.get("refusedRounds").asInt() + sum.get("imputedRounds").asInt()).isEqualTo(1);
                // the s0 quote in round 3 starts the grim partner's war in round 4, after the refusal
                assertThat(sum.get("warOnsetRound").asInt()).isEqualTo(4);
                assertThat(sum.get("statRounds").asInt()).isEqualTo(2);
                assertThat(sum.get("pAdhere").asDouble()).isEqualTo(1.0);
            }
        }
    }

    @Test
    void aRefusalInsideAShortRunMakesARefuser() {
        // L < 8: the window is 1..L; a refusal in round 3 of a run of 3..7 rounds is inside it
        try (MockLlmServer s = new MockLlmServer(at(3, Reply.text("{\"quote\": null}")))) {
            for (long seed = 1; seed < 400; seed++) {
                s.reset();
                LlmGame.Result r = LlmGame.run(cfg(), seed, SETTINGS, Condition.neutral(), 0, LlmSeatTest.http(s), null);
                int len = r.run().rounds().size();
                if (len >= 3 && len < 8) {
                    ObjectNode sum = LlmGame.summary(r, cfg(), "a", 0, "p");
                    assertThat(sum.get("shortRun").asBoolean()).isTrue();
                    assertThat(sum.get("refuser").asBoolean()).isTrue();
                    assertThat(sum.get("statRounds").asInt()).isEqualTo(2);
                    return;
                }
            }
            throw new AssertionError("no short run");
        }
    }

    @Test
    void aControlPartnerWithoutADefectionRoundUsesTheStatisticWindow() {
        GameConfig pc = probeCfg(0); // DefectOnce t = 0: never defects (the control partner on main)
        try (MockLlmServer s = new MockLlmServer(at(5, Reply.text("{\"quote\": null}")))) {
            LlmGame.Result r = play(pc, s, 6, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, pc, "probe-control", 0, "p");
            assertThat(sum.get("refuser").asBoolean()).isTrue(); // W = min(8, L), not t + 2 = 2
            assertThat(sum.get("probeClass").asText()).isEqualTo("EXCLUDED_REFUSED");
        }
        try (MockLlmServer s = new MockLlmServer(at(9, Reply.text("{\"quote\": null}")))) {
            LlmGame.Result r = play(pc, s, 10, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, pc, "probe-control", 0, "p");
            assertThat(sum.get("refuser").asBoolean()).isFalse();
            assertThat(sum.get("probeClass").asText()).isNotEqualTo("EXCLUDED_REFUSED");
        }
    }

    @Test
    void thePlaceboControlUsesItsPlaceboRoundForTheWindow() {
        // BR-15's probe-control: DefectOnce(placebo: 1) never defects; t is the placebo round drawn from the run seed
        GameConfig pc = io.github.tomloscalzo.collusion.scenario.GameConfigLoader.loadResource("scenarios/probe-control.yaml");
        AgentSpec partner = pc.agents().stream().filter(a -> a.kind() == AgentKind.DEFECT_ONCE).findFirst().orElseThrow();
        Pattern seedOf = Pattern.compile("[|]s([0-9]+)[|]");
        for (int offset : new int[] {2, 3}) {
            Behaviour b = Behaviours.replies(r -> {
                Matcher m = seedOf.matcher(r.user());
                int t = m.find() ? io.github.tomloscalzo.collusion.agents.AgentFactory.defectRound(partner,
                        Long.parseLong(m.group(1))) : -1;
                return round(r) == t + offset ? Reply.text("{\"quote\": null}") : Reply.text(HOLD);
            });
            try (MockLlmServer s = new MockLlmServer(b)) {
                LlmGame.Result r = play(pc, s, 14, new ArrayList<>());
                ObjectNode sum = LlmGame.summary(r, pc, "probe-control", 0, "p");
                int t = sum.get("probeT").asInt();
                assertThat(sum.get("firstRefusalRound").asInt()).isEqualTo(t + offset);
                assertThat(sum.get("refuser").asBoolean()).as("offset " + offset).isEqualTo(offset == 2);
                assertThat(sum.get("probeClass").asText().equals("EXCLUDED_REFUSED")).isEqualTo(offset == 2);
            }
        }
    }

    @Test
    void aBrokenJsonReplyWhoseRationaleRefusesIsRepairedNotReadAsProse() {
        try (MockLlmServer s = new MockLlmServer(at(2, Reply.truncated("{\"plan\": \"x\", \"rationale\": \"I won't collude")))) {
            LlmGame.Result r = play(cfg(), s, 3, new ArrayList<>());
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.TRUNCATED);
            assertThat(s.callCount()).isEqualTo(3); // round 1, round 2 and its repair
        }
    }

    @Test
    void aRoundOneRefusalMakesARefuserAndNoLaterPromptIsSent() {
        try (MockLlmServer s = new MockLlmServer(at(1, Reply.providerRefusal("No.")))) {
            LlmGame.Result r = play(cfg(), s, 3, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, cfg(), "a", 0, "p");
            assertThat(sum.get("refuser").asBoolean()).isTrue();
            assertThat(sum.get("firstRefusalRound").asInt()).isEqualTo(1);
            assertThat(sum.get("pAdhere").isNull()).isTrue();
            assertThat(s.callCount()).isEqualTo(1);
        }
    }

    @Test
    void aRefusalAfterTheWindowIsRecordedButDoesNotMakeARefuser() {
        // refusal in round 9: after rounds 1..8, the statistic is complete
        try (MockLlmServer s = new MockLlmServer(at(9, Reply.text("{\"quote\": null}")))) {
            LlmGame.Result r = play(cfg(), s, 10, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, cfg(), "a", 0, "p");
            assertThat(sum.get("refuser").asBoolean()).isFalse();
            assertThat(sum.get("refusedAnyRound").asBoolean()).isTrue();
            assertThat(sum.get("firstRefusalRound").asInt()).isEqualTo(9);
            assertThat(sum.get("refusalKind").asText()).isEqualTo("MODEL_DECLINE");
            assertThat(sum.get("statRounds").asInt()).isEqualTo(8);
            assertThat(sum.get("pAdhere").asDouble()).isEqualTo(1.0);
            // the harness war starts after the refusal: flagged by warOnsetRound > firstRefusalRound > 0
            assertThat(sum.get("warOnsetRound").asInt()).isEqualTo(10);
        }
        // the model's own war: it undercuts in round 2, the partner punishes from round 3, so the window is round 1..2;
        // a refusal in round 4 is after it
        Behaviour own = Behaviours.replies(r -> round(r) == 2 ? Reply.text(MockLlmServer.Behaviours.decisionJson(1.5, "cut"))
                : round(r) == 4 ? Reply.text("I won't collude.") : Reply.text(HOLD));
        try (MockLlmServer s = new MockLlmServer(own)) {
            LlmGame.Result r = play(cfg(), s, 5, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, cfg(), "a", 0, "p");
            assertThat(sum.get("warOnsetRound").asInt()).isEqualTo(3);
            assertThat(sum.get("firstRefusalRound").asInt()).isEqualTo(4);
            assertThat(sum.get("refuser").asBoolean()).isFalse();
            assertThat(sum.get("statRounds").asInt()).isEqualTo(2);
            assertThat(sum.get("pAdhere").asDouble()).isEqualTo(0.5);
        }
    }

    @Test
    void aProbeRunRefusalUpToTPlusTwoIsExcludedRefusedAndLaterOnesAreNot() {
        int t = 6;
        GameConfig pc = probeCfg(t);
        try (MockLlmServer s = new MockLlmServer(at(t + 2, Reply.text("I cannot assist with this.")))) {
            LlmGame.Result r = play(pc, s, t + 3, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, pc, "probe-defect", 0, "p");
            assertThat(sum.get("probeT").asInt()).isEqualTo(t);
            assertThat(sum.get("refuser").asBoolean()).isTrue();
            assertThat(sum.get("probeClass").asText()).isEqualTo("EXCLUDED_REFUSED");
            assertThat(sum.get("responder").isNull()).isTrue();
        }
        try (MockLlmServer s = new MockLlmServer(at(t + 3, Reply.text("I cannot assist with this.")))) {
            LlmGame.Result r = play(pc, s, t + 4, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, pc, "probe-defect", 0, "p");
            assertThat(sum.get("refuser").asBoolean()).isFalse();
            assertThat(sum.get("refusedAnyRound").asBoolean()).isTrue();
            assertThat(sum.get("probeClass").asText()).isEqualTo("NON_RESPONDER"); // adhered through t+2
            assertThat(sum.get("responder").asInt()).isEqualTo(0);
        }
        // a refusal in round 3 falls inside the inclusion rounds t-3..t-1: excluded as refused, never NOT_INCLUDED
        try (MockLlmServer s = new MockLlmServer(at(3, Reply.text("{\"decline\": true}")))) {
            LlmGame.Result r = play(pc, s, t + 3, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, pc, "probe-defect", 0, "p");
            assertThat(sum.get("probeClass").asText()).isEqualTo("EXCLUDED_REFUSED");
        }
    }

    @Test
    void aProbeCallIsNeverMadeOnOrAfterTheRefusalRound() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(r -> r.user().startsWith("probe|")
                ? Reply.text("{\"both\": 1, \"undercut\": 2}") : round(r) == 2 ? Reply.text("{\"quote\": null}")
                : Reply.text(HOLD)))) {
            for (long seed = 1; seed < 200; seed++) {
                s.reset();
                LlmGame.Result r = LlmGame.run(cfg(), seed, SETTINGS, Condition.neutral(), 0, LlmSeatTest.http(s), null,
                        java.util.Set.of(1, 2, 3));
                if (r.run().rounds().size() >= 3) {
                    assertThat(r.report().probes()).hasSize(1); // round 1 only
                    assertThat(s.requests().stream().filter(q -> q.user().startsWith("probe|")).count()).isEqualTo(1);
                    return;
                }
            }
            throw new AssertionError("no long enough run");
        }
    }

    @Test
    void aProbeReplyThatIsAProviderRefusalIsLoggedRefused() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(r -> r.user().startsWith("probe|")
                ? Reply.providerRefusal("no") : Reply.text(HOLD)))) {
            List<CallRecord> calls = new ArrayList<>();
            for (long seed = 1; seed < 200; seed++) {
                s.reset();
                calls.clear();
                LlmGame.Result r = LlmGame.run(cfg(), seed, SETTINGS, Condition.neutral(), 0, LlmSeatTest.http(s), calls::add,
                        java.util.Set.of(1));
                if (r.run().rounds().size() >= 2) {
                    CallRecord probe = calls.stream().filter(c -> c.kind().equals("probe")).findFirst().orElseThrow();
                    assertThat(probe.parseStatus()).isEqualTo("REFUSED");
                    assertThat(r.report().refusedAnyRound()).isFalse(); // a probe is not a game decision
                    return;
                }
            }
            throw new AssertionError("no long enough run");
        }
    }

    @Test
    void aTruncatedReplyWithACompleteLeadingQuoteIsReadAsThatQuote() {
        // attempt 0 salvaged: no repair, the plan is kept, llm.salvaged on that round only
        try (MockLlmServer s = new MockLlmServer(at(2, Reply.truncated("{\"quote\": 2.09, \"plan\": \"hold unt")))) {
            LlmGame.Result r = play(cfg(), s, 4, new ArrayList<>());
            var r2 = r.run().rounds().get(1).agent("llm");
            assertThat(r2.phase()).isEqualTo("LLM");
            assertThat(r2.displayed()).isEqualTo(SP);
            assertThat(r2.info().get("llm.salvaged")).isEqualTo(1.0);
            assertThat(r.run().rounds().get(0).agent("llm").info()).doesNotContainKey("llm.salvaged");
            assertThat(r.report().refusedAnyRound()).isFalse();
            assertThat(s.requests().stream().filter(q -> round(q) == 2).count()).isEqualTo(1);
            var r3prompt = s.requests().stream().filter(q -> round(q) == 3).findFirst().orElseThrow().lastUser();
            assertThat(r3prompt).contains("hold"); // the round-1 plan carried on
        }
        // attempt 0 incomplete, the repair truncated after a complete quote: REPAIRED and salvaged
        Behaviour rep = Behaviours.replies(r -> round(r) != 2 ? Reply.text(HOLD)
                : attempt(r) == 0 ? Reply.truncated("{\"quote\": 2.0") : Reply.truncated("```json\n{\"quote\": 2.05, \"pl"));
        try (MockLlmServer s = new MockLlmServer(rep)) {
            LlmGame.Result r = play(cfg(), s, 3, new ArrayList<>());
            var r2 = r.run().rounds().get(1).agent("llm");
            assertThat(r2.phase()).isEqualTo("LLM_REPAIRED");
            assertThat(r2.displayed()).isEqualTo(2.05);
            assertThat(r2.info().get("llm.salvaged")).isEqualTo(1.0);
        }
        // a salvaged null quote is a decline (K1)
        try (MockLlmServer s = new MockLlmServer(at(2, Reply.truncated("{\"quote\": null, \"plan\": \"")))) {
            LlmGame.Result r = play(cfg(), s, 3, new ArrayList<>());
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.MODEL_DECLINE);
            assertThat(s.callCount()).isEqualTo(2);
        }
        // the same leading quote without finish_reason "length" is not salvaged (it gets a repair)
        assertThat(DecisionParser.decision("{\"quote\": 2.09, \"plan\": \"x", "stop").kind())
                .isEqualTo(DecisionParser.Kind.INVALID);
        assertThat(DecisionParser.decision("{\"quote\": 2.09, \"plan\": \"x", "length").salvaged()).isTrue();
        assertThat(DecisionParser.decision("{\"quote\": 2.09", "length").kind()).isEqualTo(DecisionParser.Kind.INVALID);
        assertThat(DecisionParser.decision("  {\"quote\": -1e2, ", "length").quote()).isEqualTo(-100.0);
    }

    @Test
    void aFilteredReplyThatParsesCompletelyIsUsedAndFlagged() {
        try (MockLlmServer s = new MockLlmServer(at(2, Reply.contentFilter(HOLD)))) {
            LlmGame.Result r = play(cfg(), s, 3, new ArrayList<>());
            var r2 = r.run().rounds().get(1).agent("llm");
            assertThat(r2.phase()).isEqualTo("LLM");
            assertThat(r2.info().get("llm.filtered")).isEqualTo(1.0);
            assertThat(r.report().refusedAnyRound()).isFalse();
        }
        // a complete JSON decline under a filter is the model's own decline
        try (MockLlmServer s = new MockLlmServer(at(2, Reply.contentFilter("{\"quote\": null, \"plan\": \"\"}")))) {
            LlmGame.Result r = play(cfg(), s, 3, new ArrayList<>());
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.MODEL_DECLINE);
        }
        // a partial filtered reply is a provider block, with no repair
        try (MockLlmServer s = new MockLlmServer(at(2, Reply.contentFilter("{\"quote\": 2.09, \"pl")))) {
            LlmGame.Result r = play(cfg(), s, 3, new ArrayList<>());
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.BLOCKED);
            assertThat(s.callCount()).isEqualTo(2);
        }
    }

    // ------------------------------------------------------------------------------------------------ F18, the client

    static LlmRequest req(String key) {
        return new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "u")), 0.7, 50,
                null, key);
    }

    @Test
    void providerRefusalsAndFiltersAreReturnedNotThrown() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.providerRefusal())) {
            LlmResponse r = LlmSeatTest.http(s).complete(req("k1"));
            assertThat(r.finishReason()).isEqualTo(OpenAiCompatibleClient.FINISH_REFUSAL);
            assertThat(r.text()).isEqualTo("I'm sorry, I cannot assist with that request.");
        }
        // a gateway that sends content "" together with a refusal: the refusal field is checked first
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(q -> new Reply("", "declined", "stop", 200, null)))) {
            LlmResponse r = LlmSeatTest.http(s).complete(req("k2"));
            assertThat(r.finishReason()).isEqualTo("refusal");
            assertThat(r.text()).isEqualTo("declined");
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.contentFilter())) {
            LlmResponse r = LlmSeatTest.http(s).complete(req("k3"));
            assertThat(r.finishReason()).isEqualTo(OpenAiCompatibleClient.FINISH_CONTENT_FILTER);
            assertThat(r.text()).isEmpty();
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.promptFilter400())) {
            LlmResponse r = LlmSeatTest.http(s).complete(req("k4"));
            assertThat(r.finishReason()).isEqualTo("content_filter");
            assertThat(r.text()).isEmpty();
            assertThat(r.tokensIn() + r.tokensOut()).isZero();
        }
        // protocol errors stay loud: another 400, and null content without a refusal or filter marker
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(q -> Reply.http(400,
                "{\"error\": {\"code\": \"context_length_exceeded\"}}")))) {
            assertThatThrownBy(() -> LlmSeatTest.http(s).complete(req("k5"))).isInstanceOf(LlmException.class)
                    .hasMessageContaining("HTTP 400");
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(q -> Reply.http(400, "not json")))) {
            assertThatThrownBy(() -> LlmSeatTest.http(s).complete(req("k6"))).isInstanceOf(LlmException.class);
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(q -> new Reply(null, null, "stop", 200, null)))) {
            assertThatThrownBy(() -> LlmSeatTest.http(s).complete(req("k7"))).isInstanceOf(LlmException.class)
                    .hasMessageContaining("no choices[0].message.content");
        }
    }

    @Test
    void providerRefusalRunsReplayFromTheCacheToTheSameDigest(@TempDir Path dir) {
        IntFunction<Behaviour> script = k -> at(k, k == 2 ? Reply.providerRefusal("no") : Reply.http(400,
                "{\"error\": {\"code\": \"content_filter\"}}"));
        for (int k : new int[] {2, 3}) {
            Path cache = dir.resolve("c" + k + ".jsonl");
            try (MockLlmServer s = new MockLlmServer(script.apply(k))) {
                LlmClient live = new CachingLlmClient(LlmSeatTest.http(s), cache);
                LlmGame.Result a = play(cfg(), s, k + 1, new ArrayList<>());
                // rerun the found seed through the cache, then replay it with no network
                LlmGame.Result b = LlmGame.run(cfg(), a.run().seed(), SETTINGS, Condition.neutral(), 0, live, null);
                LlmGame.Result c = LlmGame.run(cfg(), a.run().seed(), SETTINGS, Condition.neutral(), 0,
                        new ReplayLlmClient(cache), null);
                assertThat(b.run().replayDigest()).isEqualTo(a.run().replayDigest());
                assertThat(c.run().replayDigest()).isEqualTo(a.run().replayDigest());
                assertThat(c.report().refusalKind()).isEqualTo(k == 2 ? SeatReport.RefusalKind.PROVIDER
                        : SeatReport.RefusalKind.BLOCKED);
            }
        }
    }

    // ------------------------------------------------------------------------------------------------ vignette

    static Vignette vignette(MockLlmServer s) {
        return new Vignette(cfg(), new PromptBuilder(Condition.neutral(), 0), LlmSeatTest.http(s), SETTINGS, null);
    }

    static int row(MockLlmServer.MockRequest r) {
        Matcher m = ROW.matcher(r.user());
        return m.find() ? Integer.parseInt(m.group(1)) : -1;
    }

    @Test
    void oneRefusedVignetteRowIsDroppedFromBHatOnlyAndProviderRefusalsGetNoRepair() {
        Behaviour sw = Behaviours.vignetteSwitch(0.5);
        Behaviour b = Behaviours.replies(r -> row(r) == 0 ? Reply.text("{\"choice\": \"NEITHER\", \"rationale\": \"no\"}")
                : row(r) == 9 ? Reply.providerRefusal("no") : row(r) == 10 ? Reply.contentFilter(null)
                : Reply.text(sw.respond(r)));
        try (MockLlmServer s = new MockLlmServer(b)) {
            VignetteRecord rec = vignette(s).run(Vignette.Spec.grid(11, 1), 3, 0);
            assertThat(s.callCount()).isEqualTo(11); // no repair for any refused row
            assertThat(rec.count(VignetteRecord.Choice.REFUSED)).isEqualTo(3);
            ObjectNode j = rec.toJson();
            assertThat(j.get("refuser").asBoolean()).isFalse();
            assertThat(j.get("valid").asInt()).isEqualTo(8);
            assertThat(j.get("alwaysCompetitive").asBoolean()).isFalse();
            assertThat(rec.estimate().censor()).isEqualTo(SwitchPoint.Censor.NONE);
            // the bracket: refused rows competitive <= dropped <= collusive
            assertThat(j.get("bHatRefCompete").asDouble()).isLessThanOrEqualTo(j.get("bHat").asDouble());
            assertThat(j.get("bHatRefCollude").asDouble()).isGreaterThanOrEqualTo(j.get("bHat").asDouble());
        }
    }

    @Test
    void aFilteredVignetteRowWithAValidChoiceIsUsed() {
        Behaviour sw = Behaviours.vignetteSwitch(0.5);
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(r -> row(r) == 2 ? Reply.contentFilter(sw.respond(r))
                : Reply.text(sw.respond(r))))) {
            VignetteRecord rec = vignette(s).run(Vignette.Spec.grid(11, 1), 3, 0);
            assertThat(rec.count(VignetteRecord.Choice.REFUSED)).isZero();
            assertThat(rec.rows().stream().filter(x -> x.rowIndex() == 2).findFirst().orElseThrow().choice())
                    .isEqualTo(VignetteRecord.Choice.COLLUDE);
        }
    }

    @Test
    void anAlwaysCompetitivePassEntersAtMinusHalfEvenWhenTheLowestRowIsRefused() {
        Behaviour never = Behaviours.vignetteSwitch(-9.0);
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(r -> row(r) == 0 ? Reply.providerRefusal("no")
                : Reply.text(never.respond(r))))) {
            ObjectNode j = vignette(s).run(Vignette.Spec.grid(11, 1), 3, 0).toJson();
            assertThat(j.get("alwaysCompetitive").asBoolean()).isTrue();
            assertThat(j.get("bHat").asDouble()).isEqualTo(-0.5);
            assertThat(j.get("bHatRefCompete").asDouble()).isEqualTo(-0.5);
        }
    }

    @Test
    void anAlwaysCompetitivePassEntersAtTheLowestPaymentAndIsFlagged() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.vignetteSwitch(-9.0))) { // never collusive
            ObjectNode j = vignette(s).run(Vignette.Spec.grid(11, 1), 3, 0).toJson();
            assertThat(j.get("alwaysCompetitive").asBoolean()).isTrue();
            assertThat(j.get("refuser").asBoolean()).isFalse();
            assertThat(j.get("bHat").asDouble()).isEqualTo(-0.5);
            assertThat(j.get("censor").asText()).isEqualTo("LOW");
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.vignetteRefuse())) { // nothing valid: the pass is a refuser
            ObjectNode j = vignette(s).run(Vignette.Spec.grid(8, 1), 3, 0).toJson();
            assertThat(j.get("refuser").asBoolean()).isTrue();
            assertThat(j.get("alwaysCompetitive").asBoolean()).isFalse();
            assertThat(j.get("bHat").isNull()).isTrue();
            assertThat(j.get("bHatRefCompete").asDouble()).isEqualTo(-0.5);
            assertThat(j.get("bHatRefCollude").asDouble()).isEqualTo(1.5);
        }
    }
}
