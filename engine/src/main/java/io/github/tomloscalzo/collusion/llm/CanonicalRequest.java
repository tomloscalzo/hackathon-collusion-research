package io.github.tomloscalzo.collusion.llm;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.results.Canonical;

/**
 * Canonical form of a request: sorted-key JSON of every field, including the draw key (the draw index), hashed with
 * SHA-256. This hash is the cache key and the request hash recorded in call records and vignette digests. The optional
 * thinking, topP and topK are written only when set, so a request without them keeps its eight-field text and hash.
 */
public final class CanonicalRequest {
    private CanonicalRequest() {}

    public static ObjectNode json(LlmRequest r) {
        ObjectNode n = Canonical.MAPPER.createObjectNode();
        n.put("provider", r.provider());
        n.put("modelSnapshot", r.modelSnapshot());
        n.put("system", r.system());
        ArrayNode turns = n.putArray("turns");
        for (LlmRequest.Turn t : r.turns()) {
            ObjectNode o = turns.addObject();
            o.put("role", t.role());
            o.put("content", t.content());
        }
        n.put("temperature", r.temperature());
        n.put("maxTokens", r.maxTokens());
        if (r.responseSchema() == null) {
            n.putNull("responseSchema");
        } else {
            n.put("responseSchema", r.responseSchema());
        }
        n.put("drawKey", r.drawKey());
        if (r.thinking() != null) {
            n.put("thinking", r.thinking().booleanValue());
        }
        if (r.topP() != null) {
            n.put("topP", r.topP().doubleValue());
        }
        if (r.topK() != null) {
            n.put("topK", r.topK().intValue());
        }
        return n;
    }

    public static String text(LlmRequest r) {
        return Canonical.text(json(r));
    }

    public static String sha256(LlmRequest r) {
        return Canonical.sha256(text(r));
    }
}
