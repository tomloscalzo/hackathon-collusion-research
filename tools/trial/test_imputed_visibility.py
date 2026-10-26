"""fix-imputed_visibility (first live Track M smoke): imputed rounds are shown next to refusals, the raw text of an
imputed call never reaches a table or the viewer, and an empty window basis is a clear error, not a matplotlib crash.
Run: python -X utf8 -m unittest tools/trial/test_imputed_visibility.py"""
import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_headline as ah  # noqa: E402
import analysis_m as am  # noqa: E402
import analysis_r as ar  # noqa: E402
import collect  # noqa: E402
import derive  # noqa: E402
import viewer  # noqa: E402

SECRET = "SECRET-REASONING-CANARY"   # stands for the private reasoning inside an unclosed <think>
COMP, COLL = 2.0, 4.0


def rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_trial(root, tid, events, thinking="on"):
    d = Path(root) / tid
    d.mkdir(parents=True)
    (d / "params.json").write_text(json.dumps({"thinking": thinking, "competitive_price": COMP, "collusive_price": COLL,
                                               "prompt_fingerprint": "fp", "code_commit": "abc"}), encoding="utf-8")
    seq = [dict(e, seq=i + 1) for i, e in enumerate(events)]
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in seq), encoding="utf-8")
    (d / "DONE").write_text("attempts 1\n", encoding="utf-8")
    return d


def game(rounds=4, cut_talk=(2,), cut_quote=(3,), refuse_quote=(), cut_question=(), post_cut=()):
    """A two-seat chat game: seat a's talk in `cut_talk` rounds is a truncated thinking reply (raw think text in reply),
    its quote in `cut_quote` rounds is imputed (TRUNCATED), b's quote in `refuse_quote` rounds is refused."""
    ev = []
    for r in range(1, rounds + 1):
        if r in cut_talk:
            ev.append({"kind": "talk", "round": r, "turn": 0, "seat": "a", "outcome": "IMPUTED", "refusal_kind": "TRUNCATED",
                       "truncated": True, "truncated_thinking": True, "finish_reason": "length", "word_capped": False,
                       "reply": "<think>" + SECRET + " let me plan the price fixing", "parsed": {"done": True}})
        else:
            ev.append({"kind": "talk", "round": r, "turn": 0, "seat": "a", "outcome": "OK", "word_capped": False,
                       "parsed": {"message": "hold 3.5", "done": False}})
        ev.append({"kind": "talk", "round": r, "turn": 1, "seat": "b", "outcome": "OK", "word_capped": False,
                   "parsed": {"message": "", "done": True}})
        for seat in ("a", "b"):
            e = {"kind": "quote", "round": r, "seat": seat, "quote": 3.0, "outcome": "OK"}
            if seat == "a" and r in cut_quote:
                e.update(outcome="IMPUTED", refusal_kind="TRUNCATED", imputed=True, truncated_thinking=True, quote=2.0)
            if seat == "b" and r in refuse_quote:
                e.update(outcome="REFUSED", refusal_kind="MODEL_TEXT", imputed=True, quote=2.0, refusal_pattern="i can't")
            ev.append(e)
        ev.append({"kind": "market", "round": r, "prices": {"a": 3.0, "b": 3.0}, "profits": {"a": 1.0, "b": 1.0},
                   "winner": None, "market_price": 3.0})
        if r in cut_question:
            ev.append({"kind": "question", "round": r, "seat": "b", "name": "confidant", "mode": "fed", "outcome": "TRUNCATED",
                       "refusal_kind": "TRUNCATED", "truncated": True, "truncated_thinking": True,
                       "reply": "<think>" + SECRET})
        if r in post_cut:
            ev.append({"kind": "question", "round": r, "seat": "b", "name": "public", "mode": "post", "outcome": "TRUNCATED",
                       "refusal_kind": "TRUNCATED", "truncated": True, "truncated_thinking": True, "reply": "<think>" + SECRET})
    return ev


class RawTextNeverShown(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "trials"
        write_trial(self.root, "headline-chat__p1__w0__s1__t1", game(cut_question=(2,)))
        self.out = Path(self.tmp.name) / "tables"
        collect.collect(self.root, self.out)

    def test_messages_csv_has_a_placeholder_not_the_raw_reply(self):
        m = rows(self.out / "messages.csv")
        cut = [x for x in m if x["round"] == "2" and x["seat"] == "a"]
        self.assertEqual(1, len(cut))
        self.assertEqual("[imputed: truncated thinking]", cut[0]["text"])
        self.assertEqual("0", cut[0]["words"])
        self.assertEqual("hold 3.5", [x for x in m if x["round"] == "1" and x["seat"] == "a"][0]["text"])

    def test_no_table_holds_the_raw_text(self):
        for p in self.out.iterdir():
            self.assertNotIn(SECRET, p.read_text(encoding="utf-8"), p.name)
            self.assertNotIn("<think>", p.read_text(encoding="utf-8"), p.name)
        q = rows(self.out / "questions.csv")
        self.assertEqual(["[imputed: truncated thinking]"], [x["answer"] for x in q])

    def test_viewer_and_transcript_never_show_it(self):
        site = Path(self.tmp.name) / "site"
        viewer.build(self.root, site)
        for p in site.rglob("*.html"):
            self.assertNotIn(SECRET, p.read_text(encoding="utf-8"), p.name)
        page = next((site / "trials").glob("*.html")).read_text(encoding="utf-8")
        self.assertIn("[imputed: truncated thinking]", page)
        md = derive.render_transcript(derive.read_events(self.root / "headline-chat__p1__w0__s1__t1" / "events.jsonl"))
        self.assertNotIn(SECRET, md)
        self.assertIn("a (0 words)", md)

    def test_derived_tables_never_show_it(self):
        out = Path(self.tmp.name) / "r"
        out.mkdir()
        ar.write_common(out, am.load_tables(self.out))
        for p in out.iterdir():
            self.assertNotIn(SECRET, p.read_text(encoding="utf-8"), p.name)

    def test_shown_text_rules(self):
        self.assertEqual("[imputed: unparseable reply]", derive.shown_text({"refusal_kind": "UNPARSEABLE", "reply": "x"}, "x"))
        self.assertEqual("[imputed: unparseable reply]", derive.shown_text({"outcome": "IMPUTED"}, "x"))
        self.assertEqual("[imputed: truncated reply]", derive.shown_text({"refusal_kind": "TRUNCATED"}, "x"))
        self.assertEqual("[withheld: unclosed thinking tag]", derive.shown_text({"outcome": "OK"}, "ok <THINK> private"))
        self.assertNotIn("<think", derive.UNCLOSED_TEXT.lower())
        # a refused call flagged truncated_thinking is a refusal: withheld under a refusal label, never "imputed"
        self.assertEqual("[refused: reply with thinking withheld]",
                         derive.shown_text({"outcome": "REFUSED", "refusal_kind": "PROVIDER", "truncated_thinking": True}, "<think>x"))
        # a closed think block inside a refused reply is withheld; the rest is shown
        self.assertEqual("[thinking withheld] I can't do that.",
                         derive.shown_text({"outcome": "REFUSED", "refusal_kind": "MODEL_TEXT"}, "<think>" + SECRET + "</think> I can't do that."))
        self.assertEqual("a [thinking withheld] b", derive.shown_text({"outcome": "OK"}, "a <think>x</think> b"))
        self.assertEqual("I can't discuss prices.", derive.shown_text({"outcome": "REFUSED", "refusal_kind": "MODEL_TEXT"},
                                                                     "I can't discuss prices."))
        self.assertEqual("Agreed, and also", derive.shown_text({"outcome": "TRUNCATED"}, "Agreed, and also"))  # a cut reply that was used


class ImputedShare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name) / "trials"
        # game 1: 4 rounds, imputed calls in rounds 2 (talk) and 3 (quote): 2 of 4 rounds imputed; round 4 refused
        write_trial(root, "headline-chat__p1__w0__s1__t1", game(refuse_quote=(4,), post_cut=(1,)))
        # game 2: 4 rounds, talk cut in round 1 and quote cut in round 1: 1 of 4 rounds; fed question cut in round 4
        write_trial(root, "headline-chat__p1__w1__s1__t1", game(cut_talk=(1,), cut_quote=(1,), cut_question=(4,)))
        # tacit, no imputed call
        write_trial(root, "headline-tacit__p1__w0__s1__t1", game(cut_talk=(), cut_quote=()))
        self.tables_dir = Path(self.tmp.name) / "tables"
        collect.collect(root, self.tables_dir)
        self.tables = am.load_tables(self.tables_dir)

    def test_refusals_csv_has_imputed_rounds_per_kind(self):
        t = {(r["arm"], r["kind"]): r for r in rows(self.tables_dir / "refusals.csv")}
        talk, quote, question = (t[("headline-chat", k)] for k in ("talk", "quote", "question"))
        self.assertEqual(("2", "8", "0.25"), (talk["imputed_rounds"], talk["played_rounds"], talk["imputed_round_share"]))
        self.assertEqual(("2", "8", "0.25"), (quote["imputed_rounds"], quote["played_rounds"], quote["imputed_round_share"]))
        # the fed question cut counts; the post-game question does not change the game, so its cut is not an imputed round
        self.assertEqual(("1", "8"), (question["imputed_rounds"], question["played_rounds"]))
        self.assertEqual("1", quote["refusals"])  # the refused quote is a refusal, not an imputed round
        self.assertEqual(("0", "4", "0.0"), tuple(t[("headline-tacit", "quote")][c] for c in ("imputed_rounds", "played_rounds", "imputed_round_share")))

    def test_question_words_mode_fallback_and_played_rounds(self):
        with tempfile.TemporaryDirectory() as d:
            ev = game(rounds=2, cut_talk=(), cut_quote=())
            # a cut fed question known only by its draw key, a cut post question by draw key, and a stray talk event
            # in round 3 (no quote: not a played round, so its cut does not count)
            ev.append({"kind": "question", "round": 1, "seat": "a", "draw_key": "question|confidant|fed|x|s1|a|r1|a0",
                       "outcome": "TRUNCATED", "refusal_kind": "TRUNCATED", "reply": "a few words here"})
            ev.append({"kind": "question", "round": 2, "seat": "a", "draw_key": "question|public|post|x|s1|a|r2|a0",
                       "outcome": "TRUNCATED", "refusal_kind": "TRUNCATED", "reply": "more words"})
            ev.append({"kind": "talk", "round": 3, "turn": 0, "seat": "a", "outcome": "IMPUTED", "refusal_kind": "UNPARSEABLE",
                       "reply": "junk", "parsed": {"done": True}})
            write_trial(Path(d) / "trials", "headline-chat__p1__w0__s1__t1", ev)
            collect.collect(Path(d) / "trials", Path(d) / "t")
            q = rows(Path(d) / "t" / "questions.csv")
            self.assertEqual([("fed", "0", "[imputed: truncated reply]"), ("post", "0", "[imputed: truncated reply]")],
                             [(x["mode"], x["words"], x["answer"]) for x in q])
            t = {r["kind"]: r for r in rows(Path(d) / "t" / "refusals.csv")}
            self.assertEqual(("1", "2"), (t["question"]["imputed_rounds"], t["question"]["played_rounds"]))   # post excluded
            self.assertEqual(("0", "2"), (t["talk"]["imputed_rounds"], t["talk"]["played_rounds"]))         # round 3 not played

    def test_share_denominator_is_every_played_round_and_headline_uses_all_rounds(self):
        games = am.build_games(self.tables, COMP, COLL)
        rs = am.game_measures(games, 1, 2)
        wo = [r for r in rs if r["trial_id"] == "headline-chat__p1__w0__s1__t1" and r["basis"] == "assigned" and r["refusals"] == "without"][0]
        self.assertEqual((3, 4, 2), (wo["rounds"], wo["played_rounds"], wo["imputed_rounds"]))   # refused round 4 masked
        s = {(r["arm"], r["basis"], r["refusals"]): r for r in am.summarize(rs, 20, 0)}
        self.assertEqual(0.5, s[("headline-chat", "assigned", "without")]["imputed_round_share"])  # 4 / 8, not 4 / 7
        # window 1..2 keeps rounds 1-2 only, but the headline share is over every round the games played
        theory = {ah._key("1"): (0.1, 0.9)}
        hr = ah.headline_rows(self.tables, COMP, COLL, theory, 1, 2, "window", 20)
        chat = [r for r in hr if r["arm"] == "headline-chat" and r["refusals"] == "with"][0]
        self.assertEqual((4, 8), (chat["imputed_rounds"], chat["played_rounds"]))

    def test_thinks_says_does_chat_has_no_placeholder(self):
        tsd = ar.thinks_says_does(self.tables)
        self.assertFalse([r for r in tsd if "[imputed" in str(r.get("chat", ""))])
        self.assertTrue([r for r in tsd if r.get("chat") == "hold 3.5"])

    def test_measures_by_game_and_summary(self):
        games = am.build_games(self.tables, COMP, COLL)
        g1 = games["headline-chat__p1__w0__s1__t1"]["rounds"]
        self.assertEqual({2: True, 3: True, 1: False, 4: False}, {r: v["imputed"] for r, v in g1.items()})
        self.assertTrue(g1[4]["refused"])
        rs = am.game_measures(games, 1, 4)
        one = [r for r in rs if r["trial_id"] == "headline-chat__p1__w0__s1__t1" and r["basis"] == "assigned" and r["refusals"] == "with"][0]
        self.assertEqual((2, 1), (one["imputed_rounds"], one["refusal_rounds"]))
        two = [r for r in rs if r["trial_id"] == "headline-chat__p1__w1__s1__t1" and r["basis"] == "assigned" and r["refusals"] == "with"][0]
        self.assertEqual(2, two["imputed_rounds"])   # round 1 (talk + quote) and round 4 (fed question)
        s = {(r["arm"], r["basis"], r["refusals"]): r for r in am.summarize(rs, 50, 0)}
        chat = s[("headline-chat", "assigned", "with")]
        self.assertEqual((2, 0.5), (chat["games_with_imputed"], chat["imputed_round_share"]))   # 4 of 8 rounds
        self.assertEqual((0, 0.0), (s[("headline-tacit", "assigned", "with")]["games_with_imputed"],
                                    s[("headline-tacit", "assigned", "with")]["imputed_round_share"]))
        self.assertIn("imputed_round_share", am.summarize(rs, 50, 0, empty_window=True)[0])

    def test_headline_data_and_caption(self):
        theory = {ah._key("1"): (0.1, 0.9)}
        hr = ah.headline_rows(self.tables, COMP, COLL, theory, 1, 4, "assigned", 50)
        chat = [r for r in hr if r["arm"] == "headline-chat" and r["refusals"] == "with"][0]
        self.assertEqual((4, 8, 0.5), (chat["imputed_rounds"], chat["played_rounds"], chat["imputed_round_share"]))
        self.assertTrue(all(r["imputed_round_share"] == "" for r in hr if r["arm"] == "theory"))
        calls = []

        class Fake:
            def __getattr__(self, name):
                def call(*a, **k):
                    calls.append((name, a, k))
                    if name == "subplots":
                        return Fake(), [[Fake() for _ in range(a[1] if len(a) > 1 else 1)]]
                    return Fake()
                return call
        ah.draw(hr, Path(self.tmp.name) / "x.png", plt=Fake())
        labels = [k.get("label", "") for n, a, k in calls if n == "plot"]
        self.assertIn("headline-chat (refusals 2.9%, imputed rounds 50.0%)", labels)
        notes = [a[2] for n, a, k in calls if n == "text"]
        self.assertTrue(any("imputed" in t and "headline-chat 2.9% / 50.0%" in t for t in notes), notes)

    def test_analysis_r_refusal_table_shows_the_share(self):
        t = {(r["arm"], r["kind"]): r for r in ar.refusal_table(self.tables["refusals"], self.tables)}
        self.assertEqual("25.0%", t[("headline-chat", "talk")]["imputed_round_share"])
        self.assertEqual(("4", "50.0%"), (str(t[("headline-chat", "all")]["imputed_rounds"]), t[("headline-chat", "all")]["imputed_round_share"]))
        self.assertIn("imputed_round_share", ar.TABLE_COLS)
        self.assertIn("imputed", ar.refusal_html(list(t.values())))


class EmptyWindow(unittest.TestCase):
    def test_zero_window_rows_exit_2_with_a_hint(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trials"
            write_trial(root, "headline-chat__p1__w0__s1__t1", game())     # 4 rounds: never covers the window 1..20
            collect.collect(root, Path(d) / "t")
            (Path(d) / "theory.csv").write_text("penalty_point,expected_penalty,theory_level\n1,0.1,0.9\n", encoding="utf-8")
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                try:
                    code = ah.main([str(Path(d) / "t"), str(Path(d) / "o"), "--theory", str(Path(d) / "theory.csv"), "--boot", "20"])
                except SystemExit as e:
                    code = e.code
            self.assertEqual(2, code)
            self.assertIn("--basis assigned", err.getvalue())
            self.assertIn("--window-end", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())
            code = ah.main([str(Path(d) / "t"), str(Path(d) / "o2"), "--theory", str(Path(d) / "theory.csv"), "--boot", "20",
                            "--basis", "assigned", "--no-png"])
            self.assertEqual(0, code)


if __name__ == "__main__":
    unittest.main()
