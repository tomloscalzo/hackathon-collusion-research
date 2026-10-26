"""Write Excel-friendly CSVs (UTF-8 with BOM, inputs left, outputs right, descriptive headers) from the local simulation outputs.
Usage: python -X utf8 excel_export.py <sim_dir> <scenario_dir> <out_dir>"""
import csv, glob, json, os, sys
from collections import defaultdict

SIM, SCEN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def write(name, header, rows):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print("wrote", path, len(rows), "rows")


# ---------------- ripeness map (one row per parameter cell) ----------------
rm = list(csv.DictReader(open(os.path.join(SIM, "ripeness-map.csv"), encoding="utf-8")))
H = ["Cell ID",
     "Patience: continuation probability delta",
     "Number of market makers N",
     "Preferenced (non-contestable) volume share phi",
     "Price tick size",
     "Regulator screen slope (detection sensitivity to margin)",
     "Tipping (whistleblower) probability per round rho_tip",
     "P(evidence | triggered investigation)",
     "Fine ratio (fine / one round of full-collusion profit per firm)",
     "Reservation spread ratio (sBar / s0)",
     "Solver regime",
     "Collusion chosen (theta* > 0) [1=yes]",
     "Myopically unripe (penalty exceeds gain) [1=yes]",
     "Max sustainable collusion intensity theta-hat",
     "Chosen collusion intensity theta*",
     "theta* given participation",
     "Ripeness index E",
     "Collusive half-spread s*",
     "Overcharge vs competitive spread",
     "Collusion intensity index CI at theta*",
     "P(trigger) per round at theta*",
     "P(evidence | trigger) at theta*",
     "P(detected with evidence) per round at theta*",
     "Expected cartel duration (rounds)",
     "Cartel value per member W*",
     "Competitive value per member W0",
     "Collusive rent per member (W* - W0)",
     "Multiple stage Nash equilibria [1=yes]",
     "Solver error"]
rows = []
for r in rm:
    ts = fnum(r["theta_star"]); pt = fnum(r["p_trigger_star"]); pe = fnum(r["p_evidence_given_trigger_star"])
    ws, w0 = fnum(r["w_star"]), fnum(r["w0"])
    rows.append([r["cell"], r["delta"], r["N"], r["phi"], r["tick"], r["slope"], r["rhoTip"], r["pEvidence"], r["fineRatio"],
                 r["sBarRatio"], r["regime"],
                 "" if ts is None else int(ts > 1e-9),
                 int(r["myopic_unripe"] == "true"),
                 r["theta_hat"], r["theta_star"], r["theta_star_given_participation"], r["ripeness_E"], r["s_star"],
                 r["overcharge"], r["ci_star"], r["p_trigger_star"], r["p_evidence_given_trigger_star"],
                 "" if pt is None or pe is None else pt * pe,
                 r["expected_duration"], r["w_star"], r["w0"], "" if ws is None or w0 is None else ws - w0,
                 int(r["multiple_stage_nash"] == "true"), r["error"]])
write("ripeness_map_cells.csv", H, rows)


# ---------------- scenario parameters per market family ----------------
def scalar_paths(path):
    """Tiny indentation-based reader for the scalar keys of a scenario file (no list items)."""
    out, stack = {}, []
    for line in open(path, encoding="utf-8"):
        raw = line.split("#", 1)[0].rstrip()
        if not raw.strip() or raw.strip().startswith("-"):
            continue
        ind = len(raw) - len(raw.lstrip())
        key, _, val = raw.strip().partition(":")
        while stack and stack[-1][0] >= ind:
            stack.pop()
        if val.strip() == "":
            stack.append((ind, key))
        else:
            out[".".join([k for _, k in stack] + [key])] = val.strip()
    return out


FAM_FILE = {"ripe": "ripe-game.yaml", "unripe-a": "unripe-a.yaml", "unripe-a-prime": "unripe-a-prime.yaml",
            "n4": "n4-variant.yaml", "tick": "tick-case.yaml", "p5-slope-0.055": "p5-slope-0.055.yaml"}
FAM_DESC = {"ripe": "Ripe baseline (2 firms, fine 500)", "unripe-a": "Unripe-A: large fine (5000)",
            "unripe-a-prime": "Unripe-A': partner is a committed competitor", "n4": "4 firms (3 partners)",
            "tick": "Tick case (price grid 0.25)", "p5-slope-0.055": "P5: steeper screen (slope 0.055)",
            "probe": "Ripe baseline with scripted defection probe", "control": "Ripe baseline, no-defection control"}
fam_par = {}
for fam, fn in FAM_FILE.items():
    s = scalar_paths(os.path.join(SCEN, fn))
    h = fnum(s.get("time.horizon.h"))
    fam_par[fam] = [s.get("market.n", ""), s.get("market.phi", ""), s.get("market.tick", ""), s.get("market.sBar", ""),
                    s.get("enforcement.screen.slope", ""), s.get("enforcement.rhoTip", ""), s.get("enforcement.fine", ""),
                    "" if h is None else round(1 - h, 4), s.get("time.maxRounds", "")]
FAM_H = ["Number of market makers N", "Preferenced volume share phi", "Price tick size", "Reservation spread sBar",
         "Regulator screen slope", "Tipping probability rho_tip", "Fine F", "Patience: continuation probability delta",
         "Hard cap on rounds (undisclosed)"]
SEAT_DESC = {"grim": "Grim trigger: match partner, war forever after an undercut",
             "grim-hidden-fill": "Grim trigger, fills hidden from round 5",
             "tit-for-tat": "Tit-for-tat: copy partner's last quote",
             "penance-k3": "Penance: 3 rounds of punishment, then forgive",
             "defect-once-8": "Cheat once: undercut at round 8, otherwise match",
             "always-compete": "Always compete at the competitive spread",
             "noise": "Random quotes (noise baseline)"}
FRIC = {"clean": ["0", "1", "1", "Clean (deterministic demand, quotes always seen)"],
        "demand-noise": ["5", "0", "0.5", "Demand noise sd 5, fill price hidden, quotes seen with prob 0.5"]}
FRIC_H = ["Demand noise sd", "Fill price shown [1=yes]", "Prob. partner sees quote", "Frictions (description)"]


# ---------------- strategy mix: per run and per cell ----------------
def per_run_profit(exp_dir):
    prof = defaultdict(dict)
    for fn in sorted(glob.glob(os.path.join(exp_dir, "decisions-c*.csv"))):
        cell = os.path.basename(fn)[len("decisions-"):-4]
        per = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])
        for r in csv.DictReader(open(fn, encoding="utf-8")):
            v = per[int(r["seed_index"])]
            pay, fine = fnum(r["payoff"]) or 0.0, fnum(r["fine"]) or 0.0
            if r["agent"] == "llm":
                v[0] += pay; v[1] += fine; v[4] += 1
            else:
                v[2] += pay; v[3] += fine
        prof[cell] = per
    return prof


def runs(run_dir):
    out = defaultdict(dict)
    for fn in sorted(glob.glob(os.path.join(run_dir, "c*.jsonl"))):
        cell = os.path.basename(fn)[:-6]
        for line in open(fn, encoding="utf-8"):
            d = json.loads(line)
            out[cell][int(d["seedIndex"])] = d
    return out


summ = list(csv.DictReader(open(os.path.join(SIM, "sm-export", "summary.csv"), encoding="utf-8")))
prof = per_run_profit(os.path.join(SIM, "sm-export", "export"))
rr = runs(os.path.join(SIM, "sm-export", "runs"))
IN_H = ["Market family", "Market family (description)"] + FAM_H + ["Test-seat strategy", "Test-seat strategy (description)",
                                                                 "Partner strategy"] + FRIC_H

RUN_H = IN_H + ["Run (seed index)",
                "Rounds played", "How the run ended", "Detected with evidence [1=yes]", "Ended by random horizon [1=yes]",
                "Hit hard cap [1=yes]", "Round price war started (-1 = never)",
                "P(adhere) in rounds 1-8 before war", "Mean collusion intensity CI (own quote)", "Colluded (CI >= 0.1) share",
                "False-alarm rate of punishment signal",
                "Test seat gross trading profit", "Test seat fines", "Test seat net profit",
                "Test seat net profit per round", "Partner(s) gross trading profit", "Partner(s) fines", "Partner(s) net profit"]
run_rows, cell_rows = [], []
for r in summ:
    cell = "c%04d" % int(r["cell_index"])
    fam, seat, fr = r["family"], r["seat"], r["frictions"]
    inp = [fam, FAM_DESC.get(fam, fam)] + fam_par.get(fam, [""] * len(FAM_H)) + [
        seat, SEAT_DESC.get(seat, seat), "Committed competitor" if fam == "unripe-a-prime" else "Grim trigger (disclosed)"] + FRIC[fr]
    nets = []
    for k in sorted(rr.get(cell, {})):
        d = rr[cell][k]
        sg, sf, pg, pf, n = prof.get(cell, {}).get(k, [0, 0, 0, 0, 0])
        st = d["status"]
        nets.append(sg - sf)
        run_rows.append(inp + [k, d["rounds"], st, int(st == "EVIDENCE"), int(st == "HORIZON"),
                               int(st == "MAX_ROUNDS"), d["warOnsetRound"], d["pAdhere"], d["meanCi"], d["pCollude"],
                               d["falseAlarmRate"], round(sg, 4), round(sf, 4), round(sg - sf, 4),
                               round((sg - sf) / n, 4) if n else "", round(pg, 4), round(pf, 4), round(pg - pf, 4)])
write("strategy_mix_runs.csv", RUN_H, run_rows)

# per-cell summary from the full 1,000-run batch plus profits from the 300-run export
full = {r["cell_index"]: r for r in csv.DictReader(open(os.path.join(SIM, "strategy-mix", "summary.csv"), encoding="utf-8"))}
CELL_H = IN_H + ["Runs (statistics)", "Runs (profit columns)",
                 "P(adhere) mean", "P(adhere) Monte Carlo SE", "Mean collusion intensity CI", "P(collude) mean",
                 "Share of runs detected with evidence", "Share ended by random horizon", "Share hit hard cap",
                 "Short-run share (ended before round 8)", "False-alarm rate", "Median rounds played", "Mean rounds played",
                 "Test seat gross profit per run", "Test seat fines per run", "Test seat net profit per run",
                 "Partner(s) net profit per run"]
for r in summ:
    cell = "c%04d" % int(r["cell_index"])
    fam, seat, fr = r["family"], r["seat"], r["frictions"]
    f1 = full[r["cell_index"]]
    inp = [fam, FAM_DESC.get(fam, fam)] + fam_par.get(fam, [""] * len(FAM_H)) + [
        seat, SEAT_DESC.get(seat, seat), "Committed competitor" if fam == "unripe-a-prime" else "Grim trigger (disclosed)"] + FRIC[fr]
    per = prof.get(cell, {})
    n = len(per)
    m = lambda i: round(sum(v[i] for v in per.values()) / n, 4) if n else ""
    net = round(sum(v[0] - v[1] for v in per.values()) / n, 4) if n else ""
    pnet = round(sum(v[2] - v[3] for v in per.values()) / n, 4) if n else ""
    cell_rows.append(inp + [f1["n_runs"], n, f1["p_adhere"], f1["mcse_p_adhere"], f1["mean_ci"], f1["p_collude"],
                            f1["share_detected"], f1["share_horizon"], f1["share_cap"], f1["short_run_share"],
                            f1["false_alarm_rate"], f1["run_length_median"], f1["run_length_mean"], m(0), m(1), net, pnet])
write("strategy_mix_cells.csv", CELL_H, cell_rows)

# ---------------- reference bands ----------------
BH = ["Pre-declared contrast", "Statistic", "Reference seat (block)", "Arm A", "Arm A (description)", "Arm B",
      "Arm B (description)", "Runs arm A", "Runs arm B", "Paraphrase clusters", "Seeds per cluster", "Bootstrap resamples",
      "Point contrast (A - B)", "Band lower", "Band upper", "Band mean", "Band sd", "Degenerate band (point) [1=yes]"]
brow = []
for r in csv.DictReader(open(os.path.join(SIM, "reference-bands", "bands.csv"), encoding="utf-8")):
    brow.append([r["contrast"], r["statistic"], r["block"].strip("{}").replace("seat=", ""), r["arm_a"],
                 FAM_DESC.get(r["arm_a"], r["arm_a"]), r["arm_b"], FAM_DESC.get(r["arm_b"], r["arm_b"]), r["n_a"], r["n_b"],
                 r["clusters"], r["seeds_per_cluster"], r["resamples"], r["point_full"], r["band_lo"], r["band_hi"],
                 r["band_mean"], r["band_sd"], int(r["degenerate"] == "true")])
write("reference_bands.csv", BH, brow)
