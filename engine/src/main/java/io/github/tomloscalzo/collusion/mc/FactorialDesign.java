package io.github.tomloscalzo.collusion.mc;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoadException;
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
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * A factorial sweep: a base game YAML, factors with levels (each factor flagged treatment: true/false, T14), the
 * seat/partner ids, the number of runs per cell and the master seed. Cells are the Cartesian product, the first factor
 * varying slowest. crnBlockId = hash of the non-treatment factor labels, so all treatment arms of one block share the
 * run seeds (and therefore every name-hashed demand / horizon / detection / noise stream) at the same seed index.
 *
 * <p>Sweep file keys (unknown keys fail): id, base, masterSeed, runsPerCell, seat, partner, probeTs, factors, contrasts,
 * band. A factor is {name, treatment, levels}; a level is {label, base?, vars?, set?, agents?, probe?}:
 * base replaces the game document (put such a factor first); vars define numbers that "${name}" string values refer to;
 * set maps dotted paths to values (observation.demandNoiseSd: 5); agents is a list of {id, kind?, category?, config?}
 * where a known id is changed (a given kind replaces the kind and the whole config, config alone merges) and an unknown
 * id is appended; probe is DEFECT or CONTROL (the probe partner's defection round t comes from probeTs by seed index).
 */
public final class FactorialDesign {
    private static final YAMLMapper YAML = new YAMLMapper();
    private static final Pattern VAR = Pattern.compile("^\\$\\{(\\w+)}$");
    private static final Set<String> TOP = Set.of("id", "base", "masterSeed", "runsPerCell", "seat", "partner", "probeTs",
            "factors", "contrasts", "band");
    private static final Set<String> STATS = Set.of("pAdhere", "meanCi", "pCollude", "gap", "responder");

    public enum Probe { NONE, DEFECT, CONTROL }

    public record Level(String label, JsonNode spec) {}

    public record Factor(String name, boolean treatment, List<Level> levels) {}

    public record Contrast(String name, String factor, String a, String b, String statistic) {}

    public record BandSpec(int clusters, int seedsPerCluster, int resamples, long seed) {}

    /** One cell. labels are factor name to level label in factor order; config is the composed game. */
    public record Cell(int index, Map<String, String> labels, String blockId, String key, GameConfig config,
                       JsonNode tree, Probe probe) {
        public String name() {
            StringBuilder sb = new StringBuilder();
            for (var e : labels.entrySet()) {
                if (sb.length() > 0) {
                    sb.append('|');
                }
                sb.append(e.getKey()).append('=').append(e.getValue());
            }
            return sb.toString();
        }
    }

    private final String id;
    private final long masterSeed;
    private final int runsPerCell;
    private final String seat;
    private final String partner;
    private final List<Integer> probeTs;
    private final List<Factor> factors;
    private final List<Contrast> contrasts;
    private final BandSpec band;
    private final String sweepHash;
    private final Map<String, String> scenarioHashes = new TreeMap<>();
    private final List<Cell> cells;

    private FactorialDesign(String id, long masterSeed, int runsPerCell, String seat, String partner,
                            List<Integer> probeTs, List<Factor> factors, List<Contrast> contrasts, BandSpec band,
                            String sweepHash, Map<String, String> scenarioHashes, List<Cell> cells) {
        this.id = id;
        this.masterSeed = masterSeed;
        this.runsPerCell = runsPerCell;
        this.seat = seat;
        this.partner = partner;
        this.probeTs = probeTs;
        this.factors = factors;
        this.contrasts = contrasts;
        this.band = band;
        this.sweepHash = sweepHash;
        this.scenarioHashes.putAll(scenarioHashes);
        this.cells = cells;
    }

    public String id() { return id; }
    public long masterSeed() { return masterSeed; }
    public int runsPerCell() { return runsPerCell; }
    public String seat() { return seat; }
    public String partner() { return partner; }
    public List<Integer> probeTs() { return probeTs; }
    public List<Factor> factors() { return factors; }
    public List<Contrast> contrasts() { return contrasts; }
    public BandSpec band() { return band; }
    public String sweepHash() { return sweepHash; }
    public Map<String, String> scenarioHashes() { return scenarioHashes; }
    public List<Cell> cells() { return cells; }

    /** The game seed of run seedIndex in a block: independent of the treatment levels and of the thread schedule. */
    public long runSeed(String blockId, int seedIndex) {
        return new SeedPolicy(masterSeed).streamSeed("crn:" + blockId + ":" + seedIndex);
    }

    /** The probe defection round for a seed index (probeTs cycled by seed). */
    public int probeT(int seedIndex) {
        return probeTs.get(seedIndex % probeTs.size());
    }

    /** Returns a design with another runsPerCell (cell keys change, so summaries of other sizes are not reused). */
    public FactorialDesign withRunsPerCell(int n) {
        List<Cell> cs = new ArrayList<>();
        for (Cell c : cells) {
            cs.add(new Cell(c.index(), c.labels(), c.blockId(), cellKey(c.labels(), c.tree(), c.probe(), n), c.config(),
                    c.tree(), c.probe()));
        }
        return new FactorialDesign(id, masterSeed, n, seat, partner, probeTs, factors, contrasts, band, sweepHash,
                scenarioHashes, cs);
    }

    // ------------------------------------------------------------------ loading

    public static FactorialDesign load(Path file) {
        try {
            String text = Files.readString(file, StandardCharsets.UTF_8);
            return parse(text, file.toAbsolutePath().getParent());
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read sweep " + file + ": " + e.getMessage(), e);
        }
    }

    public static FactorialDesign loadResource(String name) {
        try (InputStream in = FactorialDesign.class.getClassLoader().getResourceAsStream(name)) {
            if (in == null) {
                throw new ScenarioLoadException("Resource not found: " + name);
            }
            return parse(new String(in.readAllBytes(), StandardCharsets.UTF_8), null);
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read resource " + name + ": " + e.getMessage(), e);
        }
    }

    public static FactorialDesign parse(String yaml, Path dir) {
        JsonNode root;
        try {
            root = YAML.readTree(yaml);
        } catch (IOException e) {
            throw new ScenarioLoadException("Invalid sweep YAML: " + e.getMessage(), e);
        }
        if (root == null || !root.isObject()) {
            throw new ScenarioLoadException("Sweep must be a mapping");
        }
        only(root, "sweep", TOP);
        String id = text(root, "id", null);
        String baseName = root.has("base") ? text(root, "base", null) : null;
        long master = root.has("masterSeed") ? integral(root.get("masterSeed"), "masterSeed") : 0L;
        int runs = (int) (root.has("runsPerCell") ? integral(root.get("runsPerCell"), "runsPerCell") : 1000L);
        if (runs < 1) {
            throw new ScenarioLoadException("runsPerCell must be >= 1");
        }
        String seat = text(root, "seat", "llm");
        String partner = text(root, "partner", "partner");
        List<Integer> probeTs = new ArrayList<>();
        if (root.has("probeTs")) {
            for (JsonNode n : root.get("probeTs")) {
                probeTs.add((int) integral(n, "probeTs[]"));
            }
        }
        if (probeTs.isEmpty()) {
            probeTs.add(8);
        }

        List<Factor> factors = new ArrayList<>();
        JsonNode fs = root.get("factors");
        if (fs == null || !fs.isArray() || fs.isEmpty()) {
            throw new ScenarioLoadException("factors (a non-empty list) is required");
        }
        java.util.Set<String> names = new java.util.HashSet<>();
        for (JsonNode f : fs) {
            only(f, "factor", Set.of("name", "treatment", "levels"));
            String name = text(f, "name", null);
            if (!names.add(name)) {
                throw new ScenarioLoadException("Duplicate factor " + name);
            }
            if (!f.has("treatment") || !f.get("treatment").isBoolean()) {
                throw new ScenarioLoadException("factor " + name + ": treatment (true | false) is required (T14)");
            }
            List<Level> levels = new ArrayList<>();
            java.util.Set<String> labels = new java.util.HashSet<>();
            if (!f.has("levels") || !f.get("levels").isArray() || f.get("levels").isEmpty()) {
                throw new ScenarioLoadException("factor " + name + ": levels (a non-empty list) is required");
            }
            for (JsonNode l : f.get("levels")) {
                only(l, "level of " + name, Set.of("label", "base", "vars", "set", "agents", "probe"));
                String label = text(l, "label", null);
                if (!labels.add(label)) {
                    throw new ScenarioLoadException("factor " + name + ": duplicate level " + label);
                }
                levels.add(new Level(label, l));
            }
            factors.add(new Factor(name, f.get("treatment").asBoolean(), levels));
        }

        List<Contrast> contrasts = new ArrayList<>();
        if (root.has("contrasts")) {
            for (JsonNode c : root.get("contrasts")) {
                only(c, "contrast", Set.of("name", "factor", "a", "b", "statistic"));
                Contrast ct = new Contrast(text(c, "name", null), text(c, "factor", null), text(c, "a", null),
                        text(c, "b", null), text(c, "statistic", "meanCi"));
                Factor f = factors.stream().filter(x -> x.name().equals(ct.factor())).findFirst().orElseThrow(
                        () -> new ScenarioLoadException("contrast " + ct.name() + ": unknown factor " + ct.factor()));
                if (!f.treatment()) {
                    throw new ScenarioLoadException("contrast " + ct.name() + ": factor must be a treatment factor");
                }
                for (String lv : List.of(ct.a(), ct.b())) {
                    if (f.levels().stream().noneMatch(x -> x.label().equals(lv))) {
                        throw new ScenarioLoadException("contrast " + ct.name() + ": unknown level " + lv);
                    }
                }
                if (!STATS.contains(ct.statistic())) {
                    throw new ScenarioLoadException("contrast " + ct.name() + ": statistic must be one of " + STATS);
                }
                contrasts.add(ct);
            }
        }
        BandSpec band = new BandSpec(10, 3, 1000, 20261022L);
        if (root.has("band")) {
            JsonNode b = root.get("band");
            only(b, "band", Set.of("clusters", "seedsPerCluster", "resamples", "seed"));
            band = new BandSpec(b.has("clusters") ? (int) integral(b.get("clusters"), "band.clusters") : 10,
                    b.has("seedsPerCluster") ? (int) integral(b.get("seedsPerCluster"), "band.seedsPerCluster") : 3,
                    b.has("resamples") ? (int) integral(b.get("resamples"), "band.resamples") : 1000,
                    b.has("seed") ? integral(b.get("seed"), "band.seed") : 20261022L);
        }

        Map<String, String> hashes = new TreeMap<>();
        Map<String, JsonNode> baseCache = new java.util.HashMap<>();
        List<Cell> cells = new ArrayList<>();
        int[] idx = new int[factors.size()];
        int total = 1;
        for (Factor f : factors) {
            total *= f.levels().size();
        }
        for (int c = 0; c < total; c++) {
            int rem = c;
            for (int i = factors.size() - 1; i >= 0; i--) {
                int sz = factors.get(i).levels().size();
                idx[i] = rem % sz;
                rem /= sz;
            }
            cells.add(buildCell(c, factors, idx, baseName, dir, hashes, baseCache, seat, runs, probeTs));
        }
        return new FactorialDesign(id, master, runs, seat, partner, probeTs, factors, contrasts, band,
                Canonical.sha256(yaml), hashes, cells);
    }

    private static Cell buildCell(int index, List<Factor> factors, int[] idx, String baseName, Path dir,
                                  Map<String, String> hashes, Map<String, JsonNode> baseCache, String seat, int runs,
                                  List<Integer> probeTs) {
        Map<String, String> labels = new LinkedHashMap<>();
        ObjectNode nonTreatment = JsonNodeFactory.instance.objectNode();
        ObjectNode tree = null;
        if (baseName != null) {
            tree = loadBase(baseName, dir, hashes, baseCache);
        }
        Map<String, JsonNode> vars = new TreeMap<>();
        Probe probe = Probe.NONE;
        for (int i = 0; i < factors.size(); i++) {
            Factor f = factors.get(i);
            Level lv = f.levels().get(idx[i]);
            labels.put(f.name(), lv.label());
            if (!f.treatment()) {
                nonTreatment.put(f.name(), lv.label());
            }
            JsonNode spec = lv.spec();
            if (spec.has("base")) {
                tree = loadBase(spec.get("base").asText(), dir, hashes, baseCache);
            }
            if (tree == null) {
                throw new ScenarioLoadException("No base game for cell " + labels + ": give a sweep 'base' or a level 'base'");
            }
            if (spec.has("vars")) {
                spec.get("vars").fields().forEachRemaining(e -> vars.put(e.getKey(), e.getValue()));
            }
            if (spec.has("probe")) {
                probe = Probe.valueOf(spec.get("probe").asText());
            }
            final ObjectNode cur = tree;
            if (spec.has("set")) {
                spec.get("set").fields().forEachRemaining(e -> setPath(cur, e.getKey(), e.getValue().deepCopy()));
            }
            if (spec.has("agents")) {
                for (JsonNode a : spec.get("agents")) {
                    overrideAgent(tree, a);
                }
            }
        }
        substitute(tree, vars);
        String blockId = Canonical.sha256(Canonical.text(nonTreatment)).substring(0, 16);
        GameConfig cfg;
        try {
            cfg = GameConfigLoader.parse(YAML.writeValueAsString(tree));
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot compose cell " + labels + ": " + e.getMessage(), e);
        } catch (ScenarioLoadException e) {
            throw new ScenarioLoadException("Cell " + labels + ": " + e.getMessage(), e);
        }
        if (cfg.agents().stream().anyMatch(a -> a.kind() == AgentKind.LLM)) {
            throw new ScenarioLoadException("Cell " + labels + ": the LLM seat placeholder is not filled by a scripted agent");
        }
        if (cfg.agents().stream().noneMatch(a -> a.id().equals(seat))) {
            throw new ScenarioLoadException("Cell " + labels + ": no agent with the seat id '" + seat + "'");
        }
        if (probe != Probe.NONE) {
            // the probe partner must be a DEFECT_ONCE agent (its t is set per run)
            if (cfg.agents().stream().noneMatch(a -> a.kind() == AgentKind.DEFECT_ONCE)) {
                throw new ScenarioLoadException("Cell " + labels + ": a probe cell needs a DEFECT_ONCE partner");
            }
        }
        return new Cell(index, labels, blockId, cellKey(labels, tree, probe, runs), cfg, tree, probe);
    }

    static String cellKey(Map<String, String> labels, JsonNode tree, Probe probe, int runs) {
        ObjectNode k = JsonNodeFactory.instance.objectNode();
        ObjectNode l = k.putObject("labels");
        labels.forEach(l::put);
        k.set("game", tree);
        k.put("probe", probe.name());
        k.put("runs", runs);
        return Canonical.sha256(Canonical.text(k)).substring(0, 16);
    }

    private static ObjectNode loadBase(String name, Path dir, Map<String, String> hashes, Map<String, JsonNode> cache) {
        JsonNode cached = cache.get(name);
        if (cached == null) {
            String content = readSource(name, dir);
            hashes.put(name, Canonical.sha256(content));
            try {
                cached = YAML.readTree(content);
            } catch (IOException e) {
                throw new ScenarioLoadException("Invalid base " + name + ": " + e.getMessage(), e);
            }
            if (!cached.isObject()) {
                throw new ScenarioLoadException("Base " + name + " must be a mapping");
            }
            cache.put(name, cached);
        }
        return (ObjectNode) cached.deepCopy();
    }

    private static String readSource(String name, Path dir) {
        try {
            Path p = Path.of(name);
            if (Files.isRegularFile(p)) {
                return Files.readString(p, StandardCharsets.UTF_8);
            }
            if (dir != null && Files.isRegularFile(dir.resolve(name))) {
                return Files.readString(dir.resolve(name), StandardCharsets.UTF_8);
            }
            try (InputStream in = FactorialDesign.class.getClassLoader().getResourceAsStream(name)) {
                if (in != null) {
                    return new String(in.readAllBytes(), StandardCharsets.UTF_8);
                }
            }
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read " + name + ": " + e.getMessage(), e);
        }
        throw new ScenarioLoadException("Base scenario not found (file or classpath resource): " + name);
    }

    private static void setPath(ObjectNode tree, String path, JsonNode value) {
        String[] parts = path.split("\\.");
        ObjectNode cur = tree;
        for (int i = 0; i < parts.length - 1; i++) {
            JsonNode nx = cur.get(parts[i]);
            if (nx == null || nx.isNull()) {
                nx = cur.putObject(parts[i]);
            } else if (!nx.isObject()) {
                throw new ScenarioLoadException("set " + path + ": '" + parts[i] + "' is not a mapping");
            }
            cur = (ObjectNode) nx;
        }
        cur.set(parts[parts.length - 1], value);
    }

    private static void overrideAgent(ObjectNode tree, JsonNode a) {
        only(a, "agents[]", Set.of("id", "kind", "category", "config"));
        String aid = text(a, "id", null);
        ArrayNode list = (ArrayNode) tree.get("agents");
        if (list == null) {
            list = tree.putArray("agents");
        }
        ObjectNode target = null;
        for (JsonNode x : list) {
            if (aid.equals(x.path("id").asText())) {
                target = (ObjectNode) x;
            }
        }
        if (target == null) {
            target = list.addObject();
            target.put("id", aid);
            if (!a.has("category")) {
                target.put("category", "M");
            }
        }
        if (a.has("category")) {
            target.set("category", a.get("category").deepCopy());
        }
        if (a.has("kind")) {
            target.set("kind", a.get("kind").deepCopy());
            target.remove("config");
        }
        if (a.has("config")) {
            ObjectNode cfg = target.has("config") ? (ObjectNode) target.get("config") : target.putObject("config");
            a.get("config").fields().forEachRemaining(e -> cfg.set(e.getKey(), e.getValue().deepCopy()));
        }
    }

    private static void substitute(JsonNode node, Map<String, JsonNode> vars) {
        if (node.isObject()) {
            ObjectNode o = (ObjectNode) node;
            List<String> names = new ArrayList<>();
            o.fieldNames().forEachRemaining(names::add);
            for (String f : names) {
                JsonNode v = o.get(f);
                JsonNode r = resolve(v, vars);
                if (r != v) {
                    o.set(f, r);
                } else {
                    substitute(v, vars);
                }
            }
        } else if (node.isArray()) {
            ArrayNode a = (ArrayNode) node;
            for (int i = 0; i < a.size(); i++) {
                JsonNode v = a.get(i);
                JsonNode r = resolve(v, vars);
                if (r != v) {
                    a.set(i, r);
                } else {
                    substitute(v, vars);
                }
            }
        }
    }

    private static JsonNode resolve(JsonNode v, Map<String, JsonNode> vars) {
        if (v.isTextual()) {
            Matcher m = VAR.matcher(v.asText());
            if (m.matches()) {
                JsonNode r = vars.get(m.group(1));
                if (r == null) {
                    throw new ScenarioLoadException("Undefined variable ${" + m.group(1) + "}");
                }
                return r.deepCopy();
            }
        }
        return v;
    }

    private static void only(JsonNode n, String section, Set<String> allowed) {
        if (!n.isObject()) {
            throw new ScenarioLoadException(section + " must be a mapping");
        }
        Iterator<String> it = n.fieldNames();
        while (it.hasNext()) {
            String f = it.next();
            if (!allowed.contains(f)) {
                throw new ScenarioLoadException("Unknown key '" + f + "' in " + section);
            }
        }
    }

    private static String text(JsonNode n, String key, String dflt) {
        if (!n.has(key) || n.get(key).isNull()) {
            if (dflt == null) {
                throw new ScenarioLoadException("'" + key + "' is required");
            }
            return dflt;
        }
        if (!n.get(key).isValueNode()) {
            throw new ScenarioLoadException("'" + key + "' must be a scalar");
        }
        return n.get(key).asText();
    }

    private static long integral(JsonNode n, String what) {
        if (!n.isIntegralNumber()) {
            throw new ScenarioLoadException(what + " must be an integer");
        }
        return n.asLong();
    }
}
