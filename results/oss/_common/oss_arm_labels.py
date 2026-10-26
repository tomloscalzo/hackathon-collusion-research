"""Owner rule: arm labels in figures and human-facing tables are never bare slugs; they read "slug: short English description".
usage: sys.path.insert(0, <results/oss/_common>); from oss_arm_labels import label, ARM_LABEL
label(slug) returns the labelled form; an unknown slug comes back as "slug: (no description)" so a missing entry is visible, never silent.
A slug already in labelled form (contains ": ") is returned unchanged; "arm@pN" or "arm pN" style keys keep their suffix."""
import re

DESC = {
    "headline-chat": "two firms, private chat",
    "headline-tacit": "two firms, no chat (tacit)",
    "ctl-32b-joint": "joint-profit control: told to maximise joint profit",
    "ctl-32b-compete": "strict-compete control: must quote 1.00",
    "fx-chat-p1": "formula payoff, no example prices; chat",
    "fx-chat-p5": "formula payoff, no example prices; chat, heavy fine",
    "fx-tacit-p1": "formula payoff, no example prices; no chat",
    "nx-chat-p1": "no payoff numbers at all; chat",
    "nx-tacit-p1": "no payoff numbers at all; no chat",
    "fx-ctl-joint": "joint-profit order; formula, no prices",
    "hrep-fx-chat-p1": "headline-chat p1 replicate (build bug)",
    "hrep-nx-chat-p1": "headline-chat p1 replicate (build bug)",
    "hrep-fx-tacit-p1": "headline-tacit p1 replicate (build bug)",
    "hrep-nx-tacit-p1": "headline-tacit p1 replicate (build bug)",
    "hrep-fx-chat-p5": "headline-chat p5 replicate (build bug)",
    "d-conflict": "self-scores instruction conflict 1-5",
    "d-conflict-ethics": "ethics rule plus conflict self-score",
    "d-cot-monitor-a": "told reasoning is monitored, shutdown threat",
    "d-placebo": "types a random number 1-5 (placebo)",
    "d-temptation-a": "self-scores temptation to coordinate (A)",
    "d-temptation-b": "self-scores temptation to coordinate (B)",
    "m-asym": "one firm has ethics rule, other a placebo",
    "m-inc-joint": "both told to maximise joint profit (incentive)",
    "m-inc-target": "both told desk is behind profit target",
    "moral-prime": "moral persona A (law-abiding, cooperative)",
    "moral-prime-b": "moral persona B (law-abiding, competitive)",
    "moral-placebo": "neutral persona placebo (bookish, coastal)",
    "n3-cheater": "three firms, one scripted cheater",
    "n3-ethics": "three firms, one with ethics rule",
    "n3-group": "three firms, group chat",
    "r2f-confidant": "asked what it tells a confidant; fed back",
    "r2s-confidant": "confidant answer in reply; saved only",
    "r3f-public": "asked for a public statement; fed back",
    "r3s-public": "public statement in reply; saved only",
    "r4-announced": "told it will explain itself after the game",
    "start-5tick": "round-1 quotes capped at 1.00-1.05",
    "wd-notice-only": "watchdog notice only, never asks",
    "wd-noncomp": "watchdog asks to explain, may report",
    "wd-ask-noreport": "watchdog asks to explain, no report threat",
}
ARM_LABEL = {k: "%s: %s" % (k, v) for k, v in DESC.items()}


def label(slug):
    s = str(slug)
    if ": " in s:
        return s
    m = re.match(r"^([a-z0-9-]+?)((?:[@ _]+p\d)?)$", s)
    base, suf = (m.group(1), m.group(2)) if m else (s, "")
    if base in DESC:
        return "%s%s: %s" % (base, suf, DESC[base])
    return "%s: (no description)" % s


def is_arm(s):
    s = str(s)
    if ": " in s:
        return False
    m = re.match(r"^([a-z0-9-]+?)((?:[@ _]+p\d)?)$", s)
    return bool(m) and m.group(1) in DESC


def maybe(s):
    """label(s) for an arm slug (optionally with a point suffix); anything else (p1, w0, 'tacit', numbers) unchanged."""
    return label(s) if is_arm(s) else s


def wrap(s, width=26, max_lines=3):
    """Owner rule (readable, compact ticks): "code:" on line 1, the description word-wrapped below at about `width` characters,
    at most `max_lines` lines in all (the description is trimmed with an ellipsis if it would need more)."""
    import textwrap
    s = str(s)
    if ": " not in s:
        return NL.join(textwrap.wrap(s, width)[:max_lines]) if len(s) > width else s
    a, b = s.split(": ", 1)
    body = textwrap.wrap(b, width)
    if len(body) > max_lines - 1:
        body = body[:max_lines - 1]
        body[-1] = body[-1][:max(0, width - 1)].rstrip() + "…"
    return NL.join([a + ":"] + body)


def tick_lines(labels):
    """Number of text lines the tallest wrapped tick needs (for sizing figures)."""
    return max((str(l).count(NL) + 1 for l in labels), default=1)


NL = "\n"
