package io.github.tomloscalzo.collusion.core.model;

public record EnforcementParams(ScreenShape screen, double rhoTip, boolean tipDuringPunishment,
                                double rhoCoop, double fine, double piPost) {
    public EnforcementParams withScreen(ScreenShape v) { return new EnforcementParams(v, rhoTip, tipDuringPunishment, rhoCoop, fine, piPost); }
    public EnforcementParams withRhoTip(double v) { return new EnforcementParams(screen, v, tipDuringPunishment, rhoCoop, fine, piPost); }
    public EnforcementParams withRhoCoop(double v) { return new EnforcementParams(screen, rhoTip, tipDuringPunishment, v, fine, piPost); }
    public EnforcementParams withFine(double v) { return new EnforcementParams(screen, rhoTip, tipDuringPunishment, rhoCoop, v, piPost); }
}
