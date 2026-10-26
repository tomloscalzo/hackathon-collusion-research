package io.github.tomloscalzo.collusion.core.model;

public sealed interface Horizon permits Horizon.Random, Horizon.Known {
    /** Random termination with per-period hazard h. */
    record Random(double h) implements Horizon {}

    /** Known finite horizon of the given number of periods. */
    record Known(int periods) implements Horizon {}
}
