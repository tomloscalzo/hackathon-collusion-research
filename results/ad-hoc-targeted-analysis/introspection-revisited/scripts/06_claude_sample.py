"""Blinded items for the second monitor (Claude readers): the answers and the chat of rounds 1-3 of the held-out (test) games of the
four in-game question arms, both models. Same frozen MONITOR instructions as the open-model monitor. Items are shuffled and given random
ids; the key (id -> game, channel) is written separately and must not be read by the readers.
Created by Claude at the prompting of the repository owner."""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0])
from common import WORK  # noqa: E402
from prompts import MONITOR_SYSTEM, CHANNEL  # noqa: E402

INGAME = ["r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public"]
req = {}
for x in open(WORK + "/requests.jsonl", encoding="utf8"):
    q = json.loads(x)
    if q["id"].startswith("G|"):
        req[q["id"]] = q
G = pd.read_csv(WORK + "/game_labels.csv")
t = G[G.arm.isin(INGAME) & (G.split == "test")]
items = []
for r in t.itertuples():
    for ch in ["answers", "chat"]:
        k = "G|%s|%s|%s" % (r.model, r.trial_id, ch)
        if k in req:
            items.append((k, r.model, ch, req[k]["messages"][1]["content"]))
rng = np.random.default_rng(99)
rng.shuffle(items)
key = []
batches = {}
for i, (k, model, ch, body) in enumerate(items):
    iid = "C%03d" % (i + 1)
    key.append(dict(item=iid, request_id=k, model=model, channel=ch))
    b = "%s_%s" % (ch, "g" if model == "gptoss" else "q")
    batches.setdefault(b, []).append((iid, body))
pd.DataFrame(key).to_csv(WORK + "/claude_key.csv", index=False)
import os
os.makedirs(WORK + "/claude_items", exist_ok=True)
for b, lst in batches.items():
    n = 0
    step = 20 if b == "chat_g" else 40
    for j in range(0, len(lst), step):
        n += 1
        with open("%s/claude_items/%s_%d.txt" % (WORK, b, n), "w", encoding="utf8") as f:
            for iid, body in lst[j:j + step]:
                f.write("=" * 20 + " ITEM %s " % iid + "=" * 20 + "\n" + body + "\n\n")
        print(b, n, len(lst[j:j + step]))
with open(WORK + "/claude_items/INSTRUCTIONS.txt", "w", encoding="utf8") as f:
    f.write(MONITOR_SYSTEM + "\n\nEach ITEM below is one game. Rate every item independently. Output one CSV line per item: item,probability\n")
