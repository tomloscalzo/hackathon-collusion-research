package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.agents.llm.Condition;
import io.github.tomloscalzo.collusion.agents.llm.LlmGame;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** U14 through LlmAgent: chat arm with fed questions; seat llm1's quote in round 2 is unreadable (imputed). */
class PlanLineAgentTest {
    private static final String OLD = "Your plan from the previous round: ";

    @Test
    void talkQuoteAndQuestionPromptsNameThePlanRoundAfterAnImputedRound(@TempDir Path dir) throws Exception {
        List<LlmRequest> reqs = new ArrayList<>();
        LlmClient client = r -> {
            reqs.add(r);
            Matcher m = InGameQuestionsTest.KEY.matcher(r.drawKey());
            assertThat(m.matches()).as(r.drawKey()).isTrue();
            String seat = m.group(2);
            int round = Integer.parseInt(m.group(3));
            String text = switch (m.group(1)) {
                case "talk" -> "{\"message\": \"\", \"done\": true}";
                case "question" -> "an answer";
                default -> seat.equals("llm1") && round == 2 ? "no json here"
                        : "{\"quote\": 2.09, \"plan\": \"planR" + round + "\", \"rationale\": \"why\"}";
            };
            return new LlmResponse(text, 10, 10, 0L, false, CanonicalRequest.sha256(r), "stop", null, null);
        };
        GameConfig cfg = InGameQuestionsTest.longGame(dir, 6);
        LlmGame.run(cfg, 3, InGameQuestionsTest.S, Condition.neutral(), 0, client, null, java.util.Set.of(), true, null, true,
                LlmGame.Extras.NONE.withQuestions(InGameQuestionsTest.questions()));
        String seat = "|llm1|";
        String q = "Your most recent plan (round 1): planR1";
        // round 3: quote and talk turns (planRound 1, round 3), question after round 3 (plan carried into it: planR1)
        assertThat(find(reqs, "game|", seat + "r3|a0")).contains(q).doesNotContain(OLD);
        assertThat(find(reqs, "talk|", seat + "r3|t0")).contains(q).doesNotContain(OLD);
        assertThat(find(reqs, "question|", seat + "r3|")).contains(q).doesNotContain(OLD);
        // round 2 still reads the previous round's plan; round 4 the round-3 plan
        assertThat(find(reqs, "game|", seat + "r2|a0")).contains(OLD + "planR1");
        assertThat(find(reqs, "question|", seat + "r2|")).contains(OLD + "planR1");
        assertThat(find(reqs, "game|", seat + "r4|a0")).contains(OLD + "planR3").doesNotContain("most recent plan");
        assertThat(find(reqs, "question|", seat + "r4|")).contains(OLD + "planR3").doesNotContain("most recent plan");
    }

    private static String find(List<LlmRequest> reqs, String kind, String part) {
        return reqs.stream().filter(r -> r.drawKey().startsWith(kind) && r.drawKey().contains(part)).findFirst()
                .orElseThrow(() -> new AssertionError(kind + part)).turns().get(0).content();
    }
}
