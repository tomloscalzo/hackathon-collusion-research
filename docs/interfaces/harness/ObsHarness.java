import io.github.tomloscalzo.collusion.agents.Agent;
import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.Decision;
import io.github.tomloscalzo.collusion.engine.Game;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.results.RunRecord;
import io.github.tomloscalzo.collusion.results.RunWriter;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Local data generator for the interface checks (committed under docs/interfaces/harness; not part of the engine
 * build): plays real engine games in which every seat is wrapped by a recorder, and
 * writes each Observation the engine built and each Decision the agent returned, serialised by the engine's own
 * Jackson mapper (Canonical.MAPPER + Canonical.text), plus the RunRecord line. Seats are declared kind LLM so that the
 * Game passes them to the SeatFactory; the factory builds the scripted agent named in config "as" (the AgentKind
 * ordinal is not used; the mapping is by the explicit table below).
 */
public class ObsHarness {
    record Wrap(Agent inner, String cfgName, Writer obs, Writer dec) implements Agent {
        public String id() { return inner.id(); }
        public java.util.Optional<SignalReference> signalReference() { return inner.signalReference(); }
        public String disclosedRule() { return inner.disclosedRule(); }
        public Decision decide(Observation o) {
            Decision d = inner.decide(o);
            try {
                var on = Canonical.MAPPER.valueToTree(o);
                ((com.fasterxml.jackson.databind.node.ObjectNode) on).put("_cfg", cfgName);
                obs.write(Canonical.text(on) + "\n");
                var dn = Canonical.MAPPER.valueToTree(d);
                ((com.fasterxml.jackson.databind.node.ObjectNode) dn).put("_cfg", cfgName);
                dec.write(Canonical.text(dn) + "\n");
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
            return d;
        }
    }

    public static void main(String[] a) throws Exception {
        Path out = Path.of(a[0]);
        Files.createDirectories(out);
        // (name, scenario resource, observation override (o, sd, showFill), roster as (id, kind, config))
        record Case(String name, String res, double o, double sd, boolean fill, int window, List<Object[]> roster) {}
        List<Case> cases = List.of(
                new Case("clean-grim-vs-hidden", "scenarios/ripe-game.yaml", 1.0, 0.0, true, 10, List.of(
                        new Object[] {"llm", AgentKind.TRIGGER_K, Map.of("theta", 0.546, "k", -1L, "hiddenFillFromRound", 4L)},
                        new Object[] {"partner", AgentKind.TRIGGER_K, Map.of("theta", 0.546, "k", 3L)})),
                new Case("noisy-tft-vs-grim", "scenarios/ripe-game.yaml", 0.5, 5.0, false, 3, List.of(
                        new Object[] {"llm", AgentKind.TIT_FOR_TAT, Map.of("theta", 0.546, "injectAtRound", 6L)},
                        new Object[] {"partner", AgentKind.TRIGGER_K, Map.of("theta", 0.546, "k", -1L)})),
                new Case("penance-vs-defect", "scenarios/ripe-game.yaml", 1.0, 0.0, true, 0, List.of(
                        new Object[] {"llm", AgentKind.PENANCE, Map.of("theta", 0.546, "k", 3L)},
                        new Object[] {"partner", AgentKind.DEFECT_ONCE, Map.of("theta", 0.546, "t", 3L)})),
                new Case("n4-logit-noise", "scenarios/n4-variant.yaml", 0.0, 2.0, true, 10, List.of(
                        new Object[] {"llm", AgentKind.LOGIT, Map.of("partnerTheta", 0.546, "sigma", 1.0)},
                        new Object[] {"partner", AgentKind.NOISE, Map.of()},
                        new Object[] {"partner2", AgentKind.TRIGGER_K, Map.of("theta", 0.546, "k", -1L)},
                        new Object[] {"partner3", AgentKind.ALWAYS_COMPETE, Map.of()})));
        try (Writer obs = Files.newBufferedWriter(out.resolve("observations.jsonl"), StandardCharsets.UTF_8);
             Writer dec = Files.newBufferedWriter(out.resolve("decisions.jsonl"), StandardCharsets.UTF_8)) {
            Files.deleteIfExists(out.resolve("runs.jsonl"));
            for (Case c : cases) {
                GameConfig base = GameConfigLoader.loadResource(c.res());
                List<AgentSpec> placeholder = new ArrayList<>();
                Map<String, AgentSpec> real = new java.util.HashMap<>();
                for (Object[] r : c.roster()) {
                    @SuppressWarnings("unchecked") Map<String, Object> cf = (Map<String, Object>) r[2];
                    placeholder.add(new AgentSpec((String) r[0], AgentCategory.M, AgentKind.LLM));
                    real.put((String) r[0], new AgentSpec((String) r[0], AgentCategory.M, (AgentKind) r[1], cf));
                }
                GameConfig cfg = new GameConfig(base.scenario(), base.observation().withO(c.o()).withDemandNoiseSd(c.sd())
                        .withShowFillPrice(c.fill()), new io.github.tomloscalzo.collusion.engine.HistoryPolicy(c.window()),
                        base.detection(), placeholder);
                Game g = new Game(cfg, (spec, gc, seeds, s) -> new Wrap(
                        AgentFactory.create(real.get(spec.id()), gc.scenario(), gc.observation(), seeds), c.name(), obs, dec));
                for (long seed = 1; seed <= 3; seed++) {
                    RunRecord r = g.run(seed);
                    RunWriter.append(out.resolve("runs.jsonl"), r);
                }
            }
        }
        System.out.println("done");
    }
}
