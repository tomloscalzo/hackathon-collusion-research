package io.github.tomloscalzo.collusion.agents.llm;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Locale;
import java.util.function.Supplier;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * The talk-phase reply: the flat schema {@link #TALK_SCHEMA} (proposal B1; also docs/interfaces/schemas/llm_talk_reply.schema.json)
 * and its parser. Pure: it reads text and returns what the reply means; the 150-word cut is {@code talk.WordCap}, applied by
 * the caller to {@link Parsed#message()}.
 *
 * <p>Rules (proposal B1, gotchas 6 and 8). {@code done: true} (or the string "true") is "done" and any message text sent
 * with it is logged, not delivered. An empty message with {@code done: false} is also "done". A refusal in prose, or a JSON
 * message that is itself a refusal, counts as "done" and is flagged (decision 5), even when sent with done true. Leading
 * speaker tags such as "M2:", "SYSTEM:" or "[M2]" are stripped and flagged. A JSON object may sit inside prose or a code
 * fence, and a reply nested inside the message is unwrapped once. An unreadable reply is INVALID;
 * {@link #parse(String, Supplier)} then asks for one repair ({@link PromptBuilder#REPAIR_TEXT}) and, if that fails too,
 * imputes "done" (flagged, outcome IMPUTED); the caller logs the raw replies itself.
 *
 * <p>Refusal (gotcha 6 and Q2: in-character talk must not misfire). In talk a refusal means declining the task or the
 * conversation ({@link #TASK_REFUSAL}: "I can't help with this request", "I will not participate in this conversation",
 * "As an AI I won't ...", or a bare "I'm sorry, but I can't." as the whole message), never a firm's statement about its own
 * conduct: refusing to collude, promises, threats and price talk are messages. The quote call keeps the broader
 * {@link DecisionParser#REFUSAL}, because there a prose "I won't collude" in place of a quote is a refusal of the decision.
 * As a second guard, inside a JSON message the pattern counts only when it starts the message (at most three words before
 * it) and nothing after it contains a digit. Rare misfires are logged (the raw text is in {@code logged}), never hidden.
 */
public final class TalkParser {
    private TalkParser() {}

    /** Sent as response_format.json_schema (name "talk") in chat arms. Flat: no oneOf, no maxLength. */
    public static final String TALK_SCHEMA = "{\"type\":\"object\",\"properties\":{\"message\":{\"type\":\"string\"},"
            + "\"done\":{\"type\":\"boolean\"}},\"required\":[\"message\",\"done\"]}";

    public enum Outcome { MESSAGE, DONE, REFUSED, INVALID }

    /**
     * message: the text to deliver (null unless MESSAGE). logged: the message text exactly as the reply gave it, before tag
     * stripping, whatever the outcome (null if none). refusalPattern: the matched refusal text for REFUSED. refusalKind
     * (events.jsonl refusal_kind): MODEL_TEXT for a refusal in prose without a JSON object, MODEL_DECLINE for a refusal
     * inside a JSON reply, UNPARSEABLE for an imputed reply, else null.
     */
    public record Parsed(Outcome outcome, String message, String logged, String refusalPattern, String refusalKind,
                         boolean tagStripped, boolean repaired, boolean imputed) {
        /** True when the seat is finished for the round (done, empty, refusal or imputed). */
        public boolean isDone() {
            return outcome == Outcome.DONE || outcome == Outcome.REFUSED;
        }

        /** The events.jsonl outcome (CONTRACTS.md): OK, REPAIRED, REFUSED, IMPUTED (INVALID before any repair). */
        public String eventOutcome() {
            if (imputed) {
                return "IMPUTED";
            }
            if (outcome == Outcome.REFUSED) {
                return "REFUSED";
            }
            if (outcome == Outcome.INVALID) {
                return "INVALID";
            }
            return repaired ? "REPAIRED" : "OK";
        }
    }

    /** Speaker names; "Firm" and "Market maker" take a one-character label, so "Firm costs:" is prose. */
    private static final String TAGS = "(?:M\\d+|SYSTEM|YOU|ASSISTANT|USER|MARKET\\s+MAKER\\s+[A-Za-z0-9]|FIRM\\s+[A-Za-z0-9])";
    /** "M2:", "SYSTEM:", "**M2**:", "**M2:**", "[M2]:" - the colon is required, so "System-wide" is prose. */
    private static final Pattern TAG_COLON = Pattern.compile("^\\s*\\**\\s*\\[?" + TAGS + "\\]?\\**\\s*:\\s*\\**\\s*",
            Pattern.CASE_INSENSITIVE);
    /** "M2 - ": a spaced dash, seat labels only. */
    private static final Pattern TAG_DASH = Pattern.compile("^\\s*\\[?M\\d+\\]?\\s+[-–—]\\s+", Pattern.CASE_INSENSITIVE);
    private static final Pattern TAG_BRACKETED = Pattern.compile("^\\s*\\[\\s*" + TAGS + "\\s*\\]\\s*", Pattern.CASE_INSENSITIVE);
    private static final Pattern DIGIT = Pattern.compile("\\d");

    /** A first-person decline: "I can't", "I won't", "I'm unable to", "I won't be able to", "I refuse to", "I must decline to", ... */
    private static final String DECLINE_CORE = "(?:i(?:\\s+(?:can(?:'t|not|\\s+not)(?:\\s+and\\s+will\\s+not)?|won't(?:\\s+be\\s+able\\s+to)?|"
            + "will\\s+not(?:\\s+be\\s+able\\s+to)?|am\\s+(?:unable|not\\s+able|not\\s+going|not\\s+willing)|refuse|"
            + "(?:must|have\\s+to)\\s+(?:decline|refrain)|decline|do\\s+not\\s+feel\\s+comfortable|don't\\s+feel\\s+comfortable)"
            + "|'m\\s+(?:unable|not\\s+able|not\\s+going|not\\s+willing|not\\s+comfortable)|'m\\s+going\\s+to\\s+decline))";
    private static final String DECLINE = "\\b" + DECLINE_CORE + "\\s+(?:to\\s+|from\\s+)?";
    /** What a task-level decline is about: the request, the task, the scenario, the conversation, the game, the role-play. */
    private static final String TASK_NOUN = "(?:request|task|scenario|simulation|game|conversation|chat|discussion|role-?play|exercise|"
            + "prompt|instruction)s?";
    private static final String THIS = "(?:this|that|the|your|such\\s+a|such)\\s+";
    /** The end of the declining sentence: a full stop, "!" or the end of the message. A comma, "if", "unless" ... go on, so it is talk. */
    private static final String END = "\\s*(?:[.!]|$)";
    /** The ways to say "I will not do the job": all must end the sentence right after the object. */
    private static final String TASK_OBJECT = "(?:(?:help|assist)(?:(?:\\s+you)?\\s+with\\s+(?:(?:this|that|these|those)(?:\\s+" + TASK_NOUN
            + ")?|" + THIS + TASK_NOUN + "))?"
            + "|(?:(?:participat|engag|continu|proceed)(?:e|ing)?|take\\s+part)(?:\\s+(?:in|with))?"
            + "(?:\\s+(?:this|that)(?:\\s+" + TASK_NOUN + ")?|\\s+" + THIS + TASK_NOUN + ")?"
            + "|comply(?:ing)?(?:\\s+with\\s+(?:(?:this|that)(?:\\s+" + TASK_NOUN + ")?|" + THIS + TASK_NOUN + "))?"
            + "|(?:fulfil+|complete)\\s+(?:this|that|" + THIS + TASK_NOUN + ")"
            + "|(?:answer|respond\\s+to|play)\\s+" + THIS + TASK_NOUN
            + "|(?:pretend|role-?play)\\b[^.!?\\n]{0,40}"
            + "|" + THIS + TASK_NOUN + ")" + END;
    /** An apology or an AI self-description: the voice of an assistant, not of a market maker. */
    private static final String VOICE = "(?:(?:i'?m\\s+|i\\s+am\\s+|i\\s+)?(?:really\\s+|so\\s+|very\\s+|truly\\s+)?(?:sorry|afraid)|"
            + "i\\s+apologi[sz]e|apologies|unfortunately)";
    /** The task-verb objects of an apologetic decline ("help with X", "continue with this", "take part"). */
    private static final String VOICE_TASK_VERB = "(?:(?:help|assist|facilitate)(?:\\s+(?:you\\s+)?with\\s+[^.!?,;:\\n]{1,60})?"
            + "|(?:continu|proceed|participat|engag|comply|provid)\\w*(?:\\s+(?:with|in)\\s+(?:this|that|it)(?:\\s+" + TASK_NOUN + ")?)?"
            + "|facilitate\\s+[^.!?,;:\\n]{1,60}|take\\s+part(?:\\s+in\\s+(?:this|that))?)";
    /** A reason that names the task (law, policy, price fixing, being an AI), as opposed to the firm's own reasons. */
    private static final String TASK_CUE = "(?:illegal|unlawful|policy|policies|guidelines|price[- ]?fixing|collu|unethical|against\\s+my"
            + "|not\\s+allowed|not\\s+permitted|as\\s+an\\s+ai|language\\s+model)";
    /**
     * The talk-phase refusal (Q2 fix): the model declines the TASK, not a market move. Only assistant-style declines of the
     * job or the conversation count, each ending its sentence: "I can't help with this request.", "I will not participate in
     * this conversation.", "I cannot continue." and, in an apologetic or AI voice, "I'm sorry, but I can't help with
     * price fixing." or "As an AI I won't take part." A firm's statement about its own conduct is in-character talk and a
     * message, including refusing to collude ("I will not collude with you. Let's compete."), promises ("I won't do that
     * again"), threats, rejections of an offer ("I decline, your proposal is bad.", "I can't do that, my costs are too
     * high.") and price talk. Known ambiguity, accepted and logged: an apologetic one-liner such as "Sorry, I can't do that."
     * is read as a refusal, and an assistant refusal of collusion without an apology ("I can't help with price fixing.") is
     * read as the firm's own talk (an undercount of refusals, by design). In the apologetic voice a comma-reason tail
     * ("..., as it is illegal") counts only after a task verb (help, assist, facilitate, participate, comply, provide, take
     * part, continue) and only when the reason holds a task cue (illegal, policy, guidelines, price fixing, collusion, "against
     * my", "not allowed", "as an AI" ...); "Sorry, I can't do that, because you undercut me." stays a message. Accepted residual:
     * a firm's own reason that happens to hold a cue after a task verb ("Sorry, I can't continue, as price fixing is illegal")
     * is read as a refusal (so are firm-side uses of the weakest cues "policy" and "collusion" after a task verb, e.g. "Sorry, I can't
     * continue, as our policy is firm"; proceed and engage count as task verbs too), and a true assistant refusal after a bare
     * "do that" with a comma-reason ("Sorry, I can't do that, as it is illegal") or a non-cue reason is a message (an
     * undercount of refusals, by design). This differs on purpose from {@link DecisionParser#REFUSAL}, which stays for the quote call:
     * there a prose "I won't collude" in place of a quote is a refusal of the decision, while in talk it is a sentence of
     * the conversation.
     */
    static final Pattern TASK_REFUSAL = Pattern.compile("(?i)"
            + DECLINE + TASK_OBJECT
            // apologetic voice: a task-level object (help/assist/facilitate with something, continue, participate, comply, do that),
            // ending the sentence, or a task verb followed by a task-cue reason ("..., as it is illegal")
            + "|" + VOICE + "[,.]?\\s*(?:but\\s+)?" + "(?:" + DECLINE_CORE
            + "(?:(?:\\s+(?:to\\s+|from\\s+)?" + VOICE_TASK_VERB + "|\\s+(?:to\\s+|from\\s+)?(?:do\\s+(?:that|this)|that|this))?" + END
            // a comma-reason is a refusal only after a task verb and with a task cue in the reason
            + "|\\s+(?:to\\s+|from\\s+)?" + VOICE_TASK_VERB + ",\\s*(?:as|because|since)\\b[^.!?\\n]{0,80}?\\b" + TASK_CUE + ")"
            + ")"
            // AI voice
            + "|\\bas\\s+an?\\s+(?:ai|artificial\\s+intelligence|(?:ai\\s+)?language\\s+model|ai\\s+assistant)\\b[^.!?\\n]{0,80}?\\b"
            + "(?:can't|cannot|won't|will\\s+not|unable|not\\s+able|refuse|decline|do\\s+not\\s+engage|don't\\s+engage)\\b"
            // short assistant-style statements about the job
            + "|\\bunable\\s+to\\s+(?:assist|help|comply)\\b" + END
            + "|\\bi\\s+cannot\\s+and\\s+will\\s+not\\b[^.!?,\\n]{0,40}" + END
            + "|^\\W*i'?m\\s+not\\s+comfortable\\s+(?:with|doing|continuing|participating)(?:\\s+(?:in\\s+)?(?:this|that))?\\W*$");

    /** One reply, no repair: INVALID when it cannot be read. */
    public static Parsed parse(String reply) {
        if (reply == null || reply.isBlank()) {
            return invalid();
        }
        JsonNode n = DecisionParser.extractObject(reply);
        if (n == null) {
            return reply.indexOf('{') < 0 && refusalInMessage(reply) != null ? refused(reply, reply, "MODEL_TEXT", false) : invalid();
        }
        boolean done = isTrue(n.get("done"));
        String msg = n.path("message").isTextual() ? n.get("message").asText() : null;
        String logged = msg;
        if (msg != null && msg.strip().startsWith("{")) {
            JsonNode inner = DecisionParser.extractObject(msg);
            if (inner != null && inner.path("message").isTextual()) {
                done |= isTrue(inner.get("done"));
                msg = inner.get("message").asText();
            }
        }
        if (msg == null) {
            return done ? new Parsed(Outcome.DONE, null, null, null, null, false, false, false) : invalid();
        }
        boolean stripped = false;
        for (int i = 0; i < 5; i++) {
            int end = leadingTagEnd(msg);
            if (end < 0) {
                break;
            }
            msg = msg.substring(end);
            stripped = true;
        }
        if (msg.isBlank()) {
            return new Parsed(Outcome.DONE, null, logged, null, null, stripped, false, false);
        }
        String pattern = refusalInMessage(msg);
        if (pattern != null) {
            return new Parsed(Outcome.REFUSED, null, logged, pattern, "MODEL_DECLINE", stripped, false, false);
        }
        if (done) {
            return new Parsed(Outcome.DONE, null, logged, null, null, stripped, false, false);
        }
        return new Parsed(Outcome.MESSAGE, msg.strip(), logged, null, null, stripped, false, false);
    }

    /**
     * Parses the reply; on INVALID asks {@code repair} once for a second reply (the caller sends PromptBuilder.REPAIR_TEXT);
     * if that is INVALID too, or the supplier returns null, the result is "done", imputed. A null supplier means no repair
     * is possible. A refusal or a readable reply never triggers a repair.
     */
    public static Parsed parse(String reply, Supplier<String> repair) {
        Parsed first = parse(reply);
        if (first.outcome() != Outcome.INVALID) {
            return first;
        }
        if (repair != null) {
            Parsed second = parse(repair.get());
            if (second.outcome() != Outcome.INVALID) {
                return new Parsed(second.outcome(), second.message(), second.logged(), second.refusalPattern(),
                        second.refusalKind(), second.tagStripped(), true, false);
            }
        }
        return new Parsed(Outcome.DONE, null, null, null, "UNPARSEABLE", false, repair != null, true);
    }

    private static boolean isTrue(JsonNode d) {
        return d != null && (d.isBoolean() ? d.asBoolean() : d.isTextual() && d.asText().strip().equalsIgnoreCase("true"));
    }

    /** End of a leading speaker tag, or -1. */
    private static int leadingTagEnd(String msg) {
        for (Pattern p : new Pattern[] {TAG_COLON, TAG_DASH, TAG_BRACKETED}) {
            Matcher m = p.matcher(msg);
            if (m.find()) {
                return m.end();
            }
        }
        return -1;
    }

    /** The matched refusal text when a JSON message is itself a refusal (see the class comment), else null. */
    private static String refusalInMessage(String msg) {
        String text = DecisionParser.normalise(msg);
        Matcher m = TASK_REFUSAL.matcher(text);
        if (!m.find()) {
            return null;
        }
        String before = text.substring(0, m.start()).strip();
        boolean anchored = before.isEmpty() || before.split("\\s+").length <= 3;
        return anchored && !DIGIT.matcher(text.substring(m.end())).find() ? m.group().toLowerCase(Locale.ROOT).strip() : null;
    }

    private static Parsed invalid() {
        return new Parsed(Outcome.INVALID, null, null, null, null, false, false, false);
    }

    private static Parsed refused(String text, String logged, String kind, boolean stripped) {
        Matcher m = TASK_REFUSAL.matcher(DecisionParser.normalise(text));
        String pattern = m.find() ? m.group().toLowerCase(Locale.ROOT).strip() : "refusal";
        return new Parsed(Outcome.REFUSED, null, logged, pattern, kind, stripped, false, false);
    }
}
