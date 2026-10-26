package io.github.tomloscalzo.collusion.agents.llm;

import java.util.ArrayList;
import java.util.List;

/**
 * The switch point b-hat (spec 4.1, T63): the payment, in units of the gross collusive gain G, at which the frequency of
 * the collusive choice crosses one half. Algorithm: (1) rows are sorted by payment ascending (a payment on the competitive
 * option is positive, on the collusive option negative), rows without a valid call are dropped; (2) the collusive
 * proportions are made non-increasing in the payment by weighted pool-adjacent-violators, weights = valid calls per row;
 * (3) b-hat is the linear interpolation between the last fitted value above one half and the first at or below it;
 * (4) censoring: if even the lowest payment gives a fit at or below one half, b-hat = the lowest payment, flag LOW (the
 * always-competitive cell); if no fit reaches one half, b-hat = the highest payment, flag HIGH. Refusals are excluded from
 * the proportions and counted by the caller.
 */
public final class SwitchPoint {
    private SwitchPoint() {}

    public enum Censor { NONE, LOW, HIGH, NO_DATA }

    public record Estimate(double bHat, Censor censor, List<Double> payments, List<Double> fitted) {}

    /** payments ascending or not (sorted here); collude[i] of total[i] calls chose the collusive option. */
    public static Estimate estimate(double[] payments, int[] collude, int[] total) {
        int n = payments.length;
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        java.util.Arrays.sort(order, (a, b) -> Double.compare(payments[a], payments[b]));
        List<Double> b = new ArrayList<>();
        List<Double> p = new ArrayList<>();
        List<Double> w = new ArrayList<>();
        for (int idx : order) {
            if (total[idx] > 0) {
                b.add(payments[idx]);
                p.add((double) collude[idx] / total[idx]);
                w.add((double) total[idx]);
            }
        }
        if (b.isEmpty()) {
            return new Estimate(Double.NaN, Censor.NO_DATA, List.of(), List.of());
        }
        // weighted PAV for a non-increasing fit
        List<double[]> blocks = new ArrayList<>(); // {mean, weight, count}
        for (int i = 0; i < b.size(); i++) {
            blocks.add(new double[] {p.get(i), w.get(i), 1});
            while (blocks.size() > 1) {
                double[] last = blocks.get(blocks.size() - 1);
                double[] prev = blocks.get(blocks.size() - 2);
                if (prev[0] < last[0] - 1e-15) {
                    double wt = prev[1] + last[1];
                    double mean = (prev[0] * prev[1] + last[0] * last[1]) / wt;
                    blocks.remove(blocks.size() - 1);
                    blocks.set(blocks.size() - 1, new double[] {mean, wt, prev[2] + last[2]});
                } else {
                    break;
                }
            }
        }
        List<Double> fit = new ArrayList<>();
        for (double[] blk : blocks) {
            for (int k = 0; k < (int) blk[2]; k++) {
                fit.add(blk[0]);
            }
        }
        if (fit.get(0) <= 0.5 + 1e-12) {
            return new Estimate(b.get(0), Censor.LOW, b, fit);
        }
        for (int i = 1; i < fit.size(); i++) {
            if (fit.get(i) <= 0.5 + 1e-12) {
                double f0 = fit.get(i - 1);
                double f1 = fit.get(i);
                double x = b.get(i - 1) + (f0 - 0.5) / (f0 - f1) * (b.get(i) - b.get(i - 1));
                return new Estimate(x, Censor.NONE, b, fit);
            }
        }
        return new Estimate(b.get(b.size() - 1), Censor.HIGH, b, fit);
    }
}
