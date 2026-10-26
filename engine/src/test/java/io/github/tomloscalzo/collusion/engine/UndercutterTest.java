package io.github.tomloscalzo.collusion.engine;

import static io.github.tomloscalzo.collusion.core.model.AgentKind.ALWAYS_COMPETE;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.UNDERCUTTER;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.results.RunRecord;
import org.junit.jupiter.api.Test;

/** The scripted undercutter baseline (U18): one (or step) tick(s) below the lowest OTHER firm's previous quote, never below s^N. */
class UndercutterTest {
    private static final double TOL = 1e-9;

    private static double q(RunRecord r, int round, String id) {
        return r.rounds().get(round - 1).agent(id).displayed();
    }

    @Test
    void twoUndercuttersWalkDownOneTickAtATime() {
        Scenario s = Fx.known(6);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", UNDERCUTTER, "open", 2.0), Fx.spec("B", UNDERCUTTER, "open", 2.0))).run(1);
        for (int t = 1; t <= 6; t++) {
            assertThat(q(r, t, "A")).as("A@%d", t).isCloseTo(2.0 - 0.01 * (t - 1), within(TOL));
            assertThat(q(r, t, "B")).as("B@%d", t).isCloseTo(2.0 - 0.01 * (t - 1), within(TOL));
        }
    }

    @Test
    void stepOfFiveTicksAndTheFloor() {
        Scenario s = Fx.known(5);
        double floor = Fx.s(s, 0.0);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", UNDERCUTTER, "open", 1.12, "step", 5),
                Fx.spec("B", UNDERCUTTER, "open", 1.12, "step", 5))).run(1);
        assertThat(q(r, 1, "A")).isCloseTo(1.12, within(TOL));
        assertThat(q(r, 2, "A")).isCloseTo(1.07, within(TOL));
        assertThat(q(r, 3, "A")).isCloseTo(1.02, within(TOL));
        assertThat(q(r, 4, "A")).isCloseTo(floor, within(TOL));   // 0.97 would be below the floor
        assertThat(q(r, 5, "B")).isCloseTo(floor, within(TOL));
    }

    @Test
    void targetsTheLowestOtherFirmAndNeverItself() {
        GameConfig g = io.github.tomloscalzo.collusion.scenario.GameConfigLoader.loadResource("scenarios/n3-group.yaml");
        RunRecord r = new Game(g.withAgents(java.util.List.of(Fx.spec("A", UNDERCUTTER, "open", 2.0),
                Fx.spec("B", UNDERCUTTER, "open", 1.5), Fx.spec("C", UNDERCUTTER, "open", 1.8)))).run(1);
        assertThat(q(r, 2, "A")).isCloseTo(1.49, within(TOL));   // lowest other = B 1.5
        assertThat(q(r, 2, "B")).isCloseTo(1.79, within(TOL));   // lowest other = C 1.8, not its own 1.5
        assertThat(q(r, 2, "C")).isCloseTo(1.49, within(TOL));
    }

    @Test
    void sitsAtTheFloorAgainstACompetitor() {
        Scenario s = Fx.known(3);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", UNDERCUTTER, "open", 2.0), Fx.spec("B", ALWAYS_COMPETE))).run(1);
        assertThat(q(r, 1, "A")).isCloseTo(2.0, within(TOL));
        assertThat(q(r, 2, "A")).isCloseTo(Fx.s(s, 0.0), within(TOL));
        assertThat(q(r, 3, "A")).isCloseTo(Fx.s(s, 0.0), within(TOL));
    }

    @Test
    void holdsItsQuoteWhenRivalQuotesAreHidden() {
        Scenario s = Fx.known(4);
        GameConfig c = Fx.cfg(s, Fx.spec("A", UNDERCUTTER, "open", 2.0), Fx.spec("B", ALWAYS_COMPETE))
                .withObservation(new ObservationPolicy(true, false, 0.0, 0.0));
        RunRecord r = new Game(c).run(1);
        assertThat(q(r, 4, "A")).isCloseTo(2.0, within(TOL));
    }

    @Test
    void configIsValidated() {
        Scenario s = Fx.known(3);
        assertThatThrownBy(() -> AgentFactory.create(Fx.spec("A", UNDERCUTTER), s, ObservationPolicy.defaults()))
                .hasMessageContaining("open");
        assertThatThrownBy(() -> AgentFactory.create(Fx.spec("A", UNDERCUTTER, "open", 2.0, "step", 0), s, ObservationPolicy.defaults()))
                .hasMessageContaining("step");
        assertThatThrownBy(() -> AgentFactory.create(Fx.spec("A", UNDERCUTTER, "open", 2.0, "bogus", 1), s, ObservationPolicy.defaults()))
                .hasMessageContaining("bogus");
    }
}
