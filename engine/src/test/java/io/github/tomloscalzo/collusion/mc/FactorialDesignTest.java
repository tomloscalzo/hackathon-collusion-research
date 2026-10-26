package io.github.tomloscalzo.collusion.mc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.scenario.ScenarioLoadException;
import org.junit.jupiter.api.Test;

class FactorialDesignTest {
    @Test
    void enumeratesCellsDeterministicallyFirstFactorSlowest() {
        FactorialDesign d = FactorialDesign.parse(Sweeps.TINY, null);
        assertThat(d.cells()).hasSize(4);
        assertThat(d.cells().stream().map(FactorialDesign.Cell::name).toList()).containsExactly(
                "arm=ripe|seat=tft", "arm=ripe|seat=noise", "arm=unripe-a|seat=tft", "arm=unripe-a|seat=noise");
        FactorialDesign again = FactorialDesign.parse(Sweeps.TINY, null);
        assertThat(again.cells().stream().map(FactorialDesign.Cell::key).toList())
                .isEqualTo(d.cells().stream().map(FactorialDesign.Cell::key).toList());
        var c0 = d.cells().get(0).config();
        assertThat(c0.agents().get(0).kind()).isEqualTo(AgentKind.TIT_FOR_TAT);
        assertThat(c0.agents().get(0).config()).containsEntry("theta", 0.546);
        assertThat(d.cells().get(1).config().agents().get(0).kind()).isEqualTo(AgentKind.NOISE);
        assertThat(d.cells().get(2).config().scenario().enforcement().fine()).isEqualTo(5000.0);
    }

    @Test
    void crnBlockIdIsInvariantAcrossTreatmentLevelsOnly() {
        FactorialDesign d = FactorialDesign.parse(Sweeps.TINY, null);
        var cs = d.cells();
        assertThat(cs.get(0).blockId()).isEqualTo(cs.get(2).blockId());
        assertThat(cs.get(1).blockId()).isEqualTo(cs.get(3).blockId());
        assertThat(cs.get(0).blockId()).isNotEqualTo(cs.get(1).blockId());
        for (int i : new int[] {0, 5, 19}) {
            assertThat(d.runSeed(cs.get(0).blockId(), i)).isEqualTo(d.runSeed(cs.get(2).blockId(), i));
            assertThat(d.runSeed(cs.get(0).blockId(), i)).isNotEqualTo(d.runSeed(cs.get(1).blockId(), i));
        }
        assertThat(d.runSeed(cs.get(0).blockId(), 0)).isNotEqualTo(d.runSeed(cs.get(0).blockId(), 1));
        assertThat(cs.get(0).key()).isNotEqualTo(cs.get(2).key());
        String flipped = Sweeps.TINY.replace("name: arm\n    treatment: true", "name: arm\n    treatment: false")
                .replace("name: seat\n    treatment: false", "name: seat\n    treatment: true");
        flipped = flipped.replaceAll("(?s)contrasts:.*?band:", "band:");
        FactorialDesign f = FactorialDesign.parse(flipped, null);
        assertThat(f.cells().get(0).blockId()).isNotEqualTo(f.cells().get(2).blockId());
        assertThat(f.cells().get(0).blockId()).isEqualTo(f.cells().get(1).blockId());
    }

    @Test
    void strictness() {
        assertThatThrownBy(() -> FactorialDesign.parse(Sweeps.TINY.replace("masterSeed: 7", "mastrSeed: 7"), null))
                .isInstanceOf(ScenarioLoadException.class).hasMessageContaining("mastrSeed");
        assertThatThrownBy(() -> FactorialDesign.parse(Sweeps.TINY.replace("name: arm\n    treatment: true", "name: arm"), null))
                .isInstanceOf(ScenarioLoadException.class).hasMessageContaining("treatment");
        assertThatThrownBy(() -> FactorialDesign.parse(Sweeps.TINY.replace("kind: NOISE", "kind: LLM"), null))
                .hasMessageContaining("LLM");
        assertThatThrownBy(() -> FactorialDesign.parse(Sweeps.TINY.replace("${thetaP}", "${nope}"), null))
                .hasMessageContaining("nope");
        assertThatThrownBy(() -> FactorialDesign.parse(Sweeps.TINY.replace("a: ripe,", "a: nope,"), null))
                .hasMessageContaining("unknown level");
    }

    @Test
    void shippedSweepsLoadAndHaveExpectedShape() {
        FactorialDesign sm = FactorialDesign.loadResource("sweeps/strategy-mix.yaml");
        assertThat(sm.cells()).hasSize(70);
        assertThat(sm.runsPerCell()).isEqualTo(1000);
        FactorialDesign rb = FactorialDesign.loadResource("sweeps/reference-bands.yaml");
        assertThat(rb.cells()).hasSize(21);
        assertThat(rb.contrasts().stream().map(FactorialDesign.Contrast::name).toList())
                .contains("P1-A", "P1-A-prime", "P3", "P4", "P5");
        var probe = rb.cells().stream().filter(c -> c.labels().get("arm").equals("probe")).toList();
        assertThat(probe).allMatch(c -> c.probe() == FactorialDesign.Probe.DEFECT);
        assertThat(probe).allMatch(c -> c.config().detection().mode().name().equals("OFF"));
        assertThat(rb.cells().get(0).blockId()).isEqualTo(rb.cells().get(3).blockId());
    }
}
