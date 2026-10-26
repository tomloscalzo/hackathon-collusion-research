package io.github.tomloscalzo.collusion.engine;

import static io.github.tomloscalzo.collusion.core.model.AgentKind.ALWAYS_COMPETE;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.DEFECT_ONCE;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.PENANCE;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.TRIGGER_K;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.results.RunRecord;
import org.junit.jupiter.api.Test;

/**
 * TEST_PLAN 2 snapshots with closed forms. Scenario overrides common to every test here: ripe baseline, known horizon
 * of 12 rounds (delta0 0.95), detection OFF, demandNoiseSd 0, o = 1, quoteIncrement 0.01, punishmentLevel S0,
 * tolerance 0 (k and theta per test).
 */
class TriggerSnapshotTest {
    private static final double TOL = 1e-9;

    // two-trigger-0.6: 2 x TriggerK(0.6, inf); overrides: as above.
    @Test
    void twoTrigger() {
        Scenario s = Fx.known(12);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 0.6), Fx.spec("B", TRIGGER_K, "theta", 0.6))).run(1);
        assertThat(r.rounds()).hasSize(12);
        assertThat(r.status()).isEqualTo(RunStatus.HORIZON);
        double pc = Fx.piC(s, 0.6);
        assertThat(pc).isCloseTo(33.6, within(TOL));
        r.rounds().forEach(x -> {
            assertThat(x.insideCi()).isCloseTo(0.6, within(TOL));
            for (var a : x.agents()) {
                assertThat(a.ownCi()).isCloseTo(0.6, within(TOL));
                assertThat(a.payoff()).isCloseTo(pc, within(TOL));
                assertThat(a.phase()).isEqualTo("ADHERE");
            }
        });
    }

    // payoff-identity: all-adhere, no outsiders, I^RP = 0, demandNoiseSd = 0; the engine also asserts it internally.
    @Test
    void payoffIdentityAcrossTheta() {
        Scenario s = Fx.known(3);
        for (double th : new double[] {0.1, 0.3, 0.5459, 0.8, 1.0}) {
            RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", th), Fx.spec("B", TRIGGER_K, "theta", th))).run(2);
            double snapped = r.rounds().get(0).insideQuote();
            double expected = (snapped - 1.0) * 100 * (1 - snapped / 5.0) / 2.0;
            for (var a : r.rounds().get(0).agents()) {
                assertThat(a.payoff()).isCloseTo(expected, within(1e-9));
                assertThat(a.payoff()).isCloseTo(Fx.piC(s, th), within(0.5 * 0.01 * 100)); // grid snap only
            }
        }
        // exact on-grid theta
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 1.0), Fx.spec("B", TRIGGER_K, "theta", 1.0))).run(3);
        assertThat(r.rounds().get(0).agent("A").payoff()).isCloseTo(40.0, within(TOL)); // pi_c(1) = 40 (spec 8.4)
    }

    // trigger-vs-defect-once: TriggerK(0.6, k=3) + DefectOnce(0.6, t=5); overrides: as above; iota = 0 so s^N = s0 = 1.
    @Test
    void triggerVsDefectOnce() {
        Scenario s = Fx.known(12);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("T", TRIGGER_K, "theta", 0.6, "k", 3),
                Fx.spec("D", DEFECT_ONCE, "theta", 0.6, "t", 5))).run(1);
        double pc = Fx.piC(s, 0.6);
        for (int t = 1; t <= 12; t++) {
            var rr = r.rounds().get(t - 1);
            boolean war = t >= 6 && t <= 8;
            boolean defect = t == 5;
            // inside CI: 0.6 outside rounds 5-8, 0 (iota = 0, T23: -j*iota/span = 0) in rounds 5-8
            assertThat(rr.insideCi()).isCloseTo(t >= 5 && t <= 8 ? 0.0 : 0.6, within(TOL));
            assertThat(rr.agent("T").ownCi()).isCloseTo(war ? 0.0 : 0.6, within(TOL));
            assertThat(rr.agent("D").ownCi()).isCloseTo(defect ? 0.0 : 0.6, within(TOL));
            double expectedPay = t >= 5 && t <= 8 ? 0.0 : pc;
            assertThat(rr.agent("T").payoff()).isCloseTo(expectedPay, within(TOL));
            assertThat(rr.agent("D").payoff()).isCloseTo(expectedPay, within(TOL));
            assertThat(rr.agent("T").phase()).isEqualTo(war ? "WAR" : "ADHERE");
        }
        assertThat(r.rounds().get(5).agent("T").signalSeen()).isTrue(); // seen at round 6 (observing round 5)
        assertThat(r.rounds().stream().filter(x -> x.agent("T").signalSeen()).count()).isEqualTo(1);
    }

    // T23 variant: same with a tick iota = 0.25 (j* = 2, s^N = 1.5, span 1.5) and war at s0: war-round CI = -1/3.
    @Test
    void triggerVsDefectOnceWithTick() {
        Scenario s = Fx.known(12);
        s = s.withMarket(new MarketParams(2, 0.3, 1.0, 5.0, 100, 0.25, 0.01));
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("T", TRIGGER_K, "theta", 0.6, "k", 3),
                Fx.spec("D", DEFECT_ONCE, "theta", 0.6, "t", 5))).run(1);
        double wantCi = -0.5 / 1.5; // -j* iota / (sM - s^N)
        for (int t = 6; t <= 8; t++) {
            assertThat(r.rounds().get(t - 1).insideCi()).isCloseTo(wantCi, within(TOL));
            assertThat(r.rounds().get(t - 1).agent("T").ownCi()).isCloseTo(wantCi, within(TOL));
        }
        assertThat(r.rounds().get(4).agent("D").ownCi()).isCloseTo(0.0, within(TOL)); // defects to s^N
        assertThat(r.rounds().get(4).agent("D").payoff()).isCloseTo(29.75, within(TOL));
        assertThat(r.rounds().get(4).agent("T").payoff()).isCloseTo(5.25, within(TOL));
        assertThat(r.rounds().get(8).insideCi()).isCloseTo(0.6, within(TOL));
    }

    // penance-vs-defect-once: Penance(0.6, k=3) + DefectOnce(0.6, t=5); overrides: as above.
    @Test
    void penanceVsDefectOnce() {
        Scenario s = Fx.known(12);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("P", PENANCE, "theta", 0.6, "k", 3),
                Fx.spec("D", DEFECT_ONCE, "theta", 0.6, "t", 5))).run(1);
        double x = 1.2 * 56.0; // (s - s0) Q(s) at s(0.6) = 2.2
        for (int t = 1; t <= 12; t++) {
            var rr = r.rounds().get(t - 1);
            assertThat(rr.agent("P").ownCi()).isCloseTo(0.6, within(TOL)); // rival stays at s(0.6)
            boolean pen = t >= 6 && t <= 8;
            assertThat(rr.agent("D").excluded()).isEqualTo(pen);
            if (pen) {
                assertThat(rr.insideCi()).isCloseTo(0.6, within(TOL));
                assertThat(rr.agent("D").payoff()).isCloseTo(0.3 * x / 2, within(TOL)); // preferenced share only
                assertThat(rr.agent("P").payoff()).isCloseTo(x * (0.7 + 0.15), within(TOL));
            } else if (t == 5) {
                assertThat(rr.agent("D").payoff()).isCloseTo(0.0, within(TOL));
            } else {
                assertThat(rr.agent("D").payoff()).isCloseTo(Fx.piC(s, 0.6), within(TOL));
            }
        }
        // deviator's loss over the penance equals (1-phi) X / N per round (PayoffFunctions penance loss)
        assertThat(Fx.piC(s, 0.6) - r.rounds().get(5).agent("D").payoff()).isCloseTo(0.7 * x / 2, within(TOL));
    }

    // trigger-vs-compete: TriggerK(0.6) + AlwaysCompete; overrides: as above.
    @Test
    void triggerVsCompete() {
        Scenario s = Fx.known(10);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("T", TRIGGER_K, "theta", 0.6), Fx.spec("C", ALWAYS_COMPETE))).run(1);
        r.rounds().forEach(x -> {
            assertThat(x.insideQuote()).isCloseTo(1.0, within(TOL)); // s0 from round 1
            assertThat(x.agent("T").payoff()).isCloseTo(0.0, within(TOL));
            assertThat(x.agent("C").payoff()).isCloseTo(0.0, within(TOL));
        });
        assertThat(r.rounds().get(0).agent("T").ownCi()).isCloseTo(0.6, within(TOL));
    }

    // two-trigger-false-alarm-recovery: pair TriggerK(0.6, k=3), one false signal injected into A at round 3.
    // Overrides: as above, no noise. A is at war in rounds 3-5; B sees A's war quote and mirrors in rounds 4-6 (it cannot
    // tell the cause); each ignores the other's war thanks to the grace round, so the pair recovers at round 7/8.
    @Test
    void falseAlarmRecovery() {
        Scenario s = Fx.known(16);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 0.6, "k", 3, "falseSignalAtRound", 3),
                Fx.spec("B", TRIGGER_K, "theta", 0.6, "k", 3))).run(1);
        for (int t = 1; t <= 16; t++) {
            var rr = r.rounds().get(t - 1);
            assertThat(rr.agent("A").phase().equals("WAR")).as("A war at %d", t).isEqualTo(t >= 3 && t <= 5);
            assertThat(rr.agent("B").phase().equals("WAR")).as("B war at %d", t).isEqualTo(t >= 4 && t <= 6);
            if (t >= 7) {
                assertThat(rr.insideCi()).isCloseTo(0.6, within(TOL));
            }
        }
        assertThat(r.rounds().stream().filter(x -> x.agent("A").phase().equals("WAR")).count()).isEqualTo(3);
        assertThat(r.rounds().stream().filter(x -> x.agent("B").phase().equals("WAR")).count()).isEqualTo(3);
    }
}
