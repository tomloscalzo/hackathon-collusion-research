package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Stage settlement (spec 2.2). Contestable flow (1 - phi) Q goes to the lowest effective price (displayed or hidden
 * fill) among agents not excluded by penance routing, ties split equally, executing at that price. Preferenced flow
 * phi Q is split equally among all N agents and executes at the displayed inside quote of the non-excluded agents
 * (price matching). If every agent is excluded the exclusion is void.
 */
public final class PayoffEngine {
    private static final double TIE = 1e-9;
    private final MarketParams m;
    private final boolean checkIdentity;

    public PayoffEngine(MarketParams m, boolean checkIdentity) {
        this.m = m;
        this.checkIdentity = checkIdentity;
    }

    /** volumes are true (noise-free); fillPrices are null for an agent with no volume. */
    public record Settlement(List<Double> volumes, List<Double> fillPrices, List<Double> payoffs, double insideQuote,
                             double contestablePrice, List<Boolean> excluded) {}

    public Settlement settle(List<Action.Quote> quotes, Set<Integer> excluded, boolean allMembers, double sumIRP) {
        int n = quotes.size();
        Set<Integer> excl = excluded.size() >= n ? Set.of() : excluded;
        double inside = Double.POSITIVE_INFINITY;
        double pc = Double.POSITIVE_INFINITY;
        for (int i = 0; i < n; i++) {
            if (excl.contains(i)) {
                continue;
            }
            inside = StrictMath.min(inside, quotes.get(i).displayed());
            pc = StrictMath.min(pc, quotes.get(i).effective());
        }
        List<Integer> winners = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            if (!excl.contains(i) && quotes.get(i).effective() <= pc + TIE) {
                winners.add(i);
            }
        }
        double contestableVol = (1.0 - m.phi()) * PayoffFunctions.volume(m, pc);
        double prefVol = m.phi() * PayoffFunctions.volume(m, inside);
        List<Double> vols = new ArrayList<>(n);
        List<Double> fills = new ArrayList<>(n);
        List<Double> pays = new ArrayList<>(n);
        List<Boolean> exFlags = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            double vc = winners.contains(i) ? contestableVol / winners.size() : 0.0;
            double vp = prefVol / n;
            double v = vc + vp;
            double revenue = vc * pc + vp * inside;
            vols.add(v);
            fills.add(v > 0 ? revenue / v : null);
            pays.add(revenue - v * m.s0());
            exFlags.add(excl.contains(i));
        }
        if (checkIdentity && allMembers && excl.isEmpty() && sumIRP == 0.0 && allEqual(quotes)) {
            double expected = PayoffFunctions.rent(m, inside) / n;
            for (double p : pays) {
                if (StrictMath.abs(p - expected) > 1e-9) {
                    throw new IllegalStateException("payoff identity violated: " + p + " vs " + expected);
                }
            }
        }
        return new Settlement(vols, fills, pays, inside, pc, exFlags);
    }

    private static boolean allEqual(List<Action.Quote> quotes) {
        double d = quotes.get(0).displayed();
        for (Action.Quote q : quotes) {
            if (q.hiddenFill() != null || StrictMath.abs(q.displayed() - d) > 1e-12) {
                return false;
            }
        }
        return true;
    }
}
