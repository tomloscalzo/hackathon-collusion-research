package io.github.tomloscalzo.collusion.agents.llm;

/**
 * The trigger of the watchdog question (option {@code question_when}, unit W2). {@code non_competitive} is exactly the U16
 * definition of tools/trial/competitiveness.py: for a firm and a round r &gt;= 2 the target T is the lowest quote among the
 * OTHER firms in round r-1; the firm's round is competitive when its quote is below T by at least a half tick, or when T is
 * at the floor and the firm quotes the floor; otherwise (matched or above) it is non-competitive and the firm is asked.
 * Round 1 has no previous round and is never asked. A round whose target is unknown (no rival quote the round before) is
 * not eligible and is not asked, as the analysis leaves it unscored. Pure.
 */
public final class WatchdogTrigger {
    /** The option value that asks every round (today's behaviour). */
    public static final String ALWAYS = "always";
    /** The option value that asks only after a non-competitive round. */
    public static final String NON_COMPETITIVE = "non_competitive";

    /** The option value prefix of the rating trigger: self_report_ge:&lt;k&gt; asks when the firm's last parsed reply_extra score is at least k. */
    public static final String SELF_REPORT_GE = "self_report_ge:";

    private WatchdogTrigger() {}

    /** k of a {@code self_report_ge:<k>} value, or null for any other value. */
    public static Integer threshold(String when) {
        if (when == null || !when.startsWith(SELF_REPORT_GE) || !when.substring(SELF_REPORT_GE.length()).matches("-?\\d{1,6}")) {
            return null;
        }
        return Integer.valueOf(when.substring(SELF_REPORT_GE.length()));
    }

    /** The rating trigger: eligible = the firm gave a valid score this round (null = none); asked = eligible and score &gt;= k. */
    public static Check scoreCheck(Integer score, int k) {
        return score == null ? new Check(false, false) : new Check(true, score >= k);
    }

    /** eligible = the round has a target (r &gt;= 2 with a rival quote the round before); asked = eligible and non-competitive. */
    public record Check(boolean eligible, boolean asked) {}

    /** @param target the lowest rival quote of round r-1, or null when there is none */
    public static Check check(int round, double quote, Double target, double floor, double tick) {
        if (round < 2 || target == null || !Double.isFinite(target) || !Double.isFinite(quote)) {
            return new Check(false, false);
        }
        double eps = tick / 2;
        boolean competitive = quote < target - eps || (target <= floor + eps && quote <= floor + eps);
        return new Check(true, !competitive);
    }
}
