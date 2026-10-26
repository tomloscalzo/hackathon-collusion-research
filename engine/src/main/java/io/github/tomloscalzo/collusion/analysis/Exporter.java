package io.github.tomloscalzo.collusion.analysis;

import io.github.tomloscalzo.collusion.results.RoundRecord;
import io.github.tomloscalzo.collusion.results.RunRecord;

/**
 * Long-format CSV lines for R / Python (UTF-8, LF): one line per round, and one line per decision (agent x round).
 * Missing values (no hidden fill, no fill price) are empty fields. keys are the leading id columns, already CSV-safe.
 */
public final class Exporter {
    public static final String ROUNDS_HEADER =
            "cell,seed_index,seed,round,inside_quote,inside_ci,p_trigger,p_evidence,tip_active,triggered,evidence,ended_with";
    public static final String DECISIONS_HEADER =
            "cell,seed_index,seed,round,agent,displayed,hidden_fill,own_ci,volume,observed_volume,fill_price,payoff,fine,"
                    + "signal_evaluated,signal_seen,saw_prior_quotes,phase,excluded";

    private Exporter() {}

    public static void rounds(StringBuilder sb, String cell, int seedIndex, RunRecord run) {
        for (RoundRecord r : run.rounds()) {
            sb.append(cell).append(',').append(seedIndex).append(',').append(run.seed()).append(',').append(r.round())
                    .append(',').append(r.insideQuote()).append(',').append(r.insideCi()).append(',')
                    .append(r.detection().pTrigger()).append(',').append(r.detection().pEvidence()).append(',')
                    .append(r.detection().tipActive()).append(',').append(r.detection().triggered()).append(',')
                    .append(r.detection().evidence()).append(',').append(r.endedWith() == null ? "" : r.endedWith())
                    .append('\n');
        }
    }

    public static void decisions(StringBuilder sb, String cell, int seedIndex, RunRecord run) {
        for (RoundRecord r : run.rounds()) {
            for (RoundRecord.AgentRound a : r.agents()) {
                sb.append(cell).append(',').append(seedIndex).append(',').append(run.seed()).append(',')
                        .append(r.round()).append(',').append(a.id()).append(',').append(a.displayed()).append(',')
                        .append(a.hiddenFill() == null ? "" : a.hiddenFill()).append(',').append(a.ownCi()).append(',')
                        .append(a.volume()).append(',').append(a.observedVolume()).append(',')
                        .append(a.fillPrice() == null ? "" : a.fillPrice()).append(',').append(a.payoff()).append(',')
                        .append(a.fine()).append(',').append(a.signalEvaluated()).append(',').append(a.signalSeen())
                        .append(',').append(a.sawPriorQuotes()).append(',').append(a.phase()).append(',')
                        .append(a.excluded()).append('\n');
            }
        }
    }
}
