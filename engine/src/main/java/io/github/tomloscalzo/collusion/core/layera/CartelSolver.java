package io.github.tomloscalzo.collusion.core.layera;

import io.github.tomloscalzo.collusion.core.model.DetectionShape;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.PunishmentForm;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.function.DoublePredicate;
import java.util.function.DoubleUnaryOperator;

/**
 * Stationary Layer A solver (spec 2.3-2.7): W(theta) from eq. (11), the uniform-hazard IC' of eq. (8'), the
 * constrained argmax theta* of eq. (12) and ripeness E of eq. (13).
 *
 * <p>tick = 0: a 1001-point grid on [0,1] with fixed-iteration bisection of the IC boundary and golden-section
 * refinement of the argmax. tick &gt; 0: enumeration of the discrete margins s = s^N + j tick up to sM.
 */
public final class CartelSolver {
    private static final int GRID_POINTS = 1001;
    private static final int GOLDEN_ITERS = 100;
    private static final int BISECT_ITERS = 60;
    private static final double INV_PHI = (StrictMath.sqrt(5.0) - 1.0) / 2.0;

    /** Per-scenario constants. */
    private static final class Ctx {
        final Scenario s;
        final MarketParams m;
        final double sN;
        final double sM;
        final double span;
        final double delta;
        final double z;
        final double zPost;
        final double q;
        final int k;

        Ctx(Scenario s) {
            this.s = s;
            this.m = s.market();
            this.sN = PayoffFunctions.nashMargin(m);
            this.sM = PayoffFunctions.monopolyMargin(m);
            this.span = StrictMath.max(0.0, sM - sN);
            this.delta = s.delta();
            double piN = PayoffFunctions.piNash(m);
            this.z = piN / (1.0 - delta);
            this.zPost = s.enforcement().piPost() / (1.0 - delta);
            // Spec 3.1: collective (price-war) punishment needs observation only; penance is targeted and needs attribution.
            this.q = s.punishment() == PunishmentForm.PENANCE ? s.aggregates().qTargeted() : s.aggregates().qCollective();
            this.k = s.infinitePunishment() ? -1 : s.punishmentLength();
        }

        HazardBreakdown hazard(double theta) {
            if (theta <= 0.0) {
                return HazardBreakdown.ZERO;
            }
            double margin = PayoffFunctions.margin(m, theta) - sN;
            double ci = PayoffFunctions.collusionIndex(m, PayoffFunctions.margin(m, theta));
            return Enforcement.hazard(s.enforcement(), margin, ci, s.aggregates().dBarU());
        }

        double w(double theta) {
            if (theta <= 0.0) {
                return z;
            }
            HazardBreakdown h = hazard(theta);
            double rT = h.rhoEnd();
            double rE = h.rhoFine();
            double num = PayoffFunctions.piC(m, theta) - rE * s.enforcement().fine()
                    + delta * (rE * z + (rT - rE) * zPost);
            return num / (1.0 - delta * (1.0 - rT));
        }

        boolean ic(double theta) {
            if (theta <= 0.0) {
                return true;
            }
            double rT = hazard(theta).rhoEnd();
            double psi = Enforcement.psi(delta * (1.0 - rT), q, k);
            double d = PayoffFunctions.deviationGain(m, theta);
            double l = PayoffFunctions.punishmentLoss(m, theta, s.punishment(), s.punishmentLevel(),
                    s.aggregates().sumIRP());
            double rhs = l == 0.0 ? 0.0 : psi * l;
            double tol = 1e-12 * StrictMath.max(1.0, StrictMath.max(StrictMath.abs(d), StrictMath.abs(rhs)));
            return d <= rhs + tol;
        }
    }

    /** W(theta), eq. (11). */
    public double w(Scenario s, double theta) {
        return new Ctx(s).w(theta);
    }

    /** IC'(theta), eq. (8') with the uniform-hazard closed form. */
    public boolean ic(Scenario s, double theta) {
        return new Ctx(s).ic(theta);
    }

    public boolean icUniformHazard(Scenario s, double theta) {
        return ic(s, theta);
    }

    /** Eq. (9) limit: (1 - phi)(N - 1) <= Psi (price war) or N - 1 <= Psi (penance), with rho = 0. */
    public boolean eq9Holds(Scenario s) {
        Ctx c = new Ctx(s);
        double need = s.punishment() == PunishmentForm.PENANCE
                ? s.market().n() - 1
                : (1.0 - s.market().phi()) * (s.market().n() - 1);
        return need <= Enforcement.psi(c.delta, c.q, c.k) * (1.0 + 1e-12);
    }

    public CartelSolution solve(Scenario s) {
        Ctx c = new Ctx(s);
        MarketParams m = c.m;
        boolean tickMode = m.tick() > 0;

        double[] th = buildGrid(c, tickMode);
        double[] w = new double[th.length];
        boolean[] ic = new boolean[th.length];
        for (int i = 0; i < th.length; i++) {
            w[i] = c.w(th[i]);
            ic[i] = c.ic(th[i]);
        }

        double thetaHat = thetaHat(c, th, ic, tickMode);
        double thetaPart = search(c, th, w, ic, tickMode, true, false);
        if (thetaPart < 0) {
            thetaPart = 0.0;
        }
        double thetaStar = search(c, th, w, ic, tickMode, true, true);
        double w0 = c.z;
        if (thetaStar <= 0.0 || c.w(thetaStar) <= w0 + 1e-12 * StrictMath.max(1.0, StrictMath.abs(w0))) {
            thetaStar = 0.0;
        }
        double wStar = c.w(thetaStar);

        Regime regime;
        if (thetaStar <= 0.0) {
            regime = Regime.CORNER_ZERO;
        } else if (thetaStar >= 1.0 - 1e-9) {
            regime = Regime.CORNER_ONE;
        } else {
            double thetaU = search(c, th, w, ic, tickMode, false, true);
            double wU = c.w(thetaU);
            boolean binds = wStar < wU - 1e-9 * StrictMath.max(1.0, StrictMath.abs(wU));
            regime = binds ? Regime.INTERIOR_INTERNAL : Regime.INTERIOR_EXTERNAL;
        }

        double ripeness = 0.0;
        if (thetaStar > 0.0) {
            double rT = c.hazard(thetaStar).rhoEnd();
            double piMono = PayoffFunctions.piMonopoly(m);
            ripeness = (1.0 - c.delta * (1.0 - rT)) * (wStar - c.z) / piMono;
        }

        boolean any = false;
        boolean myopic = true;
        for (double t : th) {
            if (t <= 0.0) {
                continue;
            }
            any = true;
            double rhoF = c.hazard(t).rhoFine() * s.enforcement().fine();
            if (!(rhoF > PayoffFunctions.piC(m, t))) {
                myopic = false;
                break;
            }
        }
        myopic = any && myopic;

        List<Double> tg = new ArrayList<>(th.length);
        List<Double> wg = new ArrayList<>(th.length);
        List<Boolean> ig = new ArrayList<>(th.length);
        for (int i = 0; i < th.length; i++) {
            tg.add(th[i]);
            wg.add(w[i]);
            ig.add(ic[i]);
        }
        boolean changeFlag = s.enforcement().screen().kind() == DetectionShape.CHANGE;
        return new CartelSolution(thetaHat, thetaStar, thetaPart, wStar, w0, ripeness, regime, tickMode, myopic,
                changeFlag, Collections.unmodifiableList(tg), Collections.unmodifiableList(wg),
                Collections.unmodifiableList(ig));
    }

    private static double[] buildGrid(Ctx c, boolean tickMode) {
        if (c.span <= 0.0) {
            return new double[] {0.0};
        }
        if (tickMode) {
            int n = (int) StrictMath.floor(c.span / c.m.tick() + 1e-9);
            double[] th = new double[n + 1];
            for (int j = 0; j <= n; j++) {
                th[j] = StrictMath.min(1.0, j * c.m.tick() / c.span);
            }
            return th;
        }
        double[] th = new double[GRID_POINTS];
        for (int i = 0; i < GRID_POINTS; i++) {
            th[i] = i / (double) (GRID_POINTS - 1);
        }
        return th;
    }

    private static double thetaHat(Ctx c, double[] th, boolean[] ic, boolean tickMode) {
        int last = -1;
        for (int i = 1; i < th.length; i++) {
            if (ic[i]) {
                last = i;
            }
        }
        if (last < 0) {
            return 0.0;
        }
        if (tickMode || last == th.length - 1) {
            return th[last];
        }
        double lo = th[last];
        double hi = th[last + 1];
        for (int it = 0; it < BISECT_ITERS; it++) {
            double mid = 0.5 * (lo + hi);
            if (c.ic(mid)) {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        return lo;
    }

    /** Argmax of W over the (optionally IC-feasible) set; returns -1 when the set is empty. */
    private static double search(Ctx c, double[] th, double[] w, boolean[] ic, boolean tickMode,
                                 boolean constrained, boolean includeZero) {
        int best = -1;
        for (int i = 0; i < th.length; i++) {
            if (th[i] <= 0.0 && !includeZero) {
                continue;
            }
            if (constrained && !ic[i]) {
                continue;
            }
            if (best < 0 || w[i] > w[best]) {
                best = i;
            }
        }
        if (best < 0) {
            return -1.0;
        }
        if (tickMode) {
            return th[best];
        }
        DoublePredicate feas = x -> !constrained || c.ic(x);
        double t = th[best];
        double a = t;
        if (best > 0) {
            double l = th[best - 1];
            a = feas.test(l) ? l : boundary(feas, l, t);
        }
        double b = t;
        if (best < th.length - 1) {
            double r = th[best + 1];
            b = feas.test(r) ? r : boundary(feas, r, t);
        }
        DoubleUnaryOperator f = c::w;
        double g = golden(f, a, b);
        double[] cands = {t, a, b, g};
        double bestT = t;
        double bestW = f.applyAsDouble(t);
        for (double x : cands) {
            if (x <= 0.0 && !includeZero) {
                continue;
            }
            double fx = f.applyAsDouble(x);
            if (fx > bestW) {
                bestW = fx;
                bestT = x;
            }
        }
        return bestT;
    }

    /** Bisection for the feasibility boundary between an infeasible and a feasible point; returns the feasible side. */
    private static double boundary(DoublePredicate feas, double infeasible, double feasible) {
        double bad = infeasible;
        double good = feasible;
        for (int it = 0; it < BISECT_ITERS; it++) {
            double mid = 0.5 * (bad + good);
            if (feas.test(mid)) {
                good = mid;
            } else {
                bad = mid;
            }
        }
        return good;
    }

    private static double golden(DoubleUnaryOperator f, double lo, double hi) {
        double a = lo;
        double b = hi;
        double x1 = b - INV_PHI * (b - a);
        double x2 = a + INV_PHI * (b - a);
        double f1 = f.applyAsDouble(x1);
        double f2 = f.applyAsDouble(x2);
        for (int it = 0; it < GOLDEN_ITERS; it++) {
            if (f1 < f2) {
                a = x1;
                x1 = x2;
                f1 = f2;
                x2 = a + INV_PHI * (b - a);
                f2 = f.applyAsDouble(x2);
            } else {
                b = x2;
                x2 = x1;
                f2 = f1;
                x1 = b - INV_PHI * (b - a);
                f1 = f.applyAsDouble(x1);
            }
        }
        return 0.5 * (a + b);
    }
}
