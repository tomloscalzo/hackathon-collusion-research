"""Tests for unit W2 (question_when / question_feedback): make_grid, lint_m and collect.
Run: python -X utf8 -m unittest tools/trial/test_watchdog_w2.py"""
import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import lint_m  # noqa: E402
import make_grid  # noqa: E402

DESIGN = Path(__file__).resolve().parent / "design" / "trackm_design.yaml"
PROMPTS = Path(__file__).resolve().parents[2] / "engine" / "src" / "main" / "resources" / "prompts"


def design():
    return yaml.safe_load(DESIGN.read_text(encoding="utf-8"))


class GridTest(unittest.TestCase):
    def test_wd_arms_have_the_declared_options_and_pairs(self):
        rows, _ = make_grid.expand(design(), None, make_grid.parse_global_options("payoff_examples=neutral"))
        for arm, notice, question in (("wd-noncomp", "watchdog_notice", "watchdog_explain"),
                                      ("wd-ask-noreport", "watchdog_notice_noreport", "watchdog_explain_noreport")):
            r = [x for x in rows if x["arm"] == arm]
            self.assertEqual(40, len(r))                                   # 20 pairs x 2 thinking modes
            self.assertEqual({"1"}, {str(x["penalty_point"]) for x in r})
            self.assertEqual({"private"}, {x["communication"] for x in r})
            self.assertEqual({"qwen3_32b_fp8"}, {x["model_profile"] for x in r})
            o = json.loads(r[0]["options"])
            self.assertEqual({"briefing_notice": notice, "question": question, "question_mode": "fed", "question_when": "non_competitive",
                              "question_feedback": "fed", "history_cap": 10, "payoff_examples": "neutral"}, o)
        pairs = {(x["wording"], x["seed"]) for x in rows if x["arm"] == "wd-noncomp"}
        ctl = {(x["wording"], x["seed"]) for x in rows if x["arm"] == "headline-chat" and str(x["penalty_point"]) == "1"}
        self.assertEqual(20, len(pairs))
        self.assertEqual(ctl, pairs)                                       # the same 20 pairs as the shared control

    def test_other_rows_do_not_carry_the_keys(self):
        rows, _ = make_grid.expand(design(), None, None)
        for x in rows:
            if not x["arm"].startswith("wd-"):
                self.assertNotIn("question_when", x["options"])
                self.assertNotIn("question_feedback", x["options"])

    def test_global_options_cannot_carry_them(self):
        for spec in ("question_when=non_competitive", "question_feedback=none", "payoff_examples=neutral,question_when=always"):
            with self.assertRaises(ValueError):
                make_grid.parse_global_options(spec)

    def test_an_arm_option_needs_a_question_and_a_valid_value(self):
        for opts in ({"question_when": "non_competitive"}, {"question_feedback": "fed"},
                     {"question": "confidant", "question_when": "sometimes"}, {"question": "confidant", "question_feedback": "saved"}):
            d = design()
            d["arms"] = [dict(a, options=opts) if a["name"] == "headline-chat" else a for a in d["arms"]]
            with self.assertRaises(ValueError, msg=str(opts)):
                make_grid.expand(d, None, None)
        d = design()
        d["arms"] = [dict(a, options={"question": "confidant", "question_when": "self_report_ge:3"}) if a["name"] == "headline-chat" else a
                     for a in d["arms"]]
        make_grid.expand(d, None, None)                                   # a valid value passes (the engine checks reply_extra)


class LintTest(unittest.TestCase):
    def setUp(self):
        self.texts, errs = lint_m.load_texts([PROMPTS / "seat_texts.json", PROMPTS / "questions.json"])
        self.assertEqual([], errs)

    def run_lint(self, texts=None, d=None):
        return lint_m.lint(texts or self.texts, d or design(), [], None)[0]

    def test_the_shipped_texts_and_design_pass(self):
        self.assertEqual([], self.run_lint())

    def test_the_approved_texts_are_the_design_texts_with_the_report_sentences_deleted(self):
        t = self.texts
        self.assertTrue(t["watchdog_notice"]["text"].startswith(t["watchdog_notice_noreport"]["text"]))
        self.assertTrue(t["watchdog_explain"]["text"].startswith(t["watchdog_explain_noreport"]["text"]))
        self.assertNotIn("regulator", t["watchdog_notice_noreport"]["text"])
        self.assertNotIn("regulator", t["watchdog_explain_noreport"]["text"])
        self.assertIs(t["watchdog_notice"]["true_statement"], False)
        self.assertIs(t["watchdog_notice"]["owner_approved_idle_notice"], True)
        self.assertIs(t["watchdog_explain"]["owner_approved_idle_notice"], True)
        self.assertNotIn("true_statement", t["watchdog_notice_noreport"])

    def test_an_untrue_question_needs_the_owner_flag(self):
        texts = copy.deepcopy(self.texts)
        del texts["watchdog_explain"]["owner_approved_idle_notice"]
        self.assertTrue(any("watchdog_explain" in f and "owner_approved_idle_notice" in f for f in self.run_lint(texts)))

    def test_the_flag_is_not_a_substitute_for_true_statement(self):
        texts = copy.deepcopy(self.texts)
        texts["watchdog_notice_noreport"]["owner_approved_idle_notice"] = True
        self.assertTrue(any("watchdog_notice_noreport" in f and "only for a text flagged true_statement false" in f for f in self.run_lint(texts)))
        texts = copy.deepcopy(self.texts)
        texts["watchdog_notice"]["owner_approved_idle_notice"] = "yes"
        self.assertTrue(any("must be true or false" in f for f in self.run_lint(texts)))

    def test_an_unflagged_untrue_notice_in_a_thinking_off_arm_still_fails(self):
        texts = copy.deepcopy(self.texts)
        del texts["watchdog_notice"]["owner_approved_idle_notice"]
        self.assertTrue(any("watchdog_notice" in f and "thinking off" in f for f in self.run_lint(texts)))

    def test_an_unused_untrue_question_fails(self):
        d = design()
        d["arms"] = [a for a in d["arms"] if a["name"] != "wd-noncomp"]
        self.assertTrue(any("watchdog_explain" in f and "no arm uses it" in f for f in self.run_lint(None, d)))

    def test_option_cells_are_checked(self):
        for opts, needle in (({"question": "confidant", "question_when": "sometimes"}, "question_when must be"),
                             ({"question_when": "non_competitive"}, "needs an in-game question"),
                             ({"question": "confidant", "question_feedback": "x"}, "question_feedback must be"),
                             ({"question": "confidant", "question_when": "self_report_ge:3"}, "needs a reply_extra"),
                             ({"question": "confidant", "question_when": "self_report_ge:9",
                               "reply_extra": {"name": "s", "kind": "integer", "min": 1, "max": 5, "text": "score_temptation_a"}}, "needs a reply_extra")):
            d = design()
            d["arms"] = d["arms"] + [{"name": "bad", "points": [1], "options": opts, "condition_texts": {"all": "private_chat"}}]
            self.assertTrue(any(needle in f for f in self.run_lint(None, d)), (opts, needle))
        d = design()
        d["arms"] = d["arms"] + [{"name": "ok", "points": [1], "condition_texts": {"all": "private_chat"},
                                  "options": {"question": "confidant", "question_when": "self_report_ge:3",
                                              "reply_extra": {"name": "s", "kind": "integer", "min": 1, "max": 5, "text": "score_temptation_a"}}}]
        self.assertEqual([], self.run_lint(None, d))


def quote(r, seat, q):
    return {"kind": "quote", "round": r, "seat": seat, "quote": q, "outcome": "OK"}


class CollectTest(unittest.TestCase):
    def make(self, tmp, name, params, evs):
        t = Path(tmp) / "trials" / name
        t.mkdir(parents=True)
        (t / "params.json").write_text(json.dumps(dict({"arm": name.split("__")[0], "thinking": "off", "competitive_price": 1.0}, **params)), encoding="utf-8")
        (t / "events.jsonl").write_text("".join(json.dumps(e) + chr(10) for e in evs), encoding="utf-8")
        (t / "DONE").write_text("attempts 1", encoding="utf-8")

    def test_asked_and_eligible_counts_and_the_round_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            evs = [quote(1, "a0", 2.0), quote(1, "a1", 2.0),
                   quote(2, "a0", 1.9), quote(2, "a1", 2.0),
                   {"kind": "watchdog_check", "round": 2, "seat": "a0", "eligible": True, "triggered": False, "asked": False},
                   {"kind": "watchdog_check", "round": 2, "seat": "a1", "eligible": True, "triggered": True, "asked": True},
                   {"kind": "question", "round": 2, "seat": "a1", "name": "x", "mode": "fed", "outcome": "OK", "parsed": {"message": "hi"}},
                   quote(3, "a0", 1.9), quote(3, "a1", 1.0),
                   {"kind": "watchdog_check", "round": 3, "seat": "a0", "eligible": True, "triggered": True, "asked": False},
                   {"kind": "watchdog_check", "round": 3, "seat": "a1", "eligible": False, "triggered": False, "asked": False}]
            self.make(tmp, "wd-noncomp__p1__w0__s1__t0", {"question_when": "non_competitive", "question_feedback": "fed"}, evs)
            self.make(tmp, "r2f-confidant__p1__w0__s1__t0", {}, [quote(1, "a0", 2.0)])
            out = Path(tmp) / "out"
            collect.collect(Path(tmp) / "trials", out)
            with open(out / "trials.csv", encoding="utf-8", newline="") as f:
                t = {r["arm"]: r for r in csv.DictReader(f)}
            w = t["wd-noncomp"]
            self.assertEqual(("non_competitive", "fed", "1", "3"), (w["question_when"], w["question_feedback"], w["asked_count"], w["eligible_count"]))
            o = t["r2f-confidant"]
            self.assertEqual(("", "", "", ""), (o["question_when"], o["question_feedback"], o["asked_count"], o["eligible_count"]))
            with open(out / "rounds.csv", encoding="utf-8", newline="") as f:
                r = {(x["trial_id"], x["round"], x["seat"]): x for x in csv.DictReader(f)}
            k = "wd-noncomp__p1__w0__s1__t0"
            self.assertEqual(("1", "0", "0"), (r[(k, "2", "a0")]["wd_eligible"], r[(k, "2", "a0")]["wd_triggered"], r[(k, "2", "a0")]["wd_asked"]))
            self.assertEqual(("1", "1", "1"), (r[(k, "2", "a1")]["wd_eligible"], r[(k, "2", "a1")]["wd_triggered"], r[(k, "2", "a1")]["wd_asked"]))
            self.assertEqual(("1", "1", "0"), (r[(k, "3", "a0")]["wd_eligible"], r[(k, "3", "a0")]["wd_triggered"], r[(k, "3", "a0")]["wd_asked"]))
            self.assertEqual("", r[(k, "1", "a0")]["wd_eligible"])           # round 1: no check
            # the question event of the asked round is still one questions.csv row, and a check event is not a call
            with open(out / "questions.csv", encoding="utf-8", newline="") as f:
                self.assertEqual(1, len(list(csv.DictReader(f))))


    def test_always_has_no_checks_so_the_counts_stay_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make(tmp, "wd-always__p1__w0__s1__t0", {"question_when": "always"}, [quote(1, "a0", 2.0), quote(2, "a0", 2.0)])
            out = Path(tmp) / "out"
            collect.collect(Path(tmp) / "trials", out)
            with open(out / "trials.csv", encoding="utf-8", newline="") as f:
                w = next(csv.DictReader(f))
            self.assertEqual(("always", "", ""), (w["question_when"], w["asked_count"], w["eligible_count"]))


if __name__ == "__main__":
    unittest.main()
