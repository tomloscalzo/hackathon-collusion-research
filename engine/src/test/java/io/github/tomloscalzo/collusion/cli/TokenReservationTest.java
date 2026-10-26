package io.github.tomloscalzo.collusion.cli;

import static io.github.tomloscalzo.collusion.cli.LlmCliTest.o;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.agents.llm.LlmSettings;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * C12a.5 (interface proposal v5, C6; INTERFACES.md F17): the run reservation can use --max-tokens as the per-call output
 * bound (--reserve-out-tokens max, or a number) and a larger factor (--reserve-factor); absent, it is 1.25 x the estimate
 * with 120 output tokens per game call, as before.
 */
class TokenReservationTest {
    /** A verbose reply: about 12,000 completion tokens (the mock counts characters / 4), so 9 calls of 2 short games overrun 1.25 x the 120-token estimate of 2 x 40 rounds. */
    static final String LONG = Behaviours.decisionJson(2.09, "hold " + "x".repeat(48000));

    static Map<String, String> run(String base, Path out, String... extra) {
        Map<String, String> m = o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", base, "model", "mock-model-1",
                "seed", "3", "runs", "2", "out", out.toString(), "max-tokens", "16000");
        m.putAll(o(extra));
        return m;
    }

    @Test
    void verboseRepliesAbortTheDefaultReservationAndPassWithMaxTokensAsTheBound(@TempDir Path dir) throws Exception {
        try (MockLlmServer s = new MockLlmServer(q -> LONG)) {
            // F17 as before: the 120-token assumption is exceeded on localhost
            assertThatThrownBy(() -> LlmCommands.run(run(s.baseUrl(), dir.resolve("a.jsonl"))))
                    .isInstanceOf(LlmException.BudgetExceeded.class);
            Path out = dir.resolve("b.jsonl");
            LlmCommands.run(run(s.baseUrl(), out, "reserve-out-tokens", "max"));
            assertThat(Files.readAllLines(out)).hasSize(2);
            Path out2 = dir.resolve("c.jsonl");
            LlmCommands.run(run(s.baseUrl(), out2, "reserve-out-tokens", "1000"));
            assertThat(Files.readAllLines(out2)).hasSize(2);
            Path out3 = dir.resolve("d.jsonl");
            LlmCommands.run(run(s.baseUrl(), out3, "reserve-factor", "4"));
            assertThat(Files.readAllLines(out3)).hasSize(2);
        }
    }

    @Test
    void theReservationIsTodaysWithoutTheOptionsAndGrowsWithThem() {
        LlmSettings s = new LlmSettings("openai-compatible", "m", 0.7, 2560);
        assertThat(LlmCommands.reserveOut(o(), s, 120)).isEqualTo(120);
        assertThat(LlmCommands.reserveOut(o(), s, 60)).isEqualTo(60);
        assertThat(LlmCommands.reserveOut(o("reserve-out-tokens", "max"), s, 120)).isEqualTo(2560);
        assertThat(LlmCommands.reserveOut(o("reserve-out-tokens", "700"), s, 120)).isEqualTo(700);
        assertThat(LlmCommands.reserveFactor(o())).isEqualTo(1.25);
        assertThat(LlmCommands.reservation(o(), 1000)).isEqualTo(1250);
        assertThat(LlmCommands.reservation(o("reserve-factor", "2"), 1000)).isEqualTo(2000);
        assertThatThrownBy(() -> LlmCommands.reserveOut(o("reserve-out-tokens", "0"), s, 120))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--reserve-out-tokens");
        assertThatThrownBy(() -> LlmCommands.reserveOut(o("reserve-out-tokens", "lots"), s, 120))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--reserve-out-tokens");
        assertThatThrownBy(() -> LlmCommands.reserveFactor(o("reserve-factor", "0.9")))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--reserve-factor");
    }

    @Test
    void theEstimateIsTodaysWithoutTheOptionEvenWithProbesAndAWorstCaseWithIt() {
        var cfg = LlmCommands.loadConfig("scenarios/ripe-game.yaml");
        var cond = io.github.tomloscalzo.collusion.agents.llm.Condition.parse(null);
        LlmSettings s = new LlmSettings("openai-compatible", "m", 0.7, 2560);
        int rounds = cfg.scenario().time().maxRounds();
        long today = io.github.tomloscalzo.collusion.agents.llm.CostEstimator.game(cfg, cond, 0, 3, rounds, 120, 0.02).totalTokens();
        assertThat(LlmCommands.gameEstimate(o(), cfg, s, cond, 0, 3)).isEqualTo(today);
        assertThat(LlmCommands.gameEstimate(o("probe-rounds", "1,10"), cfg, s, cond, 0, 3)).isEqualTo(today);
        // with the bound: two calls per round at prompt + bound, the repair prompt quoting a reply of the bound, probes
        var both = io.github.tomloscalzo.collusion.agents.llm.CostEstimator.game(cfg, cond, 0, 3, rounds, 2560, 1.0);
        long worst = both.totalTokens() + 3L * rounds * 2560 + 2L * 3 * (Math.round(both.avgTokensInPerCall()) + 2 * 2560);
        assertThat(LlmCommands.gameEstimate(o("reserve-out-tokens", "max", "probe-rounds", "1,10"), cfg, s, cond, 0, 3))
                .isEqualTo(worst);
        // a full-length run of one seat at the bound, every round repaired, fits: 2 calls x (prompt + bound) + quoted reply
        long perRunWorst = rounds * (2L * ((long) Math.floor(both.avgTokensInPerCall()) + 2560) + 2560);
        assertThat(LlmCommands.gameEstimate(o("reserve-out-tokens", "max"), cfg, s, cond, 0, 1)).isGreaterThanOrEqualTo(perRunWorst);
        // vignette: today without the option, every row repaired with it
        long vToday = io.github.tomloscalzo.collusion.agents.llm.CostEstimator.vignette(cfg, cond, 0, 11, 2, 1, 60, 0.02).totalTokens();
        assertThat(LlmCommands.vignetteEstimate(o(), cfg, s, cond, 0, 11, 2, 1)).isEqualTo(vToday);
        assertThat(LlmCommands.vignetteEstimate(o("reserve-out-tokens", "max"), cfg, s, cond, 0, 11, 2, 1)).isEqualTo(
                io.github.tomloscalzo.collusion.agents.llm.CostEstimator.vignette(cfg, cond, 0, 11, 2, 1, 2560, 1.0).totalTokens()
                        + 22L * 2560);
    }

    @Test
    void everyLlmSeatIsCountedWithTheOption() {
        var cfg = LlmCommands.loadConfig("scenarios/ripe-game.yaml");
        assertThat(LlmCommands.llmSeats(cfg)).isEqualTo(1);
        var cond = io.github.tomloscalzo.collusion.agents.llm.Condition.parse(null);
        LlmSettings s = new LlmSettings("openai-compatible", "m", 0.7, 400);
        java.util.List<io.github.tomloscalzo.collusion.core.model.AgentSpec> two = new java.util.ArrayList<>();
        for (var a : cfg.agents()) {
            two.add(new io.github.tomloscalzo.collusion.core.model.AgentSpec(a.id(), a.category(),
                    io.github.tomloscalzo.collusion.core.model.AgentKind.LLM, a.config()));
        }
        var cfg2 = cfg.withAgents(two);
        assertThat(LlmCommands.llmSeats(cfg2)).isEqualTo(cfg.agents().size());
        assertThat(LlmCommands.gameEstimate(o("reserve-out-tokens", "max"), cfg2, s, cond, 0, 1))
                .isEqualTo((io.github.tomloscalzo.collusion.agents.llm.CostEstimator.game(cfg2, cond, 0, 1,
                        cfg.scenario().time().maxRounds(), 400, 1.0).totalTokens() + cfg.scenario().time().maxRounds() * 400L)
                        * cfg.agents().size());
        assertThatThrownBy(() -> LlmCommands.reserveFactor(o("reserve-factor", "big")))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--reserve-factor");
    }

    @Test
    void probeCallsAreCountedWhenTheBoundIsGiven() {
        assertThat(LlmCommands.probeCallsPerRun(o())).isZero();
        assertThat(LlmCommands.probeCallsPerRun(o("probe-rounds", "1,10,defect+1"))).isEqualTo(3);
        assertThat(LlmCommands.probeCallsPerRun(o("probe-rounds", " "))).isZero();
    }
}
