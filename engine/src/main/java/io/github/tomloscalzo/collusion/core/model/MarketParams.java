package io.github.tomloscalzo.collusion.core.model;

/** Market primitives. tick is the economic tick iota (may be 0); quoteIncrement is the engine minimum move (unused by Layer A). */
public record MarketParams(int n, double phi, double s0, double sBar, double q0, double tick, double quoteIncrement) {
    public MarketParams withN(int v) { return new MarketParams(v, phi, s0, sBar, q0, tick, quoteIncrement); }
    public MarketParams withPhi(double v) { return new MarketParams(n, v, s0, sBar, q0, tick, quoteIncrement); }
    public MarketParams withS0(double v) { return new MarketParams(n, phi, v, sBar, q0, tick, quoteIncrement); }
    public MarketParams withSBar(double v) { return new MarketParams(n, phi, s0, v, q0, tick, quoteIncrement); }
    public MarketParams withTick(double v) { return new MarketParams(n, phi, s0, sBar, q0, v, quoteIncrement); }
}
