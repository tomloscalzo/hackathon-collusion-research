package io.github.tomloscalzo.collusion.mc;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import io.github.tomloscalzo.collusion.core.layera.CartelSolution;
import io.github.tomloscalzo.collusion.core.layera.CartelSolver;
import io.github.tomloscalzo.collusion.core.layera.Enforcement;
import io.github.tomloscalzo.collusion.core.layera.HazardBreakdown;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.core.model.TimeParams;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoadException;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoader;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The deterministic ripeness map (TEST_PLAN 3): the Layer A solver over a factorial grid of the closed parameter set
 * {delta, N, phi, tick, slope, rhoTip, pEvidence, fineRatio, sBarRatio}; unnamed parameters keep the base scenario's
 * value. delta sets the random-horizon hazard h = 1 - delta with delta0 = 1; pEvidence is P(evidence | trigger)
 * (scenario rhoCoop at dBarU = 0, T39); fineRatio is F / pi_c(1) in the cell's market; sBarRatio is sBar / s0.
 * Grid YAML: {id, base, parameters: {name: [levels]}}; the last parameter varies fastest. Output columns include the
 * overcharge (s(theta*) - s0)/s0 beside CI = theta* (T29), the evidence share of detection ends at theta* and the
 * expected cartel duration 1 / (1 - (1 - h)(1 - rhoTrigger(theta*))) rounds (blank for a known horizon or theta* = 0).
 */
public final class RipenessGrid {
    private static final YAMLMapper YAML = new YAMLMapper();
    private static final List<String> NAMES = List.of("delta", "N", "phi", "tick", "slope", "rhoTip", "pEvidence",
            "fineRatio", "sBarRatio");

    private final String id;
    private final Scenario base;
    private final Map<String, List<Double>> params = new LinkedHashMap<>();

    private RipenessGrid(String id, Scenario base) {
        this.id = id;
        this.base = base;
    }

    public String id() { return id; }

    public int size() {
        int n = 1;
        for (List<Double> l : params.values()) {
            n *= l.size();
        }
        return n;
    }

    public static RipenessGrid load(Path file) {
        try {
            return parse(Files.readString(file, StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read grid " + file + ": " + e.getMessage(), e);
        }
    }

    public static RipenessGrid loadResource(String name) {
        try (InputStream in = RipenessGrid.class.getClassLoader().getResourceAsStream(name)) {
            if (in == null) {
                throw new ScenarioLoadException("Resource not found: " + name);
            }
            return parse(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read resource " + name + ": " + e.getMessage(), e);
        }
    }

    public static RipenessGrid parse(String yaml) {
        try {
            JsonNode root = YAML.readTree(yaml);
            Iterator<String> it = root.fieldNames();
            while (it.hasNext()) {
                String f = it.next();
                if (!Set.of("id", "base", "parameters").contains(f)) {
                    throw new ScenarioLoadException("Unknown key '" + f + "' in grid");
                }
            }
            if (!root.hasNonNull("id") || !root.hasNonNull("base") || !root.has("parameters")) {
                throw new ScenarioLoadException("grid requires id, base and parameters");
            }
            String baseName = root.get("base").asText();
            Path p = Path.of(baseName);
            Scenario base = Files.isRegularFile(p) ? ScenarioLoader.load(p) : ScenarioLoader.loadResource(baseName);
            RipenessGrid g = new RipenessGrid(root.get("id").asText(), base);
            Iterator<Map.Entry<String, JsonNode>> pit = root.get("parameters").fields();
            while (pit.hasNext()) {
                var e = pit.next();
                if (!NAMES.contains(e.getKey())) {
                    throw new ScenarioLoadException("Unknown grid parameter '" + e.getKey() + "'; allowed " + NAMES);
                }
                List<Double> lv = new ArrayList<>();
                for (JsonNode v : e.getValue()) {
                    if (!v.isNumber()) {
                        throw new ScenarioLoadException("Grid levels of " + e.getKey() + " must be numeric");
                    }
                    lv.add(v.asDouble());
                }
                if (lv.isEmpty()) {
                    throw new ScenarioLoadException("Grid parameter " + e.getKey() + " has no levels");
                }
                g.params.put(e.getKey(), lv);
            }
            return g;
        } catch (IOException e) {
            throw new ScenarioLoadException("Invalid grid YAML: " + e.getMessage(), e);
        }
    }

    public String header() {
        StringBuilder sb = new StringBuilder("cell");
        for (String k : params.keySet()) {
            sb.append(',').append(k);
        }
        sb.append(",theta_hat,theta_star,theta_star_given_participation,ripeness_E,regime,w_star,w0,myopic_unripe,")
                .append("multiple_stage_nash,s_star,overcharge,ci_star,p_trigger_star,p_evidence_given_trigger_star,")
                .append("expected_duration,error");
        return sb.toString();
    }

    /** The scenario of cell c (row-major, last parameter fastest) and its parameter values. */
    private Scenario cell(int c, double[] vals) {
        int rem = c;
        int k = params.size();
        int i = k - 1;
        List<Map.Entry<String, List<Double>>> es = new ArrayList<>(params.entrySet());
        for (; i >= 0; i--) {
            List<Double> lv = es.get(i).getValue();
            vals[i] = lv.get(rem % lv.size());
            rem /= lv.size();
        }
        Map<String, Double> v = new LinkedHashMap<>();
        for (int j = 0; j < k; j++) {
            v.put(es.get(j).getKey(), vals[j]);
        }
        Scenario s = base;
        MarketParams m = s.market();
        if (v.containsKey("N")) {
            m = m.withN((int) Math.round(v.get("N")));
        }
        if (v.containsKey("phi")) {
            m = m.withPhi(v.get("phi"));
        }
        if (v.containsKey("tick")) {
            m = m.withTick(v.get("tick"));
        }
        if (v.containsKey("sBarRatio")) {
            m = m.withSBar(v.get("sBarRatio") * m.s0());
        }
        s = s.withMarket(m);
        if (v.containsKey("delta")) {
            s = s.withTime(new TimeParams(1.0, s.time().entryHazard(), new Horizon.Random(1.0 - v.get("delta")),
                    s.time().maxRounds()));
        }
        var e = s.enforcement();
        if (v.containsKey("slope")) {
            e = e.withScreen(e.screen().withSlope(v.get("slope")));
        }
        if (v.containsKey("rhoTip")) {
            e = e.withRhoTip(v.get("rhoTip"));
        }
        if (v.containsKey("pEvidence")) {
            e = e.withRhoCoop(v.get("pEvidence"));
        }
        if (v.containsKey("fineRatio")) {
            e = e.withFine(v.get("fineRatio") * PayoffFunctions.piC(m, 1.0));
        }
        return s.withEnforcement(e);
    }

    /** The CSV row of cell c; solver failures are reported in the error column, never thrown. */
    public String row(int c) {
        double[] vals = new double[params.size()];
        StringBuilder sb = new StringBuilder();
        Scenario s;
        try {
            s = cell(c, vals);
        } catch (RuntimeException ex) {
            return c + ",".repeat(params.size() + 15) + "," + CellSummary.csv(String.valueOf(ex.getMessage()));
        }
        sb.append(c);
        for (double x : vals) {
            sb.append(',').append(x);
        }
        try {
            ScenarioLoader.validate(s);
            CartelSolution sol = new CartelSolver().solve(s);
            MarketParams m = s.market();
            double th = sol.thetaStar();
            double sStar = PayoffFunctions.margin(m, th);
            double sN = PayoffFunctions.nashMargin(m);
            double pt = Double.NaN;
            double pe = Double.NaN;
            double dur = Double.NaN;
            if (th > 0) {
                HazardBreakdown h = Enforcement.hazard(s.enforcement(), sStar - sN,
                        PayoffFunctions.collusionIndex(m, sStar), s.aggregates().dBarU());
                pt = h.pTrigger();
                pe = h.pEvidenceGivenTrigger();
                if (s.time().horizon() instanceof Horizon.Random r) {
                    dur = 1.0 / (1.0 - (1.0 - r.h()) * (1.0 - pt));
                }
            }
            sb.append(',').append(CellSummary.num(sol.thetaHat())).append(',').append(CellSummary.num(th)).append(',')
                    .append(CellSummary.num(sol.thetaStarGivenParticipation())).append(',')
                    .append(CellSummary.num(sol.ripeness())).append(',').append(sol.regime()).append(',')
                    .append(CellSummary.num(sol.wStar())).append(',').append(CellSummary.num(sol.w0())).append(',')
                    .append(sol.myopicallyUnripe()).append(',').append(sol.multipleStageNash()).append(',')
                    .append(CellSummary.num(sStar)).append(',').append(CellSummary.num((sStar - m.s0()) / m.s0()))
                    .append(',').append(CellSummary.num(th)).append(',').append(CellSummary.num(pt)).append(',')
                    .append(CellSummary.num(pe)).append(',').append(CellSummary.num(dur)).append(',');
        } catch (RuntimeException ex) {
            sb.append(",".repeat(15)).append(',').append(CellSummary.csv(String.valueOf(ex.getMessage())));
        }
        return sb.toString();
    }

    /** Solves every cell on the pool and writes the CSV (row order = cell order). */
    public void write(Path out, int threads) throws IOException {
        List<String> rows;
        try (MonteCarloRunner pool = new MonteCarloRunner(threads)) {
            rows = pool.map(size(), this::row);
        }
        StringBuilder sb = new StringBuilder(header()).append('\n');
        for (String r : rows) {
            sb.append(r).append('\n');
        }
        Files.writeString(out, sb.toString(), StandardCharsets.UTF_8);
    }
}
