package io.github.tomloscalzo.collusion.agents;

import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.engine.Action;
import io.github.tomloscalzo.collusion.engine.Decision;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.mc.RandomStream;

/**
 * Reference seat (spec 5.8): each round an independent uniform draw on the quote grid s0 + j * quoteIncrement between
 * s0 and the monopoly margin sM (both ends included). One uniform per round from the stream noise:&lt;id&gt;.
 */
public final class NoiseAgent implements Agent {
    private final String id;
    private final double s0;
    private final double inc;
    private final int top;
    private final RandomStream stream;

    public NoiseAgent(String id, Scenario sc, RandomStream stream) {
        this.id = id;
        MarketParams m = sc.market();
        this.s0 = m.s0();
        this.inc = m.quoteIncrement();
        double sM = Math.min(PayoffFunctions.monopolyMargin(m), m.sBar());
        this.top = (int) StrictMath.floor((sM - s0) / inc + 1e-9);
        this.stream = stream;
    }

    public static String streamName(String agentId) {
        return "noise:" + agentId;
    }

    @Override public String id() { return id; }

    @Override
    public Decision decide(Observation obs) {
        int j = Math.min(top, (int) StrictMath.floor(stream.nextDouble() * (top + 1)));
        return Decision.simple(Action.Quote.of(s0 + j * inc), "NOISE");
    }
}
