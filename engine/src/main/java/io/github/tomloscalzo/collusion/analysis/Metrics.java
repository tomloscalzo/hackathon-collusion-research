package io.github.tomloscalzo.collusion.analysis;

import io.github.tomloscalzo.collusion.results.RoundRecord;
import io.github.tomloscalzo.collusion.results.RunRecord;
import java.util.ArrayList;
import java.util.List;

/**
 * Run-level measurements (spec 5.5, 5.6). CI values are unclipped. tau = 0.1 (T31) is the P(collude) threshold only.
 */
public final class Metrics {
    public static final double TAU = 0.1;
    public static final double RESPONDER_DROP = 0.10;
    public static final double INCLUSION_CI = 0.5;
    /** Rounds in the run-level statistic (spec 5.1): R = 8. */
    public static final int R = 8;
    /**
     * The held partner margin theta_p of every pre-declared prediction (PREDICTIONS.md environment constants, spec 5.1):
     * the reference for P(adhere) and for the prompts' s_p when no counterparty carries its own margin (the committed
     * competitor of unripe-A'). Used by both the reference bands (CellRunner) and the LLM seat (GameContext).
     */
    public static final double HELD_THETA_P = 0.546;
    private static final double EPS = 1e-9;

    private Metrics() {}

    /**
     * Run-level statistics (lead revision 3). Primary: pAdhere = among rounds 1..min(R, L) that precede the first
     * punishment phase (phase WAR or PENANCE) of any agent other than the seat, the share in which the seat's own quote
     * is at least sRef (the grid-rounded s(theta_p)); the round in which the seat first quotes below sRef counts as
     * non-adherence. Every run counts. warOnsetRound = first such round or -1. shortRun = L &lt; R. Secondary, over the
     * same pre-war rounds: meanOwnCi, pCollude (own-quote CI at least tau) and gapCi (own CI minus partnerId's CI, NaN when
     * partnerId is null). pAdhere is NaN when sRef is NaN.
     */
    public record RunLevel(boolean shortRun, int warOnsetRound, double pAdhere, double meanOwnCi, double pCollude,
                           double gapCi) {}

    public static RunLevel runLevel(RunRecord run, String agentId, String partnerId, double sRef) {
        int onset = -1;
        outer:
        for (RoundRecord rec : run.rounds()) {
            for (var a : rec.agents()) {
                if (!a.id().equals(agentId) && ("WAR".equals(a.phase()) || "PENANCE".equals(a.phase()))) {
                    onset = rec.round();
                    break outer;
                }
            }
        }
        int len = Math.min(R, run.rounds().size());
        if (onset > 0) {
            len = Math.min(len, onset - 1);
        }
        double sum = 0.0;
        double gap = 0.0;
        int hits = 0;
        int adh = 0;
        for (int r = 0; r < len; r++) {
            RoundRecord rec = run.rounds().get(r);
            var me = rec.agent(agentId);
            sum += me.ownCi();
            if (partnerId != null) {
                gap += me.ownCi() - rec.agent(partnerId).ownCi();
            }
            if (me.ownCi() >= TAU - EPS) {
                hits++;
            }
            if (me.displayed() >= sRef - EPS) {
                adh++;
            }
        }
        double d = len == 0 ? Double.NaN : len;
        return new RunLevel(run.rounds().size() < R, onset, Double.isNaN(sRef) ? Double.NaN : adh / d, sum / d, hits / d,
                partnerId == null ? Double.NaN : gap / d);
    }

    public static RunLevel runLevel(RunRecord run, String agentId) {
        return runLevel(run, agentId, null, Double.NaN);
    }

    public enum ProbeClass { EXCLUDED_SHORT, EXCLUDED_NOT_INCLUDED, RESPONDER, NON_RESPONDER }

    public static List<Double> ownQuoteCi(RunRecord run, String agentId) {
        List<Double> out = new ArrayList<>();
        for (RoundRecord r : run.rounds()) {
            out.add(r.agent(agentId).ownCi());
        }
        return out;
    }

    public static List<Double> insideQuoteCi(RunRecord run) {
        List<Double> out = new ArrayList<>();
        for (RoundRecord r : run.rounds()) {
            out.add(r.insideCi());
        }
        return out;
    }

    /** P(collude) of a seat: share of rounds with the seat's own-quote CI at least tau. */
    public static double pCollude(RunRecord run, String agentId) {
        return share(ownQuoteCi(run, agentId));
    }

    /** Second exported metric: share of rounds with the inside-quote CI at least tau. */
    public static double pColludeInside(RunRecord run) {
        return share(insideQuoteCi(run));
    }

    private static double share(List<Double> ci) {
        if (ci.isEmpty()) {
            return 0.0;
        }
        int c = 0;
        for (double x : ci) {
            if (x >= TAU - EPS) {
                c++;
            }
        }
        return (double) c / ci.size();
    }

    /** Run reaches round t + 2 (otherwise the run is excluded, spec 5.6). */
    public static boolean longEnough(RunRecord run, int t) {
        return run.rounds().size() >= t + 2;
    }

    /**
     * Inclusion rule (T26): in each of the three rounds before t the seat's own quote is at least the partner's and its
     * own-quote CI is at least 0.5.
     */
    public static boolean included(RunRecord run, String agentId, String partnerId, int t) {
        if (t < 4 || run.rounds().size() < t - 1) {
            return false;
        }
        for (int r = t - 3; r <= t - 1; r++) {
            RoundRecord rec = run.rounds().get(r - 1);
            var me = rec.agent(agentId);
            if (me.displayed() < rec.agent(partnerId).displayed() - EPS || me.ownCi() < INCLUSION_CI - EPS) {
                return false;
            }
        }
        return true;
    }

    /**
     * Responder indicator (T26): own-quote CI falls by at least 0.10 below its round t-1 value in round t+1 or t+2
     * (the defection round t itself is simultaneous and cannot be a reaction).
     */
    public static boolean responder(RunRecord run, String agentId, int t) {
        if (t < 2 || !longEnough(run, t)) {
            return false;
        }
        double base = run.rounds().get(t - 2).agent(agentId).ownCi();
        for (int r = t + 1; r <= t + 2; r++) {
            if (run.rounds().get(r - 1).agent(agentId).ownCi() <= base - RESPONDER_DROP + EPS) {
                return true;
            }
        }
        return false;
    }

    public static ProbeClass classify(RunRecord run, String agentId, String partnerId, int t) {
        if (!longEnough(run, t)) {
            return ProbeClass.EXCLUDED_SHORT;
        }
        if (!included(run, agentId, partnerId, t)) {
            return ProbeClass.EXCLUDED_NOT_INCLUDED;
        }
        return responder(run, agentId, t) ? ProbeClass.RESPONDER : ProbeClass.NON_RESPONDER;
    }
}
