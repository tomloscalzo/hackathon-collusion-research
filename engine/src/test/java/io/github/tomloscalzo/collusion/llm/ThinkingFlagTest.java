package io.github.tomloscalzo.collusion.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.time.Duration;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** C12a.1 (interface proposal v5, C1, C2, D1): the optional thinking flag, top_p and top_k on the request. */
class ThinkingFlagTest {
    static final String SCHEMA = "{\"type\":\"object\"}";

    static LlmRequest unset(String schema) {
        return new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "hello")), 0.7, 100,
                schema, "game|x|s1|llm|r1|a0");
    }

    static LlmRequest with(Boolean thinking, Double topP, Integer topK) {
        return new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "hello")), 0.7, 100,
                null, "game|x|s1|llm|r1|a0", thinking, topP, topK);
    }

    /** The canonical text and wire body of today's code (before C12a.1), written out by hand. */
    static final String CANONICAL_TODAY = "{\"drawKey\":\"game|x|s1|llm|r1|a0\",\"maxTokens\":100,\"modelSnapshot\":\"mock-model-1\","
            + "\"provider\":\"openai-compatible\",\"responseSchema\":null,\"system\":\"sys\",\"temperature\":0.7,"
            + "\"turns\":[{\"content\":\"hello\",\"role\":\"user\"}]}";

    static String bodyToday() {
        return "{\"max_tokens\":100,\"messages\":[{\"content\":\"sys\",\"role\":\"system\"},{\"content\":\"hello\",\"role\":\"user\"}],"
                + "\"model\":\"mock-model-1\",\"seed\":" + OpenAiCompatibleClient.seedOf("game|x|s1|llm|r1|a0")
                + ",\"temperature\":0.7,\"user\":\"game|x|s1|llm|r1|a0\"}";
    }

    @Test
    void unsetIsByteIdenticalToTodayInTheCanonicalTextAndTheWireBody() {
        assertThat(CanonicalRequest.text(unset(null))).isEqualTo(CANONICAL_TODAY);
        assertThat(CanonicalRequest.text(with(null, null, null))).isEqualTo(CANONICAL_TODAY);
        assertThat(CanonicalRequest.sha256(with(null, null, null))).isEqualTo(Canonical.sha256(CANONICAL_TODAY));
        assertThat(OpenAiCompatibleClient.body(unset(null))).isEqualTo(bodyToday());
        assertThat(OpenAiCompatibleClient.body(with(null, null, null))).isEqualTo(bodyToday());
        String withSchema = OpenAiCompatibleClient.body(unset(SCHEMA));
        assertThat(withSchema).doesNotContain("chat_template_kwargs").doesNotContain("top_p").doesNotContain("top_k");
        assertThat(CanonicalRequest.text(unset(SCHEMA))).doesNotContain("thinking").doesNotContain("topP").doesNotContain("topK");
    }

    @Test
    void thinkingOnOffAndUnsetGiveThreeDifferentHashesAndEnterTheCanonicalTextOnlyWhenSet() {
        String u = CanonicalRequest.sha256(with(null, null, null));
        String on = CanonicalRequest.sha256(with(true, null, null));
        String off = CanonicalRequest.sha256(with(false, null, null));
        assertThat(Set.of(u, on, off)).hasSize(3);
        assertThat(CanonicalRequest.text(with(false, null, null))).isEqualTo(CANONICAL_TODAY.replace(
                "\"temperature\":0.7,", "\"temperature\":0.7,\"thinking\":false,"));
        assertThat(CanonicalRequest.text(with(true, 0.95, 20))).contains("\"thinking\":true").contains("\"topK\":20")
                .contains("\"topP\":0.95");
        // top_p and top_k are fingerprinted on their own too
        assertThat(CanonicalRequest.sha256(with(null, 0.8, null))).isNotEqualTo(u);
        assertThat(CanonicalRequest.sha256(with(null, null, 20))).isNotEqualTo(u);
        assertThat(CanonicalRequest.sha256(with(false, 0.8, 20))).isNotEqualTo(CanonicalRequest.sha256(with(false, 0.95, 20)));
    }

    @Test
    void wireBodyCarriesEnableThinkingExplicitlyInBothStatesAndTopPTopKOnlyWhenSet() throws Exception {
        JsonNode off = Canonical.MAPPER.readTree(OpenAiCompatibleClient.body(with(false, null, null)));
        assertThat(off.path("chat_template_kwargs").path("enable_thinking").isBoolean()).isTrue();
        assertThat(off.path("chat_template_kwargs").path("enable_thinking").asBoolean()).isFalse();
        assertThat(off.path("chat_template_kwargs").size()).isEqualTo(1);
        assertThat(off.has("top_p")).isFalse();
        assertThat(off.has("top_k")).isFalse();
        JsonNode on = Canonical.MAPPER.readTree(OpenAiCompatibleClient.body(with(true, 0.95, 20)));
        assertThat(on.path("chat_template_kwargs").path("enable_thinking").asBoolean()).isTrue();
        assertThat(on.path("top_p").asDouble()).isEqualTo(0.95);
        assertThat(on.path("top_k").isInt()).isTrue();
        assertThat(on.path("top_k").asInt()).isEqualTo(20);
        // the request fields are not leaked to the wire under their canonical names
        assertThat(on.has("thinking")).isFalse();
        assertThat(on.has("topP")).isFalse();
        // seed and user are the same in both modes: paired runs share the provider seed (proposal §4)
        assertThat(on.path("seed")).isEqualTo(off.path("seed"));
        assertThat(on.path("user")).isEqualTo(off.path("user"));
        // with the flag unset and top_p set, no chat_template_kwargs is sent
        JsonNode p = Canonical.MAPPER.readTree(OpenAiCompatibleClient.body(with(null, 0.8, null)));
        assertThat(p.has("chat_template_kwargs")).isFalse();
        assertThat(p.path("top_p").asDouble()).isEqualTo(0.8);
    }

    @Test
    void theMockServerReceivesTheFlag() throws Exception {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.fixed(2.09))) {
            OpenAiCompatibleClient c = new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(10), null, 1);
            c.complete(with(false, null, null));
            c.complete(unset(null));
            JsonNode first = Canonical.MAPPER.readTree(s.requests().get(0).rawBody());
            assertThat(first.path("chat_template_kwargs").path("enable_thinking").asBoolean(true)).isFalse();
            assertThat(s.requests().get(1).rawBody()).doesNotContain("chat_template_kwargs");
        }
    }

    @Test
    void outOfRangeTopPAndTopKAreRejected() {
        assertThatThrownBy(() -> with(null, 0.0, null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> with(null, 1.5, null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> with(null, null, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> with(null, null, -2)).isInstanceOf(IllegalArgumentException.class);
        assertThat(with(null, 1.0, -1).topK()).isEqualTo(-1);
    }
}
