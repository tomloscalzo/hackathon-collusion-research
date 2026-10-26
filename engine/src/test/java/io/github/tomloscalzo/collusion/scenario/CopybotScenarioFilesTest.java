package io.github.tomloscalzo.collusion.scenario;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.Test;

/** The copy-bot scenario files are slice-m-p1 with the second seat replaced by a scripted COPIER named partner. */
class CopybotScenarioFilesTest {
    private static String text(String name) throws Exception {
        try (InputStream in = CopybotScenarioFilesTest.class.getClassLoader().getResourceAsStream("scenarios/" + name + ".yaml")) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8).replace("\r\n", "\n");
        }
    }

    private static String body(String t) {
        return t.substring(t.indexOf("\nid:"), t.indexOf("agents:\n"));
    }

    @Test
    void sameMarketAsTheHeadlineWithOneLlmAndACopier() throws Exception {
        GameConfig head = GameConfigLoader.loadResource("scenarios/slice-m-p1.yaml");
        String headBody = body(text("slice-m-p1")).replaceFirst("(?m)^id:.*$", "id: X");
        for (String o : List.of("150", "250", "350")) {
            String f = "copybot-p1-open" + o;
            assertThat(body(text(f)).replaceFirst("(?m)^id:.*$", "id: X")).as(f).isEqualTo(headBody);
            GameConfig c = GameConfigLoader.loadResource("scenarios/" + f + ".yaml");
            assertThat(c.scenario().market()).isEqualTo(head.scenario().market());
            assertThat(c.agents()).hasSize(2);
            assertThat(c.agents().get(0).id()).isEqualTo("llm1");
            assertThat(c.agents().get(0).kind()).isEqualTo(AgentKind.LLM);
            assertThat(c.agents().get(1).id()).isEqualTo("partner");
            assertThat(c.agents().get(1).kind()).isEqualTo(AgentKind.COPIER);
            assertThat(((Number) c.agents().get(1).config().get("open")).doubleValue()).isEqualTo(Double.parseDouble(o) / 100.0);
        }
    }
}
