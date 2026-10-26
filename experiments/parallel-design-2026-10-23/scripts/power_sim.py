#!/usr/bin/env python3
"""Power simulation for the paired P(adhere) contrast (plans/PREDICTIONS.md, tools/analysis.py rules).
Standard library only.  All numbers it prints are SIMULATION under the assumptions below, not data.

Assumptions (stated so the owner can disagree with them):
  * Per-run statistic is near-binary: a run adheres for all counted rounds (P(adhere) = 1) or deviates in round 1
    (P(adhere) = 0).  Bernoulli is the maximum-variance case for a statistic on [0, 1], so this is conservative for
    a graded statistic with the same mean.
  * Paraphrase j has a shared level shift u_j ~ N(0, SD_LEVEL) (removed by pairing) and an effect heterogeneity
    v_j ~ N(0, sd_para) (NOT removed by pairing; this is what the cluster bootstrap sees).
    arm A adherence prob p_Aj = clip(P_BASE + u_j, 0, 1); arm B p_Bj = clip(P_BASE - effect + u_j + v_j, 0, 1).
  * CRN pairing: within a (paraphrase, seed) cell the two arms' latent draws are correlated RHO (shared horizon and
    demand streams; the LLM's own sampling noise is not shared).  RHO = 0.2 by default, 0 = no pairing benefit.
  * Estimator and interval exactly as the frozen script: cell contrast A - B, cluster = paraphrase mean, estimate =
    mean of clusters, paraphrase-cluster percentile bootstrap, one-sided lower bound = alpha percentile.
    Power = share of replicates whose lower bound exceeds 0 (band edge 0 for the deterministic seats).
  * Two alphas: 0.05 (unadjusted, exploratory) and 0.05/9 = 0.00556 (first Holm step: the hardest the family can be;
    a test that survives it survives any step).  Refusals are not simulated (they reduce n per cell; the 30-run floor
    applies after exclusion).
  * B = 500 bootstrap resamples per replicate (the frozen script uses 4000; the percentile at 10 clusters is coarse
    either way), REPS replicates per design cell.
"""
import random, statistics, sys, time
from statistics import NormalDist

ND = NormalDist()
P_BASE = 0.70       # ripe-arm adherence probability (assumed; unknown before data)
SD_LEVEL = 0.20     # paraphrase level shift, removed by pairing
RHO = 0.20          # CRN correlation of latent draws across arms within a cell
N_PARA = 10
B = 500
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 300
if len(sys.argv) > 2:
    P_BASE = float(sys.argv[2])          # sensitivity: ripe-arm adherence rate (review finding 12)
QUICK = len(sys.argv) > 3 and sys.argv[3] == "quick"   # quick mode: only the 40- and 80-run rows at effect 0.30
ALPHAS = [0.05, 0.05 / 9]
rng = random.Random(20261023)

def clip(x):
    return min(1.0, max(0.0, x))

def inv(p):
    if p <= 0.0: return -1e9
    if p >= 1.0: return 1e9
    return ND.inv_cdf(p)

def one_replicate(effect, sd_para, seeds, rho=RHO):
    clusters = []
    for j in range(N_PARA):
        u = rng.gauss(0, SD_LEVEL)
        v = rng.gauss(0, sd_para)
        pa = clip(P_BASE + u)
        pb = clip(P_BASE - effect + u + v)
        ta, tb = inv(pa), inv(pb)
        tot = 0.0
        for s in range(seeds):
            e = rng.gauss(0, 1)
            za = (rho ** 0.5) * e + ((1 - rho) ** 0.5) * rng.gauss(0, 1)
            zb = (rho ** 0.5) * e + ((1 - rho) ** 0.5) * rng.gauss(0, 1)
            ya = 1.0 if za < ta else 0.0
            yb = 1.0 if zb < tb else 0.0
            tot += ya - yb
        clusters.append(tot / seeds)
    est = sum(clusters) / N_PARA
    boots = []
    for _ in range(B):
        boots.append(sum(rng.choice(clusters) for _ in range(N_PARA)) / N_PARA)
    boots.sort()
    out = {}
    for a in ALPHAS:
        k = int(a * B)
        lower = boots[max(0, min(B - 1, k))]
        out[a] = lower > 0.0
    return est, out

def power(effect, sd_para, seeds, rho=RHO):
    hits = {a: 0 for a in ALPHAS}
    ests = []
    for _ in range(REPS):
        est, out = one_replicate(effect, sd_para, seeds, rho)
        ests.append(est)
        for a in ALPHAS:
            hits[a] += out[a]
    return {a: hits[a] / REPS for a in ALPHAS}, statistics.mean(ests)

def main():
    global N_PARA
    t0 = time.time()
    print(f"SIMULATION  P_BASE={P_BASE} SD_LEVEL={SD_LEVEL} RHO={RHO} B={B} REPS={REPS} paraphrases={N_PARA}")
    if QUICK:
        print("\nQuick sensitivity: effect 0.30, sd_para 0.2, seeds 4 and 8 (power@0.05, power@0.05/9)")
        for seeds in (4, 8):
            pw, me = power(0.30, 0.2, seeds)
            print(f"P_BASE={P_BASE} seeds={seeds} runs/arm={N_PARA*seeds}  power@0.05={pw[0.05]:.2f}  power@0.05/9={pw[0.05/9]:.2f}  mean_est={me:.2f}")
        print(f"\nelapsed {time.time()-t0:.0f}s")
        return
    print("\nTable 1: power (share of replicates with one-sided lower bound > 0)")
    print("seeds  runs/arm  effect  sd_para  power@0.05  power@0.05/9  mean_est")
    for sd_para in (0.1, 0.2):
        for effect in (0.15, 0.30, 0.50):
            for seeds in (2, 4, 8, 16):
                pw, me = power(effect, sd_para, seeds)
                print(f"{seeds:5d}  {N_PARA*seeds:8d}  {effect:6.2f}  {sd_para:7.2f}  {pw[0.05]:10.2f}  {pw[0.05/9]:12.2f}  {me:8.2f}")
    print("\nTable 2: false-positive rate at effect 0 (size check of the percentile cluster bootstrap)")
    for sd_para in (0.1, 0.2):
        for seeds in (4, 16):
            pw, me = power(0.0, sd_para, seeds)
            print(f"seeds={seeds:2d} sd_para={sd_para}  fp@0.05={pw[0.05]:.3f}  fp@0.05/9={pw[0.05/9]:.3f}")
    print("\nTable 3: minimum detectable effect at 10 x 4 = 40 runs/arm (finer effect grid)")
    print("effect  sd_para  power@0.05  power@0.05/9")
    for sd_para in (0.1, 0.2):
        for effect in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50):
            pw, _ = power(effect, sd_para, 4)
            print(f"{effect:6.2f}  {sd_para:7.2f}  {pw[0.05]:10.2f}  {pw[0.05/9]:12.2f}")
    print("\nTable 4: what CRN pairing buys (effect 0.30, sd_para 0.1, 4 seeds) at rho = 0, 0.2, 0.5")
    for rho in (0.0, 0.2, 0.5):
        pw, _ = power(0.30, 0.1, 4, rho)
        print(f"rho={rho}  power@0.05={pw[0.05]:.2f}  power@0.05/9={pw[0.05/9]:.2f}")
    print("\nTable 5: seeds vs paraphrases at 80 runs/arm (effect 0.30, sd_para 0.2): 10x8 vs 20x4 (20 paraphrases is NOT available; frozen at 12)")
    pw, _ = power(0.30, 0.2, 8); print(f"10 paraphrases x 8 seeds: power@0.05={pw[0.05]:.2f} @0.05/9={pw[0.05/9]:.2f}")
    N_PARA = 20
    pw, _ = power(0.30, 0.2, 4); print(f"20 paraphrases x 4 seeds: power@0.05={pw[0.05]:.2f} @0.05/9={pw[0.05/9]:.2f}")
    N_PARA = 12
    pw, _ = power(0.30, 0.2, 4); print(f"12 paraphrases x 4 seeds: power@0.05={pw[0.05]:.2f} @0.05/9={pw[0.05/9]:.2f}")
    N_PARA = 10
    print(f"\nelapsed {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
