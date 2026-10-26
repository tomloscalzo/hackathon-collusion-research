package io.github.tomloscalzo.collusion.results;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.engine.RunStatus;
import java.util.List;

/**
 * One finished run. terminalValue is the per-member value after the last round, undiscounted (T30): piPost/(1-delta)
 * for TRIGGER_ONLY, piNash/(1-delta) for EVIDENCE (the fine is in the last round), 0 otherwise. signal* counts give the
 * emergent false-alarm rate (T5); dBarUAccumulated is 0 because the engine has no communication channels yet (T4).
 */
public record RunRecord(String scenarioId, long seed, List<String> agentIds, List<RoundRecord> rounds,
                        RunStatus status, double terminalValue, int signalEvaluations, int signalSeen,
                        int signalFalseAlarms, double dBarUConfigured, double dBarUAccumulated) {
    public RunRecord {
        agentIds = List.copyOf(agentIds);
        rounds = List.copyOf(rounds);
    }

    public JsonNode roundsJson() {
        return Canonical.MAPPER.valueToTree(rounds);
    }

    /** SHA-256 (hex) of the canonical sorted-key JSON of the rounds. */
    public String replayDigest() {
        return Canonical.digestOf(roundsJson());
    }

    public double emergentFalseAlarmRate() {
        return signalEvaluations == 0 ? 0.0 : (double) signalFalseAlarms / signalEvaluations;
    }

    /** The JSONL line object: all fields plus replayDigest. */
    public ObjectNode toJson() {
        ObjectNode n = Canonical.MAPPER.valueToTree(this);
        n.put("replayDigest", replayDigest());
        return n;
    }
}
