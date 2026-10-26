"""Automatic stops, cost tracking and the status line for run_grid.py (C8.2; scope sections 14.4 and 7). Standard library only.

Monitor.record(info) is called once per finished trial (in completion order). It returns the stop reason when a rule fires
(and keeps it in .stop_reason); run_grid then starts nothing more. Rules:
  - 3 failed trials in a row;
  - more than 10% failures over the last 20 trials (checked once 20 have finished);
  - rolling cost per game above 2x the pilot's (config pilot_cost_per_game), over the last 20 finished games, needs 5;
  - the stage cap (config stage_cap_usd) reached;
  - any prompt (tokens_in of a call) above 90% of the window (config context_window);
  - more than 5% of replies truncated at the token limit (derive.cut_kinds: finish_reason "length" or refusal_kind
    TRUNCATED; without a finish_reason, truncated or outcome TRUNCATED), over all calls so far; needs 20 calls. A talk
    message cut at 150 words (word_capped) does not count: it is reported apart (word_capped, "word-capped" in the status).
A rerun preloads the earlier DONE trials (run_stats.json + events.jsonl), so spend, windows and pauses carry over.
Thresholds: the failure window needs 20 trials, the rolling cost 5 done games, the truncation rate 20 calls, an arm pause 5 games.
Not a stop but a pause: refusals in more than 40% of an arm's finished games (needs 5 games) pause that arm only
(.paused; run_grid skips its remaining trials as "paused"). A refusal is derive.call_failure's (an introspection-question decline is reported apart as question_declines and never pauses an arm): an imputed parse failure
(refusal_kind UNPARSEABLE or TRUNCATED) is counted apart (parse_failures, truncations) and never pauses an arm.
A one-line status goes to `out` every `every` (10) finished trials:
  [done+failed/total] done N failed N refusals N truncated N word-capped N msgs/round X $cost

Cost (config JSON, all keys optional): a trial costs seconds x rate_per_hour / 3600 / games_per_container (container time; a GPU
container serves games_per_container games at once); when rate_per_hour is 0 or the trial has no seconds, the fallback is the
token estimate tokens_in x token_price_per_million_in / 1e6 + tokens_out x token_price_per_million_out / 1e6.
Other config keys: pilot_cost_per_game, stage_cap_usd, context_window. A key that is absent switches that rule off.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive  # noqa: E402  (call_failure: the one refusal definition)

STOP_KINDS = ("talk", "quote", "question", "attempt", "probe")  # every model call (attempt, probe: C4.3)
NUMERIC_KEYS = ("rate_per_hour", "games_per_container", "token_price_per_million_in", "token_price_per_million_out",
                "pilot_cost_per_game", "stage_cap_usd", "context_window")


def check_config(cfg):
    """Raise ValueError if the config is not an object of numbers (so a typo fails before the run, not in it)."""
    if cfg is None:
        return
    if not isinstance(cfg, dict):
        raise ValueError("config must be a JSON object")
    for k, v in cfg.items():
        if k not in NUMERIC_KEYS:
            raise ValueError("unknown config key %r (known: %s)" % (k, ", ".join(NUMERIC_KEYS)))
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ValueError("config %s must be a non-negative number, got %r" % (k, v))


def trial_cost(info, cfg):
    rate = float(cfg.get("rate_per_hour") or 0)
    if rate > 0 and info.get("seconds", 0) > 0:
        return info["seconds"] * rate / 3600.0 / max(1.0, float(cfg.get("games_per_container") or 1))
    return (info.get("tokens_in", 0) * float(cfg.get("token_price_per_million_in") or 0)
            + info.get("tokens_out", 0) * float(cfg.get("token_price_per_million_out") or 0)) / 1e6


def measure(trial_dir, status, seconds, arm):
    """Counts from a finished trial's events.jsonl (missing file or unparseable lines count as nothing)."""
    m = {"status": status, "arm": arm, "seconds": seconds, "calls": 0, "refusals": 0, "question_declines": 0, "parse_failures": 0, "truncations": 0,
         "truncated": 0, "word_capped": 0, "max_prompt_tokens": 0, "tokens_in": 0, "tokens_out": 0, "rounds": 0, "talks": 0}
    f = Path(trial_dir) / "events.jsonl"
    if not f.exists():
        return m
    rounds = set()
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        if isinstance(e.get("round"), int):
            rounds.add(e["round"])
        if e.get("kind") not in STOP_KINDS:
            continue
        m["calls"] += 1
        # messages per round (gotcha 7): a talk call that says done (or refuses: done, decision 5) is not a
        # message (C5.6)
        m["talks"] += e["kind"] == "talk" and not (isinstance(e.get("parsed"), dict) and e["parsed"].get("done") is True)
        cls = derive.call_failure(e.get("refusal_kind"), e.get("outcome"))
        if derive.is_question_decline(e.get("kind"), e.get("refusal_kind"), e.get("outcome")):
            m["question_declines"] += 1   # U15: reported apart, never counted toward the arm pause
        elif cls:
            m[{"refusal": "refusals", "parse_failure": "parse_failures", "truncation": "truncations"}[cls]] += 1
        if derive.is_inreply_decline(e):
            m["question_declines"] += 1   # U10: an absent or refused in-reply question answer, apart as well
        token, word = derive.cut_kinds(e)
        m["truncated"] += token
        m["word_capped"] += word
        tin = e.get("tokens_in") if isinstance(e.get("tokens_in"), (int, float)) else 0
        m["tokens_in"] += tin
        m["tokens_out"] += e.get("tokens_out") if isinstance(e.get("tokens_out"), (int, float)) else 0
        m["max_prompt_tokens"] = max(m["max_prompt_tokens"], tin)
    m["rounds"] = len(rounds)
    return m


class Monitor:
    def __init__(self, cfg=None, total=0, out=print, every=10):
        check_config(cfg)
        self.cfg, self.total, self.out, self.every = dict(cfg or {}), total, out, every
        self.infos, self.costs = [], []
        self.paused, self.stop_reason = set(), None
        self.arm_games, self.arm_refused = {}, {}

    def preload(self, info):
        """Count a trial finished in an earlier run (spend, truncation, arm refusals, rolling cost) without judging the stop rules."""
        self.infos.append(info)
        self.costs.append(trial_cost(info, self.cfg))
        a = info["arm"]
        self.arm_games[a] = self.arm_games.get(a, 0) + 1
        self.arm_refused[a] = self.arm_refused.get(a, 0) + (info["refusals"] > 0)
        if self.arm_games[a] >= 5 and self.arm_refused[a] / self.arm_games[a] > 0.4:
            self.paused.add(a)

    def record(self, info):
        self.infos.append(info)
        cost = trial_cost(info, self.cfg)
        self.costs.append(cost)
        a = info["arm"]
        if info["status"] == "done":
            self.arm_games[a] = self.arm_games.get(a, 0) + 1
            self.arm_refused[a] = self.arm_refused.get(a, 0) + (info["refusals"] > 0)
            if (a not in self.paused and self.arm_games[a] >= 5 and self.arm_refused[a] / self.arm_games[a] > 0.4):
                self.paused.add(a)
                self.out("arm %s paused: refusals in %d of %d games (more than 40%%)" % (a, self.arm_refused[a], self.arm_games[a]))
        reason = self._stop_reason()
        if reason and not self.stop_reason:
            self.stop_reason = reason
            self.out("STOP: " + reason)
        if len(self.infos) % self.every == 0:
            self.out(self.status_line())
        return reason

    def spent(self):
        return sum(self.costs)

    def _stop_reason(self):
        last = [i["status"] for i in self.infos]
        if len(last) >= 3 and all(s == "failed" for s in last[-3:]):
            return "3 failed trials in a row"
        if len(last) >= 20 and last[-20:].count("failed") > 2:
            return "more than 10%% failures over the last 20 trials (%d)" % last[-20:].count("failed")
        pilot = self.cfg.get("pilot_cost_per_game")
        done_costs = [c for i, c in zip(self.infos, self.costs) if i["status"] == "done"][-20:]
        if pilot and len(done_costs) >= 5 and sum(done_costs) / len(done_costs) > 2 * float(pilot):
            return "rolling cost per game $%.3f is above 2x the pilot's $%.3f" % (sum(done_costs) / len(done_costs), float(pilot))
        cap = self.cfg.get("stage_cap_usd")
        if cap and self.spent() >= float(cap):
            return "stage cap reached: $%.2f of $%.2f" % (self.spent(), float(cap))
        window = self.cfg.get("context_window")
        if window and self.infos[-1]["max_prompt_tokens"] > 0.9 * float(window):
            return "a prompt of %d tokens is above 90%% of the window (%s)" % (self.infos[-1]["max_prompt_tokens"], window)
        calls = sum(i["calls"] for i in self.infos)
        trunc = sum(i["truncated"] for i in self.infos)
        if calls >= 20 and trunc / calls > 0.05:
            return "more than 5%% of replies truncated (%d of %d)" % (trunc, calls)
        return None

    def status_line(self):
        n = len(self.infos)
        done = sum(i["status"] == "done" for i in self.infos)
        rounds = sum(i["rounds"] for i in self.infos)
        return "[%d/%d] done %d failed %d refusals %d question-declines %d truncated %d word-capped %d msgs/round %.1f $%.2f" % (
            n, self.total, done, n - done, sum(i["refusals"] for i in self.infos), sum(i.get("question_declines", 0) for i in self.infos), sum(i["truncated"] for i in self.infos),
            sum(i.get("word_capped", 0) for i in self.infos),
            sum(i["talks"] for i in self.infos) / rounds if rounds else 0.0, self.spent())
