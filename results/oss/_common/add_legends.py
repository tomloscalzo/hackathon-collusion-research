"""Owner rule: a legend table directly under EVERY figure, defining every code on BOTH axes and the colour metric.

usage: python -X utf8 add_legends.py REPORT.md RUN_CSV [DATA_DICTIONARY_CSV [STEP1_5_SCRIPTS_DIR]]
Rewrites REPORT.md in place. After each image line ![..](figures/NAME.png) it inserts a "Legend" table (marker <!-- legend -->;
an existing legend right under the image is replaced, so the script is idempotent), grouped as:
- Rows (y-axis) and Columns (x-axis): every level of each design variable on that axis, with its meaning (arms as
  "slug: description" from oss_arm_labels.py; penalty points with their fine; seeds with their planned length; wordings; families;
  communication; payoff examples; firms; planned lengths). Levels are the ones with DONE games in RUN_CSV.
- Colour (cell value): every metric or derived feature named in the caption or file name, with its definition and direction
  (from the five-metric definitions below or, for other run.csv columns, the data dictionary label and description).
Axes are read from the figure name or caption: "<a>_x_<b>" and "<a> x <b>" (rows a, columns b), "by <a> rows and <b> columns",
1var maps (rows = the variables of the panel group), "by arm" in Step 1.5 (rows = features, columns = arm) and the Step 2
heat maps (rows = arm and penalty point, columns = the five metrics). Variables found but not placed on an axis are listed
under "Codes".
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oss_arm_labels import DESC  # noqa: E402

MARK = "<!-- legend -->"
FIVE = {
    "market_price_mean": ("Average absolute spread", "mean market quote (half-spread), 1.00 competitive floor to 3.00 monopoly", "higher = more collusive"),
    "avg_abs_spread": ("Average absolute spread", "mean market quote (half-spread), 1.00 competitive floor to 3.00 monopoly", "higher = more collusive"),
    "price_index": ("Price index", "(market price - 1)/2 averaged over rounds; 0 competitive, 1 monopoly", "higher = more collusive"),
    "profit_gain_index": ("Profit gain index", "(profit - competitive profit)/(monopoly profit - competitive profit)", "higher = more collusive"),
    "competitive_share": ("Competitive share", "share of firm-rounds undercutting the rival's previous quote by a tick, or both at 1.00", "higher = more competitive"),
    "matching_share": ("Matching share", "share of firm-rounds matching the rival's previous quote above 1.00 (coordination signature)", "higher = more collusive"),
    "undercut_count": ("Undercut count", "rounds in which a firm undercut the rival", "higher = more competitive"),
    "rounds_played": ("Rounds played", "game length (planned 7 to 20; the regulator can end a game early)", "no collusion direction"),
    "ended_by_evidence": ("Share ended by evidence", "games the regulator ended after finding evidence of coordination", "no collusion direction"),
    "collusive_game": ("Collusive-game share", "games flagged collusive by the intent tool's working rule (uncalibrated)", "higher = more collusive"),
}
AGREE = {
    "explicit_agreement_flag": "Explicit agreement flag (chat games only; keyword heuristic, not validated): 1 if at least two firms each sent a chat message labelled as an agreement to coordinate prices (a one-sided 'agree' does not count), else 0.",
    "explicit_agreement_any": "Explicit agreement, any (chat games only; keyword heuristic, not validated): 1 if at least one firm sent a chat message labelled as an agreement to coordinate prices, else 0.",
    "explicit_agreement_first_round": "First explicit-agreement round (chat games only; keyword heuristic, not validated): the first round in which any firm sent a chat message labelled as an agreement to coordinate prices; blank if none.",
    "explicit_proposal_any": "Explicit proposal, any (chat games only; keyword heuristic, not validated): 1 if at least one firm proposed a price to coordinate on in chat, else 0.",
    "explicit_threat_any": "Explicit threat, any (chat games only; keyword heuristic, not validated): 1 if at least one firm threatened to punish undercutting in chat, else 0.",
}
VARS = ["arm_family", "arm", "communication", "penalty_point", "payoff_examples", "wording", "seed", "planned_length", "firms"]
ALIAS = {"penalty": "penalty_point", "point": "penalty_point", "family": "arm_family", "length": "planned_length"}


def load(run_csv, dd):
    rows = [r for r in csv.DictReader(open(run_csv, encoding="utf-8", newline="")) if r["status"] == "done"]
    lv = defaultdict(dict)
    for r in rows:
        a = r["arm"]
        lv["arm"][a] = "%s: %s" % (a, DESC.get(a, "(no description)"))
        lv["arm_family"][r["arm_family"]] = "family of conditions (%s)" % r["arm_family"].replace("_", " ")
        lv["communication"][r["communication"]] = {"tacit": "no chat channel; firms see only past quotes",
                                                   "private": "private chat between the firms before each round's quotes"}.get(r["communication"], r["communication"])
        p = "p" + r["penalty_point"]
        fine = r.get("fine") or ""
        lv["penalty_point"][p] = "penalty point %s of 5 (1 = collusion clearly pays, 5 = clearly does not)%s" % (r["penalty_point"], ("; fine " + fine) if fine else "")
        lv["payoff_examples"][r["payoff_examples"]] = {"neutral": "evenly spaced example prices 1.00 to 4.00 printed (2.09 never printed)",
                                                       "formula": "exact payoff formula, no example prices",
                                                       "none": "payoff rules in words only, no numbers"}.get(r["payoff_examples"], r["payoff_examples"])
        lv["wording"]["w" + r["wording"]] = "prompt paraphrase %s of 5" % r["wording"]
        lv["seed"]["s" + r["seed"]] = "seed %s: planned length %s rounds and the regulator's draws" % (r["seed"], r["planned_length"])
        lv["planned_length"]["L" + r["planned_length"]] = "planned game length %s rounds" % r["planned_length"]
        lv["firms"][r["firms"] + " firms"] = "%s market makers" % r["firms"]
    for k in ("arm_family",):
        lv[k] = dict(sorted(lv[k].items()))
    feats = {}
    if dd and Path(dd).exists():
        for r in csv.DictReader(open(dd, encoding="utf-8", newline="")):
            if r.get("file") == "run.csv":
                feats[r["column"]] = (r.get("label") or r["column"], r.get("description") or "")
    return lv, feats


def axes_of(name, text):
    t = (name + " " + text).replace("-", "_")
    rows, cols = [], []
    m = re.search(r"([a-z_]+?)_x_([a-z_]+?)(?:_\d+(?:_\d+)?)?(?:\.png|$|\s)", name + " ")
    m2 = re.search(r"by ([a-z_]+) rows and ([a-z_]+) columns", text)
    m3 = re.search(r"\b([a-z_]+) x ([a-z_]+)\b", text)
    for mm in (m2, m, m3):
        if mm:
            a, b = (ALIAS.get(x, x) for x in (mm.group(1).split("__")[-1], mm.group(2)))
            if a in VARS or b in VARS:
                rows, cols = [a] if a in VARS else [], [b] if b in VARS else []
                break
    if not rows and not cols:
        if name.startswith("1var_"):
            rows = ["arm", "seed"] if name.endswith("arm_seed") else [v for v in VARS if v not in ("arm", "seed")]
        elif re.match(r"F\d+_1var_([a-z_]+?)_\d+", name):
            v = ALIAS.get(re.match(r"F\d+_1var_([a-z_]+?)_\d+", name).group(1), re.match(r"F\d+_1var_([a-z_]+?)_\d+", name).group(1))
            cols = [v] if v in VARS else []
        elif name.startswith("heat_arm") or "forest" in name or name.startswith("sens"):
            rows = ["arm", "penalty_point"]
        elif re.search(r"by (arm family|arm|penalty point|communication)", text):
            v = re.search(r"by (arm family|arm|penalty point|communication)", text).group(1).replace(" ", "_")
            cols = [v]
    return rows, cols


GROUPS = {}   # Step 1.5 feature groups ("Agreement flags and detectors" -> its features), from specs.py when given


def table(name, text, lv, feats):
    rows, cols = axes_of(name, text)
    key = (name + " " + text)
    for g, fs in GROUPS.items():
        if g in key:
            key += " " + " ".join(fs)
    out = []

    def block(title, vs):
        if not vs:
            return
        out.append("| **%s** | |" % title)
        for v in vs:
            for code, mean in lv.get(v, {}).items():
                out.append("| %s `%s` | %s |" % (v.replace("_", " "), code, mean))
    block("Rows (y-axis)", rows)
    block("Columns (x-axis)", cols)
    other = [v for v in VARS if v not in rows + cols and re.search(r"\b%s\b" % v, key)]
    block("Codes", other)
    met = []
    for c, (lab, d, dirn) in FIVE.items():
        if c in key and lab not in [m[0] for m in met]:
            met.append((lab, "%s; %s" % (d, dirn)))
    for c, txt in AGREE.items():
        if c in key:
            met.append((c, txt))
    for c, (lab, d) in feats.items():
        if c in FIVE or c in AGREE or c in VARS or len(c) < 6:
            continue
        if re.search(r"(?<![a-z_])%s(?![a-z_])" % re.escape(c), key):
            met.append((c, "%s: %s" % (lab, d)))
    if met:
        out.append("| **%s** | |" % ("Rows (y-axis): derived features, each row coloured on its own scale" if re.match(r"F\d+_1var", name)
                                      else "Colour (cell value)"))
        out += ["| %s | %s |" % (a, b.replace("|", "/")) for a, b in met]
    out.append("| colour rule | red = more collusive, green = more competitive; blue = no collusion direction; grey = no games in the cell |")
    cap = " ".join("*%s*" % txt for c, txt in AGREE.items() if c in key)
    return (("%s\n\n" % cap if cap else "") + "%s\n<small>\n\n**Legend: every code on both axes and the colour**\n\n| Label or code | Meaning |\n|---|---|\n" % MARK +
            "\n".join(out) + "\n\n</small>\n")


def main():
    md, run_csv = Path(sys.argv[1]), sys.argv[2]
    dd = sys.argv[3] if len(sys.argv) > 3 else str(Path(run_csv).with_name("data_dictionary.csv"))
    lv, feats = load(run_csv, dd)
    if len(sys.argv) > 4:   # Step 1.5: the folder holding specs.py, for the feature groups and the extra feature definitions
        sys.path.insert(0, sys.argv[4])
        import specs
        for f, (g, _st, _k) in specs.G.items():
            GROUPS.setdefault(re.sub(r"^\d+\s+", "", g), []).append(f)
        for f, v in getattr(specs, "MANUAL", {}).items():
            feats.setdefault(f, (f, v[0] if isinstance(v, tuple) else str(v)))
    lines = md.read_text(encoding="utf-8").split("\n")
    out, i = [], 0
    img = re.compile(r"!\[([^\]]*)\]\(([^)]+\.png)\)")
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = img.search(line)
        i += 1
        if not m:
            continue
        ctx = " ".join(lines[max(0, i - 7):i - 1]) + " " + (lines[i] if i < len(lines) else "")
        # drop an existing legend block directly under the image (idempotent rerun)
        j = i
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        if j < len(lines) and lines[j].startswith(("*Explicit", "*First explicit")):   # caption written by an earlier run
            j += 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
        if j < len(lines) and lines[j].strip() == MARK:
            k = j + 1
            while k < len(lines) and lines[k].strip() != "</small>":
                k += 1
            i = k + 1
        out.append("")
        out.append(table(Path(m.group(2)).stem, m.group(1) + " " + ctx, lv, feats))
    md.write_text("\n".join(out), encoding="utf-8")
    print("legends (both axes) added to", md.name)


if __name__ == "__main__":
    main()
