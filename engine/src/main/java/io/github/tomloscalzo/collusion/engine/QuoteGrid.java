package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.core.model.MarketParams;

/** The engine quote grid s0 + j * quoteIncrement, clamped to [s0, sBar]. */
public final class QuoteGrid {
    private QuoteGrid() {}

    public static double snap(MarketParams m, double x) {
        double j = StrictMath.rint((x - m.s0()) / m.quoteIncrement());
        double g = m.s0() + j * m.quoteIncrement();
        return clamp(m, g);
    }

    public static double clamp(MarketParams m, double x) {
        return StrictMath.max(m.s0(), StrictMath.min(m.sBar(), x));
    }
}
