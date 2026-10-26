package io.github.tomloscalzo.collusion.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Function;
import java.util.logging.Logger;

/**
 * Minimal OpenAI-compatible chat client over java.net.http (POST {baseUrl}/v1/chat/completions); no provider SDK. Works
 * against vLLM's OpenAI server and against API providers by changing the base URL and the model id of the request. The
 * API key is read from the environment variable named apiKeyEnv at construction (never logged, never part of a hash); a
 * null or blank name means no Authorization header (local mock). The constructor runs RemoteGuard, so a non-local host
 * is refused unless COLLUSION_ALLOW_REMOTE=1. The per-request seed is derived from the draw key and the user field
 * carries the draw key, so a server can log and the mock can script by it. HTTP 429 and 5xx are retried up to
 * maxAttempts with a short backoff.
 *
 * <p>Provider refusals and filters (F18, INTERFACES f.3) are returned, never thrown, in this order: (1) a non-empty
 * choices[0].message.refusal string, whatever content holds: text = the refusal string, the synthetic finishReason
 * {@link #FINISH_REFUSAL}; (2) a string content: as is, with the provider's finish_reason (the caller handles
 * "content_filter"); (3) finish_reason "content_filter" without a string content: text "", finishReason
 * {@link #FINISH_CONTENT_FILTER}; (4) HTTP 400 whose JSON body has error.code "content_filter" (a prompt filter): text "",
 * tokens 0, finishReason {@link #FINISH_CONTENT_FILTER}; (5) a null content with a reasoning field or finish_reason
 * "length" (thinking cut off at max_tokens, interface proposal v5, C3): text "", the provider's finishReason and the
 * partial reasoning; (6) anything else without a string content, and any other 400, still throws, so protocol errors
 * stay loud. The finishReason is stored in the cache line, so replay reproduces it. A
 * separate reasoning text (message.reasoning_content, else message.reasoning) and usage.completion_tokens_details
 * .reasoning_tokens are returned alongside, never inside text (interface proposal v5, C3). A content that contains
 * {@code <think>} (reasoning misrouted into the answer, gotcha 16), or a non-empty reasoning on a thinking-off request,
 * is returned as is, logged and counted ({@link #misroutedReplies()}). A reply cut off inside an unclosed
 * {@code <think>} in the content (a parser that leaves unfinished thinking in content) therefore stays text, counted. The HTTP timeout is chosen per call type ({@link #callType}, proposal C4): an entry of
 * the per-call-type map, else the default (120 s from the CLI).
 */
public final class OpenAiCompatibleClient implements LlmClient {
    /** Synthetic finishReason for a provider refusal field (not an OpenAI finish_reason value). */
    public static final String FINISH_REFUSAL = "refusal";
    /** finishReason of a provider content or prompt filter. */
    public static final String FINISH_CONTENT_FILTER = "content_filter";

    private final String endpoint;
    private final String apiKey;
    private final HttpClient http;
    /** The call types of {@link #callType}, the keys a per-call-type timeout map may use. */
    public static final Set<String> CALL_TYPES = Set.of("quote", "probe", "vignette", "talk", "question", "other");
    private static final Logger LOG = Logger.getLogger(OpenAiCompatibleClient.class.getName());

    private final Duration timeout;
    private final Map<String, Duration> callTimeouts;
    private final RateLimiter limiter;
    private final int maxAttempts;
    private final AtomicLong misrouted = new AtomicLong();
    private final boolean followRedirects;
    /** Redirects followed per HTTP attempt before the attempt fails. */
    public static final int MAX_REDIRECTS = 20;

    public OpenAiCompatibleClient(String baseUrl, String apiKeyEnv) {
        this(baseUrl, apiKeyEnv, System::getenv, Duration.ofSeconds(120), null, 3);
    }

    public OpenAiCompatibleClient(String baseUrl, String apiKeyEnv, Function<String, String> env, Duration timeout,
                                  RateLimiter limiter, int maxAttempts) {
        this(baseUrl, apiKeyEnv, env, timeout, limiter, maxAttempts, Map.of());
    }

    /** As below, without following redirects (a 3xx answer throws, as before C12a.4). */
    public OpenAiCompatibleClient(String baseUrl, String apiKeyEnv, Function<String, String> env, Duration timeout,
                                  RateLimiter limiter, int maxAttempts, Map<String, Duration> callTimeouts) {
        this(baseUrl, apiKeyEnv, env, timeout, limiter, maxAttempts, callTimeouts, false);
    }

    /**
     * callTimeouts: call type ({@link #callType}) to timeout; a call type without an entry uses timeout. followRedirects
     * (C12a.4, proposal C5): follow a 301, 302, 303, 307 or 308 answer to the same origin (scheme, host and port), at most
     * {@link #MAX_REDIRECTS} times per attempt, with the API key; 307 and 308 repeat the POST, the others GET the
     * Location, as Modal expects for a call still pending after about 150 s. Each hop gets the call timeout. A redirect
     * to another origin throws, so the key never leaves the configured host.
     */
    public OpenAiCompatibleClient(String baseUrl, String apiKeyEnv, Function<String, String> env, Duration timeout,
                                  RateLimiter limiter, int maxAttempts, Map<String, Duration> callTimeouts,
                                  boolean followRedirects) {
        RemoteGuard.check(baseUrl, env);
        this.followRedirects = followRedirects;
        for (String k : callTimeouts.keySet()) {
            if (!CALL_TYPES.contains(k)) {
                throw new IllegalArgumentException("unknown call type '" + k + "' (known: " + new java.util.TreeSet<>(CALL_TYPES) + ")");
            }
        }
        this.callTimeouts = Map.copyOf(callTimeouts);
        String b = baseUrl.trim();
        while (b.endsWith("/")) {
            b = b.substring(0, b.length() - 1);
        }
        if (b.endsWith("/v1")) {
            b = b.substring(0, b.length() - 3);
        }
        this.endpoint = b + "/v1/chat/completions";
        String key = apiKeyEnv == null || apiKeyEnv.isBlank() ? null : env.apply(apiKeyEnv);
        this.apiKey = key == null || key.isBlank() ? null : key;
        boolean local = RemoteGuard.isLocalHost(URI.create(b).getHost());
        if (!local && this.apiKey == null) {
            throw new LlmException("remote endpoint needs an API key in the environment variable " + apiKeyEnv);
        }
        this.http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();
        this.timeout = timeout;
        this.limiter = limiter;
        this.maxAttempts = Math.max(1, maxAttempts);
    }

    public String endpoint() {
        return endpoint;
    }

    /** Replies so far with "<think>" in the content, or with reasoning on a thinking-off request (a missed parser or flag). */
    public long misroutedReplies() {
        return misrouted.get();
    }

    /** The call type of a request, from its draw-key prefix: game = quote, probe, vig = vignette, talk, question, else other. */
    public static String callType(String drawKey) {
        int bar = drawKey.indexOf('|');
        String p = bar < 0 ? "" : drawKey.substring(0, bar);
        switch (p) {
            case "game":
                return "quote";
            case "vig":
                return "vignette";
            case "probe":
            case "talk":
            case "question":
                return p;
            default:
                return "other";
        }
    }

    /** "quote=140,probe=120" (seconds, each > 0) as a call-type map; null or blank = empty. */
    public static Map<String, Duration> parseCallTimeouts(String spec) {
        Map<String, Duration> m = new TreeMap<>();
        if (spec == null || spec.isBlank()) {
            return m;
        }
        for (String kv : spec.split(",")) {
            String[] f = kv.trim().split("=", 2);
            if (f.length != 2 || !CALL_TYPES.contains(f[0].trim())) {
                throw new IllegalArgumentException("--call-timeout-sec: '" + kv.trim() + "' is not <call type>=<seconds> with a call "
                        + "type in " + new java.util.TreeSet<>(CALL_TYPES));
            }
            long sec = Long.parseLong(f[1].trim());
            if (sec < 1) {
                throw new IllegalArgumentException("--call-timeout-sec: '" + kv.trim() + "' must be at least 1 s");
            }
            m.put(f[0].trim(), Duration.ofSeconds(sec));
        }
        return m;
    }

    /** The per-request seed: the first 31 bits of SHA-256(drawKey). */
    public static int seedOf(String drawKey) {
        return (int) (Long.parseLong(Canonical.sha256(drawKey).substring(0, 8), 16) & 0x7fffffffL);
    }

    static String body(LlmRequest r) {
        ObjectNode b = Canonical.MAPPER.createObjectNode();
        b.put("model", r.modelSnapshot());
        ArrayNode msgs = b.putArray("messages");
        msgs.addObject().put("role", "system").put("content", r.system());
        for (LlmRequest.Turn t : r.turns()) {
            msgs.addObject().put("role", t.role()).put("content", t.content());
        }
        b.put("temperature", r.temperature());
        b.put("max_tokens", r.maxTokens());
        b.put("seed", seedOf(r.drawKey()));
        b.put("user", r.drawKey());
        if (r.thinking() != null) {
            b.putObject("chat_template_kwargs").put("enable_thinking", r.thinking().booleanValue());
        }
        if (r.topP() != null) {
            b.put("top_p", r.topP().doubleValue());
        }
        if (r.topK() != null) {
            b.put("top_k", r.topK().intValue());
        }
        if (r.responseSchema() != null) {
            try {
                JsonNode schema = Canonical.MAPPER.readTree(r.responseSchema());
                ObjectNode rf = b.putObject("response_format");
                rf.put("type", "json_schema");
                ObjectNode js = rf.putObject("json_schema");
                // proposal B1: the talk reply schema goes out under its own name; every other schema as before
                js.put("name", callType(r.drawKey()).equals("talk") ? "talk" : "decision");
                js.set("schema", schema);
            } catch (IOException e) {
                throw new LlmException("responseSchema is not valid JSON", e);
            }
        }
        String text = Canonical.text(b);
        JsonNode props = b.path("response_format").path("json_schema").path("schema").path("properties");
        return props.isObject() ? withFieldOrder(text, props) : text;
    }

    /** The decision fields whose wire order (sorted: plan, quote, rationale) every request has always used. */
    static final Set<String> BASE_FIELDS = Set.of("quote", "plan", "rationale");

    /**
     * Owner-approved (U21): a schema with an extra reply field (reply_extra) keeps the base fields in the sorted order every
     * other request uses (plan, quote, rationale) and puts each extra field right after the field it follows in the schema
     * as built (after quote by default; after rationale, so last, for position last). Guided decoding writes fields in this
     * order. Any other schema is left exactly as before (byte-identical).
     */
    static String withFieldOrder(String text, JsonNode props) {
        java.util.List<String> order = new java.util.ArrayList<>();
        props.fieldNames().forEachRemaining(order::add);
        if (!order.containsAll(BASE_FIELDS) || BASE_FIELDS.containsAll(order)) {
            return text; // not a decision schema with an extra field (talk, choice, plain decision): unchanged
        }
        java.util.List<String> out = new java.util.ArrayList<>();
        order.stream().filter(BASE_FIELDS::contains).sorted().forEach(out::add);
        String prev = null;
        for (String f : order) {
            if (!BASE_FIELDS.contains(f)) {
                int at = prev == null ? 0 : out.indexOf(prev) + 1;
                out.add(at, f);
            }
            prev = f;
        }
        StringBuilder sb = new StringBuilder("{");
        for (String f : out) {
            if (sb.length() > 1) {
                sb.append(',');
            }
            sb.append(new com.fasterxml.jackson.databind.node.TextNode(f).toString()).append(':').append(Canonical.text(props.get(f)));
        }
        String sorted = Canonical.text(props);
        int i = text.indexOf("\"properties\":" + sorted);
        if (i < 0 || text.indexOf("\"properties\":" + sorted, i + 1) >= 0) {
            throw new LlmException("response schema properties not found exactly once in the request body");
        }
        return text.substring(0, i) + "\"properties\":" + sb.append('}') + text.substring(i + "\"properties\":".length() + sorted.length());
    }

    @Override
    public LlmResponse complete(LlmRequest r) {
        String hash = CanonicalRequest.sha256(r);
        String payload = body(r);
        String type = callType(r.drawKey());
        Duration callTimeout = callTimeouts.getOrDefault(type, timeout);
        LlmException last = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            if (limiter != null) {
                limiter.acquire();
            }
            HttpRequest.Builder rb = HttpRequest.newBuilder(URI.create(endpoint)).timeout(callTimeout)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(payload, StandardCharsets.UTF_8));
            if (apiKey != null) {
                rb.header("Authorization", "Bearer " + apiKey);
            }
            long t0 = System.nanoTime();
            try {
                HttpResponse<String> resp = send(rb.build(), payload, callTimeout);
                long ms = (System.nanoTime() - t0) / 1_000_000L;
                int sc = resp.statusCode();
                if (sc == 429 || sc >= 500) {
                    last = new LlmException("HTTP " + sc + " from " + endpoint);
                    backoff(attempt);
                    continue;
                }
                if (sc == 400 && isContentFilterError(resp.body())) {
                    return new LlmResponse("", 0, 0, ms, false, hash, FINISH_CONTENT_FILTER);
                }
                if (sc != 200) {
                    throw new LlmException("HTTP " + sc + " from " + endpoint + ": " + abbreviate(resp.body())
                            + (sc / 100 == 3 && !followRedirects ? " (a redirect: use --follow-redirects on)" : ""));
                }
                JsonNode root = Canonical.MAPPER.readTree(resp.body());
                JsonNode choice = root.path("choices").path(0);
                JsonNode content = choice.path("message").path("content");
                JsonNode refusal = choice.path("message").path("refusal");
                String finish = choice.path("finish_reason").asText("");
                int tin = root.path("usage").path("prompt_tokens").asInt(0);
                int tout = root.path("usage").path("completion_tokens").asInt(0);
                String reasoning = reasoningOf(choice.path("message"));
                JsonNode rt = root.path("usage").path("completion_tokens_details").path("reasoning_tokens");
                Integer rtok = rt.isIntegralNumber() ? Integer.valueOf(rt.asInt()) : null;
                if ((content.isTextual() && content.asText().contains("<think>"))
                        || (Boolean.FALSE.equals(r.thinking()) && reasoning != null && !reasoning.isEmpty())) {
                    misrouted.incrementAndGet();
                    LOG.warning("reply thinking not in the requested state (<think> in the content, or reasoning with thinking "
                            + "off), draw " + r.drawKey());
                }
                if (refusal.isTextual() && !refusal.asText().isEmpty()) {
                    return new LlmResponse(refusal.asText(), tin, tout, ms, false, hash, FINISH_REFUSAL, reasoning, rtok);
                }
                if (content.isTextual()) {
                    return new LlmResponse(content.asText(), tin, tout, ms, false, hash, finish, reasoning, rtok);
                }
                if (finish.equals(FINISH_CONTENT_FILTER)) {
                    return new LlmResponse("", tin, tout, ms, false, hash, FINISH_CONTENT_FILTER, reasoning, rtok);
                }
                if (reasoning != null || finish.equals("length")) {
                    return new LlmResponse("", tin, tout, ms, false, hash, finish, reasoning, rtok);
                }
                throw new LlmException.EmptyContent("response has no choices[0].message.content (finish_reason '" + finish
                        + "', no reasoning field), draw " + r.drawKey(),
                        new LlmResponse("", tin, tout, ms, false, hash, finish, null, rtok));
            } catch (HttpTimeoutException e) {
                last = new LlmException("timed out after " + callTimeout + " (call type " + type + ", draw " + r.drawKey()
                        + "); raise it with --timeout-sec or --call-timeout-sec", e);
                backoff(attempt);
            } catch (IOException e) {
                last = new LlmException("transport error: " + e.getMessage(), e);
                backoff(attempt);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new LlmException("interrupted", e);
            }
        }
        throw last == null ? new LlmException("request failed") : last;
    }

    private HttpResponse<String> send(HttpRequest first, String payload, Duration callTimeout)
            throws IOException, InterruptedException {
        HttpRequest req = first;
        for (int hop = 0; ; hop++) {
            HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            int sc = resp.statusCode();
            if (!followRedirects || !(sc == 301 || sc == 302 || sc == 303 || sc == 307 || sc == 308)) {
                return resp;
            }
            if (hop >= MAX_REDIRECTS) {
                throw new LlmException("more than " + MAX_REDIRECTS + " redirects from " + endpoint);
            }
            String loc = resp.headers().firstValue("Location").orElseThrow(
                    () -> new LlmException("HTTP " + sc + " without a Location header from " + endpoint));
            URI next = req.uri().resolve(loc);
            URI base = URI.create(endpoint);
            if (!sameOrigin(base, next)) {
                throw new LlmException("redirect to another origin refused: " + next.getScheme() + "://" + next.getHost()
                        + ":" + port(next) + " (configured " + base.getScheme() + "://" + base.getHost() + ":" + port(base) + ")");
            }
            HttpRequest.Builder b = HttpRequest.newBuilder(next).timeout(callTimeout);
            if (sc == 307 || sc == 308) {
                b.header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofString(payload, StandardCharsets.UTF_8));
            } else {
                b.GET();
            }
            if (apiKey != null) {
                b.header("Authorization", "Bearer " + apiKey);
            }
            req = b.build();
        }
    }

    /** Same scheme, host and port (default ports filled in); a URI without scheme or host is never the same origin. */
    static boolean sameOrigin(URI a, URI b) {
        return a.getScheme() != null && b.getScheme() != null && a.getHost() != null && b.getHost() != null
                && a.getScheme().equalsIgnoreCase(b.getScheme()) && a.getHost().equalsIgnoreCase(b.getHost()) && port(a) == port(b);
    }

    private static int port(URI u) {
        return u.getPort() >= 0 ? u.getPort() : "https".equalsIgnoreCase(u.getScheme()) ? 443 : 80;
    }

    /** message.reasoning_content, else message.reasoning (the two names vLLM uses), when it is a string; else null. */
    static String reasoningOf(JsonNode message) {
        JsonNode r = message.path("reasoning_content");
        if (!r.isTextual()) {
            r = message.path("reasoning");
        }
        return r.isTextual() ? r.asText() : null;
    }

    /** An HTTP 400 body {"error": {"code": "content_filter", ...}} (Azure prompt filter / Prompt Shields). */
    static boolean isContentFilterError(String body) {
        try {
            JsonNode n = Canonical.MAPPER.readTree(body);
            return n != null && FINISH_CONTENT_FILTER.equals(n.path("error").path("code").asText(""));
        } catch (IOException | RuntimeException e) {
            return false;
        }
    }

    private static void backoff(int attempt) {
        try {
            Thread.sleep(50L * attempt);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private static String abbreviate(String s) {
        return s.length() > 300 ? s.substring(0, 300) + "..." : s;
    }
}
