package io.github.tomloscalzo.collusion.mc;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.analysis.Exporter;
import io.github.tomloscalzo.collusion.analysis.ReferenceBand;
import io.github.tomloscalzo.collusion.mc.CellRunner.RunResult;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.results.Manifest;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * Headless batch runner: {@code batch --sweep file.yaml --threads N --out dir [--runs N] [--full-runs] [--export]}.
 *
 * <p>Outputs in dir: {@code runs/cNNNN.jsonl} (one line per run, with replayDigest; compact by default, the complete
 * RunRecord with --full-runs), {@code summary.csv} (one row per cell, appended after the cell's runs are written),
 * {@code bands.csv} (reference bands of the sweep's contrasts), {@code manifest.json}, and with --export the long CSVs
 * {@code export/rounds-cNNNN.csv} and {@code export/decisions-cNNNN.csv}. Resumable: a cell whose cell_key is already a
 * row of summary.csv is skipped (the key hashes the cell's composed game, labels and run count).
 */
public final class BatchMain {
    private BatchMain() {}

    public record Result(int cellsTotal, int cellsRun, int cellsSkipped, Path summary) {}

    public static void main(String[] args) throws Exception {
        Map<String, String> o = new TreeMap<>();
        for (int i = 0; i < args.length; i++) {
            String a = args[i];
            if (a.equals("--full-runs") || a.equals("--export")) {
                o.put(a.substring(2), "true");
            } else if (a.startsWith("--") && i + 1 < args.length) {
                o.put(a.substring(2), args[++i]);
            } else {
                usage();
                System.exit(2);
            }
        }
        if (!o.containsKey("sweep") || !o.containsKey("out")) {
            usage();
            System.exit(2);
        }
        int threads = o.containsKey("threads") ? Integer.parseInt(o.get("threads"))
                : Runtime.getRuntime().availableProcessors();
        Integer runs = o.containsKey("runs") ? Integer.valueOf(o.get("runs")) : null;
        Result r = execute(Path.of(o.get("sweep")), Path.of(o.get("out")), threads, runs, o.containsKey("full-runs"),
                o.containsKey("export"), true);
        System.out.println("cells " + r.cellsTotal() + ", run " + r.cellsRun() + ", skipped " + r.cellsSkipped());
    }

    private static void usage() {
        System.err.println("usage: batch --sweep <file.yaml> --out <dir> [--threads N] [--runs N] [--full-runs] [--export]");
    }

    public static Result execute(Path sweep, Path out, int threads, Integer runsOverride, boolean fullRuns,
                                 boolean export, boolean log) throws IOException {
        long t0 = System.nanoTime();
        FactorialDesign design = Files.isRegularFile(sweep) ? FactorialDesign.load(sweep)
                : FactorialDesign.loadResource(sweep.toString().replace(java.io.File.separatorChar, '/'));
        if (runsOverride != null) {
            design = design.withRunsPerCell(runsOverride);
        }
        Files.createDirectories(out.resolve("runs"));
        if (export) {
            Files.createDirectories(out.resolve("export"));
        }
        Path summary = out.resolve("summary.csv");
        String header = CellSummary.header(design);
        Set<String> done = new HashSet<>();
        if (Files.exists(summary)) {
            List<String> lines = Files.readAllLines(summary, StandardCharsets.UTF_8);
            if (lines.isEmpty() || !lines.get(0).equals(header)) {
                throw new IOException("summary.csv in " + out + " has a different header; use a fresh --out directory");
            }
            for (int i = 1; i < lines.size(); i++) {
                String[] f = lines.get(i).split(",", 3);
                if (f.length > 1) {
                    done.add(f[1]);
                }
            }
        } else {
            Files.writeString(summary, header + "\n", StandardCharsets.UTF_8);
        }
        int run = 0;
        int skipped = 0;
        try (MonteCarloRunner pool = new MonteCarloRunner(threads)) {
            for (FactorialDesign.Cell cell : design.cells()) {
                if (done.contains(cell.key())) {
                    skipped++;
                    continue;
                }
                CellRunner cr = new CellRunner(design, cell, fullRuns, export);
                List<RunResult> results = pool.map(design.runsPerCell(), cr::run);
                String name = cr.cellName();
                writeAtomically(out.resolve("runs").resolve(name + ".jsonl"), join(results, 0));
                if (export) {
                    StringBuilder r = new StringBuilder(Exporter.ROUNDS_HEADER).append('\n');
                    StringBuilder d = new StringBuilder(Exporter.DECISIONS_HEADER).append('\n');
                    for (RunResult x : results) {
                        r.append(x.roundsCsv());
                        d.append(x.decisionsCsv());
                    }
                    writeAtomically(out.resolve("export").resolve("rounds-" + name + ".csv"), r.toString());
                    writeAtomically(out.resolve("export").resolve("decisions-" + name + ".csv"), d.toString());
                }
                Files.writeString(summary, CellSummary.row(cell, results) + "\n", StandardCharsets.UTF_8,
                        StandardOpenOption.APPEND);
                run++;
                if (log) {
                    System.out.println("cell " + cell.index() + "/" + design.cells().size() + " " + cell.name());
                }
            }
        }
        writeBands(design, out);
        Map<String, String> opts = new TreeMap<>();
        opts.put("fullRuns", Boolean.toString(fullRuns));
        opts.put("export", Boolean.toString(export));
        opts.put("sweepFile", sweep.toString());
        new Manifest("collusion-engine batch", Manifest.currentGitCommit(), design.id(), design.masterSeed(),
                design.sweepHash(), design.scenarioHashes(), design.runsPerCell(), threads, design.cells().size(), run,
                skipped, (System.nanoTime() - t0) / 1_000_000, Instant.now().toString(),
                System.getProperty("java.version"), opts).write(out.resolve("manifest.json"));
        return new Result(design.cells().size(), run, skipped, summary);
    }

    private static String join(List<RunResult> rs, int unused) {
        StringBuilder sb = new StringBuilder();
        for (RunResult r : rs) {
            sb.append(r.line()).append('\n');
        }
        return sb.toString();
    }

    private static void writeAtomically(Path file, String content) throws IOException {
        Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
        Files.writeString(tmp, content, StandardCharsets.UTF_8);
        Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING);
    }

    // ------------------------------------------------------------------ reference bands

    private record Arm(double[] stat, boolean[] incl) {}

    private static void writeBands(FactorialDesign design, Path out) throws IOException {
        if (design.contrasts().isEmpty()) {
            return;
        }
        var spec = design.band();
        StringBuilder sb = new StringBuilder("contrast,statistic,block,arm_a,arm_b,n_a,n_b,point_full,"
                + "band_lo,band_hi,band_mean,band_sd,degenerate,clusters,seeds_per_cluster,resamples,seed\n");
        for (var c : design.contrasts()) {
            for (FactorialDesign.Cell ca : design.cells()) {
                if (!ca.labels().get(c.factor()).equals(c.a())) {
                    continue;
                }
                Map<String, String> want = new LinkedHashMap<>(ca.labels());
                want.put(c.factor(), c.b());
                FactorialDesign.Cell cb = design.cells().stream().filter(x -> x.labels().equals(want)).findFirst()
                        .orElseThrow();
                Arm a = load(out, ca, design.runsPerCell(), c.statistic());
                Arm b = load(out, cb, design.runsPerCell(), c.statistic());
                var band = ReferenceBand.compute(a.stat(), a.incl(), b.stat(), b.incl(), spec.clusters(),
                        spec.seedsPerCluster(), spec.resamples(), spec.seed());
                Map<String, String> block = new LinkedHashMap<>(ca.labels());
                block.remove(c.factor());
                sb.append(CellSummary.csv(c.name())).append(',').append(c.statistic()).append(',')
                        .append(CellSummary.csv(block.toString())).append(',').append(CellSummary.csv(c.a())).append(',')
                        .append(CellSummary.csv(c.b())).append(',').append(count(a.incl())).append(',')
                        .append(count(b.incl())).append(',').append(CellSummary.num(band.point())).append(',')
                        .append(CellSummary.num(band.lo())).append(',').append(CellSummary.num(band.hi())).append(',')
                        .append(CellSummary.num(band.mean())).append(',').append(CellSummary.num(band.sd())).append(',')
                        .append(band.degenerate()).append(',').append(spec.clusters()).append(',')
                        .append(spec.seedsPerCluster()).append(',').append(spec.resamples()).append(',')
                        .append(spec.seed()).append('\n');
            }
        }
        writeAtomically(out.resolve("bands.csv"), sb.toString());
    }

    private static int count(boolean[] b) {
        int c = 0;
        for (boolean x : b) {
            c += x ? 1 : 0;
        }
        return c;
    }

    private static Arm load(Path out, FactorialDesign.Cell cell, int n, String statistic) throws IOException {
        Path f = out.resolve("runs").resolve("c" + String.format("%04d", cell.index()) + ".jsonl");
        List<String> lines = Files.readAllLines(f, StandardCharsets.UTF_8);
        if (lines.size() != n) {
            throw new IOException(f + " has " + lines.size() + " runs, expected " + n);
        }
        double[] stat = new double[n];
        boolean[] incl = new boolean[n];
        List<JsonNode> nodes = new ArrayList<>();
        for (String l : lines) {
            nodes.add(Canonical.MAPPER.readTree(l));
        }
        for (JsonNode j : nodes) {
            int i = j.get("seedIndex").asInt();
            switch (statistic) {
                case "pAdhere", "meanCi", "pCollude", "gap" -> {
                    incl[i] = true;
                    stat[i] = j.get(statistic.equals("gap") ? "gapCi" : statistic).asDouble();
                }
                default -> {
                    String pc = j.has("probeClass") ? j.get("probeClass").asText() : "";
                    incl[i] = pc.equals("RESPONDER") || pc.equals("NON_RESPONDER");
                    stat[i] = pc.equals("RESPONDER") ? 1.0 : 0.0;
                }
            }
        }
        return new Arm(stat, incl);
    }
}
