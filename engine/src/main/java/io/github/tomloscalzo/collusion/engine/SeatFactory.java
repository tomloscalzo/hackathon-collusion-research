package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.agents.Agent;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;

/** Builds the agent of a placeholder (kind LLM) seat for one run; used by Game when given (M4). */
@FunctionalInterface
public interface SeatFactory {
    Agent create(AgentSpec spec, GameConfig cfg, SeedPolicy seeds, long runSeed);
}
