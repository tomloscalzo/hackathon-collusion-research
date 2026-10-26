package io.github.tomloscalzo.collusion.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The append-only JSONL cache format shared by CachingLlmClient and ReplayLlmClient: one sorted-key object per line. The
 * optional reasoning and reasoningTokens are written only when non-null, so a reply without reasoning keeps the
 * seven-key line, and a line without them loads with both null.
 */
final class CacheFile {
    private CacheFile() {}

    static Map<String, LlmResponse> load(Path file) {
        Map<String, LlmResponse> m = new ConcurrentHashMap<>();
        if (!Files.isRegularFile(file)) {
            return m;
        }
        try {
            List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
            int no = 0;
            for (String line : lines) {
                no++;
                if (line.isBlank()) {
                    continue;
                }
                JsonNode n;
                try {
                    n = Canonical.MAPPER.readTree(line);
                } catch (IOException e) {
                    throw new LlmException("cache " + file + " line " + no + " is not valid JSON", e);
                }
                if (!n.hasNonNull("hash") || !n.hasNonNull("text")) {
                    throw new LlmException("cache " + file + " line " + no + " lacks hash or text");
                }
                m.putIfAbsent(n.get("hash").asText(), new LlmResponse(n.get("text").asText(), n.path("tokensIn").asInt(),
                        n.path("tokensOut").asInt(), 0L, true, n.get("hash").asText(), n.path("finishReason").asText(""),
                        n.hasNonNull("reasoning") ? n.get("reasoning").asText() : null,
                        n.hasNonNull("reasoningTokens") ? Integer.valueOf(n.get("reasoningTokens").asInt()) : null));
            }
        } catch (IOException e) {
            throw new LlmException("cannot read cache " + file, e);
        }
        return m;
    }

    static String line(LlmRequest req, LlmResponse r) {
        ObjectNode n = Canonical.MAPPER.createObjectNode();
        n.put("hash", r.requestHash());
        n.put("text", r.text());
        n.put("tokensIn", r.tokensIn());
        n.put("tokensOut", r.tokensOut());
        n.put("finishReason", r.finishReason());
        n.put("modelSnapshot", req.modelSnapshot());
        n.put("drawKey", req.drawKey());
        if (r.reasoning() != null) {
            n.put("reasoning", r.reasoning());
        }
        if (r.reasoningTokens() != null) {
            n.put("reasoningTokens", r.reasoningTokens().intValue());
        }
        return Canonical.text(n);
    }
}
