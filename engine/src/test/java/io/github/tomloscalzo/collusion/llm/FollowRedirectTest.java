package io.github.tomloscalzo.collusion.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * C12a.4 (interface proposal v5, C5): Modal answers a request still pending after about 150 s with a 303 redirect to a
 * result URL; with --follow-redirects on the client follows it (GET, same origin only, the API key kept).
 */
class FollowRedirectTest {
    static final String ANSWER = "{\"quote\": 2.40, \"plan\": \"hold\", \"rationale\": \"r\"}";

    static LlmRequest req() {
        return new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "hello")), 0.6, 100,
                null, "game|x|s1|llm|r1|a0", true, null, null);
    }

    static OpenAiCompatibleClient client(MockLlmServer s, boolean follow, Duration timeout) {
        return new OpenAiCompatibleClient(s.baseUrl(), "KEYVAR", k -> k.equals("KEYVAR") ? "test-key-not-secret" : null, timeout,
                null, 1, Map.of(), follow);
    }

    @Test
    void aSlowCallAnsweredWithTwo303sIsFollowedToItsResultWithTheKeyAndTheReasoning() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> Reply.text(ANSWER)
                .withReasoning("long thought", 900).withDelayMs(300).withRedirects(2)))) {
            LlmResponse r = client(s, true, Duration.ofSeconds(10)).complete(req());
            assertThat(r.text()).isEqualTo(ANSWER);
            assertThat(r.reasoning()).isEqualTo("long thought");
            assertThat(r.latencyMs()).isGreaterThanOrEqualTo(300);
            assertThat(s.callCount()).isEqualTo(1);           // the completion was asked for once
            assertThat(s.resultFetches()).hasSize(2);          // then two GETs of the result URL
            // Modal's shape: an absolute same-origin Location with the call id as a query; the query is kept on every hop
            assertThat(s.resultFetches()).allSatisfy(f -> {
                assertThat(f.method()).isEqualTo("GET");
                assertThat(f.authorized()).isTrue();
                assertThat(f.path()).isEqualTo("/v1/results/r0");
                assertThat(f.query()).isEqualTo("__modal_function_call_id=fc-r0");
            });
        }
    }

    @Test
    void withTheSwitchOffA303StillAbortsAsToday() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> Reply.text(ANSWER).withRedirects(1)))) {
            assertThatThrownBy(() -> client(s, false, Duration.ofSeconds(10)).complete(req())).isInstanceOf(LlmException.class)
                    .hasMessageContaining("HTTP 303").hasMessageContaining("--follow-redirects on");
            assertThat(s.resultFetches()).isEmpty();
        }
    }

    @Test
    void a307RepeatsThePostWithTheSameBodyAndKey() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> q.callIndex() == 0
                ? new Reply(null, null, "", 307, "/v1/chat/completions") : Reply.text(ANSWER)))) {
            LlmResponse r = client(s, true, Duration.ofSeconds(10)).complete(req());
            assertThat(r.text()).isEqualTo(ANSWER);
            assertThat(s.requests()).hasSize(2);   // both are POSTs (only POSTs reach the completions handler as requests)
            assertThat(s.requests().get(1).rawBody()).isEqualTo(s.requests().get(0).rawBody()).isNotEmpty();
        }
    }

    @Test
    void sameOriginComparesSchemeHostAndPortWithDefaults() {
        java.net.URI a = java.net.URI.create("https://h.modal.run/v1/chat/completions");
        assertThat(OpenAiCompatibleClient.sameOrigin(a, java.net.URI.create("https://H.modal.run:443/x?y=1"))).isTrue();
        assertThat(OpenAiCompatibleClient.sameOrigin(a, java.net.URI.create("http://h.modal.run:443/x"))).isFalse();
        assertThat(OpenAiCompatibleClient.sameOrigin(a, java.net.URI.create("http://h.modal.run/x"))).isFalse();
        assertThat(OpenAiCompatibleClient.sameOrigin(a, java.net.URI.create("https://h.modal.run:8443/x"))).isFalse();
        assertThat(OpenAiCompatibleClient.sameOrigin(a, java.net.URI.create("https://evil.example/x"))).isFalse();
        assertThat(OpenAiCompatibleClient.sameOrigin(a, java.net.URI.create("mailto:x@y"))).isFalse();
        assertThat(OpenAiCompatibleClient.sameOrigin(java.net.URI.create("https://h:8443/a"), java.net.URI.create("http://h:8443/a")))
                .isFalse();
    }

    @Test
    void aRedirectToAnotherOriginIsRefusedWithoutFollowingIt() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(
                q -> Reply.seeOther("http://198.51.100.7:8000/v1/results/x")))) {
            assertThatThrownBy(() -> client(s, true, Duration.ofSeconds(10)).complete(req())).isInstanceOf(LlmException.class)
                    .hasMessageContaining("another origin").hasMessageContaining("198.51.100.7");
        }
        // a different port on the same host is another origin too
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(
                q -> Reply.seeOther("http://127.0.0.1:9/v1/results/x")))) {
            assertThatThrownBy(() -> client(s, true, Duration.ofSeconds(10)).complete(req())).isInstanceOf(LlmException.class)
                    .hasMessageContaining("another origin");
        }
    }

    @Test
    void endlessRedirectsStopAtTheLimitAndA303WithoutLocationIsAnError() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> Reply.text(ANSWER).withRedirects(1000)))) {
            assertThatThrownBy(() -> client(s, true, Duration.ofSeconds(10)).complete(req())).isInstanceOf(LlmException.class)
                    .hasMessageContaining("redirects");
            assertThat(s.resultFetches()).hasSize(OpenAiCompatibleClient.MAX_REDIRECTS);
        }
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> Reply.http(303, "")))) {
            assertThatThrownBy(() -> client(s, true, Duration.ofSeconds(10)).complete(req())).isInstanceOf(LlmException.class)
                    .hasMessageContaining("Location");
        }
    }

    @Test
    void eachHopGetsTheCallTimeoutSoASlowResultStillTimesOut() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> Reply.text(ANSWER).withRedirects(1)
                .withResultDelayMs(1500)))) {
            assertThatThrownBy(() -> client(s, true, Duration.ofMillis(400)).complete(req())).isInstanceOf(LlmException.class)
                    .hasMessageContaining("timed out");
        }
    }
}
