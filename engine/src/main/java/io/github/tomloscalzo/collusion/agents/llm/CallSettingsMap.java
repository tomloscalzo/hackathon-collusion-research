package io.github.tomloscalzo.collusion.agents.llm;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.texts.CallType;
import java.io.IOException;
import java.util.EnumMap;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * The per-call settings map (C12b.1; interface proposal v5, group E1): for each call type (talk, quote, question) the reply
 * schema, the token limit and the timeout, plus the sampling values shared by the run (thinking, temperature, top_p,
 * top_k), each of which a call may override. Values come from the design/grid row ({@link #fromGridRow}) or from a JSON
 * map ({@link #fromJson}), and {@link #toJson} gives the form recorded in params.json. {@link #settingsFor} turns a base
 * {@link LlmSettings} into the settings of one call. Pure: nothing here is wired into a request yet, and with no map the
 * existing single {@code LlmSettings} is used as today (the caller decides; the map always sets max tokens).
 *
 * <p>Thinking is the same for every call type of a run (owner decision 10); a per-call override exists for a talk cap
 * (decision 13) and is validated like the run-level value.
 */
public final class CallSettingsMap {
    /** The reply schema of a call: the talk schema (name "talk"), the quote decision schema, or none (plain text). */
    public enum Schema { TALK, DECISION, NONE;
        public String wireName() { return name().toLowerCase(java.util.Locale.ROOT); }
    }

    /** One call type: schema, max tokens, timeout, and optional overrides of the run-level sampling values. */
    public record Call(Schema schema, int maxTokens, int timeoutSec, Boolean thinking, Double temperature, Double topP,
                       Integer topK) {
        public Call {
            Objects.requireNonNull(schema, "schema");
            if (maxTokens < 1 || timeoutSec < 1) {
                throw new IllegalArgumentException("maxTokens and timeoutSec must be >= 1");
            }
        }

        public Call(Schema schema, int maxTokens, int timeoutSec) {
            this(schema, maxTokens, timeoutSec, null, null, null, null);
        }
    }

    private static final Map<CallType, Schema> DEFAULT_SCHEMA = Map.of(CallType.TALK, Schema.TALK,
            CallType.QUOTE, Schema.DECISION, CallType.QUESTION, Schema.NONE);

    private final Boolean thinking;
    private final Double temperature;
    private final Double topP;
    private final Integer topK;
    private final Map<CallType, Call> calls;

    public CallSettingsMap(Boolean thinking, Double temperature, Double topP, Integer topK, Map<CallType, Call> calls) {
        for (CallType c : CallType.values()) {
            if (!calls.containsKey(c)) {
                throw new IllegalArgumentException("no settings for the " + c.name().toLowerCase(java.util.Locale.ROOT) + " call");
            }
        }
        if (temperature != null && temperature < 0) {
            throw new IllegalArgumentException("temperature must be >= 0: " + temperature);
        }
        this.thinking = thinking;
        this.temperature = temperature;
        this.topP = topP;
        this.topK = topK;
        this.calls = new EnumMap<>(calls);
        // validate every call's effective sampling values now, by building them
        for (CallType c : CallType.values()) {
            settingsFor(new LlmSettings("openai-compatible", "check", 0.7, 1), c);
        }
    }

    public Call call(CallType type) { return calls.get(type); }

    public Schema schema(CallType type) { return calls.get(type).schema(); }

    public int timeoutSec(CallType type) { return calls.get(type).timeoutSec(); }

    /**
     * The settings of one call: base, with this map's max tokens for the call type, and the sampling values (the call's own
     * override, else the run-level value, else base's). Unset values stay unset (null), so a map that sets nothing but
     * max tokens changes nothing else.
     */
    public LlmSettings settingsFor(LlmSettings base, CallType type) {
        Call c = calls.get(type);
        return new LlmSettings(base.provider(), base.modelSnapshot(),
                first(c.temperature(), temperature, base.temperature()), c.maxTokens(),
                first(c.thinking(), thinking, base.thinking()), first(c.topP(), topP, base.topP()),
                first(c.topK(), topK, base.topK()));
    }

    @SafeVarargs
    private static <T> T first(T... values) {
        for (T v : values) {
            if (v != null) {
                return v;
            }
        }
        return null;
    }

    /**
     * From a grid.csv row (column names as in make_grid.py): thinking (0|1), temperature, top_p, top_k (blank = unset),
     * max_tokens_talk / max_tokens_quote / max_tokens_question and timeout_sec (required).
     */
    public static CallSettingsMap fromGridRow(Map<String, String> row) {
        Map<CallType, Call> calls = new EnumMap<>(CallType.class);
        int timeout = integer(row, "timeout_sec", true);
        for (CallType c : CallType.values()) {
            calls.put(c, new Call(DEFAULT_SCHEMA.get(c), integer(row, "max_tokens_" + key(c), true), timeout));
        }
        String t = blankToNull(row.get("thinking"));
        Boolean thinking = t == null ? null : switch (t) {
            case "1" -> Boolean.TRUE;
            case "0" -> Boolean.FALSE;
            default -> throw new IllegalArgumentException("thinking must be 0 or 1: '" + t + "'");
        };
        return new CallSettingsMap(thinking, number(row, "temperature"), number(row, "top_p"),
                blankToNull(row.get("top_k")) == null ? null : integer(row, "top_k", false), calls);
    }

    /**
     * From the JSON form {@code {"thinking":bool?,"temperature":n?,"top_p":n?,"top_k":n?,"calls":{"talk":{"schema"?,
     * "max_tokens","timeout_sec","thinking"?,"temperature"?,"top_p"?,"top_k"?},"quote":{...},"question":{...}}}}.
     * Unknown keys are errors.
     */
    public static CallSettingsMap fromJson(String json) {
        JsonNode root;
        try {
            root = Canonical.MAPPER.readTree(json);
        } catch (IOException e) {
            throw new IllegalArgumentException("settings map is not valid JSON: " + e.getMessage(), e);
        }
        if (root == null || !root.isObject()) {
            throw new IllegalArgumentException("settings map must be a JSON object");
        }
        onlyKeys(root, Set.of("thinking", "temperature", "top_p", "top_k", "calls"), "settings map");
        Map<CallType, Call> calls = new EnumMap<>(CallType.class);
        JsonNode cn = root.path("calls");
        onlyKeys(cn, Set.of("talk", "quote", "question"), "calls");
        for (CallType c : CallType.values()) {
            JsonNode n = cn.path(key(c));
            if (!n.isObject()) {
                throw new IllegalArgumentException("no settings for the " + key(c) + " call");
            }
            onlyKeys(n, Set.of("schema", "max_tokens", "timeout_sec", "thinking", "temperature", "top_p", "top_k"), key(c));
            Schema s = DEFAULT_SCHEMA.get(c);
            if (n.has("schema")) {
                try {
                    s = Schema.valueOf(n.get("schema").asText("").toUpperCase(java.util.Locale.ROOT));
                } catch (IllegalArgumentException e) {
                    throw new IllegalArgumentException(key(c) + ": unknown schema '" + n.get("schema").asText() + "'");
                }
            }
            calls.put(c, new Call(s, req(n, "max_tokens", key(c)), req(n, "timeout_sec", key(c)), bool(n, "thinking"),
                    dbl(n, "temperature"), dbl(n, "top_p"), n.has("top_k") ? req(n, "top_k", key(c)) : null));
        }
        return new CallSettingsMap(bool(root, "thinking"), dbl(root, "temperature"), dbl(root, "top_p"),
                root.has("top_k") ? req(root, "top_k", "settings map") : null, calls);
    }

    /** The recorded form (what {@link #fromJson} reads back); unset values are omitted. */
    public String toJson() {
        ObjectNode r = Canonical.MAPPER.createObjectNode();
        put(r, thinking, temperature, topP, topK);
        ObjectNode cs = r.putObject("calls");
        for (CallType c : CallType.values()) {
            Call k = calls.get(c);
            ObjectNode o = cs.putObject(key(c));
            o.put("schema", k.schema().wireName()).put("max_tokens", k.maxTokens()).put("timeout_sec", k.timeoutSec());
            put(o, k.thinking(), k.temperature(), k.topP(), k.topK());
        }
        return Canonical.text(r);
    }

    private static void put(ObjectNode o, Boolean thinking, Double temperature, Double topP, Integer topK) {
        if (thinking != null) {
            o.put("thinking", thinking);
        }
        if (temperature != null) {
            o.put("temperature", temperature);
        }
        if (topP != null) {
            o.put("top_p", topP);
        }
        if (topK != null) {
            o.put("top_k", topK);
        }
    }

    private static String key(CallType c) { return c.name().toLowerCase(java.util.Locale.ROOT); }

    private static String blankToNull(String s) { return s == null || s.isBlank() ? null : s.strip(); }

    private static int integer(Map<String, String> row, String col, boolean required) {
        String s = blankToNull(row.get(col));
        if (s == null) {
            if (required) {
                throw new IllegalArgumentException("grid column " + col + " is missing or blank");
            }
            return 0;
        }
        try {
            return Integer.parseInt(s);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("grid column " + col + " is not an integer: '" + s + "'");
        }
    }

    private static Double number(Map<String, String> row, String col) {
        String s = blankToNull(row.get(col));
        if (s == null) {
            return null;
        }
        try {
            return Double.valueOf(s);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("grid column " + col + " is not a number: '" + s + "'");
        }
    }

    private static void onlyKeys(JsonNode n, Set<String> allowed, String where) {
        if (!n.isObject()) {
            throw new IllegalArgumentException(where + " must be an object");
        }
        n.fieldNames().forEachRemaining(k -> {
            if (!allowed.contains(k)) {
                throw new IllegalArgumentException(where + ": unknown key '" + k + "'");
            }
        });
    }

    private static int req(JsonNode n, String k, String where) {
        if (!n.path(k).canConvertToInt()) {
            throw new IllegalArgumentException(where + ": " + k + " must be an integer");
        }
        return n.get(k).asInt();
    }

    private static Double dbl(JsonNode n, String k) {
        if (!n.has(k) || n.get(k).isNull()) {
            return null;
        }
        if (!n.get(k).isNumber()) {
            throw new IllegalArgumentException(k + " must be a number");
        }
        return n.get(k).asDouble();
    }

    private static Boolean bool(JsonNode n, String k) {
        if (!n.has(k) || n.get(k).isNull()) {
            return null;
        }
        if (!n.get(k).isBoolean()) {
            throw new IllegalArgumentException(k + " must be true or false");
        }
        return n.get(k).asBoolean();
    }
}
