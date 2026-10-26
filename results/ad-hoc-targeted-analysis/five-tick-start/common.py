"""Shared helpers for the ad-hoc targeted analyses (self-contained copy per folder).
Data root = --data DIR containing steps/neutral/step1 and steps/anchored/step1 (analysis_final)."""
import zlib, numpy as np, pandas as pd

def step(data, run): return f"{data}/steps/{run}/step1"

def load_games(data, run="neutral"):
    """One row per done game: arm, thinking, point, wording, seed, price_index, comp_share (run.csv columns; these equal the levers.py
    definitions from the rounds table to within 0.001 and also cover the 53 games the rounds table lacks)."""
    s = step(data, run)
    r = pd.read_csv(f"{s}/run.csv", low_memory=False)
    r = r[r.status == "done"].copy()
    g = r[["trial_id","arm","thinking","penalty_point","wording","seed","rounds_played","price_index","competitive_share",
           "profit_gain_index","market_price_mean","matching_share","explicit_agreement_any","end_reason","time_to_high_price","cheater_seat","defect_round","punish_round_first","punish_lag","coalition_punished"]].rename(columns={"competitive_share":"comp_share"})
    return g

def load_rounds(data):
    rd = pd.read_csv(f"{step(data,'neutral')}/tables/rounds.csv", usecols=["trial_id","round","seat","quote","market_price","competitive_round","imputed"])
    return rd

def pairs(g, arm, pt, carm, cpt, mode, col):
    a = g[(g.arm==arm)&(g.penalty_point==pt)&(g.thinking==mode)].set_index(["wording","seed"])[col]
    c = g[(g.arm==carm)&(g.penalty_point==cpt)&(g.thinking==mode)].set_index(["wording","seed"])[col]
    j = pd.concat([a.rename("a"), c.rename("c")], axis=1, join="inner").dropna()
    return j

def boot(d, key, B=10000):
    d = np.asarray(d, float)
    if len(d) < 2: return (np.nan,)*3
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    m = d[rng.integers(0, len(d), size=(B, len(d)))].mean(axis=1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    return d.mean(), lo, hi

def contrast(g, arm, pt, carm, cpt, mode, col, key):
    j = pairs(g, arm, pt, carm, cpt, mode, col)
    d = (j.a - j.c).to_numpy(); m, lo, hi = boot(d, key)
    return dict(n_pairs=len(d), arm_mean=j.a.mean(), control_mean=j.c.mean(), diff=m, ci_lo=lo, ci_hi=hi)

def rowid_fix(g): return g

def md_table(df, fmt="{:.3f}"):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|"*len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(fmt.format(v) if isinstance(v, (float, np.floating)) and v == v else ("" if v != v else str(v)) for v in r) + " |")
    return "\n".join(out)

def ci_str(r): return f"{r['diff']:+.3f} [{r['ci_lo']:+.3f}, {r['ci_hi']:+.3f}]"

TERMS_BASE = [
 ("Half-spread, tick, floor", "Each round each firm quotes a half-spread in ticks of 0.01 between 1.00 and 3.00; the lower quote wins the business. 1.00 is the competitive floor (Nash level); 2.09 is the level theory says collusion can sustain at penalty point 3."),
 ("Price index", "(market price - 1) / (3 - 1), averaged over the game's rounds. 0 = always the floor, 1 = always the top. Lower = less collusion."),
 ("Competitive share", "Share of LLM firm-rounds (round 2 on) in which the firm undercuts the rival's last quote or both sit at 1.00. Higher = less collusion."),
 ("Rival / control", "A rival is another firm in the game. A matched control is the arm that differs only in the lever, paired on (wording, seed) within the thinking mode, at penalty point 3."),
 ("Pair, CI", "20 pairs per cell (5 wordings x 4 seeds). Effect = mean pair difference; 95% CI = percentile bootstrap of the pairs, 10,000 resamples."),
 ("Minimum detectable effect", "About 0.15-0.25 in price-index units; a CI that spans zero is a bound on the effect, not evidence of none."),
 ("Thinking off / on", "Whether the Qwen3 model's reasoning mode was switched on (run separately)."),
 ("Neutral / anchored", "Two prompt versions; neutral is primary, anchored (payoff examples anchored to the collusive level) is a check."),
]
def terms(extra=()):
    rows = list(TERMS_BASE) + list(extra)
    return "<small>\n\n**Terms**\n\n| Term | Meaning |\n|---|---|\n" + "\n".join(f"| {a} | {b} |" for a, b in rows) + "\n\n</small>\n"
