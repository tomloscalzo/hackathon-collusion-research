package io.github.tomloscalzo.collusion.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Set;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Local stand-in for an OpenAI-compatible server (com.sun.net.httpserver on an ephemeral loopback port), implementing
 * POST /v1/chat/completions with a scripted Behaviour. All tests and the M4 exit criteria run against it; no network is
 * used. Every request is recorded for assertions.
 */
public final class MockLlmServer implements AutoCloseable {
    /** A parsed request. callIndex counts requests from 0. user is the request's user field (the draw key). */
    public record MockRequest(int callIndex, String model, String system, List<LlmRequest.Turn> turns, String user,
                              double temperature, int seed, String rawBody) {
        public String lastUser() {
            return turns.get(turns.size() - 1).content();
        }
    }

    /**
     * A scripted reply beyond plain text (F18 and truncation tests): content (null = JSON null), the message.refusal field
     * (null = absent), the finish_reason, and an HTTP status other than 200 with a raw body (then the other fields are
     * ignored); optionally a reasoning text in message.reasoning_content (or the field named by reasoningField) and
     * usage.completion_tokens_details.reasoning_tokens (C12a.2).
     */
    public record Reply(String content, String refusal, String finishReason, int httpStatus, String rawBody, String reasoning,
                        Integer reasoningTokens, String reasoningField, long delayMs, int redirects, long resultDelayMs) {
        public Reply(String content, String refusal, String finishReason, int httpStatus, String rawBody) {
            this(content, refusal, finishReason, httpStatus, rawBody, null, null, null, 0L, 0, 0L);
        }

        /** The same reply with a reasoning text (null = absent) and usage.completion_tokens_details.reasoning_tokens. */
        public Reply withReasoning(String reasoning, Integer reasoningTokens) {
            return new Reply(content, refusal, finishReason, httpStatus, rawBody, reasoning, reasoningTokens, reasoningField,
                    delayMs, redirects, resultDelayMs);
        }

        /** The message field that carries the reasoning: "reasoning_content" (default) or "reasoning". */
        public Reply withReasoningField(String field) {
            return new Reply(content, refusal, finishReason, httpStatus, rawBody, reasoning, reasoningTokens, field, delayMs,
                    redirects, resultDelayMs);
        }

        /** The same reply, sent after this many milliseconds (a slow server, for timeout tests). */
        public Reply withDelayMs(long ms) {
            return new Reply(content, refusal, finishReason, httpStatus, rawBody, reasoning, reasoningTokens, reasoningField, ms,
                    redirects, resultDelayMs);
        }

        /**
         * Modal's long-call behaviour: the completion request is answered with HTTP 303 to a result URL on this server
         * (absolute Location .../v1/results/id?__modal_function_call_id=fc-id), which answers n - 1 further 303s to itself
         * (relative Location, query kept) and then this reply.
         */
        public Reply withRedirects(int n) {
            return new Reply(content, refusal, finishReason, httpStatus, rawBody, reasoning, reasoningTokens, reasoningField,
                    delayMs, n, resultDelayMs);
        }

        /** Each GET of the result URL waits this many milliseconds before answering. */
        public Reply withResultDelayMs(long ms) {
            return new Reply(content, refusal, finishReason, httpStatus, rawBody, reasoning, reasoningTokens, reasoningField,
                    delayMs, redirects, ms);
        }

        /** HTTP 303 to the given Location (absolute or relative), with no body. */
        public static Reply seeOther(String location) {
            return new Reply(null, null, "", 303, location);
        }

        /** Thinking cut off at max_tokens: content null, finish_reason "length", the partial reasoning. */
        public static Reply truncatedThinking(String partialReasoning) {
            return new Reply(null, null, "length", 200, null).withReasoning(partialReasoning, null);
        }

        public static Reply text(String content) {
            return new Reply(content, null, "stop", 200, null);
        }

        /** finish_reason "length": a reply cut off at the token limit. */
        public static Reply truncated(String content) {
            return new Reply(content, null, "length", 200, null);
        }

        /** OpenAI-style structured-output refusal: content null and message.refusal set. */
        public static Reply providerRefusal(String refusal) {
            return new Reply(null, refusal, "stop", 200, null);
        }

        /** finish_reason "content_filter"; content may be null (no reply) or a partial or complete text. */
        public static Reply contentFilter(String content) {
            return new Reply(content, null, "content_filter", 200, null);
        }

        /** A non-200 answer with this body (for example HTTP 400 with {"error": {"code": "content_filter"}}). */
        public static Reply http(int status, String body) {
            return new Reply(null, null, "", status, body);
        }
    }

    /** Scripts the assistant message text for a request; override reply for a scripted refusal field or finish_reason. */
    @FunctionalInterface
    public interface Behaviour {
        String respond(MockRequest request);

        /** The full reply; by default the text of respond with finish_reason "stop" (null from respond = HTTP 500). */
        default Reply reply(MockRequest request) {
            String t = respond(request);
            return t == null ? null : Reply.text(t);
        }
    }

    private final HttpServer server;
    private final Behaviour behaviour;
    private final Set<String> servedModels;
    private final AtomicInteger calls = new AtomicInteger();
    private final List<MockRequest> requests = Collections.synchronizedList(new ArrayList<>());
    private final List<ResultFetch> fetches = Collections.synchronizedList(new ArrayList<>());
    private final Map<String, Pending> pending = new ConcurrentHashMap<>();
    private final AtomicInteger resultIds = new AtomicInteger();

    /** One request to a result URL: its HTTP method and whether it carried an Authorization header. */
    public record ResultFetch(String path, String query, String method, boolean authorized) {}

    private record Pending(byte[] body, int hopsLeft, long delayMs) {}

    /** Accepts any request model name. */
    public MockLlmServer(Behaviour behaviour) {
        this(behaviour, Set.of());
    }

    /**
     * Serves only the given model names, as vLLM does with {@code --served-model-name}: a request whose {@code model} is
     * not one of them is recorded and counted, the behaviour is not asked, and the answer is HTTP 404 with vLLM's error
     * body. An empty set accepts any model.
     */
    public MockLlmServer(Behaviour behaviour, Set<String> servedModels) {
        this.behaviour = behaviour;
        this.servedModels = Set.copyOf(servedModels);
        try {
            this.server = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 0);
        } catch (IOException e) {
            throw new IllegalStateException("cannot start mock server", e);
        }
        server.createContext("/v1/chat/completions", this::handle);
        server.createContext("/v1/results/", this::result);
        server.setExecutor(Executors.newFixedThreadPool(4, r -> {
            Thread t = new Thread(r, "mock-llm");
            t.setDaemon(true);
            return t;
        }));
        server.start();
    }

    public String baseUrl() {
        return "http://127.0.0.1:" + server.getAddress().getPort();
    }

    public int callCount() {
        return calls.get();
    }

    /** Zeroes the call counter and forgets recorded requests (scripted behaviours index by call). */
    public void reset() {
        calls.set(0);
        requests.clear();
    }

    public List<MockRequest> requests() {
        synchronized (requests) {
            return new ArrayList<>(requests);
        }
    }

    /** Requests to result URLs (Reply.withRedirects), in order. */
    public List<ResultFetch> resultFetches() {
        synchronized (fetches) {
            return new ArrayList<>(fetches);
        }
    }

    private void result(HttpExchange ex) throws IOException {
        try (ex) {
            String path = ex.getRequestURI().getPath();
            fetches.add(new ResultFetch(path, ex.getRequestURI().getRawQuery(), ex.getRequestMethod(),
                    ex.getRequestHeaders().containsKey("Authorization")));
            String id = path.substring(path.lastIndexOf('/') + 1);
            Pending p = pending.get(id);
            if (p == null) {
                send(ex, 404, "{\"error\":\"no such result\"}".getBytes(StandardCharsets.UTF_8));
                return;
            }
            sleep(p.delayMs());
            if (p.hopsLeft() > 0) {
                pending.put(id, new Pending(p.body(), p.hopsLeft() - 1, p.delayMs()));
                ex.getResponseHeaders().add("Location", path + (ex.getRequestURI().getRawQuery() == null ? ""
                        : "?" + ex.getRequestURI().getRawQuery()));
                send(ex, 303, new byte[0]);
                return;
            }
            send(ex, 200, p.body());
        }
    }

    private static void sleep(long ms) {
        if (ms > 0) {
            try {
                Thread.sleep(ms);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    @Override
    public void close() {
        server.stop(0);
    }

    private void handle(HttpExchange ex) throws IOException {
        try (ex) {
            String raw = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            JsonNode b = Canonical.MAPPER.readTree(raw);
            String system = "";
            List<LlmRequest.Turn> turns = new ArrayList<>();
            int promptChars = 0;
            for (JsonNode m : b.path("messages")) {
                String role = m.path("role").asText();
                String content = m.path("content").asText();
                promptChars += content.length();
                if (role.equals("system")) {
                    system = content;
                } else {
                    turns.add(new LlmRequest.Turn(role, content));
                }
            }
            int idx = calls.getAndIncrement();
            MockRequest req = new MockRequest(idx, b.path("model").asText(), system, turns, b.path("user").asText(),
                    b.path("temperature").asDouble(), b.path("seed").asInt(), raw);
            requests.add(req);
            byte[] out;
            int status;
            if (!servedModels.isEmpty() && !servedModels.contains(req.model())) {
                ObjectNode err = Canonical.MAPPER.createObjectNode();
                err.put("object", "error");
                err.put("message", "The model `" + req.model() + "` does not exist.");
                err.put("type", "NotFoundError");
                err.putNull("param");
                err.put("code", 404);
                send(ex, 404, Canonical.text(err).getBytes(StandardCharsets.UTF_8));
                return;
            }
            Reply reply = behaviour.reply(req);
            if (reply != null) {
                sleep(reply.delayMs());
            }
            String text = reply == null ? null : reply.content();
            if (reply == null) {
                status = 500;
                out = "{\"error\":\"scripted failure\"}".getBytes(StandardCharsets.UTF_8);
            } else if (reply.httpStatus() / 100 == 3) {
                status = reply.httpStatus();
                out = new byte[0];
                if (reply.rawBody() != null && !reply.rawBody().isEmpty()) {
                    ex.getResponseHeaders().add("Location", reply.rawBody());
                }
            } else if (reply.httpStatus() != 200) {
                status = reply.httpStatus();
                out = (reply.rawBody() == null ? "" : reply.rawBody()).getBytes(StandardCharsets.UTF_8);
            } else {
                status = 200;
                ObjectNode root = Canonical.MAPPER.createObjectNode();
                root.put("id", "mock-" + idx);
                root.put("object", "chat.completion");
                ArrayNode choices = root.putArray("choices");
                ObjectNode c = choices.addObject();
                c.put("index", 0);
                c.put("finish_reason", reply.finishReason());
                ObjectNode msg = c.putObject("message").put("role", "assistant");
                if (text == null) {
                    msg.putNull("content");
                } else {
                    msg.put("content", text);
                }
                if (reply.refusal() != null) {
                    msg.put("refusal", reply.refusal());
                }
                if (reply.reasoning() != null) {
                    msg.put(reply.reasoningField() == null ? "reasoning_content" : reply.reasoningField(), reply.reasoning());
                }
                ObjectNode u = root.putObject("usage");
                u.put("prompt_tokens", (promptChars + 3) / 4);
                String produced = text != null ? text : reply.refusal() != null ? reply.refusal() : "";
                u.put("completion_tokens", (produced.length() + 3) / 4);
                if (reply.reasoningTokens() != null) {
                    u.putObject("completion_tokens_details").put("reasoning_tokens", reply.reasoningTokens().intValue());
                }
                out = Canonical.text(root).getBytes(StandardCharsets.UTF_8);
                if (reply.redirects() > 0) {
                    String id = "r" + resultIds.getAndIncrement();
                    pending.put(id, new Pending(out, reply.redirects() - 1, reply.resultDelayMs()));
                    // like Modal: an absolute URL on the same origin, with the call id as a query parameter
                    ex.getResponseHeaders().add("Location", baseUrl() + "/v1/results/" + id + "?__modal_function_call_id=fc-" + id);
                    status = 303;
                    out = new byte[0];
                }
            }
            send(ex, status, out);
        }
    }

    private static void send(HttpExchange ex, int status, byte[] out) throws IOException {
        ex.getResponseHeaders().add("Content-Type", "application/json");
        ex.sendResponseHeaders(status, out.length == 0 ? -1 : out.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(out);
        }
    }

    // ---------------------------------------------------------------- scripted behaviours

    /** Behaviour factories. */
    public static final class Behaviours {
        private Behaviours() {}

        public static String decisionJson(double quote, String plan) {
            return String.format(Locale.ROOT, "{\"quote\": %.2f, \"plan\": \"%s\", \"rationale\": \"scripted\"}", quote, plan);
        }

        /** Always quotes q (adhere at s_p). */
        public static Behaviour fixed(double q) {
            return r -> decisionJson(q, "hold " + q);
        }

        public static Behaviour adhere(double sp) {
            return fixed(sp);
        }

        /** Always quotes one increment below s_p (undercut by one increment from the first round). */
        public static Behaviour undercut(double sp, double increment) {
            return r -> decisionJson(sp - increment, "undercut");
        }

        public static Behaviour alwaysCompete(double s0) {
            return fixed(s0);
        }

        /** Declines every request in words (no JSON). */
        public static Behaviour refuse() {
            return r -> "I'm sorry, but I can't help with setting prices in coordination with a competitor.";
        }

        /** Declines with a valid JSON decision whose quote is null. */
        public static Behaviour declineJson() {
            return r -> "{\"quote\": null, \"plan\": \"\", \"rationale\": \"I decline to choose\"}";
        }

        /** Returns the listed quotes in order of call (the last one repeats). */
        public static Behaviour echo(List<Double> quotes) {
            List<Double> q = List.copyOf(quotes);
            return r -> decisionJson(q.get(Math.min(r.callIndex(), q.size() - 1)), "echo");
        }

        /** Not-JSON text on the listed call indices, otherwise the given behaviour. */
        public static Behaviour malformedAt(Set<Integer> callIndices, Behaviour otherwise) {
            Set<Integer> s = Set.copyOf(callIndices);
            return r -> s.contains(r.callIndex()) ? "{\"quote\": 2.0" : otherwise.respond(r);
        }

        /** The first call is malformed JSON, afterwards valid. */
        public static Behaviour malformedOnce(Behaviour otherwise) {
            return malformedAt(Set.of(0), otherwise);
        }

        private static final Pattern ROW = Pattern.compile("\\|b(-?\\d+\\.\\d+)\\|c([A-Z])\\|");

        /**
         * Vignette respondent with a switch point: chooses the collusive option iff the row payment b/G (parsed from the
         * draw key) is below bStar. The draw key also names the letter of the collusive option.
         */
        public static Behaviour vignetteSwitch(double bStar) {
            return r -> {
                Matcher m = ROW.matcher(r.user());
                if (!m.find()) {
                    return "{\"choice\": \"NEITHER\", \"rationale\": \"no row\"}";
                }
                double b = Double.parseDouble(m.group(1));
                String collusive = m.group(2);
                String other = collusive.equals("A") ? "B" : "A";
                return "{\"choice\": \"" + (b < bStar ? collusive : other) + "\", \"rationale\": \"scripted\"}";
            };
        }

        /**
         * A behaviour with full replies (refusal field, finish_reason, HTTP status); respond returns the content, or ""
         * when it is null.
         */
        public static Behaviour replies(java.util.function.Function<MockRequest, Reply> f) {
            return new Behaviour() {
                @Override
                public String respond(MockRequest request) {
                    Reply r = f.apply(request);
                    return r == null ? null : r.content() == null ? "" : r.content();
                }

                @Override
                public Reply reply(MockRequest request) {
                    return f.apply(request);
                }
            };
        }

        /** Every request answered with a provider refusal field (content null), as OpenAI structured outputs do. */
        public static Behaviour providerRefusal() {
            return replies(r -> Reply.providerRefusal("I'm sorry, I cannot assist with that request."));
        }

        /** Every request stopped by a content filter after generation (finish_reason content_filter, content null). */
        public static Behaviour contentFilter() {
            return replies(r -> Reply.contentFilter(null));
        }

        /** Every request rejected by a prompt filter: HTTP 400 with the Azure-style body error.code content_filter. */
        public static Behaviour promptFilter400() {
            return replies(r -> Reply.http(400, "{\"error\": {\"code\": \"content_filter\", \"message\": \"The "
                    + "prompt was filtered due to triggering the content management policy.\", \"status\": 400}}"));
        }

        /** Vignette respondent that always declines to choose. */
        public static Behaviour vignetteRefuse() {
            return r -> "{\"choice\": \"NEITHER\", \"rationale\": \"I decline\"}";
        }
    }
}
