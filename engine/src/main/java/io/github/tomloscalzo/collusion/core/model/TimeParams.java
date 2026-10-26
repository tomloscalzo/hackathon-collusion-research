package io.github.tomloscalzo.collusion.core.model;

/** h lives only in Horizon.Random. */
public record TimeParams(double delta0, double entryHazard, Horizon horizon, int maxRounds) {
    /** Effective discount factor: delta0 * (1 - h) for a random horizon; delta0 for a known horizon. */
    public double effectiveDelta() {
        if (horizon instanceof Horizon.Random r) {
            return delta0 * (1.0 - r.h());
        }
        return delta0;
    }

    public TimeParams withHorizon(Horizon v) { return new TimeParams(delta0, entryHazard, v, maxRounds); }
    public TimeParams withDelta0(double v) { return new TimeParams(v, entryHazard, horizon, maxRounds); }
}
