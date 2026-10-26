package io.github.tomloscalzo.collusion.mc;

/** Test fixtures: a tiny sweep (2 arms x 2 seats = 4 cells). */
final class Sweeps {
    private Sweeps() {}

    static final String TINY = """
            id: tiny
            masterSeed: 7
            runsPerCell: 20
            factors:
              - name: arm
                treatment: true
                levels:
                  - {label: ripe, base: scenarios/ripe-game.yaml, vars: {thetaP: 0.546}}
                  - {label: unripe-a, base: scenarios/unripe-a.yaml, vars: {thetaP: 0.546}}
              - name: seat
                treatment: false
                levels:
                  - {label: tft, agents: [{id: llm, kind: TIT_FOR_TAT, config: {theta: "${thetaP}"}}]}
                  - {label: noise, agents: [{id: llm, kind: NOISE}]}
            contrasts:
              - {name: c1, factor: arm, a: ripe, b: unripe-a, statistic: meanCi}
            band: {clusters: 3, seedsPerCluster: 2, resamples: 50, seed: 1}
            """;

    static final String PROBE = """
            id: probe-tiny
            masterSeed: 3
            runsPerCell: 60
            probeTs: [6, 7, 8, 9, 10]
            factors:
              - name: arm
                treatment: true
                levels:
                  - label: probe
                    base: scenarios/ripe-game.yaml
                    vars: {thetaP: 0.546}
                    probe: DEFECT
                    set: {detection.mode: "OFF"}
                    agents: [{id: partner, kind: DEFECT_ONCE, config: {theta: 0.546, t: 0}}]
                  - label: control
                    base: scenarios/ripe-game.yaml
                    vars: {thetaP: 0.546}
                    probe: CONTROL
                    set: {detection.mode: "OFF"}
                    agents: [{id: partner, kind: DEFECT_ONCE, config: {theta: 0.546, t: 0}}]
              - name: seat
                treatment: false
                levels:
                  - {label: tft, agents: [{id: llm, kind: TIT_FOR_TAT, config: {theta: "${thetaP}"}}]}
            contrasts:
              - {name: P3, factor: arm, a: probe, b: control, statistic: responder}
            """;
}
