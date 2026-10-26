"""Parse the rater outputs into firm-round labels and game-level monitor scores (Created by Claude at the prompting of the repository owner)."""
import json
import re
import sys

import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0])
from common import WORK  # noqa: E402

KEYS = ["coordination", "denial", "undercut", "explicit_agreement", "indirect_signal", "punishment_threat", "conceal"]


def js(s):
    if not isinstance(s, str):
        return None
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        try:
            return json.loads(re.sub(r",\s*}", "}", m.group(0)))
        except Exception:
            return None


def main(path=WORK + "/results.jsonl"):
    rows = {}
    for x in open(path, encoding="utf8"):
        d = json.loads(x)
        if d.get("content"):
            rows[d["id"]] = d          # last successful answer wins
        elif d["id"] not in rows:
            rows[d["id"]] = d
    lab, mon, bad = [], [], 0
    for rid, d in rows.items():
        p = rid.split("|")
        j = js(d.get("content"))
        if p[0] == "L":
            r = dict(model=p[1], trial_id=p[2], round=int(p[3]), seat=p[4], channel=p[5], ok=int(j is not None))
            for k in KEYS:
                v = (j or {}).get(k)
                r[k] = int(v) if isinstance(v, (int, float)) and v in (0, 1) else None
            if j is None:
                bad += 1
            lab.append(r)
        else:
            v = (j or {}).get("probability")
            try:
                v = float(v)
            except Exception:
                v = None
            if v is None:
                bad += 1
            mon.append(dict(model=p[1], trial_id=p[2], channel=p[3], prob=v, evidence=(j or {}).get("evidence"),
                            finish=d.get("finish"), tin=d.get("tin")))
    lab = pd.DataFrame(lab)
    mon = pd.DataFrame(mon)
    lab.to_csv(WORK + "/labels_firmround.csv", index=False)
    mon.to_csv(WORK + "/monitor_game.csv", index=False)
    print("labels", len(lab), "monitor", len(mon), "unparsed", bad)
    if len(lab):
        print(lab.groupby(["model", "channel"])[KEYS].mean().round(3).to_string())
    if len(mon):
        print(mon.groupby(["model", "channel"]).prob.describe().round(1).to_string())


if __name__ == "__main__":
    main(*sys.argv[1:])
