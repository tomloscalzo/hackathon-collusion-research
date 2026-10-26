package io.github.tomloscalzo.collusion.llm;

import java.util.List;

/**
 * One chat completion request. modelSnapshot is the pinned model id sent to the server; responseSchema is the JSON schema
 * text of the expected reply (null for free text); drawKey names the draw (run seed, round or row, attempt) and is part
 * of the canonical hash, so two draws with an identical prompt are distinct cache entries and, on a real server, get
 * distinct per-request seeds.
 *
 * <p>thinking, topP and topK are optional (null = unset; interface proposal v5, C1, C2, D1). thinking is the hybrid
 * models' chat-template switch, sent as {@code chat_template_kwargs.enable_thinking} (Qwen3 thinks by default, so false
 * must be sent explicitly); topP and topK are sent as top_p and top_k. Each enters the canonical request, and so the
 * hash, only when set: with all three unset the request, its hash and its wire body are those of the eight-field form.
 */
public record LlmRequest(String provider, String modelSnapshot, String system, List<Turn> turns, double temperature,
                         int maxTokens, String responseSchema, String drawKey, Boolean thinking, Double topP, Integer topK) {
    public LlmRequest {
        turns = List.copyOf(turns);
        if (topP != null && !(topP > 0 && topP <= 1)) {
            throw new IllegalArgumentException("topP must be in (0, 1]: " + topP);
        }
        if (topK != null && topK < 1 && topK != -1) {
            throw new IllegalArgumentException("topK must be >= 1, or -1 for no limit: " + topK);
        }
    }

    /** The eight-field request of Track S: thinking, topP and topK unset. */
    public LlmRequest(String provider, String modelSnapshot, String system, List<Turn> turns, double temperature,
                      int maxTokens, String responseSchema, String drawKey) {
        this(provider, modelSnapshot, system, turns, temperature, maxTokens, responseSchema, drawKey, null, null, null);
    }

    /** role is "user" or "assistant". */
    public record Turn(String role, String content) {}
}
