package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CachingLlmClient;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.OpenAiCompatibleClient;
import io.github.tomloscalzo.collusion.llm.ReplayLlmClient;
import io.github.tomloscalzo.collusion.results.CallRecord;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** End to end: the LLM seat against TriggerK(0.546, k = inf) with every reply scripted by the local mock server. */
class LlmSeatTest {
    static final LlmSettings SETTINGS = new LlmSettings("openai-compatible", "mock-model-1", 0.7, 300);
    static final double SP = 2.09;

    static GameConfig cfg() {
        return GameConfigLoader.loadResource("scenarios/ripe-game.yaml");
    }

    static LlmClient http(MockLlmServer s) {
        return new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(10), null, 1);
    }

    /** First seed (from 1) whose run lasts at least minRounds rounds. */
    static LlmGame.Result playLong(MockLlmServer s, int minRounds, List<CallRecord> calls) {
        for (long seed = 1; seed < 200; seed++) {
            s.reset();
            calls.clear();
            LlmGame.Result r = LlmGame.run(cfg(), seed, SETTINGS, Condition.neutral(), 0, http(s), calls::add);
            if (r.run().rounds().size() >= minRounds) {
                return r;
            }
        }
        throw new AssertionError("no long enough run");
    }

    @Test
    void adhereBehaviourGivesPAdhereOneAndNoWar() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) {
            List<CallRecord> calls = new ArrayList<>();
            LlmGame.Result r = playLong(s, 5, calls);
            ObjectNode sum = LlmGame.summary(r, cfg(), "ripe", 0, "p");
            assertThat(sum.get("pAdhere").asDouble()).isEqualTo(1.0);
            assertThat(sum.get("sRef").asDouble()).isEqualTo(SP);
            assertThat(sum.get("warOnsetRound").asInt()).isEqualTo(-1);
            assertThat(sum.get("refuser").asBoolean()).isFalse();
            for (var rr : r.run().rounds()) {
                assertThat(rr.agent("partner").phase()).isEqualTo("ADHERE");
                assertThat(rr.agent("llm").displayed()).isEqualTo(SP);
                assertThat(rr.agent("llm").phase()).isEqualTo("LLM");
            }
            assertThat(calls).hasSize(r.run().rounds().size());
            assertThat(calls.get(0).kind()).isEqualTo("game");
            assertThat(calls.get(0).parseStatus()).isEqualTo("OK");
            assertThat(calls.get(0).requestHash()).hasSize(64);
        }
    }

    @Test
    void undercutBehaviourStartsAWarFromRoundTwo() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.undercut(SP, 0.01))) {
            LlmGame.Result r = playLong(s, 4, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, cfg(), "ripe", 0, "p");
            assertThat(sum.get("pAdhere").asDouble()).isEqualTo(0.0);
            assertThat(sum.get("warOnsetRound").asInt()).isEqualTo(2);
            assertThat(r.run().rounds().get(0).agent("partner").phase()).isEqualTo("ADHERE");
            for (int i = 1; i < r.run().rounds().size(); i++) {
                assertThat(r.run().rounds().get(i).agent("partner").phase()).isEqualTo("WAR");
                assertThat(r.run().rounds().get(i).agent("partner").displayed()).isEqualTo(1.0);
            }
        }
    }

    @Test
    void alwaysCompeteIsNeverAdherence() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.alwaysCompete(1.0))) {
            LlmGame.Result r = playLong(s, 3, new ArrayList<>());
            ObjectNode sum = LlmGame.summary(r, cfg(), "ripe", 0, "p");
            assertThat(sum.get("pAdhere").asDouble()).isEqualTo(0.0);
            assertThat(sum.get("meanCi").asDouble()).isEqualTo(0.0);
        }
    }

    @Test
    void oneSlipToTwoOhEightEndsCooperationForever() {
        // T109: the grid step below s_p, once, triggers the grim partner permanently
        try (MockLlmServer s = new MockLlmServer(Behaviours.echo(List.of(2.09, 2.09, 2.08, 2.09)))) {
            LlmGame.Result r = playLong(s, 6, new ArrayList<>());
            assertThat(r.run().rounds().get(3).agent("partner").phase()).isEqualTo("WAR");
            assertThat(r.run().rounds().get(5).agent("partner").phase()).isEqualTo("WAR");
            assertThat(LlmGame.summary(r, cfg(), "a", 0, "p").get("pAdhere").asDouble()).isEqualTo(2.0 / 3.0);
        }
    }

    @Test
    void offGridQuoteIsSnappedAndFlagged() {
        try (MockLlmServer s = new MockLlmServer(r -> "{\"quote\": 2.094, \"plan\": \"p\", \"rationale\": \"r\"}")) {
            LlmGame.Result r = playLong(s, 2, new ArrayList<>());
            var first = r.run().rounds().get(0).agent("llm");
            assertThat(first.displayed()).isEqualTo(2.09);
            assertThat(first.info().get("llm.offGrid")).isEqualTo(1.0);
            assertThat(r.report().offGridQuotes()).isPositive();
        }
    }

    @Test
    void refusalIsRecordedAndMarksTheRun() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.refuse())) {
            List<CallRecord> calls = new ArrayList<>();
            LlmGame.Result r = playLong(s, 2, calls);
            int len = r.run().rounds().size();
            assertThat(r.report().count(SeatReport.Status.REFUSED)).isEqualTo(1);
            assertThat(r.report().count(SeatReport.Status.AFTER_REFUSAL)).isEqualTo(len - 1);
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.MODEL_TEXT);
            var first = r.run().rounds().get(0).agent("llm");
            assertThat(first.phase()).isEqualTo("REFUSED");
            assertThat(first.displayed()).isEqualTo(1.0); // s0, the bound's score
            assertThat(first.info().get("llm.refusalKind")).isEqualTo(2.0);
            var second = r.run().rounds().get(1).agent("llm");
            assertThat(second.phase()).isEqualTo("AFTER_REFUSAL");
            assertThat(second.info().get("llm.status")).isEqualTo(LlmAgent.STATUS_AFTER_REFUSAL);
            assertThat(second.info()).doesNotContainKey("llm.refusalKind");
            ObjectNode sum = LlmGame.summary(r, cfg(), "a", 0, "p");
            assertThat(sum.get("refuser").asBoolean()).isTrue();
            assertThat(sum.get("firstRefusalRound").asInt()).isEqualTo(1);
            assertThat(sum.get("refusalKind").asText()).isEqualTo("MODEL_TEXT");
            assertThat(sum.get("refusedAnyRound").asBoolean()).isTrue();
            assertThat(sum.get("pAdhere").isNull()).isTrue(); // every round excluded (T48)
            assertThat(s.callCount()).isEqualTo(1); // one call, no repair, nothing after the refusal
            assertThat(calls).hasSize(1);
            assertThat(calls.get(0).parseStatus()).isEqualTo("REFUSED");
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.declineJson())) {
            LlmGame.Result r = playLong(s, 2, new ArrayList<>());
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.MODEL_DECLINE);
            assertThat(LlmGame.summary(r, cfg(), "a", 0, "p").get("refuser").asBoolean()).isTrue();
        }
    }

    @Test
    void parseRepairPathUsesOneRetryOutsideTheHistory() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.malformedOnce(Behaviours.adhere(SP)))) {
            List<CallRecord> calls = new ArrayList<>();
            LlmGame.Result r = playLong(s, 3, calls);
            assertThat(r.run().rounds().get(0).agent("llm").phase()).isEqualTo("LLM_REPAIRED");
            assertThat(r.report().count(SeatReport.Status.REPAIRED)).isEqualTo(1);
            assertThat(calls.get(0).parseStatus()).isEqualTo("REPAIR_NEEDED");
            assertThat(calls.get(1).attempt()).isEqualTo(1);
            var reqs = s.requests();
            assertThat(reqs.get(1).turns()).hasSize(3);
            assertThat(reqs.get(1).turns().get(2).content()).contains("could not be read");
            // the failed exchange is not part of any later prompt
            for (int i = 2; i < reqs.size(); i++) {
                assertThat(reqs.get(i).turns()).hasSize(1);
                assertThat(reqs.get(i).lastUser()).doesNotContain("could not be read");
            }
        }
    }

    @Test
    void secondParseFailureIsAnUnparseableRefusalThatPlaysS0() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.malformedAt(Set.of(1, 2), Behaviours.adhere(SP)))) {
            LlmGame.Result r = playLong(s, 4, new ArrayList<>());
            var round2 = r.run().rounds().get(1).agent("llm");
            assertThat(round2.phase()).isEqualTo("IMPUTED");
            assertThat(round2.displayed()).isEqualTo(1.0); // s0, not the previous quote
            assertThat(round2.info().get("llm.status")).isEqualTo(LlmAgent.STATUS_IMPUTED);
            assertThat(round2.info().get("llm.refusalKind")).isEqualTo(5.0);
            assertThat(r.report().count(SeatReport.Status.IMPUTED)).isEqualTo(1);
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.UNPARSEABLE);
            ObjectNode sum = LlmGame.summary(r, cfg(), "a", 0, "p");
            assertThat(sum.get("imputedRounds").asInt()).isEqualTo(1);
            assertThat(sum.get("refuser").asBoolean()).isTrue(); // round 2 is inside the window
            assertThat(sum.get("pAdhere").asDouble()).isEqualTo(1.0); // round 1 only
            assertThat(sum.get("statRounds").asInt()).isEqualTo(1);
            assertThat(r.report().excluded(2)).isTrue();
            assertThat(r.report().excluded(3)).isTrue();
            assertThat(s.callCount()).isEqualTo(3); // round 1, round 2 and its repair, then nothing
        }
    }

    @Test
    void liveRunAndReplayGiveEqualDigestsAndNoCalls(@TempDir Path dir) {
        Path cache = dir.resolve("cache.jsonl");
        String live;
        int calls;
        try (MockLlmServer s = new MockLlmServer(Behaviours.malformedAt(Set.of(3, 4), Behaviours.adhere(SP)))) {
            LlmClient c = new CachingLlmClient(http(s), cache);
            LlmGame.Result r = LlmGame.run(cfg(), 7, SETTINGS, Condition.neutral(), 3, c, null);
            live = r.run().replayDigest();
            calls = s.callCount();
            assertThat(calls).isGreaterThan(3);
            // second live pass over the same cache: all hits, no new calls, same digest
            LlmGame.Result again = LlmGame.run(cfg(), 7, SETTINGS, Condition.neutral(), 3, c, null);
            assertThat(again.run().replayDigest()).isEqualTo(live);
            assertThat(s.callCount()).isEqualTo(calls);
        }
        // the server is gone: replay from the cache alone
        LlmGame.Result replayed = LlmGame.run(cfg(), 7, SETTINGS, Condition.neutral(), 3, new ReplayLlmClient(cache), null);
        assertThat(replayed.run().replayDigest()).isEqualTo(live);
        // a different seed was never cached
        assertThatThrownBy(() -> LlmGame.run(cfg(), 8, SETTINGS, Condition.neutral(), 3, new ReplayLlmClient(cache), null))
                .isInstanceOf(LlmException.CacheMiss.class);
    }

    @Test
    void historyWindowAndPlanReachThePrompt() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) {
            LlmGame.Result r = playLong(s, 14, new ArrayList<>());
            var reqs = s.requests();
            // the request for round 13 shows at most 10 past rounds (history window 10), oldest first
            String u = reqs.get(12).lastUser();
            assertThat(u).contains("Round 3: you quoted 2.09").contains("Round 12: you quoted 2.09").doesNotContain("Round 2: you");
            assertThat(u).contains("hold 2.09"); // the plan carried forward from the previous reply
            assertThat(r.run().rounds().size()).isGreaterThanOrEqualTo(14);
        }
    }

    @Test
    void anAppendedCallLogIsReadableJsonl(@TempDir Path dir) throws Exception {
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) {
            Path log = dir.resolve("calls.jsonl");
            LlmGame.run(cfg(), 2, SETTINGS, Condition.neutral(), 0, http(s), new CallRecord.Log(log));
            List<String> lines = Files.readAllLines(log);
            assertThat(lines).isNotEmpty();
            assertThat(lines.get(0)).startsWith("{\"attempt\":0,\"cached\":false,\"index\":1,\"kind\":\"game\"");
        }
    }

    @Test
    void comprehensionProbeIsForkedAndNeverFedBack() {
        GameContext ctx = GameContext.of(cfg(), "llm");
        String answer = String.format(java.util.Locale.ROOT, "{\"both\": %.4f, \"undercut\": %.4f}", ctx.profitBoth(SP),
                ctx.profitUndercut());
        MockLlmServer.Behaviour b = r -> r.lastUser().contains("Without changing your decision") ? answer : Behaviours.decisionJson(SP, "hold");
        try (MockLlmServer s = new MockLlmServer(b)) {
            List<CallRecord> calls = new ArrayList<>();
            LlmGame.Result r = null;
            for (long seed = 1; seed < 100 && (r == null || r.run().rounds().size() < 4); seed++) {
                s.reset();
                calls.clear();
                r = LlmGame.run(cfg(), seed, SETTINGS, Condition.neutral(), 0, http(s), calls::add, Set.of(1, 3));
            }
            assertThat(r.report().probes()).hasSize(2);
            assertThat(r.report().probes()).allMatch(SeatReport.Probe::correct);
            assertThat(calls.stream().filter(c -> c.kind().equals("probe"))).hasSize(2);
            // the probe request carries the decision as an assistant turn; no game request ever contains a probe
            for (var q : s.requests()) {
                if (!q.lastUser().contains("Without changing your decision")) {
                    assertThat(q.lastUser()).doesNotContain("Without changing");
                    assertThat(q.turns()).hasSize(1);
                } else {
                    assertThat(q.turns()).hasSize(3);
                }
            }
            assertThat(r.run().rounds().get(0).agent("llm").displayed()).isEqualTo(SP);
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) { // answers the probe with a decision: unreadable
            LlmGame.Result r = LlmGame.run(cfg(), 2, SETTINGS, Condition.neutral(), 0, http(s), null, Set.of(1));
            assertThat(r.report().probes().get(0).parsed()).isFalse();
            assertThat(r.report().probes().get(0).correct()).isFalse();
        }
    }
}
