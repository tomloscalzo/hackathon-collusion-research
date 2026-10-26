package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.core.layera.Enforcement;
import io.github.tomloscalzo.collusion.core.layera.HazardBreakdown;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.EnforcementParams;
import io.github.tomloscalzo.collusion.core.model.Scenario;

/**
 * External detection, trigger then evidence (spec 2.4). SCENARIO mode: rho_screen from the realised inside margin
 * (zero in a war at s0), rho_tip from the first round whose inside CI exceeds zero and, during a punishment phase, only
 * if tipDuringPunishment; P(evidence | trigger) from the scenario aggregates (dBarU) and rho_coop. Two uniforms are
 * consumed per round in every mode. A trigger ends the run; evidence additionally charges F.
 */
public final class DetectionProcess {
    private final Scenario s;
    private final DetectionSpec spec;
    private boolean tipLatched;

    public DetectionProcess(Scenario s, DetectionSpec spec) {
        this.s = s;
        this.spec = spec;
    }

    /** pTrigger / pEvidence are the probabilities used this round; triggered/evidence the outcomes. */
    public record Step(double pTrigger, double pEvidence, boolean tipActive, boolean triggered, boolean evidence) {}

    public Step step(double insideQuote, boolean punishing, double uTrigger, double uEvidence) {
        double pT;
        double pE;
        boolean tipOn = false;
        switch (spec.mode()) {
            case OFF -> {
                pT = 0.0;
                pE = 0.0;
            }
            case FIXED -> {
                pT = spec.pTrigger();
                pE = spec.pEvidence();
            }
            default -> {
                double ci = PayoffFunctions.collusionIndex(s.market(), insideQuote);
                if (ci > 1e-9) {
                    tipLatched = true;
                }
                tipOn = tipLatched && (s.enforcement().tipDuringPunishment() || !punishing);
                EnforcementParams e = s.enforcement();
                EnforcementParams eff = new EnforcementParams(e.screen(), tipOn ? e.rhoTip() : 0.0,
                        e.tipDuringPunishment(), e.rhoCoop(), e.fine(), e.piPost());
                HazardBreakdown h = Enforcement.hazard(eff, insideQuote - PayoffFunctions.nashMargin(s.market()), ci,
                        s.aggregates().dBarU());
                pT = h.pTrigger();
                pE = h.pEvidenceGivenTrigger();
            }
        }
        boolean trig = uTrigger < pT;
        boolean evid = trig && uEvidence < pE;
        return new Step(pT, pE, tipOn, trig, evid);
    }
}
