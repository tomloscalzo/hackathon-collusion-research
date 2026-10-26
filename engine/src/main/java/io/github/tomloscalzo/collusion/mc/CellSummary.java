package io.github.tomloscalzo.collusion.mc;

import io.github.tomloscalzo.collusion.analysis.Metrics;
import io.github.tomloscalzo.collusion.engine.RunStatus;
import io.github.tomloscalzo.collusion.mc.CellRunner.RunResult;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * The per-cell summary row. Every reduction runs over the results in seed-index order, so it does not depend on the
 * thread count. Each statistic comes with its achieved MCSE = SD / sqrt(n) (n = the runs the statistic is computed on;
 * TEST_PLAN 3: target 0.015 at n = 1000); the run-length median has a bootstrap MCSE (200 resamples, fixed seed).
 *
 * <p>p_adhere = mean over ALL runs of P(adhere) (share of rounds 1..min(8, L) before the partner's first war with own quote at
 * least s(theta_p)); mean_ci, p_collude over the same pre-war rounds; short_run_share = share of runs with L &lt; 8. The responder columns are filled for probe cells only.
 */
public final class CellSummary {
    private static final int BOOT = 200;

    private CellSummary() {}

    public static String header(FactorialDesign design) {
        StringBuilder sb = new StringBuilder("cell_index,cell_key,block_id");
        for (var f : design.factors()) {
            sb.append(',').append(f.name());
        }
        sb.append(",n_runs,short_run_share,p_adhere,mcse_p_adhere,sd_p_adhere,mean_ci,mcse_mean_ci,p_collude,mcse_p_collude,")
                .append("n_probe_included,probe_included_share,probe_short_share,responder_rate,mcse_responder_rate,")
                .append("false_alarm_rate,mcse_false_alarm_rate,false_alarm_pooled,")
                .append("run_length_median,mcse_run_length_median,run_length_mean,")
                .append("share_detected,share_horizon,share_cap");
        return sb.toString();
    }

    public static String row(FactorialDesign.Cell cell, List<RunResult> runs) {
        StringBuilder sb = new StringBuilder();
        sb.append(cell.index()).append(',').append(cell.key()).append(',').append(cell.blockId());
        for (String lab : cell.labels().values()) {
            sb.append(',').append(csv(lab));
        }
        int n = runs.size();
        List<Double> stat = new ArrayList<>();
        List<Double> ci = new ArrayList<>();
        List<Double> pc = new ArrayList<>();
        List<Double> far = new ArrayList<>();
        List<Double> resp = new ArrayList<>();
        int probeShort = 0;
        long evals = 0;
        long falseAl = 0;
        int detected = 0;
        int horizon = 0;
        int cap = 0;
        int[] lens = new int[n];
        double lenSum = 0;
        int probeRuns = 0;
        int shortRuns = 0;
        for (int i = 0; i < n; i++) {
            RunResult r = runs.get(i);
            lens[i] = r.rounds();
            lenSum += r.rounds();
            stat.add(r.pAdhere());
            ci.add(r.meanCi());
            pc.add(r.pCollude());
            if (r.shortRun()) {
                shortRuns++;
            }
            if (!Double.isNaN(r.falseAlarmRate())) {
                far.add(r.falseAlarmRate());
            }
            evals += r.signalEvaluations();
            falseAl += r.signalFalseAlarms();
            if (r.status() == RunStatus.EVIDENCE || r.status() == RunStatus.TRIGGER_ONLY) {
                detected++;
            } else if (r.status() == RunStatus.HORIZON) {
                horizon++;
            } else {
                cap++;
            }
            if (r.probeClass() != null) {
                probeRuns++;
                if (r.probeClass() == Metrics.ProbeClass.RESPONDER) {
                    resp.add(1.0);
                } else if (r.probeClass() == Metrics.ProbeClass.NON_RESPONDER) {
                    resp.add(0.0);
                } else if (r.probeClass() == Metrics.ProbeClass.EXCLUDED_SHORT) {
                    probeShort++;
                }
            }
        }
        double[] ms = meanSd(stat);
        double[] mp = meanSd(pc);
        double[] mc = meanSd(ci);
        sb.append(',').append(n).append(',').append(num((double) shortRuns / n))
                .append(',').append(num(ms[0])).append(',').append(num(mcse(ms[1], stat.size()))).append(',')
                .append(num(ms[1])).append(',').append(num(mc[0])).append(',').append(num(mcse(mc[1], ci.size()))).append(',').append(num(mp[0])).append(',').append(num(mcse(mp[1], pc.size())));
        if (probeRuns > 0) {
            double[] mr = meanSd(resp);
            sb.append(',').append(resp.size()).append(',').append(num((double) resp.size() / probeRuns)).append(',')
                    .append(num((double) probeShort / probeRuns)).append(',').append(num(mr[0])).append(',')
                    .append(num(mcse(mr[1], resp.size())));
        } else {
            sb.append(",,,,,");
        }
        double[] mf = meanSd(far);
        sb.append(',').append(num(mf[0])).append(',').append(num(mcse(mf[1], far.size()))).append(',')
                .append(num(evals == 0 ? Double.NaN : (double) falseAl / evals));
        int[] sorted = lens.clone();
        Arrays.sort(sorted);
        double med = median(sorted);
        SplittableRandom rng = new SplittableRandom(Long.parseUnsignedLong(cell.key(), 16));
        double[] boot = new double[BOOT];
        int[] tmp = new int[n];
        for (int b = 0; b < BOOT; b++) {
            for (int i = 0; i < n; i++) {
                tmp[i] = lens[rng.nextInt(n)];
            }
            Arrays.sort(tmp);
            boot[b] = median(tmp);
        }
        sb.append(',').append(num(med)).append(',').append(num(meanSd(boxed(boot))[1])).append(',')
                .append(num(lenSum / n)).append(',').append(num((double) detected / n)).append(',')
                .append(num((double) horizon / n)).append(',').append(num((double) cap / n));
        return sb.toString();
    }

    private static List<Double> boxed(double[] a) {
        List<Double> l = new ArrayList<>(a.length);
        for (double x : a) {
            l.add(x);
        }
        return l;
    }

    private static double median(int[] sorted) {
        int n = sorted.length;
        return n % 2 == 1 ? sorted[n / 2] : 0.5 * (sorted[n / 2 - 1] + sorted[n / 2]);
    }

    /** {mean, sample SD}; NaN entries when n = 0 (mean) or n &lt; 2 (SD). */
    static double[] meanSd(List<Double> v) {
        int n = v.size();
        if (n == 0) {
            return new double[] {Double.NaN, Double.NaN};
        }
        double s = 0.0;
        for (double x : v) {
            s += x;
        }
        double mean = s / n;
        if (n < 2) {
            return new double[] {mean, Double.NaN};
        }
        double ss = 0.0;
        for (double x : v) {
            ss += (x - mean) * (x - mean);
        }
        return new double[] {mean, StrictMath.sqrt(ss / (n - 1))};
    }

    static double mcse(double sd, int n) {
        return n < 2 ? Double.NaN : sd / StrictMath.sqrt(n);
    }

    static String num(double v) {
        return Double.isNaN(v) ? "" : Double.toString(v);
    }

    static String csv(String s) {
        return s.contains(",") || s.contains("\"") ? "\"" + s.replace("\"", "\"\"") + "\"" : s;
    }
}
