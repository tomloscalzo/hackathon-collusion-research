package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CachingLlmClient;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.OpenAiCompatibleClient;
import io.github.tomloscalzo.collusion.llm.ReplayLlmClient;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class VignetteTest {
    static final LlmSettings SETTINGS = new LlmSettings("openai-compatible", "mock-model-1", 0.7, 300);

    static GameConfig cfg() {
        return GameConfigLoader.loadResource("scenarios/ripe-game.yaml");
    }

    static LlmClient http(MockLlmServer s) {
        return new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(10), null, 1);
    }

    @Test
    void scriptedSwitchPointIsRecoveredWithinOneLevel() {
        for (int para : new int[] {0, 1, 5, 11}) { // both option orders and several wordings
            try (MockLlmServer s = new MockLlmServer(Behaviours.vignetteSwitch(0.5))) {
                Vignette v = new Vignette(cfg(), new PromptBuilder(Condition.neutral(), para), http(s), SETTINGS, null);
                Vignette.Spec spec = Vignette.Spec.grid(11, 2);
                VignetteRecord rec = v.run(spec, 42, para);
                double step = spec.levelsOverG().get(1) - spec.levelsOverG().get(0);
                assertThat(rec.estimate().censor()).isEqualTo(SwitchPoint.Censor.NONE);
                assertThat(Math.abs(rec.estimate().bHat() - 0.5)).isLessThanOrEqualTo(step);
                assertThat(rec.rows()).hasSize(22);
                assertThat(rec.count(VignetteRecord.Choice.REFUSED)).isZero();
                assertThat(s.callCount()).isEqualTo(22); // one row per call, no repairs
            }
        }
    }

    @Test
    void rowsAreInRandomOrderPerSeedAndEachCallHasAFreshContext() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.vignetteSwitch(0.5))) {
            Vignette v = new Vignette(cfg(), new PromptBuilder(Condition.neutral(), 2), http(s), SETTINGS, null);
            Vignette.Spec spec = Vignette.Spec.grid(10, 1);
            List<Double> a = v.run(spec, 1, 2).rows().stream().map(VignetteRecord.Row::bOverG).toList();
            List<Double> b = v.run(spec, 2, 2).rows().stream().map(VignetteRecord.Row::bOverG).toList();
            List<Double> a2 = v.run(spec, 1, 2).rows().stream().map(VignetteRecord.Row::bOverG).toList();
            assertThat(a).isNotEqualTo(spec.levelsOverG()).isNotEqualTo(b).isEqualTo(a2);
            assertThat(a).containsExactlyInAnyOrderElementsOf(spec.levelsOverG());
            for (var r : s.requests()) {
                assertThat(r.turns()).hasSize(1);
            }
        }
    }

    @Test
    void refusalIsRecordedAndExcludedNotScoredAsACost() {
        try (MockLlmServer s = new MockLlmServer(Behaviours.vignetteRefuse())) {
            Vignette v = new Vignette(cfg(), new PromptBuilder(Condition.neutral(), 0), http(s), SETTINGS, null);
            VignetteRecord rec = v.run(Vignette.Spec.grid(8, 1), 3, 0);
            assertThat(rec.count(VignetteRecord.Choice.REFUSED)).isEqualTo(8);
            assertThat(rec.estimate().censor()).isEqualTo(SwitchPoint.Censor.NO_DATA);
            assertThat(rec.estimate().bHat()).isNaN();
            // with refusals scored as the competitive choice the cell is censored at the lowest payment
            assertThat(rec.estimateRefusalsCompete().censor()).isEqualTo(SwitchPoint.Censor.LOW);
            assertThat(rec.toJson().get("refuser").asBoolean()).isTrue();
        }
        try (MockLlmServer s = new MockLlmServer(Behaviours.refuse())) { // refusal in words
            Vignette v = new Vignette(cfg(), new PromptBuilder(Condition.neutral(), 0), http(s), SETTINGS, null);
            assertThat(v.run(Vignette.Spec.grid(8, 1), 3, 0).count(VignetteRecord.Choice.REFUSED)).isEqualTo(8);
        }
    }

    @Test
    void liveAndReplayDigestsAreEqual(@TempDir Path dir) {
        Path cache = dir.resolve("v.jsonl");
        String live;
        try (MockLlmServer s = new MockLlmServer(Behaviours.vignetteSwitch(0.3))) {
            Vignette v = new Vignette(cfg(), new PromptBuilder(Condition.neutral(), 4), new CachingLlmClient(http(s), cache),
                    SETTINGS, null);
            live = v.run(Vignette.Spec.grid(12, 1), 9, 4).replayDigest();
        }
        Vignette r = new Vignette(cfg(), new PromptBuilder(Condition.neutral(), 4), new ReplayLlmClient(cache), SETTINGS, null);
        assertThat(r.run(Vignette.Spec.grid(12, 1), 9, 4).replayDigest()).isEqualTo(live);
        assertThat(live).hasSize(64);
    }

    @Test
    void priceListSizeIsEightToTwelve() {
        assertThatThrownBy(() -> Vignette.Spec.grid(7, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Vignette.Spec.grid(13, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(Vignette.Spec.grid(12, 1).levelsOverG()).hasSize(12);
    }

    @Test
    void isotonicInterpolationHandlesNoisyAndCensoredData() {
        double[] b = {0, 1, 2, 3, 4};
        // non-monotone proportions get pooled: 1, 0.2, 0.6 -> 1, 0.4, 0.4 ... crossing at b between 1 and 2
        SwitchPoint.Estimate e = SwitchPoint.estimate(b, new int[] {10, 2, 6, 0, 0}, new int[] {10, 10, 10, 10, 10});
        assertThat(e.fitted().get(1)).isEqualTo(e.fitted().get(2)).isEqualTo(0.4);
        assertThat(e.bHat()).isBetween(0.0, 1.0);
        assertThat(e.censor()).isEqualTo(SwitchPoint.Censor.NONE);
        assertThat(SwitchPoint.estimate(b, new int[] {0, 0, 0, 0, 0}, new int[] {5, 5, 5, 5, 5}).censor())
                .isEqualTo(SwitchPoint.Censor.LOW);
        assertThat(SwitchPoint.estimate(b, new int[] {5, 5, 5, 5, 5}, new int[] {5, 5, 5, 5, 5}).censor())
                .isEqualTo(SwitchPoint.Censor.HIGH);
        // linear interpolation: p = 1 at b=1, 0 at b=2 crosses at 1.5
        assertThat(SwitchPoint.estimate(new double[] {1, 2}, new int[] {4, 0}, new int[] {4, 4}).bHat()).isEqualTo(1.5);
    }
}
