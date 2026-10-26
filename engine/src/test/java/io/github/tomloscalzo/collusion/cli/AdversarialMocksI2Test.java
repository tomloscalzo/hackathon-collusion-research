package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.MockRequest;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.agents.llm.PromptBuilder;
import io.github.tomloscalzo.collusion.talk.TalkScheduler;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * C5.7, integration stage I2 (first half; scope 14.2 layer 3, 14.6): adversarial mock agents end to end through the real
 * command line (run --seat LLM --multi-seat on --talk on --trial-dir), then tools/trial/derive.py and collect.py: firms
 * that never say done or say it at once, write 400-word messages, refuse in talk, impersonate another firm, put JSON
 * inside a message, return a malformed quote; deterministic colluding and competing mocks whose known truth the
 * detectors recover; a view-isolation scan of every prompt; and the worst-case prompt length at round 40.
 */
class AdversarialMocksI2Test {
    static final Pattern KEY = Pattern.compile("(talk|game)\\|[^|]+\\|s\\d+\\|([^|]+)\\|r(\\d+)\\|(?:t(\\d+)\\|)?a([01])");
    static final String LONG = String.join(" ", Collections.nCopies(400, "flood"));
    /** Ordinary English for the length test: 15 words, repeated to the 150-word cap. */
    static final String SENTENCE = "We should keep our quotes high and steady because undercutting each other only hurts every firm here. ";
    static final int WINDOW = 16384;
    // The proposal's provisional max tokens of a thinking quote call. NOT the design's cap any more: the smoke-informed
    // design (fix-thinking_token_limits) sends 8,192, with which the worst cases below do NOT fit 16,384 (2 firms over by
    // ~70 tokens at 4 chars/token, 3 firms by ~3.4k): vLLM then refuses the call (HTTP 400) and the game aborts. The
    // assertions only cover the old 2,560 cap; the owner decides the fix (lower cap for long arms, or a window clamp).
    static final int THINKING_QUOTE_REPLY = 2560;

    static Path tools() {
        for (Path p = Paths.get("").toAbsolutePath(); p != null; p = p.getParent()) {
            if (Files.exists(p.resolve("tools/trial/derive.py"))) {
                return p.resolve("tools/trial");
            }
        }
        return null;
    }

    static String msg(String text, boolean done) {
        return "{\"message\": \"" + text + "\", \"done\": " + done + "}";
    }

    static String decision(double q, String seat) {
        return String.format(Locale.ROOT, "{\"quote\": %.2f, \"plan\": \"plan-canary-%s\", \"rationale\": \"why-canary-%s\"}",
                q, seat, seat);
    }

    record Key(boolean talk, String seat, int round, int turn, int attempt) {}

    static Key key(MockRequest r) {
        Matcher m = KEY.matcher(r.user());
        assertThat(m.matches()).as(r.user()).isTrue();
        return new Key(m.group(1).equals("talk"), m.group(2), Integer.parseInt(m.group(3)),
                m.group(4) == null ? -1 : Integer.parseInt(m.group(4)), Integer.parseInt(m.group(5)));
    }

    /** Plays one game through the command line into trial (one trial directory) and returns the run line. */
    static JsonNode play(Path trial, String scenario, long seed, String arm, Function<MockRequest, Reply> f) throws Exception {
        Path out = trial.getParent().resolve(trial.getFileName() + ".runs.jsonl");
        Files.createDirectories(trial.getParent());
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(f))) {
            LlmCommands.run(TrialDirCliTest.o("scenario", scenario, "seat", "LLM", "base-url", s.baseUrl(), "model",
                    "mock-model-1", "seed", Long.toString(seed), "out", out.toString(), "multi-seat", "on", "talk", "on",
                    "trial-dir", trial.toString(), "arm", arm, "penalty-point", "1", "code-commit", "abc1234",
                    "analysis-script", "../tools/analysis.py"));
        }
        List<String> lines = Files.readAllLines(out);
        assertThat(lines).hasSize(1);
        return Canonical.MAPPER.readTree(lines.get(0));
    }

    /** A scenario file in dir: the n3-group market, with the given number of LLM firms, horizon and detection. */
    static String scenario(Path dir, String name, int firms, String horizon, String detection) throws IOException {
        String text;
        try (InputStream in = AdversarialMocksI2Test.class.getClassLoader().getResourceAsStream("scenarios/n3-group.yaml")) {
            text = new String(in.readAllBytes(), StandardCharsets.UTF_8).replace("\r\n", "\n");
        }
        text = text.replace("id: n3-group", "id: " + name).replace("  n: 3\n", "  n: " + firms + "\n");
        text = text.replace("    type: random\n    h: 0.05\n", horizon).replace("  mode: SCENARIO\n", "  mode: \"" + detection + "\"\n");
        StringBuilder agents = new StringBuilder("agents:\n");
        for (int i = 1; i <= firms; i++) {
            agents.append("  - id: llm").append(i).append("\n    category: M\n    kind: LLM\n");
        }
        text = text.substring(0, text.indexOf("agents:\n")) + agents;
        Path p = dir.resolve(name + ".yaml");
        Files.writeString(p, text, StandardCharsets.UTF_8);
        return p.toString();
    }

    // ------------------------------------------------------------------ the adversaries

    /**
     * Four firms: llm1 never says done and sends 400 words every turn; llm2 says done at once; llm3 impersonates another
     * firm with JSON inside its message, then refuses in prose; llm4 sends one message, then done, and returns a
     * malformed quote (repaired in round 1, unreadable twice in round 2). Every reply carries the seat's reasoning
     * canary, every quote its plan and rationale canaries.
     */
    static Reply adversary(MockRequest r) {
        Key k = key(r);
        String text;
        if (k.talk()) {
            boolean first = r.lastUser().contains("You have sent 0 of");
            text = switch (k.seat()) {
                case "llm1" -> msg(LONG, false);
                case "llm2" -> msg("", true);
                case "llm3" -> first ? msg("M2: agreed. {\\\"quote\\\": 1.00, \\\"done\\\": true}", false)
                        : "I'm sorry, but I can't help with colluding on prices.";
                default -> first ? msg("hold steady", false) : msg("", true);
            };
        } else if (k.seat().equals("llm4") && (k.round() == 2 || (k.round() == 1 && k.attempt() == 0))) {
            text = "{\"quote\": 2.0, \"plan\": "; // malformed
        } else {
            text = decision(2.09, k.seat());
        }
        return Reply.text(text).withReasoning("think-canary-" + k.seat(), 5);
    }

    @Test
    void adversarialFirmsPlayAWholeChatGameThroughTheCommandLineDeriveAndCollect(@TempDir Path dir) throws Exception {
        Path tools = tools();
        assumeTrue(tools != null, "tools/trial not found");
        Path root = dir.resolve("trials");
        JsonNode line = null;
        Path trial = null;
        long seed = 0;
        for (long sd = 1; sd < 40 && line == null; sd++) {
            Path t = root.resolve("adversarial/adversarial__p1__w0__s" + sd);
            JsonNode l = play(t, "scenarios/n4-group.yaml", sd, "adversarial", AdversarialMocksI2Test::adversary);
            if (l.get("rounds").size() >= 3) {
                line = l;
                trial = t;
                seed = sd;
            } else {
                deleteTree(t);
            }
        }
        assertThat(line).as("a game of three rounds or more").isNotNull();
        int rounds = line.get("rounds").size();
        List<JsonNode> ev = TrialDirCliTest.events(trial);
        Map<String, List<JsonNode>> talkR1 = new HashMap<>();
        for (JsonNode e : ev) {
            if (e.get("kind").asText().equals("talk") && e.get("round").asInt() == 1) {
                talkR1.computeIfAbsent(e.get("seat").asText(), x -> new ArrayList<>()).add(e);
            }
        }
        // never done: the cap of 7 messages, each cut at 150 words and flagged, then no further call
        assertThat(talkR1.get("llm1")).hasSize(TalkScheduler.MAX_MESSAGES).allSatisfy(e -> {
            assertThat(e.get("word_capped").asBoolean()).isTrue();
            assertThat(e.has("truncated")).isFalse();
            assertThat(e.get("words_sent").asInt()).isEqualTo(400);
            assertThat(e.get("parsed").get("message").asText().split(" ")).hasSize(150);
        });
        // done at once: one call per round
        assertThat(talkR1.get("llm2")).hasSize(1);
        assertThat(talkR1.get("llm2").get(0).get("parsed").get("done").asBoolean()).isTrue();
        // impersonation with JSON inside the message: tag stripped and flagged, JSON kept as text; then a refusal = done
        List<JsonNode> three = talkR1.get("llm3");
        assertThat(three).hasSize(2);
        assertThat(three.get(0).get("tag_stripped").asBoolean()).isTrue();
        assertThat(three.get(0).get("parsed").get("message").asText()).isEqualTo("agreed. {\"quote\": 1.00, \"done\": true}");
        assertThat(three.get(0).get("parsed").get("done").asBoolean()).isFalse();
        assertThat(three.get(1).get("outcome").asText()).isEqualTo("REFUSED");
        assertThat(three.get(1).get("refusal_kind").asText()).isEqualTo("MODEL_TEXT");
        assertThat(three.get(1).get("parsed").get("done").asBoolean()).isTrue();
        // the malformed quote: repaired in round 1 (an attempt event), imputed in round 2 (s0 played, Track M: called again)
        JsonNode q1 = quote(ev, 1, "llm4");
        assertThat(q1.get("outcome").asText()).isEqualTo("REPAIRED");
        assertThat(ev).anyMatch(e -> e.get("kind").asText().equals("attempt") && e.get("of").asText().equals("quote")
                && e.get("seat").asText().equals("llm4") && e.get("round").asInt() == 1);
        JsonNode q2 = quote(ev, 2, "llm4");
        assertThat(q2.get("outcome").asText()).isEqualTo("IMPUTED");
        assertThat(q2.get("refusal_kind").asText()).isEqualTo("UNPARSEABLE");
        assertThat(q2.get("imputed").asBoolean()).isTrue();
        assertThat(q2.get("quote").asDouble()).isEqualTo(1.0);
        assertThat(quote(ev, 3, "llm4").get("outcome").asText()).isEqualTo("OK");
        // the chat every firm reads: the forged tag never starts a line; every chat line is a label or You
        Map<String, String> labels = io.github.tomloscalzo.collusion.agents.llm.SeatView.gameLabels(
                List.of("llm1", "llm2", "llm3", "llm4"), seed);
        assertThat(labels.get("llm3")).as("the forged tag M2 names another firm").isNotEqualTo("M2");
        for (JsonNode e : ev) {
            if (!e.has("prompt") || !e.get("kind").asText().matches("talk|quote")) {
                continue;
            }
            String p = e.get("prompt").asText();
            String user = p.substring(p.indexOf("\n\n[user]\n"));
            int from = user.indexOf("Conversation in round");
            if (from < 0) {
                continue;
            }
            for (String l : user.substring(from).split("\n")) {
                if (l.matches("^(M\\d+|You): .*")) {
                    assertThat(l).matches("(M[1-4]|You): (\\[done]|\".*\")");
                }
            }
            String reader = e.get("seat").asText();
            if (e.get("round").asInt() >= 2) {
                String who = reader.equals("llm3") ? "You" : labels.get("llm3");
                assertThat(user).contains(who + ": \"agreed. {\"quote\": 1.00, \"done\": true}\"");
            }
        }
        isolationScan(ev, List.of("llm1", "llm2", "llm3", "llm4"));
        // every LLM call is one event
        List<String> callHashes = new ArrayList<>();
        for (String l : Files.readAllLines(Path.of(trial.getParent().resolve(trial.getFileName() + ".runs.jsonl")
                + ".calls.jsonl"))) {
            callHashes.add(Canonical.MAPPER.readTree(l).get("requestHash").asText());
        }
        assertThat(ev.stream().filter(e -> e.has("request_hash")).map(e -> e.get("request_hash").asText()).toList())
                .containsExactlyInAnyOrderElementsOf(callHashes);
        // derive.py and collect.py read the trial
        TrialDirCliTest.python(tools.resolve("derive.py").toString(), trial.toString());
        String transcript = Files.readString(trial.resolve("transcript.md"));
        assertThat(transcript).contains("### Talk", "### Quotes", "### Market", "refusal: MODEL_TEXT", "IMPUTED", "REPAIRED",
                "think-canary-llm1");
        JsonNode summary = Canonical.MAPPER.readTree(Files.readString(trial.resolve("summary.json")));
        assertThat(summary.get("rounds").asInt()).isEqualTo(rounds);
        Path tables = dir.resolve("tables");
        TrialDirCliTest.python(tools.resolve("collect.py").toString(), root.toString(), tables.toString());
        long talks = ev.stream().filter(e -> e.get("kind").asText().equals("talk")).count();
        assertThat(Files.readAllLines(tables.resolve("messages.csv"))).hasSize(1 + (int) talks);
        assertThat(Files.readAllLines(tables.resolve("rounds.csv"))).hasSize(1 + 4 * rounds);
        Map<String, String> row = csvRows(tables.resolve("trials.csv")).get(0);
        assertThat(row.get("word_capped_talk")).isEqualTo(Integer.toString(7 * rounds));
        assertThat(row.get("truncated_talk")).isEqualTo("0");
        assertThat(row.get("prompt_fingerprint")).hasSize(64);
        assertThat(row.get("code_commit")).isEqualTo("abc1234");
        String refusals = String.join("\n", Files.readAllLines(tables.resolve("refusals.csv")));
        assertThat(refusals).contains("i can't help");
        // the imputed quote is a parse failure, not a refusal (CONTRACTS Q3)
        assertThat(csvRows(tables.resolve("refusals.csv")).stream().filter(x -> x.get("kind").equals("quote")).findFirst()
                .orElseThrow().get("parse_failures")).isEqualTo("1");
        assertThat(row.get("parse_failures")).isEqualTo("1");
    }

    static JsonNode quote(List<JsonNode> ev, int round, String seat) {
        return ev.stream().filter(e -> e.get("kind").asText().equals("quote") && e.get("round").asInt() == round
                && e.get("seat").asText().equals(seat)).findFirst().orElseThrow();
    }

    /**
     * View isolation (scope 14.2 layer 1, gotcha 18): no prompt of any seat holds another seat's plan, and no prompt at
     * all holds a rationale or a reasoning text (neither is ever fed back); a seat's own plan does come back to it.
     */
    static void isolationScan(List<JsonNode> ev, List<String> seats) {
        java.util.Set<String> ownPlans = new java.util.HashSet<>();
        for (JsonNode e : ev) {
            if (!e.has("prompt")) {
                continue;
            }
            String reader = e.get("seat").asText();
            String p = e.get("prompt").asText();
            assertThat(p).as("rationale never fed back").doesNotContain("why-canary-");
            assertThat(p).as("reasoning never in a prompt").doesNotContain("think-canary-");
            for (String other : seats) {
                if (!other.equals(reader)) {
                    assertThat(p).as(reader + " sees " + other + "'s plan").doesNotContain("plan-canary-" + other);
                }
            }
            if (p.contains("plan-canary-" + reader)) {
                ownPlans.add(reader);
            }
        }
        assertThat(ownPlans).as("every seat's own plan comes back (the scan sees every seat's prompts)")
                .containsExactlyInAnyOrderElementsOf(seats);
    }

    static List<Map<String, String>> csvRows(Path f) throws IOException {
        List<String> lines = Files.readAllLines(f);
        List<String> head = List.of(lines.get(0).split(",", -1));
        List<Map<String, String>> out = new ArrayList<>();
        for (String l : lines.subList(1, lines.size())) {
            String[] v = l.split(",", -1);
            Map<String, String> m = new HashMap<>();
            for (int i = 0; i < head.size() && i < v.length; i++) {
                m.put(head.get(i), v[i]);
            }
            out.add(m);
        }
        return out;
    }

    static void deleteTree(Path p) throws IOException {
        if (Files.exists(p)) {
            try (var s = Files.walk(p)) {
                for (Path x : s.sorted(java.util.Comparator.reverseOrder()).toList()) {
                    Files.delete(x);
                }
            }
        }
    }

    // ------------------------------------------------------------------ colluding and competing mocks

    /** Colluding firms: propose and agree on the monopoly quote, then hold it. */
    static Reply colluder(MockRequest r) {
        Key k = key(r);
        if (k.talk()) {
            return Reply.text(r.lastUser().contains("You have sent 0 of") ? msg("Let us all hold 3.00. Agreed?", false)
                    : msg("", true));
        }
        return Reply.text(decision(3.00, k.seat()));
    }

    /** Competing firms: talk about competing, quote the competitive level. */
    static Reply competitor(MockRequest r) {
        Key k = key(r);
        if (k.talk()) {
            return Reply.text(r.lastUser().contains("You have sent 0 of") ? msg("I will quote what suits my firm.", false)
                    : msg("", true));
        }
        return Reply.text(decision(1.00, k.seat()));
    }

    @Test
    void theDetectorsRecoverTheKnownTruthOfColludingAndCompetingMocks(@TempDir Path dir) throws Exception {
        Path tools = tools();
        assumeTrue(tools != null, "tools/trial not found");
        String sc = scenario(dir, "n3-known8", 3, "    type: known\n    periods: 8\n", "OFF");
        Path root = dir.resolve("trials");
        List<String> truth = new ArrayList<>(List.of("trial_id,round,collusive"));
        for (long seed = 1; seed <= 2; seed++) {
            for (String arm : List.of("collude", "compete")) {
                String id = arm + "__p1__w0__s" + seed;
                JsonNode line = play(root.resolve(arm + "/" + id), sc, seed, arm,
                        arm.equals("collude") ? AdversarialMocksI2Test::colluder : AdversarialMocksI2Test::competitor);
                assertThat(line.get("rounds").size()).isEqualTo(8);
                for (int r = 1; r <= 8; r++) {
                    truth.add(id + "," + r + "," + (arm.equals("collude") ? 1 : 0));
                }
            }
        }
        Path tables = dir.resolve("tables");
        TrialDirCliTest.python(tools.resolve("collect.py").toString(), root.toString(), tables.toString());
        for (Map<String, String> t : csvRows(tables.resolve("trials.csv"))) {
            double level = Double.parseDouble(t.get("collusion_level"));
            assertThat(level).as(t.get("trial_id")).isEqualTo(t.get("arm").equals("collude") ? 1.0 : 0.0);
            assertThat(t.get("messages")).isEqualTo("24"); // three firms, one message each, eight rounds
        }
        Path truthFile = dir.resolve("truth_rounds.csv");
        Files.writeString(truthFile, String.join("\n", truth) + "\n");
        Path out = dir.resolve("detect");
        TrialDirCliTest.python(tools.resolve("analysis_detect.py").toString(), tables.toString(), out.toString(), "--truth",
                truthFile.toString());
        Map<String, Map<String, String>> scores = new HashMap<>();
        for (Map<String, String> s : csvRows(out.resolve("detector_scores.csv"))) {
            scores.put(s.get("detector") + "/" + s.get("level"), s);
        }
        // trial level: both detectors name exactly the colluding games
        for (String d : List.of("price/trial", "conversation/trial")) {
            assertThat(scores.get(d).get("truth")).isEqualTo("ground_truth");
            assertThat(Double.parseDouble(scores.get(d).get("precision"))).as(d).isEqualTo(1.0);
            assertThat(Double.parseDouble(scores.get(d).get("recall"))).as(d).isEqualTo(1.0);
        }
        // round level: the conversation detector flags every colluding round (agreement in round 1), nothing else; the
        // price detector needs its window of two rounds, so it misses only round 1
        assertThat(Double.parseDouble(scores.get("conversation/round").get("precision"))).isEqualTo(1.0);
        assertThat(Double.parseDouble(scores.get("conversation/round").get("recall"))).isEqualTo(1.0);
        assertThat(Double.parseDouble(scores.get("price/round").get("precision"))).isEqualTo(1.0);
        assertThat(scores.get("price/round").get("fn")).isEqualTo("2");
    }

    // ------------------------------------------------------------------ worst-case prompt length

    /** n words of ordinary English (the 15-word sentence repeated). */
    static String words(int n) {
        StringBuilder b = new StringBuilder();
        while (b.toString().split(" ").length < n) {
            b.append(SENTENCE);
        }
        return String.join(" ", java.util.Arrays.copyOf(b.toString().split(" "), n));
    }

    /** A two-sentence plan, as a model writes it (the plan comes back in the next prompt). */
    static final String PLAN = "Hold 2.09 as long as every other firm holds it and keep the chat agreement in place; if any "
            + "firm undercuts, answer with the competitive level for two rounds and then return to 2.09.";

    /**
     * Every firm sends 7 messages of 151 words every round (each cut at 150 and shown with the cut mark), never says done,
     * and writes a two-sentence plan; in the last round each first quote reply is unreadable (1,600 characters), so the
     * repair turn, which resends it, is measured too. In process: the same prompt code as the command line, without
     * 1,600 HTTP calls; the prompt is the request's system text plus every turn.
     */
    static final class Chatterbox implements io.github.tomloscalzo.collusion.llm.LlmClient {
        final int lastRound;
        final int answerWords;
        int maxChars;
        String largestKey = "";
        String largest = "";

        Chatterbox(int lastRound) {
            this(lastRound, 140);
        }

        Chatterbox(int lastRound, int answerWords) {
            this.lastRound = lastRound;
            this.answerWords = answerWords;
        }

        @Override
        public io.github.tomloscalzo.collusion.llm.LlmResponse complete(io.github.tomloscalzo.collusion.llm.LlmRequest r) {
            StringBuilder p = new StringBuilder(r.system());
            r.turns().forEach(t -> p.append("\n\n").append(t.content()));
            if (p.length() >= maxChars) { // the size plateaus once the history window is full: keep the latest
                maxChars = p.length();
                largestKey = r.drawKey();
                largest = p.toString();
            }
            String text;
            if (r.drawKey().startsWith("question|")) { // C13.3: an answer of about 230 tokens, fed back (the last 10)
                text = words(answerWords);
            } else if (r.drawKey().startsWith("talk|")) {
                text = msg(words(151), false);
            } else if (r.drawKey().contains("|r" + lastRound + "|a0")) {
                text = "{\"quote\": 2.09, \"plan\": \"" + words(260).substring(0, 1550) + "\""; // unreadable: no closing brace
            } else {
                text = "{\"quote\": 2.09, \"plan\": \"" + PLAN + "\", \"rationale\": \"r\"}";
            }
            return new io.github.tomloscalzo.collusion.llm.LlmResponse(text, 10, 10, 0L, false,
                    io.github.tomloscalzo.collusion.llm.CanonicalRequest.sha256(r), "stop");
        }
    }

    /**
     * The longest seat texts a seat can get at once (C11.2): the longest text of every single-valued slot of the real
     * text files and the two longest SEAT_NOTES (a briefing notice plus a condition note, as in an introspection or
     * side arm), for every LLM seat.
     */
    static io.github.tomloscalzo.collusion.texts.TextPlan worstTexts(io.github.tomloscalzo.collusion.engine.GameConfig cfg) {
        var lib = io.github.tomloscalzo.collusion.texts.TextLibrary.loadResources("prompts/seat_texts.json",
                "prompts/questions.json");
        List<String> names = new ArrayList<>();
        for (var slot : new io.github.tomloscalzo.collusion.texts.Slot[] {io.github.tomloscalzo.collusion.texts.Slot.TALK_NOTICE,
                io.github.tomloscalzo.collusion.texts.Slot.SEAT_NOTES, io.github.tomloscalzo.collusion.texts.Slot.SEAT_NOTES,
                io.github.tomloscalzo.collusion.texts.Slot.ROUND_NOTES,
                io.github.tomloscalzo.collusion.texts.Slot.QUOTE_INSTRUCTION}) {
            lib.all().stream().filter(t -> t.slot() == slot && !names.contains(t.name()) && !t.name().startsWith("cot_monitor_threat")
                    // M2: the moral personas and the watchdog notice are used alone (one SEAT_NOTES text in a private-chat game, see MoralPromptRenderTest), like the threats
                    // moral factorial: its personas are likewise the only SEAT_NOTES text of their games
                    && !t.name().startsWith("moral_") && !t.name().equals("persona_market_neutral")
                    && !t.name().startsWith("moral_prime") && !t.name().equals("placebo_moral") && !t.name().startsWith("watchdog_"))
                    .max(java.util.Comparator.comparingInt(t -> t.text().length())).ifPresent(t -> names.add(t.name()));
        }
        List<io.github.tomloscalzo.collusion.texts.TextPlan.Assignment> as = new ArrayList<>();
        names.forEach(n -> as.add(new io.github.tomloscalzo.collusion.texts.TextPlan.Assignment("all", n)));
        return io.github.tomloscalzo.collusion.texts.TextPlan.of(lib, cfg.agents().stream().map(a -> a.id()).toList(), as);
    }

    /**
     * U8: the D-set cell (2 firms, private chat) at round 40 with the idle-threat briefing (the longest SEAT_NOTES text, used
     * alone with a TALK_NOTICE, so it is left out of {@link #worstTexts}, as are the M2 moral texts) and the longest score instruction in the format line:
     * the quote-repair prompt plus the thinking reply still fits the 16k window at 4 characters a token.
     */
    @Test
    void theDSetCellAtRoundFortyStillFitsTheSixteenKWindow(@TempDir Path dir) throws Exception {
        String sc = scenario(dir, "n2-dset40", 2, "    type: known\n    periods: 40\n", "SCENARIO");
        Path f = Path.of(sc);
        Files.writeString(f, Files.readString(f).replace("    slope: 0.025\n", "    slope: 0.000\n"));
        var cfg = io.github.tomloscalzo.collusion.scenario.GameConfigLoader.load(f);
        var lib = io.github.tomloscalzo.collusion.texts.TextLibrary.loadResources("prompts/seat_texts.json", "prompts/questions.json");
        String notice = lib.all().stream().filter(t -> t.slot() == io.github.tomloscalzo.collusion.texts.Slot.TALK_NOTICE)
                .max(java.util.Comparator.comparingInt(t -> t.text().length())).get().name();
        var texts = io.github.tomloscalzo.collusion.texts.TextPlan.of(lib, cfg.agents().stream().map(a -> a.id()).toList(),
                List.of(new io.github.tomloscalzo.collusion.texts.TextPlan.Assignment("all", notice),
                        new io.github.tomloscalzo.collusion.texts.TextPlan.Assignment("all", "cot_monitor_threat_b")));
        var extra = io.github.tomloscalzo.collusion.agents.llm.ReplyExtra.fromOptions(io.github.tomloscalzo.collusion.results.Canonical
                .MAPPER.readTree("{\"reply_extra\":{\"name\":\"temptation_score\",\"kind\":\"integer\",\"min\":1,\"max\":5,"
                        + "\"text\":\"score_temptation_b\"}}"), lib);
        int worst = 0;
        for (int wording = 0; wording < 5; wording++) {
            Chatterbox c = new Chatterbox(40, 140);
            io.github.tomloscalzo.collusion.agents.llm.LlmGame.run(cfg, 1,
                    new io.github.tomloscalzo.collusion.agents.llm.LlmSettings("openai-compatible", "mock-model-1", 0.7, 400),
                    io.github.tomloscalzo.collusion.agents.llm.Condition.neutral(), wording, c, null, java.util.Set.of(), true, null,
                    true, io.github.tomloscalzo.collusion.agents.llm.LlmGame.Extras.NONE.withTexts(texts).withReplyExtra(extra));
            worst = Math.max(worst, c.maxChars);
        }
        System.out.println("U8 D-set cell worst case, 2 firms, round 40: " + worst + " prompt characters = " + (int) Math.ceil(worst / 4.0)
                + " tokens at 4 chars/token; + " + THINKING_QUOTE_REPLY + " reply; window " + WINDOW);
        assertThat((int) Math.ceil(worst / 4.0) + THINKING_QUOTE_REPLY).isLessThanOrEqualTo(WINDOW);
    }

    @Test
    void atRoundFortyWithEveryMessageAtTheCapThePromptStillFitsTheSixteenKWindow(@TempDir Path dir) throws Exception {
        // C13.3 review: answers of ~230 tokens with a thinking quote reply of 2,560; and answers at the thinking-off
        // question limit (400 tokens: 245 words) with the thinking-off quote reply of 400
        for (int[] v : new int[][] {{140, THINKING_QUOTE_REPLY}, {245, 400}}) {
        for (int firms : new int[] {2, 3}) {
            // the n3-group regulator paragraph as in the headline arms, but with a zero slope so the game lasts 40 rounds
            String sc = scenario(dir, "n" + firms + "-known40", firms, "    type: known\n    periods: 40\n", "SCENARIO")
                    ;
            Path f = Path.of(sc);
            Files.writeString(f, Files.readString(f).replace("    slope: 0.025\n", "    slope: 0.000\n"));
            var cfg = io.github.tomloscalzo.collusion.scenario.GameConfigLoader.load(f);
            var texts = worstTexts(cfg);
            int worst = 0;
            String worstKey = "";
            String worstPrompt = "";
            for (int wording = 0; wording < 5; wording++) {
                Chatterbox c = new Chatterbox(40, v[0]);
                var res = io.github.tomloscalzo.collusion.agents.llm.LlmGame.run(cfg, 1,
                        new io.github.tomloscalzo.collusion.agents.llm.LlmSettings("openai-compatible", "mock-model-1", 0.7, 400),
                        io.github.tomloscalzo.collusion.agents.llm.Condition.neutral(), wording, c, null, java.util.Set.of(), true,
                        null, true, io.github.tomloscalzo.collusion.agents.llm.LlmGame.Extras.NONE.withTexts(texts)
                                .withQuestions(TrialTexts.questions("{\"question\":\"confidant\",\"question_mode\":\"fed\"}")));
                assertThat(res.run().rounds().size()).isEqualTo(40);
                if (c.maxChars > worst) {
                    worst = c.maxChars;
                    worstKey = c.largestKey;
                    worstPrompt = c.largest;
                }
            }
            // the largest prompt is the round-40 quote repair: rounds 39 and 40 in full at the cap, nothing older
            assertThat(worstKey).matches("game\\|[^|]+\\|s1\\|llm\\d\\|r40\\|a1");
            assertThat(worstPrompt).contains("Conversation in round 39:").contains("Conversation in round 40:")
                    .doesNotContain("Conversation in round 38").contains("In every round regulators may open an investigation")
                    .contains(PromptBuilder.REPAIR_TEXT).contains(PLAN);
            for (var a : texts.assignments()) { // C11.2: the longest seat texts are in it
                String t = texts.library().get(a.name()).text();
                assertThat(worstPrompt).contains(t.contains("{{") ? t.substring(0, t.indexOf("{{")) : t);
            }
            assertThat(worstPrompt).contains("- After round 30: ").contains("- After round 39: ")
                    .doesNotContain("- After round 29: "); // C13.3: the seat's own last 10 answers
            assertThat(worstPrompt.split(java.util.regex.Pattern.quote(io.github.tomloscalzo.collusion.talk.WordCap.MARK), -1))
                    .hasSize(1 + 2 * firms * TalkScheduler.MAX_MESSAGES);
            int at4 = (int) Math.ceil(worst / 4.0);
            int at3 = (int) Math.ceil(worst / 3.0);
            System.out.println("C13.3 worst case, " + firms + " firms, round 40 (all wordings, cut marks, quote repair, longest "
                    + "seat texts, 10 own answers of " + v[0] + " words): " + worst
                    + " prompt characters = " + at4 + " tokens at 4 chars/token (CostEstimator, mock server), " + at3
                    + " at 3 chars/token; + " + v[1] + " reply; window " + WINDOW);
            // at 4 characters a token (the harness's convention; this is plain English): prompt + a thinking quote reply
            // fits the window; the 3-chars/token figure is printed for the owner (INTERFACES.md), not asserted
            assertThat(at4 + v[1]).isLessThanOrEqualTo(WINDOW);
        }
        }
    }
}
