package io.github.tomloscalzo.collusion.core.model;

/** punishmentLength: number of punishment periods k; -1 means infinite (grim). */
public record Scenario(String id, MarketParams market, EnforcementParams enforcement, TimeParams time,
                       Aggregates aggregates, int punishmentLength, PunishmentForm punishment,
                       PunishmentLevel punishmentLevel, double tau) {
    public boolean infinitePunishment() { return punishmentLength < 0; }

    /** Effective discount factor (spec 2.6). */
    public double delta() { return time.effectiveDelta(); }

    public Scenario withMarket(MarketParams v) { return new Scenario(id, v, enforcement, time, aggregates, punishmentLength, punishment, punishmentLevel, tau); }
    public Scenario withEnforcement(EnforcementParams v) { return new Scenario(id, market, v, time, aggregates, punishmentLength, punishment, punishmentLevel, tau); }
    public Scenario withTime(TimeParams v) { return new Scenario(id, market, enforcement, v, aggregates, punishmentLength, punishment, punishmentLevel, tau); }
    public Scenario withAggregates(Aggregates v) { return new Scenario(id, market, enforcement, time, v, punishmentLength, punishment, punishmentLevel, tau); }
    public Scenario withPunishmentLength(int v) { return new Scenario(id, market, enforcement, time, aggregates, v, punishment, punishmentLevel, tau); }
    public Scenario withPunishment(PunishmentForm v) { return new Scenario(id, market, enforcement, time, aggregates, punishmentLength, v, punishmentLevel, tau); }
    public Scenario withPunishmentLevel(PunishmentLevel v) { return new Scenario(id, market, enforcement, time, aggregates, punishmentLength, punishment, v, tau); }
}
