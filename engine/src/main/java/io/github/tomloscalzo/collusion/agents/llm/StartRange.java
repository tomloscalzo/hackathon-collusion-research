package io.github.tomloscalzo.collusion.agents.llm;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.core.model.MarketParams;

/**
 * Unit U17, the 5-tick start control arm (option {@code start_ticks}, default off): in round 1 only, a quote must lie in
 * [s0, s0 + ticks * quoteIncrement], the competitive level plus at most {@code ticks} ticks. A round-1 quote outside is
 * handled as an invalid quote: one repair, then imputed (s0), logged. The bounds come from the market and the option, not
 * from constants. From round 2 on nothing changes.
 */
public record StartRange(int ticks) {
    /** The option key in the grid options cell. */
    public static final String OPTION = "start_ticks";
    private static final double EPS = 1e-9;

    public StartRange {
        if (ticks < 1) {
            throw new IllegalArgumentException("--options " + OPTION + " must be a positive integer, not " + ticks);
        }
    }

    /** The range of the options object, or null when it has no start_ticks. */
    public static StartRange fromOptions(JsonNode options) {
        if (options == null || !options.has(OPTION)) {
            return null;
        }
        JsonNode n = options.get(OPTION);
        if (!n.isIntegralNumber()) {
            throw new IllegalArgumentException("--options " + OPTION + " must be a positive integer: " + n);
        }
        return new StartRange(n.asInt());
    }

    public double lo(MarketParams m) {
        return m.s0();
    }

    public double hi(MarketParams m) {
        return m.s0() + ticks * m.quoteIncrement();
    }

    /** True when the raw quote may be played in round 1. */
    public boolean allows(MarketParams m, double quote) {
        return quote >= lo(m) - EPS && quote <= hi(m) + EPS;
    }
}
