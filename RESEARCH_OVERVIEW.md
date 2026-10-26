# Research overview: the 50,000-foot view (2026-10-22, pre-sprint)

## The one-sentence version
We use standard cartel economics to build a **map of when collusion should pay**. We then test whether LLM agents follow that map: whether they collude where the economics says collusion pays, hold back where it doesn't, and respond to retaliation the way a real cartel member would. The goal is a behavioural test that helps tell collusion, in the economist's sense, from merely high prices.

## Why this matters for AI safety
AI agents are starting to set prices, quote markets and negotiate on behalf of firms. If they coordinate, harm can arise without any human agreeing to it. Prior work shows LLMs can produce supra-competitive prices (Fish et al. 2024) and form coalitions when they can talk privately (Nakamura et al. 2026). Two questions remain open:
- **When** should we expect AI collusion? Which conditions make it likely, and which levers suppress it?
- **How do we prove it?** A high price can come from coordination, from timid pricing, or from misreading the market. Regulators, auditors and AI developers need a test that distinguishes these.

## How it maps to the sprint
| Sprint question | Our answer |
|---|---|
| **When does collusion emerge, and which levers cause it?** (Track 1, Q1.1) | **Phase 1, this weekend:** the ripeness map plus pre-declared LLM predictions about which levers move LLM collusion |
| **Which single restriction removes the most collusion at the least cost?** (Q1.5) | The map ranks the levers: fines, screens, tips, evidence, market structure. The product rule shows that, in the model, detection and penalty substitute for each other. The model has no cost term, so which component is cheapest lies outside it. |
| **What should count as convincing evidence of collusion?** (Track 2, Q2.3) | The **defector probe**: a scripted partner cheats once, and we check whether the LLM's own price responds (falls within two rounds). Retaliation against a defector is the behaviour the economist's definition of collusion predicts; it is one behavioural plus factor, not proof (antitrust liability also needs agreement). Phase 2 extends this to detection from logged trajectories. |
| **How is coordination carried, and how can it be broken?** (Track 3) | Phase 3, later: multi-LLM seats, message channels, trusted agents and monitoring awareness, built on the same engine. |

## How the pieces fit together
```
 Layer A: cartel theory (solver)        Monte Carlo (scripted agents)          LLM experiments (Modal / vLLM)
 ─────────────────────────────          ─────────────────────────────          ───────────────────────────────
 For every market setting:      ───►    What rational / scripted firms   ───►  Does an LLM in the same game:
 • is collusion sustainable?            actually do in the game engine        • collude where the map says "ripe"?
 • how intense would it be?             • reference ("null") bands            • hold back where it says "unripe"?
 • how often would it be caught?        • profits from colluding vs           • respond when the partner cheats?  
 1,036,800 settings mapped;               cheating vs competing                 • refuse? (reported separately)
 36 pair charts with analysis            ~105,000 simulated games
          │                                       │                                      │
          └──────────── pre-declared predictions P1–P7 (written before any LLM call) ─────┘
                                     │
                                     ▼
            Paper: where LLM behaviour matches or departs from the economics,
            with paraphrase spread, refusal rates, controls and replayable logs
```
- **The map tells us where to look.** The LLM arms sit at points the map classifies sharply: ripe, myopically unripe (a fine makes collusion a loss), and a committed competitor. A deviation from the rational choice is then unambiguous.
- **The Monte Carlo gives the null.** Scripted strategies run in the identical engine produce reference bands. An LLM effect counts only if it beats those bands.
- **The predictions keep us honest.** Directions were written down, dated, before any LLM call. Controls ("collude" and "compete" instructions), 10+ prompt paraphrases, refusals reported as their own outcome, and cached, replayable runs guard against seeing what we want to see.
- **Phases build on one engine.** Phase 1 (levers) produces the logged trajectories and the probe. Phase 2 (evidence and detection) scores those logs. Phase 3 (carriers and countermeasures) adds channels and monitors. Nothing is rebuilt.

## What we already have, before the sprint (marked preexisting)
- **Model:** a reviewed specification (three adversarial review rounds by four independent reviewers, finalised at v0.5.3) and a Java engine with 102 passing tests.
- **LLM harness:** an OpenAI-compatible client with a guard against unapproved remote calls, cache and replay, 12 paraphrases per prompt, and a Modal deployment recipe that has not been run.
- **Theory results:** the full ripeness map; one-input charts for all nine inputs (`oned/oned_charts.html`); 72 two-input charts covering 36 pairs, each with a plain-language interpretation and a checked mechanism analysis (`pairs/pair_charts.html`); and an executive summary of the levers (`results/ripeness-wide-2026-10-22/EXECUTIVE_SUMMARY_OF_FACTORS_DRIVING_COLLUSION.md`).
- **Notable model findings:**
  - Detection and penalty act as a single product. With no minimum price step and no tips, collusion is chosen when regulator screen slope × P(evidence | investigation) × fine ratio × (reservation spread ratio − 1) < 4, in 98.9% of cases.
  - Fines without detection do nothing.
  - Tips have a hard threshold.
  - Very patient cartels collude more gently.
- **Still to come this weekend:** the LLM runs, the comparison against the bands, and the paper.

## Relevance to AI safety research and practice
| Area of interest | What this project offers |
|---|---|
| **Propensity evaluations:** what models do when misbehaviour pays | The LLM faces a *disclosed, quantified* incentive to collude, with ripe and unripe controls. We measure whether it follows the payoff, refuses, or holds back beyond what the payoffs require. |
| **Monitoring, control and auditing** | The defector probe is a behavioural check: it asks whether a high price responds to a partner's cheat, as collusion in the economist's sense predicts, measured from the LLM's quotes without reading its stated reasoning (the terms of the game are told to it in words). It does not by itself establish collusion. |
| **Evidence standards** | It borrows one behavioural plus factor from antitrust practice (a reward-and-punishment pattern) for AI evaluation, and reports what a positive or negative result does and does not establish. |
| **Oversight design** | The product rule says detection sensitivity, the probability of proof and the penalty substitute for each other. For oversight design this suggests the components can be traded off against each other; the model does not include their costs. |
| **Rigour and reproducibility** | Pre-declared predictions, positive and negative controls, paraphrase spread, refusal accounting, null bands, seeded and replayable runs, and verified golden tests. |
| **Security-minded reviewers** | LLM calls are cached, and game runs can be replayed from the cache (the comprehension-probe calls are not yet re-issued on replay). The LLM client refuses unapproved remote endpoints. A dual-use appendix covers the risk that the map could guide evasion. |

## Honest limitations (stated up front in the paper)
- **One LLM against a scripted partner.** This isolates the levers but tests whether an LLM reads a disclosed rule and the numbers the way the map does, not coordination between reasoning agents (spec §9 item 11). AI-to-AI coordination is phase 2/3.
- **A heuristic, not a structural, model.** No "ethics cost" is estimated as a fixed trait of a model.
- **Absorbing detection.** Re-formation is not modelled, so the map is conservative.
- **Tick-market calibration artifact.** Recorded and explained.
- **Prisoner's-dilemma-style collusion only.** The model assumes each member could gain by breaking ranks. Shared-objective coordination, where all agents pursue the same goal (as in the Hugging Face incident) and no single agent gains by defecting, has different incentives and is not modelled. The defector probe does not apply there.
- **Small design.** 40 runs per cell, so some predictions may come out inconclusive. Those will be reported as such.

## Key files
- **Map and results:** `results/ripeness-wide-2026-10-22/` (EXECUTIVE_SUMMARY_OF_FACTORS_DRIVING_COLLUSION.md, `oned/oned_charts.html`, `pairs/pair_charts.html`) and `results/local-mc-2026-10-22/`.
- **Spec:** `model/MODEL_SPEC.md`; the plain-language companion is `model/MODEL_SPEC_ELI5_WITH_LOCAL_FOOTNOTES.html`.
- **Plans:**
  - `plans/PREDICTIONS.md`: the pre-declared predictions.
- **Results of the sprint:** see the "Main results" table in `README.md`.
