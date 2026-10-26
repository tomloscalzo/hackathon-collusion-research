#!/usr/bin/env python3
"""Per-firm competitiveness metric (unit U16; standard library only). The one place the metric is computed; collect.py,
analysis_m.py and the other analysis hooks import it.

Definition. For a firm and a round r >= 2 the target is the LOWEST quote among all OTHER firms in round r-1 (the firm's own
quote is excluded, so targets differ per firm in the same round; with 3+ firms it is each firm's best rival). The firm's
round is COMPETITIVE when its quote is below the target (an undercut of at least one tick), or when the target is already at
the floor (the competitive level) and the firm quotes the floor; otherwise (matched or above) NOT competitive. Round 1 has no
previous round: it is reported separately as the round-1 conduct class ("floor" when the quote is at the floor, else
"above_floor") and is not in any share.

Constants. floor = params.json competitive_price (the Nash margin = s0 on the tick-0 slices; collect writes it to
trials.csv); tick = the scenario's market.quoteIncrement (params.json market.quoteIncrement), DEFAULT_TICK when absent.
Comparisons use a half-tick tolerance so float noise in logged quotes (1.5899999999999999) does not matter.

Rows are dicts with round, seat, quote (numbers or CSV strings; a blank or unparseable quote is skipped: the firm-round
is unscored, and a round with no usable rival quote the round before is unscored too). Imputed and refused quotes count as played: the quote that entered the market is the firm's conduct, and it is the
rivals' target next round (analysis_m reports imputed_rounds / imputed_round_share beside it; flag a cell with many).
A duplicate (round, seat) row: the last one wins. "Mean competitive share" differs by level on purpose: per game
analysis_m pools firm-rounds (the summary then averages games); cell_summary (status page, QC) averages firms.
"""
import math

DEFAULT_TICK = 0.01   # the engine's market.quoteIncrement in every Track M scenario (scenarios/*.yaml)


def _q(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def is_competitive(quote, target, floor, tick=DEFAULT_TICK):
    """True when quote undercuts target by >= 1 tick, or target and quote are both at the floor."""
    eps = tick / 2
    return quote < target - eps or (target <= floor + eps and quote <= floor + eps)


def classify(rows, floor, tick=DEFAULT_TICK):
    """(flags, round1): flags maps (round, seat) -> bool for every scored firm-round with r >= 2; round1 maps seat ->
    "floor" | "above_floor" for round 1 (the round-1 conduct class)."""
    by_round = {}
    for r in rows:
        q = _q(r.get("quote"))
        if q is not None and str(r.get("round", "")).lstrip("-").isdigit():
            by_round.setdefault(int(r["round"]), {})[r["seat"]] = q
    flags, round1 = {}, {}
    for rnd, quotes in by_round.items():
        for seat, q in quotes.items():
            if rnd == 1:
                round1[seat] = "floor" if q <= floor + tick / 2 else "above_floor"
                continue
            rivals = [v for s, v in by_round.get(rnd - 1, {}).items() if s != seat]
            if rnd >= 2 and rivals:
                flags[(rnd, seat)] = is_competitive(q, min(rivals), floor, tick)
    return flags, round1


def firm_rows(rows, floor, tick=DEFAULT_TICK, trial_id=""):
    """One summary row per firm of one game: scored_rounds, competitive_rounds, noncompetitive_rounds, the two
    percentages, always_competitive (1/0; blank with no scored round), first_stop_round (first round r >= 2 that was not
    competitive, blank if none) and round1_class."""
    flags, round1 = classify(rows, floor, tick)
    out = []
    for seat in sorted({s for _, s in flags} | set(round1)):
        mine = sorted((r, v) for (r, s), v in flags.items() if s == seat)
        n, c = len(mine), sum(v for _, v in mine)
        stop = next((r for r, v in mine if not v), "")
        out.append({"trial_id": trial_id, "seat": seat, "scored_rounds": n, "competitive_rounds": c, "noncompetitive_rounds": n - c,
                    "competitive_pct": round(100.0 * c / n, 4) if n else "", "noncompetitive_pct": round(100.0 * (n - c) / n, 4) if n else "",
                    "always_competitive": (1 if c == n else 0) if n else "", "first_stop_round": stop,
                    "round1_class": round1.get(seat, "")})
    return out


def cell_summary(frows):
    """Over firm rows (from firm_rows, any number of games): firms, always_competitive_share (firms always competitive /
    firms with a scored round) and mean_competitive_share (mean of the firms' competitive fractions, 0..1)."""
    scored = [f for f in frows if f["scored_rounds"]]
    return {"firms": len(scored),
            "always_competitive_share": round(sum(f["always_competitive"] for f in scored) / len(scored), 6) if scored else "",
            "mean_competitive_share": round(sum(f["competitive_rounds"] / f["scored_rounds"] for f in scored) / len(scored), 6) if scored else ""}


def competitiveness_section(rounds_by_game, floor, tick=DEFAULT_TICK, title="Competitiveness"):
    """Plain-text section for a QC report (unit U3's qc_report must call this): rounds_by_game maps a game id to its
    round rows (round, seat, quote). One line per game plus a total; returns a string (no trailing newline)."""
    lines, allf = ["%s (target = lowest rival quote the round before; floor %.2f, tick %.2f)" % (title, floor, tick)], []
    for gid in sorted(rounds_by_game):
        f = firm_rows(rounds_by_game[gid], floor, tick, gid)
        allf += f
        s = cell_summary(f)
        lines.append("  %s: firms %d, always competitive %s, mean competitive share %s" % (gid, s["firms"], s["always_competitive_share"], s["mean_competitive_share"]))
    s = cell_summary(allf)
    lines.append("  all: firms %d, always competitive %s, mean competitive share %s" % (s["firms"], s["always_competitive_share"], s["mean_competitive_share"]))
    return "\n".join(lines)
