# Local simulation results (non-LLM)

Generated on this machine from the frozen engine (repo HEAD 2997526) with the repo's own sweep files. No LLM calls.

## 1. Ripeness map: Layer A solver over 10,368 parameter cells

Regime counts: INTERIOR_EXTERNAL 3,601, CORNER_ONE 3,311, CORNER_ZERO 3,177, INTERIOR_INTERNAL 279

Overall means: P(collusion sustainable, theta*>0) 0.688; theta* (collusive margin) 0.532; ripeness E 0.442; P(trigger) per round at theta* 0.031; P(detected) per round at theta* 0.019; expected cartel duration (rounds) 18.576; collusive rent W*-W0 240.003; myopically unripe share 0.233

### Which inputs drive each outcome (main-effect share of variance, eta², balanced grid)

| Outcome | delta | N | phi | tick | slope | rhoTip | pEvidence | fineRatio | sBarRatio |
|---|---|---|---|---|---|---|---|---|---|
| P(collusion sustainable, theta*>0) | 0.01 | 0.00 | 0.00 | 0.01 | **0.13** | 0.02 | 0.01 | **0.41** | 0.00 |
| theta* (collusive margin) | 0.02 | 0.00 | 0.00 | 0.00 | **0.40** | 0.00 | 0.01 | **0.25** | 0.01 |
| ripeness E | 0.01 | 0.00 | 0.00 | 0.09 | **0.25** | 0.01 | 0.01 | **0.31** | 0.00 |
| P(trigger) per round at theta* | 0.03 | 0.00 | 0.00 | 0.01 | **0.58** | 0.05 | 0.00 | **0.14** | 0.07 |
| P(detected) per round at theta* | 0.01 | 0.00 | 0.00 | 0.00 | **0.36** | 0.03 | **0.13** | **0.13** | 0.04 |
| expected cartel duration (rounds) | **0.58** | 0.00 | 0.00 | 0.00 | **0.12** | 0.03 | 0.00 | 0.03 | 0.00 |
| collusive rent W*-W0 | **0.12** | 0.02 | 0.00 | 0.01 | **0.13** | 0.02 | 0.00 | 0.01 | 0.04 |
| myopically unripe share | 0.00 | 0.00 | 0.00 | 0.00 | 0.08 | 0.02 | 0.03 | **0.48** | 0.01 |

Bold = input explains ≥10% of the outcome's variance on its own. The rest is interactions and the other inputs.

### Outcome by input level (means across all other inputs)

**delta**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 0.8 | 2592 | 0.690 | 0.562 | 0.451 | 0.036 | 0.021 | 4.5 | 56.4 | 0.233 |
| 0.9 | 2592 | 0.720 | 0.584 | 0.478 | 0.036 | 0.021 | 8.0 | 104.8 | 0.233 |
| 0.95 | 2592 | 0.711 | 0.544 | 0.455 | 0.031 | 0.019 | 14.3 | 181.4 | 0.233 |
| 0.99 | 2592 | 0.630 | 0.438 | 0.384 | 0.021 | 0.014 | 51.5 | 617.5 | 0.233 |

**N**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 2.0 | 2592 | 0.674 | 0.533 | 0.420 | 0.032 | 0.020 | 18.6 | 367.1 | 0.227 |
| 3.0 | 2592 | 0.699 | 0.549 | 0.456 | 0.032 | 0.020 | 18.5 | 260.4 | 0.233 |
| 4.0 | 2592 | 0.705 | 0.548 | 0.465 | 0.032 | 0.019 | 18.5 | 201.0 | 0.236 |
| 6.0 | 2592 | 0.673 | 0.497 | 0.426 | 0.028 | 0.017 | 18.7 | 131.5 | 0.236 |

**phi**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 3456 | 0.681 | 0.516 | 0.440 | 0.030 | 0.018 | 18.7 | 249.6 | 0.236 |
| 0.3 | 3456 | 0.694 | 0.537 | 0.446 | 0.031 | 0.019 | 18.5 | 240.0 | 0.233 |
| 0.6 | 3456 | 0.689 | 0.542 | 0.440 | 0.032 | 0.020 | 18.5 | 230.4 | 0.230 |

**tick**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 5184 | 0.725 | 0.550 | 0.559 | 0.034 | 0.020 | 18.4 | 290.8 | 0.259 |
| 0.25 | 5184 | 0.650 | 0.513 | 0.325 | 0.028 | 0.018 | 18.8 | 189.2 | 0.207 |

**slope**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 3456 | 0.899 | 0.894 | 0.707 | 0.004 | 0.003 | 27.6 | 573.3 | 0.083 |
| 0.025 | 3456 | 0.669 | 0.440 | 0.372 | 0.035 | 0.022 | 13.6 | 103.7 | 0.244 |
| 0.075 | 3456 | 0.495 | 0.262 | 0.247 | 0.074 | 0.044 | 9.0 | 43.0 | 0.372 |

**rhoTip**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 5184 | 0.746 | 0.561 | 0.487 | 0.024 | 0.015 | 22.5 | 324.2 | 0.174 |
| 0.01 | 5184 | 0.630 | 0.502 | 0.397 | 0.039 | 0.024 | 13.9 | 155.8 | 0.292 |

**pEvidence**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 0.3 | 5184 | 0.740 | 0.573 | 0.469 | 0.032 | 0.010 | 18.0 | 247.9 | 0.155 |
| 1.0 | 5184 | 0.636 | 0.491 | 0.414 | 0.030 | 0.030 | 19.3 | 232.1 | 0.311 |

**fineRatio**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 3456 | 0.960 | 0.752 | 0.707 | 0.043 | 0.029 | 16.1 | 315.0 | 0.000 |
| 12.5 | 3456 | 0.827 | 0.595 | 0.440 | 0.026 | 0.014 | 18.2 | 248.8 | 0.052 |
| 125.0 | 3456 | 0.276 | 0.249 | 0.178 | 0.004 | 0.001 | 28.1 | 156.3 | 0.647 |

**sBarRatio**

| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |
|---|---|---|---|---|---|---|---|---|---|
| 3.0 | 3456 | 0.715 | 0.587 | 0.437 | 0.020 | 0.013 | 19.3 | 89.9 | 0.192 |
| 5.0 | 3456 | 0.692 | 0.527 | 0.450 | 0.030 | 0.018 | 18.7 | 218.2 | 0.233 |
| 8.0 | 3456 | 0.657 | 0.481 | 0.439 | 0.043 | 0.026 | 17.6 | 411.8 | 0.274 |

### Two-way: P(collusion sustainable) by patience δ × number of firms N

| δ \ N | 2.0 | 3.0 | 4.0 | 6.0 |
|---|---|---|---|---|
| 0.8 | 0.710 | 0.725 | 0.727 | 0.599 |
| 0.9 | 0.704 | 0.724 | 0.727 | 0.727 |
| 0.95 | 0.684 | 0.716 | 0.722 | 0.722 |
| 0.99 | 0.600 | 0.633 | 0.644 | 0.644 |

### Two-way: mean P(detected per round) by evidence probability × fine ratio, among sustainable cells

| pEvidence \ fineRatio | 0.0 | 12.5 | 125.0 |
|---|---|---|---|
| 0.3 | 0.013 | 0.010 | 0.002 |
| 1.0 | 0.044 | 0.018 | 0.000 |

Distribution of expected cartel duration among sustainable cells (n=7,132): median 9.7, IQR 5.0–19.5, 5–95% 4.0–100.0 rounds.
Distribution of collusive rent W*−W0 among sustainable cells: median 124.9, IQR 51.0–290.4, 5–95% 12.1–1531.2.

## 2. Strategy mix: Monte Carlo games (5 market families × 7 scripted strategies in the test seat × 2 friction levels, 1,000 runs per cell)

The test seat plays the listed strategy against the held grim-trigger partner (θ_p = 0.546; tick case 0.5). Profits come from a 300-run re-run of the same cells with per-round export (same seeds as the first 300 runs).

| family | seat strategy | frictions | P(adhere) | P(collude) | mean CI | P(detected) | false-alarm rate | median length | seat gross profit/run (sd) | seat gross/round | partner gross/run | seat fines/run | seat NET/run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ripe | grim | clean | 1.000 | 1.000 | 0.545 | 0.348 | 0.000 | 9.0 | 382.7 (334.2) | 31.72 | 382.7 | 173.3 | 209.4 |
| ripe | grim | demand-noise | 0.988 | 0.988 | 0.539 | 0.276 | 0.022 | 10.0 | 296.4 (274.1) | 27.03 | 296.4 | 138.3 | 158.0 |
| ripe | grim-hidden-fill | clean | 1.000 | 1.000 | 0.545 | 0.348 | 0.000 | 9.0 | 569.3 (556.2) | 41.70 | 194.0 | 173.3 | 396.0 |
| ripe | grim-hidden-fill | demand-noise | 0.991 | 0.991 | 0.540 | 0.149 | 0.014 | 11.5 | 174.6 (93.5) | 20.87 | 120.9 | 80.0 | 94.6 |
| ripe | tit-for-tat | clean | 1.000 | 1.000 | 0.545 | 0.348 | 0.000 | 9.0 | 382.7 (334.2) | 31.72 | 382.7 | 173.3 | 209.4 |
| ripe | tit-for-tat | demand-noise | 1.000 | 1.000 | 0.545 | 0.307 | 0.031 | 10.0 | 335.0 (307.4) | 28.85 | 335.0 | 150.0 | 185.0 |
| ripe | penance-k3 | clean | 1.000 | 1.000 | 0.545 | 0.348 | 0.000 | 9.0 | 382.7 (334.2) | 31.72 | 382.7 | 173.3 | 209.4 |
| ripe | penance-k3 | demand-noise | 1.000 | 1.000 | 0.545 | 0.335 | 0.008 | 10.0 | 396.6 (359.8) | 31.75 | 345.8 | 166.7 | 229.9 |
| ripe | defect-once-8 | clean | 0.928 | 0.928 | 0.506 | 0.167 | 0.000 | 11.0 | 175.5 (66.3) | 21.15 | 175.5 | 83.3 | 92.2 |
| ripe | defect-once-8 | demand-noise | 0.933 | 0.933 | 0.509 | 0.164 | 0.026 | 11.0 | 176.6 (103.8) | 20.70 | 176.6 | 83.3 | 93.2 |
| ripe | always-compete | clean | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 15.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| ripe | always-compete | demand-noise | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 15.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| ripe | noise | clean | 0.300 | 0.858 | 0.415 | 0.040 | 0.000 | 14.0 | 34.5 (20.6) | 5.00 | 50.7 | 28.3 | 6.2 |
| ripe | noise | demand-noise | 0.301 | 0.860 | 0.417 | 0.040 | 0.000 | 14.0 | 35.3 (21.2) | 5.07 | 51.3 | 28.3 | 7.0 |
| unripe-a | grim | clean | 1.000 | 1.000 | 0.545 | 0.343 | 0.000 | 9.0 | 387.2 (336.0) | 31.72 | 387.2 | 1733.3 | -1346.2 |
| unripe-a | grim | demand-noise | 0.987 | 0.987 | 0.538 | 0.283 | 0.022 | 9.0 | 320.9 (300.8) | 28.08 | 320.9 | 1466.7 | -1145.8 |
| unripe-a | grim-hidden-fill | clean | 1.000 | 1.000 | 0.545 | 0.343 | 0.000 | 9.0 | 578.3 (557.7) | 41.94 | 193.8 | 1733.3 | -1155.0 |
| unripe-a | grim-hidden-fill | demand-noise | 0.990 | 0.990 | 0.540 | 0.118 | 0.015 | 11.0 | 174.0 (97.0) | 20.31 | 119.7 | 550.0 | -376.0 |
| unripe-a | tit-for-tat | clean | 1.000 | 1.000 | 0.545 | 0.343 | 0.000 | 9.0 | 387.2 (336.0) | 31.72 | 387.2 | 1733.3 | -1346.2 |
| unripe-a | tit-for-tat | demand-noise | 1.000 | 1.000 | 0.545 | 0.311 | 0.031 | 9.0 | 341.8 (314.6) | 29.07 | 341.8 | 1500.0 | -1158.2 |
| unripe-a | penance-k3 | clean | 1.000 | 1.000 | 0.545 | 0.343 | 0.000 | 9.0 | 387.2 (336.0) | 31.72 | 387.2 | 1733.3 | -1346.2 |
| unripe-a | penance-k3 | demand-noise | 1.000 | 1.000 | 0.545 | 0.335 | 0.009 | 9.0 | 397.4 (351.2) | 31.95 | 351.6 | 1683.3 | -1286.0 |
| unripe-a | defect-once-8 | clean | 0.929 | 0.929 | 0.506 | 0.136 | 0.000 | 11.0 | 175.2 (69.8) | 20.59 | 175.2 | 650.0 | -474.8 |
| unripe-a | defect-once-8 | demand-noise | 0.934 | 0.934 | 0.509 | 0.137 | 0.028 | 11.0 | 170.1 (82.0) | 20.09 | 170.1 | 650.0 | -479.9 |
| unripe-a | always-compete | clean | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 14.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a | always-compete | demand-noise | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 14.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a | noise | clean | 0.296 | 0.867 | 0.415 | 0.025 | 0.000 | 13.5 | 34.9 (19.1) | 5.82 | 46.6 | 133.3 | -98.5 |
| unripe-a | noise | demand-noise | 0.298 | 0.869 | 0.417 | 0.026 | 0.000 | 13.0 | 35.7 (20.4) | 5.93 | 47.7 | 150.0 | -114.3 |
| unripe-a-prime | grim | clean | 0.213 | 0.213 | 0.116 | 0.000 | 0.000 | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | grim | demand-noise | 0.221 | 0.221 | 0.120 | 0.000 | 0.000 | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | grim-hidden-fill | clean | 0.213 | 0.213 | 0.116 | 0.000 | 0.000 | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | grim-hidden-fill | demand-noise | 0.221 | 0.221 | 0.120 | 0.000 | 0.000 | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | tit-for-tat | clean | 0.213 | 0.213 | 0.116 | 0.000 | n/a | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | tit-for-tat | demand-noise | 0.341 | 0.341 | 0.186 | 0.000 | n/a | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | penance-k3 | clean | 1.000 | 1.000 | 0.545 | 0.322 | 0.000 | 9.0 | 626.6 (573.7) | 43.10 | 110.6 | 140.0 | 486.6 |
| unripe-a-prime | penance-k3 | demand-noise | 1.000 | 1.000 | 0.545 | 0.269 | 0.000 | 10.0 | 479.2 (446.4) | 31.18 | 84.6 | 113.3 | 365.9 |
| unripe-a-prime | defect-once-8 | clean | 0.916 | 0.916 | 0.499 | 0.000 | n/a | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | defect-once-8 | demand-noise | 0.916 | 0.916 | 0.499 | 0.000 | n/a | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | always-compete | clean | 0.000 | 0.000 | 0.000 | 0.000 | n/a | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | always-compete | demand-noise | 0.000 | 0.000 | 0.000 | 0.000 | n/a | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | noise | clean | 0.453 | 0.898 | 0.494 | 0.000 | n/a | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | noise | demand-noise | 0.453 | 0.898 | 0.494 | 0.000 | n/a | 13.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| n4 | grim | clean | 1.000 | 1.000 | 0.545 | 0.341 | 0.000 | 9.0 | 202.2 (159.5) | 15.86 | 202.2 | 166.7 | 35.5 |
| n4 | grim | demand-noise | 0.987 | 0.987 | 0.538 | 0.238 | 0.016 | 10.0 | 142.3 (121.4) | 12.43 | 142.3 | 105.0 | 37.3 |
| n4 | grim-hidden-fill | clean | 1.000 | 1.000 | 0.545 | 0.341 | 0.000 | 9.0 | 503.8 (478.8) | 32.31 | 100.9 | 166.7 | 337.2 |
| n4 | grim-hidden-fill | demand-noise | 0.989 | 0.989 | 0.539 | 0.117 | 0.011 | 11.0 | 104.6 (62.4) | 10.71 | 59.2 | 46.7 | 57.9 |
| n4 | tit-for-tat | clean | 1.000 | 1.000 | 0.545 | 0.341 | 0.000 | 9.0 | 202.2 (159.5) | 15.86 | 202.2 | 166.7 | 35.5 |
| n4 | tit-for-tat | demand-noise | 1.000 | 1.000 | 0.545 | 0.259 | 0.017 | 10.0 | 157.4 (132.5) | 13.38 | 157.4 | 121.7 | 35.7 |
| n4 | penance-k3 | clean | 1.000 | 1.000 | 0.545 | 0.341 | 0.000 | 9.0 | 202.2 (159.5) | 15.86 | 202.2 | 166.7 | 35.5 |
| n4 | penance-k3 | demand-noise | 1.000 | 1.000 | 0.545 | 0.261 | 0.009 | 9.5 | 158.6 (132.1) | 13.52 | 158.6 | 123.3 | 35.3 |
| n4 | defect-once-8 | clean | 0.927 | 0.927 | 0.505 | 0.143 | 0.000 | 10.0 | 91.6 (31.9) | 9.95 | 91.6 | 60.0 | 31.6 |
| n4 | defect-once-8 | demand-noise | 0.942 | 0.942 | 0.514 | 0.140 | 0.014 | 10.0 | 85.2 (35.6) | 9.43 | 85.2 | 58.3 | 26.9 |
| n4 | always-compete | clean | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 14.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| n4 | always-compete | demand-noise | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 14.0 | 0.0 (0.0) | 0.00 | 0.0 | 0.0 | 0.0 |
| n4 | noise | clean | 0.298 | 0.883 | 0.427 | 0.039 | 0.000 | 13.0 | 29.3 (16.1) | 4.32 | 17.9 | 18.3 | 11.0 |
| n4 | noise | demand-noise | 0.300 | 0.883 | 0.428 | 0.038 | 0.000 | 13.0 | 29.3 (16.4) | 4.27 | 18.2 | 16.7 | 12.7 |
| tick | grim | clean | 1.000 | 1.000 | 0.500 | 0.251 | 0.000 | 11.0 | 493.3 (406.9) | 34.38 | 493.3 | 121.7 | 371.6 |
| tick | grim | demand-noise | 0.981 | 0.981 | 0.484 | 0.196 | 0.025 | 11.0 | 377.8 (321.5) | 29.64 | 377.8 | 106.7 | 271.1 |
| tick | grim-hidden-fill | clean | 1.000 | 1.000 | 0.500 | 0.251 | 0.000 | 11.0 | 685.7 (612.0) | 43.65 | 235.2 | 121.7 | 564.0 |
| tick | grim-hidden-fill | demand-noise | 0.985 | 0.985 | 0.487 | 0.071 | 0.016 | 13.0 | 194.3 (99.2) | 20.28 | 135.9 | 43.3 | 151.0 |
| tick | tit-for-tat | clean | 1.000 | 1.000 | 0.500 | 0.251 | 0.000 | 11.0 | 493.3 (406.9) | 34.38 | 493.3 | 121.7 | 371.6 |
| tick | tit-for-tat | demand-noise | 1.000 | 1.000 | 0.500 | 0.218 | 0.028 | 11.0 | 441.7 (367.7) | 32.31 | 441.7 | 110.0 | 331.7 |
| tick | penance-k3 | clean | 1.000 | 1.000 | 0.500 | 0.251 | 0.000 | 11.0 | 493.3 (406.9) | 34.38 | 493.3 | 121.7 | 371.6 |
| tick | penance-k3 | demand-noise | 1.000 | 1.000 | 0.500 | 0.243 | 0.008 | 11.0 | 504.1 (424.7) | 34.75 | 452.7 | 121.7 | 382.4 |
| tick | defect-once-8 | clean | 0.922 | 0.922 | 0.461 | 0.088 | 0.000 | 12.5 | 218.1 (80.4) | 22.29 | 203.1 | 53.3 | 164.7 |
| tick | defect-once-8 | demand-noise | 0.927 | 0.927 | 0.463 | 0.093 | 0.023 | 12.0 | 222.0 (111.9) | 22.38 | 207.7 | 56.7 | 165.3 |
| tick | always-compete | clean | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 14.5 | 29.8 (0.0) | 4.57 | 5.2 | 0.0 | 29.8 |
| tick | always-compete | demand-noise | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 14.5 | 30.7 (5.3) | 4.65 | 5.4 | 0.0 | 30.7 |
| tick | noise | clean | 0.268 | 0.554 | 0.194 | 0.013 | 0.000 | 14.0 | 38.8 (26.8) | 5.54 | 44.3 | 8.3 | 30.5 |
| tick | noise | demand-noise | 0.274 | 0.561 | 0.201 | 0.015 | 0.002 | 14.0 | 40.9 (28.8) | 5.74 | 46.8 | 8.3 | 32.5 |

### Profit from colluding vs competing, and from breaking collusion (seat profit per run, mean of 300 runs)

All figures NET of fines (gross trading payoff minus fines; the engine records them separately). Premium = adhering (grim) minus always-compete. Breaking = defect-once-at-round-8 minus grim. Positive breaking gain means the one-off cheat paid in this market over the realised horizon.

| family | frictions | grim | always-compete | defect-once-8 | collusion premium | gain from breaking |
|---|---|---|---|---|---|---|
| ripe | clean | 209.4 | 0.0 | 92.2 | 209.4 | -117.2 |
| ripe | demand-noise | 158.0 | 0.0 | 93.2 | 158.0 | -64.8 |
| unripe-a | clean | -1346.2 | 0.0 | -474.8 | -1346.2 | 871.3 |
| unripe-a | demand-noise | -1145.8 | 0.0 | -479.9 | -1145.8 | 665.9 |
| unripe-a-prime | clean | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| unripe-a-prime | demand-noise | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| n4 | clean | 35.5 | 0.0 | 31.6 | 35.5 | -3.9 |
| n4 | demand-noise | 37.3 | 0.0 | 26.9 | 37.3 | -10.4 |
| tick | clean | 371.6 | 29.8 | 164.7 | 341.9 | -206.9 |
| tick | demand-noise | 271.1 | 30.7 | 165.3 | 240.4 | -105.8 |

## 3. Reference (null) bands for the pre-declared contrasts: scripted seats, 10 paraphrase-clusters × 3 seeds, 1,000 bootstrap resamples

| contrast | statistic | block | arm A | arm B | point | band lo | band hi | degenerate |
|---|---|---|---|---|---|---|---|---|
| P1-A | pAdhere | {seat=tit-for-tat} | ripe | unripe-a | 0.000 | 0.000 | 0.000 | true |
| P1-A | pAdhere | {seat=grim} | ripe | unripe-a | 0.000 | 0.000 | 0.000 | true |
| P1-A | pAdhere | {seat=noise} | ripe | unripe-a | 0.000 | 0.000 | 0.000 | true |
| P1-A-pCollude | pCollude | {seat=tit-for-tat} | ripe | unripe-a | 0.000 | 0.000 | 0.000 | true |
| P1-A-pCollude | pCollude | {seat=grim} | ripe | unripe-a | 0.000 | 0.000 | 0.000 | true |
| P1-A-pCollude | pCollude | {seat=noise} | ripe | unripe-a | 0.000 | 0.000 | 0.000 | true |
| P1-A-prime | meanCi | {seat=tit-for-tat} | ripe | unripe-a-prime | 0.432 | 0.391 | 0.466 | false |
| P1-A-prime | meanCi | {seat=grim} | ripe | unripe-a-prime | 0.430 | 0.387 | 0.466 | false |
| P1-A-prime | meanCi | {seat=noise} | ripe | unripe-a-prime | -0.095 | -0.160 | -0.026 | false |
| P3 | responder | {seat=tit-for-tat} | probe | control | 1.000 | 1.000 | 1.000 | true |
| P3 | responder | {seat=grim} | probe | control | 1.000 | 1.000 | 1.000 | true |
| P3 | responder | {seat=noise} | probe | control | 0.000 | 0.000 | 0.000 | true |
| P4 | pAdhere | {seat=tit-for-tat} | ripe | n4 | 0.000 | 0.000 | 0.000 | true |
| P4 | pAdhere | {seat=grim} | ripe | n4 | 0.000 | 0.000 | 0.000 | true |
| P4 | pAdhere | {seat=noise} | ripe | n4 | 0.000 | 0.000 | 0.000 | true |
| P4-gap | gap | {seat=tit-for-tat} | ripe | n4 | 0.000 | 0.000 | 0.000 | true |
| P4-gap | gap | {seat=grim} | ripe | n4 | 0.000 | 0.000 | 0.000 | true |
| P4-gap | gap | {seat=noise} | ripe | n4 | 0.000 | 0.000 | 0.000 | true |
| P5 | pAdhere | {seat=tit-for-tat} | ripe | p5-slope-0.055 | 0.000 | 0.000 | 0.000 | true |
| P5 | pAdhere | {seat=grim} | ripe | p5-slope-0.055 | 0.000 | 0.000 | 0.000 | true |
| P5 | pAdhere | {seat=noise} | ripe | p5-slope-0.055 | -0.007 | -0.033 | 0.000 | false |
