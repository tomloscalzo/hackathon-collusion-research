package io.github.tomloscalzo.collusion.testsupport;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.OpenAiCompatibleClient;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;

/** The test-only network guard itself: it is active, it blocks and records non-loopback requests, loopback still works. */
class NoRemoteNetworkGuardTest {
    static final String BLOCKED = "blocked-by-test-guard.invalid";

    @Test
    void theTestJvmHasNoRemotePermission() {
        assertThat(System.getenv("COLLUSION_ALLOW_REMOTE")).isNotEqualTo("1");
    }

    @Test
    void theGuardIsInstalledByAutodetectionNotByThisTest() {
        // a class literal does not initialise the class, so this sees what JUnit's auto-detection installed
        assertThat(java.net.ProxySelector.getDefault().getClass().getName())
                .startsWith(NoRemoteNetworkExtension.class.getName() + "$");
    }

    @Test
    void aRawSocketToANonLoopbackAddressIsBlockedAndRecorded() {
        NoRemoteNetworkExtension.drainViolations();
        // 192.0.2.1 is TEST-NET-1 (never routed); the guard must refuse it before any packet leaves
        assertThatThrownBy(() -> {
            try (java.net.Socket s = new java.net.Socket()) {
                s.connect(new java.net.InetSocketAddress("192.0.2.1", 80), 3000);
            }
        }).isInstanceOf(IOException.class);
        assertThat(NoRemoteNetworkExtension.drainViolations()).anyMatch(u -> u.contains("192.0.2.1"));
    }

    @Test
    void aNonLoopbackHttpRequestIsBlockedAndRecorded() {
        NoRemoteNetworkExtension.drainViolations();
        HttpClient c = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        HttpRequest r = HttpRequest.newBuilder(URI.create("http://" + BLOCKED + "/v1/chat/completions"))
                .timeout(Duration.ofSeconds(5)).GET().build();
        assertThatThrownBy(() -> c.send(r, HttpResponse.BodyHandlers.discarding())).isInstanceOf(IOException.class);
        assertThat(NoRemoteNetworkExtension.drainViolations()).anyMatch(u -> u.contains(BLOCKED));
    }

    @Test
    void theEngineClientIsBlockedEvenWhenTheRemoteGuardIsBypassed() {
        NoRemoteNetworkExtension.drainViolations();
        // the worst case: RemoteGuard told (through an injected environment) that remote calls are allowed
        OpenAiCompatibleClient cl = new OpenAiCompatibleClient("https://" + BLOCKED, "KEYVAR",
                k -> k.equals("COLLUSION_ALLOW_REMOTE") ? "1" : "not-a-real-key", Duration.ofSeconds(5), null, 1);
        LlmRequest req = new LlmRequest("openai-compatible", "m", "sys", List.of(new LlmRequest.Turn("user", "hi")), 0.7, 10,
                null, "guard-test");
        assertThatThrownBy(() -> cl.complete(req)).isInstanceOf(LlmException.class);
        assertThat(NoRemoteNetworkExtension.drainViolations()).anyMatch(u -> u.contains(BLOCKED));
    }

    @Test
    void loopbackIsNotAffected() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.fixed(2.09))) {
            OpenAiCompatibleClient cl = new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(5), null, 1);
            LlmRequest req = new LlmRequest("openai-compatible", "m", "sys", List.of(new LlmRequest.Turn("user", "hi")), 0.7,
                    10, null, "loopback");
            assertThat(cl.complete(req).text()).contains("2.09");
        }
        assertThat(NoRemoteNetworkExtension.drainViolations()).isEmpty();
        assertThat(NoRemoteNetworkExtension.isLoopback("localhost.evil.com")).isFalse();
        assertThat(NoRemoteNetworkExtension.isLoopback("127.0.0.1")).isTrue();
        assertThat(NoRemoteNetworkExtension.isLoopback("[0:0:0:0:0:0:0:1]")).isTrue();
        assertThat(NoRemoteNetworkExtension.isLoopback("[::1]")).isTrue();
    }
}
