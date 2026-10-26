#!/usr/bin/env python3
"""Track M analysis, part 1 (C10.1): collusion and punishment measures (standard library only; scope sections 4.5, 14.3).

Usage: python -X utf8 tools/trial/analysis_m.py <tables_dir> <out_dir> [--competitive P] [--collusive P]
           [--window-start 1] [--window-end 20] [--threshold 0.8] [--boot 2000] [--seed 0] [--contrast A:B ...]
           [--pair-arms REGEX] [--no-pairing] [--baseline DIR]
Reads ONLY the tables written by collect.py (trials.csv, rounds.csv, and for refusal rounds messages.csv and
questions.csv when present). The competitive and collusive prices default to the trials.csv columns competitive_price / collusive_price (C9.3; one value across the trials), with --competitive/--collusive as overrides.
Writes (LF, sorted, so a re-run gives identical files):
  measures_by_game.csv   one row per game x basis x refusals: level, time_to_high, high_duration, undercuts,
                         punishments, war_length, rounds, refusal_rounds, imputed_rounds (rounds with an imputed call:
                         a truncated or unparseable quote, talk or in-game question reply, derive.call_failure)
  measures_summary.csv   one row per arm x thinking x penalty_point x basis x refusals: n_games, games_with_refusal,
                         games_with_imputed and imputed_round_share (imputed rounds / played rounds, pooled), games_assigned (the
                         cell's games as assigned) and window_share (window rows: n_games / games_assigned, the share
                         of games the window --window-start..--window-end keeps, after the pairing unless --no-pairing; blank on
                         assigned rows), means, bootstrap
                         CI of the level (by game, stratified by wording; gotcha 14) with ci_method: "stratified";
                         "game" when any wording has a single game (a stratified resample would never vary it and give
                         a too narrow, even zero-width, interval, so all the cell's games are resampled across
                         wordings; a warning is printed; note the switch is all-or-nothing per cell, and wordings of 2-4
                         games are still resampled within wording, slightly too narrow, quality review Q6); "none" with fewer than 2 games (bounds blank, not estimable); per-wording means
                         as JSON. A cell whose window keeps no game still has its window rows (n_games 0,
                         window_share 0, blank measures)
  (U16) measures_by_game.csv and measures_summary.csv also carry competitive_share and always_competitive_share
                         (per game: competitive firm-rounds / scored firm-rounds, and the share of firms competitive in
                         every scored round; the summary averages them over the games). Both are blank without the
                         competitive_round column of rounds.csv. --measure competitive_share contrasts them.
  (U18) --baseline DIR (the tables dir of tools/trial/baseline_bot.py, the scripted undercutter on the same scenarios and
                         seeds) writes baseline_reference.csv (arm x thinking x penalty_point x basis: n_games, price_index, profit_gain_index,
                         competitive_share, always_competitive_share of the baseline) and adds baseline_price_index,
                         baseline_profit_gain_index, baseline_competitive_share and level_minus_baseline to measures_summary.csv
                         (matched on arm, thinking, penalty_point and basis, NOT on seeds: on the window basis the baseline and LLM cells may average different seed sets, prefer assigned; blank where the baseline has no such cell). Without the
                         option the outputs are unchanged.
  exclusions.csv         every game left out of a basis and why (corrupt, incomplete_window, unpaired_seed)
  contrasts.csv          with --contrast A:B, arm A minus arm B on seeds paired within thinking, point and wording
                         (bootstrap and ci_method as in the summary)
                         (only the two arms compared are paired; the summary's pairing does not apply)
Bases (gotcha 13): `window` = rounds window_start..window_end only, games that lack part of the window dropped and, in
the summary, the headline arms (--pair-arms, a regular expression, default ^headline-: tacit, private chat, monitored
chat) kept only on the seeds present in every headline arm of the same thinking and point; other arms (smoke, controls,
side arms, Track R) are never paired with them (--no-pairing turns the pairing off); `assigned` = every game, every round it played. Refusals: `with` keeps refusal rounds,
`without` leaves out every played round in which any quote, talk or in-game question call was refused (derive.call_failure:
an imputed parse failure, refusal_kind UNPARSEABLE or TRUNCATED, is not a refusal and does not leave a round out; undercuts are
worked out on the full sequence first, so the round after a refusal is still judged; runs skip over a left-out round).
Refusing games are never dropped.
Measures: level = mean of (market_price - competitive)/(collusive - competitive) clamped to 0..1 over the rounds;
time_to_high = first round (counted from the window start, or the first round played) with level >= threshold (blank = never); high_duration = longest run of consecutive
rounds at or above the threshold; undercuts and punishments as derive.py (a chosen quote below every rival quote of the
previous round and below its own; a punishment when a rival undercut the round before); war_length = consecutive
rounds, from the first undercut, with level below the threshold (0 with no undercut).
"""
import argparse
import csv
import json
import math
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive  # noqa: E402  (call_failure: the one refusal definition)

BASES = ("window", "assigned")
REFUSALS = ("with", "without")
NOT_CHOSEN = ("REFUSED", "IMPUTED", "AFTER_REFUSAL")
HEADLINE_ARMS = r"^headline-"   # the headline comparison: headline-tacit, headline-chat, headline-monitored (design file)


def load_tables(d):
    """Read the collect.py tables from directory d; the optional ones are [] when absent."""
    out = {}
    for name in ("trials", "rounds", "messages", "questions", "refusals"):
        f = Path(d) / (name + ".csv")
        if not f.exists() and name in ("trials", "rounds"):
            raise FileNotFoundError("%s is required (written by tools/trial/collect.py)" % f)
        if f.exists():
            with open(f, encoding="utf-8", newline="") as fh:
                out[name] = list(csv.DictReader(fh))
        else:
            out[name] = []
    return out


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def resolve_prices(tables, competitive=None, collusive=None):
    """(competitive, collusive): the given override, else the single value in trials.csv competitive_price / collusive_price
    (corrupt trials ignored). Raises ValueError when a price is not given and the trials hold none or several."""
    out = []
    for given, col, flag in ((competitive, "competitive_price", "--competitive"), (collusive, "collusive_price", "--collusive")):
        if given is None:
            vals = {_f(t.get(col)) for t in tables["trials"] if t.get("status") != "corrupt" and _f(t.get(col)) is not None and math.isfinite(_f(t.get(col)))}
            if len(vals) != 1:
                raise ValueError("%s: trials.csv holds %s %s value(s); pass %s" % (col, len(vals) or "no", col, flag))
            given = vals.pop()
        out.append(given)
    return tuple(out)


def build_games(tables, competitive, collusive):
    """game id -> dict(meta, rounds={r: dict(level, quotes, chosen, refused)}); corrupt trials are left out."""
    span = collusive - competitive
    if not span:
        raise ValueError("collusive price equals competitive price")
    games = {}
    for t in tables["trials"]:
        games[t["trial_id"]] = dict(meta=t, rounds={})
    refused, imputed = failed_rounds(tables)
    for row in tables["rounds"]:
        g = games.get(row["trial_id"])
        if g is None:
            continue
        r = int(row["round"])
        rd = g["rounds"].setdefault(r, dict(level=None, quotes={}, chosen={}, refused=False, imputed=False, competitive={}))
        price, q = _f(row["market_price"]), _f(row["quote"])
        if price is not None:
            rd["level"] = min(1.0, max(0.0, (price - competitive) / span))
        if row.get("competitive_round") in ("0", "1"):   # U16: competitiveness.py via collect.py
            rd["competitive"][row["seat"]] = row["competitive_round"] == "1"
        if q is not None:
            rd["quotes"][row["seat"]] = q
            if not (row["imputed"] in ("1", "True") or row["refusal_kind"] or row["parse_status"] in NOT_CHOSEN):
                rd["chosen"][row["seat"]] = q
    for g in games.values():  # a refusal only marks a round the game played (it has quote rows)
        for r, rd in g["rounds"].items():
            rd["refused"] = (g["meta"]["trial_id"], r) in refused
            rd["imputed"] = (g["meta"]["trial_id"], r) in imputed
    return games


def failed_rounds(tables):
    """(refused, imputed): the (trial_id, round) pairs with a refused call, and with an imputed call (derive.call_failure
    parse_failure or truncation: a truncated or unparseable reply played as imputed), over the quote, talk and in-game
    question calls (a post-game question does not change the game)."""
    refused, imputed = set(), set()
    for name in ("rounds", "messages", "questions"):
        for row in tables.get(name, []):
            if name == "questions" and row.get("mode") == "post":
                continue
            cls = derive.call_failure(row.get("refusal_kind"), row.get("parse_status"))
            if cls:
                (refused if cls == "refusal" else imputed).add((row["trial_id"], int(row["round"])))
    return refused, imputed


def measures(rounds, threshold=0.8, masked=(), first=None):
    """Measures of one game over {round: rd}. Undercuts, punishments and levels are worked out on all the rounds given,
    then the rounds in `masked` (refusal rounds under `without`) are left out of the counts and means; runs and wars
    skip over masked rounds instead of breaking at them. time_to_high counts from `first` (default: first round)."""
    rs = sorted(rounds)
    masked = set(masked)
    first = rs[0] if first is None and rs else first
    levels = {r: rounds[r]["level"] for r in rs if rounds[r]["level"] is not None and r not in masked}
    under, punish, undercutters, first_under, by_seat = 0, 0, {}, None, {}
    for r in rs:
        for seat, q in rounds[r]["chosen"].items():
            prev = rounds.get(r - 1)
            others = [v for s, v in (prev["quotes"] if prev else {}).items() if s != seat]
            own_prev = prev["chosen"].get(seat) if prev else None
            if others and q < min(others) and (own_prev is None or q < own_prev):
                if any(u != seat for u in undercutters.get(r - 1, ())):
                    punish += r not in masked
                else:
                    undercutters.setdefault(r, set()).add(seat)
                    if r not in masked:
                        under += 1
                        by_seat[seat] = by_seat.get(seat, 0) + 1
                        first_under = r if first_under is None else first_under
    run = best = 0
    for r in rs:
        if r in masked:
            continue
        run = run + 1 if levels.get(r, 0) >= threshold else 0
        best = max(best, run)
    war = 0
    for r in rs:
        if first_under is None or r < first_under or r in masked:
            continue
        if levels.get(r, 1) >= threshold:
            break
        war += 1
    comp = competitive_measures(rounds, rs, masked)
    return {"level": sum(levels.values()) / len(levels) if levels else None, **comp,
            "time_to_high": next((r - first + 1 for r in sorted(levels) if levels[r] >= threshold), None),
            "high_duration": best, "undercuts": under, "punishments": punish, "war_length": war,
            "undercuts_by_seat": json.dumps(dict(sorted(by_seat.items())), separators=(",", ":")),
            "rounds": len([r for r in rs if r not in masked]), "refusal_rounds": sum(1 for r in rs if rounds[r]["refused"]),
            "imputed_rounds": sum(1 for r in rs if rounds[r].get("imputed")), "played_rounds": len(rs)}


def competitive_measures(rounds, rs, masked=()):
    """U16 per-firm competitiveness over the rounds rs not in masked: competitive_share = competitive firm-rounds / scored
    firm-rounds (pooled), always_competitive_share = firms competitive in every scored round / firms scored (blank when
    nothing was scored; round 1 is never scored; see competitiveness.py)."""
    per = {}
    for r in rs:
        if r not in masked:
            for seat, v in rounds[r].get("competitive", {}).items():
                per.setdefault(seat, []).append(v)
    n = sum(len(v) for v in per.values())
    return {"competitive_share": sum(sum(v) for v in per.values()) / n if n else None,
            "always_competitive_share": sum(all(v) for v in per.values()) / len(per) if per else None}


def select(game, basis, start, end):
    """The rounds of a game under a basis, or None when the game lacks part of the fixed window. Under the window
    basis the first window round cannot show an undercut (the round before it is outside the window)."""
    rs = game["rounds"]
    if basis == "window":
        if any(r not in rs for r in range(start, end + 1)):
            return None
        rs = {r: v for r, v in rs.items() if start <= r <= end}
    return rs


def game_measures(games, start, end, threshold=0.8):
    """Rows (one per game x basis x refusals) with the meta columns and the measures; corrupt trials are not measured
    (see exclusions)."""
    rows = []
    for tid in sorted(games):
        m = games[tid]["meta"]
        if m.get("status") == "corrupt":
            continue
        for basis in BASES:
            rs = select(games[tid], basis, start, end)
            if rs is None:
                continue
            for ref in REFUSALS:
                masked = [r for r, v in rs.items() if v["refused"]] if ref == "without" else []
                rows.append(dict(trial_id=tid, arm=m["arm"], thinking=m["thinking"], penalty_point=m["penalty_point"],
                                 wording=m["wording"], seed=m["seed"], status=m.get("status", ""), basis=basis, refusals=ref,
                                 **measures(rs, threshold, masked, start if basis == "window" else None)))
    return rows


def exclusions(games, start, end):
    """Every game left out of a basis, with the reason: corrupt trials, and games lacking part of the fixed window."""
    out = []
    for tid in sorted(games):
        if games[tid]["meta"].get("status") == "corrupt":
            out.append(dict(trial_id=tid, basis="all", reason="corrupt"))
        elif select(games[tid], "window", start, end) is None:
            out.append(dict(trial_id=tid, basis="window", reason="incomplete_window"))
    return out


def arm_matcher(pattern):
    """A predicate on arm names: re.search with `pattern`; None matches every arm."""
    rx = None if pattern is None else re.compile(pattern)
    return lambda arm: rx is None or bool(rx.search(str(arm)))


def pair_window(rows, arms=HEADLINE_ARMS):
    """Window basis only, among the arms matching `arms` (a regular expression, default the headline arms; None = every
    arm in rows): keep such a game when every such arm in its (thinking, penalty_point) has its seed and wording too, so
    the arms of one comparison are compared on the same seeds. Rows of other arms are never paired (kept as they are).
    Returns (kept rows, dropped rows)."""
    keys, arms, scoped = {}, {}, arm_matcher(arms)
    for r in rows:
        if r["basis"] == "window" and scoped(r["arm"]):
            g = (r["thinking"], r["penalty_point"], r["refusals"])
            keys.setdefault(g + (r["arm"],), set()).add((r["wording"], r["seed"]))
            arms.setdefault(g, set()).add(r["arm"])
    kept, dropped = [], []
    for r in rows:
        g = (r["thinking"], r["penalty_point"], r["refusals"])
        if r["basis"] == "window" and scoped(r["arm"]) and any((r["wording"], r["seed"]) not in keys[g + (a,)] for a in arms[g]):
            dropped.append(r)
        else:
            kept.append(r)
    return kept, dropped


def ci_method(strata):
    """How bootstrap_ci resamples these strata: "stratified" (games within each stratum, every stratum with 2+ games),
    "game" (some stratum has a single game, which a stratified resample never varies, so it would understate the
    interval, down to zero width when every stratum has one game: games are resampled across strata instead), or
    "none" (fewer than 2 games: the interval is not estimable)."""
    vals = [v for v in strata.values() if v]
    if sum(len(v) for v in vals) < 2:
        return "none"
    return "game" if any(len(v) == 1 for v in vals) else "stratified"


def bootstrap_ci(strata, boot=2000, seed=0):
    """(mean, lo, hi): strata maps stratum -> list of values. Resamples games within each stratum (sizes kept), or, when
    a stratum has a single game, resamples all the games together (game level); lo and hi are None (not estimable)
    with fewer than 2 games. See ci_method."""
    method = ci_method(strata)
    if method == "game":
        return stratified_ci({"all": [x for k in sorted((k for k in strata if strata[k]), key=str) for x in strata[k]]}, boot, seed)
    mean, lo, hi = stratified_ci(strata, boot, seed)
    return (mean, None, None) if method == "none" else (mean, lo, hi)


def stratified_ci(strata, boot=2000, seed=0):
    """(mean, lo, hi) of a bootstrap that resamples games within each stratum (sizes kept)."""
    vals = {k: v for k, v in strata.items() if v}
    n = sum(len(v) for v in vals.values())
    if not n:
        return None, None, None
    mean = sum(sum(v) for v in vals.values()) / n
    rng = random.Random(seed)
    keys = sorted(vals, key=str)
    means = sorted(sum(rng.choice(vals[k]) for k in keys for _ in vals[k]) / n for _ in range(boot))
    return mean, means[int(round(0.025 * (boot - 1)))], means[int(round(0.975 * (boot - 1)))]


def summarize(rows, boot=2000, seed=0, empty_window=False):
    """One summary row per arm x thinking x penalty_point x basis x refusals. With empty_window, a cell whose window keeps
    no game (every game too short, or dropped by the pairing) still gets its window rows: n_games 0, window_share 0."""
    groups = {}
    for r in rows:
        groups.setdefault((r["arm"], r["thinking"], r["penalty_point"], r["basis"], r["refusals"]), []).append(r)
    out = []
    if empty_window:
        for k in [k for k in groups if k[3] == "assigned"]:
            if k[:3] + ("window",) + k[4:] not in groups:
                out.append(dict(zip(("arm", "thinking", "penalty_point", "basis", "refusals"), k[:3] + ("window",) + k[4:]),
                                n_games=0, games_with_refusal=0, games_with_imputed=0, imputed_round_share="",
                                games_assigned=len(groups[k]), window_share=0.0, level="",
                                level_lo="", level_hi="", ci_method="none", per_wording="{}", never_high=0, time_to_high="",
                                high_duration="", undercuts="", punishments="", war_length="", competitive_share="",
                                always_competitive_share=""))
    for key in sorted(groups, key=lambda k: tuple(str(x) for x in k)):
        g = groups[key]
        strata = {}
        for r in g:
            if r["level"] is not None:
                strata.setdefault(r["wording"], []).append(r["level"])
        mean, lo, hi = bootstrap_ci(strata, boot, seed)
        assigned = len(groups.get(key[:3] + ("assigned",) + key[4:], ()))
        ttd = [r["time_to_high"] for r in g if r["time_to_high"] is not None]
        avg = lambda c: round(sum(r[c] for r in g) / len(g), 6)
        avg_opt = lambda c: _r(sum(r[c] for r in g if r.get(c) is not None) / n) if (n := sum(1 for r in g if r.get(c) is not None)) else ""
        out.append(dict(zip(("arm", "thinking", "penalty_point", "basis", "refusals"), key),
                        n_games=len(g), games_with_refusal=sum(1 for r in g if r["refusal_rounds"]),
                        games_with_imputed=sum(1 for r in g if r.get("imputed_rounds")),
                        imputed_round_share=_share(g),
                        games_assigned=assigned, window_share=_r(len(g) / assigned) if key[3] == "window" and assigned else "",
                        level=_r(mean), level_lo=_r(lo), level_hi=_r(hi), ci_method=ci_method(strata),
                        per_wording=json.dumps({str(w): _r(sum(v) / len(v)) for w, v in sorted(strata.items(), key=lambda kv: str(kv[0]))}, separators=(",", ":")),
                        never_high=len(g) - len(ttd), time_to_high=_r(sum(ttd) / len(ttd)) if ttd else "",
                        high_duration=avg("high_duration"), undercuts=avg("undercuts"), punishments=avg("punishments"),
                        war_length=avg("war_length"), competitive_share=avg_opt("competitive_share"),
                        always_competitive_share=avg_opt("always_competitive_share")))
    return sorted(out, key=lambda r: tuple(str(r[c]) for c in ("arm", "thinking", "penalty_point", "basis", "refusals")))


def contrasts(rows, arm_a, arm_b, boot=2000, seed=0, measure="level"):
    """Arm A minus arm B per (thinking, penalty_point, basis, refusals), paired on wording and seed."""
    cells = {}
    for r in rows:
        if r["arm"] in (arm_a, arm_b) and r[measure] is not None:
            c = cells.setdefault((r["thinking"], r["penalty_point"], r["basis"], r["refusals"]), {})
            k = (r["wording"], r["seed"], r["arm"])
            if k in c:
                raise ValueError("duplicate game for %s (wording, seed, arm) in one cell" % (k,))
            c[k] = r[measure]
    out = []
    for key in sorted(cells, key=lambda k: tuple(str(x) for x in k)):
        c, strata = cells[key], {}
        for (w, s, arm), v in sorted(c.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
            if arm == arm_a and (w, s, arm_b) in c:
                strata.setdefault(w, []).append(v - c[(w, s, arm_b)])
        mean, lo, hi = bootstrap_ci(strata, boot, seed)
        out.append(dict(zip(("thinking", "penalty_point", "basis", "refusals"), key), contrast="%s-%s" % (arm_a, arm_b),
                        measure=measure, n_pairs=sum(len(v) for v in strata.values()), diff=_r(mean), diff_lo=_r(lo), diff_hi=_r(hi),
                        ci_method=ci_method(strata)))
    return out


def warn_ci_methods(rows, what):
    """One stderr warning per kind of bootstrap fallback among rows carrying ci_method (see ci_method)."""
    for method, text in (("game", "a wording with a single game: game-level bootstrap across wordings"),
                         ("none", "fewer than 2 games: interval not estimable, bounds blank")):
        n = sum(1 for r in rows if r.get("ci_method") == method)
        if n:
            print("warning: %d of %d %s have %s (ci_method %s)" % (n, len(rows), what, text, method), file=sys.stderr)


BASELINE_COLS = ("baseline_price_index", "baseline_profit_gain_index", "baseline_competitive_share", "level_minus_baseline")


def add_baseline(summary, baseline_dir, start=1, end=20, threshold=0.8):
    """(summary rows with the BASELINE_COLS filled from the baseline tables dir, the baseline reference rows). The match is
    arm x thinking x penalty_point x basis; a summary row without a baseline cell has blanks."""
    import baseline_bot
    try:
        ref = baseline_bot.reference_rows(baseline_dir, start, end, threshold)
    except (OSError, ValueError, KeyError) as e:
        raise SystemExit("error: --baseline %s: %s" % (baseline_dir, e))
    by = {(r["arm"], r["thinking"], str(r["penalty_point"]), r["basis"]): r for r in ref}
    out = []
    for s in summary:
        b = by.get((s["arm"], s["thinking"], str(s["penalty_point"]), s["basis"]))
        row = dict(s, baseline_price_index=b["price_index"] if b else "", baseline_profit_gain_index=b["profit_gain_index"] if b else "",
                   baseline_competitive_share=b["competitive_share"] if b else "")
        row["level_minus_baseline"] = _r(s["level"] - b["price_index"]) if b and s["level"] != "" and b["price_index"] != "" else ""
        out.append(row)
    return out, ref


def _share(rows):
    """Imputed rounds / played rounds, pooled over the games (blank without rounds)."""
    played = sum(r.get("played_rounds", 0) for r in rows)
    return _r(sum(r.get("imputed_rounds", 0) for r in rows) / played) if played else ""


def _r(x):
    return "" if x is None else round(x, 6)


def write_csv(path, rows, cols=None):
    cols = cols or (list(rows[0]) if rows else [])
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r[k] is None else r[k]) for k in cols})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tables_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--competitive", type=float, help="override; default trials.csv competitive_price")
    ap.add_argument("--collusive", type=float, help="override; default trials.csv collusive_price")
    ap.add_argument("--window-start", type=int, default=1)
    ap.add_argument("--window-end", type=int, default=20)
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--contrast", action="append", default=[], metavar="A:B")
    ap.add_argument("--measure", default="level", help="measure the contrasts use (default level)")
    ap.add_argument("--pair-arms", default=HEADLINE_ARMS, metavar="REGEX",
                    help="arms whose window summary is paired on common seeds (default %(default)s; other arms are not paired)")
    ap.add_argument("--no-pairing", action="store_true", help="do not restrict the window summary to common seeds")
    ap.add_argument("--baseline", metavar="DIR", help="tables dir written by baseline_bot.py: add the undercutter baseline as reference columns")
    a = ap.parse_args(argv)
    tables = load_tables(a.tables_dir)
    try:
        competitive, collusive = resolve_prices(tables, a.competitive, a.collusive)
    except ValueError as e:
        ap.error(str(e))
    games = build_games(tables, competitive, collusive)
    rows = game_measures(games, a.window_start, a.window_end, a.threshold)
    excl = exclusions(games, a.window_start, a.window_end)
    unpaired = rows   # a contrast pairs its own two arms (contrasts()), never on the summary's arm set
    if not a.no_pairing:
        try:
            rows, dropped = pair_window(rows, a.pair_arms)
        except re.error as e:
            ap.error("--pair-arms: %s" % e)
        excl += [dict(trial_id=r["trial_id"], basis="window", reason="unpaired_seed") for r in dropped if r["refusals"] == "with"]
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "measures_by_game.csv", rows, ["trial_id", "arm", "thinking", "penalty_point", "wording", "seed", "basis",
                                                  "refusals", "status", "level", "time_to_high", "high_duration", "undercuts",
                                                  "punishments", "war_length", "undercuts_by_seat", "rounds", "refusal_rounds",
                                                  "imputed_rounds", "competitive_share", "always_competitive_share"])
    write_csv(out / "exclusions.csv", sorted(excl, key=lambda r: (r["trial_id"], r["basis"], r["reason"])), ["trial_id", "basis", "reason"])
    summary = summarize(rows, a.boot, a.seed, empty_window=True)
    extra = ()
    if a.baseline:
        summary, ref = add_baseline(summary, a.baseline, a.window_start, a.window_end, a.threshold)
        write_csv(out / "baseline_reference.csv", ref, ["arm", "thinking", "penalty_point", "basis", "n_games", "price_index", "profit_gain_index",
                                                        "competitive_share", "always_competitive_share"])
        extra = ("baseline_reference.csv",)
    write_csv(out / "measures_summary.csv", summary)
    warn_ci_methods(summary, "summary cells")
    for c in a.contrast:
        if c.count(":") != 1:
            ap.error("--contrast needs A:B")
    if a.contrast:
        crows = [r for c in a.contrast for r in contrasts(unpaired, *c.split(":"), boot=a.boot, seed=a.seed, measure=a.measure)]
        write_csv(out / "contrasts.csv", crows)
        warn_ci_methods(crows, "contrast cells")
    for n in ("measures_by_game.csv", "measures_summary.csv", "exclusions.csv") + (("contrasts.csv",) if a.contrast else ()) + extra:
        print(out / n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
