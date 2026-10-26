package io.github.tomloscalzo.collusion.agents;

import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.PunishmentLevel;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.engine.Action;
import io.github.tomloscalzo.collusion.engine.Decision;
import io.github.tomloscalzo.collusion.engine.DeviationSignal;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.engine.QuoteGrid;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

/**
 * Grim / finite-k trigger. Adheres at s(theta) until a seen deviation, then quotes the war price (s0 for
 * PunishmentLevel.S0, s^N for STATIC_NASH) for k rounds (k &lt; 0 = forever), ignoring signals during its own war and for one grace
 * round after it (so a symmetric pair recovers after a false alarm instead of alternating wars forever). Optional hidden fill from a given round (per-quote option, T2).
 */
public final class TriggerK implements Agent {
    private final String id;
    private final Scenario sc;
    private final ObservationPolicy op;
    private final double theta;
    private final int k;
    private final double tolerance;
    private final int hiddenFromRound;
    private final double hiddenDelta;
    private final double sRef;
    private final double sWar;
    private int warLeft;
    private boolean warForever;
    private int lastWarRound;
    private final int forcedSignalRound;

    public TriggerK(String id, Scenario sc, ObservationPolicy op, double theta, int k, double tolerance,
                    int hiddenFromRound, double hiddenDelta, int forcedSignalRound) {
        this.forcedSignalRound = forcedSignalRound;
        this.id = id;
        this.sc = sc;
        this.op = op;
        this.theta = theta;
        this.k = k;
        this.tolerance = tolerance;
        this.hiddenFromRound = hiddenFromRound;
        this.hiddenDelta = hiddenDelta;
        this.sRef = QuoteGrid.snap(sc.market(), PayoffFunctions.margin(sc.market(), theta));
        this.sWar = warQuote(sc);
    }

    public static double warQuote(Scenario sc) {
        return sc.punishmentLevel() == PunishmentLevel.STATIC_NASH
                ? PayoffFunctions.nashMargin(sc.market()) : sc.market().s0();
    }

    @Override
    public String id() {
        return id;
    }

    @Override
    public Optional<SignalReference> signalReference() {
        return Optional.of(new SignalReference(sRef, tolerance));
    }

    /** T103/T87: built by case; the trigger is on the best quote in the market, s_p is the grid-rounded margin. */
    @Override
    public String disclosedRule() {
        String by = tolerance > 0 ? String.format(Locale.ROOT, " by more than %.2f", tolerance) : "";
        String head = String.format(Locale.ROOT,
                "The other market maker quotes a half-spread of %.2f each round. If the best quote in the market is below %.2f%s in any round, it quotes %.2f ",
                sRef, sRef, by, sWar);
        if (k < 0) {
            return head + "for the rest of the game.";
        }
        return head + String.format(Locale.ROOT, "for %d rounds and then returns to %.2f.", k, sRef);
    }

    @Override
    public Decision decide(Observation obs) {
        boolean evaluated = false;
        boolean seen = false;
        int t = obs.round();
        boolean skip = warForever || warLeft > 0 || (lastWarRound > 0 && t - 1 <= lastWarRound + 1);
        if (obs.last() != null && !skip) {
            evaluated = true;
            seen = DeviationSignal.seen(sc.market(), op, obs.last(), sRef, tolerance) || t == forcedSignalRound;
            if (seen) {
                if (k < 0) {
                    warForever = true;
                } else {
                    warLeft = k;
                }
            }
        }
        if (warForever || warLeft > 0) {
            if (!warForever) {
                warLeft--;
            }
            lastWarRound = t;
            return new Decision(Action.Quote.of(sWar), evaluated, seen, "WAR", true, List.of());
        }
        Action.Quote q = hiddenFromRound > 0 && obs.round() >= hiddenFromRound
                ? Action.Quote.hidden(sRef, QuoteGrid.snap(sc.market(), sRef - hiddenDelta))
                : Action.Quote.of(sRef);
        return new Decision(q, evaluated, seen, "ADHERE", false, List.of());
    }
}
