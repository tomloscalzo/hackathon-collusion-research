package io.github.tomloscalzo.collusion.core.layera;

import io.github.tomloscalzo.collusion.core.model.EnforcementParams;
import io.github.tomloscalzo.collusion.core.model.SignalKind;

/** Enforcement multiplier (eq. 8), hazards (eq. 10) and detection probabilities (eq. 14). */
public final class Enforcement {
    private Enforcement() {}

    /** Psi = delta q (1 - delta^k)/(1 - delta); k < 0 means infinite (delta q/(1 - delta)); k = 0 gives 0. */
    public static double psi(double delta, double q, int k) {
        if (k == 0 || q == 0.0) {
            return 0.0;
        }
        if (k < 0) {
            return delta >= 1.0 ? Double.POSITIVE_INFINITY : delta * q / (1.0 - delta);
        }
        if (delta >= 1.0) {
            return q * k;
        }
        return delta * q * (1.0 - StrictMath.pow(delta, k)) / (1.0 - delta);
    }

    /**
     * Hazard at a coalition state theta > 0. The caller gates theta = 0 (both hazards zero); rho_tip applies for
     * every theta > 0 and is not gated on tau (spec 2.4).
     */
    public static HazardBreakdown hazard(EnforcementParams e, double marginAboveNash, double ci, double dBarU) {
        double rhoScreen = StrictMath.min(1.0, e.screen().slope() * e.screen().g(marginAboveNash, ci));
        double pTrigger = 1.0 - (1.0 - rhoScreen) * (1.0 - e.rhoTip());
        double pEvidence = 1.0 - (1.0 - dBarU) * (1.0 - e.rhoCoop());
        return new HazardBreakdown(pTrigger, pEvidence);
    }

    /** Eq. (14), collective punishment: public signal q = o; private independent signals 1 - (1 - o)^(n-1). */
    public static double qCollective(double o, int n, SignalKind kind) {
        if (kind == SignalKind.PUBLIC) {
            return o;
        }
        return 1.0 - StrictMath.pow(1.0 - o, n - 1);
    }
}
