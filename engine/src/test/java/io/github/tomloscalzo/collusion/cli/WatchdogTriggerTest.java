package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.agents.llm.Condition;
import io.github.tomloscalzo.collusion.agents.llm.LlmGame;
import io.github.tomloscalzo.collusion.agents.llm.LlmSettings;
import io.github.tomloscalzo.collusion.agents.llm.QuestionPlan;
import io.github.tomloscalzo.collusion.agents.llm.ReplyExtra;
import io.github.tomloscalzo.collusion.agents.llm.WatchdogTrigger;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import io.github.tomloscalzo.collusion.results.CallRecord;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import io.github.tomloscalzo.collusion.texts.TextLibrary;
import io.github.tomloscalzo.collusion.trial.EventsWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Unit W2: the options question_when and question_feedback. non_competitive asks firm i after round r only when its round-r
 * quote was not below the lowest other firm's round r-1 quote (unless that was the floor and the firm also quoted the floor):
 * the U16 rule. self_report_ge:k asks when the firm's own score is at least k. A round that is not asked writes no call, no
 * sink record and no question event, only a watchdog_check event. Absent or always = today's game, request for request. The
 * question text name here (confidant) is a placeholder: the real texts are data.
 */
class WatchdogTriggerTest {
    static final LlmSettings S = new LlmSettings("openai-compatible", "mock-model-1", 0.7, 300);
    static final Pattern KEY = Pattern.compile("(talk|game|question)\\|(?:confidant\\|fed\\|)?[^|]+\\|s\\d+\\|([^|]+)\\|r(\\d+)\\|.*");
    static final String OPT = "{\"question\":\"confidant\",\"question_mode\":\"fed\"";
    static final String ALWAYS = OPT + ",\"question_when\":\"always\"}";
    static final String NONCOMP = OPT + ",\"question_when\":\"non_competitive\"}";
    static final String PLAIN = OPT + "}";
    static final String SCORE_FIELD = ",\"reply_extra\":{\"name\":\"temptation_score\",\"kind\":\"integer\",\"min\":1,\"max\":5,"
            + "\"position\":\"last\",\"text\":\"score_temptation_a\"}";
    static final String SCORE = OPT + ",\"question_when\":\"self_report_ge:3\"" + SCORE_FIELD + "}";
    static final int ROUNDS = 9;
    /** quote table: seat -> quote in rounds 1..9 */
    static final Map<String, double[]> QUOTES = Map.of(
            "llm1", new double[] {2.00, 1.90, 1.90, 1.80, 1.50, 1.00, 1.00, 1.00, 1.50},
            "llm2", new double[] {2.00, 2.00, 1.80, 1.90, 1.50, 1.20, 1.00, 1.00, 1.00});
    /** score table (self_report_ge): seat -> score in rounds 1..9 */
    static final Map<String, int[]> SCORES = Map.of(
            "llm1", new int[] {1, 2, 3, 4, 5, 2, 1, 3, 2},
            "llm2", new int[] {5, 1, 1, 2, 3, 3, 2, 1, 4});

    /** Plays the tables. */
    static final class Table implements LlmClient {
        final List<LlmRequest> requests = new ArrayList<>();

        @Override
        public LlmResponse complete(LlmRequest r) {
            requests.add(r);
            Matcher m = KEY.matcher(r.drawKey());
            assertThat(m.matches()).as(r.drawKey()).isTrue();
            int round = Integer.parseInt(m.group(3));
            String text = switch (m.group(1)) {
                case "talk" -> "{\"message\": \"\", \"done\": true}";
                case "question" -> "I decided on my own. CANARY-" + m.group(2) + "-r" + m.group(3) + "-END";
                default -> "{\"quote\": " + QUOTES.get(m.group(2))[round - 1] + ", \"plan\": \"p\", \"rationale\": \"r\""
                        + (r.responseSchema() != null && r.responseSchema().contains("temptation_score")
                                ? ", \"temptation_score\": " + SCORES.get(m.group(2))[round - 1] : "") + "}";
            };
            return new LlmResponse(text, 10, 10, 0L, false, CanonicalRequest.sha256(r), "stop", null, null);
        }
    }

    static GameConfig game(Path dir) throws Exception {
        return GameConfigLoader.load(Path.of(AdversarialMocksI2Test.scenario(dir, "w2-known" + ROUNDS, 2,
                "    type: known\n    periods: " + ROUNDS + "\n", "OFF")));
    }

    static boolean competitive(double q, double t) {
        return q < t - 0.005 || (t <= 1.005 && q <= 1.005);
    }

    /** The rule written out again from the definition, independent of WatchdogTrigger: seat|rN of every triggered firm-round. */
    static TreeSet<String> expectedTriggered() {
        TreeSet<String> out = new TreeSet<>();
        for (String seat : QUOTES.keySet()) {
            String other = seat.equals("llm1") ? "llm2" : "llm1";
            for (int r = 2; r <= ROUNDS; r++) {
                if (!competitive(QUOTES.get(seat)[r - 1], QUOTES.get(other)[r - 2])) {
                    out.add(seat + "|r" + r);
                }
            }
        }
        return out;
    }

    static TreeSet<String> withoutLastRound(TreeSet<String> in) {
        TreeSet<String> out = new TreeSet<>(in);
        out.removeIf(s -> s.endsWith("|r" + ROUNDS));
        return out;
    }

    static Table play(Path dir, String options, EventsWriter ev, List<CallRecord> sink) throws Exception {
        Table t = new Table();
        LlmGame.Extras x = LlmGame.Extras.NONE.withQuestions(TrialTexts.questions(options));
        if (options.contains("reply_extra")) {
            TextLibrary lib = TextLibrary.loadResources("prompts/seat_texts.json", "prompts/questions.json");
            x = x.withReplyExtra(ReplyExtra.fromOptions(Canonical.MAPPER.readTree(options), lib));
        }
        LlmGame.run(game(dir), 3, S, Condition.neutral(), 0, t, sink == null ? null : sink::add, java.util.Set.of(), true, ev, true, x);
        return t;
    }

    static TreeSet<String> askedOf(Table t) {
        TreeSet<String> out = new TreeSet<>();
        for (LlmRequest r : t.requests) {
            Matcher m = KEY.matcher(r.drawKey());
            m.matches();
            if (m.group(1).equals("question")) {
                out.add(m.group(2) + "|r" + m.group(3));
            }
        }
        return out;
    }

    static List<JsonNode> events(Path file) throws Exception {
        List<JsonNode> out = new ArrayList<>();
        for (String l : Files.readAllLines(file)) {
            out.add(Canonical.MAPPER.readTree(l));
        }
        return out;
    }

    @Test
    void theU16RuleOnTheEdgeCases() {
        // round 1 and an unknown target: never eligible, never asked
        assertThat(WatchdogTrigger.check(1, 3.0, 2.0, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(false, false));
        assertThat(WatchdogTrigger.check(2, 3.0, null, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(false, false));
        // below the target by a tick: competitive, not asked; matching and above: asked
        assertThat(WatchdogTrigger.check(2, 1.99, 2.0, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(true, false));
        assertThat(WatchdogTrigger.check(2, 2.0, 2.0, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(true, true));
        assertThat(WatchdogTrigger.check(2, 2.5, 2.0, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(true, true));
        // float noise in a logged quote does not matter
        assertThat(WatchdogTrigger.check(2, 1.5899999999999999, 1.59, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(true, true));
        // target at the floor: quoting the floor is competitive, anything above it is not
        assertThat(WatchdogTrigger.check(3, 1.0, 1.0, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(true, false));
        assertThat(WatchdogTrigger.check(3, 1.01, 1.0, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(true, true));
        // a target one tick above the floor, the firm at the floor: an undercut, competitive
        assertThat(WatchdogTrigger.check(3, 1.0, 1.01, 1.0, 0.01)).isEqualTo(new WatchdogTrigger.Check(true, false));
        // the rating trigger: no valid score = not eligible; the threshold is inclusive
        assertThat(WatchdogTrigger.scoreCheck(null, 3)).isEqualTo(new WatchdogTrigger.Check(false, false));
        assertThat(WatchdogTrigger.scoreCheck(2, 3)).isEqualTo(new WatchdogTrigger.Check(true, false));
        assertThat(WatchdogTrigger.scoreCheck(3, 3)).isEqualTo(new WatchdogTrigger.Check(true, true));
        assertThat(WatchdogTrigger.threshold("self_report_ge:4")).isEqualTo(4);
        assertThat(WatchdogTrigger.threshold("self_report_ge:")).isNull();
        assertThat(WatchdogTrigger.threshold("always")).isNull();
    }

    @Test
    void nonCompetitiveAsksExactlyTheRoundsOfTheU16RuleAndUnaskedRoundsWriteNoCall(@TempDir Path dir) throws Exception {
        Path ev = dir.resolve("events.jsonl");
        List<CallRecord> sink = new ArrayList<>();
        Table t = play(dir, NONCOMP, new EventsWriter(ev), sink);
        TreeSet<String> triggered = expectedTriggered();
        // by hand from the quote table: llm1 matches llm2's 1.80 in round 4 and leaves the floor in round 9; llm2 matches llm1's
        // 2.00 in round 2 and 1.90 in round 4; llm1 at 1.00 against 1.00 in round 8 (the floor exception) and every undercut are competitive
        assertThat(triggered).containsExactly("llm1|r4", "llm1|r9", "llm2|r2", "llm2|r4");
        TreeSet<String> asked = withoutLastRound(triggered);
        assertThat(triggered).contains("llm1|r" + ROUNDS); // the last round triggers, and is the one not asked
        assertThat(asked).isNotEmpty().hasSizeLessThan(2 * (ROUNDS - 1));
        assertThat(askedOf(t)).isEqualTo(asked);
        assertThat(sink.stream().filter(c -> c.kind().equals("question")).count()).isEqualTo(asked.size());
        TreeSet<String> qev = new TreeSet<>();
        TreeMap<String, JsonNode> checks = new TreeMap<>();
        for (JsonNode e : events(ev)) {
            String k = e.get("kind").asText();
            String cell = e.has("seat") ? e.get("seat").asText() + "|r" + e.get("round").asInt() : "";
            assertThat(k).isNotEqualTo("question_skip");
            if (k.equals("question")) {
                qev.add(cell);
            } else if (k.equals("watchdog_check")) {
                assertThat(checks.put(cell, e)).as("one check per seat and round: " + cell).isNull();
                // a check is not a call: nothing that identifies or prices a model call
                assertThat(e.has("draw_key") || e.has("request_hash") || e.has("tokens_in") || e.has("prompt")
                        || e.has("reply") || e.has("outcome")).isFalse();
            }
        }
        assertThat(qev).isEqualTo(asked);
        assertThat(checks.keySet()).hasSize(2 * (ROUNDS - 1)); // every firm-round from round 2
        checks.forEach((cell, e) -> {
            assertThat(e.get("eligible").asBoolean()).isTrue();
            assertThat(e.get("triggered").asBoolean()).as(cell).isEqualTo(triggered.contains(cell));
            assertThat(e.get("asked").asBoolean()).as(cell).isEqualTo(asked.contains(cell));
            assertThat(e.get("when").asText()).isEqualTo("non_competitive");
        });
        // an answer is fed back only to its own seat, and only for the rounds it was asked: the firm knows it was questioned
        boolean fedSomewhere = false;
        for (LlmRequest r : t.requests) {
            Matcher m = KEY.matcher(r.drawKey());
            m.matches();
            Matcher c = Pattern.compile("CANARY-(llm\\d)-r(\\d+)-END").matcher(r.system() + r.turns().get(0).content());
            while (c.find()) {
                fedSomewhere = true;
                assertThat(c.group(1)).isEqualTo(m.group(2));
                assertThat(asked).contains(c.group(1) + "|r" + c.group(2));
            }
        }
        assertThat(fedSomewhere).isTrue();
    }

    @Test
    void anUntriggeredFirmMakesNoQuestionCall(@TempDir Path dir) throws Exception {
        // the table has rounds where one firm undercuts (competitive) while the other matches or is above
        TreeSet<String> asked = askedOf(play(dir, NONCOMP, null, null));
        assertThat(asked).anyMatch(s -> s.startsWith("llm1")).anyMatch(s -> s.startsWith("llm2"));
        assertThat(asked).doesNotContain("llm1|r2", "llm1|r3", "llm1|r6", "llm1|r7", "llm1|r8", "llm2|r3", "llm2|r6", "llm2|r7", "llm2|r8");
    }

    @Test
    void theJavaTriggerEqualsCompetitivenessPyOnTheSameQuotes(@TempDir Path dir) throws Exception {
        Path tools = AdversarialMocksI2Test.tools();
        org.junit.jupiter.api.Assumptions.assumeTrue(tools != null, "tools/trial not found");
        Path ev = dir.resolve("events.jsonl");
        play(dir, NONCOMP, new EventsWriter(ev), null);
        // the quotes exactly as the game logged them (events.jsonl quote events), as the rows competitiveness.py reads
        StringBuilder rows = new StringBuilder("[");
        for (JsonNode e : events(ev)) {
            if (e.get("kind").asText().equals("quote")) {
                rows.append(rows.length() > 1 ? "," : "").append("{\"round\":").append(e.get("round").asInt()).append(",\"seat\":\"")
                        .append(e.get("seat").asText()).append("\",\"quote\":").append(e.get("quote").asText()).append("}");
            }
        }
        rows.append("]");
        Path rowsFile = dir.resolve("rows.json");
        Files.writeString(rowsFile, rows.toString());
        Path script = dir.resolve("golden.py");
        Files.writeString(script, "import json, sys\nsys.path.insert(0, sys.argv[1])\nimport competitiveness as c\n"
                + "rows = json.load(open(sys.argv[2], encoding=\"utf-8\"))\nflags, _ = c.classify(rows, 1.0, 0.01)\n"
                + "print(json.dumps(sorted('%s|r%d' % (s, r) for (r, s), ok in flags.items() if not ok)))\n");
        String out = TrialDirCliTest.python(script.toString(), tools.toString(), rowsFile.toString()).strip();
        TreeSet<String> py = new TreeSet<>();
        Canonical.MAPPER.readTree(out.substring(out.indexOf('['))).forEach(n -> py.add(n.asText()));
        TreeSet<String> java = new TreeSet<>();
        for (JsonNode e : events(ev)) {
            if (e.get("kind").asText().equals("watchdog_check") && e.get("triggered").asBoolean()) {
                java.add(e.get("seat").asText() + "|r" + e.get("round").asInt());
            }
        }
        assertThat(py).isNotEmpty();
        assertThat(java).isEqualTo(py).isEqualTo(expectedTriggered());
    }

    @Test
    void selfReportGeAsksOnTheFirmsOwnScoreAtOrAboveK(@TempDir Path dir) throws Exception {
        Path ev = dir.resolve("events.jsonl");
        Table t = play(dir, SCORE, new EventsWriter(ev), null);
        TreeSet<String> triggered = new TreeSet<>();
        for (String seat : SCORES.keySet()) {
            for (int r = 1; r <= ROUNDS; r++) {
                if (SCORES.get(seat)[r - 1] >= 3) {
                    triggered.add(seat + "|r" + r);
                }
            }
        }
        assertThat(askedOf(t)).isEqualTo(withoutLastRound(triggered)).isNotEmpty();
        long checks = events(ev).stream().filter(e -> e.get("kind").asText().equals("watchdog_check")).count();
        assertThat(checks).isEqualTo(2 * ROUNDS); // round 1 can trigger a rating
        for (JsonNode e : events(ev)) {
            if (e.get("kind").asText().equals("watchdog_check")) {
                String cell = e.get("seat").asText() + "|r" + e.get("round").asInt();
                assertThat(e.get("triggered").asBoolean()).as(cell).isEqualTo(triggered.contains(cell));
                assertThat(e.get("score").asInt()).isEqualTo(SCORES.get(e.get("seat").asText())[e.get("round").asInt() - 1]);
            }
        }
    }

    @Test
    void questionFeedbackNoneLogsTheAnswerButNeverShowsItBack(@TempDir Path dir) throws Exception {
        Table fed = play(dir, NONCOMP, null, null);
        Table none = play(dir, OPT + ",\"question_when\":\"non_competitive\",\"question_feedback\":\"none\"}", null, null);
        assertThat(askedOf(none)).isEqualTo(askedOf(fed));
        assertThat(none.requests).noneMatch(r -> (r.system() + r.turns().get(0).content()).contains("CANARY-"));
        assertThat(fed.requests).anyMatch(r -> (r.system() + r.turns().get(0).content()).contains("CANARY-"));
    }

    @Test
    void absentAndAlwaysAreTheSameGameRequestForRequestWithNoWatchdogEvents(@TempDir Path dir) throws Exception {
        Path e1 = dir.resolve("a.jsonl");
        Path e2 = dir.resolve("b.jsonl");
        Table plain = play(dir, PLAIN, new EventsWriter(e1), null);
        Table always = play(dir, ALWAYS, new EventsWriter(e2), null);
        assertThat(always.requests.stream().map(CanonicalRequest::sha256).toList())
                .isEqualTo(plain.requests.stream().map(CanonicalRequest::sha256).toList());
        assertThat(askedOf(plain)).hasSize(2 * ROUNDS); // today asks every round, the last one included
        assertThat(Files.readString(e2)).isEqualTo(Files.readString(e1)).doesNotContain("watchdog_check").doesNotContain("question_skip");
        // the explicit feedback value fed is today's behaviour too
        Table fedExplicit = play(dir, OPT + ",\"question_feedback\":\"fed\"}", null, null);
        assertThat(fedExplicit.requests.stream().map(CanonicalRequest::sha256).toList())
                .isEqualTo(plain.requests.stream().map(CanonicalRequest::sha256).toList());
        // round 1 is identical with the trigger on (no question has been asked yet)
        Table nc = play(dir, NONCOMP, new EventsWriter(dir.resolve("c.jsonl")), null);
        assertThat(nc.requests).hasSizeLessThan(plain.requests.size());
        assertThat(nc.requests.stream().filter(r -> r.drawKey().startsWith("game|") && r.drawKey().contains("|r1|"))
                .map(CanonicalRequest::sha256).toList())
                .isEqualTo(plain.requests.stream().filter(r -> r.drawKey().startsWith("game|") && r.drawKey().contains("|r1|"))
                        .map(CanonicalRequest::sha256).toList());
    }

    @Test
    void theOptionsAreChecked() {
        assertThatThrownBy(() -> TrialTexts.questions("{\"question_when\":\"non_competitive\"}"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("question_when without a question");
        assertThatThrownBy(() -> TrialTexts.questions("{\"question_feedback\":\"none\"}"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("question_feedback without a question");
        assertThatThrownBy(() -> TrialTexts.questions(OPT + ",\"question_when\":\"sometimes\"}"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("question_when must be");
        assertThatThrownBy(() -> TrialTexts.questions(OPT + ",\"question_when\":true}"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrialTexts.questions("{\"question\":\"confidant\",\"question_mode\":\"post\",\"question_when\":\"non_competitive\"}"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrialTexts.questions("{\"question\":\"confidant\",\"question_mode\":\"post\",\"question_feedback\":\"none\"}"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrialTexts.questions(OPT + ",\"question_feedback\":\"saved\"}"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("question_feedback must be");
        // the rating trigger needs an integer reply field with k inside its range
        assertThatThrownBy(() -> TrialTexts.questions(OPT + ",\"question_when\":\"self_report_ge:3\"}"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("needs a reply_extra");
        assertThatThrownBy(() -> TrialTexts.questions(SCORE.replace("self_report_ge:3", "self_report_ge:9")))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("inside its range");
        assertThat(TrialTexts.questions(SCORE).get(0).scoreThreshold()).isEqualTo(3);
        List<QuestionPlan.Entry> q = TrialTexts.questions(NONCOMP);
        assertThat(q).hasSize(1);
        assertThat(q.get(0).nonCompetitiveOnly()).isTrue();
        assertThat(q.get(0).conditional()).isTrue();
        assertThat(TrialTexts.questions(ALWAYS).get(0).conditional()).isFalse();
        assertThat(TrialTexts.questions(PLAIN).get(0).conditional()).isFalse();
        assertThat(TrialTexts.questions(PLAIN).get(0).shown()).isTrue();
        assertThat(TrialTexts.questions(OPT + ",\"question_feedback\":\"none\"}").get(0).shown()).isFalse();
        assertThat(TrialTexts.questionWhen(PLAIN)).isNull();
        assertThat(TrialTexts.questionWhen(ALWAYS)).isEqualTo("always");
        assertThat(TrialTexts.questionWhen(NONCOMP)).isEqualTo("non_competitive");
        assertThat(TrialTexts.questionFeedback(PLAIN)).isNull();
        assertThat(TrialTexts.questionWhen("{}")).isNull();
        // the post-game pass is never conditional: question_when needs an in-game question
        assertThatThrownBy(() -> TrialTexts.postQuestions("{\"post_game_question\":\"confidant\",\"question_when\":\"non_competitive\"}"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("question_when without a question");
    }
}
