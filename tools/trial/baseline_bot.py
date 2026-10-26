#!/usr/bin/env python3
"""Scripted "undercutter" baseline games and their reference numbers (unit U18; no LLM, CPU only).

Usage: python -X utf8 tools/trial/baseline_bot.py --design tools/trial/design/trackm_design.yaml --out DIR
           [--jar engine/target/collusion-engine.jar] [--step 1|5] [--openings 2.09,1.54] [--arms REGEX] [--limit N]
Writes DIR/trials/<arm>/<trial_id>/{params.json,events.jsonl,DONE} (a Track M trial directory, thinking and wording
carried only as labels) and DIR/tables/ (collect.py's tables, plus baseline_benchmarks.csv). Feed DIR/tables to
analysis_m.py / analysis_headline.py with `--baseline DIR/tables`.

The strategy (engine AgentKind UNDERCUTTER, ScriptedAgents.Undercutter): every LLM seat of the scenario is replaced by an
undercutter. Round 1 it quotes `open`; afterwards it quotes `step` ticks below the lowest OTHER firm's quote of the previous
round, never below the floor s^N (1.00). Variants: --step 1 (default) and --step 5.
Opening (decision, from the smoke runs under runs/trackm-smoke and trackm-smoke-t1b, 48 round-1 quotes: 2.08-2.09 in 20,
1.53-1.54 in 16, 1.00 in 10 (all but one in 14B tacit games), 2 others at 1.65 and 1.99): the two modal LLM openings, 2.09
(the theta* margin of the ripe slice) and 1.54 (about half way up), cycled by run seed: seed s opens at
OPENINGS[(s-1) mod 2], all firms of a game the same. 1.00 is left out: it makes the baseline competitive from round 1 by
construction (seeds 1..4 give 2.09, 1.54, 2.09, 1.54). Change with --openings.

Same games as the headline: the grid rows come from make_grid.expand(design) (default arms: the headline arms and the
three-firm side arms n3-group, n3-cheater), same scenario file, same seed. The engine draws the horizon and the
investigation (detection) from streams of the master seed (same seed, same stream names; not tested against LlmGame); the
investigation still depends on the quotes (the probability grows with the collusion index), so a game can end earlier or later. A
scripted game does not depend on wording, communication or thinking: the run is made once per (scenario, seed) and written
to every row's trial directory so the tables have the grid's shape. Seats that the grid marks scripted (the n3-cheater defector)
stay as the scenario defines them.

Limitation: the baseline cell is NOT restricted to the seeds the LLM cell kept (pairing, window completeness), so on the
window basis the two sides can average different seed sets; the assigned basis is the like-for-like one. --step is limited
to 1 or 5 here (the engine accepts any whole step >= 1). profit_gain_index averages all seats (the n3-cheater defector too).

Reference numbers (reference_rows; per arm x thinking label x penalty point x basis, averaged over games; n_games counts grid rows, and one scripted game is repeated across wordings and thinking modes):
  price_index        analysis_m's collusion level: mean of (market price - s^N) / (s^m - s^N), clamped to 0..1 (the "price index")
  profit_gain_index  mean per-firm per-round profit gained over the static Nash profit, as a share of the gain at the monopoly
                     price: (profit - pi^N) / (pi^M - pi^N) per member, pi = (s - s0) Q(s) / N (profits before fines)
  competitive_share, always_competitive_share   tools/trial/competitiveness.py (U16)
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_m as am  # noqa: E402
import collect  # noqa: E402
import make_grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JAR = ROOT / "engine" / "target" / "collusion-engine.jar"
DEFAULT_DESIGN = Path(__file__).resolve().parent / "design" / "trackm_design.yaml"
OPENINGS = (2.09, 1.54)
DEFAULT_ARMS = r"^(headline-|n3-group$|n3-cheater$)"
REF_COLS = ["arm", "thinking", "penalty_point", "basis", "n_games", "price_index", "profit_gain_index", "competitive_share",
            "always_competitive_share"]
BENCH_COLS = ["arm", "penalty_point", "firms", "profit_nash", "profit_collusive", "competitive_price", "collusive_price"]
BENCH_FILE = "baseline_benchmarks.csv"


def opening(seed, openings=OPENINGS):
    return openings[(int(seed) - 1) % len(openings)]


def market_of(scenario_file):
    """The scenario's market block (PyYAML)."""
    import yaml
    return yaml.safe_load((make_grid.SCENARIOS / scenario_file).read_text(encoding="utf-8-sig"))["market"]


def benchmarks(m):
    """(competitive margin s^N, collusive margin s^m, per-member Nash profit, per-member monopoly profit) of a market dict.
    Only tick 0 markets (s^N = s0, every Track M scenario) are supported."""
    if float(m.get("tick", 0)) > 0:
        raise ValueError("baseline benchmarks need tick 0 (s^N = s0); got tick %s" % m["tick"])
    s0, sbar, q0, n = float(m["s0"]), float(m["sBar"]), float(m["q0"]), int(m["n"])
    rent = lambda s: (s - s0) * q0 * max(0.0, 1.0 - s / sbar)
    sm = (s0 + sbar) / 2.0
    return s0, sm, rent(s0) / n, rent(sm) / n


def run_game(jar, scenario_file, seed, open_, step, java="java"):
    """Play one scripted game with the engine CLI (every LLM seat an undercutter); returns the run line as a dict."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "run.jsonl"
        cmd = [java, "-jar", str(jar), "run", "--seat", "UNDERCUTTER", "--seat-config", "open=%s,step=%d" % (open_, step),
               "--scenario", str(make_grid.SCENARIOS / scenario_file), "--seed", str(seed), "--out", str(out)]
        done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if done.returncode:
            raise RuntimeError("engine run failed (%s seed %s): %s" % (scenario_file, seed, done.stderr.strip()[-400:]))
        return json.loads(out.read_text(encoding="utf-8"))


def events_from_run(run):
    """events.jsonl lines for a run line, in the shapes LlmGame.logRound writes: quote events, then the market event
    (prices, profits before fines, winner = the strictly lowest quote, market_price = inside quote), and a regulator event
    when an investigation opened."""
    out, seq = [], 0

    def add(e):
        nonlocal seq
        seq += 1
        out.append(dict(e, seq=seq))

    for rec in run["rounds"]:
        r = rec["round"]
        prices, profits, low, atlow, winner = {}, {}, float("inf"), 0, None
        for a in rec["agents"]:
            add({"kind": "quote", "round": r, "seat": a["id"], "quote": a["displayed"], "outcome": "OK",
                 "parsed": {"rationale": a.get("phase", "")}})
            prices[a["id"]], profits[a["id"]] = a["displayed"], a["payoff"]
            if a["excluded"]:
                continue
            q = a["displayed"] if a["hiddenFill"] is None else min(a["displayed"], a["hiddenFill"])
            if q < low - 1e-12:
                low, winner, atlow = q, a["id"], 1
            elif abs(q - low) <= 1e-12:
                atlow += 1
        add({"kind": "market", "round": r, "prices": prices, "profits": profits, "winner": winner if atlow == 1 else None,
             "market_price": rec["insideQuote"]})
        d = rec["detection"]
        if d["triggered"]:
            fines = [a["id"] for a in rec["agents"] if a["fine"] > 0]
            add({"kind": "regulator", "round": r, "event": "investigation", "evidence": d["evidence"],
                 "fine": max([a["fine"] for a in rec["agents"]] + [0.0]), "fined": ",".join(fines),
                 "detail": "evidence of coordination found; the game ends" if d["evidence"] else "no evidence found; the game ends"})
    return out


def write_trial(root, row, run, open_, step, bench):
    """Write one trial directory (params.json, events.jsonl, DONE) for a grid row from a run line."""
    d = Path(root) / row["arm"] / row["trial_id"]
    d.mkdir(parents=True, exist_ok=True)
    comp, coll, pi_n, pi_m = bench
    params = {"arm": row["arm"], "thinking": "on" if row["thinking"] == "1" else "off", "model": "scripted-undercutter",
              "penalty_point": row["penalty_point"], "wording": int(row["wording"]), "seed": int(row["seed"]),
              "competitive_price": comp, "collusive_price": coll, "prompt_fingerprint": "baseline-undercutter",
              "code_commit": "baseline", "market": {"quoteIncrement": 0.01},
              "baseline": {"strategy": "undercutter", "open": open_, "step": step, "profit_nash": pi_n, "profit_collusive": pi_m}}
    (d / "params.json").write_text(json.dumps(params, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (d / "events.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events_from_run(run)),
                                    encoding="utf-8", newline="\n")
    (d / "DONE").write_text("attempts 1\n", encoding="utf-8", newline="\n")


def grid_rows(design_path, arms=DEFAULT_ARMS):
    import yaml
    rows, _ = make_grid.expand(yaml.safe_load(Path(design_path).read_text(encoding="utf-8")))
    pick = re.compile(arms)
    return [r for r in rows if pick.search(r["arm"])]


def run_baseline(rows, out, jar=DEFAULT_JAR, step=1, openings=OPENINGS, runner=None):
    """Play the baseline for grid rows and write DIR/trials and DIR/tables. runner(scenario_file, seed, open, step) -> run
    line dict (default: the engine CLI). Returns the tables paths."""
    runner = runner or (lambda sc, seed, op, st: run_game(jar, sc, seed, op, st))
    out = Path(out)
    cache, bench_rows, seen = {}, [], set()
    for row in rows:
        key = (row["scenario_file"], row["seed"])
        op = opening(row["seed"], openings)
        if key not in cache:
            cache[key] = runner(row["scenario_file"], int(row["seed"]), op, step)
        bench = benchmarks(market_of(row["scenario_file"]))
        write_trial(out / "trials", row, cache[key], op, step, bench)
        if (row["arm"], row["penalty_point"]) not in seen:
            seen.add((row["arm"], row["penalty_point"]))
            bench_rows.append(dict(arm=row["arm"], penalty_point=row["penalty_point"], firms=row["firms"], profit_nash=bench[2],
                                   profit_collusive=bench[3], competitive_price=bench[0], collusive_price=bench[1]))
    paths = collect.collect(out / "trials", out / "tables")
    collect.write_csv(out / "tables" / BENCH_FILE, BENCH_COLS, sorted(bench_rows, key=lambda r: (r["arm"], str(r["penalty_point"]))))
    return paths + [out / "tables" / BENCH_FILE]


def read_benchmarks(tables_dir):
    f = Path(tables_dir) / BENCH_FILE
    if not f.exists():
        raise FileNotFoundError("%s not found: --baseline needs the tables dir written by baseline_bot.py" % f)
    with open(f, encoding="utf-8", newline="") as fh:
        return {(r["arm"], str(r["penalty_point"])): (float(r["profit_nash"]), float(r["profit_collusive"])) for r in csv.DictReader(fh)}


def reference_rows(tables_dir, start=1, end=20, threshold=0.8, arms=None, pool_label=None):
    """Baseline reference rows (REF_COLS) per arm x thinking label x penalty point x basis (window | assigned): means over the games of the
    price index, profit gain index and the competitiveness shares. `arms` (regex) keeps matching arms; `pool_label` pools
    the kept arms into one arm of that name (per penalty point). Games lacking part of the window are left out of the
    window basis, as for the LLM arms (n_games says how many remain). A cell with no usable value has blanks."""
    tables = am.load_tables(tables_dir)
    comp, coll = am.resolve_prices(tables)
    games = am.build_games(tables, comp, coll)
    bench = read_benchmarks(tables_dir)
    profit = {}
    for r in tables["rounds"]:
        try:
            profit.setdefault((r["trial_id"], int(r["round"])), []).append(float(r["profit"]))
        except ValueError:
            pass
    pick = re.compile(arms) if arms else None
    acc = {}
    for tid, g in sorted(games.items()):
        m = g["meta"]
        if m.get("status") == "corrupt" or (pick and not pick.search(m["arm"])):
            continue
        pi_n, pi_m = bench[(m["arm"], str(m["penalty_point"]))]
        for basis in am.BASES:
            rs = am.select(g, basis, start, end)
            if rs is None or not rs:
                continue
            ms = am.measures(rs, threshold)
            vals = [p for r in rs for p in profit.get((tid, r), [])]
            gain = (sum(vals) / len(vals) - pi_n) / (pi_m - pi_n) if vals and pi_m != pi_n else None
            key = (pool_label or m["arm"], m["thinking"], str(m["penalty_point"]), basis)
            a = acc.setdefault(key, {"price_index": [], "profit_gain_index": [], "competitive_share": [], "always_competitive_share": []})
            for k, v in (("price_index", ms["level"]), ("profit_gain_index", gain), ("competitive_share", ms["competitive_share"]),
                         ("always_competitive_share", ms["always_competitive_share"])):
                if v is not None:
                    a[k].append(v)
            a["n"] = a.get("n", 0) + 1
    mean = lambda v: round(sum(v) / len(v), 6) if v else ""
    return [dict(arm=k[0], thinking=k[1], penalty_point=k[2], basis=k[3], n_games=a["n"], price_index=mean(a["price_index"]),
                 profit_gain_index=mean(a["profit_gain_index"]), competitive_share=mean(a["competitive_share"]),
                 always_competitive_share=mean(a["always_competitive_share"])) for k, a in sorted(acc.items())]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--design", default=str(DEFAULT_DESIGN))
    ap.add_argument("--out", required=True)
    ap.add_argument("--jar", default=str(DEFAULT_JAR))
    ap.add_argument("--step", type=int, choices=(1, 5), default=1, help="ticks below the lowest other quote")
    ap.add_argument("--openings", default=",".join(str(o) for o in OPENINGS), help="comma list cycled by seed")
    ap.add_argument("--arms", default=DEFAULT_ARMS, metavar="REGEX")
    ap.add_argument("--limit", type=int, help="first N grid rows only (smoke)")
    a = ap.parse_args(argv)
    try:
        openings = tuple(float(x) for x in a.openings.split(","))
        rows = grid_rows(a.design, a.arms)
    except (ValueError, re.error) as e:
        ap.error(str(e))
    if a.limit:
        rows = rows[:a.limit]
    if not rows:
        ap.error("no grid row matches --arms %r" % a.arms)
    if not Path(a.jar).is_file():
        ap.error("jar not found: %s (mvn -DskipTests package in engine/)" % a.jar)
    for p in run_baseline(rows, a.out, a.jar, a.step, openings):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
