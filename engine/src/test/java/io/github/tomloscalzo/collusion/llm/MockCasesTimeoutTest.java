package io.github.tomloscalzo.collusion.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** C12a.3 (interface proposal v5, C3, C4; test plan §11 C): mock-server cases and the timeout per call type. */
class MockCasesTimeoutTest {
    static LlmRequest req(String draw) {
        return new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "hello")), 0.6, 100,
                null, draw, true, null, null);
    }

    static OpenAiCompatibleClient client(MockLlmServer s, Duration dflt, Map<String, Duration> perType) {
        return new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, dflt, null, 1, perType);
    }

    static MockLlmServer server(Reply r) {
        return new MockLlmServer(MockLlmServer.Behaviours.replies(q -> r));
    }

    @Test
    void nullContentCutOffInsideTheReasoningIsAnEmptyTruncatedReplyWithItsPartialReasoning() {
        try (MockLlmServer s = server(Reply.truncatedThinking("Let me think about the other firm ... and"))) {
            LlmResponse r = client(s, Duration.ofSeconds(10), Map.of()).complete(req("game|x|s1|llm|r1|a0"));
            assertThat(r.text()).isEmpty();
            assertThat(r.finishReason()).isEqualTo("length");
            assertThat(r.reasoning()).isEqualTo("Let me think about the other firm ... and");
        }
    }

    @Test
    void nullContentWithFinishLengthAndNoReasoningIsAlsoAnEmptyTruncatedReply() {
        try (MockLlmServer s = server(new Reply(null, null, "length", 200, null))) {
            LlmResponse r = client(s, Duration.ofSeconds(10), Map.of()).complete(req("game|x|s1|llm|r1|a0"));
            assertThat(r.text()).isEmpty();
            assertThat(r.finishReason()).isEqualTo("length");
            assertThat(r.reasoning()).isNull();
        }
    }

    @Test
    void nullContentWithReasoningAndFinishStopIsAnEmptyReplyNotAnException() {
        try (MockLlmServer s = server(new Reply(null, null, "stop", 200, null).withReasoning("thought only", 12))) {
            LlmResponse r = client(s, Duration.ofSeconds(10), Map.of()).complete(req("game|x|s1|llm|r1|a0"));
            assertThat(r.text()).isEmpty();
            assertThat(r.finishReason()).isEqualTo("stop");
            assertThat(r.reasoning()).isEqualTo("thought only");
            assertThat(r.reasoningTokens()).isEqualTo(12);
        }
    }

    @Test
    void nullContentWithoutReasoningOrLengthStillThrowsWithAClearMessage() {
        try (MockLlmServer s = server(new Reply(null, null, "stop", 200, null))) {
            assertThatThrownBy(() -> client(s, Duration.ofSeconds(10), Map.of()).complete(req("game|x|s1|llm|r1|a0")))
                    .isInstanceOf(LlmException.class).hasMessageContaining("choices[0].message.content")
                    .hasMessageContaining("finish_reason 'stop'");
        }
    }

    @Test
    void theRefusalAndFilterOrderIsCheckedBeforeTheNullContentRule() {
        try (MockLlmServer s = server(Reply.providerRefusal("no").withReasoning("r", null))) {
            LlmResponse r = client(s, Duration.ofSeconds(10), Map.of()).complete(req("game|x|s1|llm|r1|a0"));
            assertThat(r.finishReason()).isEqualTo(OpenAiCompatibleClient.FINISH_REFUSAL);
            assertThat(r.text()).isEqualTo("no");
        }
        try (MockLlmServer s = server(Reply.contentFilter(null).withReasoning("r", null))) {
            LlmResponse r = client(s, Duration.ofSeconds(10), Map.of()).complete(req("game|x|s1|llm|r1|a0"));
            assertThat(r.finishReason()).isEqualTo(OpenAiCompatibleClient.FINISH_CONTENT_FILTER);
        }
    }

    @Test
    void aThinkTagInTheContentIsKeptAsTextAndCounted() {
        try (MockLlmServer s = server(Reply.text("<think>misrouted</think>{\"quote\": 2.0}"))) {
            OpenAiCompatibleClient c = client(s, Duration.ofSeconds(10), Map.of());
            LlmResponse r = c.complete(req("game|x|s1|llm|r1|a0"));
            assertThat(r.text()).startsWith("<think>");
            assertThat(c.misroutedReplies()).isEqualTo(1);
            c.complete(req("game|x|s1|llm|r2|a0"));
            assertThat(c.misroutedReplies()).isEqualTo(2);
        }
        try (MockLlmServer s = server(Reply.text("{\"quote\": 2.0}"))) {
            OpenAiCompatibleClient c = client(s, Duration.ofSeconds(10), Map.of());
            c.complete(req("game|x|s1|llm|r1|a0"));
            assertThat(c.misroutedReplies()).isZero();
        }
    }

    @Test
    void aSlowReplyPastTheTimeoutFailsAndAPerCallTypeTimeoutLetsItThrough() {
        try (MockLlmServer s = server(Reply.text("{\"quote\": 2.0}").withDelayMs(1200))) {
            OpenAiCompatibleClient c = client(s, Duration.ofMillis(300), Map.of("quote", Duration.ofSeconds(5)));
            // a quote call (game|...) gets 5 s: it waits for the slow reply
            long t0 = System.nanoTime();
            assertThat(c.complete(req("game|x|s1|llm|r1|a0")).text()).contains("2.0");
            assertThat((System.nanoTime() - t0) / 1_000_000L).isGreaterThanOrEqualTo(1100);
            // a probe call has no entry: the 300 ms default applies, and the error names the timeout and the call type
            assertThatThrownBy(() -> c.complete(req("probe|x|s1|llm|r1"))).isInstanceOf(LlmException.class)
                    .hasMessageContaining("timed out").hasMessageContaining("probe").hasMessageContaining("PT0.3S");
        }
    }

    @Test
    void aReplyCutOffInsideAnUnclosedThinkInTheContentStaysTextAndIsCounted() {
        // the shape a reasoning parser may give when </think> never came: content "<think>partial...", no reasoning field
        try (MockLlmServer s = server(Reply.truncated("<think>The other firm held 2.40 and"))) {
            OpenAiCompatibleClient c = client(s, Duration.ofSeconds(10), Map.of());
            LlmResponse r = c.complete(req("game|x|s1|llm|r1|a0"));
            assertThat(r.text()).isEqualTo("<think>The other firm held 2.40 and");
            assertThat(r.finishReason()).isEqualTo("length");
            assertThat(r.reasoning()).isNull();
            assertThat(c.misroutedReplies()).isEqualTo(1);
        }
    }

    @Test
    void reasoningOnAThinkingOffRequestIsCountedAsMisrouted() {
        LlmRequest off = new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "hello")),
                0.7, 100, null, "game|x|s1|llm|r1|a0", false, null, null);
        try (MockLlmServer s = server(new Reply(null, null, "stop", 200, null).withReasoning("{\"quote\": 2.0}", null))) {
            OpenAiCompatibleClient c = client(s, Duration.ofSeconds(10), Map.of());
            LlmResponse r = c.complete(off);
            assertThat(r.text()).isEmpty();
            assertThat(c.misroutedReplies()).isEqualTo(1);
            c.complete(req("game|x|s1|llm|r2|a0"));   // thinking on: reasoning is expected, not counted
            assertThat(c.misroutedReplies()).isEqualTo(1);
        }
    }

    @Test
    void theConstructorRefusesAnUnknownCallTypeKey() {
        try (MockLlmServer s = server(Reply.text("x"))) {
            assertThatThrownBy(() -> client(s, Duration.ofSeconds(1), Map.of("game", Duration.ofSeconds(5))))
                    .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("game");
        }
    }

    @Test
    void callTypesComeFromTheDrawKeyPrefix() {
        assertThat(OpenAiCompatibleClient.callType("game|x|s1|llm|r1|a0")).isEqualTo("quote");
        assertThat(OpenAiCompatibleClient.callType("probe|x|s1|llm|r1")).isEqualTo("probe");
        assertThat(OpenAiCompatibleClient.callType("vig|x|s1|p0|row1|b0.1000|cA|d0|a0")).isEqualTo("vignette");
        assertThat(OpenAiCompatibleClient.callType("talk|x|s1|llm|r1|t0|a0")).isEqualTo("talk");
        assertThat(OpenAiCompatibleClient.callType("question|r2|fed|x|s1|llm|r1|a0")).isEqualTo("question");
        assertThat(OpenAiCompatibleClient.callType("k1")).isEqualTo("other");
        assertThatThrownBy(() -> OpenAiCompatibleClient.parseCallTimeouts("quote=140,bogus=3"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("bogus");
        assertThatThrownBy(() -> OpenAiCompatibleClient.parseCallTimeouts("quote=0"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(OpenAiCompatibleClient.parseCallTimeouts("quote=140, probe=120"))
                .containsEntry("quote", Duration.ofSeconds(140)).containsEntry("probe", Duration.ofSeconds(120)).hasSize(2);
        assertThat(OpenAiCompatibleClient.parseCallTimeouts(null)).isEmpty();
    }
}
