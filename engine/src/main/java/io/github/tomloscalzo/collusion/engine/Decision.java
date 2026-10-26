package io.github.tomloscalzo.collusion.engine;

import java.util.List;

/**
 * An agent decision with its audit trail. signalEvaluated: the agent looked for a deviation this round; signalSeen: it
 * saw one. phase is a free label (ADHERE, WAR, ...). punishing marks a punishment phase for the tip rule.
 * info holds numeric audit values (e.g. the logit agent EVs). excludeFromContestable lists agents the engine must route contestable flow away from this round (penance).
 */
public record Decision(Action.Quote action, boolean signalEvaluated, boolean signalSeen, String phase,
                       boolean punishing, List<String> excludeFromContestable,
                       java.util.Map<String, Double> info) {
    public Decision {
        info = java.util.Collections.unmodifiableMap(new java.util.TreeMap<>(info));
        excludeFromContestable = List.copyOf(excludeFromContestable);
    }

    public Decision(Action.Quote action, boolean signalEvaluated, boolean signalSeen, String phase,
                    boolean punishing, List<String> excludeFromContestable) {
        this(action, signalEvaluated, signalSeen, phase, punishing, excludeFromContestable, java.util.Map.of());
    }

    public static Decision simple(Action.Quote action, String phase) {
        return new Decision(action, false, false, phase, false, List.of());
    }
}
