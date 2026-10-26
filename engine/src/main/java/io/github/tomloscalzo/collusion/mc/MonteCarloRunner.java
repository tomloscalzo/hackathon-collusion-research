package io.github.tomloscalzo.collusion.mc;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.IntFunction;

/**
 * Bounded thread pool for independent jobs. Job i must depend only on i (its seed comes from the design, never from
 * the thread or the scheduling order); results come back in index order so every reduction downstream is sequential and
 * the output is identical for any thread count.
 */
public final class MonteCarloRunner implements AutoCloseable {
    private final ExecutorService pool;
    private final int threads;

    public MonteCarloRunner(int threads) {
        if (threads < 1) {
            throw new IllegalArgumentException("threads must be >= 1");
        }
        this.threads = threads;
        AtomicInteger id = new AtomicInteger();
        this.pool = Executors.newFixedThreadPool(threads, r -> {
            Thread t = new Thread(r, "mc-worker-" + id.incrementAndGet());
            t.setDaemon(true);
            return t;
        });
    }

    public int threads() {
        return threads;
    }

    /** Runs job(0..n-1) on the pool and returns the results in index order; the first failure is rethrown. */
    public <T> List<T> map(int n, IntFunction<T> job) {
        if (n == 0) {
            return new ArrayList<>();
        }
        @SuppressWarnings("unchecked")
        T[] out = (T[]) new Object[n];
        int chunk = Math.max(1, Math.min(64, n / (threads * 8)));
        List<Future<?>> fs = new ArrayList<>();
        for (int from = 0; from < n; from += chunk) {
            final int a = from;
            final int b = Math.min(n, from + chunk);
            fs.add(pool.submit(() -> {
                for (int i = a; i < b; i++) {
                    out[i] = job.apply(i);
                }
            }));
        }
        try {
            for (Future<?> f : fs) {
                f.get();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        } catch (ExecutionException e) {
            fs.forEach(f -> f.cancel(true));
            Throwable c = e.getCause();
            throw c instanceof RuntimeException re ? re : new IllegalStateException(c);
        }
        List<T> res = new ArrayList<>(n);
        for (T t : out) {
            res.add(t);
        }
        return res;
    }

    @Override
    public void close() {
        pool.shutdownNow();
    }
}
