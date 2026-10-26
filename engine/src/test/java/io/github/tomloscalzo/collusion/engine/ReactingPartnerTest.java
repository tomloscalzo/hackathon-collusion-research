package io.github.tomloscalzo.collusion.engine;

import static io.github.tomloscalzo.collusion.core.model.AgentKind.LOGIT;
import static io.github.tomloscalzo.collusion.core.model.AgentKind.TRIGGER_K;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.agents.LogitAgent;
import io.github.tomloscalzo.collusion.core.layera.CartelSolver;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.results.RunRecord;
import org.junit.jupiter.api.Test;

/**
 * reacting-partner-rational. Overrides: ripe baseline economics, known horizon 8 with delta0 0.95 (delta 0.95),
 * detection OFF, demandNoiseSd 0, o = 1, quoteIncrement 0.01, punishmentLevel S0, partner tolerance 0 (lead correction),
 * LogitAgent lambda0 = 0 and sigma stated per test (T28).
 */
class ReactingPartnerTest {
    private static final double HALF_INC = 0.005;

    private void check(int partnerK, double sigma) {
        Scenario s = Fx.known(8);
        double thetaStar = new CartelSolver().solve(s).thetaStar();
        assertThat(thetaStar).isCloseTo(0.5459, within(1e-3));
        double sStar = Fx.s(s, thetaStar);
        GameConfig c = Fx.cfg(s,
                Fx.spec("L", LOGIT, "lambda0", 0.0, "sigma", sigma, "partnerTheta", thetaStar, "partnerK", partnerK),
                Fx.spec("P", TRIGGER_K, "theta", thetaStar, "k", partnerK));
        RunRecord r = new Game(c).run(11);
        r.rounds().forEach(x -> {
            assertThat(x.agent("L").displayed()).isCloseTo(sStar, within(HALF_INC));
            assertThat(x.agent("P").phase()).isEqualTo("ADHERE");
        });
        double evA = r.rounds().get(0).agent("L").info().get("evAdhere");
        double evU = r.rounds().get(0).agent("L").info().get("evUndercut");
        System.out.printf("reacting-partner k=%d sigma=%g: s*=%.4f quote=%.2f EV(adhere)=%.3f EV(undercut one increment)=%.3f%n",
                partnerK, sigma, sStar, r.rounds().get(0).agent("L").displayed(), evA, evU);
        assertThat(evA).isGreaterThan(evU);
    }

    @Test
    void grimPartnerArgmax() {
        check(-1, 0.0); // k = scenario punishmentLength = -1 (grim)
    }

    @Test
    void grimPartnerSmallSigma() {
        check(-1, 1e-3);
    }

    @Test
    void threeRoundWarPartner() {
        check(3, 0.0);
    }

    // The logit agent EVs match the solver: adhering at s_p is worth W(theta_p).
    @Test
    void adhereValueIsW() {
        Scenario s = Fx.known(8);
        double thetaStar = new CartelSolver().solve(s).thetaStar();
        double sP = Math.rint((Fx.s(s, thetaStar) - 1.0) / 0.01) * 0.01 + 1.0;
        double theta = (sP - 1.0) / 2.0;
        LogitAgent l = new LogitAgent("L", s, 0.0, 0.0, thetaStar, 3, 0.0);
        assertThat(l.evAdhere()).isCloseTo(new CartelSolver().w(s, theta), within(1e-6));
    }
}
