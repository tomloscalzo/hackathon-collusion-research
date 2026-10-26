package io.github.tomloscalzo.collusion.core.model;

public record Aggregates(double qCollective, double qTargeted, double dBarU, double sumIRP, double punishCost) {
    public Aggregates withQCollective(double v) { return new Aggregates(v, qTargeted, dBarU, sumIRP, punishCost); }
    public Aggregates withQTargeted(double v) { return new Aggregates(qCollective, v, dBarU, sumIRP, punishCost); }
    public Aggregates withSumIRP(double v) { return new Aggregates(qCollective, qTargeted, dBarU, v, punishCost); }
}
