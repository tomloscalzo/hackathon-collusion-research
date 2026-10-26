package io.github.tomloscalzo.collusion.results;

import io.github.tomloscalzo.collusion.engine.RunStatus;
import java.util.List;

/**
 * One round. insideQuote is the displayed inside quote (excluded agents ignored), insideCi its unclipped collusion
 * index. endedWith is the run status when the run ended after this round, else null.
 */
public record RoundRecord(int round, List<AgentRound> agents, double insideQuote, double insideCi,
                          DetectionRound detection, RunStatus endedWith) {
    public RoundRecord {
        agents = List.copyOf(agents);
    }

    public AgentRound agent(String id) {
        for (AgentRound a : agents) {
            if (a.id().equals(id)) {
                return a;
            }
        }
        throw new IllegalArgumentException("No agent " + id);
    }

    /**
     * Per-agent data. noise is the standard-normal demand draw, observedVolume = volume + demandNoiseSd * noise.
     * sawPriorQuotes: whether the previous round's quotes were visible to this agent (draw from signal:id).
     */
    public record AgentRound(String id, double displayed, Double hiddenFill, double ownCi, double volume,
                             double noise, double observedVolume, Double fillPrice, double payoff, double fine,
                             boolean signalEvaluated, boolean signalSeen, boolean sawPriorQuotes, String phase,
                             boolean excluded, java.util.Map<String, Double> info) {}

    public record DetectionRound(double pTrigger, double pEvidence, boolean tipActive, boolean triggered,
                                 boolean evidence) {}
}
