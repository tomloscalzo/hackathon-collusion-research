package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Golden replay digests of scripted runs (the prompt-independent half of INTERFACES finding F24). A replayDigest hashes
 * the rounds JSON, so it moves when the round-record shape, a stream name or draw order, settlement, detection or the
 * printed numerics change, which is exactly what would make every cached LLM run fail to replay (INTERFACES i.0 items
 * 6, 7, 9 and 11). The values were produced by `run --scenario ... --seed ...` on JDK 17 on 2026-10-23.
 *
 * If an intended engine change moves a digest: regenerate the value with the command in each case, and say in the commit
 * message that phase-1 replay digests change (after the first real LLM call this also needs owner approval). The prompt
 * half of F24 (byte-freezing the rendered requests) is enforced at freeze time by testing/preflight.py, not here, so that
 * deliberate prompt edits before the freeze do not break this test.
 */
class GoldenDigestTest {
    static String digest(Path dir, String... kv) throws Exception {
        Map<String, String> o = new TreeMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            o.put(kv[i], kv[i + 1]);
        }
        Path out = dir.resolve("golden-" + o.hashCode() + ".jsonl");
        o.put("out", out.toString());
        Main.run(o);
        return Canonical.MAPPER.readTree(Files.readAllLines(out).get(0)).get("replayDigest").asText();
    }

    @Test
    void scriptedTriggerPair(@TempDir Path dir) throws Exception {
        // run --scenario scenarios/engine-trigger-pair.yaml --seed 42   (15 rounds, HORIZON)
        assertThat(digest(dir, "scenario", "scenarios/engine-trigger-pair.yaml", "seed", "42"))
                .isEqualTo("f9297ab7e41b52b4391bbd4da29f9e059d19fd84ec4e4280e7aca61002e362c0");
    }

    @Test
    void ripeGameWithScriptedSeats(@TempDir Path dir) throws Exception {
        // run --scenario scenarios/ripe-game.yaml --seed 7 --seat TIT_FOR_TAT --seat-config theta=0.546   (10 rounds, EVIDENCE)
        assertThat(digest(dir, "scenario", "scenarios/ripe-game.yaml", "seed", "7", "seat", "TIT_FOR_TAT", "seat-config",
                "theta=0.546")).isEqualTo("3395f745ac723e293b40491cd24659f8a84e946ee2ea969259339c7b3500e698");
        // ... --seat TRIGGER_K --seat-config theta=0.546,k=-1,tolerance=0   (10 rounds, EVIDENCE)
        assertThat(digest(dir, "scenario", "scenarios/ripe-game.yaml", "seed", "7", "seat", "TRIGGER_K", "seat-config",
                "theta=0.546,k=-1,tolerance=0")).isEqualTo("e3e6ee8af9abefd25d37018c1c2990bbcd4310e6e304e78175f4b6876e01ed7d");
    }
}
