package io.github.tomloscalzo.collusion.llm;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** C12a.2 (interface proposal v5, C3 reading, D2): reasoning stored in the response and the cache file. */
class ReasoningStorageTest {
    static final String ANSWER = "{\"quote\": 2.40, \"plan\": \"hold\", \"rationale\": \"r\"}";
    static final String THOUGHT = "The other firm held 2.40 for two rounds ... \"quoted\" ü";

    static LlmRequest req(String draw) {
        return new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "hello")), 0.6, 100,
                null, draw, true, 0.95, 20);
    }

    static OpenAiCompatibleClient client(MockLlmServer s) {
        return new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(10), null, 1);
    }

    @Test
    void theClientReadsReasoningContentAndReasoningTokensAndKeepsTextTheAnswerOnly() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(
                q -> MockLlmServer.Reply.text(ANSWER).withReasoning(THOUGHT, 57)))) {
            LlmResponse r = client(s).complete(req("k1"));
            assertThat(r.text()).isEqualTo(ANSWER);
            assertThat(r.reasoning()).isEqualTo(THOUGHT);
            assertThat(r.reasoningTokens()).isEqualTo(57);
            assertThat(r.finishReason()).isEqualTo("stop");
        }
    }

    @Test
    void theReasoningFieldIsTheFallbackName() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(
                q -> MockLlmServer.Reply.text(ANSWER).withReasoning(THOUGHT, null).withReasoningField("reasoning")))) {
            LlmResponse r = client(s).complete(req("k1"));
            assertThat(s.requests()).hasSize(1);
            assertThat(r.text()).isEqualTo(ANSWER);
            assertThat(r.reasoning()).isEqualTo(THOUGHT);
            assertThat(r.reasoningTokens()).isNull();
        }
    }

    @Test
    void reasoningContentWinsOverReasoningAndRefusalAndFilterRepliesKeepTheirReasoning() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> {
            if (q.callIndex() == 0) {   // the fallback name alone
                return MockLlmServer.Reply.text(ANSWER).withReasoning("other", null).withReasoningField("reasoning");
            }
            return q.callIndex() == 1 ? MockLlmServer.Reply.providerRefusal("no").withReasoning("why not", 4)
                    : MockLlmServer.Reply.contentFilter(null).withReasoning("filtered thought", 5);
        }))) {
            OpenAiCompatibleClient c = client(s);
            assertThat(c.complete(req("k0")).reasoning()).isEqualTo("other");
            LlmResponse ref = c.complete(req("k1"));
            assertThat(ref.finishReason()).isEqualTo(OpenAiCompatibleClient.FINISH_REFUSAL);
            assertThat(ref.reasoning()).isEqualTo("why not");
            assertThat(ref.reasoningTokens()).isEqualTo(4);
            LlmResponse f = c.complete(req("k2"));
            assertThat(f.finishReason()).isEqualTo(OpenAiCompatibleClient.FINISH_CONTENT_FILTER);
            assertThat(f.reasoning()).isEqualTo("filtered thought");
        }
        com.fasterxml.jackson.databind.node.ObjectNode m = Canonical.MAPPER.createObjectNode();
        m.put("reasoning", "second");
        m.put("reasoning_content", "first");
        assertThat(OpenAiCompatibleClient.reasoningOf(m)).isEqualTo("first");
    }

    @Test
    void aReplyWithoutReasoningHasNone() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.fixed(2.09))) {
            LlmResponse r = client(s).complete(req("k1"));
            assertThat(r.reasoning()).isNull();
            assertThat(r.reasoningTokens()).isNull();
        }
    }

    @Test
    void theSevenArgumentResponseHasNoReasoningAndAsCachedKeepsIt() {
        LlmResponse old = new LlmResponse("t", 1, 2, 3L, false, "h", "stop");
        assertThat(old.reasoning()).isNull();
        assertThat(old.reasoningTokens()).isNull();
        LlmResponse r = new LlmResponse("t", 1, 2, 3L, false, "h", "stop", "why", 9).asCached();
        assertThat(r.cached()).isTrue();
        assertThat(r.latencyMs()).isZero();
        assertThat(r.reasoning()).isEqualTo("why");
        assertThat(r.reasoningTokens()).isEqualTo(9);
    }

    @Test
    void aCacheLineRoundTripsTheReasoningThroughCacheAndReplay(@TempDir Path dir) throws Exception {
        Path file = dir.resolve("cache.jsonl");
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(
                q -> MockLlmServer.Reply.text(ANSWER).withReasoning(THOUGHT, 57)))) {
            CachingLlmClient c = new CachingLlmClient(client(s), file);
            LlmResponse fresh = c.complete(req("d0"));
            assertThat(fresh.reasoning()).isEqualTo(THOUGHT);
            assertThat(fresh.reasoningTokens()).isEqualTo(57);
            LlmResponse hit = c.complete(req("d0"));
            assertThat(hit.cached()).isTrue();
            assertThat(hit.reasoning()).isEqualTo(THOUGHT);
            assertThat(s.callCount()).isEqualTo(1);
        }
        JsonNode line = Canonical.MAPPER.readTree(Files.readAllLines(file, StandardCharsets.UTF_8).get(0));
        assertThat(line.get("reasoning").asText()).isEqualTo(THOUGHT);
        assertThat(line.get("reasoningTokens").asInt()).isEqualTo(57);
        assertThat(line.get("text").asText()).isEqualTo(ANSWER);
        // a fresh cache instance and the replay client both restore it, with no server
        LlmResponse again = new CachingLlmClient(r -> {
            throw new AssertionError("no call expected");
        }, file).complete(req("d0"));
        assertThat(again.reasoning()).isEqualTo(THOUGHT);
        assertThat(again.reasoningTokens()).isEqualTo(57);
        LlmResponse replay = new ReplayLlmClient(file).complete(req("d0"));
        assertThat(replay.text()).isEqualTo(ANSWER);
        assertThat(replay.reasoning()).isEqualTo(THOUGHT);
        assertThat(replay.reasoningTokens()).isEqualTo(57);
    }

    @Test
    void withoutReasoningTheCacheLineIsTodaysSevenKeyLine() {
        LlmRequest q = new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "u")), 0.7,
                100, null, "game|x|s1|llm|r1|a0");
        LlmResponse r = new LlmResponse("{\"quote\": 2.09}", 10, 4, 5L, false, "ab", "stop");
        assertThat(CacheFile.line(q, r)).isEqualTo("{\"drawKey\":\"game|x|s1|llm|r1|a0\",\"finishReason\":\"stop\",\"hash\":\"ab\","
                + "\"modelSnapshot\":\"mock-model-1\",\"text\":\"{\\\"quote\\\": 2.09}\",\"tokensIn\":10,\"tokensOut\":4}");
        // reasoning tokens alone are written alone; an empty reasoning is kept as such (not null)
        assertThat(CacheFile.line(q, new LlmResponse("t", 1, 1, 0L, false, "ab", "stop", null, 3)))
                .contains("\"reasoningTokens\":3").doesNotContain("\"reasoning\":");
        assertThat(CacheFile.line(q, new LlmResponse("t", 1, 1, 0L, false, "ab", "stop", "", null)))
                .contains("\"reasoning\":\"\"").doesNotContain("reasoningTokens");
    }

    @Test
    void aGameRunStoresReasoningInTheCacheReplaysAndNeverPutsItIntoAPrompt(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("runs.jsonl");
        String canary = "CANARY-REASONING-7f3a";
        // call 0 is unreadable (a repair turn follows, which quotes the reply text back), every reply carries reasoning
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> MockLlmServer.Reply.text(
                q.callIndex() == 0 ? "not json" : MockLlmServer.Behaviours.decisionJson(2.09, "hold"))
                .withReasoning(canary + " call " + q.callIndex(), 11)))) {
            io.github.tomloscalzo.collusion.cli.LlmCommands.run(new java.util.TreeMap<>(java.util.Map.of("scenario",
                    "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model", "mock-model-1", "seed", "3",
                    "runs", "2", "out", out.toString(), "probe-rounds", "1", "thinking", "on")));
            assertThat(s.requests()).hasSizeGreaterThan(3);
            assertThat(s.requests().get(1).lastUser()).contains("could not be read");
            for (var r : s.requests()) {
                assertThat(r.rawBody()).as(r.user()).doesNotContain(canary);
            }
        }
        List<String> lines = Files.readAllLines(Path.of(out + ".cache.jsonl"), StandardCharsets.UTF_8);
        assertThat(lines).isNotEmpty().allSatisfy(l -> assertThat(l).contains("\"reasoning\":\"" + canary)
                .contains("\"reasoningTokens\":11"));
        assertThat(io.github.tomloscalzo.collusion.cli.LlmCommands.replay(new java.util.TreeMap<>(java.util.Map.of(
                "cache", out + ".cache.jsonl", "run", out.toString())))).isZero();
    }

    @Test
    void anOldCacheLineWithoutReasoningStillLoads(@TempDir Path dir) throws Exception {
        Path file = dir.resolve("old.jsonl");
        String hash = CanonicalRequest.sha256(req("d0"));
        Files.writeString(file, "{\"drawKey\":\"d0\",\"finishReason\":\"stop\",\"hash\":\"" + hash + "\",\"modelSnapshot\":\"mock-model-1\","
                + "\"text\":\"x\",\"tokensIn\":1,\"tokensOut\":2}\n", StandardCharsets.UTF_8);
        LlmResponse r = new ReplayLlmClient(file).complete(req("d0"));
        assertThat(r.text()).isEqualTo("x");
        assertThat(r.reasoning()).isNull();
        assertThat(r.reasoningTokens()).isNull();
    }
}
