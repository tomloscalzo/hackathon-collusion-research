package io.github.tomloscalzo.collusion.llm;

import java.util.function.LongSupplier;

/** Simple token bucket: ratePerSecond tokens are added per second up to burst; acquire() blocks for one token. */
public final class RateLimiter {
    private final double ratePerSecond;
    private final double burst;
    private final LongSupplier nanoClock;
    private double tokens;
    private long last;

    public RateLimiter(double ratePerSecond, int burst) {
        this(ratePerSecond, burst, System::nanoTime);
    }

    public RateLimiter(double ratePerSecond, int burst, LongSupplier nanoClock) {
        if (ratePerSecond <= 0 || burst < 1) {
            throw new IllegalArgumentException("ratePerSecond > 0 and burst >= 1 required");
        }
        this.ratePerSecond = ratePerSecond;
        this.burst = burst;
        this.nanoClock = nanoClock;
        this.tokens = burst;
        this.last = nanoClock.getAsLong();
    }

    private void refill() {
        long now = nanoClock.getAsLong();
        tokens = Math.min(burst, tokens + (now - last) / 1e9 * ratePerSecond);
        last = now;
    }

    public synchronized boolean tryAcquire() {
        refill();
        if (tokens >= 1.0) {
            tokens -= 1.0;
            return true;
        }
        return false;
    }

    /** Blocks (sleeping) until a token is available. */
    public void acquire() {
        while (true) {
            long waitNanos;
            synchronized (this) {
                refill();
                if (tokens >= 1.0) {
                    tokens -= 1.0;
                    return;
                }
                waitNanos = (long) ((1.0 - tokens) / ratePerSecond * 1e9);
            }
            try {
                Thread.sleep(Math.max(1L, waitNanos / 1_000_000L));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new LlmException("interrupted while waiting for the rate limiter", e);
            }
        }
    }
}
