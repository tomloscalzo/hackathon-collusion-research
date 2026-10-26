package io.github.tomloscalzo.collusion.scenario;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.agents.llm.Condition;
import io.github.tomloscalzo.collusion.agents.llm.GameContext;
import io.github.tomloscalzo.collusion.agents.llm.ParaphraseFile;
import io.github.tomloscalzo.collusion.agents.llm.PromptBuilder;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.mc.FactorialDesign;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Cross-machine reproducibility: the same commit checked out with LF (Linux, Modal client boxes) or CRLF (Windows with
 * core.autocrlf=true) must give the same parsed configurations, the same CRN cells, the same rendered prompts (so the
 * same request hashes and cache keys) and the same template hashes in the manifest. The root .gitattributes pins LF for
 * hashed inputs; these tests check that the scenario and sweep text that reaches a request or a seed does not depend on
 * it, and that the prompt files are byte-stable LF.
 * (The manifest's raw-text hashes of scenario, sweep and analysis files do depend on the bytes; that is what the
 * .gitattributes policy and testing/check_line_endings.py cover.)
 */
class LineEndingInvarianceTest {
    static String resource(String name) throws Exception {
        try (InputStream in = LineEndingInvarianceTest.class.getClassLoader().getResourceAsStream(name)) {
            assertThat(in).as(name).isNotNull();
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    static String lf(String s) {
        return s.replace("\r\n", "\n");
    }

    static String crlf(String s) {
        return lf(s).replace("\n", "\r\n");
    }

    static List<String> yamlResources(String dir) throws Exception {
        URL url = LineEndingInvarianceTest.class.getClassLoader().getResource(dir);
        assertThat(url).as(dir).isNotNull();
        List<String> out = new ArrayList<>();
        try (Stream<Path> s = Files.list(Path.of(url.toURI()))) {
            s.map(p -> p.getFileName().toString()).filter(n -> n.endsWith(".yaml")).sorted().forEach(n -> out.add(dir + "/" + n));
        }
        return out;
    }

    @Test
    void scenarioAndGameFilesParseIdenticallyWithLfAndCrlf() throws Exception {
        List<String> names = yamlResources("scenarios");
        assertThat(names).hasSizeGreaterThanOrEqualTo(5);
        int games = 0;
        for (String name : names) {
            String text = resource(name);
            if (text.contains("\nagents:")) {
                GameConfig a = GameConfigLoader.parse(lf(text));
                GameConfig b = GameConfigLoader.parse(crlf(text));
                assertThat(b).as(name).isEqualTo(a);
                games++;
            } else {
                assertThat(ScenarioLoader.parse(crlf(text))).as(name).isEqualTo(ScenarioLoader.parse(lf(text)));
            }
        }
        assertThat(games).isPositive();
    }

    @Test
    void sweepCellsAndCrnBlocksAreLineEndingInvariant() throws Exception {
        int sweeps = 0;
        for (String name : yamlResources("sweeps")) {
            String text = lf(resource(name));
            if (text.startsWith("parameters:") || text.contains("\nparameters:")) {
                continue; // a ripeness grid for `solve` (no seeds), not a factorial sweep
            }
            List<FactorialDesign.Cell> a = FactorialDesign.parse(text, null).cells();
            List<FactorialDesign.Cell> b = FactorialDesign.parse(crlf(text), null).cells();
            assertThat(b).as(name).isEqualTo(a);
            sweeps++;
        }
        assertThat(sweeps).isGreaterThanOrEqualTo(2);
    }

    /**
     * The prompt files are byte-stable: stored with LF and marked -text (engine/.gitattributes), so every checkout reads
     * the same bytes and the manifest's templateHashes are the SHA-256 of exactly those bytes. This fails if a prompt file
     * picks up CRLF (an editor, or a change to the attributes). It does not exercise ParaphraseFile's own CRLF
     * normalisation, which reads the classpath itself; covering that would need a text-taking overload (a change to the
     * LLM adapter, so not made here).
     */
    @Test
    void promptFilesAreLfOnDiskAndTheirTemplateHashesAreThoseBytes() throws Exception {
        Map<String, String> hashes = ParaphraseFile.allHashes();
        for (String t : ParaphraseFile.TEMPLATES) {
            String raw = resource("prompts/" + t + ".json");
            assertThat(raw).as(t).doesNotContain("\r");
            assertThat(hashes.get(t)).as(t).isEqualTo(Canonical.sha256(raw));
        }
    }

    /** A CRLF scenario file leaks nothing into the rendered prompts (the templates themselves are covered above). */
    @Test
    void renderedPromptsCarryNoCarriageReturnFromAnyCheckout() throws Exception {
        String text = resource("scenarios/ripe-game.yaml");
        GameConfig cfg = GameConfigLoader.parse(crlf(text));
        GameContext ctx = GameContext.of(cfg, GameContext.firstLlmSeat(cfg));
        GameConfig cfgLf = GameConfigLoader.parse(lf(text));
        GameContext ctxLf = GameContext.of(cfgLf, GameContext.firstLlmSeat(cfgLf));
        Observation obs = new Observation(2, "llm", List.of("llm", "partner"), List.of(
                new Observation.PastRound(1, 2.09, null, true, Map.of("partner", 2.09), 2.09, 30.82, 2.09, false)), 0.5);
        for (String c : List.of("", "elicitation=E2", "elicitation=COMPETITIVE", "label=legal,guardrail=on,notice=on")) {
            for (int p = 0; p < 12; p++) {
                PromptBuilder pb = new PromptBuilder(Condition.parse(c), p);
                String sys = pb.gameSystem(ctx);
                String turn = pb.gameTurn(ctx, obs, "hold");
                assertThat(sys).doesNotContain("\r").isEqualTo(pb.gameSystem(ctxLf));
                assertThat(turn).doesNotContain("\r").isEqualTo(pb.gameTurn(ctxLf, obs, "hold"));
            }
        }
    }
}
