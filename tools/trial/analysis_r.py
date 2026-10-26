#!/usr/bin/env python3
"""Track R analysis and the refusal table (C10.4; scope sections 4.5 and 4.7; standard library, plus PyYAML to read the
design file when neither --grid nor both --control and --arms are given).

Usage: python -X utf8 tools/trial/analysis_r.py <tables_dir> <out_dir> [--competitive P] [--collusive P]
           [--grid grid.csv | --design trackm_design.yaml] [--control ARM] [--arms A,B,...] [--window-start 1]
           [--window-end 20] [--boot 2000] [--seed 0]
Reads the collect.py tables, and the arm names of Track R from the design: the control is the arm whose `introspection`
is R0 or, when the design has none (the current design), the headline arm of the introspection cell's communication (the
Track R arms play the same 20 wording-seed pairs as the headline, so no duplicate control games exist), else the shared control
`headline-chat` when it is in the tables; the arms are those with R1, R2f, R3f, R2s, R3s, R4 ... (the grid.csv `introspection` column with --grid, else the arms of the design
file, default tools/trial/design/trackm_design.yaml, which needs PyYAML). --control / --arms override (comma list).
Question modes (questions.csv `mode`): fed (R2f/R3f, a separate call whose answers are shown back), inreply (R2s/R3s, a text
field in the quote reply, saved and never shown back) and post (R4, after the game). fed and inreply answers count as in-game
questions (the first one sets after_first_question); post does not.
Design arms without trials are named in a warning. When the control or every selected arm has no trial in the tables, the
r_differential files are not written, the error is printed and the exit status is 1 (the refusal table and
thinks_says_does.csv are still written, any r_differential file left from an earlier run is removed); the same when no
game of any selected arm pairs with a control game (a warning names each arm with no pair). An unreadable or empty grid
or design file exits 2. Writes:
  r_differential_by_round.csv  arm minus control per round, on games paired by thinking, penalty point, wording and seed:
                               n_pairs, diff (mean level difference), bootstrap CI (by game, stratified by wording, or across
                               wordings when a wording has a single pair, as with the one Track R seed: ci_method), and
                               after_first_question (round > the first round with a fed question for that arm; arms with no
                               fed questions, R1 and R4, act from round 1, so every round is `after`; a warning is printed
                               when questions.csv is empty). Both refusals variants (with | without:
                               a round is left out of a pair when either game's round had a refusal).
  r_differential_competitive_by_round.csv  the same, for the per-round competitive share (U16: share of the firms scored
                               in the round, by competitiveness.py, that were competitive; round 1 is never scored) instead of the
                               level (these files carry a `measure` column).
  d_differential_by_round.csv / d_differential_games.csv  the D-set arms (name matching --dset-arms, default `^d-`) against
                               the shared control (--dset-control, default headline-chat), same pairing: per round (measures level
                               and competitive_share; every round counts, no question phase) and game-level contrasts (all
                               measures incl. competitive_share, phase all). Written whenever a D arm and its control are in the
                               tables, whether or not a Track R arm is.
  r_differential_phases.csv    the same difference averaged per game before and after the first question
  r_differential_games.csv     game-level contrasts (level, time_to_high, undercuts, punishments, war_length) via analysis_m, as
                               assigned (phase all) and on the fixed windows before / after the first question
  thinks_says_does.csv         one row per trial x round x seat: reasoning, chat (that seat's messages that round, joined
                               by " | "; the seat's own messages only), confidant and public answers (in-game questions, fed or
                               inreply, whose name contains "confid" / "public"; `mode` = the question modes in the row, joined by "|",
                               to split them), post_confidant / post_public (the same questions asked in
                               the post-game pass, mode post, kept apart because they are not fed back), quote, market_price,
                               refused (the quote call), imputed. A cell with only a post-game answer gets a row with no quote. `reasoning` is read from an optional `reasoning` column of
                               rounds.csv, messages.csv or questions.csv; collect.py writes it (C9.3) when the events carry reasoning;
                               blank otherwise.
  refusal_table.csv / .html    the refusal table (prominent): arm x thinking x kind plus an `all` row per arm and thinking,
                               sorted by refusal rate, highest first; parse_failures and truncations (imputed calls,
                               refusal_kind UNPARSEABLE / TRUNCATED, never refusals: derive.call_failure) next to the refusals,
                               and imputed_rounds / imputed_round_share (played rounds with an imputed call of that kind;
                               the `all` rows count a round once over all kinds)
"""
import argparse
import csv
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_headline as ah  # noqa: E402  (pct only; matplotlib is imported lazily there)
import analysis_m as am  # noqa: E402

PAIR = ("thinking", "penalty_point", "wording", "seed")
DESIGN = Path(__file__).resolve().parent / "design" / "trackm_design.yaml"
MEASURES = ("level", "time_to_high", "undercuts", "punishments", "war_length", "competitive_share")   # competitive_share: U16
TABLE_COLS = ["arm", "thinking", "kind", "trials", "calls", "refusals", "refusal_rate", "parse_failures", "truncations",
              "imputed_rounds", "imputed_round_share", "patterns"]
R_FILES = ("r_differential_by_round.csv", "r_differential_phases.csv", "r_differential_games.csv",
           "r_differential_competitive_by_round.csv")
D_FILES = ("d_differential_by_round.csv", "d_differential_games.csv")
SHARED_CONTROL = "headline-chat"   # unit U10: the introspection and D-set arms are paired with it; there is no separate R0 arm
ARM_LEVEL = re.compile(r"^R\d+[fs]?$", re.I)   # R1, R2f, R3f, R2s, R3s, R4 ...
BY_ROUND_COLS = ["arm", "control", "refusals", "round", "after_first_question", "n_pairs", "diff", "diff_lo", "diff_hi", "ci_method"]


def introspection_arms(grid=None, design=DESIGN):
    """arm -> introspection level (R0, R1, ...) from grid.csv's introspection column, else from the design file's arms."""
    if grid:
        with open(grid, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            raise ValueError("%s has no rows" % grid)
        if "introspection" not in rows[0] or "arm" not in rows[0]:
            raise ValueError("%s has no arm or introspection column" % grid)
        out = {}
        for r in rows:
            lv = (r.get("introspection") or "").strip()
            if lv and out.setdefault(r["arm"], lv) != lv:
                raise ValueError("%s: arm %s has two introspection values (%s, %s)" % (grid, r["arm"], out[r["arm"]], lv))
        return out
    import yaml
    try:
        d = yaml.safe_load(Path(design).read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError("%s is not valid YAML: %s" % (design, e))
    arms = d.get("arms") if isinstance(d, dict) else None
    if not isinstance(arms, list) or not all(isinstance(a, dict) and a.get("name") for a in arms):
        raise ValueError("%s has no list of named arms" % design)
    return {str(a["name"]): str(a["introspection"]).strip() for a in arms if a.get("introspection")}


HEADLINE_OF = {"tacit": "headline-tacit", "private": "headline-chat", "monitored": "headline-monitored"}


def headline_control(grid=None, design=DESIGN):
    """The headline arm that is the Track R control (R0) when the design has no R0 arm of its own: the headline arm of the
    introspection cell's communication (the Track R arms play the same 20 wording-seed pairs as the headline), or None."""
    try:
        if grid:
            with open(grid, encoding="utf-8-sig", newline="") as f:
                comms = {r["communication"] for r in csv.DictReader(f) if (r.get("introspection") or "").strip()}
            comm = comms.pop() if len(comms) == 1 else None
        else:
            import yaml
            comm = ((yaml.safe_load(Path(design).read_text(encoding="utf-8")) or {}).get("introspection_cell") or {}).get("communication")
    except (OSError, ValueError, ImportError, KeyError, AttributeError):
        return None
    return HEADLINE_OF.get(comm)


def select_arms(levels, present, control=None, arms=None, headline=None):
    """(control, arms, warnings) from the introspection levels (unless given); ValueError when the control or every arm
    has no trial among `present` (the arm names in the tables). With no R0 arm in `levels`, the control is `headline`
    (the cell's headline arm, see headline_control) when given."""
    if control is None:
        ctl = sorted(a for a, lv in levels.items() if lv.upper() == "R0") or ([headline] if headline else [])
        if not ctl and SHARED_CONTROL in present:
            ctl = [SHARED_CONTROL]   # unit U10: the shared control when the cell is not named
        if len(ctl) != 1:
            raise ValueError("the design or grid names %d R0 (control) arms: %s, and %s is not in the tables; pass --control"
                             % (len(ctl), ", ".join(ctl) or "none", SHARED_CONTROL))
        control = ctl[0]
    if arms is None:
        arms = sorted((a for a, lv in levels.items() if ARM_LEVEL.match(lv) and lv.upper() != "R0" and a != control),
                      key=lambda a: (levels[a].upper(), a))
    if not arms:
        raise ValueError("no Track R arms selected (--arms empty, or the design or grid names none besides the control)")
    if control not in present:
        raise ValueError("the control arm %r has no trial in the tables (arms there: %s)" % (control, ", ".join(sorted(present)) or "none"))
    missing = [a for a in arms if a not in present]
    if len(missing) == len(arms):
        raise ValueError("none of the selected arms (%s) has a trial in the tables" % ", ".join(arms))
    warns = ["warning: arm %s has no trial in the tables; skipped" % a for a in missing]
    return control, [a for a in arms if a in present], warns


def first_question_rounds(tables):
    """arm -> first round with a fed (in-game) question call."""
    arm_of = {t["trial_id"]: t["arm"] for t in tables["trials"] if t.get("status") != "corrupt"}
    out = {}
    for q in tables.get("questions", []):
        if q.get("mode") != "post" and q["trial_id"] in arm_of:
            a, r = arm_of[q["trial_id"]], int(q["round"])
            out[a] = min(r, out.get(a, r))
    return out


def _by_key(games, arm):
    out = {}
    for g in games.values():
        if g["meta"]["arm"] == arm and g["meta"].get("status") != "corrupt":
            key = tuple(g["meta"][k] for k in PAIR)
            if key in out:
                raise ValueError("two games of arm %s share thinking, point, wording and seed %s" % (arm, key))
            out[key] = g
    return out


def _pairs(games, control, arm):
    ctl, mine = _by_key(games, control), _by_key(games, arm)
    if not ctl:
        raise ValueError("no games for the control arm %r" % control)
    return [(k, mine[k], ctl[k]) for k in sorted(mine, key=lambda k: tuple(str(x) for x in k)) if k in ctl]


def _first_round(tables, games, arm):
    """The round after which the arm's intervention is felt: its first fed question round; 0 for an arm with no fed questions
    (R1 and R4 act from round 1, so every round counts as `after`)."""
    fq = first_question_rounds(tables).get(arm)
    if fq is None and not tables.get("questions"):
        print("warning: questions.csv is empty or missing; every round counts as after the first question", file=sys.stderr)
    return fq if fq is not None else 0


def _value(rd, measure):
    """A round's level, or its competitive share (U16: competitive firms / scored firms; None when no firm was scored)."""
    if measure == "level":
        return rd["level"]
    flags = list(rd.get("competitive", {}).values())
    return sum(flags) / len(flags) if flags else None


def _diff(a, c, r, ref, measure="level"):
    """Difference arm minus control in round r of the measure (level or competitive_share), or None (round missing, no
    value, or left out under `without`)."""
    ra, rc = a["rounds"].get(r), c["rounds"].get(r)
    if ra is None or rc is None:
        return None
    va, vc = _value(ra, measure), _value(rc, measure)
    if va is None or vc is None:
        return None
    if ref == "without" and (ra["refused"] or rc["refused"]):
        return None
    return va - vc


def round_differential(games, tables, control, arm, boot=2000, seed=0, measure="level", first=None):
    """Per-round differential arm minus control of `measure` (level or competitive_share). `first` = the round after which the
    arm's intervention is felt (default: its first in-game question round); the D-set arms pass 0 (no questions)."""
    pairs = _pairs(games, control, arm)
    first = _first_round(tables, games, arm) if first is None else first
    rows = []
    for ref in am.REFUSALS:
        for r in sorted({r for _, a, c in pairs for r in set(a["rounds"]) & set(c["rounds"])}):
            strata = {}
            for key, a, c in pairs:
                d = _diff(a, c, r, ref, measure)
                if d is not None:
                    strata.setdefault(key[2], []).append(d)
            mean, lo, hi = am.bootstrap_ci(strata, boot, seed)
            rows.append(dict(arm=arm, control=control, measure=measure, refusals=ref, round=r, after_first_question=int(r > first),
                             n_pairs=sum(len(v) for v in strata.values()), diff=am._r(mean), diff_lo=am._r(lo), diff_hi=am._r(hi),
                             ci_method=am.ci_method(strata)))
    return rows


def phase_summary(games, tables, control, arms, boot=2000, seed=0):
    out = []
    for arm in arms:
        pairs, first = _pairs(games, control, arm), _first_round(tables, games, arm)
        for ref in am.REFUSALS:
            for phase in ("before", "after"):
                strata = {}
                for key, a, c in pairs:
                    ds = [d for r in set(a["rounds"]) & set(c["rounds"]) if (r > first) == (phase == "after")
                          for d in [_diff(a, c, r, ref)] if d is not None]
                    if ds:
                        strata.setdefault(key[2], []).append(sum(ds) / len(ds))
                mean, lo, hi = am.bootstrap_ci(strata, boot, seed)
                out.append(dict(arm=arm, control=control, refusals=ref, phase=phase, first_question_round=first,
                                n_pairs=sum(len(v) for v in strata.values()), diff=am._r(mean), diff_lo=am._r(lo), diff_hi=am._r(hi),
                                ci_method=am.ci_method(strata)))
    return out


def game_contrasts(games, control, arms, start, end, boot=2000, seed=0, tables=None):
    """Game-level contrasts. phase `all`: as assigned. With `tables`, phases `before` (window start..first question round) and
    `after` (first question round + 1..end) use the fixed window basis of that part, so the totals compare like with like."""
    whole = [r for r in am.game_measures(games, start, end) if r["basis"] == "assigned"]
    out = []
    for arm in arms:
        parts = [("all", whole)]
        if tables is not None:
            first = _first_round(tables, games, arm)
            for phase, (a, b) in (("before", (start, first)), ("after", (max(start, first + 1), end))):
                if a <= b:
                    parts.append((phase, [r for r in am.game_measures(games, a, b) if r["basis"] == "window"]))
        for phase, rows in parts:
            for m in MEASURES:
                out += [dict(r, phase=phase) for r in am.contrasts(rows, arm, control, boot, seed, m)]
    return out


def thinks_says_does(tables):
    cell = {}
    modes = {}

    def put(tid, r, seat, key, text):
        if text:
            c = cell.setdefault((tid, int(r), seat), {})
            c[key] = c[key] + " | " + text if key in c else text

    base = {}
    for row in tables["rounds"]:
        base[(row["trial_id"], int(row["round"]), row["seat"])] = row
        put(row["trial_id"], row["round"], row["seat"], "reasoning", row.get("reasoning", ""))
    for m in tables.get("messages", []):
        if m["seat"]:
            if not am.derive.withheld(m["text"]):   # an imputed turn said nothing: no placeholder in `chat`
                put(m["trial_id"], m["round"], m["seat"], "chat", m["text"])
            put(m["trial_id"], m["round"], m["seat"], "reasoning", m.get("reasoning", ""))
    for q in tables.get("questions", []):
        name = q["question"].lower()
        key = "confidant" if "confid" in name else "public" if "public" in name else None
        if key:
            put(q["trial_id"], q["round"], q["seat"], ("post_" if q.get("mode") == "post" else "") + key, q["answer"])
            if q["answer"] and q.get("mode"):
                modes.setdefault((q["trial_id"], int(q["round"]), q["seat"]), set()).add(q["mode"])
        put(q["trial_id"], q["round"], q["seat"], "reasoning", q.get("reasoning", ""))
    rows = []
    for (tid, r, seat) in sorted(set(base) | set(cell)):  # cells with only a post-game answer or talk get a row with no quote
        b = base.get((tid, r, seat), {})
        c = cell.get((tid, r, seat), {})
        rows.append(dict(trial_id=tid, round=r, seat=seat, mode="|".join(sorted(modes.get((tid, r, seat), ()))),
                         reasoning=c.get("reasoning", ""), chat=c.get("chat", ""),
                         confidant=c.get("confidant", ""), public=c.get("public", ""), post_confidant=c.get("post_confidant", ""),
                         post_public=c.get("post_public", ""), quote=am._f(b["quote"]) if b else "",
                         market_price=am._f(b["market_price"]) if b else "",
                         refused=int(bool(b and am.derive.call_failure(b["refusal_kind"], b["parse_status"]) == "refusal")),
                         imputed=int(bool(b and b["imputed"] in ("1", "True")))))
    return rows


def _imputed_all(tables):
    """(arm, thinking) -> (imputed rounds, played rounds) over all call kinds (a round counts once), from the tables."""
    _, imputed = am.failed_rounds(tables)
    meta = {t["trial_id"]: (t["arm"], t["thinking"]) for t in tables.get("trials", []) if t.get("status") != "corrupt"}
    played, out = {(r["trial_id"], int(r["round"])) for r in tables.get("rounds", []) if r["trial_id"] in meta}, {}
    for tid, rnd in played:
        a, b = out.get(meta[tid], (0, 0))
        out[meta[tid]] = (a + ((tid, rnd) in imputed), b + 1)
    return out


def refusal_table(refusals, tables=None):
    """Rows of refusal_table.csv; with `tables`, the `all` rows carry the imputed-round share over all kinds."""
    agg, pooled = {}, _imputed_all(tables) if tables else {}
    for r in refusals:
        for kind in (r["kind"], "all"):
            a = agg.setdefault((r["arm"], r["thinking"], kind), dict(trials=0, calls=0, refusals=0, parse_failures=0, truncations=0,
                                                                     imputed_rounds=0, played_rounds=0))
            for c in ("calls", "refusals", "parse_failures", "truncations") + (("imputed_rounds", "played_rounds") if kind != "all" else ()):
                a[c] += int(r.get(c) or 0)   # parse_failures / truncations: absent in tables collected before Q3 (imputed: fix-imputed_visibility)
            if kind == "all":
                a["imputed_rounds"], a["played_rounds"] = pooled.get((r["arm"], r["thinking"]), (0, 0))
            a["trials"] = max(a["trials"], int(r.get("trials") or 0)) if kind != "all" else a["trials"]
    rows = [dict(arm=k[0], thinking=k[1], kind=k[2], trials=v["trials"] or "", calls=v["calls"], refusals=v["refusals"],
                 parse_failures=v["parse_failures"], truncations=v["truncations"],
                 imputed_rounds=v["imputed_rounds"] if v["played_rounds"] else "",
                 imputed_round_share=ah.pct(v["imputed_rounds"] / v["played_rounds"]) if v["played_rounds"] else "",
                 refusal_rate=ah.pct(v["refusals"] / v["calls"]) if v["calls"] else "",
                 _rate=v["refusals"] / v["calls"] if v["calls"] else -1, patterns="") for k, v in agg.items()]
    for row in rows:
        row["patterns"] = "; ".join("%s: %s" % (r["kind"], r["patterns"]) for r in refusals
                                    if (r["arm"], r["thinking"]) == (row["arm"], row["thinking"]) and r.get("patterns") and row["kind"] in ("all", r["kind"]))
    rows.sort(key=lambda r: (-r["_rate"], str(r["arm"]), str(r["thinking"]), r["kind"] != "all", str(r["kind"])))
    for r in rows:
        del r["_rate"]
    return rows


def refusal_html(rows):
    cols = TABLE_COLS
    head = "".join("<th>%s</th>" % c for c in cols)
    body = "".join("<tr%s>%s</tr>" % (' class="all"' if r["kind"] == "all" else "", "".join("<td>%s</td>" % html.escape(str(r[c])) for c in cols)) for r in rows)
    return ("<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>Refusals</title><style>body{font-family:sans-serif}"
            "table{border-collapse:collapse}td,th{border:1px solid #999;padding:4px 8px}tr.all{font-weight:bold;background:#eef}</style></head>"
            "<body><h1>Refusals by arm, thinking mode and kind</h1><p>Refusal rate = refused calls / calls. Parse failures (refusal_kind UNPARSEABLE) and truncations (TRUNCATED) are imputed "
            "calls, counted apart and never as refusals; imputed-round share = played rounds with an imputed call of that kind "
            "(bold rows: of any kind; post-game questions excluded) / played rounds. The bold rows pool all kinds. "
            "Refusing games are never dropped.</p><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></body></html>\n" % (head, body))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tables_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--competitive", type=float, help="override; default trials.csv competitive_price")
    ap.add_argument("--collusive", type=float, help="override; default trials.csv collusive_price")
    ap.add_argument("--control", help="control arm (default: the design arm with introspection R0)")
    ap.add_argument("--arms", help="comma list (default: the design arms with introspection R1, R2 ...)")
    ap.add_argument("--grid", help="grid.csv whose introspection column names the Track R arms")
    ap.add_argument("--design", default=str(DESIGN), help="design file read when --grid is not given (default %(default)s)")
    ap.add_argument("--dset-arms", default="^d-", help="regex of the D-set arm names (unit U8); default %(default)s")
    ap.add_argument("--dset-control", default=SHARED_CONTROL, help="the D-set control arm (default %(default)s)")
    ap.add_argument("--window-start", type=int, default=1)
    ap.add_argument("--window-end", type=int, default=20)
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    tables = am.load_tables(a.tables_dir)
    try:
        competitive, collusive = am.resolve_prices(tables, a.competitive, a.collusive)
    except ValueError as e:
        ap.error(str(e))
    games = am.build_games(tables, competitive, collusive)
    levels = {}
    if a.control is None or a.arms is None:
        try:
            levels = introspection_arms(a.grid, a.design)
        except (OSError, ValueError, ImportError) as e:
            ap.error("cannot read the Track R arms: %s" % e)
    present = {str(g["meta"]["arm"]) for g in games.values() if g["meta"].get("status") != "corrupt"}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    warns = []
    try:
        control, arms, warns = select_arms(levels, present, a.control.strip() if a.control is not None else None,
                                           [x.strip() for x in a.arms.split(",") if x.strip()] if a.arms is not None else None,
                                           headline_control(a.grid, a.design))
        for arm in arms:
            if not _pairs(games, control, arm):
                warns.append("warning: no game of arm %s pairs with a %s game (thinking, point, wording, seed)" % (arm, control))
        if all(not _pairs(games, control, arm) for arm in arms):
            raise ValueError("no game of the selected arms pairs with a control game")
    except ValueError as e:
        for w in warns:
            print(w, file=sys.stderr)
        for n in R_FILES:
            (out / n).unlink(missing_ok=True)
        write_common(out, tables)
        write_dset(out, games, tables, present, a)
        print("error: %s; the r_differential files were not written" % e, file=sys.stderr)
        return 1
    for w in warns:
        print(w, file=sys.stderr)
    a.control = control
    by_round = [r for arm in arms for r in round_differential(games, tables, a.control, arm, a.boot, a.seed)]
    comp_round = [r for arm in arms for r in round_differential(games, tables, a.control, arm, a.boot, a.seed, "competitive_share")]
    phases = phase_summary(games, tables, a.control, arms, a.boot, a.seed)
    gc = game_contrasts(games, a.control, arms, a.window_start, a.window_end, a.boot, a.seed, tables)
    am.write_csv(out / "r_differential_by_round.csv", by_round, BY_ROUND_COLS)
    am.write_csv(out / "r_differential_competitive_by_round.csv", comp_round, ["measure"] + BY_ROUND_COLS)
    am.write_csv(out / "r_differential_phases.csv", phases,
                 ["arm", "control", "refusals", "phase", "first_question_round", "n_pairs", "diff", "diff_lo", "diff_hi", "ci_method"])
    am.write_csv(out / "r_differential_games.csv", gc,
                 ["contrast", "measure", "phase", "thinking", "penalty_point", "basis", "refusals", "n_pairs", "diff", "diff_lo", "diff_hi", "ci_method"])
    am.warn_ci_methods(by_round + comp_round + phases + gc, "Track R differential cells")
    write_common(out, tables)
    write_dset(out, games, tables, present, a)
    for n in sorted(p.name for p in out.iterdir()):
        print(out / n)
    return 0


def write_dset(out, games, tables, present, a):
    """The D-set differential (unit U16 follow-up): each present arm matching --dset-arms against --dset-control, per round (level
    and competitive_share) and game-level (all measures), whenever the control and a D arm are in the tables. Any file left from an
    earlier run is removed first."""
    for n in D_FILES:
        (out / n).unlink(missing_ok=True)
    try:
        pat = re.compile(a.dset_arms)
    except re.error as e:
        print("warning: --dset-arms is not a regular expression (%s); no D-set differential" % e, file=sys.stderr)
        return
    arms = sorted(x for x in present if pat.search(x) and x != a.dset_control)
    if not arms:
        return
    if a.dset_control not in present:
        print("warning: the D-set control %s has no trial in the tables; no D-set differential" % a.dset_control, file=sys.stderr)
        return
    arms = [x for x in arms if _pairs(games, a.dset_control, x)]
    if not arms:
        print("warning: no D-set game pairs with a %s game; no D-set differential" % a.dset_control, file=sys.stderr)
        return
    by_round = [r for arm in arms for m in ("level", "competitive_share")
                for r in round_differential(games, tables, a.dset_control, arm, a.boot, a.seed, m, first=0)]
    gc = game_contrasts(games, a.dset_control, arms, a.window_start, a.window_end, a.boot, a.seed)
    am.write_csv(out / "d_differential_by_round.csv", by_round, ["measure"] + BY_ROUND_COLS)
    am.write_csv(out / "d_differential_games.csv", gc,
                 ["contrast", "measure", "phase", "thinking", "penalty_point", "basis", "refusals", "n_pairs", "diff", "diff_lo", "diff_hi", "ci_method"])
    am.warn_ci_methods(by_round + gc, "D-set differential cells")


def write_common(out, tables):
    """The outputs that do not depend on the Track R arms: thinks_says_does.csv and the refusal table."""
    am.write_csv(out / "thinks_says_does.csv", thinks_says_does(tables),
                 ["trial_id", "round", "seat", "mode", "reasoning", "chat", "confidant", "public", "post_confidant", "post_public", "quote",
                  "market_price", "refused", "imputed"])
    table = refusal_table(tables["refusals"], tables)
    am.write_csv(out / "refusal_table.csv", table, TABLE_COLS)
    (out / "refusal_table.html").write_text(refusal_html(table), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
