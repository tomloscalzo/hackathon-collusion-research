package io.github.tomloscalzo.collusion.llm;

import java.util.concurrent.atomic.AtomicLong;

/**
 * Run-level token budget (T9). A run reserves an estimate once, atomically, before its first call; every call settles
 * its actual tokens against that reservation; closing the reservation returns the unspent part. Reservation and
 * settlement are never both applied per call. A settle that exceeds the run's own reservation is refused.
 */
public final class Budget {
    private final long limit;
    private final AtomicLong reserved = new AtomicLong();
    private final AtomicLong used = new AtomicLong();

    public Budget(long limitTokens) {
        if (limitTokens <= 0) {
            throw new IllegalArgumentException("a budget needs a positive token limit");
        }
        this.limit = limitTokens;
    }

    public long limit() {
        return limit;
    }

    /** Tokens spent so far (settled). */
    public long used() {
        return used.get();
    }

    /** Tokens currently held by open reservations (including their spent part). */
    public long reserved() {
        return reserved.get();
    }

    public Reservation reserve(long tokens) {
        if (tokens <= 0) {
            throw new IllegalArgumentException("reservation must be positive");
        }
        while (true) {
            long cur = reserved.get();
            if (cur + tokens > limit) {
                throw new LlmException.BudgetExceeded("budget " + limit + " tokens: cannot reserve " + tokens
                        + " (already reserved " + cur + ")");
            }
            if (reserved.compareAndSet(cur, cur + tokens)) {
                return new Reservation(tokens);
            }
        }
    }

    public final class Reservation implements AutoCloseable {
        private final long amount;
        private final AtomicLong spent = new AtomicLong();
        private volatile boolean closed;

        private Reservation(long amount) {
            this.amount = amount;
        }

        public void settle(long actualTokens) {
            if (closed) {
                throw new LlmException("reservation already closed");
            }
            long s = spent.addAndGet(actualTokens);
            used.addAndGet(actualTokens);
            if (s > amount) {
                throw new LlmException.BudgetExceeded("run reservation of " + amount + " tokens exceeded (" + s + ")");
            }
        }

        public long spent() {
            return spent.get();
        }

        public long remaining() {
            return amount - spent.get();
        }

        /** Releases the unspent part of the reservation back to the budget (idempotent). */
        @Override
        public synchronized void close() {
            if (!closed) {
                closed = true;
                // the spent part stays counted: reserved() = open reservations + tokens already spent
                reserved.addAndGet(-(amount - spent.get()));
            }
        }
    }
}
