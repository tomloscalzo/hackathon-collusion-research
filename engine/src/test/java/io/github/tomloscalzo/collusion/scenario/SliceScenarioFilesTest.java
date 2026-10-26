package io.github.tomloscalzo.collusion.scenario;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.core.layera.CartelSolver;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

/** C2.1: the five expected-penalty slice files state theta* in a comment; each is checked against the solver. */
class SliceScenarioFilesTest {
    private static final List<String> NAMES = List.of("slice-p1", "slice-p2", "slice-p3", "slice-p4", "slice-p5");
    private static final List<String> M_NAMES = List.of("slice-m-p1", "slice-m-p2", "slice-m-p3", "slice-m-p4", "slice-m-p5");
    private static final double[] FINES = {100, 300, 500, 1000, 2000};
    private static final Pattern THEORY = Pattern.compile("(?m)^# theory-theta-star: ([0-9.]+)$");

    private static String text(String name) throws IOException {
        try (InputStream in = SliceScenarioFilesTest.class.getClassLoader().getResourceAsStream("scenarios/" + name + ".yaml")) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static double stated(String name) throws IOException {
        Matcher m = THEORY.matcher(text(name));
        assertThat(m.find()).as(name + " states its theory value").isTrue();
        return Double.parseDouble(m.group(1));
    }

    @Test
    void statedTheoryValueMatchesTheSolver() throws IOException {
        for (String n : NAMES) {
            GameConfig c = GameConfigLoader.loadResource("scenarios/" + n + ".yaml");
            double solved = new CartelSolver().solve(c.scenario()).thetaStar();
            assertThat(stated(n)).as(n).isCloseTo(solved, within(0.0005));
        }
    }

    @Test
    void finesRunFromCollusionPaysToCollusionDoesNotPay() throws IOException {
        double prev = Double.MAX_VALUE;
        for (int i = 0; i < NAMES.size(); i++) {
            GameConfig c = GameConfigLoader.loadResource("scenarios/" + NAMES.get(i) + ".yaml");
            assertThat(c.scenario().enforcement().fine()).isEqualTo(FINES[i]);
            assertThat(c.scenario().enforcement().rhoCoop()).isEqualTo(1.0);
            assertThat(stated(NAMES.get(i))).isLessThan(prev);
            prev = stated(NAMES.get(i));
        }
        assertThat(stated("slice-p1")).isGreaterThan(0.6);
        assertThat(stated("slice-p5")).isEqualTo(0.0);
    }

    @Test
    void sameMarketAsRipeGameAndPartnerPlaysTheTheoryLevel() throws IOException {
        var ripe = GameConfigLoader.loadResource("scenarios/ripe-game.yaml").scenario();
        for (String n : NAMES) {
            GameConfig c = GameConfigLoader.loadResource("scenarios/" + n + ".yaml");
            assertThat(c.scenario().market()).isEqualTo(ripe.market());
            assertThat(c.scenario().enforcement().screen()).isEqualTo(ripe.enforcement().screen());
            assertThat(c.scenario().time()).isEqualTo(ripe.time());
            assertThat(c.agents()).hasSize(2);
            assertThat(c.agents().get(0).kind()).isEqualTo(AgentKind.LLM);
            var p = c.agents().get(1);
            if (stated(n) > 0) {
                assertThat(p.kind()).isEqualTo(AgentKind.TRIGGER_K);
                assertThat((double) p.config().get("theta")).isEqualTo(stated(n));
            } else {
                assertThat(p.kind()).isEqualTo(AgentKind.ALWAYS_COMPETE);
            }
        }
    }

    /** The Track M twins: two LLM seats, everything else (market, screen, fine, horizon, theory line) as slice-pN. */
    @Test
    void trackMTwinsDifferOnlyInTheirSeats() throws IOException {
        for (int i = 0; i < NAMES.size(); i++) {
            String s = NAMES.get(i);
            String m = M_NAMES.get(i);
            GameConfig cs = GameConfigLoader.loadResource("scenarios/" + s + ".yaml");
            GameConfig cm = GameConfigLoader.loadResource("scenarios/" + m + ".yaml");
            assertThat(cm.scenario().id()).isEqualTo(m);
            assertThat(cm.scenario()).as(m).usingRecursiveComparison().ignoringFields("id").isEqualTo(cs.scenario());
            assertThat(cm.agents()).hasSize(2);
            assertThat(cm.agents().get(0).id()).isEqualTo("llm1");
            assertThat(cm.agents().get(1).id()).isEqualTo("llm2");
            assertThat(cm.agents().get(0).kind()).isEqualTo(AgentKind.LLM);
            assertThat(cm.agents().get(1).kind()).isEqualTo(AgentKind.LLM);
            assertThat(body(m)).as(m + " text above agents: apart from comments and id").isEqualTo(body(s));
            assertThat(stated(m)).as(m).isEqualTo(stated(s));
            double solved = new CartelSolver().solve(cm.scenario()).thetaStar();
            assertThat(stated(m)).as(m).isCloseTo(solved, within(0.0005));
        }
    }

    /** The text above the agents block without comment lines and the id line (those name the file). */
    private static String body(String name) throws IOException {
        String t = text(name).replace("\r\n", "\n");
        return java.util.Arrays.stream(t.substring(0, t.indexOf("\nagents:")).split("\n"))
                .filter(l -> !l.startsWith("#") && !l.startsWith("id:")).collect(java.util.stream.Collectors.joining("\n"));
    }
}
