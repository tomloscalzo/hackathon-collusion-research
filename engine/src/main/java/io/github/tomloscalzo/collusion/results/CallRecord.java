package io.github.tomloscalzo.collusion.results;

import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.function.Consumer;

/**
 * One LLM call as logged beside the runs (JSONL, sorted keys). kind is "game" or "vignette"; runKey names the run or the
 * vignette pass; index is the round or row (0-based row index); attempt is 0 for the first call and 1 for the repair.
 * parseStatus is OK, REPAIR_NEEDED (first attempt unparseable, a repair follows), REFUSED or PARSE_FAIL.
 * clamp (optional, only when the context clamp bound on this call): callType, attempt, estPromptTokens,
 * requestedMaxTokens, grantedMaxTokens, skipped, window, margin, minTokens. latencyMs is provenance only and never enters a digest.
 */
public record CallRecord(String kind, String runKey, int index, int attempt, String requestHash, boolean cached,
                         int tokensIn, int tokensOut, long latencyMs, String parseStatus,
                         @com.fasterxml.jackson.annotation.JsonInclude(com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL)
                         java.util.Map<String, Object> clamp) {
    /** Without a clamp object (every record unless the context clamp bound; then the line has no "clamp" key). */
    public CallRecord(String kind, String runKey, int index, int attempt, String requestHash, boolean cached,
                      int tokensIn, int tokensOut, long latencyMs, String parseStatus) {
        this(kind, runKey, index, attempt, requestHash, cached, tokensIn, tokensOut, latencyMs, parseStatus, null);
    }

    /** The same record with the context clamp's fields (camelCase keys: callType, estPromptTokens, ...). */
    public CallRecord withClamp(java.util.Map<String, Object> c) {
        return new CallRecord(kind, runKey, index, attempt, requestHash, cached, tokensIn, tokensOut, latencyMs, parseStatus, c);
    }

    public ObjectNode toJson() {
        return Canonical.MAPPER.valueToTree(this);
    }

    /** Appends CallRecords to a JSONL file; usable as a Consumer. */
    public static final class Log implements Consumer<CallRecord> {
        private final Path file;

        public Log(Path file) {
            this.file = file;
        }

        @Override
        public synchronized void accept(CallRecord r) {
            try (Writer w = Files.newBufferedWriter(file, StandardCharsets.UTF_8, StandardOpenOption.CREATE,
                    StandardOpenOption.APPEND)) {
                w.write(Canonical.text(r.toJson()));
                w.write('\n');
            } catch (IOException e) {
                throw new IllegalStateException("cannot write call log " + file, e);
            }
        }
    }
}
