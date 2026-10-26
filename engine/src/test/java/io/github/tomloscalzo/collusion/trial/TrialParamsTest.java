package io.github.tomloscalzo.collusion.trial;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** C4.1: the params.json writer (scope 4.6). Logging only: nothing here touches prompts, cache keys or digests. */
class TrialParamsTest {
    private static final String SERVED = "Qwen--Qwen3-14B--" + "a".repeat(40) + "+vllm0.8.5";

    private static TrialParams.Builder full() {
        return TrialParams.builder("m-chat__p3__w1__s7", "M-CHAT")
                .condition("neutral").penaltyPoint(3)
                .market(Map.of("s0", 1.0, "sBar", 5.0, "fine", 500.0, "continuation", 0.95))
                .prices(1.0, 3.0).highThreshold(0.7)
                .seat("llm1", "llm", null, SERVED)
                .seat("bot", "scripted", "trigger-k", null)
                .wording(1).seed(7).drawKeys(List.of("game|s|s7|llm1|r1|a0", "talk|s|s7|llm1|r1|t0|a0"))
                .talkLimits(7, 150)
                .conditionText("chat_monitored", "TALK_NOTICE", "A regulator reads all messages.", List.of("llm1"))
                .sampling(0.7, 400, true)
                .codeCommit("abc123")
                .promptFingerprint("game_system_m", "f".repeat(64))
                .scenarioFingerprint("e".repeat(64));
    }

    @Test
    void writesEveryParameterOfTheTrial(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("params.json");
        full().build().write(f);
        JsonNode n = Canonical.MAPPER.readTree(Files.readString(f, StandardCharsets.UTF_8));
        assertThat(n.path("trial").asText()).isEqualTo("m-chat__p3__w1__s7");
        assertThat(n.path("arm").asText()).isEqualTo("M-CHAT");
        assertThat(n.path("competitive_price").asDouble()).isEqualTo(1.0);
        assertThat(n.path("collusive_price").asDouble()).isEqualTo(3.0);
        assertThat(n.path("high_threshold").asDouble()).isEqualTo(0.7);
        assertThat(n.path("n_firms").asInt()).isEqualTo(2);
        assertThat(n.path("expected_penalty_point").asInt()).isEqualTo(3);
        assertThat(n.path("market").path("fine").asDouble()).isEqualTo(500.0);
        assertThat(n.path("wording_index").asInt()).isEqualTo(1);
        assertThat(n.path("seed").asLong()).isEqualTo(7);
        assertThat(n.path("draw_keys")).hasSize(2);
        assertThat(n.path("talk").path("max_messages").asInt()).isEqualTo(7);
        assertThat(n.path("talk").path("max_words").asInt()).isEqualTo(150);
        assertThat(n.path("condition_texts").get(0).path("seats").get(0).asText()).isEqualTo("llm1");
        assertThat(n.path("condition_texts").get(0).path("slot").asText()).isEqualTo("TALK_NOTICE");
        assertThat(n.path("sampling").path("temperature").asDouble()).isEqualTo(0.7);
        assertThat(n.path("sampling").path("max_tokens").asInt()).isEqualTo(400);
        assertThat(n.path("thinking").asBoolean()).isTrue();
        assertThat(n.path("code_commit").asText()).isEqualTo("abc123");
        assertThat(n.path("prompt_fingerprints").path("game_system_m").asText()).hasSize(64);
        assertThat(n.path("scenario_fingerprint").asText()).hasSize(64);
    }

    @Test
    void seatsCarryModelIdentityOrScriptedRule() {
        JsonNode n = full().build().toJson();
        JsonNode llm = n.path("seats").get(0);
        assertThat(llm.path("kind").asText()).isEqualTo("llm");
        assertThat(llm.path("model").path("served_name").asText()).isEqualTo(SERVED);
        assertThat(llm.path("model").path("model_id").asText()).isEqualTo("Qwen/Qwen3-14B");
        assertThat(llm.path("model").path("revision").asText()).isEqualTo("a".repeat(40));
        assertThat(llm.path("model").path("variant").asText()).isEqualTo("vllm0.8.5");
        JsonNode bot = n.path("seats").get(1);
        assertThat(bot.path("rule").asText()).isEqualTo("trigger-k");
        assertThat(bot.has("model")).isFalse();
    }

    @Test
    void outputIsCanonicalAndDeterministic(@TempDir Path dir) throws Exception {
        Path a = dir.resolve("a.json");
        Path b = dir.resolve("b.json");
        full().build().write(a);
        full().build().write(b);
        assertThat(Files.readString(a)).isEqualTo(Files.readString(b)).endsWith("\n");
        JsonNode n = Canonical.MAPPER.readTree(Files.readString(a));
        assertThat(Canonical.text(n) + "\n").isEqualTo(Files.readString(a));
    }

    @Test
    void refusesToBuildWithoutThePricesDeriveNeeds() {
        assertThatThrownBy(() -> TrialParams.builder("t", "A").seat("x", "llm", null, SERVED).build())
                .isInstanceOf(IllegalStateException.class).hasMessageContaining("competitive_price");
        assertThatThrownBy(() -> TrialParams.builder("t", "A").prices(3.0, 1.0).build())
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrialParams.builder("t", "A").prices(1.0, 3.0).build())
                .isInstanceOf(IllegalStateException.class).hasMessageContaining("seat");
    }

    @Test
    void highThresholdIsOmittedUnlessSetAndTalkOnlyWhenGiven() {
        JsonNode n = TrialParams.builder("t", "S").prices(1.0, 2.0).seat("a", "llm", null, "mock-model-1").build().toJson();
        assertThat(n.has("high_threshold")).isFalse();
        assertThat(n.has("talk")).isFalse();
        assertThat(n.path("seats").get(0).path("model").path("model_id").isNull()).isTrue();
    }

    @Test
    void fileFingerprintIgnoresLineEndingStyle(@TempDir Path dir) throws Exception {
        Path lf = dir.resolve("lf.json");
        Path crlf = dir.resolve("crlf.json");
        Files.writeString(lf, "{\"a\":1}\n{\"b\":2}\n");
        Files.writeString(crlf, "{\"a\":1}\r\n{\"b\":2}\r\n");
        assertThat(TrialParams.fileFingerprint(lf)).isEqualTo(TrialParams.fileFingerprint(crlf)).hasSize(64);
    }

    @Test
    void writesOnePromptFingerprintStringForCollect() {
        JsonNode a = full().build().toJson();
        assertThat(a.path("prompt_fingerprint").asText()).hasSize(64);
        assertThat(full().build().toJson().path("prompt_fingerprint")).isEqualTo(a.path("prompt_fingerprint"));
        JsonNode b = full().promptFingerprint("game_system_m", "0".repeat(64)).build().toJson();
        assertThat(b.path("prompt_fingerprint")).isNotEqualTo(a.path("prompt_fingerprint"));
        // the scenario is not part of it: the trials of one arm play several scenario files (one per penalty point)
        JsonNode c = full().scenarioFingerprint("1".repeat(64)).build().toJson();
        assertThat(c.path("prompt_fingerprint")).isEqualTo(a.path("prompt_fingerprint"));
        assertThat(c.path("scenario_fingerprint")).isNotEqualTo(a.path("scenario_fingerprint"));
        assertThat(TrialParams.builder("t", "S").prices(1, 2).seat("a", "llm", null, "m").build().toJson()
                .has("prompt_fingerprint")).isFalse();
    }

    @Test
    void feedsDeriveSummaryKeys() {
        JsonNode n = full().build().toJson();
        for (String k : List.of("competitive_price", "collusive_price")) {
            assertThat(n.get(k).isNumber()).as(k).isTrue();
        }
    }

    @Test
    void rejectsBadSeatKindAndDuplicateSeat() {
        assertThatThrownBy(() -> TrialParams.builder("t", "A").seat("x", "LLM", null, SERVED))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TrialParams.builder("t", "A").seat("x", "llm", null, SERVED).seat("x", "llm", null, SERVED))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
