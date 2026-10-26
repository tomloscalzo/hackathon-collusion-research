package io.github.tomloscalzo.collusion.scenario;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.engine.DetectionSpec;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.HistoryPolicy;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * Loads an engine game: the optional sections observation, history, detection and the required agents list are split
 * off and the remainder goes through the strict ScenarioLoader unchanged (so ScenarioLoader still rejects them).
 * Unknown keys in the new sections fail too.
 */
public final class GameConfigLoader {
    private static final YAMLMapper YAML = new YAMLMapper();
    private static final Set<String> EXTRA = Set.of("observation", "history", "detection", "agents");

    private GameConfigLoader() {}

    public static GameConfig parse(String yaml) {
        try {
            JsonNode root = YAML.readTree(yaml);
            if (!(root instanceof ObjectNode obj)) {
                throw new ScenarioLoadException("Game document must be a mapping");
            }
            ObjectNode rest = obj.deepCopy();
            for (String k : EXTRA) {
                rest.remove(k);
            }
            Scenario sc = ScenarioLoader.parse(YAML.writeValueAsString(rest));
            ObservationPolicy op = observation(obj.get("observation"));
            HistoryPolicy hp = history(obj.get("history"));
            DetectionSpec ds = detection(obj.get("detection"));
            List<AgentSpec> agents = agents(obj.get("agents"));
            try {
                return new GameConfig(sc, op, hp, ds, agents);
            } catch (IllegalArgumentException e) {
                throw new ScenarioLoadException("Invalid game: " + e.getMessage(), e);
            }
        } catch (IOException e) {
            throw new ScenarioLoadException("Invalid game YAML: " + e.getMessage(), e);
        }
    }

    public static GameConfig load(Path file) {
        try {
            return parse(Files.readString(file, StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read " + file + ": " + e.getMessage(), e);
        }
    }

    public static GameConfig loadResource(String name) {
        try (InputStream in = GameConfigLoader.class.getClassLoader().getResourceAsStream(name)) {
            if (in == null) {
                throw new ScenarioLoadException("Resource not found: " + name);
            }
            return parse(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read resource " + name + ": " + e.getMessage(), e);
        }
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

    private static double num(JsonNode n, String key, double dflt, String section) {
        if (!n.has(key)) {
            return dflt;
        }
        if (!n.get(key).isNumber()) {
            throw new ScenarioLoadException(section + "." + key + " must be numeric");
        }
        return n.get(key).asDouble();
    }

    private static boolean bool(JsonNode n, String key, boolean dflt, String section) {
        if (!n.has(key)) {
            return dflt;
        }
        if (!n.get(key).isBoolean()) {
            throw new ScenarioLoadException(section + "." + key + " must be boolean");
        }
        return n.get(key).asBoolean();
    }

    private static ObservationPolicy observation(JsonNode n) {
        if (n == null) {
            return ObservationPolicy.defaults();
        }
        only(n, "observation", Set.of("showOwnVolume", "showFillPrice", "demandNoiseSd", "o"));
        ObservationPolicy op = new ObservationPolicy(bool(n, "showOwnVolume", true, "observation"),
                bool(n, "showFillPrice", true, "observation"), num(n, "demandNoiseSd", 0.0, "observation"),
                num(n, "o", 1.0, "observation"));
        if (op.demandNoiseSd() < 0 || op.o() < 0 || op.o() > 1) {
            throw new ScenarioLoadException("observation requires demandNoiseSd >= 0 and o in [0, 1]");
        }
        return op;
    }

    private static HistoryPolicy history(JsonNode n) {
        if (n == null) {
            return HistoryPolicy.defaults();
        }
        only(n, "history", Set.of("window"));
        return new HistoryPolicy((int) num(n, "window", 10, "history"));
    }

    private static DetectionSpec detection(JsonNode n) {
        if (n == null) {
            return DetectionSpec.scenario();
        }
        only(n, "detection", Set.of("mode", "pTrigger", "pEvidence"));
        if (!n.has("mode") || !n.get("mode").isTextual()) {
            throw new ScenarioLoadException("detection.mode is required (OFF | SCENARIO | FIXED)");
        }
        DetectionSpec.Mode mode;
        try {
            mode = DetectionSpec.Mode.valueOf(n.get("mode").asText());
        } catch (IllegalArgumentException e) {
            throw new ScenarioLoadException("Unknown detection.mode '" + n.get("mode").asText() + "'");
        }
        double pt = num(n, "pTrigger", 0.0, "detection");
        double pe = num(n, "pEvidence", 0.0, "detection");
        if (pt < 0 || pt > 1 || pe < 0 || pe > 1) {
            throw new ScenarioLoadException("detection probabilities must be in [0, 1]");
        }
        return new DetectionSpec(mode, pt, pe);
    }

    private static List<AgentSpec> agents(JsonNode n) {
        if (n == null || !n.isArray() || n.isEmpty()) {
            throw new ScenarioLoadException("agents (a non-empty list) is required");
        }
        List<AgentSpec> out = new ArrayList<>();
        for (JsonNode a : n) {
            only(a, "agents[]", Set.of("id", "category", "kind", "config"));
            for (String req : List.of("id", "category", "kind")) {
                if (!a.hasNonNull(req)) {
                    throw new ScenarioLoadException("agents[] requires '" + req + "'");
                }
            }
            Map<String, Object> cfg = new TreeMap<>();
            JsonNode c = a.get("config");
            if (c != null) {
                if (!c.isObject()) {
                    throw new ScenarioLoadException("agents[].config must be a mapping");
                }
                c.fields().forEachRemaining(e -> {
                    JsonNode v = e.getValue();
                    if (v.isIntegralNumber()) {
                        cfg.put(e.getKey(), v.asLong());
                    } else if (v.isNumber()) {
                        cfg.put(e.getKey(), v.asDouble());
                    } else {
                        throw new ScenarioLoadException("agents[].config." + e.getKey() + " must be numeric");
                    }
                });
            }
            try {
                out.add(new AgentSpec(a.get("id").asText(), AgentCategory.valueOf(a.get("category").asText()),
                        AgentKind.valueOf(a.get("kind").asText()), cfg));
            } catch (IllegalArgumentException e) {
                throw new ScenarioLoadException("Bad agent entry: " + e.getMessage(), e);
            }
        }
        return out;
    }
}
