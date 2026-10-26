package io.github.tomloscalzo.collusion.llm;

/** A chat completion backend (HTTP client, cache layer, replay layer). Implementations must be thread safe. */
public interface LlmClient {
    LlmResponse complete(LlmRequest request);
}
