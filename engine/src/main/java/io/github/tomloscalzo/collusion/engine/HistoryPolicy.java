package io.github.tomloscalzo.collusion.engine;

/** Number of past rounds shown to an agent; window &lt;= 0 means the full history. */
public record HistoryPolicy(int window) {
    public static HistoryPolicy defaults() {
        return new HistoryPolicy(10);
    }
}
