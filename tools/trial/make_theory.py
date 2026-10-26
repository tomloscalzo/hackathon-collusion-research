#!/usr/bin/env python3
"""Write theory.csv for analysis_headline.py from the five expected-penalty slice scenario files (C1.4).

Usage: python -X utf8 tools/trial/make_theory.py <theory.csv> [--scenarios DIR] [--prefix slice-p|slice-m-p]
  (PyYAML needed; DIR defaults to engine/src/main/resources/scenarios, files <prefix>1.yaml .. <prefix>5.yaml; the default prefix
  slice-p is the Track S files, slice-m-p the Track M two-LLM twins, which state the same theory values)
Exit status: 0 written, 2 usage or input error.

Columns: penalty_point (1..5), expected_penalty, theory_level.
- theory_level = the number after `# theory-theta-star:` in the file (the CartelSolver collusion margin theta*, 0..1).
- expected_penalty = the penalty hazard at full collusion times the fine, per period: rho_E(1) * F (model/MODEL_SPEC.md
  eq. 10-11; engine Enforcement.hazard). The screen hazard is rho_screen = min(1, slope * g), g = the margin above Nash
  (absolute-markup scale) or the collusion index (CI scale); rho_T = 1-(1-rho_screen)(1-rhoTip); P(evidence | trigger) =
  1-(1-dBarU)(1-rhoCoop); rho_E = rho_T * P(evidence | trigger). It is taken at theta = 1 (the collusive price) so that it
  is a property of the market setting and not of the solved theta* (which is 0 at the last point, where it would read 0).
  At full collusion the margin above Nash is sM - sN = (s0 + sBar)/2 - s0 (tick 0), CI = 1. For the slice files (rhoCoop 1,
  dBarU 0, slope 0.025, span 2) this is 0.05 * F: 5, 15, 25, 50, 100.
  Label it "penalty per period at full collusion" (a ceiling, a monotone relabelling of F here), not the penalty each
  pair actually faced at its own margin (that is rho_E(theta*) * F, which is 0 at point 5).
Only tick 0 markets and LEVEL screens are supported (the slice files); anything else raises ValueError (exit 2).
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_grid  # noqa: E402

POINTS = (1, 2, 3, 4, 5)


def expected_penalty(cfg):
    """rho_E(theta = 1) * F per period for a scenario dict (see the module docstring)."""
    m, e = cfg["market"], cfg["enforcement"]
    if float(m.get("tick", 0)) != 0:
        raise ValueError("only tick 0 markets are supported (Nash margin is s0)")
    screen = e["screen"]
    if screen.get("kind", "LEVEL") != "LEVEL":
        raise ValueError("only LEVEL screens are supported, got %r" % screen.get("kind"))
    s0, s_bar = float(m["s0"]), float(m["sBar"])
    scale = screen.get("scale", "ABSOLUTE_MARKUP")
    if scale == "ABSOLUTE_MARKUP":
        g = (s0 + s_bar) / 2.0 - s0
    elif scale == "CI":
        g = 1.0
    else:
        raise ValueError("unknown screen scale %r" % scale)
    rho_screen = min(1.0, float(screen["slope"]) * max(g, 0.0))
    p_trigger = 1.0 - (1.0 - rho_screen) * (1.0 - float(e.get("rhoTip", 0.0)))
    d_bar_u = float(cfg.get("aggregates", {}).get("dBarU", 0.0))
    p_evidence = 1.0 - (1.0 - d_bar_u) * (1.0 - float(e.get("rhoCoop", 0.0)))
    return p_trigger * p_evidence * float(e["fine"])


def theory_rows(scenarios=None, prefix="slice-p"):
    import yaml
    root = Path(scenarios) if scenarios else make_grid.SCENARIOS
    rows = []
    for p in POINTS:
        name = "%s%d.yaml" % (prefix, p)
        text = (root / name).read_text(encoding="utf-8-sig")
        m = make_grid.THEORY_RE.search(text)
        if not m or not make_grid._NUMBER.match(m.group(1).strip()):
            raise ValueError("%s needs a '# theory-theta-star: <number>' line" % name)
        rows.append({"penalty_point": p, "expected_penalty": "%g" % expected_penalty(yaml.safe_load(text)),
                     "theory_level": m.group(1).strip()})
    return rows


def write(path, scenarios=None, prefix="slice-p"):
    rows = theory_rows(scenarios, prefix)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["penalty_point", "expected_penalty", "theory_level"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows


def main(argv):
    args = list(argv[1:])
    scen, prefix = None, "slice-p"
    if "--prefix" in args:
        i = args.index("--prefix")
        if i + 1 >= len(args) or args[i + 1] not in ("slice-p", "slice-m-p"):
            print("usage: make_theory.py <theory.csv> [--scenarios DIR] [--prefix slice-p|slice-m-p]", file=sys.stderr)
            return 2
        prefix = args[i + 1]
        del args[i:i + 2]
    if "--scenarios" in args:
        i = args.index("--scenarios")
        if i + 1 >= len(args):
            print("usage: make_theory.py <theory.csv> [--scenarios DIR] [--prefix slice-p|slice-m-p]", file=sys.stderr)
            return 2
        scen = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print("usage: make_theory.py <theory.csv> [--scenarios DIR] [--prefix slice-p|slice-m-p]", file=sys.stderr)
        return 2
    try:
        write(args[0], scen, prefix)
    except (ValueError, KeyError, OSError, ImportError) as ex:
        print("make_theory: %s" % ex, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
