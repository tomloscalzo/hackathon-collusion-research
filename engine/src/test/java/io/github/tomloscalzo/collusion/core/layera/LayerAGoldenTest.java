package io.github.tomloscalzo.collusion.core.layera;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.core.model.Aggregates;
import io.github.tomloscalzo.collusion.core.model.EnforcementParams;
import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.PunishmentForm;
import io.github.tomloscalzo.collusion.core.model.PunishmentLevel;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.core.model.SignalKind;
import io.github.tomloscalzo.collusion.core.model.TimeParams;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoader;
import org.junit.jupiter.api.Test;

class LayerAGoldenTest {
    private final CartelSolver solver = new CartelSolver();

    private static Scenario base() {
        return ScenarioLoader.loadResource("scenarios/ripe-baseline.yaml");
    }

    private static Scenario withH(Scenario s, double h) {
        return s.withTime(s.time().withHorizon(new Horizon.Random(h)));
    }

    /** delta0 = 1 and h = 1 - delta. */
    private static Scenario withDelta(Scenario s, double delta) {
        return s.withTime(new TimeParams(1.0, s.time().entryHazard(), new Horizon.Random(1.0 - delta), s.time().maxRounds()));
    }

    private static Scenario noHazard(Scenario s) {
        EnforcementParams e = s.enforcement();
        return s.withEnforcement(new EnforcementParams(e.screen().withSlope(0.0), 0.0, e.tipDuringPunishment(), 0.0, 0.0, 0.0));
    }

    private void assertSens(Scenario s, double theta, double e) {
        CartelSolution sol = solver.solve(s);
        assertThat(sol.thetaStar()).isCloseTo(theta, within(1e-3));
        assertThat(sol.ripeness()).isCloseTo(e, within(1e-3));
    }

    // 1
    @Test
    void ripeBaseline() {
        Scenario s = base();
        assertThat(s.delta()).isCloseTo(0.95, within(1e-12));
        CartelSolution sol = solver.solve(s);
        assertThat(sol.thetaStar()).isCloseTo(0.5459, within(1e-3));
        assertThat(sol.wStar()).isCloseTo(238.43, within(0.1));
        assertThat(sol.ripeness()).isCloseTo(0.4526, within(1e-3));
        assertThat(sol.regime()).isEqualTo(Regime.INTERIOR_EXTERNAL);
        assertThat(sol.w0()).isCloseTo(0.0, within(1e-12));
        assertThat(solver.w(s, 1.0)).isCloseTo(153.85, within(0.1));
        assertThat(sol.multipleStageNash()).isFalse();
        assertThat(sol.myopicallyUnripe()).isFalse();
        assertThat(sol.thetaGrid()).hasSize(1001);
        double rho = 0.025 * 2 * sol.thetaStar();
        double psi = Enforcement.psi(s.delta() * (1 - rho), 1.0, -1);
        assertThat(psi).isCloseTo(12.17, within(0.01));
        assertThat(psi).isGreaterThan(0.7);
        assertThat(solver.ic(s, sol.thetaStar())).isTrue();
    }

    // 2
    @Test
    void sensitivities() {
        Scenario b = base();
        assertSens(withH(b, 0.10), 0.6051, 0.4659);
        assertSens(withH(b, 0.01), 0.3624, 0.3670);
        EnforcementParams e = b.enforcement();
        assertSens(b.withEnforcement(e.withRhoTip(0.01)), 0.5985, 0.3435);
        assertSens(b.withEnforcement(e.withRhoTip(0.02)), 0.6399, 0.2284);
        assertSens(b.withEnforcement(e.withRhoCoop(0.3)), 0.684, 0.772);
        assertSens(b.withEnforcement(e.withRhoCoop(0.6)), 0.626, 0.625);
        assertSens(b.withEnforcement(e.withRhoCoop(0.0)), 0.740, 0.932);
        assertSens(b.withMarket(b.market().withN(3)), 0.4395, 0.2738);
        assertSens(b.withMarket(b.market().withN(4)), 0.3249, 0.1381);
        assertSens(b.withMarket(b.market().withSBar(4.0)), 0.5564, 0.4323);
        assertSens(b.withMarket(b.market().withSBar(6.0)), 0.5320, 0.4618);
    }

    // 3
    @Test
    void unripeA() {
        Scenario s = base().withEnforcement(base().enforcement().withFine(5000));
        CartelSolution sol = solver.solve(s);
        assertThat(sol.thetaStar()).isEqualTo(0.0);
        assertThat(sol.ripeness()).isEqualTo(0.0);
        assertThat(sol.myopicallyUnripe()).isTrue();
        assertThat(sol.regime()).isEqualTo(Regime.CORNER_ZERO);
    }

    // 4
    @Test
    void handValues() {
        MarketParams m = base().market();
        assertThat(PayoffFunctions.piC(m, 1.0)).isCloseTo(40.0, within(1e-9));
        assertThat(PayoffFunctions.piD(m, 1.0)).isCloseTo(68.0, within(1e-9));
        assertThat(PayoffFunctions.deviationGain(m, 1.0)).isCloseTo(28.0, within(1e-9));
        assertThat(PayoffFunctions.piD(m.withTick(0.5), 1.0)).isCloseTo(63.75, within(1e-9));
        MarketParams t = m.withTick(0.25);
        assertThat(PayoffFunctions.nashTickMultiple(t)).isEqualTo(2);
        assertThat(PayoffFunctions.nashMargin(t)).isCloseTo(1.5, within(1e-12));
        assertThat(PayoffFunctions.piNash(t)).isCloseTo(17.5, within(1e-9));
        assertThat(PayoffFunctions.deviationGain(t, 0.0)).isCloseTo(-1.5625, within(1e-9));
        assertThat(PayoffFunctions.deviationGain(t, 0.0)).isCloseTo(0.25 * 75 * 0.85 - 17.5, within(1e-9));
    }

    // 5
    @Test
    void psi() {
        for (double d : new double[] {0.1, 0.5, 0.9, 0.99}) {
            assertThat(Enforcement.psi(d, 0.7, 1)).isCloseTo(d * 0.7, within(1e-12));
            assertThat(Enforcement.psi(d, 1.0, -1)).isCloseTo(d / (1 - d), within(1e-9));
            for (int k : new int[] {1, 2, 5, 10, 50}) {
                assertThat(Enforcement.psi(d, 0.8, k)).isLessThanOrEqualTo(d * 0.8 * k + 1e-12);
            }
        }
        assertThat(Enforcement.psi(0.9, 1.0, 10)).isCloseTo(9 * (1 - Math.pow(0.9, 10)), within(1e-12));
        assertThat(Enforcement.psi(0.9, 1.0, 0)).isEqualTo(0.0);
    }

    private static Scenario friedman(double delta, int k) {
        Scenario s = noHazard(withDelta(base(), delta));
        return s.withMarket(s.market().withN(2).withPhi(0.0)).withPunishmentLength(k);
    }

    private boolean icAllTheta(Scenario s) {
        CartelSolution sol = solver.solve(s);
        boolean all = true;
        boolean none = true;
        for (int i = 1; i < sol.icGrid().size(); i++) {
            all &= sol.icGrid().get(i);
            none &= !sol.icGrid().get(i);
        }
        assertThat(all || none).as("IC is theta-independent").isTrue();
        return all;
    }

    // 6
    @Test
    void friedmanBoundary() {
        assertThat(icAllTheta(friedman(0.5 + 1e-3, -1))).isTrue();
        assertThat(icAllTheta(friedman(0.5 - 1e-3, -1))).isFalse();
        assertThat(icAllTheta(friedman(0.5437 + 1e-3, 3))).isTrue();
        assertThat(icAllTheta(friedman(0.5437 - 1e-3, 3))).isFalse();
        assertThat(solver.solve(friedman(0.6, -1)).thetaHat()).isEqualTo(1.0);
        assertThat(solver.solve(friedman(0.4, -1)).thetaHat()).isEqualTo(0.0);
    }

    // 7
    @Test
    void eq9Limit() {
        Scenario s = noHazard(withDelta(base(), 0.7));
        s = s.withMarket(s.market().withN(3).withPhi(0.3));
        boolean expected = (1 - 0.3) * 2 <= Enforcement.psi(0.7, 1.0, -1);
        assertThat(solver.eq9Holds(s)).isEqualTo(expected);
        for (double th : new double[] {0.1, 0.5, 1.0}) {
            assertThat(solver.ic(s, th)).isEqualTo(expected);
        }
        // fails case
        Scenario f = noHazard(withDelta(base(), 0.55));
        f = f.withMarket(f.market().withN(3).withPhi(0.0));
        for (double th : new double[] {0.1, 0.5, 1.0}) {
            assertThat(solver.ic(f, th)).isFalse();
        }
        assertThat(solver.eq9Holds(f)).isFalse();

        Scenario many = noHazard(withDelta(base(), 0.95));
        many = many.withMarket(many.market().withN(50).withPhi(0.0));
        CartelSolution ms = solver.solve(many);
        assertThat(ms.thetaHat()).isEqualTo(0.0);
        assertThat(ms.thetaStar()).isEqualTo(0.0);

        Scenario folk = noHazard(withH(base(), 0.005));
        folk = folk.withMarket(folk.market().withN(5).withPhi(0.0));
        CartelSolution fs = solver.solve(folk);
        assertThat(fs.thetaStar()).isCloseTo(1.0, within(1e-6));
        assertThat(fs.regime()).isEqualTo(Regime.CORNER_ONE);
    }

    // 8
    @Test
    void penanceVersusPriceWar() {
        // N = 3, delta = 0.55: Psi = 1.222. Price war threshold (1-phi)*2 moves with phi; penance needs 2 <= Psi.
        Scenario s = noHazard(withDelta(base(), 0.55));
        Scenario w3 = s.withMarket(s.market().withN(3).withPhi(0.3));
        Scenario w6 = s.withMarket(s.market().withN(3).withPhi(0.6));
        assertThat(solver.ic(w3, 0.5)).isFalse(); // 1.4 > 1.222
        assertThat(solver.ic(w6, 0.5)).isTrue(); // 0.8 <= 1.222
        Scenario p3 = w3.withPunishment(PunishmentForm.PENANCE);
        Scenario p6 = w6.withPunishment(PunishmentForm.PENANCE);
        assertThat(solver.ic(p3, 0.5)).isFalse(); // 2 > 1.222
        assertThat(solver.ic(p6, 0.5)).isFalse();
        // delta = 0.7: Psi = 2.333, penance holds for both phi; ratio is phi independent
        Scenario t = noHazard(withDelta(base(), 0.7));
        for (double phi : new double[] {0.3, 0.6}) {
            Scenario pen = t.withMarket(t.market().withN(3).withPhi(phi)).withPunishment(PunishmentForm.PENANCE);
            assertThat(solver.ic(pen, 0.5)).isTrue();
            MarketParams m = pen.market();
            double ratio = PayoffFunctions.deviationGain(m, 0.5)
                    / PayoffFunctions.punishmentLoss(m, 0.5, PunishmentForm.PENANCE, PunishmentLevel.S0, 0.0);
            assertThat(ratio).isCloseTo(2.0, within(1e-9));
        }
    }

    // 9
    @Test
    void jStar() {
        MarketParams m = base().market();
        assertThat(PayoffFunctions.nashTickMultiple(m.withTick(0.125))).isEqualTo(2);
        assertThat(PayoffFunctions.nashTickMultiple(m.withTick(0.25))).isEqualTo(2);
        assertThat(PayoffFunctions.nashTickMultiple(m.withN(5).withPhi(0.5).withTick(0.125))).isEqualTo(1);
        assertThat(PayoffFunctions.nashMargin(m)).isEqualTo(1.0);
    }

    // 10
    @Test
    void tickIcBinding() {
        Scenario b = base();
        Scenario s = b.withMarket(b.market().withTick(0.25)).withPunishmentLength(1)
                .withAggregates(b.aggregates().withQCollective(0.5));
        CartelSolution sol = solver.solve(s);
        assertThat(sol.multipleStageNash()).isTrue();
        assertThat(sol.thetaGrid()).hasSize(7);
        double span = 1.5;
        for (int j = 0; j < 7; j++) {
            double margin = 1.5 + 0.25 * j;
            assertThat(sol.thetaGrid().get(j)).isCloseTo(0.25 * j / span, within(1e-12));
            assertThat(sol.icGrid().get(j)).as("IC at s=" + margin).isEqualTo(margin <= 2.0 + 1e-9);
        }
        int jMax = 0;
        for (int j = 1; j < 7; j++) {
            if (sol.wGrid().get(j) > sol.wGrid().get(jMax)) {
                jMax = j;
            }
        }
        assertThat(1.5 + 0.25 * jMax).isCloseTo(2.25, within(1e-9));
        assertThat(sol.wGrid().get(jMax)).isCloseTo(460.6, within(0.1));
        assertThat(sol.thetaStar()).isCloseTo(0.333, within(1e-3));
        assertThat(sol.thetaHat()).isCloseTo(0.333, within(1e-3));
        assertThat(sol.regime()).isEqualTo(Regime.INTERIOR_INTERNAL);
        assertThat(sol.ripeness()).isCloseTo(0.156, within(1e-3));
        assertThat(sol.wStar()).isCloseTo(451.0, within(0.1));
    }

    // 11
    @Test
    void nasdaq() {
        Scenario b = base();
        for (int n : new int[] {10, 60}) {
            for (double sBar : new double[] {0.5, 1.0, 2.0}) {
                MarketParams m = new MarketParams(n, 0.5, 0.0625, sBar, 100, 0.0625, 0.0625);
                assertThat(PayoffFunctions.nashTickMultiple(m)).isEqualTo(1);
                assertThat(PayoffFunctions.nashMargin(m)).isCloseTo(0.125, within(1e-12));
                assertThat(PayoffFunctions.collusionIndex(m, 0.125)).isCloseTo(0.0, within(1e-12));
                double expected = sBar == 0.5 ? 0.800 : sBar == 1.0 ? 0.308 : 0.138;
                assertThat(PayoffFunctions.collusionIndex(m, 0.25)).isCloseTo(expected, within(1e-3));
            }
            MarketParams m0 = new MarketParams(n, 0.5, 0.0625, 1.0, 100, 0.0, 0.0625);
            Scenario s = noHazard(withH(b, 0.0002)).withMarket(m0);
            assertThat(s.delta()).isCloseTo(0.9998, within(1e-12));
            assertThat(solver.eq9Holds(s)).isTrue();
        }
    }

    // 12
    @Test
    void eq15AndQ() {
        double a = 0.05 * 0.95 / 0.05;
        assertThat(Enforcement.psi(0.95, 1.0, -1) * 0.05).isCloseTo(a, within(1e-9));
        assertThat(a).isCloseTo(0.95, within(1e-9));
        double piC = 40, piP = 0;
        double eff = PayoffFunctions.effectivePiC(piC, piP, 0.05, 0.95, -1);
        assertThat((piC - eff) / (piC - piP)).isCloseTo(0.4872, within(1e-4));
        assertThat(eff).isGreaterThanOrEqualTo(piP);
        assertThat(Enforcement.qCollective(0.5, 3, SignalKind.PRIVATE)).isCloseTo(0.75, within(1e-12));
        assertThat(Enforcement.qCollective(0.5, 3, SignalKind.PUBLIC)).isCloseTo(0.5, within(1e-12));
    }

    @Test
    void changeKindAcceptedWithFlag() {
        Scenario b = base();
        var sc = new io.github.tomloscalzo.collusion.core.model.ScreenShape(
                io.github.tomloscalzo.collusion.core.model.DetectionShape.CHANGE,
                b.enforcement().screen().scale(), 0.025);
        CartelSolution sol = solver.solve(b.withEnforcement(b.enforcement().withScreen(sc)));
        assertThat(sol.screenChangeTreatedAsLevel()).isTrue();
        assertThat(sol.thetaStar()).isCloseTo(0.5459, within(1e-3));
    }

    @Test
    void staticNashPunishmentAndIrp() {
        MarketParams m = base().market().withTick(0.25);
        // L at theta = 0 under STATIC_NASH is 0 plus IRP
        assertThat(PayoffFunctions.punishmentLoss(m, 0.0, PunishmentForm.PRICE_WAR, PunishmentLevel.STATIC_NASH, 0.0))
                .isCloseTo(0.0, within(1e-12));
        assertThat(PayoffFunctions.punishmentLoss(m, 0.0, PunishmentForm.PRICE_WAR, PunishmentLevel.STATIC_NASH, 2.0))
                .isCloseTo(2.0, within(1e-12));
        Aggregates a = base().aggregates().withSumIRP(1.0);
        assertThat(a.sumIRP()).isEqualTo(1.0);
    }
}
