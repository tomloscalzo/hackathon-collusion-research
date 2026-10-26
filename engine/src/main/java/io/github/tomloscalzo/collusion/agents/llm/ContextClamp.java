package io.github.tomloscalzo.collusion.agents.llm;

import io.github.tomloscalzo.collusion.llm.LlmRequest;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * The context clamp (unit U2, owner-approved LLM-client change; off by default). The server refuses a request whose prompt
 * plus max_tokens exceeds its context window (HTTP 400, a lost game). Before each call the agent estimates the prompt
 * conservatively; when {@code prompt + max_tokens > window - margin} the call's max_tokens is lowered to
 * {@code window - margin - prompt}; when fewer than {@code min(minTokens, the call's own max_tokens)} would remain the call is not sent and the round is
 * recorded as truncated and imputed (the C12b.3 path). Every time the clamp binds, {@link Info} is logged (a
 * {@code context_clamp} event in events.jsonl and the call record's {@code clamp} object). Nothing is clamped, and no
 * request, hash or record changes, when the clamp is off (the agent holds none).
 *
 * <p>The estimate is {@code ceil(chars / charsPerToken)} over the system prompt and every turn, plus
 * {@code PER_MESSAGE} tokens per message and {@code BASE} for the chat template; charsPerToken defaults to 3.0 (the
 * pessimistic end of the owner's 3 to 4 characters a token). The response schema is not counted (the margin covers it).
 */
public record ContextClamp(int window, int margin, int minTokens, double charsPerToken, String trial, String arm) {
    public static final int DEFAULT_WINDOW = 16384;
    public static final int DEFAULT_MARGIN = 256;
    public static final int DEFAULT_MIN_TOKENS = 1024;
    public static final double DEFAULT_CHARS_PER_TOKEN = 3.0;
    static final int PER_MESSAGE = 8;
    static final int BASE = 16;
    /** finish_reason of the synthetic reply of a call that was not sent. */
    public static final String SKIPPED = "context_clamp_skipped";

    public ContextClamp {
        if (window < 1 || margin < 0 || minTokens < 1 || !(charsPerToken > 0) || margin + minTokens >= window) {
            throw new IllegalArgumentException("context clamp: need window > margin + minTokens, minTokens >= 1, chars/token > 0");
        }
    }

    public static ContextClamp of(String trial, String arm) {
        return new ContextClamp(DEFAULT_WINDOW, DEFAULT_MARGIN, DEFAULT_MIN_TOKENS, DEFAULT_CHARS_PER_TOKEN, trial, arm);
    }

    /** The conservative prompt-token estimate of a request. */
    public int estimate(LlmRequest r) {
        long chars = r.system() == null ? 0 : r.system().length();
        for (LlmRequest.Turn t : r.turns()) {
            chars += t.content() == null ? 0 : t.content().length();
        }
        return (int) Math.ceil(chars / charsPerToken) + BASE + PER_MESSAGE * (1 + r.turns().size());
    }

    /** What one binding looked like: granted is 0 when skipped. */
    public record Info(String callType, int attempt, int estPromptTokens, int requestedMaxTokens, int grantedMaxTokens,
                       boolean skipped, int window, int margin, int minTokens) {
        /** The call record's clamp object (camelCase). */
        public Map<String, Object> toRecord() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("callType", callType);
            m.put("attempt", attempt);
            m.put("estPromptTokens", estPromptTokens);
            m.put("requestedMaxTokens", requestedMaxTokens);
            m.put("grantedMaxTokens", grantedMaxTokens);
            m.put("skipped", skipped);
            m.put("window", window);
            m.put("margin", margin);
            m.put("minTokens", minTokens);
            return m;
        }

        /** The context_clamp event's fields (snake_case, events.jsonl). */
        public Map<String, Object> toEventFields(String trial, String arm, String drawKey) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("trial", trial);
            m.put("arm", arm);
            m.put("call_type", callType);
            m.put("attempt", attempt);
            m.put("est_prompt_tokens", estPromptTokens);
            m.put("requested_max_tokens", requestedMaxTokens);
            m.put("granted_max_tokens", grantedMaxTokens);
            m.put("skipped", skipped);
            m.put("window", window);
            m.put("margin", margin);
            m.put("min_tokens", minTokens);
            m.put("draw_key", drawKey);
            return m;
        }
    }

    /** The outcome for one request: req = the request to send (lowered when it bound; the original when skipped). */
    public record Result(LlmRequest req, Info info) {
        public boolean skipped() {
            return info != null && info.skipped();
        }
    }

    /** info is null when the clamp did not bind (req is then the request itself). */
    public Result apply(LlmRequest r, String callType, int attempt) {
        int est = estimate(r);
        int room = window - margin - est;
        if (r.maxTokens() <= room) {
            return new Result(r, null);
        }
        boolean skip = room < Math.min(minTokens, r.maxTokens()); // relative minimum (U22): a small request is never skipped for being below minTokens
        Info info = new Info(callType, attempt, est, r.maxTokens(), skip ? 0 : room, skip, window, margin, minTokens);
        if (skip) {
            return new Result(r, info);
        }
        return new Result(new LlmRequest(r.provider(), r.modelSnapshot(), r.system(), r.turns(), r.temperature(), room,
                r.responseSchema(), r.drawKey(), r.thinking(), r.topP(), r.topK()), info);
    }
}
