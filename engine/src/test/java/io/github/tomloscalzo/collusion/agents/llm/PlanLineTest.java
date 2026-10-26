package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviour;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.CallRecord;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.Test;

/**
 * U14: after an imputed round (no plan saved) the Track M plan line names the round of the plan it shows ("Your most
 * recent plan (round k): ..."); when the plan is the previous round's, or in Track S, the line is unchanged.
 */
class PlanLineTest {
    private static final String OLD = "Your plan from the previous round: ";

    /** Round r's reply holds the plan "planR&lt;r&gt;"; rounds in bad get a cut-off reply (both attempts); prompts kept by round. */
    private static Behaviour scripted(List<Integer> bad, Map<Integer, String> promptByRound) {
        return Behaviours.replies(r -> {
            int k = RefusalHandlingTest.round(r);
            if (RefusalHandlingTest.attempt(r) == 0) {
                promptByRound.put(k, r.lastUser());
            }
            return bad.contains(k) ? Reply.truncated("{\"quote\": 2.")
                    : Reply.text(MockLlmServer.Behaviours.decisionJson(RefusalHandlingTest.SP, "planR" + k));
        });
    }

    private static Map<Integer, String> play(List<Integer> bad, boolean trackM) {
        Map<Integer, String> prompts = new TreeMap<>();
        try (MockLlmServer s = new MockLlmServer(scripted(bad, prompts))) {
            GameConfig cfg = RefusalHandlingTest.cfg();
            for (long seed = 1; seed < 400; seed++) {
                s.reset();
                prompts.clear();
                LlmGame.Result r = LlmGame.run(cfg, seed, RefusalHandlingTest.SETTINGS, Condition.neutral(), 0,
                        LlmSeatTest.http(s), (CallRecord c) -> { }, java.util.Set.of(), trackM);
                if (r.run().rounds().size() >= 6) {
                    return new TreeMap<>(prompts);
                }
            }
        }
        throw new AssertionError("no long enough run");
    }

    @Test
    void afterAnImputedRoundTheLineNamesTheRoundOfThePlanShown() {
        Map<Integer, String> p = play(List.of(2, 3), true);
        assertThat(p.get(2)).contains(OLD + "planR1");
        assertThat(p.get(3)).contains("Your most recent plan (round 1): planR1").doesNotContain(OLD);
        assertThat(p.get(4)).contains("Your most recent plan (round 1): planR1").doesNotContain(OLD);
        assertThat(p.get(5)).contains(OLD + "planR4").doesNotContain("most recent plan");
    }

    @Test
    void afterARecoveredRoundTheLineIsTheOldWordingAgain() {
        Map<Integer, String> p = play(List.of(2), true);
        assertThat(p.get(3)).contains("Your most recent plan (round 1): planR1");
        assertThat(p.get(4)).contains(OLD + "planR3").doesNotContain("most recent plan");
        assertThat(p.get(5)).contains(OLD + "planR4").doesNotContain("most recent plan");
    }

    @Test
    void withoutAnImputedRoundNoPromptChanges() {
        Map<Integer, String> p = play(List.of(), true);
        assertThat(p.get(1)).contains("You have no plan from an earlier round.");
        for (int k = 2; k <= 6; k++) {
            assertThat(p.get(k)).contains(OLD + "planR" + (k - 1)).doesNotContain("most recent plan");
        }
    }

    @Test
    void trackSNeverUsesTheNewWording() {
        // Track S stops prompting after a refusal; a builder asked for the new line still gives the old one
        GameConfig cfg = RefusalHandlingTest.cfg();
        var g = GameContext.of(cfg, GameContext.firstLlmSeat(cfg));
        var obs = new io.github.tomloscalzo.collusion.engine.Observation(5, "llm", List.of("llm", "partner"), List.of(), 0.0);
        PromptBuilder s = new PromptBuilder(Condition.neutral(), 0);
        String t = s.gameTurn(g, obs, "keep", null, 1);
        assertThat(t).contains(OLD + "keep").doesNotContain("most recent plan");
        assertThat(t).isEqualTo(s.gameTurn(g, obs, "keep"));
    }

    @Test
    void quoteTalkAndQuestionTurnsAgreeOnTheLine() {
        GameConfig cfg = RefusalHandlingTest.cfg();
        var g = GameContext.of(cfg, GameContext.firstLlmSeat(cfg));
        var obs = new io.github.tomloscalzo.collusion.engine.Observation(5, "llm", List.of("llm", "partner"), List.of(), 0.0);
        PromptBuilder m = PromptBuilder.trackM(Condition.neutral(), 0, true);
        assertThat(m.gameTurn(g, obs, "keep", "C", 2)).contains("Your most recent plan (round 2): keep");
        assertThat(m.talkTurn(g, obs, "keep", "C", 0, 2)).contains("Your most recent plan (round 2): keep");
        assertThat(m.questionTurn(g, obs, "keep", 2.0, "r", "C", "Q?", 2)).contains("Your most recent plan (round 2): keep");
        // previous round, unknown (0) and no plan: unchanged
        assertThat(m.gameTurn(g, obs, "keep", "C", 4)).contains(OLD + "keep");
        assertThat(m.gameTurn(g, obs, "keep", "C")).contains(OLD + "keep");
        assertThat(m.gameTurn(g, obs, "", "C", 2)).contains("You have no plan from an earlier round.");
    }
}
