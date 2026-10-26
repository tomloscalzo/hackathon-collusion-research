package io.github.tomloscalzo.collusion.engine;

import java.util.List;
import java.util.Map;

/**
 * What an agent sees when choosing a quote for the given (1-based) round. history holds up to the policy window of
 * past rounds, oldest first. choiceDraw is one uniform from the agent's own stream (always drawn).
 */
public record Observation(int round, String selfId, List<String> agentIds, List<PastRound> history, double choiceDraw) {
    public Observation {
        agentIds = List.copyOf(agentIds);
        history = List.copyOf(history);
    }

    public PastRound last() {
        return history.isEmpty() ? null : history.get(history.size() - 1);
    }

    /**
     * One past round as seen by this agent. rivalQuotes and insideQuote are empty/null when the quotes were not
     * observed that round (o &lt; 1). ownVolume (noisy) and ownFillPrice are null when the policy hides them or there
     * was no fill. insideQuote is the displayed inside quote including the agent itself.
     */
    public record PastRound(int round, double ownQuote, Double ownHiddenFill, boolean quotesVisible,
                            Map<String, Double> rivalQuotes, Double insideQuote, Double ownVolume,
                            Double ownFillPrice, boolean ownExcluded) {
        public PastRound {
            rivalQuotes = Map.copyOf(rivalQuotes);
        }
    }
}
