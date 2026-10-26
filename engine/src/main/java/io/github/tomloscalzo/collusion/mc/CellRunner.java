package io.github.tomloscalzo.collusion.mc;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.analysis.Exporter;
import io.github.tomloscalzo.collusion.analysis.Metrics;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.engine.Game;
import io.github.tomloscalzo.collusion.engine.QuoteGrid;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.RunStatus;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.results.RoundRecord;
import io.github.tomloscalzo.collusion.results.RunRecord;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Runs the games of one cell and condenses each into a {@link RunResult} (thread-safe; Game holds no run state). */
public final class CellRunner {
    /** Per-run output. NaN means "not available" (excluded run, no signal evaluations, not a probe cell). */
    public record RunResult(int index, long seed, RunStatus status, int rounds, boolean shortRun, int warOnset, double pAdhere, double meanCi, double gapCi,
                            double pCollude, double falseAlarmRate, int signalEvaluations, int signalSeen,
                            int signalFalseAlarms, int probeT, Metrics.ProbeClass probeClass, String line,
                            String roundsCsv, String decisionsCsv) {}

    private final FactorialDesign design;
    private final FactorialDesign.Cell cell;
    private final boolean fullRuns;
    private final boolean export;
    private final Map<Integer, Game> probeGames = new TreeMap<>();
    private final Game game;
    private final String cellName;
    private final double sRef;

    public CellRunner(FactorialDesign design, FactorialDesign.Cell cell, boolean fullRuns, boolean export) {
        this.design = design;
        this.cell = cell;
        this.fullRuns = fullRuns;
        this.export = export;
        double thetaP = Metrics.HELD_THETA_P; // held partner margin unless a non-seat agent of the cell carries its own theta
        for (AgentSpec a : cell.config().agents()) {
            if (!a.id().equals(design.seat()) && a.config().get("theta") instanceof Number th) {
                thetaP = th.doubleValue();
                break;
            }
        }
        var mk = cell.config().scenario().market();
        this.sRef = QuoteGrid.snap(mk, PayoffFunctions.margin(mk, thetaP));
        this.cellName = "c" + String.format("%04d", cell.index());
        if (cell.probe() == FactorialDesign.Probe.NONE) {
            this.game = new Game(cell.config());
        } else {
            this.game = null;
            for (int t : design.probeTs()) {
                long tt = cell.probe() == FactorialDesign.Probe.DEFECT ? t : 0L;
                List<AgentSpec> ags = new ArrayList<>();
                for (AgentSpec a : cell.config().agents()) {
                    ags.add(a.id().equals(design.partner()) ? a.with("t", tt) : a);
                }
                probeGames.put(t, new Game(cell.config().withAgents(ags)));
            }
        }
    }

    public String cellName() {
        return cellName;
    }

    public RunResult run(int index) {
        long seed = design.runSeed(cell.blockId(), index);
        int probeT = -1;
        Game g = game;
        if (cell.probe() != FactorialDesign.Probe.NONE) {
            probeT = design.probeT(index);
            g = probeGames.get(probeT);
        }
        RunRecord run = g.run(seed);
        Metrics.RunLevel rl = Metrics.runLevel(run, design.seat(), design.partner(), sRef);
        Metrics.ProbeClass pc = probeT < 0 ? null : Metrics.classify(run, design.seat(), design.partner(), probeT);
        double far = run.signalEvaluations() == 0 ? Double.NaN : run.emergentFalseAlarmRate();

        ObjectNode n = fullRuns ? run.toJson() : Canonical.MAPPER.createObjectNode();
        if (!fullRuns) {
            n.put("scenarioId", run.scenarioId());
            n.put("seed", seed);
            n.put("status", run.status().name());
            n.put("signalEvaluations", run.signalEvaluations());
            n.put("signalSeen", run.signalSeen());
            n.put("signalFalseAlarms", run.signalFalseAlarms());
            n.put("terminalValue", run.terminalValue());
            n.put("replayDigest", run.replayDigest());
        }
        n.put("cell", cellName);
        n.put("cellKey", cell.key());
        n.put("seedIndex", index);
        n.put("rounds", fullRuns ? run.rounds().size() : run.rounds().size());
        n.put("shortRun", rl.shortRun());
        put(n, "gapCi", rl.gapCi());
        put(n, "pAdhere", rl.pAdhere());
        n.put("warOnsetRound", rl.warOnsetRound());
        put(n, "meanCi", rl.meanOwnCi());
        put(n, "pCollude", rl.pCollude());
        put(n, "falseAlarmRate", far);
        if (probeT >= 0) {
            n.put("probeT", probeT);
            n.put("probeClass", pc.name());
        }
        ArrayNode own = n.putArray("ownCi");
        ArrayNode inside = n.putArray("insideCi");
        for (RoundRecord r : run.rounds()) {
            own.add(r.agent(design.seat()).ownCi());
            inside.add(r.insideCi());
        }
        String rc = "";
        String dc = "";
        if (export) {
            StringBuilder sr = new StringBuilder();
            StringBuilder sd = new StringBuilder();
            Exporter.rounds(sr, cellName, index, run);
            Exporter.decisions(sd, cellName, index, run);
            rc = sr.toString();
            dc = sd.toString();
        }
        return new RunResult(index, seed, run.status(), run.rounds().size(), rl.shortRun(), rl.warOnsetRound(), rl.pAdhere(), rl.meanOwnCi(), rl.gapCi(),
                rl.pCollude(), far, run.signalEvaluations(), run.signalSeen(), run.signalFalseAlarms(), probeT, pc,
                Canonical.text(n), rc, dc);
    }

    private static void put(ObjectNode n, String f, double v) {
        if (Double.isNaN(v)) {
            n.putNull(f);
        } else {
            n.put(f, v);
        }
    }
}
