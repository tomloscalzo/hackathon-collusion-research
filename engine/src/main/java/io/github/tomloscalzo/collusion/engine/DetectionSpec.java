package io.github.tomloscalzo.collusion.engine;

/**
 * How external detection runs. OFF: never (probe runs, spec 5.6). SCENARIO: the Layer A screen on the realised inside
 * margin plus the tip rate (Enforcement.hazard). FIXED: constant per-round P(trigger) and P(evidence | trigger), used
 * by the channel-evidence snapshots.
 */
public record DetectionSpec(Mode mode, double pTrigger, double pEvidence) {
    public enum Mode { OFF, SCENARIO, FIXED }

    public static DetectionSpec off() { return new DetectionSpec(Mode.OFF, 0.0, 0.0); }
    public static DetectionSpec scenario() { return new DetectionSpec(Mode.SCENARIO, 0.0, 0.0); }
    public static DetectionSpec fixed(double pTrigger, double pEvidence) { return new DetectionSpec(Mode.FIXED, pTrigger, pEvidence); }
}
