package io.github.tomloscalzo.collusion.agents.llm;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.texts.SeatText;
import io.github.tomloscalzo.collusion.texts.Slot;
import io.github.tomloscalzo.collusion.texts.TextLibrary;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Which questions a trial asks, from the grid row's {@code options} JSON and the questions file (C13.1; proposal groups D
 * and F). Option keys (trackm_design.yaml): {@code question} (a question name), {@code question_mode} (fed, the default,
 * or post), {@code history_cap} (if given, must equal {@link SeatView#ANSWER_WINDOW}), and {@code post_game_question} (a
 * question name asked in the post-game pass, mode post). The text of each question is the QUESTION-slot text of that name
 * in the library. No option means no question calls, so prompts and fingerprints stay as they are today. Pure.
 */
public final class QuestionPlan {
    /** One question call kind: the name, how it is asked, and its text. */
    public record Entry(String name, QuestionKeys.Mode mode, String text, String when, boolean feedback) {
        /** An entry asked every round and fed back (the default; question_when and question_feedback absent). */
        public Entry(String name, QuestionKeys.Mode mode, String text) {
            this(name, mode, text, WatchdogTrigger.ALWAYS, true);
        }

        /** True when the question is asked only after a non-competitive round (question_when non_competitive). */
        public boolean nonCompetitiveOnly() { return WatchdogTrigger.NON_COMPETITIVE.equals(when); }

        /** k when the question is asked only after a self-report score of at least k (question_when self_report_ge:k), else null. */
        public Integer scoreThreshold() { return WatchdogTrigger.threshold(when); }

        /** True when question_when is anything but always: each round is checked and logged, the last round is not asked. */
        public boolean conditional() { return !WatchdogTrigger.ALWAYS.equals(when); }

        /** True when the answer is recorded in the seat's own view and shown back in its later prompts (fed mode and feedback on). */
        public boolean shown() { return fedBack() && feedback; }

        /** The draw key of this question for a seat and round. */
        public String drawKey(String scenario, long seed, String seat, int round) {
            return QuestionKeys.key(name, mode, scenario, seed, seat, round);
        }

        /** True when the seat's answer is shown back to it in its later prompts (only the in-game "fed" mode). */
        public boolean fedBack() { return mode == QuestionKeys.Mode.FED; }
    }

    private static final Set<String> KEYS = Set.of("question", "question_mode", "history_cap", "post_game_question",
            "question_when", "question_feedback");

    private QuestionPlan() {}

    /** The questions named in the options (in the order question, then post_game_question); empty when none. */
    public static List<Entry> fromOptionsJson(TextLibrary library, String optionsJson) {
        List<Entry> out = new ArrayList<>();
        if (optionsJson == null || optionsJson.isBlank()) {
            return out;
        }
        JsonNode o;
        try {
            o = Canonical.MAPPER.readTree(optionsJson);
        } catch (IOException e) {
            throw new IllegalArgumentException("options is not valid JSON: " + e.getMessage(), e);
        }
        if (o == null || !o.isObject()) {
            throw new IllegalArgumentException("options must be a JSON object");
        }
        // options also carry keys of other features (round_reminder, quote_instruction, ...): only ours are read
        if (o.has("history_cap")) {
            if (!o.get("history_cap").isIntegralNumber() || o.get("history_cap").asInt(-1) != SeatView.ANSWER_WINDOW) {
                throw new IllegalArgumentException("history_cap must be the number " + SeatView.ANSWER_WINDOW);
            }
            if (!o.has("question")) {
                throw new IllegalArgumentException("history_cap without a question");
            }
        }
        if (o.has("question_mode") && !o.has("question")) {
            throw new IllegalArgumentException("question_mode without a question");
        }
        String when = WatchdogTrigger.ALWAYS;
        if (o.has("question_when")) { // unit W2: absent = always, byte-identical to before
            if (!o.has("question")) {
                throw new IllegalArgumentException("question_when without a question");
            }
            JsonNode w = o.get("question_when");
            if (!w.isTextual() || !(w.asText().equals(WatchdogTrigger.ALWAYS) || w.asText().equals(WatchdogTrigger.NON_COMPETITIVE)
                    || WatchdogTrigger.threshold(w.asText()) != null)) {
                throw new IllegalArgumentException("question_when must be 'always', 'non_competitive' or 'self_report_ge:<k>': " + w);
            }
            when = w.asText();
            if (o.has("question_mode") && !"fed".equals(o.get("question_mode").asText())) {
                throw new IllegalArgumentException("question_when needs an in-game (fed) question, not mode " + o.get("question_mode").asText());
            }
            Integer k = WatchdogTrigger.threshold(when);
            if (k != null) {
                ReplyExtra re = ReplyExtra.fromOptions(o, library);
                if (re == null || re.kind() != ReplyExtra.Kind.INTEGER || k < re.min() || k > re.max()) {
                    throw new IllegalArgumentException("question_when self_report_ge:" + k
                            + " needs a reply_extra of kind integer with " + k + " inside its range");
                }
            }
        }
        boolean feedback = true;
        if (o.has("question_feedback")) { // unit W2: fed (default, today's behaviour) or none (the answer is logged, never shown back)
            if (!o.has("question")) {
                throw new IllegalArgumentException("question_feedback without a question");
            }
            if (o.has("question_mode") && !"fed".equals(o.get("question_mode").asText())) {
                throw new IllegalArgumentException("question_feedback needs an in-game (fed) question, not mode " + o.get("question_mode").asText());
            }
            String f = o.get("question_feedback").isTextual() ? o.get("question_feedback").asText() : "";
            if (!f.equals("fed") && !f.equals("none")) {
                throw new IllegalArgumentException("question_feedback must be 'fed' or 'none': " + o.get("question_feedback"));
            }
            feedback = f.equals("fed");
        }
        if (o.has("question")) {
            QuestionKeys.Mode mode = o.has("question_mode") ? QuestionKeys.Mode.ofTag(o.get("question_mode").asText()) : QuestionKeys.Mode.FED;
            Entry e = entry(library, o.get("question").asText(), mode);
            out.add(new Entry(e.name(), e.mode(), e.text(), when, feedback));
        }
        if (o.has("post_game_question")) { // C13.4: a name, or a list of names (the R0 comparison asks both questions)
            JsonNode p = o.get("post_game_question");
            if (p.isArray()) {
                if (p.isEmpty()) {
                    throw new IllegalArgumentException("post_game_question is an empty list");
                }
                for (JsonNode n : p) {
                    if (!n.isTextual()) {
                        throw new IllegalArgumentException("post_game_question must hold question names: " + p);
                    }
                    out.add(entry(library, n.asText(), QuestionKeys.Mode.POST));
                }
            } else if (p.isTextual()) {
                out.add(entry(library, p.asText(), QuestionKeys.Mode.POST));
            } else {
                throw new IllegalArgumentException("post_game_question must be a question name or a list of names: " + p);
            }
        }
        for (int i = 0; i < out.size(); i++) {
            for (int j = i + 1; j < out.size(); j++) {
                if (out.get(i).name().equals(out.get(j).name()) && out.get(i).mode() == out.get(j).mode()) {
                    throw new IllegalArgumentException("question '" + out.get(i).name() + "' is asked twice in mode "
                            + out.get(i).mode().tag());
                }
            }
        }
        return out;
    }

    private static Entry entry(TextLibrary library, String name, QuestionKeys.Mode mode) {
        if (!library.has(name)) {
            throw new IllegalArgumentException("unknown question '" + name + "'");
        }
        if (!QuestionKeys.validName(name)) {
            throw new IllegalArgumentException("question name '" + name + "' cannot be used in a draw key");
        }
        SeatText t = library.get(name);
        if (t.slot() != Slot.QUESTION) {
            throw new IllegalArgumentException("text '" + name + "' is not a question (slot " + t.slot() + ")");
        }
        if (t.text().isBlank()) {
            throw new IllegalArgumentException("question '" + name + "' has no text");
        }
        return new Entry(name, mode, t.text());
    }

    /** The option keys this class reads (a caller can tell them from the keys of other features). */
    public static Set<String> optionKeys() { return KEYS; }
}
