"""Python re-implementation of the Layer A cartel solver (MODEL_SPEC eqs 4-13) for the tick-free LLM scenarios.

Tick-free core (tick 0, price matching): s^N = s0, pi^N = 0, pi_post = 0, grim price war at s0 (pi_p = 0),
q = 1, k = infinity, rho_tip = 0, dBarU = 0, so P(evidence | trigger) = rhoCoop.
"""
import numpy as np


def solve(N=2, phi=0.3, s0=1.0, sbar=5.0, q0=100.0, slope=0.025, p_ev=1.0, fine=500.0, delta=0.95,
          rho_tip=0.0, grid=200001):
    sm = (s0 + sbar) / 2.0
    th = np.linspace(0.0, 1.0, grid)
    s = s0 + th * (sm - s0)
    Q = q0 * np.maximum(0.0, 1.0 - s / sbar)
    pic = (s - s0) * Q / N
    rho_screen = np.minimum(1.0, slope * (s - s0))
    rhoT = 1.0 - (1.0 - rho_screen) * (1.0 - rho_tip)
    rhoT[0] = 0.0
    rhoE = rhoT * p_ev
    # W(theta), eq. (11), with Z = Z_post = 0
    W = (pic - rhoE * fine) / (1.0 - delta * (1.0 - rhoT))
    W[0] = 0.0
    # IC' (8'): D <= Psi(delta(1-rhoT)) L ; tick 0: D = (s-s0)Q(1-phi)(1-1/N), L = pic
    dt = delta * (1.0 - rhoT)
    psi = dt / (1.0 - dt)
    ic = (1 - phi) * (N - 1) <= psi + 1e-12
    Wc = np.where(ic, W, -np.inf)
    i = int(np.argmax(Wc))
    theta_star = th[i] if Wc[i] > 1e-12 else 0.0
    s_star = s0 + theta_star * (sm - s0)
    pim = (sm - s0) * q0 * (1 - sm / sbar) / N
    fine_ratio = fine / pim
    composite = slope * p_ev * fine_ratio * (sbar / s0 - 1.0)
    # IC-feasible maximum theta-hat
    theta_hat = th[ic].max() if ic.any() else 0.0
    # textbook patience threshold and the phi-adjusted one (eq. 9 with Psi = delta/(1-delta))
    d_text = 1 - 1.0 / N
    a = (1 - phi) * (N - 1)
    d_phi = a / (1 + a)
    return dict(theta_star=theta_star, s_star=s_star, fine_ratio=fine_ratio, composite=composite,
                pi_m=pim, theta_hat=theta_hat, delta_textbook=d_text, delta_phi=d_phi,
                W_star=float(Wc[i]) if Wc[i] > -np.inf else 0.0,
                fine_threshold=4.0 * pim / (slope * p_ev * (sbar / s0 - 1.0)),
                tip_composite=rho_tip * p_ev * fine_ratio)


if __name__ == "__main__":
    import aff  # noqa: F401
    ann = {(2, 100): .7029, (2, 300): .6262, (2, 500): .5459, (2, 1000): .3249, (2, 2000): 0.0, (3, 500): .4395}
    for (N, F), a in ann.items():
        r = solve(N=N, fine=F)
        print(N, F, "theta*=%.4f (annot %.4f) s*=%.3f FR=%.2f composite=%.3f fineThr=%.0f" % (
            r["theta_star"], a, r["s_star"], r["fine_ratio"], r["composite"], r["fine_threshold"]))
