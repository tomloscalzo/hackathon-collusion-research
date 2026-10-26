package io.github.tomloscalzo.collusion.agents;

import io.github.tomloscalzo.collusion.core.layera.CartelSolver;
import io.github.tomloscalzo.collusion.core.layera.Enforcement;
import io.github.tomloscalzo.collusion.core.layera.HazardBreakdown;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.EnforcementParams;
import io.github.tomloscalzo.collusion.core.model.PunishmentForm;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.engine.Action;
import io.github.tomloscalzo.collusion.engine.Decision;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.engine.QuoteGrid;
import java.util.ArrayList;
import java.util.List;

/**
 * Descriptive synthetic agent facing a disclosed TriggerK(partnerTheta, partnerK) partner. For the two candidates adhere at
 * s_p and undercut by one quoteIncrement it computes the continuation value V(q): quote q now (undercutting wins the contestable flow),
 * then, if q is below s_p by more than partnerTolerance, face the partner war for partnerK rounds, then adhere at s_p
 * forever, all with the scenario hazards, fine and terminal values; adhering at s_p has V = W(theta_p) of the Layer A
 * solver. Utility is V(q) minus lambda0 (payoff units, a reluctance charged when the own-quote CI is at least tau) and
 * the choice is softmax(utility / sigma); sigma &lt;= 0 is the exact argmax (ties go to the higher quote). The policy
 * is stationary (it models the partner as adhering/reacting and ignores observed history). The value is "gross" of
 * nothing else: the external penalty is inside V through the hazard terms (T6 split not implemented).
 */
public final class LogitAgent implements Agent {
    private final String id;
    private final List<Double> quotes = new ArrayList<>();
    private final List<Double> probs = new ArrayList<>();
    private final List<Double> evs = new ArrayList<>();

    public LogitAgent(String id, Scenario sc, double lambda0, double sigma, double partnerTheta, int partnerK,
                      double partnerTolerance) {
        this.id = id;
        var m = sc.market();
        EnforcementParams e = sc.enforcement();
        double delta = sc.delta();
        double sN = PayoffFunctions.nashMargin(m);
        double sP = QuoteGrid.snap(m, PayoffFunctions.margin(m, partnerTheta));
        double thetaP = StrictMath.max(0.0, StrictMath.min(1.0, PayoffFunctions.collusionIndex(m, sP)));
        double wP = new CartelSolver().w(sc, thetaP);
        double z = PayoffFunctions.piNash(m) / (1.0 - delta);
        double zPost = e.piPost() / (1.0 - delta);
        double c = PayoffFunctions.contestableShare(m);
        double pEv = 1.0 - (1.0 - sc.aggregates().dBarU()) * (1.0 - e.rhoCoop());
        double rwT = e.tipDuringPunishment() ? e.rhoTip() : 0.0;
        double rwE = rwT * pEv;
        double warPay = PayoffFunctions.piPunish(m, thetaP, PunishmentForm.PRICE_WAR, sc.punishmentLevel(), 0.0);
        double uw = warPay - rwE * e.fine() + delta * (rwE * z + (rwT - rwE) * zPost);
        double surv = delta * (1.0 - rwT);
        double vWar;
        if (partnerK < 0) {
            vWar = uw / (1.0 - surv);
        } else {
            vWar = wP;
            for (int j = 0; j < partnerK; j++) {
                vWar = uw + surv * vWar;
            }
        }
        List<Double> util = new ArrayList<>();
        int jMax = (int) StrictMath.floor((sP - m.s0()) / m.quoteIncrement() + 1e-9);
        for (int j = StrictMath.max(0, jMax - 1); j <= jMax; j++) {
            double q = QuoteGrid.snap(m, m.s0() + j * m.quoteIncrement());
            boolean under = q < sP - 1e-9;
            boolean punished = q < sP - partnerTolerance - 1e-9;
            double ci = PayoffFunctions.collusionIndex(m, q);
            HazardBreakdown h = ci > 1e-9 ? Enforcement.hazard(e, q - sN, ci, sc.aggregates().dBarU())
                    : HazardBreakdown.ZERO;
            double stage = under ? c * PayoffFunctions.rent(m, q) : PayoffFunctions.rent(m, sP) / m.n();
            double rT = h.rhoEnd();
            double rE = h.rhoFine();
            double v = stage - rE * e.fine()
                    + delta * (rE * z + (rT - rE) * zPost + (1.0 - rT) * (punished ? vWar : wP));
            double u = v - (ci >= sc.tau() ? lambda0 : 0.0);
            quotes.add(q);
            evs.add(v);
            util.add(u);
        }
        double best = Double.NEGATIVE_INFINITY;
        for (double u : util) {
            best = StrictMath.max(best, u);
        }
        if (sigma <= 0.0) {
            int pick = -1;
            for (int i = 0; i < util.size(); i++) {
                if (util.get(i) >= best - 1e-12) {
                    pick = i;
                }
            }
            for (int i = 0; i < util.size(); i++) {
                probs.add(i == pick ? 1.0 : 0.0);
            }
        } else {
            double sum = 0.0;
            List<Double> w = new ArrayList<>();
            for (double u : util) {
                double x = StrictMath.exp((u - best) / sigma);
                w.add(x);
                sum += x;
            }
            for (double x : w) {
                probs.add(x / sum);
            }
        }
    }

    @Override
    public String id() {
        return id;
    }

    /** EV of adhering at s_p (the last candidate) and of undercutting one increment (the first). */
    public double evAdhere() { return evs.get(evs.size() - 1); }

    public double evUndercut() { return evs.get(0); }

    /** The quote grid and the choice distribution, for inspection. */
    public List<Double> quoteGrid() {
        return List.copyOf(quotes);
    }

    public List<Double> choiceProbabilities() {
        return List.copyOf(probs);
    }

    @Override
    public Decision decide(Observation obs) {
        double acc = 0.0;
        double pick = quotes.get(quotes.size() - 1);
        for (int i = 0; i < probs.size(); i++) {
            acc += probs.get(i);
            if (obs.choiceDraw() < acc) {
                pick = quotes.get(i);
                break;
            }
        }
        return new Decision(Action.Quote.of(pick), false, false, "LOGIT", false, List.of(),
                java.util.Map.of("evAdhere", evAdhere(), "evUndercut", evUndercut()));
    }
}
