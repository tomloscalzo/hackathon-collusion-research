import csv, sys, collections
rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
keys = ["N","phi","tick","slope","rhoTip","pEvidence","fineRatio","sBarRatio"]
print("deltas", sorted(set(r["delta"] for r in rows)))
for k in keys: print(k, sorted(set(r[k] for r in rows)))
by = collections.defaultdict(dict)
for r in rows: by[tuple(r[k] for k in keys)][r["delta"]] = r
flips = []
for key, d in by.items():
    a, b = d.get("0.8"), d.get("0.99")
    if a and b and float(a["theta_star"]) > 0 and float(b["theta_star"]) <= 0:
        flips.append((key, a, b))
print("flips", len(flips))
cnt = collections.Counter()
for key, a, b in flips:
    cnt[(a["regime"], b["regime"])] += 1
print(cnt)
# characterize flips by params
for i,k in enumerate(keys):
    print(k, collections.Counter(f[0][i] for f in flips))
show = ["cell","theta_hat","theta_star","theta_star_given_participation","regime","w_star","w0","ripeness_E","p_trigger_star","expected_duration"]
for key, a, b in flips[:6]:
    print(dict(zip(keys,key)))
    print("  0.8 ", {k:a[k] for k in show})
    print("  0.99", {k:b[k] for k in show})
