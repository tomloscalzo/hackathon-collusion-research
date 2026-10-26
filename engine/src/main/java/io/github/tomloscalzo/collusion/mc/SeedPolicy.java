package io.github.tomloscalzo.collusion.mc;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Name-hashed streams: the seed of a stream is the first 8 bytes of SHA-256(masterSeed + "|" + name). A stream depends
 * only on the master seed and its own name, so adding or removing an agent never perturbs another stream
 * (roster invariance). Stream names used by the engine: demand:&lt;agent&gt;, signal:&lt;observer&gt;, choice:&lt;agent&gt;,
 * detection, horizon. The engine draws a fixed number of values per round from each stream.
 */
public final class SeedPolicy {
    private final long masterSeed;

    public SeedPolicy(long masterSeed) {
        this.masterSeed = masterSeed;
    }

    public long masterSeed() {
        return masterSeed;
    }

    public long streamSeed(String name) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] h = md.digest((masterSeed + "|" + name).getBytes(StandardCharsets.UTF_8));
            long v = 0;
            for (int i = 0; i < 8; i++) {
                v = (v << 8) | (h[i] & 0xffL);
            }
            return v;
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    public RandomStream stream(String name) {
        return new RandomStream(streamSeed(name));
    }

    public static String demand(String agent) { return "demand:" + agent; }
    public static String signal(String observer) { return "signal:" + observer; }
    public static String choice(String agent) { return "choice:" + agent; }
}
