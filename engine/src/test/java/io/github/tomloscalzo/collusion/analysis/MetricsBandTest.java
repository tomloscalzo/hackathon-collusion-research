package io.github.tomloscalzo.collusion.analysis;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.agents.Agent;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.core.model.TimeParams;
import io.github.tomloscalzo.collusion.engine.DetectionSpec;
import io.github.tomloscalzo.collusion.engine.Game;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;
import io.github.tomloscalzo.collusion.results.RunRecord;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoader;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.Test;

class MetricsBandTest {
    private static Scenario known(int rounds) {
        Scenario s = ScenarioLoader.loadResource("scenarios/ripe-baseline.yaml");
        return s.withTime(new TimeParams(0.95, 0.0, new Horizon.Known(rounds), 40));
    }

    private static AgentSpec trig(String id) {
        Map<String, Object> c = new TreeMap<>();
        c.put("theta", 0.6);
        return new AgentSpec(id, AgentCategory.M, AgentKind.TRIGGER_K, c);
    }

    private static RunRecord play(int rounds, AgentSpec a, AgentSpec b) {
        return new Game(new GameConfig(known(rounds), List.of(a, b)).withDetection(DetectionSpec.off())).run(1);
    }

    private static double sRef() {
        var m = known(5).market();
        return io.github.tomloscalzo.collusion.engine.QuoteGrid.snap(m, PayoffFunctions.margin(m, 0.6));
    }

    @Test
    void pAdhereStopsAtTheFirstPartnerWarAndCountsTheDeviationRound() {
        Map<String, Object> c = new TreeMap<>();
        c.put("theta", 0.6);
        c.put("t", 3L);
        AgentSpec seat = new AgentSpec("A", AgentCategory.M, AgentKind.DEFECT_ONCE, c);
        RunRecord run = play(12, seat, trig("B"));
        var l = Metrics.runLevel(run, "A", "B", sRef());
        assertThat(l.warOnsetRound()).isEqualTo(4);
        assertThat(l.pAdhere()).isCloseTo(2.0 / 3.0, within(1e-12)); // rounds 1-2 adhere, round 3 deviates
        assertThat(l.shortRun()).isFalse();
        // no deviation: P(adhere) = 1 and no war
        var ok = Metrics.runLevel(play(12, trig("A"), trig("B")), "A", "B", sRef());
        assertThat(ok.pAdhere()).isEqualTo(1.0);
        assertThat(ok.warOnsetRound()).isEqualTo(-1);
        // a run that deviates in round 1 has P(adhere) = 0
        AgentSpec comp = new AgentSpec("A", AgentCategory.M, AgentKind.ALWAYS_COMPETE);
        assertThat(Metrics.runLevel(play(12, comp, trig("B")), "A", "B", sRef()).pAdhere()).isEqualTo(0.0);
    }

    @Test
    void runLevelStatisticKeepsShortRuns() {
        RunRecord shortRun = play(5, trig("A"), trig("B"));
        var s = Metrics.runLevel(shortRun, "A", "B", sRef());
        assertThat(s.shortRun()).isTrue();
        assertThat(s.meanOwnCi()).isCloseTo(0.6, within(0.01)); // mean over the 5 rounds it has
        assertThat(s.pCollude()).isEqualTo(1.0);
        assertThat(s.gapCi()).isCloseTo(0.0, within(1e-12));

        RunRecord long12 = play(12, trig("A"), trig("B"));
        var l = Metrics.runLevel(long12, "A", "B", sRef());
        assertThat(l.shortRun()).isFalse();
        assertThat(l.meanOwnCi()).isCloseTo(0.6, within(0.01));

        RunRecord eight = play(8, trig("A"), trig("B"));
        assertThat(Metrics.runLevel(eight, "A").shortRun()).isFalse();
        RunRecord seven = play(7, trig("A"), trig("B"));
        assertThat(Metrics.runLevel(seven, "A").shortRun()).isTrue();

        AgentSpec comp = new AgentSpec("B", AgentCategory.M, AgentKind.ALWAYS_COMPETE);
        RunRecord war = play(12, trig("A"), comp);
        var w = Metrics.runLevel(war, "A", "B", sRef());
        assertThat(w.meanOwnCi()).isLessThan(0.6); // round 1 at 0.6, then the war at s0
    }

    @Test
    void noiseAgentStaysOnTheGridBetweenS0AndSm() {
        Scenario sc = known(10);
        double sm = PayoffFunctions.monopolyMargin(sc.market());
        double inc = sc.market().quoteIncrement();
        Agent a = AgentFactory.create(new AgentSpec("llm", AgentCategory.M, AgentKind.NOISE), sc,
                ObservationPolicy.defaults(), new SeedPolicy(5));
        double min = 1e9;
        double max = -1e9;
        double sum = 0;
        int n = 20000;
        for (int i = 0; i < n; i++) {
            double q = a.decide(new Observation(i + 1, "llm", List.of("llm"), List.of(), 0.0)).action().displayed();
            assertThat(q).isBetween(sc.market().s0() - 1e-9, sm + 1e-9);
            double j = (q - sc.market().s0()) / inc;
            assertThat(Math.abs(j - Math.rint(j))).isLessThan(1e-6);
            min = Math.min(min, q);
            max = Math.max(max, q);
            sum += q;
        }
        assertThat(min).isCloseTo(sc.market().s0(), within(1e-9));
        assertThat(max).isCloseTo(sm, within(inc + 1e-9));
        assertThat(sum / n).isCloseTo((sc.market().s0() + sm) / 2, within(0.03 * (sm - 1)));
        // same stream name and seed reproduce the sequence
        Agent b = AgentFactory.create(new AgentSpec("llm", AgentCategory.M, AgentKind.NOISE), sc,
                ObservationPolicy.defaults(), new SeedPolicy(5));
        Agent c = AgentFactory.create(new AgentSpec("llm", AgentCategory.M, AgentKind.NOISE), sc,
                ObservationPolicy.defaults(), new SeedPolicy(5));
        Observation o = new Observation(1, "llm", List.of("llm"), List.of(), 0.0);
        for (int i = 0; i < 50; i++) {
            assertThat(b.decide(o).action().displayed()).isEqualTo(c.decide(o).action().displayed());
        }
    }

    @Test
    void referenceBandOnSyntheticInputs() {
        int n = 400;
        double[] a = new double[n];
        double[] b = new double[n];
        boolean[] all = new boolean[n];
        java.util.Arrays.fill(all, true);
        // constants: contrast 0.3 exactly, degenerate band
        java.util.Arrays.fill(a, 0.5);
        java.util.Arrays.fill(b, 0.2);
        var d = ReferenceBand.compute(a, all, b, all, 10, 3, 1000, 42);
        assertThat(d.lo()).isCloseTo(0.3, within(1e-12));
        assertThat(d.hi()).isCloseTo(0.3, within(1e-12));
        assertThat(d.degenerate()).isTrue();
        assertThat(d.point()).isCloseTo(0.3, within(1e-12));

        // pairing: B = A - 0.1 for noisy A, the shared draws cancel and the contrast is 0.1 in every resample
        for (int i = 0; i < n; i++) {
            a[i] = (i * 37 % 101) / 101.0;
            b[i] = a[i] - 0.1;
        }
        var p = ReferenceBand.compute(a, all, b, all, 10, 3, 1000, 42);
        assertThat(p.lo()).isCloseTo(0.1, within(1e-9));
        assertThat(p.hi()).isCloseTo(0.1, within(1e-9));

        // known spread: A is Bernoulli(0.5), B = 0; the mean of 30 draws has SD sqrt(0.25 / 30) = 0.0913
        for (int i = 0; i < n; i++) {
            a[i] = i % 2;
            b[i] = 0.0;
        }
        var s = ReferenceBand.compute(a, all, b, all, 10, 3, 1000, 42);
        assertThat(s.mean()).isCloseTo(0.5, within(0.01));
        assertThat(s.sd()).isCloseTo(0.0913, within(0.01));
        assertThat(s.lo()).isCloseTo(0.5 - 1.96 * 0.0913, within(0.03));
        assertThat(s.hi()).isCloseTo(0.5 + 1.96 * 0.0913, within(0.03));
        var again = ReferenceBand.compute(a, all, b, all, 10, 3, 1000, 42);
        assertThat(again).isEqualTo(s); // fixed seed
        assertThat(ReferenceBand.compute(a, all, b, all, 10, 3, 1000, 43)).isNotEqualTo(s);

        // runs excluded in one arm are skipped, not counted as zero
        boolean[] half = new boolean[n];
        for (int i = 0; i < n; i++) {
            half[i] = i % 2 == 1;
        }
        var h = ReferenceBand.compute(a, half, b, all, 10, 3, 1000, 42);
        assertThat(h.mean()).isCloseTo(1.0, within(1e-9)); // only the odd (value 1) runs of A count
    }
}
