package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.core.model.TimeParams;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoader;
import java.util.List;
import java.util.Map;

/** Test fixtures: the ripe baseline with a known horizon (delta0 0.95), detection off, quoteIncrement 0.01. */
final class Fx {
    private Fx() {}

    static Scenario base() {
        return ScenarioLoader.loadResource("scenarios/ripe-baseline.yaml");
    }

    static Scenario known(int rounds) {
        Scenario s = base();
        return s.withTime(new TimeParams(0.95, 0.0, new Horizon.Known(rounds), 80));
    }

    static AgentSpec spec(String id, AgentKind k, Object... kv) {
        java.util.TreeMap<String, Object> c = new java.util.TreeMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            c.put((String) kv[i], kv[i + 1]);
        }
        return new AgentSpec(id, AgentCategory.M, k, c);
    }

    static GameConfig cfg(Scenario s, AgentSpec... a) {
        return new GameConfig(s, List.of(a)).withDetection(DetectionSpec.off());
    }

    static double piC(Scenario s, double theta) {
        return PayoffFunctions.piC(s.market(), theta);
    }

    static double s(Scenario s, double theta) {
        return PayoffFunctions.margin(s.market(), theta);
    }

    static Map<String, Object> none() {
        return Map.of();
    }
}
