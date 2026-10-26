package io.github.tomloscalzo.collusion.agents.llm;

/**
 * Model-side settings of a run: provider label, pinned model snapshot, temperature (fixed per model) and token cap; and
 * the optional thinking switch, top_p and top_k (null = unset, today's requests; interface proposal v5, C1, C2), copied
 * into every request of the run.
 */
public record LlmSettings(String provider, String modelSnapshot, double temperature, int maxTokens, Boolean thinking,
                          Double topP, Integer topK) {
    public LlmSettings {
        if (modelSnapshot == null || modelSnapshot.isBlank()) {
            throw new IllegalArgumentException("a pinned model snapshot id is required");
        }
        if (temperature < 0 || maxTokens < 1) {
            throw new IllegalArgumentException("temperature >= 0 and maxTokens >= 1 required");
        }
        if (topP != null && !(topP > 0 && topP <= 1)) {
            throw new IllegalArgumentException("--top-p must be in (0, 1]: " + topP);
        }
        if (topK != null && topK < 1 && topK != -1) {
            throw new IllegalArgumentException("--top-k must be >= 1, or -1 for no limit: " + topK);
        }
    }

    /** Settings with thinking, topP and topK unset. */
    public LlmSettings(String provider, String modelSnapshot, double temperature, int maxTokens) {
        this(provider, modelSnapshot, temperature, maxTokens, null, null, null);
    }

    public static LlmSettings of(String model) {
        return new LlmSettings("openai-compatible", model, 0.7, 400);
    }
}
