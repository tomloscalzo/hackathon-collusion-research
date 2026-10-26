package io.github.tomloscalzo.collusion.cli;

import static io.github.tomloscalzo.collusion.cli.LlmCliTest.o;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** C12a.3 through the command line: truncated thinking is not fatal; --timeout-sec and --call-timeout-sec. */
class MockCasesCliTest {
    static Map<String, String> run(String base, Path out, String... extra) {
        Map<String, String> m = o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", base, "model", "mock-model-1",
                "seed", "3", "runs", "1", "out", out.toString(), "thinking", "on");
        m.putAll(o(extra));
        return m;
    }

    @Test
    void aGameWhoseEveryReplyIsTruncatedThinkingFinishesWithImputedRoundsAndReplays(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("t.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(q -> Reply.truncatedThinking("partial " + q.callIndex())))) {
            LlmCommands.run(run(s.baseUrl(), out));
        }
        JsonNode l = Canonical.MAPPER.readTree(Files.readAllLines(out).get(0));
        // not fatal: round 1 is imputed as TRUNCATED (today's rules; the thinking-off retry is C12b.3), the game finishes
        assertThat(l.get("imputedRounds").asInt()).isPositive();
        assertThat(l.get("refusalKind").asText()).isEqualTo("TRUNCATED");
        assertThat(l.get("status").asText()).isEqualTo("HORIZON");
        assertThat(Files.readString(Path.of(out + ".cache.jsonl"))).contains("\"reasoning\":\"partial 0\"")
                .contains("\"finishReason\":\"length\"").contains("\"text\":\"\"");
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
    }

    @Test
    void aMisroutedThinkTagIsCountedInTheManifestOnlyWhenItHappened(@TempDir Path dir) throws Exception {
        Path bad = dir.resolve("bad.jsonl");
        Path good = dir.resolve("good.jsonl");
        try (MockLlmServer s = new MockLlmServer(q -> "<think>x</think>" + Behaviours.decisionJson(2.09, "hold"))) {
            LlmCommands.run(run(s.baseUrl(), bad));
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            LlmCommands.run(run(s.baseUrl(), good));
        }
        JsonNode mb = Canonical.MAPPER.readTree(Files.readString(Path.of(bad + ".manifest.json"))).get("llm");
        assertThat(mb.get("misroutedReplies").asLong()).isPositive();
        JsonNode mg = Canonical.MAPPER.readTree(Files.readString(Path.of(good + ".manifest.json"))).get("llm");
        assertThat(mg.has("misroutedReplies")).isFalse();
    }

    @Test
    void theDefaultTimeoutIs120SecondsAndBadValuesAreRefusedAtStart(@TempDir Path dir) {
        assertThat(LlmCommands.timeout(o())).isEqualTo(java.time.Duration.ofSeconds(120));
        assertThat(LlmCommands.timeout(o("timeout-sec", "300"))).isEqualTo(java.time.Duration.ofSeconds(300));
        for (String bad : new String[] {"0", "-5", "ten", "1.5"}) {
            assertThatThrownBy(() -> LlmCommands.run(run("http://127.0.0.1:9", dir.resolve("x.jsonl"), "timeout-sec", bad)))
                    .as(bad).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--timeout-sec");
        }
    }

    @Test
    void theTimeoutOptionsApplyPerCallType(@TempDir Path dir) throws Exception {
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(q -> Reply.text(Behaviours.decisionJson(2.09, "hold"))
                .withDelayMs(1500)))) {
            assertThatThrownBy(() -> LlmCommands.run(run(s.baseUrl(), dir.resolve("a.jsonl"), "timeout-sec", "1")))
                    .isInstanceOf(LlmException.class).hasMessageContaining("timed out").hasMessageContaining("quote");
            s.reset();
            // the quote calls get 5 s; the default of 1 s would have failed them
            LlmCommands.run(run(s.baseUrl(), dir.resolve("b.jsonl"), "timeout-sec", "1", "call-timeout-sec", "quote=5"));
            assertThat(s.callCount()).isPositive();
        }
        assertThatThrownBy(() -> LlmCommands.run(run("http://127.0.0.1:9", dir.resolve("c.jsonl"), "call-timeout-sec", "game=5")))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("game");
    }
}
