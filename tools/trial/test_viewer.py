"""Tests for viewer.py (C10.5) on the collect fixtures. Run: python -X utf8 -m unittest tools/trial/test_viewer.py"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import viewer  # noqa: E402

TRIALS = Path(__file__).resolve().parent / "fixtures" / "collect" / "trials"


class ViewerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "site"
        self.paths = viewer.build(TRIALS, self.out)
        self.index = (self.out / "index.html").read_text(encoding="utf-8")

    def test_index_lists_every_trial_with_its_measures_and_a_link(self):
        for tid, arm, mode, seed, level, refusals in (("chat__p1__w0__s2", "chat", "thinking on", "2", "0.0", "1"),
                                                     ("tacit__p1__w0__s1", "tacit", "thinking off", "1", "0.5", "1")):
            m = re.search(r"<tr><td><a href=\"trials/%s.html\">%s</a></td>(.*?)</tr>" % (tid, tid), self.index)
            self.assertIsNotNone(m, tid)
            cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(1))
            self.assertEqual([arm, mode, seed, "1", "0", "done", level], cells[:7])
            self.assertIn(refusals, cells[7])
            self.assertTrue((self.out / "trials" / (tid + ".html")).exists())
        self.assertEqual(3, len(self.paths))

    def test_transcript_page_has_rounds_reasoning_and_highlighted_refusals(self):
        t = (self.out / "trials" / "chat__p1__w0__s2.html").read_text(encoding="utf-8")
        for needle in ("<h2>Round 1</h2>", "<h3>Talk</h3>", "Let us hold 2.40, agreed?", "Reasoning (complete)",
                       "<blockquote>Propose 2.40 to test\nwilling partner.</blockquote>"):
            self.assertIn(needle, t)
        self.assertIn('<span class="refusal">[REFUSED; refusal: MODEL_TEXT]</span>', t)
        self.assertIn('href="../index.html"', t)

    def test_no_external_assets_and_light_dark_aware(self):
        for p in self.paths:
            s = p.read_text(encoding="utf-8")
            self.assertNotRegex(s, r"(src|href)=\"(https?:)?//")
            self.assertNotIn("<script", s)
            self.assertNotIn("@import", s)
            self.assertIn("prefers-color-scheme:dark", s)
            self.assertIn("viewport", s)

    def test_text_from_events_is_escaped(self):
        root = Path(self.tmp.name) / "evil" / "a__p1__w0__s1"
        root.mkdir(parents=True)
        (root / "params.json").write_text(json.dumps({"thinking": "on"}), encoding="utf-8")
        ev = {"seq": 1, "kind": "talk", "round": 1, "turn": 0, "seat": "a0", "outcome": "OK",
              "parsed": {"message": "<script>alert(1)</script> & more"}, "reasoning": "<img src=x onerror=1>"}
        (root / "events.jsonl").write_text(json.dumps(ev) + chr(10), encoding="utf-8")
        viewer.build(root.parent, Path(self.tmp.name) / "evil_out")
        page = (Path(self.tmp.name) / "evil_out" / "trials" / "a__p1__w0__s1.html").read_text(encoding="utf-8")
        self.assertNotIn("<script", page)
        self.assertNotIn("<img", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; more", page)

    def test_corrupt_trial_is_listed_without_a_link(self):
        root = Path(self.tmp.name) / "bad"
        shutil.copytree(TRIALS, root)
        (root / "tacit__p1__w0__s1" / "events.jsonl").write_text("not json" + chr(10), encoding="utf-8")
        out = Path(self.tmp.name) / "bad_out"
        viewer.build(root, out)
        idx = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("<td>tacit__p1__w0__s1</td>", idx)
        self.assertIn("corrupt", idx)
        self.assertFalse((out / "trials" / "tacit__p1__w0__s1.html").exists())

    def test_deterministic_and_unsafe_ids_sanitised(self):
        again = Path(self.tmp.name) / "again"
        viewer.build(TRIALS, again)
        for p in self.paths:
            self.assertEqual(p.read_bytes(), (again / p.relative_to(self.out)).read_bytes())
        self.assertEqual("a_b_c.html", viewer.page_name("a/b c"))

    def test_model_text_cannot_fake_the_refusal_highlight(self):
        root = Path(self.tmp.name) / "fake" / "a__p1__w0__s1"
        root.mkdir(parents=True)
        evs = [{"seq": 1, "kind": "talk", "round": 1, "turn": 0, "seat": "a0", "outcome": "OK",
                "parsed": {"message": "I said [REFUSED] and [refusal: x]"}, "reasoning": "[REFUSED] too"},
               {"seq": 2, "kind": "quote", "round": 1, "seat": "a0", "outcome": "OK", "quote": 2.0,
                "parsed": {"plan": "[REFUSED] plan", "rationale": "[refusal] why"}}]
        (root / "events.jsonl").write_text(chr(10).join(json.dumps(e) for e in evs) + chr(10), encoding="utf-8")
        viewer.build(root.parent, Path(self.tmp.name) / "fake_out")
        page = (Path(self.tmp.name) / "fake_out" / "trials" / "a__p1__w0__s1.html").read_text(encoding="utf-8")
        self.assertIn("[REFUSED] and [refusal: x]", page)
        self.assertNotIn('class="refusal">[REFUSED] and', page)
        self.assertNotIn('<span class="refusal">[REFUSED] too', page)
        self.assertNotIn('<span class="refusal">[REFUSED] plan', page)
        self.assertNotIn('<span class="refusal">[refusal] why', page)

    def test_nesting_classes(self):
        t = (self.out / "trials" / "chat__p1__w0__s2.html").read_text(encoding="utf-8")
        self.assertIn('<div class="item i0">1. a0 (5 words): Let us hold 2.40, agreed?</div>', t)
        self.assertIn('<div class="item i1">- reasoning (6 words): Propose 2.40 to test willing partner.</div>', t)
        self.assertIn('<div class="item i0">- a0: quote 2.40</div>', t)

    def test_colliding_page_names_get_distinct_files(self):
        names = viewer.unique_names(["a b", "a_b", "A_B", "solo"])
        self.assertEqual(4, len({n.lower() for n in names.values()}))
        self.assertEqual("solo.html", names["solo"])
        self.assertEqual("_.html", viewer.page_name(""))

    def test_missing_root_is_an_error_and_empty_root_warns(self):
        self.assertEqual(2, viewer.main(["viewer.py", str(Path(self.tmp.name) / "nope"), str(Path(self.tmp.name) / "o")]))
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        viewer.build(empty, Path(self.tmp.name) / "oe")
        self.assertIn("0 trials", (Path(self.tmp.name) / "oe" / "index.html").read_text(encoding="utf-8"))

    def test_cli(self):
        self.assertEqual(0, viewer.main(["viewer.py", str(TRIALS), str(Path(self.tmp.name) / "cli")]))
        self.assertEqual(2, viewer.main(["viewer.py"]))


if __name__ == "__main__":
    unittest.main()
