"""Tests for conduct.py on small fixtures copied from real Track S stage0 shards (fixtures/t0 = Qwen3-14B thinking off,
fixtures/t1 = thinking on, one aborted shard). Run: python -X utf8 -m unittest experiments/p2-posthoc-2026-10-24/test_conduct.py"""
import hashlib, os, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import conduct  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def tree_hash(root):
    h = hashlib.sha256()
    for dp, _, fns in sorted(os.walk(root)):
        for fn in sorted(fns):
            h.update(fn.encode())
            h.update(open(os.path.join(dp, fn), "rb").read())
    return h.hexdigest()


class ConductTest(unittest.TestCase):
    def rows(self, *dirs):
        rows, aborted, warnings = conduct.score([os.path.join(FIX, d) for d in dirs])
        return {(r["arm"], r["thinking"], r["block"]): r for r in rows}, aborted, warnings

    def test_classes_thinking_off(self):
        rows, aborted, warnings = self.rows("t0")
        e2 = rows[("e2", "off", "seeds 1-4")]
        # each shard holds 4 runs (seeds 1-4). e2_p0_s1: 2.09 x4 (hold); e2_p2_s1: 2.08, 2.08, 1.50, 2.08
        self.assertEqual((e2["n"], e2["r1_hold"], e2["r1_onetick_2.08"], e2["r1_other_undercut"], e2["r1_competitive"]),
                         (8, 4, 3, 1, 0))
        # competitive_p0_s1 opens at 1.01, 1.00, 1.00, 1.01
        comp = rows[("competitive", "off", "seeds 1-4")]
        self.assertEqual((comp["n"], comp["r1_other_undercut"], comp["r1_competitive"], comp["r1_hold"], comp["war_free"]),
                         (4, 2, 2, 0, 0))
        self.assertEqual(aborted, [])
        self.assertEqual(warnings, [])

    def test_war_free_ci_and_quote_counts(self):
        rows, _, _ = self.rows("t0")
        e2 = rows[("e2", "off", "seeds 1-4")]
        self.assertEqual(e2["war_free"], 4)  # the four hold runs never undercut; every e2_p2_s1 run does
        self.assertEqual(e2["war_free_share"], "0.500")
        self.assertAlmostEqual(float(e2["r1_ci_mean"]), (4 * 0.545 + 3 * 0.54 + 0.25) / 8, places=3)
        self.assertEqual(e2["quotes_2.08_all_rounds"], 15)
        comp = rows[("competitive", "off", "seeds 1-4")]
        self.assertAlmostEqual(float(comp["r1_ci_mean"]), (2 * 0.005 + 0) / 4, places=2)

    def test_aborted_shard_and_truncation(self):
        rows, aborted, _ = self.rows("t1")
        r = rows[("e2", "on", "seeds 1-4")]
        self.assertEqual((r["n"], r["aborted"]), (1, 1))  # e2_p7_s2 completed, e2_p1_s2 has no run line
        self.assertEqual(r["truncated_calls"], 1)  # the aborted shard's one reply ended with finishReason=length
        self.assertEqual(len(aborted), 1)
        self.assertIn("HTTP 400", aborted[0][5])
        self.assertNotIn("http", aborted[0][5])  # urls are redacted

    def test_class_boundaries(self):
        c = conduct.classify
        self.assertEqual([c(2.09, 2.09, 1.0), c(2.5, 2.09, 1.0), c(2.08, 2.09, 1.0), c(2.07, 2.09, 1.0),
                          c(1.01, 2.09, 1.0), c(1.0, 2.09, 1.0)], ["hold", "hold", "onetick", "other", "other", "competitive"])

    def test_seed_blocks(self):
        self.assertEqual(conduct.block_of(4), "seeds 1-4")
        self.assertEqual(conduct.block_of(5), "seeds 5+")

    def test_read_only_and_outputs(self):
        before = tree_hash(FIX)
        with tempfile.TemporaryDirectory() as d:
            csvp, mdp = os.path.join(d, "c.csv"), os.path.join(d, "c.md")
            self.assertEqual(conduct.main([os.path.join(FIX, "t0"), os.path.join(FIX, "t1"), "--out-csv", csvp,
                                           "--out-md", mdp]), 0)
            head = open(csvp, encoding="utf8").readline().strip().split(",")
            self.assertEqual(head, conduct.FIELDS)
            self.assertIn("| e2 |", open(mdp, encoding="utf8").read())
        self.assertEqual(tree_hash(FIX), before)

    def test_span_recovered_from_data_not_hardcoded(self):
        import json
        lines = [json.loads(open(os.path.join(FIX, "t0", "e2_p0_s1.jsonl"), encoding="utf8").readline())]
        self.assertAlmostEqual(conduct.estimate_span(lines, 1.0), 2.0, places=2)
        self.assertEqual(conduct.read_s0(conduct.DEFAULT_SCENARIO), 1.0)


    def _write_shard(self, d, name, seeds, undercut_later):
        """Copy the real e2_p0_s1 run line (opens at 2.09), relabel its seed, optionally undercut in round 2."""
        import json
        base = json.loads(open(os.path.join(FIX, "t0", "e2_p0_s1.jsonl"), encoding="utf8").readline())
        with open(os.path.join(d, name), "w", encoding="utf8", newline="\n") as f:
            for sd in seeds:
                l = json.loads(json.dumps(base))
                l["seed"] = sd
                if undercut_later:
                    for a in l["rounds"][1]["agents"]:
                        if a["id"] == l["seat"]:
                            a["displayed"] = 1.5
                f.write(json.dumps(l) + "\n")

    def test_hold_then_undercut_is_not_war_free(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_shard(d, "e2_p0_s1.jsonl", [1, 2], True)
            rows, _, _ = conduct.score([d])
            r = rows[0]
            self.assertEqual((r["r1_hold"], r["war_free"], r["war_free_share"]), (2, 0, "0.000"))

    def test_seed_blocks_split_and_straddle(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_shard(d, "e2_p0_s3.jsonl", [3, 4, 5, 6], False)  # straddles the boundary
            self._write_shard(d, "e2_p1_s7.jsonl", [7, 8], False)
            rows, _, _ = conduct.score([d])
            by = {r["block"]: r["n"] for r in rows}
            self.assertEqual(by, {"seeds 1-4": 2, "seeds 5+": 4})

    def test_duplicates_across_roots_and_empty_root(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2, tempfile.TemporaryDirectory() as e:
            self._write_shard(d1, "e2_p0_s1.jsonl", [1, 2], False)
            self._write_shard(d2, "e2_p0_s1.jsonl", [1, 2], False)
            rows, _, warnings = conduct.score([d1, d2, e])
            self.assertEqual(rows[0]["n"], 2)
            self.assertEqual(sum("duplicate run skipped" in w for w in warnings), 2)
            self.assertTrue(any("no shard files found" in w for w in warnings))

    def test_truncated_final_line_and_empty_run_file(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_shard(d, "e2_p0_s1.jsonl", [1], False)
            with open(os.path.join(d, "e2_p0_s1.jsonl"), "a", encoding="utf8") as f:
                f.write('{"seed": 2, "rounds": [')  # cut off mid-write
            open(os.path.join(d, "e2_p1_s1.jsonl"), "w").close()  # empty run file = aborted
            rows, aborted, _ = conduct.score([d])
            self.assertEqual((rows[0]["n"], rows[0]["aborted"]), (1, 1))
            self.assertEqual(len(aborted), 1)


if __name__ == "__main__":
    unittest.main()
