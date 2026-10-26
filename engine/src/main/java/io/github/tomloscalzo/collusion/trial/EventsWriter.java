package io.github.tomloscalzo.collusion.trial;

import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Map;

/**
 * The events.jsonl of one Track M trial (scope 4.6): one sorted-key JSON line per call or market event, appended as it
 * happens. The field names are the contract with tools/trial/derive.py (CONTRACTS.md): kind (talk, quote, market, regulator,
 * question), round, seq, seat, turn, parsed.message/done/plan/rationale/quote, quote, outcome, refusal_kind, truncated,
 * imputed, prices, profits, winner, market_price, tokens_in, tokens_out, cache_hit, and the optional reasoning,
 * reasoning_tokens, name and mode (questions); talk events also word_capped (always), words_sent and tag_stripped (C5.6).
 *
 * <p>Logging is a pure side effect: arguments are only read, nothing is returned to the game, and a failing sink never
 * throws into it; the first failure is kept in {@link #error()} for the caller to report. Absent values are omitted.
 */
public final class EventsWriter {
    /** What one LLM call looked like: prompt as sent, raw reply, optional reasoning, usage, and its identity. */
    public record Call(String prompt, String reply, String reasoning, Integer reasoningTokens, int tokensIn, int tokensOut,
                       long latencyMs, boolean cacheHit, String requestHash, String drawKey, String finishReason,
                       String refusalPattern) {
        /** Without a refusal pattern (the matched refusal text, for refusals.csv). */
        public Call(String prompt, String reply, String reasoning, Integer reasoningTokens, int tokensIn, int tokensOut,
                long latencyMs, boolean cacheHit, String requestHash, String drawKey, String finishReason) {
            this(prompt, reply, reasoning, reasoningTokens, tokensIn, tokensOut, latencyMs, cacheHit, requestHash, drawKey,
                    finishReason, null);
        }
    }

    private final Path file;
    private int seq;
    private Exception error;

    /** Refuses a file that already has content: one writer per trial, never mixed with an earlier log. */
    public EventsWriter(Path file) {
        this.file = file;
        try {
            if (Files.exists(file) && Files.size(file) > 0) {
                throw new IllegalStateException("events log already has content: " + file);
            }
        } catch (IOException e) {
            error = e;
        }
    }

    /** The first write failure, or null. */
    public synchronized Exception error() {
        return error;
    }

    /** @deprecated pre-Q9 form: writes word_capped false; use the form with wordCapped (C5.6). */
    @Deprecated
    public synchronized void talk(int round, int turn, String seat, Call c, String message, Boolean done, String outcome,
            String refusalKind, boolean truncated) {
        talk(round, turn, seat, c, message, done, outcome, refusalKind, truncated, false, Map.of());
    }

    /**
     * truncated: the reply hit the token limit (finish_reason "length"); wordCapped: the message was cut at 150 words by
     * WordCap (always written, true or false: CONTRACTS Q9, read by derive.cut_kinds). extra: further scalar fields of a
     * talk call (C5.6: tag_stripped, words_sent).
     */
    public synchronized void talk(int round, int turn, String seat, Call c, String message, Boolean done, String outcome,
            String refusalKind, boolean truncated, boolean wordCapped, Map<String, ?> extra) {
        log(() -> {
        ObjectNode e = call("talk", round, seat, c, outcome, refusalKind);
        e.put("word_capped", wordCapped);
        e.put("turn", turn);
        if (truncated) {
            e.put("truncated", true);
        }
        if (message != null || done != null) {
            ObjectNode p = e.putObject("parsed");
            putIf(p, "message", message);
            if (done != null) {
                p.put("done", done);
            }
        }
        extra.forEach((k, v) -> { // last, so an extra never replaces a field written above
            if (!RESERVED.contains(k) && !e.has(k)) {
                e.set(k, Canonical.MAPPER.valueToTree(v));
            }
        });
        return e;
        });
    }

    public synchronized void quote(int round, String seat, Call c, Double quote, String plan, String rationale,
            String outcome, String refusalKind, boolean imputed) {
        quote(round, seat, c, quote, plan, rationale, outcome, refusalKind, imputed, false);
    }

    /** truncated: the reply hit the token limit (finish_reason length), also when its quote was still read (rule 0). */
    public synchronized void quote(int round, String seat, Call c, Double quote, String plan, String rationale,
            String outcome, String refusalKind, boolean imputed, boolean truncated) {
        quote(round, seat, c, quote, plan, rationale, outcome, refusalKind, imputed, truncated, Map.of());
    }

    /** extra: further scalar fields of a quote call (C12b.3: truncated_thinking), written last, never replacing a field. */
    public synchronized void quote(int round, String seat, Call c, Double quote, String plan, String rationale,
            String outcome, String refusalKind, boolean imputed, boolean truncated, Map<String, ?> extra) {
        log(() -> {
        ObjectNode e = call("quote", round, seat, c, outcome, refusalKind);
        if (truncated) {
            e.put("truncated", true);
        }
        if (quote != null) {
            num(e, "quote", quote);
        }
        if (imputed) {
            e.put("imputed", true);
        }
        if (quote != null || plan != null || rationale != null) {
            ObjectNode p = e.putObject("parsed");
            if (quote != null) {
                num(p, "quote", quote);
            }
            putIf(p, "plan", plan);
            putIf(p, "rationale", rationale);
        }
        extra.forEach((k, v) -> { // last, so an extra never replaces a field written above
            if (!RESERVED.contains(k) && !e.has(k)) {
                e.set(k, Canonical.MAPPER.valueToTree(v));
            }
        });
        return e;
        });
    }

    /** winner is the seat that took the market, or null for a tie or shared market (the key is still written). */
    public synchronized void market(int round, Map<String, Double> prices, Map<String, Double> profits, String winner,
            double marketPrice) {
        log(() -> {
        ObjectNode e = base("market", round);
        e.set("prices", numbers(prices));
        e.set("profits", numbers(profits));
        e.put("winner", winner);
        num(e, "market_price", marketPrice);
        return e;
        });
    }

    /** extra: further scalar fields such as seat, amount or flagged. */
    public synchronized void regulator(int round, String event, String detail, Map<String, ?> extra) {
        log(() -> {
        ObjectNode e = base("regulator", round);
        e.put("event", event);
        putIf(e, "detail", detail);
        extra.forEach((k, v) -> {
            if (!RESERVED.contains(k)) {
                e.set(k, Canonical.MAPPER.valueToTree(v));
            }
        });
        return e;
        });
    }

    /** mode is "fed" (in-game, shown back to the seat) or "post" (post-game pass). */
    public synchronized void question(int round, String seat, String name, String mode, Call c, String answer,
            String outcome, String refusalKind) {
        question(round, seat, name, mode, c, answer, outcome, refusalKind, Map.of());
    }

    /** extra: further scalar fields of a question call (C13.3: truncated, truncated_thinking), never replacing a field. */
    public synchronized void question(int round, String seat, String name, String mode, Call c, String answer,
            String outcome, String refusalKind, Map<String, ?> extra) {
        log(() -> {
        ObjectNode e = call("question", round, seat, c, outcome, refusalKind);
        e.put("name", name).put("mode", mode);
        extra.forEach((k, v) -> {
            if (!RESERVED.contains(k) && !e.has(k)) {
                e.set(k, Canonical.MAPPER.valueToTree(v));
            }
        });
        if (answer != null) {
            e.putObject("parsed").put("message", answer);
        }
        return e;
        });
    }

    /**
     * Unit W2: the check of question_when for one seat and round (a firm-round of round 2 on, and of round 1 under the rating
     * trigger). NOT a model call: no draw key, no tokens, no cache entry. eligible = the trigger could be evaluated (a target
     * for non_competitive, a valid score for self_report_ge); triggered = the rule says ask; asked = the question call was made
     * (a triggered question after the last round is not asked). target, quote and score are the numbers the rule read (null
     * when absent), so an audit can re-run the rule. collect counts eligible and asked rounds from these events.
     */
    public synchronized void watchdogCheck(int round, String seat, String name, String when, boolean eligible, boolean triggered,
            boolean asked, Double quote, Double target, Integer score) {
        log(() -> {
        ObjectNode e = base("watchdog_check", round);
        e.put("seat", seat).put("name", name).put("when", when).put("eligible", eligible).put("triggered", triggered)
                .put("asked", asked);
        if (quote != null) {
            num(e, "quote", quote);
        }
        if (target != null) {
            num(e, "target", target);
        }
        if (score != null) {
            e.put("score", score.intValue());
        }
        return e;
        });
    }

    /**
     * Any other model call (C4.3): kind "attempt" (a first reply that was unreadable and got a repair; extra names the
     * call type in "of" and the attempt number), or "probe" (a Track S comprehension probe). derive.py and collect.py
     * ignore these kinds; they are logged so that every call is in the record. extra: further scalar fields.
     */
    public synchronized void otherCall(String kind, int round, String seat, Call c, String outcome, Map<String, ?> extra) {
        log(() -> {
        ObjectNode e = call(kind, round, seat, c, outcome, null);
        extra.forEach((k, v) -> {
            if (!RESERVED.contains(k) && !e.has(k)) {
                e.set(k, Canonical.MAPPER.valueToTree(v));
            }
        });
        return e;
        });
    }

    /**
     * An empty talk reply read as "done" (unit E1, option empty_talk_as_done, gpt-oss only): kind "empty_reply_as_done", seat,
     * round, turn, draw_key (the call's), finish_reason and the tokens of the empty reply. The same turn also has its ordinary
     * talk event (parsed.done true, message ""). derive.py ignores the kind; collect.py counts it (empty_talk_done_count).
     */
    public synchronized void emptyReplyAsDone(int round, String seat, int turn, String drawKey, String finishReason,
            int tokensIn, int tokensOut) {
        log(() -> {
        ObjectNode e = base("empty_reply_as_done", round);
        e.put("seat", seat);
        e.put("turn", turn);
        e.put("draw_key", drawKey);
        e.put("finish_reason", finishReason);
        e.put("tokens_in", tokensIn);
        e.put("tokens_out", tokensOut);
        return e;
        });
    }

    /**
     * The context clamp bound on a call (unit U2): kind "context_clamp", seat, then the fields (trial, arm, call_type,
     * attempt, est_prompt_tokens, requested_max_tokens, granted_max_tokens, skipped, window, margin, min_tokens, draw_key).
     * derive.py and collect.py ignore the kind.
     */
    public synchronized void contextClamp(int round, String seat, Map<String, ?> fields) {
        log(() -> {
        ObjectNode e = base("context_clamp", round);
        e.put("seat", seat);
        fields.forEach((k, v) -> {
            if (!RESERVED.contains(k) && !e.has(k) && v != null) {
                e.set(k, Canonical.MAPPER.valueToTree(v));
            }
        });
        return e;
        });
    }

    private ObjectNode base(String kind, int round) {
        ObjectNode e = Canonical.MAPPER.createObjectNode();
        e.put("kind", kind).put("round", round);
        return e;
    }

    private ObjectNode call(String kind, int round, String seat, Call c, String outcome, String refusalKind) {
        ObjectNode e = base(kind, round);
        e.put("seat", seat);
        putIf(e, "outcome", outcome);
        putIf(e, "refusal_kind", refusalKind);
        putIf(e, "refusal_pattern", c.refusalPattern());
        putIf(e, "prompt", c.prompt());
        putIf(e, "reply", c.reply());
        putIf(e, "reasoning", c.reasoning());
        if (c.reasoningTokens() != null) {
            e.put("reasoning_tokens", c.reasoningTokens());
        }
        e.put("tokens_in", c.tokensIn()).put("tokens_out", c.tokensOut()).put("latency_ms", c.latencyMs());
        e.put("cache_hit", c.cacheHit());
        putIf(e, "request_hash", c.requestHash());
        putIf(e, "draw_key", c.drawKey());
        putIf(e, "finish_reason", c.finishReason());
        return e;
    }

    private static void putIf(ObjectNode n, String key, String value) {
        if (value != null) {
            n.put(key, value);
        }
    }

    private static final java.util.Set<String> RESERVED = java.util.Set.of("seq", "kind", "round", "event");

    /** NaN and infinity are not JSON: they are written as null. */
    private static void num(ObjectNode n, String key, double v) {
        if (Double.isFinite(v)) {
            n.put(key, v);
        } else {
            n.putNull(key);
        }
    }

    private static ObjectNode numbers(Map<String, Double> m) {
        ObjectNode o = Canonical.MAPPER.createObjectNode();
        m.forEach((k, v) -> {
            if (v == null) {
                o.putNull(k);
            } else {
                num(o, k, v);
            }
        });
        return o;
    }

    /** Builds and writes one event; anything that goes wrong (bad arguments included) is kept, never thrown. */
    private void log(java.util.function.Supplier<ObjectNode> event) {
        try {
            emit(event.get());
        } catch (RuntimeException ex) {
            if (error == null) {
                error = ex;
            }
        }
    }

    private void emit(ObjectNode body) {
        ObjectNode e = Canonical.MAPPER.createObjectNode();
        e.put("seq", seq + 1);
        e.setAll(body);
        try {
            Path dir = file.getParent();
            if (dir != null) {
                Files.createDirectories(dir);
            }
            try (Writer w = Files.newBufferedWriter(file, StandardCharsets.UTF_8, StandardOpenOption.CREATE,
                    StandardOpenOption.APPEND)) {
                w.write(Canonical.text(e));
                w.write('\n');
            }
            seq++;
        } catch (IOException | RuntimeException ex) {
            if (error == null) {
                error = ex;
            }
        }
    }
}
