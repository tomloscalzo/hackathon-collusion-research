package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** C3.3: every LLM seat's own SeatReport is kept (Finding F6). */
class SeatReportsTest {
    static final LlmSettings SETTINGS = new LlmSettings("openai-compatible", "mock-model-1", 0.7, 300);

    static GameConfig load(String name) {
        return GameConfigLoader.loadResource("scenarios/" + name + ".yaml");
    }

    /** Every seat quotes 2.09, except that refuser declines (quote null) in round 2. */
    static LlmClient client(String refuser) {
        return r -> {
            boolean decline = r.drawKey().contains("|" + refuser + "|r2|");
            String text = decline ? "{\"quote\": null, \"plan\": \"\", \"rationale\": \"I decline.\"}"
                    : "{\"quote\": 2.09, \"plan\": \"hold\", \"rationale\": \"r\"}";
            return new LlmResponse(text, 10, 7, 0L, false, CanonicalRequest.sha256(r), "stop");
        };
    }

    static long longSeed(GameConfig cfg, int minRounds) {
        for (long seed = 1; seed < 300; seed++) {
            if (LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, client("none"), null).run().rounds().size()
                    >= minRounds) {
                return seed;
            }
        }
        throw new AssertionError("no long enough run");
    }

    @Test
    void everyLlmSeatKeepsItsOwnReportUnderItsOwnId() {
        GameConfig cfg = load("n3-group");
        long seed = longSeed(cfg, 4);
        LlmGame.Result r = LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, client("llm2"), null, Set.of(), true);
        int rounds = r.run().rounds().size();
        assertThat(r.reports()).containsOnlyKeys("llm1", "llm2", "llm3");
        assertThat(List.copyOf(r.reports().keySet())).containsExactly("llm1", "llm2", "llm3"); // roster order
        assertThat(r.reports().get("llm1")).isNotSameAs(r.reports().get("llm2")).isNotSameAs(r.reports().get("llm3"));
        for (String s : List.of("llm1", "llm3")) {
            SeatReport rep = r.report(s);
            assertThat(rep.refusedAnyRound()).as(s).isFalse();
            assertThat(rep.rounds()).hasSize(rounds).containsOnly(SeatReport.Status.OK);
            assertThat(rep.calls()).isEqualTo(rounds);
            assertThat(rep.tokensOut()).isEqualTo(7L * rounds);
        }
        SeatReport two = r.report("llm2");
        assertThat(two.firstRefusalRound()).isEqualTo(2);
        assertThat(two.refusalKind()).isEqualTo(SeatReport.RefusalKind.MODEL_DECLINE);
        assertThat(two.rounds()).hasSize(rounds);
        // the bound seat is the first LLM seat, and report() is its own report
        assertThat(r.seatId()).isEqualTo("llm1");
        assertThat(r.report()).isSameAs(r.reports().get("llm1"));
        assertThatThrownBy(() -> r.report("nobody")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> r.reports().put("x", new SeatReport())).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void scriptedSeatsHaveNoReport() {
        GameConfig cfg = load("n3-cheater");
        LlmGame.Result r = LlmGame.run(cfg, longSeed(cfg, 2), SETTINGS, Condition.neutral(), 0, client("none"), null,
                Set.of(), true);
        assertThat(r.reports()).containsOnlyKeys("llm1", "llm2");
    }

    @Test
    void theReportUnderTheFirstSeatsIdIsTheFirstSeatsOwnEvenWithTheSwitchOff() {
        GameConfig cfg = load("n3-group");
        long seed = longSeed(cfg, 4);
        // the last LLM seat refuses: before C3.3 its report was returned under llm1's id (F6)
        LlmGame.Result r = LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, client("llm3"), null);
        assertThat(r.report().refusedAnyRound()).isFalse();
        assertThat(r.report()).isSameAs(r.reports().get("llm1"));
        assertThat(r.report("llm3").firstRefusalRound()).isEqualTo(2);
    }

    @Test
    void oneSeatGamesReportExactlyThatSeat() {
        GameConfig cfg = load("ripe-game");
        for (boolean multi : new boolean[] {false, true}) {
            LlmGame.Result r = LlmGame.run(cfg, 3, SETTINGS, Condition.neutral(), 0, client("llm"), null, Set.of(), multi);
            assertThat(r.reports()).containsOnlyKeys("llm");
            assertThat(r.report()).isSameAs(r.reports().get("llm"));
            assertThat(r.partnerId()).isEqualTo("partner");
        }
    }
}
