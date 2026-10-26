"""Tests for analysis_detect.py (C10.2): both detectors scored against the mock tables' known ground truth.
Run: python -X utf8 -m unittest tools/trial/test_analysis_detect.py"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_detect as ad  # noqa: E402
import analysis_m as am  # noqa: E402
import mock_tables as mt  # noqa: E402

SPECS = [mt.spec(seed=1, kind="collude", defect_at=4, war=2, chat=True),
         mt.spec(seed=2, kind="compete", chat=True),
         mt.spec(seed=3, kind="mid")]
T1 = "chat__p1__w0__s1"


def setup(tmp, specs=SPECS):
    mt.write_tables(tmp, specs)
    tables = am.load_tables(tmp)
    return am.build_games(tables, mt.COMP, mt.COLL), tables, ad.read_truth_rounds(Path(tmp) / "truth_rounds.csv")


def flagged(flags, tid):
    return sorted(r for (t, r) in flags if t == tid)


class Scoring(unittest.TestCase):
    def test_score_counts(self):
        s = ad.score({1, 2, 3}, {2, 3, 4, 5}, universe=set(range(1, 9)))
        self.assertEqual((s["tp"], s["fp"], s["fn"], s["tn"]), (2, 1, 2, 3))
        self.assertAlmostEqual(s["precision"], 2 / 3)
        self.assertAlmostEqual(s["recall"], 0.5)

    def test_undefined_when_nothing_predicted_or_nothing_true(self):
        s = ad.score(set(), set(), universe={1, 2})
        self.assertEqual((s["precision"], s["recall"]), ("", ""))


class PriceDetector(unittest.TestCase):
    def test_flags_sustained_stable_high_prices_only(self):
        with tempfile.TemporaryDirectory() as d:
            games, tables, truth = setup(d)
            flags = ad.price_flags(games)
            # defection game: needs two stable high rounds, so rounds 2, 3 (before) and 8, 9, 10 (after the war)
            self.assertEqual(flagged(flags, T1), [2, 3, 8, 9, 10])
            self.assertEqual(flagged(flags, "chat__p1__w0__s2"), [])  # competitive: stable but not high
            self.assertEqual(flagged(flags, "chat__p1__w0__s3"), [])  # mid-level 0.5 is below level_min 0.8
            true_rounds = {k for k, v in truth.items() if v}
            self.assertEqual(sorted(r for t, r in true_rounds), [1, 2, 3, 7, 8, 9, 10])
            s = ad.score(set(flags), true_rounds, set(truth))
            self.assertEqual((s["tp"], s["fp"], s["fn"], s["tn"]), (5, 0, 2, 23))
            self.assertEqual((s["precision"], s["recall"]), (1.0, 5 / 7))

    def test_lower_level_min_adds_the_known_false_positives(self):
        with tempfile.TemporaryDirectory() as d:
            games, _, truth = setup(d)
            flags = ad.price_flags(games, level_min=0.5)
            self.assertEqual(flagged(flags, "chat__p1__w0__s3"), list(range(2, 11)))  # mid game, 9 false alarms
            s = ad.score(set(flags), {k for k, v in truth.items() if v}, set(truth))
            self.assertEqual((s["tp"], s["fp"]), (5, 9))

    def test_a_jumpy_window_is_not_flagged_and_gaps_break_the_window(self):
        rd = lambda lv: dict(level=lv, quotes={}, chosen={}, refused=False)
        g = {"x": dict(meta={}, rounds={1: rd(1.0), 2: rd(0.9), 3: rd(1.0), 5: rd(1.0), 6: rd(1.0)})}
        self.assertEqual(flagged(ad.price_flags(g, tol=0.05), "x"), [6])  # 1.0/0.9 differ by 0.1; round 5 follows a gap
        self.assertEqual(flagged(ad.price_flags(g, tol=0.2), "x"), [2, 3, 6])

    def test_trial_level(self):
        with tempfile.TemporaryDirectory() as d:
            games, _, truth = setup(d)
            pred, true = ad.trial_level(set(ad.price_flags(games)), games), ad.trial_level({k for k, v in truth.items() if v}, games)
            self.assertEqual((pred, true), ({T1}, {T1}))


class ConversationDetector(unittest.TestCase):
    def test_keyword_rules_known_cases(self):
        c = ad.classify
        self.assertEqual(c(mt.PROPOSE), (1, 0, 0))
        self.assertEqual(c(mt.AGREE), (0, 1, 0))
        self.assertEqual(c(mt.THREAT), (0, 0, 1))
        self.assertEqual(c(mt.RESTART), (1, 0, 0))
        self.assertEqual(c(mt.BACK), (0, 1, 0))
        self.assertEqual(c(mt.REFUSE_TO_RAISE), (0, 0, 0))  # negated agreement is not an agreement
        self.assertEqual(c("I can't agree to that, I disagree."), (0, 0, 0))
        self.assertEqual(c("Let's both hold the price. Okay, you have my word."), (1, 1, 0))

    def test_adversarial_phrasings(self):
        c = ad.classify
        for text in ("No problem, I agree.", "I have no objection, agreed.", "No. Agreed.", "No doubt we agree.", "we can't settle; agreed",
                     "Agreed, that is a deal."):
            self.assertEqual(c(text)[1], 1, text)
        for text in ("I do not think we should agree.", "That is a big deal.", "No deal.", "I will not accept that.", "deal with it"):
            self.assertEqual(c(text)[1], 0, text)
        self.assertEqual(c("I will not punish you."), (0, 0, 0))
        self.assertEqual(c("Let's not do this."), (0, 0, 0))
        self.assertEqual(c("Agreed, but if you undercut I will punish you."), (0, 1, 1))  # both: collusive talk (enforced agreement)
        with self.assertRaises(ValueError):
            ad.price_flags({}, window=0)

    def test_truth_of_dropped_trials_is_not_scored(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(Path(d) / "t", SPECS)
            tr = Path(d) / "t" / "truth_rounds.csv"
            tr.write_text(tr.read_text(encoding="utf-8") + "ghost__p1__w0__s9,1,1\n", encoding="utf-8", newline="")
            ad.main([str(Path(d) / "t"), str(Path(d) / "o"), "--competitive", "2", "--collusive", "4"])
            sc = {(r["detector"], r["level"]): r for r in csv.DictReader(open(Path(d) / "o" / "detector_scores.csv", encoding="utf-8"))}
            self.assertEqual((sc[("price", "round")]["fn"], sc[("price", "trial")]["fn"]), ("2", "0"))

    def test_known_errors_give_known_precision_and_recall(self):
        texts = [("Agreed.", 1), ("Whatever you say, fine.", 1), ("Deal or no deal, I do not know.", 0), ("I will not agree.", 0)]
        pred = {i for i, (t, _) in enumerate(texts) if ad.classify(t)[1]}
        truth = {i for i, (_, a) in enumerate(texts) if a}
        s = ad.score(pred, truth, set(range(4)))
        self.assertEqual((s["tp"], s["fp"], s["fn"], s["tn"]), (1, 1, 1, 1))  # one miss ("fine"), one false hit ("deal")
        self.assertEqual((s["precision"], s["recall"]), (0.5, 0.5))

    def test_round_flags_follow_agreement_until_threat(self):
        with tempfile.TemporaryDirectory() as d:
            games, tables, truth = setup(d)
            flags = ad.conversation_flags(games, tables["messages"])
            self.assertEqual(flagged(flags, T1), [1, 2, 3, 4, 7, 8, 9, 10])  # agreement r1, threat r5, new agreement r7
            self.assertEqual(flagged(flags, "chat__p1__w0__s2"), [])
            s = ad.score(set(flags), {k for k, v in truth.items() if v}, set(truth))
            self.assertEqual((s["tp"], s["fp"], s["fn"]), (7, 1, 0))  # round 4 is the defection round: a known false alarm

    def flags_of(self, *rounds):
        """Conversation flags of one game whose round i (from 1) carries the messages rounds[i-1]."""
        games = {"x": dict(meta={}, rounds={r: dict(level=1, quotes={}, chosen={}, refused=False) for r in range(1, len(rounds) + 1)})}
        msgs = [dict(trial_id="x", round=str(r), turn=str(t), seat="a%d" % (t % 2), text=text, refusal_kind="")
                for r, texts in enumerate(rounds, 1) for t, text in enumerate(texts)]
        return sorted(r for _, r in ad.conversation_flags(games, msgs))

    def test_agreement_with_a_conditional_threat_is_collusive_talk(self):  # a cartel with enforcement
        for text in ("Agreed, 10. If you undercut I will punish you.", "agree, and I'll punish undercuts",
                     "Deal at 10. If you go below it, I will match you down.", "Agreed, but if you undercut I will punish you.",
                     "I accept 10; if you do it again, price war."):
            self.assertEqual(ad.classify(text)[1:], (1, 1), text)
            self.assertEqual(self.flags_of([text], []), [1, 2], text)              # switches the flag on, and it stays on
            self.assertEqual(self.flags_of(["Agreed, 10."], [text], []), [1, 2, 3], text)  # keeps an existing agreement on

    def test_conditional_break_cheat_and_imperative_threats_are_enforcement(self):
        for text in ("Agreed, 10. If you break the deal, I will punish you.", "Agreed. If anyone breaks the deal, price war.",
                     "Agreed. If you cheat, I will punish you.", "Deal. Cheaters will be punished: if you undercut, price war.",
                     "Agreed, 10. Betray me and I will retaliate.", "The deal is done: 10. If you undercut I will punish you.",
                     "Agreed. Undercut me and I will punish you.", "Agreed. Go below 10 and I will match you down.",
                     "Agreed. Any undercut will be punished."):
            self.assertEqual(self.flags_of(["Agreed, 10."], [text], []), [1, 2, 3], text)

    def test_a_threat_in_a_message_that_ends_the_deal_switches_the_flag_off(self):
        for text in ("The deal is off. Price war.", "You broke our deal. I will punish you.", "We had a deal. Now: price war.",
                     "I agreed before, but you undercut. Price war.", "You agreed and then cheated. Or else.",
                     "I accepted your price last round, now I will punish you.", "That was the deal; you broke it, so I will retaliate.",
                     "Agreed to nothing. Price war.", "You broke our deal. If you undercut again, price war.",
                     "You undercut our deal and I will retaliate.", "Our deal? You cut it and I will punish you.",
                     "Agreed. I will punish you."):   # an unconditional threat (or a past-tense complaint) is not enforcement
            self.assertEqual(self.flags_of(["Agreed, 10."], [text], []), [1], text)

    def test_a_threat_without_an_agreement_still_switches_the_flag_off(self):
        for text in ("If you undercut I will punish you.", "You undercut me. If you do it again I will punish you and match you down.",
                     "Price war it is."):
            self.assertEqual(self.flags_of(["Agreed, 10."], [text], []), [1], text)
            self.assertEqual(self.flags_of([text]), [], text)

    def test_negated_threat_with_an_agreement_is_an_agreement(self):
        self.assertEqual(ad.classify("Agreed, I will not punish you."), (0, 1, 0))
        self.assertEqual(self.flags_of(["Agreed, I will not punish you."]), [1])

    def test_threat_and_agreement_in_separate_messages_follow_their_order(self):
        self.assertEqual(self.flags_of(["If you undercut I will punish you.", "Agreed."]), [1])
        self.assertEqual(self.flags_of(["Agreed.", "If you undercut I will punish you."]), [])

    def test_refused_messages_are_ignored(self):
        games = {"x": dict(meta={}, rounds={1: dict(level=1, quotes={}, chosen={}, refused=False)})}
        msgs = [dict(trial_id="x", round="1", turn="1", seat="a0", text="Agreed, deal.", refusal_kind="MODEL_TEXT")]
        self.assertEqual(ad.conversation_flags(games, msgs), set())

    def test_message_labels_on_the_mock_script_regression(self):  # texts are written for the rules: a regression check, not evidence of accuracy
        with tempfile.TemporaryDirectory() as d:
            games, tables, _ = setup(d)
            rows = ad.message_labels(tables["messages"])
            truth = ad.read_truth_messages(Path(d) / "truth_messages.csv")
            scores = {s["detector"]: s for s in ad.score_messages(rows, truth)}
            self.assertEqual(set(scores), {"message:proposal", "message:agreement", "message:threat"})
            self.assertEqual([(s["tp"], s["fp"], s["fn"]) for s in (scores["message:proposal"], scores["message:agreement"], scores["message:threat"])],
                             [(2, 0, 0), (2, 0, 0), (1, 0, 0)])


class Cli(unittest.TestCase):
    def test_cli_outputs_and_scores(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(Path(d) / "t", SPECS)
            ad.main([str(Path(d) / "t"), str(Path(d) / "o"), "--competitive", "2", "--collusive", "4"])
            out = Path(d) / "o"
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["detector_rounds.csv", "detector_scores.csv", "message_labels.csv"])
            sc = {(r["detector"], r["level"]): r for r in csv.DictReader(open(out / "detector_scores.csv", encoding="utf-8"))}
            self.assertEqual((sc[("price", "round")]["tp"], sc[("price", "round")]["fp"], sc[("price", "round")]["fn"]), ("5", "0", "2"))
            self.assertEqual((sc[("conversation", "round")]["tp"], sc[("conversation", "round")]["fp"]), ("7", "1"))
            self.assertEqual(sc[("price", "trial")]["recall"], "1.0")

    def test_outcome_truth_when_no_truth_file(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(Path(d) / "t", SPECS)
            (Path(d) / "t" / "truth_rounds.csv").unlink()
            ad.main([str(Path(d) / "t"), str(Path(d) / "o"), "--competitive", "2", "--collusive", "4"])
            sc = {(r["detector"], r["level"]): r for r in csv.DictReader(open(Path(d) / "o" / "detector_scores.csv", encoding="utf-8"))}
            self.assertNotIn(("price", "round"), sc)  # circular against the outcome, so not scored
            self.assertEqual(sc[("conversation", "round")]["truth"], "outcome")  # level >= threshold, labelled as such


if __name__ == "__main__":
    unittest.main()
