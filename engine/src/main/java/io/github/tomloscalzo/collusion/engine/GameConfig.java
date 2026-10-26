package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** A scenario plus the engine sections: observation, history, detection and the roster (market.n agents). */
public record GameConfig(Scenario scenario, ObservationPolicy observation, HistoryPolicy history,
                         DetectionSpec detection, List<AgentSpec> agents) {
    public GameConfig {
        agents = List.copyOf(agents);
        if (observation.demandNoiseSd() < 0 || observation.o() < 0 || observation.o() > 1) {
            throw new IllegalArgumentException("observation: demandNoiseSd >= 0 and o in [0,1] required");
        }
        if (agents.size() != scenario.market().n()) {
            throw new IllegalArgumentException("roster size " + agents.size() + " != market.n " + scenario.market().n());
        }
        Set<String> ids = new HashSet<>();
        for (AgentSpec a : agents) {
            if (a.id() == null || a.id().isBlank() || !ids.add(a.id())) {
                throw new IllegalArgumentException("agent ids must be non-empty and unique: " + a.id());
            }
        }
    }

    public GameConfig(Scenario scenario, List<AgentSpec> agents) {
        this(scenario, ObservationPolicy.defaults(), HistoryPolicy.defaults(), DetectionSpec.scenario(), agents);
    }

    public GameConfig withScenario(Scenario v) { return new GameConfig(v, observation, history, detection, agents); }
    public GameConfig withObservation(ObservationPolicy v) { return new GameConfig(scenario, v, history, detection, agents); }
    public GameConfig withDetection(DetectionSpec v) { return new GameConfig(scenario, observation, history, v, agents); }
    public GameConfig withAgents(List<AgentSpec> v) { return new GameConfig(scenario, observation, history, detection, v); }
}
