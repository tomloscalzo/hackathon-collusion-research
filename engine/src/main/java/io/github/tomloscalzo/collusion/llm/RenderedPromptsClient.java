package io.github.tomloscalzo.collusion.llm;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.HashSet;
import java.util.Set;

/**
 * A pure side output (Track S, U4): writes every request's rendered prompt, the system prompt and each turn exactly as
 * sent, with the SHA-256 of each, to a JSONL file (one sorted-key line per distinct request hash), so a shard's prompts
 * can be reconstructed downstream. It forwards the request untouched and returns the inner response unchanged, so it
 * cannot change a request, a cache key or a digest; a write failure is remembered ({@link #error()}), never thrown.
 * Line keys: hash (the canonical request hash, the call log's requestHash and the cache key), drawKey, modelSnapshot,
 * system, systemSha256, turns [{role, content, sha256}]. A request already in the file (a rerun, a cache hit) is not
 * written twice.
 */
public final class RenderedPromptsClient implements LlmClient {
    private final LlmClient inner;
    private final Path file;
    private final Set<String> seen = new HashSet<>();
    private volatile IOException error;

    public RenderedPromptsClient(LlmClient inner, Path file) {
        this.inner = inner;
        this.file = file;
        try {
            if (Files.isRegularFile(file)) {
                for (String l : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                    if (!l.isBlank()) {
                        seen.add(Canonical.MAPPER.readTree(l).path("hash").asText());
                    }
                }
            }
        } catch (IOException | RuntimeException e) {
            error = e instanceof IOException io ? io : new IOException(e);
        }
    }

    @Override
    public LlmResponse complete(LlmRequest request) {
        record(request);
        return inner.complete(request);
    }

    /** The first write error, or null. */
    public IOException error() {
        return error;
    }

    static ObjectNode line(LlmRequest r) {
        ObjectNode n = Canonical.MAPPER.createObjectNode();
        n.put("hash", CanonicalRequest.sha256(r));
        n.put("drawKey", r.drawKey());
        n.put("modelSnapshot", r.modelSnapshot());
        n.put("system", r.system());
        n.put("systemSha256", Canonical.sha256(r.system()));
        ArrayNode turns = n.putArray("turns");
        for (LlmRequest.Turn t : r.turns()) {
            ObjectNode tn = turns.addObject();
            tn.put("role", t.role());
            tn.put("content", t.content());
            tn.put("sha256", Canonical.sha256(t.content()));
        }
        return n;
    }

    private synchronized void record(LlmRequest request) {
        try {
            ObjectNode n = line(request);
            if (!seen.add(n.get("hash").asText())) {
                return;
            }
            try (Writer w = Files.newBufferedWriter(file, StandardCharsets.UTF_8, StandardOpenOption.CREATE,
                    StandardOpenOption.APPEND)) {
                w.write(Canonical.text(n));
                w.write('\n');
            }
        } catch (IOException | RuntimeException e) {
            if (error == null) {
                error = e instanceof IOException io ? io : new IOException(e);
            }
        }
    }
}
