package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.mc.RandomStream;

/**
 * The single deviation-signal generator (ticket T1). The visibility draw uses the observer's own stream
 * {@code signal:<observer>}, exactly one uniform per round. The seen rule (TEST_PLAN preamble): a deviation is seen when
 * the inside quote is below the reference margin minus the tolerance; when the inside quote was not observed and the
 * agent sees its own volume, when that volume is more than 2 * demandNoiseSd below the volume expected under adherence,
 * Q(reference)/N.
 */
public final class DeviationSignal {
    private static final double EPS = 1e-9;

    private DeviationSignal() {}

    /** One uniform: are the previous round's quotes visible to this observer? o = 1 always, o = 0 never. */
    public static boolean quotesVisible(RandomStream signalStream, double o) {
        return signalStream.nextDouble() < o;
    }

    public static boolean seen(MarketParams m, ObservationPolicy op, Observation.PastRound last, double refMargin,
                               double tolerance) {
        if (last == null) {
            return false;
        }
        if (last.insideQuote() != null) {
            return last.insideQuote() < refMargin - tolerance - EPS;
        }
        if (op.showOwnVolume() && last.ownVolume() != null) {
            double expected = PayoffFunctions.volume(m, refMargin) / m.n();
            return expected - last.ownVolume() > 2.0 * op.demandNoiseSd() + EPS;
        }
        return false;
    }
}
