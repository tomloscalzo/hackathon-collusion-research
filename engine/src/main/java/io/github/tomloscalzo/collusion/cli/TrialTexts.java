package io.github.tomloscalzo.collusion.cli;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.texts.TextLibrary;
import io.github.tomloscalzo.collusion.texts.Slot;
import io.github.tomloscalzo.collusion.texts.TextPlan;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * The seat texts of one trial from the command line (C11.2): {@code --condition-texts} is the grid's condition_texts cell
 * ({@code seat:name;seat:name}, seat {@code all} = every LLM seat) and {@code --options} the grid's options cell (JSON);
 * its round_reminder, quote_instruction and briefing_notice name texts for every LLM seat (CONTRACTS, lane J). A grid
 * seat name is a seat id of the scenario, or {@code llm<i>}, the i-th seat of the roster (make_grid.py numbers the
 * seats list from 1, scripted seats included). Texts are read from prompts/seat_texts.json and prompts/questions.json.
 * Neither option given: no plan (null), today's prompts.
 */
final class TrialTexts {
    private TrialTexts() {}

    static final List<String> RESOURCES = List.of("prompts/seat_texts.json", "prompts/questions.json");
    /** Option keys that name a seat text for every LLM seat. */
    static final List<String> TEXT_OPTIONS = List.of("briefing_notice", "round_reminder", "quote_instruction");
    /** The slot each text option must name (same order). */
    static final List<Slot> OPTION_SLOTS = List.of(Slot.SEAT_NOTES, Slot.ROUND_NOTES, Slot.QUOTE_INSTRUCTION);
    /** Option keys of the question calls (C13.3, C13.4): not played yet, so refused rather than ignored. */
    static final Set<String> QUESTION_OPTIONS = Set.of("question", "question_mode", "history_cap", "post_game_question",
            "question_when", "question_feedback");
    private static final Pattern POSITION = Pattern.compile("llm([1-9][0-9]*)");

    /** The plan of the run's options, or null when neither --condition-texts nor --options is given. */
    static TextPlan plan(Map<String, String> o, GameConfig cfg, boolean multiSeat) {
        String cell = o.get("condition-texts");
        String options = o.get("options");
        if (cell == null && options == null) {
            return null;
        }
        if (!multiSeat) {
            throw new IllegalArgumentException("--condition-texts and --options need --multi-seat on");
        }
        return plan(cell, options, cfg);
    }

    static TextPlan plan(String cell, String options, GameConfig cfg) {
        List<String> llm = cfg.agents().stream().filter(a -> a.kind() == AgentKind.LLM).map(AgentSpec::id).toList();
        TextLibrary lib = TextLibrary.loadResources(RESOURCES.toArray(String[]::new));
        List<TextPlan.Assignment> as = new ArrayList<>();
        for (TextPlan.Assignment a : TextPlan.parseCell(cell)) {
            if (lib.has(a.name()) && lib.get(a.name()).slot() == Slot.REPLY_FIELD) { // rendered only by --options reply_extra
                throw new IllegalArgumentException("--condition-texts: '" + a.name() + "' is a reply-field instruction, not a seat "
                        + "text (use --options reply_extra)");
            }
            if (lib.has(a.name()) && lib.get(a.name()).slot() == Slot.QUESTION) { // a question renders only in its call
                throw new IllegalArgumentException("--condition-texts: '" + a.name() + "' is a question, not a seat text "
                        + "(questions are --options question / post_game_question, C13.3)");
            }
            as.add(new TextPlan.Assignment(seat(a.seat(), cfg, llm), a.name()));
        }
        JsonNode opt = options(options);
        for (int i = 0; i < TEXT_OPTIONS.size(); i++) {
            String k = TEXT_OPTIONS.get(i);
            if (opt.has(k)) {
                String name = opt.get(k).asText();
                if (lib.get(name).slot() != OPTION_SLOTS.get(i)) {
                    throw new IllegalArgumentException("--options " + k + ": '" + name + "' is a " + lib.get(name).slot()
                            + " text, not " + OPTION_SLOTS.get(i));
                }
                as.add(new TextPlan.Assignment(TextPlan.ALL, name));
            }
        }
        return TextPlan.of(lib, llm, as);
    }

    /** Unit U17: the round-1 quote range of the options cell (start_ticks), or null when off (the default). */
    static io.github.tomloscalzo.collusion.agents.llm.StartRange startRange(String options) {
        return io.github.tomloscalzo.collusion.agents.llm.StartRange.fromOptions(options(options));

    }

    /** Unit E1: the option that reads an empty talk reply as done (gpt-oss only; the trial command sets it for those rows). */
    static final String EMPTY_TALK_OPTION = "empty_talk_as_done";

    /** True when the options cell has empty_talk_as_done "on" (or true); absent or "off" = false (today's rules). */
    static boolean emptyTalkAsDone(String options) {
        JsonNode n = options(options);
        return n.has(EMPTY_TALK_OPTION) && emptyTalkValue(n.get(EMPTY_TALK_OPTION));
    }

    private static boolean emptyTalkValue(JsonNode v) {
        if (v.isBoolean()) {
            return v.asBoolean();
        }
        if (v.isTextual() && (v.asText().equals("on") || v.asText().equals("off"))) {
            return v.asText().equals("on");
        }
        throw new IllegalArgumentException("--options " + EMPTY_TALK_OPTION + " must be on or off: " + v);
    }

    /** Unit N1: the payoff-example numbers of the options cell (payoff_examples), or null when absent (= anchored). */
    static io.github.tomloscalzo.collusion.agents.llm.PayoffExamples payoffExamples(String options) {
        return io.github.tomloscalzo.collusion.agents.llm.PayoffExamples.fromOptions(options(options));
    }

    /** The optional extra reply field of the options cell (U8, ReplyExtra); null without one. */
    static io.github.tomloscalzo.collusion.agents.llm.ReplyExtra replyExtra(String options) {
        return io.github.tomloscalzo.collusion.agents.llm.ReplyExtra.fromOptions(options(options),
                TextLibrary.loadResources(RESOURCES.toArray(String[]::new)));
    }

    /** The in-game (fed) questions of the options cell (C13.3; QuestionPlan); empty without a question. */
    static List<io.github.tomloscalzo.collusion.agents.llm.QuestionPlan.Entry> questions(String options) {
        options(options); // the same checks as the texts
        return io.github.tomloscalzo.collusion.agents.llm.QuestionPlan.fromOptionsJson(
                TextLibrary.loadResources(RESOURCES.toArray(String[]::new)), options).stream()
                .filter(io.github.tomloscalzo.collusion.agents.llm.QuestionPlan.Entry::fedBack).toList();
    }

    /** The post-game pass's question of the options cell (C13.4, post_game_question, mode post); empty without one. */
    static List<io.github.tomloscalzo.collusion.agents.llm.QuestionPlan.Entry> postQuestions(String options) {
        options(options);
        return io.github.tomloscalzo.collusion.agents.llm.QuestionPlan.fromOptionsJson(
                TextLibrary.loadResources(RESOURCES.toArray(String[]::new)), options).stream()
                .filter(q -> !q.fedBack()).toList();
    }

    /** Unit W2: the question_when value of the options cell ("always" or "non_competitive"), or null when the key is absent. */
    static String questionWhen(String options) {
        JsonNode n = options(options).get("question_when");
        if (n == null) {
            return null;
        }
        questions(options); // validates the value and that a question is set
        return n.asText();
    }

    /** Unit W2: the question_feedback value of the options cell ("fed" or "none"), or null when the key is absent. */
    static String questionFeedback(String options) {
        JsonNode n = options(options).get("question_feedback");
        if (n == null) {
            return null;
        }
        questions(options);
        return n.asText();
    }

    /** The options cell: a JSON object of known keys; empty or absent = {}. */
    static JsonNode options(String json) {
        if (json == null || json.isBlank()) {
            return Canonical.MAPPER.createObjectNode();
        }
        JsonNode n;
        try {
            n = Canonical.MAPPER.readTree(json);
        } catch (IOException e) {
            throw new IllegalArgumentException("--options is not valid JSON: " + e.getMessage(), e);
        }
        if (n == null || !n.isObject()) {
            throw new IllegalArgumentException("--options must be a JSON object: " + json);
        }
        n.fieldNames().forEachRemaining(k -> {
            if (TEXT_OPTIONS.contains(k)) {
                if (!n.get(k).isTextual() || n.get(k).asText().isBlank()) {
                    throw new IllegalArgumentException("--options " + k + " must name a seat text: " + n.get(k));
                }
            } else if (k.equals("reply_field")) {
                if (!n.get(k).isBoolean() || n.get(k).asBoolean()) { // owner decision 3: R1 adds no reply field
                    throw new IllegalArgumentException("--options reply_field must be false (R1 has no reply field)");
                }
            } else if (k.equals(io.github.tomloscalzo.collusion.agents.llm.StartRange.OPTION)) {
                io.github.tomloscalzo.collusion.agents.llm.StartRange.fromOptions(n); // U17: validated here
            } else if (k.equals(io.github.tomloscalzo.collusion.agents.llm.PayoffExamples.OPTION)) {
                io.github.tomloscalzo.collusion.agents.llm.PayoffExamples.fromOptions(n); // N1: validated here
            } else if (k.equals(EMPTY_TALK_OPTION)) {
                emptyTalkValue(n.get(k)); // E1: validated here
            } else if (k.equals("reply_extra")) {
                // validated by ReplyExtra.fromOptions (replyExtra), which also needs the text library
            } else if (k.equals("question_mode") && !n.get(k).asText().equals("fed")) {
                throw new IllegalArgumentException("--options question_mode must be fed in a game (post is the post-game pass)");
            } else if (QUESTION_OPTIONS.contains(k)) {
                // question, question_mode fed, history_cap: read by QuestionPlan (C13.3)
            } else {
                throw new IllegalArgumentException("--options has unknown key '" + k + "'");
            }
        });
        return n;
    }

    /**
     * A grid seat name as a seat id: all; llm&lt;i&gt; = the i-th roster seat, which must be an LLM seat (a scenario seat
     * with that id at another position is refused as ambiguous); else an LLM seat id.
     */
    static String seat(String name, GameConfig cfg, List<String> llm) {
        if (name.equals(TextPlan.ALL)) {
            return name;
        }
        Matcher m = POSITION.matcher(name);
        if (m.matches()) {
            int i = Integer.parseInt(m.group(1));
            if (i <= cfg.agents().size() && cfg.agents().get(i - 1).kind() == AgentKind.LLM) {
                String id = cfg.agents().get(i - 1).id();
                if (!id.equals(name) && cfg.agents().stream().anyMatch(a -> a.id().equals(name))) {
                    throw new IllegalArgumentException("--condition-texts seat '" + name + "' is ambiguous: roster seat " + i
                            + " is '" + id + "', and another seat has the id '" + name + "'");
                }
                return id;
            }
        } else if (llm.contains(name)) {
            return name;
        }
        throw new IllegalArgumentException("--condition-texts seat '" + name + "' is not an LLM seat of the scenario " + llm);
    }

    /** The seats a text applies to (all = every LLM seat), for params.json. */
    static List<String> seatsOf(TextPlan.Assignment a, GameConfig cfg) {
        if (!a.seat().equals(TextPlan.ALL)) {
            return List.of(a.seat());
        }
        return cfg.agents().stream().filter(x -> x.kind() == AgentKind.LLM).map(AgentSpec::id).toList();
    }

    /** SHA-256 (LF line ends) of each text file, for params.json's prompt fingerprints. */
    static Map<String, String> hashes() {
        Map<String, String> out = new TreeMap<>();
        for (String r : RESOURCES) {
            try (InputStream in = TrialTexts.class.getClassLoader().getResourceAsStream(r)) {
                if (in == null) {
                    throw new IllegalStateException("text file not found: " + r);
                }
                String name = r.substring(r.lastIndexOf('/') + 1, r.length() - ".json".length());
                out.put(name, Canonical.sha256(new String(in.readAllBytes(), StandardCharsets.UTF_8).replace("\r\n", "\n")));
            } catch (IOException e) {
                throw new IllegalStateException("cannot read " + r, e);
            }
        }
        return out;
    }
}
