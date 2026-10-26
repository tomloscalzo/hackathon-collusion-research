package io.github.tomloscalzo.collusion.mc;

import java.util.SplittableRandom;

/** A named random stream. Gaussian draws always consume exactly two uniforms so that draw counts per round are fixed. */
public final class RandomStream {
    private final SplittableRandom rng;

    RandomStream(long seed) {
        this.rng = new SplittableRandom(seed);
    }

    /** Uniform on [0, 1). */
    public double nextDouble() {
        return rng.nextDouble();
    }

    /** Standard normal by Box-Muller (cosine branch only); consumes two uniforms. */
    public double nextGaussian() {
        double u1 = 1.0 - rng.nextDouble();
        double u2 = rng.nextDouble();
        return StrictMath.sqrt(-2.0 * StrictMath.log(u1)) * StrictMath.cos(2.0 * StrictMath.PI * u2);
    }
}
