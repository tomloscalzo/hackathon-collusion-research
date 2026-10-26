package io.github.tomloscalzo.collusion.trial;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** C4.2: the events.jsonl writer. Field names are the contract with tools/trial/derive.py (CONTRACTS.md). */
class EventsWriterTest {
    private static List<JsonNode> read(Path f) throws IOException {
        List<JsonNode> out = new ArrayList<>();
        for (String l : Files.readAllLines(f, StandardCharsets.UTF_8)) {
            out.add(Canonical.MAPPER.readTree(l));
        }
        return out;
    }

    private static EventsWriter.Call call() {
        return new EventsWriter.Call("PROMPT", "REPLY", null, null, 900, 20, 800L, false, "h1", "talk|s|s1|a0|r1|t0|a0", "stop");
    }

    @Test
    void talkEventUsesDeriveFieldNames(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("events.jsonl");
        EventsWriter w = new EventsWriter(f);
        w.talk(1, 0, "a0", call(), "Hello", false, "OK", null, false);
        JsonNode e = read(f).get(0);
        assertThat(e.path("kind").asText()).isEqualTo("talk");
        assertThat(e.path("round").asInt()).isEqualTo(1);
        assertThat(e.path("seq").asInt()).isEqualTo(1);
        assertThat(e.path("turn").asInt()).isEqualTo(0);
        assertThat(e.path("seat").asText()).isEqualTo("a0");
        assertThat(e.path("parsed").path("message").asText()).isEqualTo("Hello");
        assertThat(e.path("parsed").path("done").asBoolean()).isFalse();
        assertThat(e.path("outcome").asText()).isEqualTo("OK");
        assertThat(e.path("prompt").asText()).isEqualTo("PROMPT");
        assertThat(e.path("reply").asText()).isEqualTo("REPLY");
        assertThat(e.path("tokens_in").asInt()).isEqualTo(900);
        assertThat(e.path("tokens_out").asInt()).isEqualTo(20);
        assertThat(e.path("latency_ms").asLong()).isEqualTo(800);
        assertThat(e.path("cache_hit").asBoolean()).isFalse();
        assertThat(e.path("request_hash").asText()).isEqualTo("h1");
        assertThat(e.path("draw_key").asText()).startsWith("talk|");
        assertThat(e.path("finish_reason").asText()).isEqualTo("stop");
        assertThat(e.has("reasoning")).isFalse();
        assertThat(e.has("truncated")).isFalse();
    }

    @Test
    void truncatedAndRefusedTalk(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        w.talk(2, 0, "a1", call(), "cut text", false, "TRUNCATED", null, true);
        w.talk(3, 1, "a1", call(), null, null, "REFUSED", "MODEL_TEXT", false);
        List<JsonNode> ev = read(f);
        assertThat(ev.get(0).path("truncated").asBoolean()).isTrue();
        assertThat(ev.get(0).path("outcome").asText()).isEqualTo("TRUNCATED");
        assertThat(ev.get(1).has("parsed")).isFalse();
        assertThat(ev.get(1).path("refusal_kind").asText()).isEqualTo("MODEL_TEXT");
        assertThat(ev.get(1).path("seq").asInt()).isEqualTo(2);
    }

    @Test
    void quoteEventCarriesQuotePlanRationaleAndImputed(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        w.quote(1, "a0", call(), 2.4, "Hold.", "Pays best.", "OK", null, false);
        w.quote(2, "a0", call(), 2.0, null, null, "IMPUTED", "UNPARSEABLE", true);
        w.quote(3, "a1", call(), null, null, null, "REFUSED", "MODEL_TEXT", false);
        List<JsonNode> ev = read(f);
        assertThat(ev.get(0).path("quote").asDouble()).isEqualTo(2.4);
        assertThat(ev.get(0).path("parsed").path("quote").asDouble()).isEqualTo(2.4);
        assertThat(ev.get(0).path("parsed").path("plan").asText()).isEqualTo("Hold.");
        assertThat(ev.get(0).path("parsed").path("rationale").asText()).isEqualTo("Pays best.");
        assertThat(ev.get(1).path("imputed").asBoolean()).isTrue();
        assertThat(ev.get(1).path("quote").asDouble()).isEqualTo(2.0);
        assertThat(ev.get(1).path("refusal_kind").asText()).isEqualTo("UNPARSEABLE");
        assertThat(ev.get(2).has("quote")).isFalse();
    }

    @Test
    void marketAndRegulatorEvents(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        Map<String, Double> prices = new LinkedHashMap<>(Map.of("a0", 2.0, "a1", 2.3));
        w.market(2, prices, Map.of("a0", 2.5, "a1", 0.0), "a0", 2.0);
        w.market(3, Map.of("a0", 2.0, "a1", 2.0), Map.of("a0", 0.4, "a1", 0.4), null, 2.0);
        w.regulator(2, "fine", null, Map.of("seat", "a0", "amount", 0.5));
        List<JsonNode> ev = read(f);
        assertThat(ev.get(0).path("kind").asText()).isEqualTo("market");
        assertThat(ev.get(0).path("prices").path("a1").asDouble()).isEqualTo(2.3);
        assertThat(ev.get(0).path("profits").path("a0").asDouble()).isEqualTo(2.5);
        assertThat(ev.get(0).path("winner").asText()).isEqualTo("a0");
        assertThat(ev.get(0).path("market_price").asDouble()).isEqualTo(2.0);
        assertThat(ev.get(1).has("winner")).isTrue();
        assertThat(ev.get(1).path("winner").isNull()).isTrue();
        assertThat(ev.get(2).path("kind").asText()).isEqualTo("regulator");
        assertThat(ev.get(2).path("event").asText()).isEqualTo("fine");
        assertThat(ev.get(2).path("seat").asText()).isEqualTo("a0");
        assertThat(ev.get(2).path("amount").asDouble()).isEqualTo(0.5);
    }

    @Test
    void questionAndReasoningFields(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        EventsWriter.Call c = new EventsWriter.Call("P", "R", "I thought about it.", 55, 400, 30, 10L, true, "h",
                "question|confidant|fed|c|s1|a0|r1|a0", "stop");
        w.question(1, "a0", "confidant", "fed", c, "I held 2.40.", "OK", null);
        JsonNode e = read(f).get(0);
        assertThat(e.path("kind").asText()).isEqualTo("question");
        assertThat(e.path("name").asText()).isEqualTo("confidant");
        assertThat(e.path("mode").asText()).isEqualTo("fed");
        assertThat(e.path("reply").asText()).isEqualTo("R");
        assertThat(e.path("parsed").path("message").asText()).isEqualTo("I held 2.40.");
        assertThat(e.path("reasoning").asText()).isEqualTo("I thought about it.");
        assertThat(e.path("reasoning_tokens").asInt()).isEqualTo(55);
        assertThat(e.path("cache_hit").asBoolean()).isTrue();
    }

    @Test
    void reasoningOnTalkAndQuoteToo(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        EventsWriter.Call c = new EventsWriter.Call("P", "R", "why", null, 1, 1, 1L, false, "h", "k", null);
        w.talk(1, 0, "a0", c, "m", false, "OK", null, false);
        w.quote(1, "a0", c, 2.0, "p", "r", "OK", null, false);
        for (JsonNode e : read(f)) {
            assertThat(e.path("reasoning").asText()).isEqualTo("why");
            assertThat(e.has("reasoning_tokens")).isFalse();
        }
    }

    @Test
    void loggingIsAPureSideEffect(@TempDir Path dir) throws Exception {
        Map<String, Double> prices = new LinkedHashMap<>(Map.of("a0", 2.0));
        Map<String, Double> copy = new LinkedHashMap<>(prices);
        Map<String, Object> extra = new LinkedHashMap<>(Map.of("x", 1));
        Map<String, Object> extraCopy = new LinkedHashMap<>(extra);
        EventsWriter w = new EventsWriter(dir.resolve("e.jsonl"));
        w.market(1, prices, prices, null, 2.0);
        w.regulator(1, "screen", "d", extra);
        assertThat(prices).isEqualTo(copy);
        assertThat(extra).isEqualTo(extraCopy);
        // a failing sink never throws into the game; the failure is kept for the caller to report
        Path blocker = dir.resolve("notadir");
        Files.writeString(blocker, "x");
        EventsWriter bad = new EventsWriter(blocker.resolve("events.jsonl"));
        bad.regulator(1, "screen", null, Map.of());
        bad.talk(1, 0, "a0", call(), "m", false, "OK", null, false);
        assertThat(bad.error()).isNotNull();
        assertThat(w.error()).isNull();
    }

    @Test
    void refusalPatternIsWrittenWhenGiven(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        EventsWriter.Call c = new EventsWriter.Call("P", "I cannot help", null, null, 1, 1, 1L, false, "h", "k", "stop", "i cannot");
        w.talk(1, 0, "a0", c, null, true, "REFUSED", "MODEL_TEXT", false);
        w.quote(1, "a0", c, null, null, null, "REFUSED", "MODEL_TEXT", false);
        w.question(1, "a0", "n", "fed", c, null, "REFUSED", "MODEL_TEXT");
        for (JsonNode e : read(f)) {
            assertThat(e.path("refusal_pattern").asText()).isEqualTo("i cannot");
            assertThat(e.path("refusal_kind").asText()).isEqualTo("MODEL_TEXT");
        }
        w.talk(2, 0, "a0", call(), "x", false, "OK", null, false);
        assertThat(read(f).get(3).has("refusal_pattern")).isFalse();
    }

    @Test
    void badArgumentsNeverThrowAndDoNotBurnASeq(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        w.talk(1, 0, "a0", null, "m", false, "OK", null, false);
        w.regulator(1, "x", null, null);
        assertThat(w.error()).isNotNull();
        w.talk(1, 1, "a0", call(), "m", false, "OK", null, false);
        assertThat(read(f)).hasSize(1);
        assertThat(read(f).get(0).path("seq").asInt()).isEqualTo(1);
    }

    @Test
    void regulatorExtraCannotOverwriteReservedKeys(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        w.regulator(4, "fine", null, Map.of("seq", 99, "kind", "talk", "round", 7, "event", "x", "amount", 1.5));
        JsonNode e = read(f).get(0);
        assertThat(e.path("seq").asInt()).isEqualTo(1);
        assertThat(e.path("kind").asText()).isEqualTo("regulator");
        assertThat(e.path("round").asInt()).isEqualTo(4);
        assertThat(e.path("event").asText()).isEqualTo("fine");
        assertThat(e.path("amount").asDouble()).isEqualTo(1.5);
    }

    @Test
    void nonFiniteNumbersAreWrittenAsNull(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        EventsWriter w = new EventsWriter(f);
        w.market(1, Map.of("a0", Double.NaN), Map.of("a0", Double.POSITIVE_INFINITY), null, Double.NaN);
        w.quote(1, "a0", call(), Double.NaN, null, null, "OK", null, false);
        for (String line : Files.readAllLines(f)) {
            assertThat(line).doesNotContain("NaN").doesNotContain("Infinity");
        }
        assertThat(read(f).get(0).path("market_price").isNull()).isTrue();
    }

    @Test
    void refusesToMixWithAnExistingLog(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("e.jsonl");
        Files.writeString(f, "{\"seq\":1}\n");
        assertThatThrownBy(() -> new EventsWriter(f)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void talkEventsCarryAnExplicitWordCapFlagApartFromTruncation(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("events.jsonl");
        EventsWriter w = new EventsWriter(f);
        w.talk(1, 0, "a0", call(), "cut text", false, "OK", null, false, true, Map.of("words_sent", 400));
        w.talk(1, 1, "a1", call(), "short", false, "OK", null, true, false, Map.of());
        w.talk(1, 2, "a0", call(), "", true, "OK", null, false);
        assertThat(w.error()).isNull();
        List<String> lines = Files.readAllLines(f);
        JsonNode a = Canonical.MAPPER.readTree(lines.get(0));
        JsonNode b = Canonical.MAPPER.readTree(lines.get(1));
        JsonNode c = Canonical.MAPPER.readTree(lines.get(2));
        assertThat(a.get("word_capped").asBoolean()).isTrue();
        assertThat(a.has("truncated")).isFalse();
        assertThat(a.get("words_sent").asInt()).isEqualTo(400);
        assertThat(b.get("word_capped").asBoolean()).isFalse();
        assertThat(b.get("truncated").asBoolean()).isTrue();
        assertThat(c.get("word_capped").isBoolean() && !c.get("word_capped").asBoolean()).isTrue();
    }

    @Test
    void deriveReadsTheWrittenFile(@TempDir Path dir) throws Exception {
        Path derive = null;
        for (Path p = Paths.get("").toAbsolutePath(); p != null && derive == null; p = p.getParent()) {
            if (Files.exists(p.resolve("tools/trial/derive.py"))) {
                derive = p.resolve("tools/trial/derive.py");
            }
        }
        assumeTrue(derive != null, "derive.py not found");
        Files.writeString(dir.resolve("params.json"), "{\"competitive_price\": 2.0, \"collusive_price\": 2.4}\n");
        EventsWriter w = new EventsWriter(dir.resolve("events.jsonl"));
        w.talk(1, 0, "a0", call(), "Let us keep 2.40.", false, "OK", null, false);
        w.talk(1, 1, "a1", call(), "", true, "OK", null, false);
        w.quote(1, "a0", call(), 2.4, "Hold.", "Pays.", "OK", null, false);
        w.quote(1, "a1", call(), 2.4, "Match.", "Agreed.", "OK", null, false);
        w.market(1, Map.of("a0", 2.4, "a1", 2.4), Map.of("a0", 1.2, "a1", 1.2), null, 2.4);
        w.regulator(1, "screen", "flagged", Map.of("flagged", true));
        w.question(1, "a0", "confidant", "fed", new EventsWriter.Call("P", "R", "deep thought", 3, 4, 5, 6L, false, "h", "k", null),
                "I held.", "OK", null);
        Process proc;
        try {
            proc = new ProcessBuilder("python", "-X", "utf8", derive.toString(), dir.toString()).redirectErrorStream(true).start();
        } catch (IOException e) {
            assumeTrue(false, "python not available");
            return;
        }
        String out = new String(proc.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        assertThat(proc.waitFor(60, TimeUnit.SECONDS)).isTrue();
        assertThat(proc.exitValue()).as(out).isEqualTo(0);
        assertThat(out).doesNotContain("warning");
        String transcript = Files.readString(dir.resolve("transcript.md"), StandardCharsets.UTF_8);
        assertThat(transcript).contains("a0 (4 words)", "Let us keep 2.40.", "done", "quote 2.40", "market price: 2.40",
                "screen", "confidant", "deep thought");
        JsonNode s = Canonical.MAPPER.readTree(Files.readString(dir.resolve("summary.json"), StandardCharsets.UTF_8));
        assertThat(s.path("collusion_level").asDouble()).isEqualTo(1.0);
        assertThat(s.path("seats").path("a0").path("tokens_in").asInt()).isEqualTo(900 + 900 + 4);
        assertThat(s.path("seats").path("a1").path("profit_total").asDouble()).isEqualTo(1.2);
    }
}
