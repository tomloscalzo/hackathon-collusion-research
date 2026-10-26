package io.github.tomloscalzo.collusion.scenario;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.core.layera.CartelSolver;
import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.agents.AgentFactory;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Structure of the multi-firm scenario files (C2.2; played only from C3.5 on, so no game is run here). */
class MultiFirmScenarioFilesTest {
    private static GameConfig load(String name) {
        return GameConfigLoader.loadResource("scenarios/" + name + ".yaml");
    }

    private static void sameMarketAsRipeExceptN(GameConfig c) {
        var ripe = load("ripe-game").scenario();
        var s = c.scenario();
        assertThat(s.market().phi()).isEqualTo(ripe.market().phi());
        assertThat(s.market().s0()).isEqualTo(ripe.market().s0());
        assertThat(s.market().sBar()).isEqualTo(ripe.market().sBar());
        assertThat(s.market().q0()).isEqualTo(ripe.market().q0());
        assertThat(s.enforcement().fine()).isEqualTo(500.0);
        assertThat(s.enforcement().screen().slope()).isEqualTo(0.025);
        assertThat(s.time().maxRounds()).isEqualTo(40);
        assertThat(s.time().delta0()).isEqualTo(ripe.time().delta0());
        assertThat(s.punishment()).isEqualTo(ripe.punishment());
    }

    private static long llmSeats(GameConfig c) {
        return c.agents().stream().filter(a -> a.kind() == AgentKind.LLM).count();
    }

    @Test
    void threeFirmGroupHasThreeLlmSeats() {
        GameConfig c = load("n3-group");
        assertThat(c.scenario().market().n()).isEqualTo(3);
        assertThat(c.agents()).extracting(AgentSpec::id).containsExactly("llm1", "llm2", "llm3");
        assertThat(llmSeats(c)).isEqualTo(3);
        assertThat(c.agents()).allMatch(a -> a.category() == AgentCategory.M);
        sameMarketAsRipeExceptN(c);
    }

    @Test
    void fourFirmGroupHasFourLlmSeats() {
        GameConfig c = load("n4-group");
        assertThat(c.scenario().market().n()).isEqualTo(4);
        assertThat(c.agents()).extracting(AgentSpec::id).containsExactly("llm1", "llm2", "llm3", "llm4");
        assertThat(llmSeats(c)).isEqualTo(4);
        sameMarketAsRipeExceptN(c);
    }

    @Test
    void cheaterMarketHasTwoLlmSeatsAndAPlantedDefectOnceFirm() {
        GameConfig c = load("n3-cheater");
        assertThat(c.scenario().market().n()).isEqualTo(3);
        assertThat(llmSeats(c)).isEqualTo(2);
        AgentSpec ch = c.agents().get(2);
        assertThat(ch.id()).isEqualTo("cheater");
        assertThat(ch.kind()).isEqualTo(AgentKind.DEFECT_ONCE);
        assertThat(ch.config()).containsKey("theta").containsEntry("tMin", 6L).containsEntry("tMax", 10L)
                .doesNotContainKey("t").doesNotContainKey("placebo");
        sameMarketAsRipeExceptN(c);
        // the cheat round is drawn from the seed, always within 6..10, and room remains for t + 3
        for (long seed = 1; seed <= 50; seed++) {
            int t = AgentFactory.defectRound(ch, seed);
            assertThat(t).isBetween(6, 10);
        }
        assertThat(c.scenario().time().maxRounds()).isGreaterThanOrEqualTo(10 + 3);
    }

    @Test
    void cheaterPlaysTheThreeFirmTheoryLevelBeforeItCheats() throws Exception {
        GameConfig c = load("n3-cheater");
        double solved = new CartelSolver().solve(c.scenario()).thetaStar();
        double cfgTheta = ((Number) c.agents().get(2).config().get("theta")).doubleValue();
        assertThat(cfgTheta).isCloseTo(solved, org.assertj.core.data.Offset.offset(0.0005));
        assertThat(cfgTheta).isNotEqualTo(0.546); // not the two-firm level
        // the file's '# theory-theta-star:' comment (read by make_grid) equals the solver's value too
        String text = new String(getClass().getResourceAsStream("/scenarios/n3-cheater.yaml").readAllBytes(),
                java.nio.charset.StandardCharsets.UTF_8);
        var m = java.util.regex.Pattern.compile("(?m)^#\\s*theory-theta-star:\\s*([0-9.]+)\\s*$").matcher(text);
        assertThat(m.find()).isTrue();
        assertThat(Double.parseDouble(m.group(1))).isCloseTo(solved, org.assertj.core.data.Offset.offset(0.0005));
    }

    @Test
    void cheatRoundVariesAcrossSeeds() {
        AgentSpec ch = load("n3-cheater").agents().get(2);
        var rounds = new java.util.HashSet<Integer>();
        for (long seed = 1; seed <= 200; seed++) {
            rounds.add(AgentFactory.defectRound(ch, seed));
        }
        assertThat(rounds).containsExactlyInAnyOrder(6, 7, 8, 9, 10);
        for (long seed = 1; seed <= 5; seed++) {
            assertThat(AgentFactory.defectRound(ch, seed)).isEqualTo((int) (5 + seed));
        }
    }

    @Test
    void theoryParametersAreSolvableAtEachN() {
        for (String name : List.of("n3-group", "n3-cheater", "n4-group")) {
            var sol = new CartelSolver().solve(load(name).scenario());
            assertThat(sol.thetaStar()).isBetween(0.0, 1.0);
        }
    }
}
