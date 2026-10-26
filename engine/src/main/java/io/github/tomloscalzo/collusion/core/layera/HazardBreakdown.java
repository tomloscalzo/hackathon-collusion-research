package io.github.tomloscalzo.collusion.core.layera;

/** Eq. (10): rho_T = P(trigger) ends the rents; rho_E = P(trigger) P(evidence | trigger) also pays F. */
public record HazardBreakdown(double pTrigger, double pEvidenceGivenTrigger) {
    public static final HazardBreakdown ZERO = new HazardBreakdown(0.0, 0.0);

    public double rhoEnd() { return pTrigger; }

    public double rhoFine() { return pTrigger * pEvidenceGivenTrigger; }
}
