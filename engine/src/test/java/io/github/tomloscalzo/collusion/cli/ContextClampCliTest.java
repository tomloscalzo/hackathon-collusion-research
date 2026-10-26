package io.github.tomloscalzo.collusion.cli;

import static io.github.tomloscalzo.collusion.cli.TruncatedThinkingTest.DECISION;
import static io.github.tomloscalzo.collusion.cli.TruncatedThinkingTest.game;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.MockRequest;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.function.Function;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Unit U2, the context clamp end to end on the mock server: off = byte-identical requests, call records, cache and
 * digest; on with an unreachable limit = the same; on with a tight window = max_tokens lowered or the call not sent, the
 * round imputed as truncated, every binding logged in events.jsonl and on the call record, prompt + max_tokens never
 * above window - margin, and a replay of the run line reproduces the digest.
 */
class ContextClampCliTest {
    static final String SCEN = "scenarios/n3-group.yaml";
    static final Function<MockRequest, Reply> OK = game(q -> Reply.text(DECISION));

    static int maxTokens(MockRequest r) {
        try {
            return Canonical.MAPPER.readTree(r.rawBody()).get("max_tokens").asInt();
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    /** The estimate of the clamp for a request as the server saw it (default chars per token 3.0). */
    static int estimate(MockRequest r) {
        long chars = r.system().length();
        for (var t : r.turns()) {
            chars += t.content().length();
        }
        return (int) Math.ceil(chars / 3.0) + 16 + 8 * (1 + r.turns().size());
    }

    static String digest(TruncatedThinkingTest.Run r) throws Exception {
        return Canonical.MAPPER.readTree(Files.readAllLines(r.out()).get(0)).get("replayDigest").asText();
    }

    static List<JsonNode> clampEvents(Path trial) throws Exception {
        return TrialDirCliTest.events(trial).stream().filter(e -> e.get("kind").asText().equals("context_clamp")).toList();
    }

    static List<String> lines(Path file) throws Exception {
        return Files.readAllLines(file).stream().map(c -> c.replaceAll("\"latencyMs\":\\d+", "")).toList();
    }

    @Test
    void offAndAnUnreachableLimitSendTheSameBytesAndWriteTheSameRecords(@TempDir Path dir) throws Exception {
        var base = TruncatedThinkingTest.run(dir, "base", SCEN, true, OK, "thinking", "on");
        var off = TruncatedThinkingTest.run(dir, "off", SCEN, true, OK, "thinking", "on", "context-clamp", "off");
        var huge = TruncatedThinkingTest.run(dir, "huge", SCEN, true, OK, "thinking", "on", "context-clamp", "on",
                "context-window", "100000000", "context-margin", "0");
        List<String> bodies = base.requests().stream().map(MockRequest::rawBody).toList();
        assertThat(off.requests().stream().map(MockRequest::rawBody).toList()).isEqualTo(bodies);
        assertThat(huge.requests().stream().map(MockRequest::rawBody).toList()).isEqualTo(bodies);
        assertThat(digest(off)).isEqualTo(digest(base));
        assertThat(digest(huge)).isEqualTo(digest(base));
        List<String> calls = lines(Path.of(base.out() + ".calls.jsonl"));
        assertThat(calls).isNotEmpty().noneMatch(c -> c.contains("clamp"));
        assertThat(lines(Path.of(off.out() + ".calls.jsonl"))).isEqualTo(calls);
        assertThat(lines(Path.of(huge.out() + ".calls.jsonl"))).isEqualTo(calls);
        assertThat(lines(Path.of(off.out() + ".cache.jsonl"))).isEqualTo(lines(Path.of(base.out() + ".cache.jsonl")));
        assertThat(lines(Path.of(huge.out() + ".cache.jsonl"))).isEqualTo(lines(Path.of(base.out() + ".cache.jsonl")));
        assertThat(clampEvents(base.trial())).isEmpty();
        assertThat(clampEvents(huge.trial())).isEmpty();
        JsonNode params = Canonical.MAPPER.readTree(Files.readString(base.trial().resolve("params.json")));
        assertThat(params.has("context_clamp")).isFalse();
        assertThat(Canonical.MAPPER.readTree(Files.readAllLines(base.out()).get(0)).get("llm").has("contextClamp")).isFalse();
    }

    @Test
    void aTightWindowLowersMaxTokensAndLogsEveryBindingThenReplays(@TempDir Path dir) throws Exception {
        var base = TruncatedThinkingTest.run(dir, "base", SCEN, true, OK, "thinking", "on");
        int maxEst = base.requests().stream().mapToInt(ContextClampCliTest::estimate).max().orElseThrow();
        int window = maxEst + 1500 + 100; // the longest prompt keeps 1,500 tokens (>= 1,024): lowered, never skipped
        var r = TruncatedThinkingTest.run(dir, "tight", SCEN, true, OK, "thinking", "on", "context-clamp", "on",
                "context-window", Integer.toString(window), "context-margin", "100", "trial-id", "trial-A", "arm", "arm-A");
        List<JsonNode> ev = clampEvents(r.trial());
        assertThat(ev).isNotEmpty();
        for (JsonNode e : ev) {
            assertThat(e.get("trial").asText()).isEqualTo("trial-A");
            assertThat(e.get("arm").asText()).isEqualTo("arm-A");
            assertThat(e.get("skipped").asBoolean()).isFalse();
            assertThat(e.get("window").asInt()).isEqualTo(window);
            assertThat(e.get("requested_max_tokens").asInt()).isEqualTo(TruncatedThinkingTest.LIMIT);
            assertThat(e.get("granted_max_tokens").asInt()).isBetween(1024, TruncatedThinkingTest.LIMIT - 1);
            assertThat(e.get("est_prompt_tokens").asInt() + e.get("granted_max_tokens").asInt()).isEqualTo(window - 100);
            assertThat(List.of("quote", "talk")).contains(e.get("call_type").asText());
            assertThat(e.has("round") && e.has("seat") && e.has("draw_key") && e.has("attempt")).isTrue();
        }
        // the invariant, on what the server saw
        assertThat(r.requests()).allSatisfy(q -> assertThat(estimate(q) + maxTokens(q)).isLessThanOrEqualTo(window - 100));
        // the logged grant is the max_tokens that was sent
        for (JsonNode e : ev) {
            MockRequest q = r.requests().stream().filter(x -> x.user().equals(e.get("draw_key").asText())).findFirst().orElseThrow();
            assertThat(maxTokens(q)).isEqualTo(e.get("granted_max_tokens").asInt());
        }
        // the call record carries the same
        List<JsonNode> calls = new java.util.ArrayList<>();
        for (String l : Files.readAllLines(Path.of(r.out() + ".calls.jsonl"))) {
            calls.add(Canonical.MAPPER.readTree(l));
        }
        assertThat(calls.stream().filter(c -> c.has("clamp")).count()).isEqualTo(ev.size());
        JsonNode c = calls.stream().filter(x -> x.has("clamp")).findFirst().orElseThrow().get("clamp");
        assertThat(c.get("requestedMaxTokens").asInt()).isEqualTo(TruncatedThinkingTest.LIMIT);
        assertThat(c.get("skipped").asBoolean()).isFalse();
        assertThat(Canonical.MAPPER.readTree(Files.readString(r.trial().resolve("params.json"))).get("context_clamp").get("window")
                .asInt()).isEqualTo(window);
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", r.out() + ".cache.jsonl", "run", r.out().toString()))).isZero();
        SeatsIntegrationI1Test.schemaCheck(r.out(), Path.of(r.out() + ".calls.jsonl"));
    }

    @Test
    void whenTooLittleIsLeftTheCallIsNotSentAndTheRoundIsImputedAsTruncated(@TempDir Path dir) throws Exception {
        var base = TruncatedThinkingTest.run(dir, "base", SCEN, true, OK, "thinking", "on");
        int maxEst = base.requests().stream().mapToInt(ContextClampCliTest::estimate).max().orElseThrow();
        int window = maxEst + 500 + 100; // the longest prompts keep 500 < 1,024 tokens
        var r = TruncatedThinkingTest.run(dir, "skip", SCEN, true, OK, "thinking", "on", "context-clamp", "on",
                "context-window", Integer.toString(window), "context-margin", "100", "trial-id", "t", "arm", "a");
        List<JsonNode> skipped = clampEvents(r.trial()).stream().filter(e -> e.get("skipped").asBoolean()).toList();
        assertThat(skipped).isNotEmpty();
        for (JsonNode e : skipped) {
            assertThat(e.get("granted_max_tokens").asInt()).isZero();
            assertThat(window - 100 - e.get("est_prompt_tokens").asInt()).isLessThan(1024);
            assertThat(r.requests()).noneMatch(q -> q.user().equals(e.get("draw_key").asText())); // never sent
        }
        JsonNode q = skipped.stream().filter(e -> e.get("call_type").asText().equals("quote")).findFirst().orElseThrow();
        if (q != null) { // a quote: imputed and truncated (C12b.3 path), no repair
            JsonNode ev = TruncatedThinkingTest.quoteEvent(r.trial(), q.get("seat").asText(), q.get("round").asInt());
            assertThat(ev.get("outcome").asText()).isEqualTo("TRUNCATED");
            assertThat(ev.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
            assertThat(ev.get("imputed").asBoolean()).isTrue();
            assertThat(ev.get("context_clamp_skipped").asBoolean()).isTrue();
            assertThat(ev.has("truncated_thinking")).isFalse();
            assertThat(r.requests()).noneMatch(x -> x.user().equals(
                    "game|n3-group|s2|" + q.get("seat").asText() + "|r" + q.get("round").asInt() + "|a1"));
        }
        for (JsonNode e : skipped) { // a skipped talk turn is done, imputed and TRUNCATED, never repaired
            if (e.get("call_type").asText().equals("talk")) {
                JsonNode t = TruncatedThinkingTest.talkEvent(r.trial(), e.get("seat").asText(), e.get("round").asInt(),
                        Integer.parseInt(e.get("draw_key").asText().replaceAll(".*\\|t(\\d+)\\|a\\d$", "$1")));
                assertThat(t.get("refusal_kind").asText()).isEqualTo("TRUNCATED");
                assertThat(t.get("context_clamp_skipped").asBoolean()).isTrue();
                assertThat(t.has("truncated_thinking")).isFalse();
                assertThat(t.get("parsed").get("done").asBoolean()).isTrue();
            }
        }
        assertThat(r.requests()).allSatisfy(x -> assertThat(estimate(x) + maxTokens(x)).isLessThanOrEqualTo(window - 100));
        List<String> calls = lines(Path.of(r.out() + ".calls.jsonl"));
        assertThat(calls).anyMatch(c -> c.contains("\"skipped\":true") && c.contains("\"parseStatus\":\"PARSE_FAIL\""));
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", r.out() + ".cache.jsonl", "run", r.out().toString()))).isZero();
        SeatsIntegrationI1Test.schemaCheck(r.out(), Path.of(r.out() + ".calls.jsonl"));
    }

    @Test
    void theWindowFlagsNeedTheSwitch() {
        assertThatThrownBy(() -> LlmCommands.contextClamp(TrialDirCliTest.o("context-window", "9000"), "a"))
                .hasMessageContaining("--context-clamp on");
        assertThat(LlmCommands.contextClamp(TrialDirCliTest.o(), "a")).isNull();
        var c = LlmCommands.contextClamp(TrialDirCliTest.o("context-clamp", "on"), "a");
        assertThat(c.window()).isEqualTo(16384);
        assertThat(c.margin()).isEqualTo(256);
        assertThat(c.minTokens()).isEqualTo(1024);
    }
}
