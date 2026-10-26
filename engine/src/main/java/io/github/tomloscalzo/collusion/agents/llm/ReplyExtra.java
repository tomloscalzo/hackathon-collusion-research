package io.github.tomloscalzo.collusion.agents.llm;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.texts.Slot;
import io.github.tomloscalzo.collusion.texts.TextLibrary;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * One optional named extra field of the quote reply (U8, generic so that U10 can reuse it): a self-report that the seat gives
 * after its quote (D-set scores: last, U21), behind the {@code --options} key {@code reply_extra} (default absent: the schema, the format line and
 * every prompt are byte-identical to before). Shape of the option:
 * <pre>{"name": "conflict_score", "kind": "integer", "min": 1, "max": 5, "text": "score_conflict"}
 * {"name": "feeling", "kind": "text", "max_chars": 300, "text": "some_text_name"}</pre>
 * {@code text} names a REPLY_FIELD text (the instruction, appended to the reply-format line of the system prompt). The field
 * sits right after the quote in the schema and in the format line, unless the option says {@code "position": "last"} (U21:
 * the field then comes after the rationale, in the schema order (guided decoding writes fields in that order) and in the format
 * line, so the plan and rationale are written before the rating; the D-set integer scores use it; the key absent or
 * {@code "after_quote"} keeps the U8 position, so text-kind R2s/R3s and every earlier option cell are unchanged). The answer is parsed and logged (events.jsonl quote
 * events: self_report, self_report_name, self_report_kind, self_report_valid) and never reaches a later prompt (the plan and
 * the rationale are the only parts of a reply that do). An unreadable or out-of-range value is logged as null with
 * self_report_valid false and does not affect the quote's outcome.
 */
public record ReplyExtra(String name, Kind kind, int min, int max, int maxChars, String textName, String text,
                         boolean last) {
    public enum Kind { INTEGER, TEXT }

    /** Option keys of {@code reply_extra}. */
    static final Set<String> KEYS = Set.of("name", "kind", "min", "max", "max_chars", "text", "position");
    private static final Pattern NAME = Pattern.compile("[a-z][a-z0-9_]{0,31}");
    private static final Set<String> TAKEN = Set.of("quote", "plan", "rationale", "decline", "choice", "message", "done");
    public static final int DEFAULT_MAX_CHARS = 300;

    public ReplyExtra {
        if (!NAME.matcher(name).matches() || TAKEN.contains(name)) {
            throw new IllegalArgumentException("reply_extra name '" + name + "' must be lower-case letters, digits and _ "
                    + "(up to 32, starting with a letter) and not one of " + new java.util.TreeSet<>(TAKEN));
        }
        if (kind == Kind.INTEGER && min > max) {
            throw new IllegalArgumentException("reply_extra min " + min + " is above max " + max);
        }
        if (kind == Kind.TEXT && maxChars < 1) {
            throw new IllegalArgumentException("reply_extra max_chars must be positive");
        }
    }

    /** The reply_extra of an options object (TrialTexts.options), or null when the key is absent. */
    public static ReplyExtra fromOptions(JsonNode options, TextLibrary lib) {
        if (options == null || !options.has("reply_extra")) {
            return null;
        }
        JsonNode n = options.get("reply_extra");
        if (!n.isObject()) {
            throw new IllegalArgumentException("--options reply_extra must be an object: " + n);
        }
        n.fieldNames().forEachRemaining(k -> {
            if (!KEYS.contains(k)) {
                throw new IllegalArgumentException("--options reply_extra has unknown key '" + k + "'");
            }
        });
        String name = textual(n, "name");
        String kindText = textual(n, "kind");
        Kind kind = switch (kindText) {
            case "integer" -> Kind.INTEGER;
            case "text" -> Kind.TEXT;
            default -> throw new IllegalArgumentException("--options reply_extra kind must be integer or text: " + kindText);
        };
        String textName = textual(n, "text");
        boolean last = false;
        if (n.has("position")) {
            String pos = textual(n, "position");
            if (!pos.equals("after_quote") && !pos.equals("last")) {
                throw new IllegalArgumentException("--options reply_extra position must be after_quote or last: " + pos);
            }
            last = pos.equals("last");
        }
        if (!lib.has(textName) || lib.get(textName).slot() != Slot.REPLY_FIELD) {
            throw new IllegalArgumentException("--options reply_extra text '" + textName + "' must name a REPLY_FIELD text");
        }
        if (kind == Kind.INTEGER) {
            if (n.has("max_chars")) {
                throw new IllegalArgumentException("--options reply_extra max_chars is for kind text");
            }
            return new ReplyExtra(name, kind, intOf(n, "min"), intOf(n, "max"), DEFAULT_MAX_CHARS, textName,
                    lib.get(textName).text(), last);
        }
        if (n.has("min") || n.has("max")) {
            throw new IllegalArgumentException("--options reply_extra min and max are for kind integer");
        }
        return new ReplyExtra(name, kind, 0, 0, n.has("max_chars") ? intOf(n, "max_chars") : DEFAULT_MAX_CHARS, textName,
                lib.get(textName).text(), last);
    }

    private static String textual(JsonNode n, String key) {
        if (!n.has(key) || !n.get(key).isTextual() || n.get(key).asText().isBlank()) {
            throw new IllegalArgumentException("--options reply_extra needs a text value for '" + key + "'");
        }
        return n.get(key).asText();
    }

    private static int intOf(JsonNode n, String key) {
        if (!n.has(key) || !n.get(key).isInt()) {
            throw new IllegalArgumentException("--options reply_extra needs an integer value for '" + key + "'");
        }
        return n.get(key).asInt();
    }

    /** The value slot of the format line, e.g. {@code <integer from 1 to 5>}. */
    String valueHint() {
        return kind == Kind.INTEGER ? "<integer from " + min + " to " + max + ">" : "\"<text, at most " + maxChars + " characters>\"";
    }

    /** The decision schema with this field right after the quote, or after the rationale when position is last (and required). */
    public String decisionSchema() {
        String prop = kind == Kind.INTEGER ? "{\"type\":\"integer\",\"minimum\":" + min + ",\"maximum\":" + max + "}"
                : "{\"type\":\"string\"}";
        if (last) {
            return PromptBuilder.DECISION_SCHEMA
                    .replace("\"rationale\":{\"type\":\"string\"}", "\"rationale\":{\"type\":\"string\"},\"" + name + "\":" + prop)
                    .replace("\"rationale\"]}", "\"rationale\",\"" + name + "\"]}");
        }
        return PromptBuilder.DECISION_SCHEMA
                .replace("\"quote\":{\"type\":[\"number\",\"null\"]},", "\"quote\":{\"type\":[\"number\",\"null\"]},\"" + name + "\":" + prop + ",")
                .replace("\"required\":[\"quote\",", "\"required\":[\"quote\",\"" + name + "\",");
    }

    /** What a quote reply gave: value (Integer, String or null), valid (false for a missing, unreadable or out-of-range value). */
    public record Answer(Object value, boolean valid) {}

    /** Reads the field from the (already accepted) quote reply text. */
    public Answer parse(String replyText) {
        JsonNode obj = replyText == null ? null : DecisionParser.extractObject(replyText);
        JsonNode v = obj == null ? null : obj.get(name);
        if (v == null || v.isNull()) {
            return new Answer(null, false);
        }
        if (kind == Kind.INTEGER) {
            Integer i = null;
            if (v.isNumber() && v.asDouble() == Math.rint(v.asDouble()) && Math.abs(v.asDouble()) < 1e9) {
                i = (int) v.asDouble();
            } else if (v.isTextual() && v.asText().trim().matches("-?\\d{1,9}")) {
                i = Integer.valueOf(v.asText().trim());
            }
            return i != null && i >= min && i <= max ? new Answer(i, true) : new Answer(null, false);
        }
        if (!v.isTextual() || v.asText().isBlank()) {
            return new Answer(null, false);
        }
        String s = v.asText().strip();
        return new Answer(s.length() > maxChars ? s.substring(0, maxChars) : s, true);
    }

    /** The reply text without this field (the probe re-sends the accepted reply; the answer must not travel); unchanged if unreadable. */
    public String strip(String replyText) {
        JsonNode obj = replyText == null ? null : DecisionParser.extractObject(replyText);
        if (obj == null || !obj.has(name)) {
            return replyText;
        }
        ((com.fasterxml.jackson.databind.node.ObjectNode) obj).remove(name);
        return obj.toString();
    }

    /** The scalar fields logged on a quote event (events.jsonl). */
    public Map<String, Object> eventFields(Answer a) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("self_report", a.value());
        m.put("self_report_name", name);
        m.put("self_report_kind", kind.name().toLowerCase(Locale.ROOT));
        m.put("self_report_valid", a.valid());
        return m;
    }
}
