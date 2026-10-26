# Hand recomputation of spec eq (4),(5),(10),(11) for N=2, phi=0, tick=0.25, s0=1, sBar=3, Q0=100, pEv=0.3
s0, sBar, Q0, N, phi, tick, pEv = 1.0, 3.0, 100.0, 2, 0.0, 0.25, 0.3
Q = lambda s: Q0 * max(0.0, 1 - s / sBar)
sN = s0 + 1 * tick           # j* = 1: j=2 fails since 1*Q(1.25)=58.3 > 2*Q(1.5)/2=50
sM = (s0 + sBar) / 2
piN = (sN - s0) * Q(sN) / N
piC1 = (sM - s0) * Q(sM) / N
print("sN", sN, "piN", piN, "piC(1)", piC1)

def W(theta, delta, slope, tip, F, piPost):
    Z, Zp = piN / (1 - delta), piPost / (1 - delta)
    if theta == 0: return Z
    s = sN + theta * (sM - sN)
    pc = (s - s0) * Q(s) / N
    rT = 1 - (1 - min(1, slope * (s - sN))) * (1 - tip)
    rE = rT * pEv
    return (pc - rE * F + delta * (rE * Z + (rT - rE) * Zp)) / (1 - delta * (1 - rT))

cases = [("cells 162/7938", 0.025, 0.01, 0.0), ("cells 150/7926", 0.025, 0.0, 125 * piC1)]
for name, slope, tip, F in cases:
    print("==", name, "slope", slope, "tip", tip, "F", F)
    for delta in (0.8, 0.99):
        for piPost, lab in ((0.0, "piPost=0 (grid)"), (piN, "piPost=piN (cf)")):
            ws = {j: W(j / 3, delta, slope, tip, F, piPost) for j in range(4)}
            best = max(ws, key=ws.get)
            print(f"  delta={delta} {lab}: " + ", ".join(f"W({j}/3)={w:.3f}" for j, w in ws.items()) + f"  -> theta*={best}/3")
