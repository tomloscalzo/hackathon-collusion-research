package io.github.tomloscalzo.collusion.llm;

import java.nio.file.Path;
import java.util.Map;

/** Serves completions from a cache file only; a request with no entry throws LlmException.CacheMiss (no network). */
public final class ReplayLlmClient implements LlmClient {
    private final Map<String, LlmResponse> entries;

    public ReplayLlmClient(Path cacheFile) {
        this.entries = CacheFile.load(cacheFile);
    }

    public int size() {
        return entries.size();
    }

    @Override
    public LlmResponse complete(LlmRequest request) {
        String hash = CanonicalRequest.sha256(request);
        LlmResponse r = entries.get(hash);
        if (r == null) {
            throw new LlmException.CacheMiss("replay: no cache entry for request " + hash + " (drawKey "
                    + request.drawKey() + ")");
        }
        return r.asCached();
    }
}
