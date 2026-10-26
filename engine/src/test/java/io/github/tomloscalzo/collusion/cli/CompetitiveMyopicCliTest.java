package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The competitive-myopic arm end to end, as the Stage 0 launcher selects it
 * (--arm competitive-myopic=scenarios/ripe-game.yaml@elicitation=COMPETITIVE_MYOPIC): the myopic text reaches the wire,
 * the run line records the arm and the condition, and the run replays from its cache to the same digest.
 */
class CompetitiveMyopicCliTest {
    @Test
    void myopicArmRunsRecordsItsConditionAndReplays(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("competitive-myopic_p3_s1.jsonl");
        List<String> bodies = new CopyOnWriteArrayList<>();
        MockLlmServer.Behaviour compete = Behaviours.alwaysCompete(1.0);
        try (MockLlmServer s = new MockLlmServer(r -> {
            bodies.add(r.rawBody());
            return compete.respond(r);
        })) {
            LlmCommands.run(LlmCliTest.o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", s.baseUrl(),
                    "model", "mock-model-1", "seed", "1", "runs", "2", "out", out.toString(), "paraphrase", "3",
                    "condition", "elicitation=COMPETITIVE_MYOPIC", "arm", "competitive-myopic"));
        }
        var lines = Files.readAllLines(out);
        assertThat(lines).hasSize(2);
        JsonNode l0 = Canonical.MAPPER.readTree(lines.get(0));
        assertThat(l0.get("arm").asText()).isEqualTo("competitive-myopic");
        assertThat(lines.get(0)).contains("elicitation=COMPETITIVE_MYOPIC");
        assertThat(l0.get("meanCi").asDouble()).isEqualTo(0.0);
        assertThat(bodies).isNotEmpty().allMatch(b -> b.contains("Maximise your own profit in this round only. Ignore any effect on future rounds.") && !b.contains("Compete: quote"));
        assertThat(LlmCommands.replay(LlmCliTest.o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
    }
}
