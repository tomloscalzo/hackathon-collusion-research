package io.github.tomloscalzo.collusion.agents.llm;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.engine.QuoteGrid;
import java.util.ArrayList;
import java.util.List;

/**
 * Unit N1, the numbers of the worked payoff examples in the prompt (option {@code payoff_examples}). ANCHORED (the
 * default, today's prompts) builds the examples around the theory's sustainable collusive level s_P, which tells the
 * reader the answer. NEUTRAL builds them around fixed round half-spreads that do not depend on s_P. Only the numbers
 * change; every sentence stays as it is. FORMULA replaces the examples with the exact profit rule as equations (no
 * worked numbers, no example quote levels); NONE leaves out every numeric example and every formula. Both also drop
 * the audit text's example point (the probability formula in words stays).
 */
public enum PayoffExamples {
    ANCHORED, NEUTRAL, FORMULA, NONE;

    /** True for the modes that print no example prices at all (FORMULA, NONE). */
    public boolean noExamplePrices() {
        return this == FORMULA || this == NONE;
    }

    /** The option value written to params.json (lower case); anchored is never written. */
    public String optionValue() {
        return name().toLowerCase(java.util.Locale.ROOT);
    }

    /** The option key in the grid options cell. */
    public static final String OPTION = "payoff_examples";

    /** NEUTRAL: the equal-quote example points (one place for all neutral constants). */
    public static final double[] EQUAL_QUOTES = {1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00};
    /** NEUTRAL: the others' quote in the undercut example, and the seat's own quote against the war level. */
    public static final double LEVEL = 2.50;
    /** NEUTRAL: the best quote at which the audit text states the investigation probability. */
    public static final double AUDIT_POINT = 2.00;

    private static final double EPS = 1e-9;

    /** The mode of the options object, or null when it has no payoff_examples (= anchored). */
    public static PayoffExamples fromOptions(JsonNode options) {
        if (options == null || !options.has(OPTION)) {
            return null;
        }
        JsonNode n = options.get(OPTION);
        String v = n.isTextual() ? n.asText() : "";
        return switch (v) {
            case "anchored" -> ANCHORED;
            case "neutral" -> NEUTRAL;
            case "formula" -> FORMULA;
            case "none" -> NONE;
            default -> throw new IllegalArgumentException("--options " + OPTION
                    + " must be \"anchored\", \"neutral\", \"formula\" or \"none\", not " + n);
        };
    }

    /**
     * The equal-quote points: each constant that lies within [s0, sBar], snapped to the quote grid, duplicates dropped.
     * (A constant outside the market's range is left out, not clamped, so no end point is repeated.)
     */
    public static List<Double> equalQuotes(MarketParams m) {
        List<Double> out = new ArrayList<>();
        for (double x : EQUAL_QUOTES) {
            if (x < m.s0() - EPS || x > m.sBar() + EPS) {
                continue;
            }
            double g = QuoteGrid.snap(m, x);
            if (!out.contains(g)) {
                out.add(g);
            }
        }
        return out;
    }

    /** A single neutral point, snapped to the grid; outside [s0, sBar] it is the nearest in-range grid point. */
    public static double point(MarketParams m, double x) {
        return QuoteGrid.snap(m, x);
    }
}
