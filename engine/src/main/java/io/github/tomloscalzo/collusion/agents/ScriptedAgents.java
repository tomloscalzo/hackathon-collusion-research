package io.github.tomloscalzo.collusion.agents;

import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.engine.Action;
import io.github.tomloscalzo.collusion.engine.Decision;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.engine.QuoteGrid;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** The simple scripted agents (no LLM). */
public final class ScriptedAgents {
    private ScriptedAgents() {}

    /** Quotes s^N every round. */
    public static final class AlwaysCompete implements Agent {
        private final String id;
        private final double sN;

        public AlwaysCompete(String id, Scenario sc) {
            this.id = id;
            this.sN = PayoffFunctions.nashMargin(sc.market());
        }

        @Override public String id() { return id; }

        @Override
        public Decision decide(Observation obs) {
            return Decision.simple(Action.Quote.of(sN), "COMPETE");
        }
    }

    /**
     * Adheres at s(theta), defects to s^N in round t, then adheres again (T17). With placebo set it never defects: t is
     * then only the placebo round at which the P3 control run is classified (spec 5.6, BR-15). t &lt;= 0 never defects.
     */
    public static final class DefectOnce implements Agent {
        private final String id;
        private final double sTheta;
        private final double sN;
        private final int t;
        private final boolean placebo;

        public DefectOnce(String id, Scenario sc, double theta, int t) {
            this(id, sc, theta, t, false);
        }

        public DefectOnce(String id, Scenario sc, double theta, int t, boolean placebo) {
            this.id = id;
            this.sTheta = QuoteGrid.snap(sc.market(), PayoffFunctions.margin(sc.market(), theta));
            this.sN = PayoffFunctions.nashMargin(sc.market());
            this.t = t;
            this.placebo = placebo;
        }

        @Override public String id() { return id; }

        /** The defection round, or the placebo round of a placebo agent. */
        public int round() { return t; }

        public boolean placebo() { return placebo; }

        @Override
        public java.util.Optional<Double> referenceMargin() {
            return java.util.Optional.of(sTheta);
        }

        @Override
        public Decision decide(Observation obs) {
            return !placebo && obs.round() == t ? Decision.simple(Action.Quote.of(sN), "DEFECT")
                    : Decision.simple(Action.Quote.of(sTheta), "ADHERE");
        }
    }

    /**
     * Echoes the lowest rival quote seen in the previous round, capped at s(theta); s(theta) in round 1 and repeats its
     * own last quote when the rivals quotes were not visible. injectAt (&gt; 0) replaces its quote in that round by s^N.
     */
    public static final class TitForTat implements Agent {
        private final String id;
        private final double sTheta;
        private final double sN;
        private final int injectAt;

        public TitForTat(String id, Scenario sc, double theta, int injectAt) {
            this.id = id;
            this.sTheta = QuoteGrid.snap(sc.market(), PayoffFunctions.margin(sc.market(), theta));
            this.sN = PayoffFunctions.nashMargin(sc.market());
            this.injectAt = injectAt;
        }

        @Override public String id() { return id; }

        @Override
        public java.util.Optional<Double> referenceMargin() {
            return java.util.Optional.of(sTheta);
        }

        @Override
        public Decision decide(Observation obs) {
            if (injectAt > 0 && obs.round() == injectAt) {
                return Decision.simple(Action.Quote.of(sN), "INJECT");
            }
            Observation.PastRound last = obs.last();
            if (last == null) {
                return Decision.simple(Action.Quote.of(sTheta), "ADHERE");
            }
            if (!last.quotesVisible() || last.rivalQuotes().isEmpty()) {
                return Decision.simple(Action.Quote.of(last.ownQuote()), "HOLD");
            }
            double low = sTheta;
            for (double q : last.rivalQuotes().values()) {
                low = Math.min(low, q);
            }
            return Decision.simple(Action.Quote.of(low), low < sTheta ? "ECHO" : "ADHERE");
        }
    }

    /**
     * Always quotes s(theta). A rival whose quote was below s(theta) - tolerance in the previous round (attribution
     * through the displayed quotes) is routed away from contestable flow for k rounds, ignoring new signals meanwhile.
     */
    public static final class Penance implements Agent {
        private final String id;
        private final double sTheta;
        private final int k;
        private final double tolerance;
        private int left;
        private String target;

        public Penance(String id, Scenario sc, double theta, int k, double tolerance) {
            this.id = id;
            this.sTheta = QuoteGrid.snap(sc.market(), PayoffFunctions.margin(sc.market(), theta));
            this.k = k;
            this.tolerance = tolerance;
        }

        @Override public String id() { return id; }

        @Override
        public java.util.Optional<SignalReference> signalReference() {
            return java.util.Optional.of(new SignalReference(sTheta, tolerance));
        }

        @Override
        public Decision decide(Observation obs) {
            boolean evaluated = false;
            boolean seen = false;
            Observation.PastRound last = obs.last();
            if (left == 0 && last != null) {
                evaluated = true;
                if (last.quotesVisible()) {
                    String worst = null;
                    double low = sTheta - tolerance - 1e-9;
                    for (Map.Entry<String, Double> e : new java.util.TreeMap<>(last.rivalQuotes()).entrySet()) {
                        if (e.getValue() < low) {
                            low = e.getValue();
                            worst = e.getKey();
                        }
                    }
                    if (worst != null) {
                        seen = true;
                        target = worst;
                        left = k;
                    }
                }
            }
            List<String> excl = new ArrayList<>();
            boolean punishing = false;
            if (left > 0) {
                excl.add(target);
                left--;
                punishing = true;
            }
            return new Decision(Action.Quote.of(sTheta), evaluated, seen, punishing ? "PENANCE" : "ADHERE", punishing,
                    excl);
        }
    }

    /**
     * The competitive-bot baseline (U18). Round 1 quotes {@code open} (snapped to the grid); afterwards it quotes
     * {@code step} ticks below the LOWEST OTHER firm's quote of the previous round, never below s^N (the floor). It repeats
     * its own last quote when the rivals' quotes were not visible. It has no theta, no memory and no punishment phase.
     */
    public static final class Undercutter implements Agent {
        private final String id;
        private final Scenario sc;
        private final double open;
        private final double floor;
        private final double drop;

        public Undercutter(String id, Scenario sc, double open, int stepTicks) {
            this.id = id;
            this.sc = sc;
            this.floor = PayoffFunctions.nashMargin(sc.market());
            this.open = Math.max(floor, QuoteGrid.snap(sc.market(), open));
            this.drop = stepTicks * sc.market().quoteIncrement();
        }

        @Override public String id() { return id; }

        @Override
        public Decision decide(Observation obs) {
            Observation.PastRound last = obs.last();
            if (last == null) {
                return Decision.simple(Action.Quote.of(open), "OPEN");
            }
            if (!last.quotesVisible() || last.rivalQuotes().isEmpty()) {
                return Decision.simple(Action.Quote.of(last.ownQuote()), "HOLD");
            }
            double low = Double.MAX_VALUE;
            for (double q : last.rivalQuotes().values()) {
                low = Math.min(low, q);
            }
            return Decision.simple(Action.Quote.of(Math.max(floor, QuoteGrid.snap(sc.market(), low - drop))), "UNDERCUT");
        }
    }

    /**
     * The copy-bot control (Track M). Round 1 quotes {@code open} (snapped to the grid, within [s^N, sBar]); afterwards it
     * quotes the other firm's quote of the previous round, never below s^N (with several other firms: the lowest of them). It
     * repeats its own last quote when the rivals' quotes were not visible. No theta, no memory, no punishment, and no
     * disclosed rule, so an LLM seat beside it reads the same prompt as beside an LLM rival.
     */
    public static final class Copier implements Agent {
        private final String id;
        private final Scenario sc;
        private final double open;
        private final double floor;

        public Copier(String id, Scenario sc, double open) {
            this.id = id;
            this.sc = sc;
            this.floor = PayoffFunctions.nashMargin(sc.market());
            this.open = Math.min(sc.market().sBar(), Math.max(floor, QuoteGrid.snap(sc.market(), open)));
        }

        @Override public String id() { return id; }

        @Override
        public Decision decide(Observation obs) {
            Observation.PastRound last = obs.last();
            if (last == null) {
                return Decision.simple(Action.Quote.of(open), "OPEN");
            }
            if (!last.quotesVisible() || last.rivalQuotes().isEmpty()) {
                return Decision.simple(Action.Quote.of(last.ownQuote()), "HOLD");
            }
            double low = Double.MAX_VALUE;
            for (double q : last.rivalQuotes().values()) {
                low = Math.min(low, q);
            }
            return Decision.simple(Action.Quote.of(Math.max(floor, QuoteGrid.snap(sc.market(), low))), "COPY");
        }
    }
}
