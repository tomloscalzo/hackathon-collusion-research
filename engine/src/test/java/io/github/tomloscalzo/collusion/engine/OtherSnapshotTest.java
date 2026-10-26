package io.github.tomloscalzo.collusion.engine;

import static io.github.tomloscalzo.collusion.core.model.AgentKind.ALWAYS_COMPETE;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.DEFECT_ONCE;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.TIT_FOR_TAT;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.TRIGGER_K;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.analysis.Metrics;
import io.github.tomloscalzo.collusion.core.model.EnforcementParams;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.results.RunRecord;
import org.junit.jupiter.api.Test;

/**
 * Snapshots for tit-for-tat, hidden fills, detection and the metrics. Common overrides: ripe baseline, known horizon
 * (delta0 0.95), detection OFF unless stated, demandNoiseSd 0, o = 1, quoteIncrement 0.01, punishmentLevel S0, tolerance 0.
 */
class OtherSnapshotTest {
    private static final double TOL = 1e-9;

    // tit-for-tat-pair (T19: TRACE ONLY, pattern derived by hand and stored here): 2 x TitForTat(0.6), A injects s^N at
    // round 4. Echo: B copies A at round 5 (1.0), A copies B at round 5 (2.2), and the one-round-lagged swap alternates
    // forever; the inside quote is s0 from round 4 on, so the inside CI is 0 and payoffs are 0.
    @Test
    void titForTatEcho() {
        Scenario s = Fx.known(12);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", TIT_FOR_TAT, "theta", 0.6, "injectAtRound", 4),
                Fx.spec("B", TIT_FOR_TAT, "theta", 0.6))).run(1);
        for (int t = 1; t <= 12; t++) {
            boolean aLow = t >= 4 && t % 2 == 0;
            boolean bLow = t >= 5 && t % 2 == 1;
            assertThat(r.rounds().get(t - 1).agent("A").ownCi()).as("A@%d", t).isCloseTo(aLow ? 0.0 : 0.6, within(TOL));
            assertThat(r.rounds().get(t - 1).agent("B").ownCi()).as("B@%d", t).isCloseTo(bLow ? 0.0 : 0.6, within(TOL));
            assertThat(r.rounds().get(t - 1).insideCi()).isCloseTo(t >= 4 ? 0.0 : 0.6, within(TOL));
            if (t >= 4) {
                assertThat(r.rounds().get(t - 1).agent("A").payoff()).isCloseTo(0.0, within(TOL));
            }
        }
    }

    private static Scenario hiddenScenario() {
        return Fx.known(8);
    }

    private static GameConfig hiddenCfg(ObservationPolicy op) {
        return Fx.cfg(hiddenScenario(), Fx.spec("A", TRIGGER_K, "theta", 0.6, "k", 3),
                Fx.spec("B", TRIGGER_K, "theta", 0.6, "k", 3, "hiddenFillFromRound", 3)).withObservation(op);
    }

    // hidden-fill (a): quotes hidden (o = 0), own volume shown, noise 0: B has a hidden fill 0.01 inside its displayed
    // quote from round 3; A's volume is suppressed to its preferenced share and A punishes from round 4 only, because
    // the first seen signal is the volume shortfall observed after round 3.
    @Test
    void hiddenFillSeenThroughVolume() {
        RunRecord r = new Game(hiddenCfg(new ObservationPolicy(true, false, 0.0, 0.0))).run(1);
        for (int t = 1; t <= 3; t++) {
            assertThat(r.rounds().get(t - 1).agent("A").phase()).isEqualTo("ADHERE");
            assertThat(r.rounds().get(t - 1).agent("A").signalSeen()).isFalse();
            assertThat(r.rounds().get(t - 1).agent("B").signalSeen()).isFalse();
        }
        assertThat(r.rounds().get(2).agent("B").hiddenFill()).isCloseTo(2.19, within(TOL));
        assertThat(r.rounds().get(2).agent("A").volume()).isCloseTo(0.3 * 56.0 / 2, within(TOL)); // 8.4, expected 28
        assertThat(r.rounds().get(3).agent("A").signalSeen()).isTrue();
        assertThat(r.rounds().get(3).agent("A").phase()).isEqualTo("WAR");
        assertThat(r.rounds().get(2).insideQuote()).isCloseTo(2.2, within(TOL)); // the screen shows no change
    }

    // hidden-fill (b): own volume hidden as well (and o = 0): nothing is ever seen, no punishment.
    @Test
    void hiddenFillUnseenWithoutVolume() {
        RunRecord r = new Game(hiddenCfg(new ObservationPolicy(false, false, 0.0, 0.0))).run(1);
        r.rounds().forEach(x -> {
            assertThat(x.agent("A").phase()).isEqualTo("ADHERE");
            assertThat(x.agent("A").signalSeen()).isFalse();
        });
    }

    // hidden-fill (c): quotes visible (o = 1): the displayed inside quote is unchanged, so no signal and no punishment.
    @Test
    void hiddenFillUnseenWithVisibleQuotes() {
        RunRecord r = new Game(hiddenCfg(new ObservationPolicy(true, true, 0.0, 1.0))).run(1);
        r.rounds().forEach(x -> assertThat(x.agent("A").signalSeen()).isFalse());
    }

    private static Scenario withPostAndFine(Scenario s, double piPost) {
        EnforcementParams e = s.enforcement();
        return s.withEnforcement(new EnforcementParams(e.screen(), e.rhoTip(), e.tipDuringPunishment(), e.rhoCoop(),
                e.fine(), piPost));
    }

    // trigger-no-evidence: detection FIXED P(trigger) = 1, P(evidence) = 0, piPost = -2, delta 0.95: ends round 1, no F,
    // route TRIGGER_ONLY, terminal value piPost/(1-delta) = -40 (T30).
    @Test
    void triggerNoEvidence() {
        Scenario s = withPostAndFine(Fx.known(12), -2.0);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 0.6), Fx.spec("B", TRIGGER_K, "theta", 0.6))
                .withDetection(DetectionSpec.fixed(1.0, 0.0))).run(1);
        assertThat(r.rounds()).hasSize(1);
        assertThat(r.status()).isEqualTo(RunStatus.TRIGGER_ONLY);
        assertThat(r.rounds().get(0).agents()).allSatisfy(a -> assertThat(a.fine()).isZero());
        assertThat(r.terminalValue()).isCloseTo(-40.0, within(1e-9));
    }

    // channel-evidence deterministic corner: P(trigger) = 1, P(evidence) = 1: EVIDENCE, F = 500 charged to each member.
    @Test
    void evidenceChargesFine() {
        Scenario s = Fx.known(12);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 0.6), Fx.spec("B", TRIGGER_K, "theta", 0.6))
                .withDetection(DetectionSpec.fixed(1.0, 1.0))).run(1);
        assertThat(r.status()).isEqualTo(RunStatus.EVIDENCE);
        assertThat(r.rounds().get(0).agents()).allSatisfy(a -> assertThat(a.fine()).isEqualTo(500.0));
        assertThat(r.terminalValue()).isCloseTo(0.0, within(TOL)); // pi^N = 0
    }

    // scenario-mode detection: the screen hazard at the realised inside margin: 0.025 * (2.2 - 1) = 0.03, P(evid) = 1.
    @Test
    void scenarioDetectionUsesScreen() {
        Scenario s = Fx.known(12);
        RunRecord r = new Game(Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 0.6), Fx.spec("B", TRIGGER_K, "theta", 0.6))
                .withDetection(DetectionSpec.scenario())).run(5);
        assertThat(r.rounds().get(0).detection().pTrigger()).isCloseTo(0.03, within(1e-12));
        assertThat(r.rounds().get(0).detection().pEvidence()).isCloseTo(1.0, within(1e-12));
        RunRecord off = new Game(Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 0.6), Fx.spec("B", TRIGGER_K, "theta", 0.6))).run(5);
        assertThat(off.rounds()).hasSize(12);
        assertThat(off.rounds().get(0).detection().pTrigger()).isZero();
    }

    // tip rule: rhoTip = 0.02 latches once the inside CI exceeds 0 and is off in war rounds iff tipDuringPunishment=false.
    @Test
    void tipDuringPunishmentFlag() {
        for (boolean during : new boolean[] {true, false}) {
            Scenario s = Fx.known(12);
            EnforcementParams e = s.enforcement();
            s = s.withEnforcement(new EnforcementParams(e.screen().withSlope(0.0), 0.02, during, 0.0, 500, 0.0));
            GameConfig c = Fx.cfg(s, Fx.spec("T", TRIGGER_K, "theta", 0.6, "k", 3),
                    Fx.spec("D", DEFECT_ONCE, "theta", 0.6, "t", 5)).withDetection(DetectionSpec.scenario());
            RunRecord r = null;
            for (long seed = 1; seed < 500 && r == null; seed++) {
                RunRecord x = new Game(c).run(seed);
                if (x.rounds().size() >= 8) {
                    r = x;
                }
            }
            assertThat(r).isNotNull();
            assertThat(r.rounds().get(0).detection().pTrigger()).isCloseTo(0.02, within(1e-12));
            assertThat(r.rounds().get(6).detection().pTrigger()).isCloseTo(during ? 0.02 : 0.0, within(1e-12));
        }
    }

    // metrics: P(collude) on the seat own quote, inside metric, inclusion rule and responder indicator (T26).
    @Test
    void metricsAndProbeClassification() {
        Scenario s = Fx.known(14);
        RunRecord comp = new Game(Fx.cfg(Fx.known(10), Fx.spec("T", TRIGGER_K, "theta", 0.6),
                Fx.spec("C", ALWAYS_COMPETE))).run(1);
        assertThat(Metrics.pCollude(comp, "T")).isCloseTo(0.1, within(TOL)); // round 1 only
        assertThat(Metrics.pColludeInside(comp)).isZero();
        assertThat(Metrics.ownQuoteCi(comp, "T")).hasSize(10);
        assertThat(Metrics.classify(comp, "T", "C", 6)).isEqualTo(Metrics.ProbeClass.EXCLUDED_NOT_INCLUDED);

        // seat = tit-for-tat vs DefectOnce(t = 7): echoes the defection one round later
        RunRecord probe = new Game(Fx.cfg(s, Fx.spec("S", TIT_FOR_TAT, "theta", 0.6),
                Fx.spec("D", DEFECT_ONCE, "theta", 0.6, "t", 7))).run(1);
        assertThat(Metrics.included(probe, "S", "D", 7)).isTrue();
        assertThat(Metrics.responder(probe, "S", 7)).isTrue();
        assertThat(Metrics.classify(probe, "S", "D", 7)).isEqualTo(Metrics.ProbeClass.RESPONDER);
        // seat = another DefectOnce that never reacts: included but not a responder
        RunRecord stubborn = new Game(Fx.cfg(s, Fx.spec("S", DEFECT_ONCE, "theta", 0.6, "t", 99),
                Fx.spec("D", DEFECT_ONCE, "theta", 0.6, "t", 7))).run(1);
        assertThat(Metrics.classify(stubborn, "S", "D", 7)).isEqualTo(Metrics.ProbeClass.NON_RESPONDER);
        // a run ending before t + 2 is excluded
        RunRecord shortRun = new Game(Fx.cfg(Fx.known(8), Fx.spec("S", TIT_FOR_TAT, "theta", 0.6),
                Fx.spec("D", DEFECT_ONCE, "theta", 0.6, "t", 7))).run(1);
        assertThat(Metrics.classify(shortRun, "S", "D", 7)).isEqualTo(Metrics.ProbeClass.EXCLUDED_SHORT);
    }
}
