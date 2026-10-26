"""Draw the 30-passage blind validation sample for the concealment keyword (seeded). Writes validation_key.csv (committed) and
the blind reader file validation_blind.json (to the scratch dir given by --blind-out). Usage: python -X utf8 validation_sample.py --passages P --blind-out F"""
import argparse, csv, json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measures as M
csv.field_size_limit(10**9)
ap = argparse.ArgumentParser(); ap.add_argument("--passages", required=True); ap.add_argument("--blind-out", required=True); a = ap.parse_args()
rows = [r for r in csv.DictReader(open(a.passages, encoding="utf-8")) if r["arm"].startswith("wd-")]
rng = random.Random(20261026)
strict = [r for r in rows if M.CONCEAL_STRICT.search(r["text"])]
subtle = [r for r in rows if not M.CONCEAL_STRICT.search(r["text"]) and M.CONCEAL_SUBTLE.search(r["text"]) and not M.CONCEAL_CAUGHT.search(r["text"])]
caught = [r for r in rows if not M.CONCEAL_STRICT.search(r["text"]) and M.CONCEAL_CAUGHT.search(r["text"]) and not M.CONCEAL_SUBTLE.search(r["text"])]
non = [r for r in rows if not M.CONCEAL.search(r["text"]) and M.REGULATOR.search(r["text"])]
def pick(pool, k):
    out = []
    for model in ("gpt-oss-20b", "Qwen3-32B (thinking on)"):
        p = [r for r in pool if r["model"] == model]; rng.shuffle(p); out += p[: k // 2]
    return out
sel = [("strict", r) for r in pick(strict, 8)] + [("subtle-only", r) for r in pick(subtle, 6)] + [("caught-only", r) for r in pick(caught, 6)] + [("non-hit", r) for r in pick(non, 10)]
rng.shuffle(sel)
key, blind = [], []
for i, (stratum, r) in enumerate(sel, 1):
    t = r["text"]; windowed = 0
    if len(t) > 1800:
        m = M.CONCEAL.search(t); c = m.start() if m else 0; s = max(0, c - 900); t = t[s:s + 1800]; windowed = 1
    pid = "P%02d" % i
    blind.append(dict(id=pid, text=t))
    key.append(dict(id=pid, stratum=stratum, model=r["model"], arm=r["arm"], channel=r["channel"], trial_id=r["trial_id"], round=r["round"], windowed=windowed, keyword_hit=int(bool(M.CONCEAL.search(r["text"]))), strict_hit=int(bool(M.CONCEAL_STRICT.search(r["text"])))))
json.dump(blind, open(a.blind_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
with open(Path(__file__).resolve().parent / "validation_key.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(key[0])); w.writeheader(); w.writerows(key)
print(len(key), {s: sum(1 for k in key if k["stratum"] == s) for s in ("strict", "subtle-only", "caught-only", "non-hit")})
