package io.github.tomloscalzo.collusion.llm;

/**
 * A completion. cached is true when it came from the cache (no call was made). reasoning is the server's separate
 * reasoning text (vLLM's reasoning_content, or reasoning), null when the reply carries none; reasoningTokens is
 * usage.completion_tokens_details.reasoning_tokens when the server reports it, else null (interface proposal v5, D2).
 * text stays the answer only: no prompt code reads reasoning.
 */
public record LlmResponse(String text, int tokensIn, int tokensOut, long latencyMs, boolean cached, String requestHash,
                          String finishReason, String reasoning, Integer reasoningTokens) {
    /** A completion without reasoning. */
    public LlmResponse(String text, int tokensIn, int tokensOut, long latencyMs, boolean cached, String requestHash,
                       String finishReason) {
        this(text, tokensIn, tokensOut, latencyMs, cached, requestHash, finishReason, null, null);
    }

    public LlmResponse asCached() {
        return new LlmResponse(text, tokensIn, tokensOut, 0L, true, requestHash, finishReason, reasoning, reasoningTokens);
    }
}
