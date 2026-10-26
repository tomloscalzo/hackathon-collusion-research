package io.github.tomloscalzo.collusion.mc;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.core.model.TimeParams;
import io.github.tomloscalzo.collusion.engine.DetectionSpec;
import io.github.tomloscalzo.collusion.engine.Game;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.analysis.Metrics;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoader;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

class ScenarioFilesAndPerfTest {
    @Test
    void everyScenarioNamedInPredictionsResolvesWithAnLlmSeatPlaceholder() {
        for (String name : List.of("unripe-a", "unripe-a-prime", "p5-slope-0.055", "n4-variant", "ripe-game", "tick-case")) {
            GameConfig c = GameConfigLoader.loadResource("scenarios/" + name + ".yaml");
            assertThat(c.scenario().time().maxRounds()).isEqualTo(40);
            AgentSpec seat = c.agents().get(0);
            assertThat(seat.id()).isEqualTo("llm");
            assertThat(seat.category()).isEqualTo(AgentCategory.M);
            assertThat(seat.kind()).isEqualTo(AgentKind.LLM);
        }
        assertThat(ScenarioLoader.loadResource("scenarios/ripe-baseline.yaml").time().maxRounds()).isEqualTo(40);
        assertThat(GameConfigLoader.loadResource("scenarios/unripe-a.yaml").scenario().enforcement().fine()).isEqualTo(5000.0);
        assertThat(GameConfigLoader.loadResource("scenarios/p5-slope-0.055.yaml").scenario().enforcement().screen().slope())
                .isEqualTo(0.055);
        var n4 = GameConfigLoader.loadResource("scenarios/n4-variant.yaml");
        assertThat(n4.agents()).hasSize(4);
        assertThat(n4.agents().get(1).config()).containsEntry("theta", 0.546);
        assertThat(GameConfigLoader.loadResource("scenarios/unripe-a-prime.yaml").agents().get(1).kind())
                .isEqualTo(AgentKind.ALWAYS_COMPETE);
    }

    @Test
    void ripenessGridReproducesBaselineAndSensitivityGoldens() {
        String yaml = "id: t\nbase: scenarios/ripe-baseline.yaml\nparameters:\n  delta: [0.90, 0.95, 0.99]\n";
        RipenessGrid g = RipenessGrid.parse(yaml);
        assertThat(g.size()).isEqualTo(3);
        String[] h = g.header().split(",");
        java.util.List<String> cols = List.of(h);
        String[] r = g.row(1).split(",", -1);
        assertThat(Double.parseDouble(r[cols.indexOf("theta_star")])).isEqualTo(0.546, org.assertj.core.api.Assertions.within(0.001));
        assertThat(Double.parseDouble(r[cols.indexOf("ripeness_E")])).isEqualTo(0.453, org.assertj.core.api.Assertions.within(0.001));
        // T29: overcharge (s(theta*) - s0)/s0 beside CI = theta*
        assertThat(Double.parseDouble(r[cols.indexOf("overcharge")])).isGreaterThan(1.0);
        assertThat(Double.parseDouble(r[cols.indexOf("ci_star")])).isEqualTo(Double.parseDouble(r[cols.indexOf("theta_star")]));
        assertThat(Double.parseDouble(g.row(0).split(",", -1)[cols.indexOf("theta_star")]))
                .isEqualTo(0.605, org.assertj.core.api.Assertions.within(0.001));
        assertThat(Double.parseDouble(g.row(2).split(",", -1)[cols.indexOf("theta_star")]))
                .isEqualTo(0.362, org.assertj.core.api.Assertions.within(0.001));
        assertThat(r).hasSize(cols.size());
        assertThat(RipenessGrid.loadResource("sweeps/ripeness-map.yaml").size()).isEqualTo(10368);
    }

    /** 10,000 short scripted runs (12 rounds, two TriggerK, full replay digest and run-level statistic) on 8 threads. */
    @Test
    @Tag("perf")
    void tenThousandShortRunsOnEightThreads() {
        Scenario s = ScenarioLoader.loadResource("scenarios/ripe-baseline.yaml")
                .withTime(new TimeParams(0.95, 0.0, new Horizon.Known(12), 40));
        Map<String, Object> c = new TreeMap<>();
        c.put("theta", 0.546);
        GameConfig cfg = new GameConfig(s, List.of(new AgentSpec("A", AgentCategory.M, AgentKind.TRIGGER_K, c),
                new AgentSpec("B", AgentCategory.M, AgentKind.TRIGGER_K, c))).withDetection(DetectionSpec.off());
        Game g = new Game(cfg);
        long t0 = System.nanoTime();
        List<Double> out;
        try (MonteCarloRunner p = new MonteCarloRunner(8)) {
            out = p.map(10_000, i -> {
                var run = g.run(1000L + i);
                run.replayDigest();
                return Metrics.runLevel(run, "A").meanOwnCi();
            });
        }
        double secs = (System.nanoTime() - t0) / 1e9;
        System.out.println("perf: 10000 runs in " + secs + " s");
        assertThat(out).hasSize(10_000);
        assertThat(secs).isLessThan(60.0);
    }
}
