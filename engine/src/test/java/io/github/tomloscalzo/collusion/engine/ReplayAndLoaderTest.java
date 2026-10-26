package io.github.tomloscalzo.collusion.engine;

import static io.github.tomloscalzo.collusion.core.model.AgentKind.TRIGGER_K;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.results.RunRecord;
import io.github.tomloscalzo.collusion.results.RunWriter;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoadException;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * replay (digest equality, JSONL round trip, roster-invariant streams) and the game-config loader. Overrides for the
 * replay tests: ripe baseline, known horizon 10 (delta0 0.95), detection SCENARIO, demandNoiseSd 5, o = 0.5,
 * quoteIncrement 0.01.
 */
class ReplayAndLoaderTest {
    private static GameConfig noisy(boolean third) {
        Scenario s = Fx.known(10);
        List<io.github.tomloscalzo.collusion.core.model.AgentSpec> a = new ArrayList<>(List.of(
                Fx.spec("A", TRIGGER_K, "theta", 0.6, "k", 3), Fx.spec("B", TRIGGER_K, "theta", 0.6, "k", 3)));
        if (third) {
            a.add(Fx.spec("C", TRIGGER_K, "theta", 0.6, "k", 3));
            s = s.withMarket(s.market().withN(3));
        }
        return new GameConfig(s, new ObservationPolicy(true, true, 5.0, 0.5), HistoryPolicy.defaults(),
                DetectionSpec.scenario(), a);
    }

    @Test
    void replayDigestEqualAndSeedSensitive() {
        Game g = new Game(noisy(false));
        RunRecord a = g.run(42);
        RunRecord b = new Game(noisy(false)).run(42);
        assertThat(a.replayDigest()).isEqualTo(b.replayDigest()).hasSize(64);
        assertThat(a).isEqualTo(b);
        assertThat(g.run(43).replayDigest()).isNotEqualTo(a.replayDigest());
    }

    @Test
    void jsonlRoundTripKeepsDigest() throws Exception {
        RunRecord a = new Game(noisy(false)).run(7);
        Path f = Files.createTempFile("runs", ".jsonl");
        try {
            RunWriter.append(f, a);
            RunWriter.append(f, new Game(noisy(false)).run(8));
            List<String> lines = Files.readAllLines(f, StandardCharsets.UTF_8);
            assertThat(lines).hasSize(2);
            JsonNode n = Canonical.MAPPER.readTree(lines.get(0));
            assertThat(n.get("replayDigest").asText()).isEqualTo(a.replayDigest());
            assertThat(Canonical.digestOf(n.get("rounds"))).isEqualTo(a.replayDigest());
            assertThat(n.get("scenarioId").asText()).isEqualTo("ripe-baseline");
            assertThat(lines.get(0)).isEqualTo(RunWriter.line(a));
        } finally {
            Files.deleteIfExists(f);
        }
    }

    // roster invariance: agent A's demand noise and quote-visibility draws do not change when C joins (n = 3).
    @Test
    void streamsAreRosterInvariant() {
        RunRecord two = new Game(noisy(false)).run(99);
        RunRecord three = new Game(noisy(true)).run(99);
        assertThat(two.rounds()).hasSize(10);
        assertThat(three.rounds()).hasSize(10);
        for (String id : List.of("A", "B")) {
            for (int t = 0; t < 10; t++) {
                assertThat(three.rounds().get(t).agent(id).noise()).isEqualTo(two.rounds().get(t).agent(id).noise());
                assertThat(three.rounds().get(t).agent(id).sawPriorQuotes())
                        .isEqualTo(two.rounds().get(t).agent(id).sawPriorQuotes());
            }
        }
        SeedPolicy p = new SeedPolicy(5);
        assertThat(p.streamSeed("demand:A")).isEqualTo(new SeedPolicy(5).streamSeed("demand:A"));
        assertThat(p.streamSeed("demand:A")).isNotEqualTo(p.streamSeed("demand:B"));
        assertThat(p.streamSeed("signal:A")).isNotEqualTo(p.streamSeed("demand:A"));
        assertThat(p.stream("horizon").nextDouble()).isEqualTo(new SeedPolicy(5).stream("horizon").nextDouble());
    }

    @Test
    void loadsEngineScenarioAndRuns() {
        GameConfig c = GameConfigLoader.loadResource("scenarios/engine-trigger-pair.yaml");
        assertThat(c.agents()).hasSize(2);
        assertThat(c.scenario().market().quoteIncrement()).isEqualTo(0.01);
        assertThat(c.detection().mode()).isEqualTo(DetectionSpec.Mode.SCENARIO);
        RunRecord r = new Game(c).run(3);
        assertThat(r.rounds()).isNotEmpty();
        assertThat(AgentFactory.create(c.agents().get(0), c.scenario(), c.observation()).disclosedRule())
                .contains("2.20").contains("rest of the game");
    }

    @Test
    void loaderStaysStrict() throws Exception {
        String y = Files.readString(Path.of("src/main/resources/scenarios/engine-trigger-pair.yaml"));
        assertThatThrownBy(() -> GameConfigLoader.parse(y.replace("o: 1", "o: 1.5"))).isInstanceOf(ScenarioLoadException.class);
        assertThatThrownBy(() -> GameConfigLoader.parse(y.replace("demandNoiseSd: 0", "demandNoiseSd: -1")))
                .isInstanceOf(ScenarioLoadException.class);
        assertThatThrownBy(() -> GameConfigLoader.parse(y.replace("showFillPrice: true", "showFillPrize: true")))
                .isInstanceOf(ScenarioLoadException.class);
        assertThatThrownBy(() -> GameConfigLoader.parse(y.replace("category: M", "category: Q"))).isInstanceOf(ScenarioLoadException.class);
        assertThatThrownBy(() -> GameConfigLoader.parse(y + "bogus: 1\n")).isInstanceOf(ScenarioLoadException.class);
        assertThatThrownBy(() -> GameConfigLoader.parse(Files.readString(Path.of("src/main/resources/scenarios/ripe-baseline.yaml"))))
                .isInstanceOf(ScenarioLoadException.class).hasMessageContaining("agents");
        // the core loader still rejects the engine sections and still loads the baseline
        assertThatThrownBy(() -> ScenarioLoader.parse(y)).isInstanceOf(ScenarioLoadException.class);
        assertThat(ScenarioLoader.loadResource("scenarios/ripe-baseline.yaml").id()).isEqualTo("ripe-baseline");
        // o = 0 and demandNoiseSd = 0 are legal (T2)
        assertThat(GameConfigLoader.parse(y.replace("o: 1", "o: 0")).observation().o()).isZero();
    }
}
