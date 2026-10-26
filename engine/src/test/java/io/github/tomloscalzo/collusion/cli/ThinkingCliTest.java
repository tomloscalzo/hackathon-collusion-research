package io.github.tomloscalzo.collusion.cli;

import static io.github.tomloscalzo.collusion.cli.LlmCliTest.o;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** C12a.1: --thinking on|off, --top-p and --top-k on run --seat LLM (and vignette); absent = today's behaviour. */
class ThinkingCliTest {
    static Map<String, String> run(String base, Path out, String... extra) {
        Map<String, String> m = o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", base, "model", "mock-model-1",
                "seed", "3", "runs", "2", "out", out.toString(), "probe-rounds", "1");
        m.putAll(o(extra));
        return m;
    }

    @Test
    void thinkingOffIsSentOnEveryCallRecordedInTheRunLineAndReplays(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("off.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            LlmCommands.run(run(s.baseUrl(), out, "thinking", "off", "top-p", "0.8", "top-k", "20"));
            assertThat(s.requests()).hasSizeGreaterThan(2);
            boolean sawProbe = false;
            for (var r : s.requests()) {
                JsonNode b = Canonical.MAPPER.readTree(r.rawBody());
                assertThat(b.path("chat_template_kwargs").path("enable_thinking").isBoolean()).as(r.user()).isTrue();
                assertThat(b.path("chat_template_kwargs").path("enable_thinking").asBoolean()).isFalse();
                assertThat(b.path("top_p").asDouble()).isEqualTo(0.8);
                assertThat(b.path("top_k").asInt()).isEqualTo(20);
                sawProbe |= r.user().startsWith("probe|");
            }
            assertThat(sawProbe).isTrue();
        }
        var lines = Files.readAllLines(out);
        JsonNode llm = Canonical.MAPPER.readTree(lines.get(0)).get("llm");
        assertThat(llm.get("thinking").isBoolean()).isTrue();
        assertThat(llm.get("thinking").asBoolean()).isFalse();
        assertThat(llm.get("topP").asDouble()).isEqualTo(0.8);
        assertThat(llm.get("topK").asInt()).isEqualTo(20);
        JsonNode m = Canonical.MAPPER.readTree(Files.readString(Path.of(out + ".manifest.json"))).get("llm");
        assertThat(m.get("thinking").asBoolean(true)).isFalse();
        assertThat(m.get("topP").asDouble()).isEqualTo(0.8);
        assertThat(m.get("topK").asInt()).isEqualTo(20);
        // replay rebuilds the thinking-off game requests from the run line (probes are not replayed, F7): all hit
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
        // without the flag in the run line the requests differ (thinking is in the hash): every line misses
        Path stripped = dir.resolve("stripped.jsonl");
        StringBuilder sb = new StringBuilder();
        for (String l : lines) {
            ObjectNode n = (ObjectNode) Canonical.MAPPER.readTree(l);
            ((ObjectNode) n.get("llm")).remove("thinking");
            sb.append(Canonical.text(n)).append('\n');
        }
        Files.writeString(stripped, sb.toString());
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", stripped.toString()))).isEqualTo(2);
    }

    @Test
    void withoutTheOptionsNothingNewIsSentOrRecorded(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("plain.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            LlmCommands.run(run(s.baseUrl(), out));
            for (var r : s.requests()) {
                assertThat(r.rawBody()).doesNotContain("chat_template_kwargs").doesNotContain("top_p").doesNotContain("top_k");
            }
        }
        JsonNode llm = Canonical.MAPPER.readTree(Files.readAllLines(out).get(0)).get("llm");
        assertThat(llm.has("thinking")).isFalse();
        assertThat(llm.has("topP")).isFalse();
        assertThat(llm.has("topK")).isFalse();
        JsonNode m = Canonical.MAPPER.readTree(Files.readString(Path.of(out + ".manifest.json"))).get("llm");
        assertThat(m.has("thinking")).isFalse();
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
    }

    @Test
    void thinkingOnAndOffNeverShareACacheEntry(@TempDir Path dir) throws Exception {
        Path cache = dir.resolve("shared.cache.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            LlmCommands.run(run(s.baseUrl(), dir.resolve("a.jsonl"), "thinking", "on", "cache", cache.toString()));
            int afterOn = s.callCount();
            LlmCommands.run(run(s.baseUrl(), dir.resolve("b.jsonl"), "thinking", "off", "cache", cache.toString()));
            assertThat(s.callCount()).isEqualTo(2 * afterOn);
            JsonNode b = Canonical.MAPPER.readTree(s.requests().get(0).rawBody());
            assertThat(b.path("chat_template_kwargs").path("enable_thinking").asBoolean()).isTrue();
        }
    }

    @Test
    void aVignetteSendsRecordsAndReplaysTheFlag(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("v.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.vignetteSwitch(0.5))) {
            LlmCommands.vignette(o("scenario", "scenarios/ripe-game.yaml", "base-url", s.baseUrl(), "model", "mock-model-1",
                    "rows", "11", "draws", "1", "seed", "5", "out", out.toString(), "thinking", "off", "top-k", "20"));
            assertThat(s.requests()).hasSize(11);
            for (var r : s.requests()) {
                JsonNode b = Canonical.MAPPER.readTree(r.rawBody());
                assertThat(b.path("chat_template_kwargs").path("enable_thinking").isBoolean()).as(r.user()).isTrue();
                assertThat(b.path("chat_template_kwargs").path("enable_thinking").asBoolean()).isFalse();
                assertThat(b.path("top_k").asInt()).isEqualTo(20);
            }
        }
        JsonNode llm = Canonical.MAPPER.readTree(Files.readAllLines(out).get(0)).get("llm");
        assertThat(llm.get("thinking").asBoolean(true)).isFalse();
        assertThat(llm.get("topK").asInt()).isEqualTo(20);
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
    }

    @Test
    void outOfRangeTopPOrTopKIsRefusedAtParsing(@TempDir Path dir) {
        assertThatThrownBy(() -> LlmCommands.run(run("http://127.0.0.1:9", dir.resolve("x.jsonl"), "top-p", "0")))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--top-p");
        assertThatThrownBy(() -> LlmCommands.run(run("http://127.0.0.1:9", dir.resolve("x.jsonl"), "top-k", "0")))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--top-k");
        assertThat(Files.exists(dir.resolve("x.jsonl.cache.jsonl"))).isFalse();
    }

    @Test
    void aBadThinkingValueIsRefusedBeforeAnyCall(@TempDir Path dir) {
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            for (String bad : new String[] {"true", "ON", "", "yes"}) {
                assertThatThrownBy(() -> LlmCommands.run(run(s.baseUrl(), dir.resolve("x.jsonl"), "thinking", bad)))
                        .as(bad).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--thinking");
            }
            assertThat(s.callCount()).isZero();
        }
    }
}
