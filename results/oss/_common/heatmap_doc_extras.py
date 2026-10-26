"""Owner rules for the gpt-oss Step 0.5 and Step 1.5 documents.

usage: python -X utf8 heatmap_doc_extras.py DOC.md RUN_CSV
1. Inserts the heat-map balance caveat right after the orientation paragraph (the first paragraph starting "**Orientation";
   else after the title).
2. Appends one appendix section on empty_talk_done_count: a technical covariate, not a collusion outcome, so it gets no maps,
   only a small diagnostic table (mean count, share of games with any, games) per arm x communication.
Idempotent (markers <!-- balance-caveat --> and <!-- empty-talk-appendix -->).
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oss_arm_labels import label  # noqa: E402

CAV = ("<!-- balance-caveat -->\n> **Reading the heat maps: the design is not a full Cartesian product.** Most arms are played at one penalty point and "
       "one communication condition only, and each seed is used with exactly one wording. A one-variable map (one input on its own) "
       "therefore averages over different mixes of cells for each level, so its means can be lopsided: a level can look high or low "
       "because of which arms happen to sit in it. Read every cell with its n, and prefer the two-variable maps or balanced slices "
       "(for example the headline cells, or one arm against its own control at the same point) before drawing a conclusion.\n")
APP_MARK = "<!-- empty-talk-appendix -->"


def main():
    md, run_csv = Path(sys.argv[1]), sys.argv[2]
    s = md.read_text(encoding="utf-8")
    if "<!-- balance-caveat -->" not in s:
        parts = s.split("\n\n")
        k = next((i for i, p in enumerate(parts) if p.lstrip().startswith("**Orientation")), 0)
        parts.insert(k + 1, CAV)
        s = "\n\n".join(parts)
    if APP_MARK not in s:
        g = defaultdict(list)
        for r in csv.DictReader(open(run_csv, encoding="utf-8", newline="")):
            if r["status"] == "done" and r.get("arm_build_bug") != "1" and r.get("empty_talk_done_count", "") != "":
                g[(r["arm"], r["communication"])].append(int(r["empty_talk_done_count"]))
        rows = sorted(g.items(), key=lambda kv: (kv[0][1], kv[0][0]))
        t = ["\n%s\n## Appendix: empty talk replies read as done (technical covariate, not a collusion outcome)\n" % APP_MARK,
             "gpt-oss-20b sometimes returns an empty chat reply; the engine option `empty_talk_as_done` (gpt-oss only) reads it as the firm "
             "saying nothing that turn. `empty_talk_done_count` counts such turns per game. It describes the model and the harness, not "
             "collusion, so it has no heat maps here; Step 2 uses it as a covariate (sensitivity: drop the games with a count above 0). "
             "Tacit games have no chat, so their count is always 0.\n",
             "<small>\n", "| Arm | Communication | Games | Mean count per game | Share of games with any |", "|---|---|---|---|---|"]
        for (arm, comm), v in rows:
            t.append("| %s | %s | %d | %.2f | %.2f |" % (label(arm), comm, len(v), sum(v) / len(v), sum(1 for x in v if x > 0) / len(v)))
        t += ["\n</small>\n"]
        s = s.rstrip() + "\n" + "\n".join(t)
    md.write_text(s, encoding="utf-8")
    print("balance caveat and empty-talk appendix in", md.name)


if __name__ == "__main__":
    main()
