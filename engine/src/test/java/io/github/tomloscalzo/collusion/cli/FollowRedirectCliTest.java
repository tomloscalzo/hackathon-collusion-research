package io.github.tomloscalzo.collusion.cli;

import static io.github.tomloscalzo.collusion.cli.LlmCliTest.o;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** C12a.4 through the command line: --follow-redirects on|off (absent = off, as before). */
class FollowRedirectCliTest {
    static Map<String, String> run(String base, Path out, String... extra) {
        Map<String, String> m = o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", base, "model", "mock-model-1",
                "seed", "3", "runs", "1", "out", out.toString());
        m.putAll(o(extra));
        return m;
    }

    @Test
    void aGameOnASlowRedirectingServerFinishesWithTheSwitchOnAndAbortsWithoutIt(@TempDir Path dir) throws Exception {
        try (MockLlmServer s = new MockLlmServer(Behaviours.replies(q -> Reply.text(Behaviours.decisionJson(2.09, "hold"))
                .withDelayMs(50).withRedirects(1)))) {
            assertThatThrownBy(() -> LlmCommands.run(run(s.baseUrl(), dir.resolve("a.jsonl"))))
                    .isInstanceOf(LlmException.class).hasMessageContaining("HTTP 303");
            Path out = dir.resolve("b.jsonl");
            LlmCommands.run(run(s.baseUrl(), out, "follow-redirects", "on"));
            assertThat(Files.readAllLines(out)).hasSize(1);
            assertThat(s.resultFetches()).hasSize(s.callCount() - 1);   // the aborted run made one call and no fetch
            assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
        }
        assertThatThrownBy(() -> LlmCommands.run(run("http://127.0.0.1:9", dir.resolve("c.jsonl"), "follow-redirects", "yes")))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--follow-redirects");
    }
}
