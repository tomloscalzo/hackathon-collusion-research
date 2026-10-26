package io.github.tomloscalzo.collusion.core.model;

/**
 * What an agent sees about the previous round. showOwnVolume / showFillPrice: own volume (with additive noise) and own
 * average fill price. demandNoiseSd: absolute volume units, independent per agent (T20). o: per-round probability that
 * the displayed quotes of the previous round are visible to an observer (T2: o in [0,1]; 0 = no quote observation).
 */
public record ObservationPolicy(boolean showOwnVolume, boolean showFillPrice, double demandNoiseSd, double o) {
    public static ObservationPolicy defaults() {
        return new ObservationPolicy(true, true, 0.0, 1.0);
    }

    public ObservationPolicy withShowOwnVolume(boolean v) { return new ObservationPolicy(v, showFillPrice, demandNoiseSd, o); }
    public ObservationPolicy withShowFillPrice(boolean v) { return new ObservationPolicy(showOwnVolume, v, demandNoiseSd, o); }
    public ObservationPolicy withDemandNoiseSd(double v) { return new ObservationPolicy(showOwnVolume, showFillPrice, v, o); }
    public ObservationPolicy withO(double v) { return new ObservationPolicy(showOwnVolume, showFillPrice, demandNoiseSd, v); }
}
