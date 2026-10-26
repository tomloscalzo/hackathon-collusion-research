package io.github.tomloscalzo.collusion.scenario;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.StreamReadFeature;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonDeserializer;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.module.SimpleModule;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import com.fasterxml.jackson.dataformat.yaml.YAMLGenerator;
import com.fasterxml.jackson.dataformat.yaml.YAMLMapper;
import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Iterator;

/** Strict YAML scenario loader: unknown or missing keys fail, and the core-range checks are enforced. */
public final class ScenarioLoader {
    public static final double MAX_PHI = 0.8;

    private static final ObjectMapper MAPPER = buildMapper();

    private ScenarioLoader() {}

    private static ObjectMapper buildMapper() {
        YAMLFactory factory = YAMLFactory.builder()
                .disable(YAMLGenerator.Feature.WRITE_DOC_START_MARKER)
                .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
                .build();
        SimpleModule module = new SimpleModule("collusion-horizon");
        module.addSerializer(Horizon.class, new HorizonSerializer());
        module.addDeserializer(Horizon.class, new HorizonDeserializer());
        return YAMLMapper.builder(factory)
                .addModule(module)
                .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
                .enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES)
                .enable(DeserializationFeature.FAIL_ON_MISSING_CREATOR_PROPERTIES)
                .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
                .build();
    }

    public static Scenario parse(String yaml) {
        Scenario s;
        try {
            s = MAPPER.readValue(yaml, Scenario.class);
        } catch (IOException | RuntimeException e) {
            throw new ScenarioLoadException("Invalid scenario YAML: " + e.getMessage(), e);
        }
        if (s == null) {
            throw new ScenarioLoadException("Empty scenario document");
        }
        validate(s);
        return s;
    }

    public static Scenario load(Path file) {
        try {
            return parse(Files.readString(file, StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read " + file + ": " + e.getMessage(), e);
        }
    }

    /** Loads a classpath resource such as "scenarios/ripe-baseline.yaml". */
    public static Scenario loadResource(String name) {
        try (InputStream in = ScenarioLoader.class.getClassLoader().getResourceAsStream(name)) {
            if (in == null) {
                throw new ScenarioLoadException("Resource not found: " + name);
            }
            return parse(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot read resource " + name + ": " + e.getMessage(), e);
        }
    }

    public static String toYaml(Scenario s) {
        try {
            return MAPPER.writeValueAsString(s);
        } catch (IOException e) {
            throw new ScenarioLoadException("Cannot serialise scenario: " + e.getMessage(), e);
        }
    }

    /** Core-range checks (spec 8.1: phi in the core range; 3.3: IRP only with finite k). */
    public static void validate(Scenario s) {
        if (s.id() == null || s.id().isBlank()) {
            throw new ScenarioLoadException("id is required");
        }
        var m = s.market();
        if (m == null || s.enforcement() == null || s.time() == null || s.aggregates() == null
                || s.enforcement().screen() == null || s.time().horizon() == null
                || s.punishment() == null || s.punishmentLevel() == null) {
            throw new ScenarioLoadException("Missing required section or enum");
        }
        if (m.n() < 2) {
            throw new ScenarioLoadException("market.n must be >= 2");
        }
        if (!(m.phi() >= 0.0) || m.phi() > MAX_PHI) {
            throw new ScenarioLoadException("market.phi must be in [0, " + MAX_PHI + "], got " + m.phi());
        }
        if (!(m.sBar() > m.s0()) || !(m.q0() > 0) || m.tick() < 0 || !(m.quoteIncrement() > 0)) {
            throw new ScenarioLoadException("market requires sBar > s0, q0 > 0, tick >= 0, quoteIncrement > 0");
        }
        if (s.aggregates().sumIRP() > 0 && s.punishmentLength() < 0) {
            throw new ScenarioLoadException("aggregates.sumIRP > 0 requires a finite punishmentLength");
        }
        if (s.punishmentLength() == 0 || s.punishmentLength() < -1) {
            throw new ScenarioLoadException("punishmentLength must be -1 (infinite) or >= 1");
        }
        double d0 = s.time().delta0();
        if (!(d0 > 0 && d0 <= 1)) {
            throw new ScenarioLoadException("time.delta0 must be in (0, 1]");
        }
        if (s.time().horizon() instanceof Horizon.Random r && !(r.h() >= 0 && r.h() < 1)) {
            throw new ScenarioLoadException("horizon.h must be in [0, 1)");
        }
        if (s.time().horizon() instanceof Horizon.Known k && k.periods() < 1) {
            throw new ScenarioLoadException("horizon.periods must be >= 1");
        }
        if (!(s.tau() >= 0)) {
            throw new ScenarioLoadException("tau must be >= 0");
        }
    }

    private static final class HorizonSerializer extends JsonSerializer<Horizon> {
        @Override
        public void serialize(Horizon value, JsonGenerator g, SerializerProvider p) throws IOException {
            g.writeStartObject();
            if (value instanceof Horizon.Random r) {
                g.writeStringField("type", "random");
                g.writeNumberField("h", r.h());
            } else if (value instanceof Horizon.Known k) {
                g.writeStringField("type", "known");
                g.writeNumberField("periods", k.periods());
            }
            g.writeEndObject();
        }
    }

    private static final class HorizonDeserializer extends JsonDeserializer<Horizon> {
        @Override
        public Horizon deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
            JsonNode n = ctxt.readTree(p);
            if (!n.isObject() || !n.hasNonNull("type")) {
                throw JsonMappingException.from(p, "horizon requires a 'type' (random | known)");
            }
            String type = n.get("type").asText();
            Iterator<String> names = n.fieldNames();
            while (names.hasNext()) {
                String f = names.next();
                boolean ok = f.equals("type") || (type.equals("random") && f.equals("h"))
                        || (type.equals("known") && f.equals("periods"));
                if (!ok) {
                    throw JsonMappingException.from(p, "Unknown horizon property '" + f + "' for type " + type);
                }
            }
            switch (type) {
                case "random":
                    if (!n.hasNonNull("h") || !n.get("h").isNumber()) {
                        throw JsonMappingException.from(p, "horizon type random requires numeric h");
                    }
                    return new Horizon.Random(n.get("h").asDouble());
                case "known":
                    if (!n.hasNonNull("periods") || !n.get("periods").isIntegralNumber()) {
                        throw JsonMappingException.from(p, "horizon type known requires integer periods");
                    }
                    return new Horizon.Known(n.get("periods").asInt());
                default:
                    throw JsonMappingException.from(p, "Unknown horizon type '" + type + "'");
            }
        }
    }
}
