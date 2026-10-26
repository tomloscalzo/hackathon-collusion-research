package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.util.List;
import org.junit.jupiter.api.Test;

/** The copy-bot control: the one LLM firm reads the very same system prompt as the LLM seat of the two-LLM headline. */
class CopierPromptTest {
    private static GameConfig load(String name) {
        return GameConfigLoader.loadResource("scenarios/" + name + ".yaml");
    }

    private static List<String> ids(GameConfig cfg) {
        return cfg.agents().stream().map(AgentSpec::id).toList();
    }

    @Test
    void theLlmSeatBesideACopierReadsTheHeadlinePromptInEveryWording() {
        GameConfig head = load("slice-m-p1");
        for (String f : List.of("copybot-p1-open150", "copybot-p1-open250", "copybot-p1-open350")) {
            GameConfig cb = load(f);
            GameContext gh = GameContext.of(head, "llm1", SeatView.seeded("llm1", ids(head), 7));
            GameContext gc = GameContext.of(cb, "llm1", SeatView.seeded("llm1", ids(cb), 7));
            // the rival label the seat reads in its history must match the headline's for every seed (sorted-id shuffle)
            for (long seed = 1; seed <= 300; seed++) {
                assertThat(new java.util.ArrayList<>(SeatView.shared("llm1", ids(cb), seed).labels().values()))
                        .as(f + " seed " + seed).isEqualTo(new java.util.ArrayList<>(SeatView.shared("llm1", ids(head), seed).labels().values()));
            }
            assertThat(gc.partnerRuleText()).isEqualTo(gh.partnerRuleText());
            assertThat(gc.sP()).isEqualTo(gh.sP());
            for (int p = 0; p < 5; p++) {
                PromptBuilder pb = PromptBuilder.trackM(Condition.neutral(), p);
                assertThat(pb.gameSystem(gc)).as(f + " p" + p).isEqualTo(pb.gameSystem(gh));
            }
        }
    }
}
