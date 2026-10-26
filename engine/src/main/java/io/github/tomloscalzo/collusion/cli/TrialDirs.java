package io.github.tomloscalzo.collusion.cli;

import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.agents.llm.Condition;
import io.github.tomloscalzo.collusion.agents.llm.LlmSettings;
import io.github.tomloscalzo.collusion.agents.llm.ParaphraseFile;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.results.Manifest;
import io.github.tomloscalzo.collusion.trial.EventsWriter;
import io.github.tomloscalzo.collusion.trial.TrialParams;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * The trial directory of {@code run --seat LLM --trial-dir DIR} (C4.3, scope 4.6): params.json, written before the game,
 * and events.jsonl, written during it. Logging only: nothing here is read by the game, the prompts or the cache.
 */
final class TrialDirs {
    private TrialDirs() {}

    static final String PARAMS = "params.json";
    static final String EVENTS = "events.jsonl";

    /** The draw-key grammars of the calls a trial can make (proposal D3), recorded in params.json. */
    static final List<String> DRAW_KEYS = List.of("game|<scenario>|s<seed>|<seat>|r<round>|a<0|1>",
            "probe|<scenario>|s<seed>|<seat>|r<round>");
    /** With the talk phase (C5.5): turn = the round's talk calls so far, done turns included (TalkScheduler.Round.turn). */
    static final String TALK_DRAW_KEY = "talk|<scenario>|s<seed>|<seat>|r<round>|t<turn>|a<0|1>";
    /** With in-game questions (C13.3, QuestionKeys). */
    static final String QUESTION_DRAW_KEY = "question|<name>|fed|<scenario>|s<seed>|<seat>|r<round>|a0";
    /** With the post-game pass (C13.4). */
    static final String POST_DRAW_KEY = "question|<name>|post|<scenario>|s<seed>|<seat>|r<round>|a0";

    /**
     * A fresh events log in dir. A rerun in the same directory (run_grid.py retries there, reusing the cache) replaces
     * the earlier, incomplete log: the game is replayed from the cache, so the new log is the whole record.
     */
    static EventsWriter openEvents(Path dir) throws IOException {
        Files.createDirectories(dir);
        Files.deleteIfExists(dir.resolve(EVENTS));
        return new EventsWriter(dir.resolve(EVENTS));
    }

    /**
     * params.json. Beside the TrialParams keys (C4.1) it carries the keys collect.py reads first (model, penalty_point,
     * wording; C9.2) and multi_seat. thinking is null when --thinking is unset (no flag sent: the model's own default).
     * The competitive and collusive prices are the Nash margin and the monopoly margin, the ends of the collusion index.
     */
    static void writeParams(Path dir, Map<String, String> o, String scenario, String scenarioText, GameConfig cfg,
                            LlmSettings s, Condition cond, int paraphrase, long seed, String arm, boolean multiSeat,
                            boolean talk, io.github.tomloscalzo.collusion.texts.TextPlan texts,
                            io.github.tomloscalzo.collusion.agents.llm.CallSettingsMap calls, boolean questions, boolean post)
            throws IOException {
        writeParams(dir, o, scenario, scenarioText, cfg, s, cond, paraphrase, seed, arm, multiSeat, talk, texts, calls,
                questions, post, null);
    }

    /** clamp (unit U2; null = off): written as params.json "context_clamp" only when on. */
    static void writeParams(Path dir, Map<String, String> o, String scenario, String scenarioText, GameConfig cfg,
                            LlmSettings s, Condition cond, int paraphrase, long seed, String arm, boolean multiSeat,
                            boolean talk, io.github.tomloscalzo.collusion.texts.TextPlan texts,
                            io.github.tomloscalzo.collusion.agents.llm.CallSettingsMap calls, boolean questions, boolean post,
                            io.github.tomloscalzo.collusion.agents.llm.ContextClamp clamp)
            throws IOException {
        Path d = dir.toAbsolutePath().normalize();
        String trial = o.getOrDefault("trial-id", d.getFileName() == null ? "trial" : d.getFileName().toString());
        var m = cfg.scenario().market();
        Map<String, Object> market = new TreeMap<>();
        market.put("scenario_id", cfg.scenario().id());
        market.put("scenario", Canonical.MAPPER.convertValue(cfg.scenario(), Map.class));
        market.put("observation", Canonical.MAPPER.convertValue(cfg.observation(), Map.class));
        market.put("history", Canonical.MAPPER.convertValue(cfg.history(), Map.class));
        market.put("detection", Canonical.MAPPER.convertValue(cfg.detection(), Map.class));
        TrialParams.Builder b = TrialParams.builder(trial, arm).condition(cond.canonical()).market(market)
                .prices(PayoffFunctions.nashMargin(m), PayoffFunctions.monopolyMargin(m)).wording(paraphrase).seed(seed)
                .drawKeys(java.util.stream.Stream.of(DRAW_KEYS.stream(), talk ? java.util.stream.Stream.of(TALK_DRAW_KEY)
                        : java.util.stream.Stream.<String>empty(), questions ? java.util.stream.Stream.of(QUESTION_DRAW_KEY)
                        : java.util.stream.Stream.<String>empty(), post ? java.util.stream.Stream.of(POST_DRAW_KEY)
                        : java.util.stream.Stream.<String>empty()).flatMap(x -> x).toList())
                .sampling(s.temperature(), s.maxTokens(), Boolean.TRUE.equals(s.thinking()))
                .codeCommit(o.getOrDefault("code-commit", Manifest.currentGitCommit()))
                .scenarioFingerprint(Canonical.sha256(scenarioText.replace("\r\n", "\n")));
        Integer point = o.containsKey("penalty-point") ? Integer.valueOf(o.get("penalty-point")) : null;
        if (point != null) {
            b.penaltyPoint(point);
        }
        if (talk) {
            b.talkLimits(io.github.tomloscalzo.collusion.talk.TalkScheduler.MAX_MESSAGES,
                    io.github.tomloscalzo.collusion.talk.WordCap.MAX_WORDS);
        }
        ParaphraseFile.allHashes().forEach(b::promptFingerprint);
        if (texts != null) { // C11.2: the seat texts in this trial's prompts, and the text files in its fingerprint
            TrialTexts.hashes().forEach(b::promptFingerprint);
            for (var a : texts.assignments()) {
                var t = texts.library().get(a.name());
                b.conditionText(t.name(), t.slot().name(), t.text(), TrialTexts.seatsOf(a, cfg));
            }
        }
        for (AgentSpec a : cfg.agents()) {
            if (a.kind() == AgentKind.LLM) {
                b.seat(a.id(), "llm", null, s.modelSnapshot());
            } else {
                b.seat(a.id(), "scripted", a.kind().name() + (a.config().isEmpty() ? "" : " " + a.config()), null);
            }
        }
        ObjectNode n = b.build().toJson();
        n.put("model", s.modelSnapshot());
        n.put("wording", paraphrase);
        n.put("scenario_file", scenario);
        n.put("multi_seat", multiSeat);
        if (point != null) {
            n.put("penalty_point", point);
        }
        if (s.thinking() == null) {
            n.putNull("thinking");
        }
        if (calls != null) { // C12b.2: the per-call settings map (s = the quote call's effective settings)
            n.set("settings", Canonical.MAPPER.readTree(calls.toJson()));
        }
        var extra = texts == null ? null : TrialTexts.replyExtra(o.get("options")); // U8: the optional extra reply field
        if (extra != null) {
            ObjectNode re = n.putObject("reply_extra");
            re.put("name", extra.name());
            re.put("kind", extra.kind().name().toLowerCase(java.util.Locale.ROOT));
            if (extra.kind() == io.github.tomloscalzo.collusion.agents.llm.ReplyExtra.Kind.INTEGER) {
                re.put("min", extra.min());
                re.put("max", extra.max());
            } else {
                re.put("max_chars", extra.maxChars());
            }
            if (extra.last()) {
                re.put("position", "last"); // U21; absent = right after the quote (earlier params.json unchanged)
            }
            re.put("text_name", extra.textName());
            re.put("text", extra.text());
        }
        if (clamp != null) {
            n.set("context_clamp", Canonical.MAPPER.valueToTree(clamp));
        }
        // unit N1: written only when not anchored (absent = anchored, so earlier params.json bytes are unchanged)
        if (texts != null) {
            var pe = TrialTexts.payoffExamples(o.get("options"));
            if (pe != null && pe != io.github.tomloscalzo.collusion.agents.llm.PayoffExamples.ANCHORED) {
                n.put(io.github.tomloscalzo.collusion.agents.llm.PayoffExamples.OPTION, pe.optionValue());
            }
        }
        // unit E1: written only when on (absent = off, so earlier params.json bytes are unchanged)
        if (texts != null && TrialTexts.emptyTalkAsDone(o.get("options"))) {
            n.put(TrialTexts.EMPTY_TALK_OPTION, true);
        }
        // unit W2: written only when the option is given (absent = always, so earlier params.json bytes are unchanged)
        String qWhen = texts == null ? null : TrialTexts.questionWhen(o.get("options"));
        if (qWhen != null) {
            n.put("question_when", qWhen);
        }
        String qFeedback = texts == null ? null : TrialTexts.questionFeedback(o.get("options"));
        if (qFeedback != null) {
            n.put("question_feedback", qFeedback);
        }
        ObjectNode sampling = (ObjectNode) n.get("sampling");
        if (s.topP() != null) {
            sampling.put("top_p", s.topP());
        }
        if (s.topK() != null) {
            sampling.put("top_k", s.topK());
        }
        Files.createDirectories(dir);
        Files.writeString(dir.resolve(PARAMS), Canonical.text(n) + "\n", StandardCharsets.UTF_8);
    }
}
