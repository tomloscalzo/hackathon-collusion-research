package io.github.tomloscalzo.collusion.core.model;

/** Screen hazard shape: rho_screen = min(1, slope * g), g(x) = max(0, x) on the chosen scale. */
public record ScreenShape(DetectionShape kind, ScreenScale scale, double slope) {
    /** g on the scale: marginAboveNash = s - s^N, ci = unclipped CI. g(x <= 0) = 0. */
    public double g(double marginAboveNash, double ci) {
        double x = scale == ScreenScale.CI ? ci : marginAboveNash;
        return x > 0 ? x : 0.0;
    }

    public ScreenShape withSlope(double v) { return new ScreenShape(kind, scale, v); }
}
