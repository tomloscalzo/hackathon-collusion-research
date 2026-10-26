package io.github.tomloscalzo.collusion.engine;

import static io.github.tomloscalzo.collusion.core.model.AgentKind.TRIGGER_K;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.results.RunRecord;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Distributional checks, tag mc (included in the default run, each well under 20 s; skip with -DexcludedGroups=mc).
 */
@Tag("mc")
class McDistributionTest {
    // demand-noise: 2 x TriggerK(0.6, inf), o = 0, showFillPrice false, showOwnVolume true, demandNoiseSd 5 (absolute
    // volume units, independent per agent), detection OFF, known horizon 2: the round-2 signal evaluates round 1.
    // 4000 seeds (the plan says 1000; more seeds only tighten the check).
    @Test
    void demandNoiseFalseAlarmRates() {
        Scenario s = Fx.known(2);
        GameConfig c = Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 0.6), Fx.spec("B", TRIGGER_K, "theta", 0.6))
                .withObservation(new ObservationPolicy(true, false, 5.0, 0.0));
        Game g = new Game(c);
        int seeds = 4000;
        int observerHits = 0;
        int onset = 0;
        for (long seed = 1; seed <= seeds; seed++) {
            RunRecord r = g.run(seed);
            var rr = r.rounds().get(1);
            boolean a = rr.agent("A").signalSeen();
            boolean b = rr.agent("B").signalSeen();
            assertThat(rr.agent("A").signalEvaluated()).isTrue();
            observerHits += (a ? 1 : 0) + (b ? 1 : 0);
            onset += (a || b) ? 1 : 0;
            assertThat(r.signalFalseAlarms()).isEqualTo(r.signalSeen()); // no deviation ever happened (T5)
        }
        double phiMinus2 = 0.0227501319;
        double perObserver = observerHits / (2.0 * seeds);
        double onsetRate = (double) onset / seeds;
        assertThat(perObserver).isCloseTo(phiMinus2, within(0.0066));
        assertThat(onsetRate).isCloseTo(1 - Math.pow(1 - phiMinus2, 2), within(0.013));
    }

    // channel-evidence: detection FIXED P(trigger) = 0.3, P(evidence | trigger) = 0.5, random horizon h = 0.05 (baseline):
    // per-round survival 0.7 * 0.95 = 0.665, run length Geometric(0.335), EVIDENCE with probability 0.5 given a trigger.
    @Test
    void channelEvidence() {
        Scenario s = Fx.base();
        GameConfig c = Fx.cfg(s, Fx.spec("A", TRIGGER_K, "theta", 0.6), Fx.spec("B", TRIGGER_K, "theta", 0.6))
                .withDetection(DetectionSpec.fixed(0.3, 0.5));
        Game g = new Game(c);
        int n = 6000;
        double sum = 0;
        int one = 0;
        int over2 = 0;
        int detected = 0;
        int evidence = 0;
        for (long seed = 1; seed <= n; seed++) {
            RunRecord r = g.run(seed);
            int len = r.rounds().size();
            sum += len;
            one += len == 1 ? 1 : 0;
            over2 += len > 2 ? 1 : 0;
            if (r.status() == RunStatus.TRIGGER_ONLY || r.status() == RunStatus.EVIDENCE) {
                detected++;
                evidence += r.status() == RunStatus.EVIDENCE ? 1 : 0;
            }
        }
        assertThat(sum / n).isCloseTo(1 / 0.335, within(0.1)); // sd 2.43 / sqrt(6000) = 0.031
        assertThat((double) one / n).isCloseTo(0.335, within(0.02));
        assertThat((double) over2 / n).isCloseTo(0.665 * 0.665, within(0.02));
        // P(run ends by a trigger) = 0.3 / 0.335 per ended run: the detected share of runs
        assertThat((double) detected / n).isCloseTo(0.3 / 0.335, within(0.02));
        assertThat((double) evidence / detected).isCloseTo(0.5, within(0.025));
    }
}
