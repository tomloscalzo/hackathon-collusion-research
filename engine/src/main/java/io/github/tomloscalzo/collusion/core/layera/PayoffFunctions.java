package io.github.tomloscalzo.collusion.core.layera;

import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.PunishmentForm;
import io.github.tomloscalzo.collusion.core.model.PunishmentLevel;

/** Stage payoffs of the market-maker instantiation (spec 2.1-2.2, eq. 1, 4-7, 15). All numerics use StrictMath. */
public final class PayoffFunctions {
    private PayoffFunctions() {}

    private static final double NASH_TOL = 1e-12;
    private static final int MAX_J = 10_000_000;

    /** Eq. (4). */
    public static double volume(MarketParams m, double s) {
        return m.q0() * StrictMath.max(0.0, 1.0 - s / m.sBar());
    }

    /** c = (1 - phi) + phi/N. */
    public static double contestableShare(MarketParams m) {
        return (1.0 - m.phi()) + m.phi() / m.n();
    }

    /** Monopoly margin (s0 + sBar)/2. */
    public static double monopolyMargin(MarketParams m) {
        return (m.s0() + m.sBar()) / 2.0;
    }

    /** j*: largest j >= 1 with (j-1) c Q(s0+(j-1)tick) <= j Q(s0+j tick)/N. Returns 0 when tick = 0 (s^N = s0). */
    public static int nashTickMultiple(MarketParams m) {
        if (!(m.tick() > 0)) {
            return 0;
        }
        double c = contestableShare(m);
        int best = 1;
        for (int j = 2; j < MAX_J; j++) {
            double sj = m.s0() + j * m.tick();
            if (sj >= m.sBar()) {
                break;
            }
            double lhs = (j - 1) * c * volume(m, m.s0() + (j - 1) * m.tick());
            double rhs = j * volume(m, sj) / m.n();
            if (lhs <= rhs + NASH_TOL) {
                best = j;
            }
        }
        return best;
    }

    /** s^N = s0 + j* tick (s0 when tick = 0). */
    public static double nashMargin(MarketParams m) {
        return m.s0() + nashTickMultiple(m) * m.tick();
    }

    /** sM - s^N, floored at 0. */
    public static double span(MarketParams m) {
        return StrictMath.max(0.0, monopolyMargin(m) - nashMargin(m));
    }

    /** Eq. (1). */
    public static double margin(MarketParams m, double theta) {
        double sN = nashMargin(m);
        return sN + theta * (monopolyMargin(m) - sN);
    }

    /** Eq. (2), unclipped; 0 when the span is degenerate. */
    public static double collusionIndex(MarketParams m, double s) {
        double sN = nashMargin(m);
        double d = monopolyMargin(m) - sN;
        return d > 0 ? (s - sN) / d : 0.0;
    }

    /** X = (s - s0) Q(s). */
    public static double rent(MarketParams m, double s) {
        return (s - m.s0()) * volume(m, s);
    }

    /** Eq. (5). */
    public static double piC(MarketParams m, double theta) {
        return rent(m, margin(m, theta)) / m.n();
    }

    /** Eq. (6); the limit as iota goes to 0 when tick = 0. */
    public static double piD(MarketParams m, double theta) {
        double s = margin(m, theta);
        double c = contestableShare(m);
        if (m.tick() > 0) {
            return rent(m, s - m.tick()) * c;
        }
        return rent(m, s) * c;
    }

    /** Eq. (7). */
    public static double deviationGain(MarketParams m, double theta) {
        return piD(m, theta) - piC(m, theta);
    }

    /** Static-Nash profit (s^N - s0) Q(s^N)/N. */
    public static double piNash(MarketParams m) {
        return rent(m, nashMargin(m)) / m.n();
    }

    /** Monopoly profit per member (sM - s0) Q(sM)/N. */
    public static double piMonopoly(MarketParams m) {
        return rent(m, monopolyMargin(m)) / m.n();
    }

    /** Punishment-phase payoff pi_p = pi_war - sumIRP (price war) or pi_c - (1-phi)X/N - sumIRP (penance). */
    public static double piPunish(MarketParams m, double theta, PunishmentForm f, PunishmentLevel lvl, double sumIRP) {
        double war;
        if (f == PunishmentForm.PENANCE) {
            war = piC(m, theta) - (1.0 - m.phi()) * rent(m, margin(m, theta)) / m.n();
        } else if (lvl == PunishmentLevel.STATIC_NASH) {
            war = piNash(m);
        } else {
            war = 0.0;
        }
        return war - sumIRP;
    }

    /** L = pi_c - pi_p. */
    public static double punishmentLoss(MarketParams m, double theta, PunishmentForm f, PunishmentLevel lvl, double sumIRP) {
        return piC(m, theta) - piPunish(m, theta, f, lvl, sumIRP);
    }

    /** Eq. (15): pi_c^eff = pi_c - A (pi_c - pi_p)/(1 + A), A = alpha delta (1 - delta^k)/(1 - delta); k < 0 = infinite. */
    public static double effectivePiC(double piC, double piP, double alpha, double delta, int k) {
        double a = alpha * Enforcement.psi(delta, 1.0, k);
        return piC - a * (piC - piP) / (1.0 + a);
    }
}
