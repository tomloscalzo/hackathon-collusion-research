package io.github.tomloscalzo.collusion.analysis;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Reference band (spec 5.8, TEST_PLAN 3): the distribution of the paired contrast estimator at the LLM design size when
 * scripted agents occupy the seat. Inputs are the per-run statistics of the two arms in matched (block, seed index)
 * cells: entry i of arm A and entry i of arm B share the CRN draws. One resample draws clusters x seedsPerCluster seed
 * indices with replacement (the same indices in both arms, consecutive groups of seedsPerCluster are the pseudo
 * paraphrase-cells); the cluster contrast is mean(A over included runs) - mean(B over included runs); the resample
 * contrast is the mean over clusters where both arms have an included run. The band is the 2.5 and 97.5 percentiles
 * (linear interpolation, type 7) over the resamples, with a fixed seed.
 */
public final class ReferenceBand {
    public static final int DEFAULT_CLUSTERS = 10;
    public static final int DEFAULT_RESAMPLES = 1000;

    private ReferenceBand() {}

    public record Band(double lo, double hi, double mean, double sd, double point, int resamples, int usedResamples,
                       boolean degenerate) {}

    public static Band compute(double[] statA, boolean[] inclA, double[] statB, boolean[] inclB, int clusters,
                               int seedsPerCluster, int resamples, long seed) {
        int n = statA.length;
        if (n == 0 || statB.length != n || inclA.length != n || inclB.length != n) {
            throw new IllegalArgumentException("arms must be non-empty and matched (same length)");
        }
        if (clusters < 1 || seedsPerCluster < 1 || resamples < 1) {
            throw new IllegalArgumentException("clusters, seedsPerCluster and resamples must be >= 1");
        }
        SplittableRandom rng = new SplittableRandom(seed);
        double[] vals = new double[resamples];
        int used = 0;
        for (int b = 0; b < resamples; b++) {
            double sum = 0.0;
            int cnt = 0;
            for (int c = 0; c < clusters; c++) {
                double sa = 0.0;
                double sb = 0.0;
                int na = 0;
                int nb = 0;
                for (int k = 0; k < seedsPerCluster; k++) {
                    int i = rng.nextInt(n);
                    if (inclA[i]) {
                        sa += statA[i];
                        na++;
                    }
                    if (inclB[i]) {
                        sb += statB[i];
                        nb++;
                    }
                }
                if (na > 0 && nb > 0) {
                    sum += sa / na - sb / nb;
                    cnt++;
                }
            }
            if (cnt > 0) {
                vals[used++] = sum / cnt;
            }
        }
        double point = fullContrast(statA, inclA, statB, inclB);
        if (used == 0) {
            return new Band(Double.NaN, Double.NaN, Double.NaN, Double.NaN, point, resamples, 0, false);
        }
        double[] v = Arrays.copyOf(vals, used);
        Arrays.sort(v);
        double mean = 0.0;
        for (double x : v) {
            mean += x;
        }
        mean /= used;
        double ss = 0.0;
        for (double x : v) {
            ss += (x - mean) * (x - mean);
        }
        double sd = used > 1 ? StrictMath.sqrt(ss / (used - 1)) : 0.0;
        double lo = percentile(v, 0.025);
        double hi = percentile(v, 0.975);
        return new Band(lo, hi, mean, sd, point, resamples, used, hi - lo < 1e-9);
    }

    /** The contrast on the full scripted population: mean(A included) - mean(B included). */
    public static double fullContrast(double[] statA, boolean[] inclA, double[] statB, boolean[] inclB) {
        double sa = 0.0;
        double sb = 0.0;
        int na = 0;
        int nb = 0;
        for (int i = 0; i < statA.length; i++) {
            if (inclA[i]) {
                sa += statA[i];
                na++;
            }
            if (inclB[i]) {
                sb += statB[i];
                nb++;
            }
        }
        return na > 0 && nb > 0 ? sa / na - sb / nb : Double.NaN;
    }

    static double percentile(double[] sorted, double p) {
        double pos = p * (sorted.length - 1);
        int lo = (int) StrictMath.floor(pos);
        int hi = Math.min(sorted.length - 1, lo + 1);
        return sorted[lo] + (pos - lo) * (sorted[hi] - sorted[lo]);
    }
}
