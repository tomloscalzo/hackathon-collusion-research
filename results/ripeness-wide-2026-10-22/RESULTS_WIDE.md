# Wide ripeness map: Layer A solver over the expanded parameter landscape

1,036,800 cells; non-LLM, model-generated. Regimes: CORNER_ZERO 718,914, INTERIOR_EXTERNAL 158,916, CORNER_ONE 99,079, INTERIOR_INTERNAL 59,891

## Which inputs drive each outcome (main-effect share of variance, eta²)

| Outcome | delta | N | phi | tick | slope | rhoTip | pEvidence | fineRatio | sBarRatio |
|---|---|---|---|---|---|---|---|---|---|
| P(collusion chosen, θ*>0) | 0.02 | 0.02 | 0.00 | 0.03 | 0.08 | 0.03 | 0.02 | **0.23** | 0.00 |
| θ* (chosen intensity) | 0.02 | 0.02 | 0.00 | 0.02 | **0.17** | 0.02 | 0.01 | **0.16** | 0.01 |
| Ripeness E | 0.02 | 0.01 | 0.00 | 0.08 | **0.12** | 0.02 | 0.01 | **0.17** | 0.00 |
| P(trigger)/round | 0.01 | 0.02 | 0.00 | 0.00 | **0.36** | **0.19** | 0.00 | **0.15** | 0.09 |
| P(detected)/round | 0.00 | 0.01 | 0.00 | 0.00 | **0.16** | 0.09 | **0.19** | **0.17** | 0.04 |
| Expected duration (rounds) | **0.50** | 0.01 | 0.00 | 0.00 | 0.09 | 0.05 | 0.00 | 0.04 | 0.00 |
| Collusive rent W*−W0 | 0.03 | 0.01 | 0.00 | 0.00 | 0.06 | 0.01 | 0.00 | 0.01 | 0.01 |
| Myopically unripe share | 0.00 | 0.00 | 0.00 | 0.01 | 0.07 | 0.03 | 0.06 | **0.41** | 0.05 |

Bold = explains ≥10% of the variance on its own.

## Outcome by input level (means over all other inputs)

**Patience δ (continuation probability)**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 0.5 | 0.170 | 0.103 | 0.061 | 0.051 | 0.019 | 1.9 | 5.1 | 0.434 |
| 0.7 | 0.279 | 0.194 | 0.123 | 0.059 | 0.023 | 3.0 | 13.2 | 0.434 |
| 0.8 | 0.338 | 0.243 | 0.157 | 0.061 | 0.024 | 4.2 | 20.8 | 0.434 |
| 0.9 | 0.367 | 0.264 | 0.178 | 0.059 | 0.025 | 7.2 | 36.7 | 0.434 |
| 0.95 | 0.343 | 0.242 | 0.171 | 0.054 | 0.024 | 12.1 | 58.3 | 0.434 |
| 0.99 | 0.269 | 0.173 | 0.137 | 0.043 | 0.021 | 38.6 | 163.5 | 0.434 |

**Number of market makers N**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 2.0 | 0.348 | 0.265 | 0.169 | 0.067 | 0.028 | 9.5 | 88.8 | 0.424 |
| 3.0 | 0.346 | 0.249 | 0.167 | 0.060 | 0.025 | 9.7 | 63.5 | 0.433 |
| 4.0 | 0.317 | 0.217 | 0.150 | 0.056 | 0.023 | 10.3 | 48.4 | 0.438 |
| 6.0 | 0.266 | 0.169 | 0.120 | 0.047 | 0.020 | 11.7 | 30.6 | 0.438 |
| 10.0 | 0.194 | 0.115 | 0.083 | 0.039 | 0.017 | 15.0 | 16.7 | 0.438 |

**Preferenced volume share φ**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.263 | 0.174 | 0.121 | 0.051 | 0.021 | 11.9 | 51.2 | 0.438 |
| 0.3 | 0.293 | 0.200 | 0.136 | 0.054 | 0.023 | 10.9 | 49.6 | 0.435 |
| 0.6 | 0.327 | 0.235 | 0.156 | 0.060 | 0.025 | 10.0 | 48.0 | 0.430 |

**Price tick size**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.380 | 0.258 | 0.242 | 0.059 | 0.023 | 11.3 | 71.8 | 0.489 |
| 0.25 | 0.306 | 0.211 | 0.108 | 0.051 | 0.022 | 10.6 | 44.6 | 0.440 |
| 0.5 | 0.198 | 0.140 | 0.063 | 0.054 | 0.025 | 10.4 | 32.4 | 0.375 |

**Regulator screen slope**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.553 | 0.525 | 0.352 | 0.013 | 0.005 | 19.2 | 258.2 | 0.194 |
| 0.01 | 0.430 | 0.326 | 0.210 | 0.029 | 0.012 | 12.2 | 61.9 | 0.295 |
| 0.025 | 0.345 | 0.233 | 0.153 | 0.045 | 0.019 | 9.4 | 30.8 | 0.373 |
| 0.05 | 0.275 | 0.165 | 0.112 | 0.066 | 0.027 | 7.4 | 16.6 | 0.443 |
| 0.075 | 0.236 | 0.130 | 0.090 | 0.080 | 0.032 | 6.7 | 11.2 | 0.486 |
| 0.1 | 0.204 | 0.105 | 0.076 | 0.094 | 0.039 | 6.1 | 8.4 | 0.520 |
| 0.15 | 0.169 | 0.079 | 0.060 | 0.115 | 0.048 | 5.6 | 5.6 | 0.565 |
| 0.2 | 0.144 | 0.061 | 0.049 | 0.134 | 0.058 | 5.0 | 4.1 | 0.599 |

**Tipping probability per round ρ_tip**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.385 | 0.254 | 0.181 | 0.033 | 0.014 | 14.7 | 91.1 | 0.342 |
| 0.01 | 0.303 | 0.212 | 0.139 | 0.053 | 0.022 | 9.4 | 41.7 | 0.424 |
| 0.05 | 0.196 | 0.143 | 0.092 | 0.104 | 0.044 | 5.4 | 15.9 | 0.538 |

**P(evidence | investigation)**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 0.1 | 0.392 | 0.264 | 0.184 | 0.061 | 0.006 | 9.7 | 58.8 | 0.251 |
| 0.3 | 0.301 | 0.207 | 0.139 | 0.054 | 0.016 | 10.7 | 49.5 | 0.403 |
| 0.6 | 0.252 | 0.176 | 0.116 | 0.051 | 0.031 | 11.5 | 45.1 | 0.506 |
| 1.0 | 0.233 | 0.165 | 0.112 | 0.053 | 0.053 | 12.4 | 45.0 | 0.578 |

**Fine ratio (fine ÷ one round of full-collusion profit per firm)**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.674 | 0.450 | 0.370 | 0.084 | 0.045 | 7.9 | 95.8 | 0.000 |
| 5.0 | 0.548 | 0.364 | 0.244 | 0.063 | 0.025 | 9.2 | 73.7 | 0.048 |
| 12.5 | 0.408 | 0.279 | 0.173 | 0.049 | 0.014 | 10.6 | 59.6 | 0.185 |
| 25.0 | 0.294 | 0.205 | 0.123 | 0.038 | 0.008 | 12.0 | 48.9 | 0.358 |
| 50.0 | 0.203 | 0.146 | 0.083 | 0.026 | 0.005 | 14.2 | 39.6 | 0.525 |
| 125.0 | 0.113 | 0.085 | 0.047 | 0.013 | 0.002 | 17.5 | 29.9 | 0.701 |
| 250.0 | 0.069 | 0.054 | 0.033 | 0.005 | 0.001 | 21.1 | 25.7 | 0.804 |
| 500.0 | 0.048 | 0.041 | 0.027 | 0.002 | 0.000 | 23.7 | 23.7 | 0.854 |

**Reservation spread ratio s̄/s₀**

| level | P(collusion chosen, θ*>0) | θ* (chosen intensity) | Ripeness E | P(trigger)/round | P(detected)/round | Expected duration (rounds) | Collusive rent W*−W0 | Myopically unripe share |
|---|---|---|---|---|---|---|---|---|
| 2.0 | 0.240 | 0.204 | 0.125 | 0.030 | 0.013 | 12.8 | 6.1 | 0.232 |
| 3.0 | 0.319 | 0.248 | 0.140 | 0.039 | 0.017 | 11.5 | 16.1 | 0.399 |
| 5.0 | 0.328 | 0.218 | 0.149 | 0.054 | 0.023 | 10.5 | 38.7 | 0.457 |
| 8.0 | 0.304 | 0.185 | 0.143 | 0.069 | 0.028 | 10.0 | 72.1 | 0.515 |
| 12.0 | 0.281 | 0.161 | 0.133 | 0.083 | 0.034 | 9.8 | 115.0 | 0.569 |
