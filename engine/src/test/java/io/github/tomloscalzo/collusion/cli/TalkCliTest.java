package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** C5.5: run --seat LLM --multi-seat on --talk on through the real client, cache, call log, schema check and replay. */
class TalkCliTest {
    static Map<String, String> o(String... kv) {
        return TrialDirCliTest.o(kv);
    }

    /** Talk: one message, then done; quotes hold 2.09. */
    static MockLlmServer.Behaviour behaviour() {
        return r -> r.user().startsWith("talk|")
                ? (r.lastUser().contains("You have sent 0 of") ? "{\"message\": \"Hold 2.09?\", \"done\": false}"
                : "{\"message\": \"\", \"done\": true}")
                : Behaviours.decisionJson(2.09, "hold");
    }

    @Test
    void aChatArmRunsThroughTheCommandLineReplaysAndPassesTheSchemas(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("c.jsonl");
        try (MockLlmServer s = new MockLlmServer(behaviour())) {
            LlmCommands.run(o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model",
                    "mock-model-1", "seed", "2", "runs", "2", "out", out.toString(), "multi-seat", "on", "talk", "on",
                    "analysis-script", "../tools/analysis.py"));
            // talk calls go out with the talk schema under the name "talk"; quote calls keep "decision"
            for (MockLlmServer.MockRequest r : s.requests()) {
                JsonNode body = Canonical.MAPPER.readTree(r.rawBody());
                String name = body.path("response_format").path("json_schema").path("name").asText();
                assertThat(name).isEqualTo(r.user().startsWith("talk|") ? "talk" : "decision");
            }
            assertThat(s.requests()).anyMatch(r -> r.user().startsWith("talk|"));
        }
        List<String> lines = Files.readAllLines(out);
        assertThat(lines).hasSize(2);
        JsonNode line = Canonical.MAPPER.readTree(lines.get(0));
        assertThat(line.get("llm").get("talk").asBoolean()).isTrue();
        List<String> calls = Files.readAllLines(Path.of(out + ".calls.jsonl"));
        long talk = calls.stream().filter(c -> c.contains("\"kind\":\"talk\"")).count();
        int rounds = 0;
        for (String l : lines) {
            rounds += Canonical.MAPPER.readTree(l).get("rounds").size();
        }
        assertThat(talk).isEqualTo(6L * rounds); // three seats: one message and one done each per round
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
        SeatsIntegrationI1Test.schemaCheck(out, Path.of(out + ".calls.jsonl"));
    }

    @Test
    void talkIsOffByDefaultAndNeedsMultiSeat(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("t.jsonl");
        try (MockLlmServer s = new MockLlmServer(behaviour())) {
            LlmCommands.run(o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model",
                    "mock-model-1", "seed", "2", "out", out.toString(), "multi-seat", "on", "analysis-script",
                    "../tools/analysis.py"));
            assertThat(s.requests()).noneMatch(r -> r.user().startsWith("talk|"));
            assertThat(Canonical.MAPPER.readTree(Files.readAllLines(out).get(0)).get("llm").has("talk")).isFalse();
            assertThatThrownBy(() -> LlmCommands.run(o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "base-url",
                    s.baseUrl(), "model", "mock-model-1", "out", dir.resolve("x.jsonl").toString(), "talk", "on")))
                    .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--multi-seat on");
            assertThatThrownBy(() -> LlmCommands.run(o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "base-url",
                    s.baseUrl(), "model", "mock-model-1", "out", dir.resolve("y.jsonl").toString(), "multi-seat", "on",
                    "talk", "yes"))).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--talk");
        }
    }

    @Test
    void aChatTrialDirectoryRecordsTheTalkLimitsAndTheTalkDrawKey(@TempDir Path dir) throws Exception {
        Path trial = dir.resolve("trial");
        try (MockLlmServer s = new MockLlmServer(behaviour())) {
            LlmCommands.run(o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model",
                    "mock-model-1", "seed", "2", "out", dir.resolve("c.jsonl").toString(), "multi-seat", "on", "talk", "on",
                    "trial-dir", trial.toString(), "analysis-script", "../tools/analysis.py"));
        }
        JsonNode p = Canonical.MAPPER.readTree(Files.readString(trial.resolve("params.json")));
        assertThat(p.get("talk").get("max_messages").asInt()).isEqualTo(7);
        assertThat(p.get("talk").get("max_words").asInt()).isEqualTo(150);
        assertThat(p.has("communication")).isFalse(); // the grid's own column carries the condition (C14.1)
        assertThat(p.get("draw_keys").toString()).contains("talk|<scenario>|s<seed>|<seat>|r<round>|t<turn>|a<0|1>");
        assertThat(p.get("prompt_fingerprints").has("game_talk")).isTrue();
    }
}
