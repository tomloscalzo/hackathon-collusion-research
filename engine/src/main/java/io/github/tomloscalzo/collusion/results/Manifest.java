package io.github.tomloscalzo.collusion.results;

import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.TreeMap;

/**
 * Run manifest written next to every sweep's outputs (sorted-key JSON): the git commit of the working tree the batch was
 * started in, the master seed, hashes of the sweep file and of every base scenario, the thread count and the wall time.
 * Times and thread counts never influence results; they are recorded for provenance only. M4 adds the optional llm section.
 */
public record Manifest(String tool, String gitCommit, String sweepId, long masterSeed, String sweepSha256,
                       Map<String, String> scenarioHashes, int runsPerCell, int threads, int cellsTotal, int cellsRun,
                       int cellsSkipped, long wallTimeMs, String startedAt, String javaVersion,
                       Map<String, String> options, Map<String, Object> llm) {
    public Manifest {
        scenarioHashes = new TreeMap<>(scenarioHashes);
        options = new TreeMap<>(options);
        llm = new TreeMap<>(llm == null ? Map.of() : llm);
    }

    /** A manifest without an LLM section (M3 batches). */
    public Manifest(String tool, String gitCommit, String sweepId, long masterSeed, String sweepSha256,
                    Map<String, String> scenarioHashes, int runsPerCell, int threads, int cellsTotal, int cellsRun,
                    int cellsSkipped, long wallTimeMs, String startedAt, String javaVersion,
                    Map<String, String> options) {
        this(tool, gitCommit, sweepId, masterSeed, sweepSha256, scenarioHashes, runsPerCell, threads, cellsTotal, cellsRun,
                cellsSkipped, wallTimeMs, startedAt, javaVersion, options, Map.of());
    }

    /**
     * M4: the llm section holds provider and modelSnapshot (the served model name; together the model identity), modelId,
     * modelRevision and modelVariant (parsed from the served name, null outside the deploy recipe's convention),
     * baseUrlHost, temperature, maxTokens, templateHashes, paraphraseItemHashes (SHA-256 of each frozen prompt file and
     * item), analysisScriptSha256, budget and call counts. It is omitted from the JSON when empty so M3 manifests are
     * unchanged.
     */
    public ObjectNode toJson() {
        ObjectNode n = Canonical.MAPPER.valueToTree(this);
        if (llm.isEmpty()) {
            n.remove("llm");
        }
        return n;
    }

    public void write(Path file) throws IOException {
        Files.writeString(file, Canonical.text(toJson()) + "\n", StandardCharsets.UTF_8);
    }

    /** git rev-parse HEAD in the working directory, or "unknown" when git or a repository is unavailable. */
    public static String currentGitCommit() {
        try {
            Process p = new ProcessBuilder("git", "rev-parse", "HEAD").redirectErrorStream(false).start();
            String out = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8).trim();
            p.getErrorStream().readAllBytes();
            if (!p.waitFor(10, java.util.concurrent.TimeUnit.SECONDS)) {
                p.destroyForcibly();
                return "unknown";
            }
            return p.exitValue() == 0 && out.matches("[0-9a-f]{7,64}") ? out : "unknown";
        } catch (IOException e) {
            return "unknown";
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return "unknown";
        }
    }
}
