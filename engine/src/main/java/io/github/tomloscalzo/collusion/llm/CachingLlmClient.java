package io.github.tomloscalzo.collusion.llm;

import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Append-only JSONL cache keyed by the canonical request hash (draw index included). A hit returns the stored completion
 * text byte-identically and makes no call; a miss calls the delegate and appends one line. LLM reproducibility rests on
 * this cache, never on the provider.
 */
public final class CachingLlmClient implements LlmClient {
    private final LlmClient delegate;
    private final Path file;
    private final Map<String, LlmResponse> entries;
    private final AtomicLong hits = new AtomicLong();
    private final AtomicLong misses = new AtomicLong();

    public CachingLlmClient(LlmClient delegate, Path file) {
        this.delegate = delegate;
        this.file = file;
        this.entries = CacheFile.load(file);
    }

    public long hits() {
        return hits.get();
    }

    public long misses() {
        return misses.get();
    }

    public int size() {
        return entries.size();
    }

    @Override
    public LlmResponse complete(LlmRequest request) {
        String hash = CanonicalRequest.sha256(request);
        LlmResponse cached = entries.get(hash);
        if (cached != null) {
            hits.incrementAndGet();
            return cached.asCached();
        }
        misses.incrementAndGet();
        LlmResponse fresh = delegate.complete(request);
        LlmResponse stored = new LlmResponse(fresh.text(), fresh.tokensIn(), fresh.tokensOut(), fresh.latencyMs(), false,
                hash, fresh.finishReason(), fresh.reasoning(), fresh.reasoningTokens());
        synchronized (this) {
            if (entries.putIfAbsent(hash, stored) == null) {
                try (Writer w = Files.newBufferedWriter(file, StandardCharsets.UTF_8, StandardOpenOption.CREATE,
                        StandardOpenOption.APPEND)) {
                    w.write(CacheFile.line(request, stored));
                    w.write('\n');
                } catch (IOException e) {
                    throw new LlmException("cannot append to cache " + file, e);
                }
            }
        }
        return stored;
    }
}
