package io.github.tomloscalzo.collusion.scenario;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.core.model.TimeParams;
import org.junit.jupiter.api.Test;

class ScenarioLoaderTest {
    private static Scenario base() {
        return ScenarioLoader.loadResource("scenarios/ripe-baseline.yaml");
    }

    private static String baseYaml() throws Exception {
        try (var in = ScenarioLoaderTest.class.getClassLoader().getResourceAsStream("scenarios/ripe-baseline.yaml")) {
            // line-ending agnostic: the tests below edit the text with LF-terminated strings, and a Windows checkout
            // with core.autocrlf=true has CRLF unless .gitattributes pins LF
            return new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8).replace("\r\n", "\n");
        }
    }

    @Test
    void roundTrips() {
        Scenario s = base();
        assertThat(ScenarioLoader.parse(ScenarioLoader.toYaml(s))).isEqualTo(s);
        assertThat(s.delta()).isCloseTo(0.95, within(1e-12));
        assertThat(s.punishmentLength()).isEqualTo(-1);
        Scenario known = s.withTime(new TimeParams(1.0, 0.0, new Horizon.Known(10), 10));
        assertThat(ScenarioLoader.parse(ScenarioLoader.toYaml(known))).isEqualTo(known);
    }

    @Test
    void rejectsUnknownKeys() throws Exception {
        assertThatThrownBy(() -> ScenarioLoader.parse(baseYaml() + "bogus: 1\n")).isInstanceOf(ScenarioLoadException.class);
        assertThatThrownBy(() -> ScenarioLoader.parse(baseYaml().replace("  tick: 0.0\n", "  tick: 0.0\n  tik: 1\n")))
                .isInstanceOf(ScenarioLoadException.class);
    }

    @Test
    void rejectsHighPhi() throws Exception {
        assertThatThrownBy(() -> ScenarioLoader.parse(baseYaml().replace("phi: 0.3", "phi: 0.95")))
                .isInstanceOf(ScenarioLoadException.class).hasMessageContaining("phi");
    }

    @Test
    void rejectsIrpWithInfinitePunishment() throws Exception {
        assertThatThrownBy(() -> ScenarioLoader.parse(baseYaml().replace("sumIRP: 0", "sumIRP: 1")))
                .isInstanceOf(ScenarioLoadException.class).hasMessageContaining("sumIRP");
        Scenario ok = ScenarioLoader.parse(baseYaml().replace("sumIRP: 0", "sumIRP: 1").replace("punishmentLength: -1", "punishmentLength: 3"));
        assertThat(ok.aggregates().sumIRP()).isEqualTo(1.0);
    }

    @Test
    void rejectsMissingKeys() throws Exception {
        assertThatThrownBy(() -> ScenarioLoader.parse(baseYaml().replace("tau: 0.1\n", "")))
                .isInstanceOf(ScenarioLoadException.class);
    }
}
