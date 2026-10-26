package io.github.tomloscalzo.collusion.engine;

import static io.github.tomloscalzo.collusion.core.model.AgentKind.ALWAYS_COMPETE;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.COPIER;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.UNDERCUTTER;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.results.RunRecord;
import org.junit.jupiter.api.Test;

/** The scripted copy-bot control: round 1 its opening quote, afterwards the other firm's previous quote. */
class CopierTest {
    private static final double TOL = 1e-9;

    private static double q(RunRecord r, int round, String id) {
        return r.rounds().get(round - 1).agent(id).displayed();
    }

    @Test
    void twoCopiersAtTheSameOpenStayFrozenForever() {
        Scenario s = Fx.known(8);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", COPIER, "open", 2.5), Fx.spec("B", COPIER, "open", 2.5))).run(1);
        for (int t = 1; t <= 8; t++) {
            assertThat(q(r, t, "A")).as("A@%d", t).isCloseTo(2.5, within(TOL));
            assertThat(q(r, t, "B")).as("B@%d", t).isCloseTo(2.5, within(TOL));
        }
    }

    @Test
    void twoCopiersAtDifferentOpensSwapQuotesEveryRound() {
        Scenario s = Fx.known(6);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", COPIER, "open", 1.5), Fx.spec("B", COPIER, "open", 3.0))).run(1);
        for (int t = 1; t <= 6; t++) {
            boolean odd = t % 2 == 1;
            assertThat(q(r, t, "A")).as("A@%d", t).isCloseTo(odd ? 1.5 : 3.0, within(TOL));
            assertThat(q(r, t, "B")).as("B@%d", t).isCloseTo(odd ? 3.0 : 1.5, within(TOL));
        }
    }

    @Test
    void followsAnUndercutterOneRoundBehind() {
        Scenario s = Fx.known(4);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("C", COPIER, "open", 2.0), Fx.spec("U", UNDERCUTTER, "open", 2.0))).run(1);
        assertThat(q(r, 1, "C")).isCloseTo(2.0, within(TOL));
        assertThat(q(r, 2, "U")).isCloseTo(1.99, within(TOL));
        assertThat(q(r, 2, "C")).isCloseTo(2.0, within(TOL));    // copies U's round-1 quote
        assertThat(q(r, 3, "C")).isCloseTo(1.99, within(TOL));   // copies U's round-2 quote
        assertThat(q(r, 3, "U")).isCloseTo(1.99, within(TOL));   // U undercuts C's round-2 quote 2.0
        assertThat(q(r, 4, "C")).isCloseTo(1.99, within(TOL));   // copies U's round-3 quote
        assertThat(q(r, 4, "U")).isCloseTo(1.98, within(TOL));
    }

    @Test
    void copiesACompetitorDownToTheFloor() {
        Scenario s = Fx.known(3);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("C", COPIER, "open", 2.0), Fx.spec("B", ALWAYS_COMPETE))).run(1);
        assertThat(q(r, 1, "C")).isCloseTo(2.0, within(TOL));
        assertThat(q(r, 2, "C")).isCloseTo(Fx.s(s, 0.0), within(TOL));
        assertThat(q(r, 3, "C")).isCloseTo(Fx.s(s, 0.0), within(TOL));
    }

    @Test
    void holdsItsQuoteWhenRivalQuotesAreHidden() {
        Scenario s = Fx.known(4);
        GameConfig c = Fx.cfg(s, Fx.spec("A", COPIER, "open", 2.0), Fx.spec("B", ALWAYS_COMPETE))
                .withObservation(new ObservationPolicy(true, false, 0.0, 0.0));
        RunRecord r = new Game(c).run(1);
        assertThat(q(r, 4, "A")).isCloseTo(2.0, within(TOL));
    }

    @Test
    void openIsSnappedAndClamped() {
        Scenario s = Fx.known(2);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", COPIER, "open", 0.2), Fx.spec("B", COPIER, "open", 99))).run(1);
        assertThat(q(r, 1, "A")).isCloseTo(Fx.s(s, 0.0), within(TOL));
        assertThat(q(r, 1, "B")).isCloseTo(5.0, within(TOL));
        RunRecord r2 = new Game(Fx.cfg(s, Fx.spec("A", COPIER, "open", 2.504), Fx.spec("B", COPIER, "open", 2.004))).run(1);
        assertThat(q(r2, 1, "A")).isCloseTo(2.50, within(TOL));
        assertThat(q(r2, 1, "B")).isCloseTo(2.00, within(TOL));
    }

    @Test
    void copiesTheLowestOfSeveralOtherFirms() {
        GameConfig g = io.github.tomloscalzo.collusion.scenario.GameConfigLoader.loadResource("scenarios/n3-group.yaml");
        RunRecord r = new Game(g.withAgents(java.util.List.of(Fx.spec("A", COPIER, "open", 2.0),
                Fx.spec("B", COPIER, "open", 1.5), Fx.spec("C", COPIER, "open", 1.8)))).run(1);
        assertThat(q(r, 2, "A")).isCloseTo(1.5, within(TOL));   // lowest other = B
        assertThat(q(r, 2, "B")).isCloseTo(1.8, within(TOL));   // lowest other = C, not itself
        assertThat(q(r, 2, "C")).isCloseTo(1.5, within(TOL));
    }

    @Test
    void carriesNoDisclosedRuleAndNoReferenceMargin() {
        Scenario s = Fx.known(2);
        var a = AgentFactory.create(Fx.spec("A", COPIER, "open", 2.0), s, ObservationPolicy.defaults());
        assertThat(a.disclosedRule()).isEmpty();
        assertThat(a.referenceMargin()).isEmpty();
    }

    @Test
    void configIsValidated() {
        Scenario s = Fx.known(2);
        assertThatThrownBy(() -> AgentFactory.create(Fx.spec("A", COPIER), s, ObservationPolicy.defaults()))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("open");
        assertThatThrownBy(() -> AgentFactory.create(Fx.spec("A", COPIER, "open", 2.0, "step", 1), s, ObservationPolicy.defaults()))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("unknown config key");
    }
}
