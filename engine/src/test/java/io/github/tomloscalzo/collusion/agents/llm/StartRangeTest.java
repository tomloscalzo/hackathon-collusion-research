package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.CallRecord;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/**
 * Unit U17, the 5-tick start control arm: in round 1 only a quote must lie in [s0, s0 + start_ticks ticks]; a quote outside
 * is an invalid reply (one repair, then imputed to s0, logged); round 2 on is free; off (the default) changes nothing.
 */
class StartRangeTest {
    static final double S0 = 1.0;

    static String reply(double q) {
        return Behaviours.decisionJson(q, "x");
    }

    /** Round 1 gets first (attempt 0) and then second (attempt 1); every later round quotes later. */
    static LlmGame.Result play(StartRange range, String first, String second, double later, List<CallRecord> calls,
                               MockLlmServer[] out) {
        return play(range, first, second, later, calls, out, LlmSeatTest.SETTINGS, null);
    }

    static LlmGame.Result play(StartRange range, String first, String second, double later, List<CallRecord> calls,
                               MockLlmServer[] out, LlmSettings settings, io.github.tomloscalzo.collusion.trial.EventsWriter ev) {
        MockLlmServer s = new MockLlmServer(Behaviours.replies(r -> RefusalHandlingTest.round(r) == 1
                ? Reply.text(RefusalHandlingTest.attempt(r) == 0 ? first : second) : Reply.text(reply(later))));
        out[0] = s;
        LlmGame.Extras ex = LlmGame.Extras.NONE.withStartRange(range);
        return LlmGame.run(RefusalHandlingTest.cfg(), 3, settings, Condition.neutral(), 0, LlmSeatTest.http(s),
                calls::add, Set.of(), true, ev, false, ex);
    }

    static double quote(LlmGame.Result r, int round) {
        return r.run().rounds().get(round - 1).agent("llm").displayed();
    }

    static String phase(LlmGame.Result r, int round) {
        return r.run().rounds().get(round - 1).agent("llm").phase();
    }

    @Test
    void offByDefaultARound1QuoteFarAboveFiveTicksIsPlayed() {
        List<CallRecord> calls = new ArrayList<>();
        MockLlmServer[] s = new MockLlmServer[1];
        LlmGame.Result r = play(null, reply(1.80), reply(1.80), 1.80, calls, s);
        try (MockLlmServer x = s[0]) {
            assertThat(quote(r, 1)).isEqualTo(1.80);
            assertThat(phase(r, 1)).isEqualTo("LLM");
            assertThat(calls.get(0).parseStatus()).isEqualTo("OK");
            assertThat(x.requests()).noneMatch(q -> RefusalHandlingTest.attempt(q) == 1);
        }
    }

    @Test
    void boundsAreFloorAndFiveTicksAndComeFromTheOptionValue() {
        StartRange five = new StartRange(5);
        var m = RefusalHandlingTest.cfg().scenario().market();
        assertThat(five.lo(m)).isEqualTo(S0);
        assertThat(five.hi(m)).isEqualTo(1.05, org.assertj.core.data.Offset.offset(1e-12));
        assertThat(five.allows(m, 1.00)).isTrue();
        assertThat(five.allows(m, 1.05)).isTrue();
        assertThat(five.allows(m, 1.0501)).isFalse();
        assertThat(five.allows(m, 0.99)).isFalse();
        assertThat(new StartRange(3).allows(m, 1.04)).isFalse();
        assertThat(new StartRange(3).allows(m, 1.03)).isTrue();
        assertThat(StartRange.fromOptions(new ObjectMapper().createObjectNode())).isNull();
        assertThat(StartRange.fromOptions(new ObjectMapper().createObjectNode().put("start_ticks", 5))).isEqualTo(five);
        assertThatThrownBy(() -> StartRange.fromOptions(new ObjectMapper().createObjectNode().put("start_ticks", 0)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StartRange.fromOptions(new ObjectMapper().createObjectNode().put("start_ticks", "5")))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void anInRangeRound1QuoteAtTheTopEdgeIsPlayedWithNoRepair() {
        List<CallRecord> calls = new ArrayList<>();
        MockLlmServer[] s = new MockLlmServer[1];
        LlmGame.Result r = play(new StartRange(5), reply(1.05), reply(1.05), 1.80, calls, s);
        try (MockLlmServer x = s[0]) {
            assertThat(quote(r, 1)).isEqualTo(1.05);
            assertThat(phase(r, 1)).isEqualTo("LLM");
            assertThat(calls.get(0).parseStatus()).isEqualTo("OK");
        }
    }

    @Test
    void anOutOfRangeRound1QuoteIsRepairedOnceAndAnInRangeRepairIsPlayed() {
        List<CallRecord> calls = new ArrayList<>();
        MockLlmServer[] s = new MockLlmServer[1];
        LlmGame.Result r = play(new StartRange(5), reply(1.80), reply(1.03), 1.80, calls, s);
        try (MockLlmServer x = s[0]) {
            assertThat(quote(r, 1)).isEqualTo(1.03);
            assertThat(phase(r, 1)).isEqualTo("LLM_REPAIRED");
            assertThat(calls.get(0).parseStatus()).isEqualTo("REPAIR_NEEDED");
            assertThat(calls.get(1).parseStatus()).isEqualTo("OK");
            assertThat(x.requests().stream().filter(q -> RefusalHandlingTest.round(q) == 1)).hasSize(2);
        }
    }

    @Test
    void aRound1QuoteOutOfRangeTwiceIsImputedToS0AndRound2IsFree() {
        List<CallRecord> calls = new ArrayList<>();
        MockLlmServer[] s = new MockLlmServer[1];
        LlmGame.Result r = play(new StartRange(5), reply(1.80), reply(1.06), 1.80, calls, s);
        try (MockLlmServer x = s[0]) {
            assertThat(quote(r, 1)).isEqualTo(S0);
            assertThat(phase(r, 1)).isEqualTo("IMPUTED");
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.UNPARSEABLE);
            assertThat(calls.get(0).parseStatus()).isEqualTo("REPAIR_NEEDED");
            assertThat(calls.get(1).parseStatus()).isEqualTo("PARSE_FAIL");
            assertThat(x.requests().stream().filter(q -> RefusalHandlingTest.round(q) == 1)).hasSize(2);
            assertThat(quote(r, 2)).isEqualTo(1.80); // free from round 2; the seat is still called after the imputed round
            assertThat(phase(r, 2)).isEqualTo("LLM");
        }
    }

    static final LlmSettings THINKING = new LlmSettings("openai-compatible", "mock-model-1", 0.7, 300, true, null, null);

    @Test
    void withThinkingOnAClosedThinkBlockWithAnOutOfRangeQuoteIsImputedAsTruncatedNeverRepaired() {
        List<CallRecord> calls = new ArrayList<>();
        MockLlmServer[] s = new MockLlmServer[1];
        LlmGame.Result r = play(new StartRange(5), "<think>hmm</think>" + reply(1.80), reply(1.03), 1.80, calls, s, THINKING, null);
        try (MockLlmServer x = s[0]) {
            assertThat(phase(r, 1)).isEqualTo("IMPUTED");
            assertThat(r.report().refusalKind()).isEqualTo(SeatReport.RefusalKind.TRUNCATED);
            assertThat(x.requests().stream().filter(q -> RefusalHandlingTest.round(q) == 1)).hasSize(1); // no repair turn
        }
    }

    @Test
    void withThinkingOnAPlainOutOfRangeQuoteIsRepairedAndTheEventMarksTheFirstReply(@org.junit.jupiter.api.io.TempDir
            java.nio.file.Path dir) throws Exception {
        List<CallRecord> calls = new ArrayList<>();
        MockLlmServer[] s = new MockLlmServer[1];
        var ev = new io.github.tomloscalzo.collusion.trial.EventsWriter(dir.resolve("events.jsonl"));
        LlmGame.Result r = play(new StartRange(5), reply(1.80), reply(1.02), 1.80, calls, s, THINKING, ev);
        try (MockLlmServer x = s[0]) {
            assertThat(quote(r, 1)).isEqualTo(1.02);
            assertThat(phase(r, 1)).isEqualTo("LLM_REPAIRED");
        }
        List<String> lines = java.nio.file.Files.readAllLines(dir.resolve("events.jsonl"));
        String q1 = lines.stream().filter(l -> l.contains("\"kind\":\"quote\"") && l.contains("\"round\":1,")).findFirst().orElseThrow();
        assertThat(q1).contains("\"start_range_violation\":\"first_reply\"");
    }

    @Test
    void onlyTheSeatWhoseRound1QuoteIsOutOfRangeIsImputed() {
        var cfg = io.github.tomloscalzo.collusion.scenario.GameConfigLoader.loadResource("scenarios/slice-m-p3.yaml");
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(r -> Reply.text(reply(
                RefusalHandlingTest.round(r) == 1 ? (r.user().contains("|llm1|") ? 1.80 : 1.03) : 1.50))))) {
            LlmGame.Result r = LlmGame.run(cfg, 3, LlmSeatTest.SETTINGS, Condition.neutral(), 0, LlmSeatTest.http(s), null,
                    Set.of(), true, null, false, LlmGame.Extras.NONE.withStartRange(new StartRange(5)));
            var r1 = r.run().rounds().get(0);
            assertThat(r1.agent("llm1").phase()).isEqualTo("IMPUTED");
            assertThat(r1.agent("llm1").displayed()).isEqualTo(S0);
            assertThat(r1.agent("llm2").phase()).isEqualTo("LLM");
            assertThat(r1.agent("llm2").displayed()).isEqualTo(1.03);
            assertThat(r.run().rounds().get(1).agent("llm1").displayed()).isEqualTo(1.50); // free from round 2
        }
    }

    @Test
    void aClampSkippedRound1IsImputedWithOrWithoutTheRangeAndNothingIsSent() {
        for (StartRange range : new StartRange[] {null, new StartRange(5)}) {
            try (MockLlmServer s = new MockLlmServer(Behaviours.replies(r -> Reply.text(reply(1.80))))) {
                LlmGame.Result r = LlmGame.run(RefusalHandlingTest.cfg(), 3, LlmSeatTest.SETTINGS, Condition.neutral(), 0,
                        LlmSeatTest.http(s), null, Set.of(), true, null, false, LlmGame.Extras.NONE.withStartRange(range)
                                .withClamp(new ContextClamp(1000, 100, 200, 3.0, "t", "a")));
                assertThat(phase(r, 1)).isEqualTo("IMPUTED");
                assertThat(s.callCount()).isZero();
            }
        }
    }

    @Test
    void aQuoteBelowTheFloorIsAlsoOutOfRange() {
        List<CallRecord> calls = new ArrayList<>();
        MockLlmServer[] s = new MockLlmServer[1];
        LlmGame.Result r = play(new StartRange(5), reply(0.90), reply(0.90), 1.20, calls, s);
        try (MockLlmServer x = s[0]) {
            assertThat(phase(r, 1)).isEqualTo("IMPUTED");
        }
    }
}
