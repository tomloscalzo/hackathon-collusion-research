package io.github.tomloscalzo.collusion.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class LlmClientTest {
    static LlmRequest req(String draw) {
        return new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "hello")), 0.7, 100,
                null, draw);
    }

    static OpenAiCompatibleClient client(MockLlmServer s) {
        return new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(10), null, 1);
    }

    @Test
    void canonicalHashIncludesDrawIndexAndIsStable() {
        assertThat(CanonicalRequest.sha256(req("a"))).isEqualTo(CanonicalRequest.sha256(req("a"))).hasSize(64);
        assertThat(CanonicalRequest.sha256(req("a"))).isNotEqualTo(CanonicalRequest.sha256(req("b")));
        assertThat(CanonicalRequest.text(req("a"))).startsWith("{\"drawKey\":\"a\",\"maxTokens\":100,\"modelSnapshot\"");
    }

    @Test
    void clientTalksToTheMockAndSendsTheWireFields() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.fixed(2.09))) {
            LlmResponse r = client(s).complete(req("k1"));
            assertThat(r.text()).contains("\"quote\": 2.09");
            assertThat(r.tokensIn()).isPositive();
            assertThat(r.cached()).isFalse();
            var q = s.requests().get(0);
            assertThat(q.model()).isEqualTo("mock-model-1");
            assertThat(q.user()).isEqualTo("k1");
            assertThat(q.system()).isEqualTo("sys");
            assertThat(q.seed()).isEqualTo(OpenAiCompatibleClient.seedOf("k1"));
        }
    }

    @Test
    void remoteHostIsRefusedWithoutTheEnvVar() {
        assertThatThrownBy(() -> new OpenAiCompatibleClient("https://api.example.com", "SOME_KEY", k -> null,
                Duration.ofSeconds(1), null, 1)).isInstanceOf(LlmException.RemoteNotAllowed.class)
                .hasMessageContaining("api.example.com").hasMessageContaining("COLLUSION_ALLOW_REMOTE");
        assertThatThrownBy(() -> RemoteGuard.check("https://api.example.com/v1", k -> "0"))
                .isInstanceOf(LlmException.RemoteNotAllowed.class);
        assertThatThrownBy(() -> RemoteGuard.check("http://localhost.evil.com:8000", k -> null))
                .isInstanceOf(LlmException.RemoteNotAllowed.class);
        assertThatThrownBy(() -> RemoteGuard.check("http://localhost@evil.com/", k -> null))
                .isInstanceOf(LlmException.RemoteNotAllowed.class);
        assertThatThrownBy(() -> RemoteGuard.check("ftp://localhost/", k -> null)).isInstanceOf(LlmException.class);
        // allowed: loopback hosts, and a remote host only with COLLUSION_ALLOW_REMOTE=1 (no network call is made here)
        RemoteGuard.check("http://127.0.0.1:8000", k -> null);
        RemoteGuard.check("http://localhost:8000/v1", k -> null);
        RemoteGuard.check("https://x.modal.run", k -> k.equals("COLLUSION_ALLOW_REMOTE") ? "1" : null);
        assertThat(new OpenAiCompatibleClient("https://x.modal.run", "KEYVAR",
                k -> k.equals("COLLUSION_ALLOW_REMOTE") ? "1" : "secret", Duration.ofSeconds(1), null, 1).endpoint())
                .isEqualTo("https://x.modal.run/v1/chat/completions");
    }

    @Test
    void cacheHitIsByteIdenticalAndMakesNoCall(@TempDir Path dir) throws Exception {
        Path file = dir.resolve("cache.jsonl");
        try (MockLlmServer s = new MockLlmServer(r -> "{\"quote\": 2.09, \"plan\": \"café \\\"x\\\"\", \"rationale\": \"ü\"}")) {
            CachingLlmClient c = new CachingLlmClient(client(s), file);
            LlmResponse a = c.complete(req("d0"));
            LlmResponse b = c.complete(req("d0"));
            assertThat(a.cached()).isFalse();
            assertThat(b.cached()).isTrue();
            assertThat(b.text()).isEqualTo(a.text());
            assertThat(s.callCount()).isEqualTo(1);
            // a different draw index is a different entry
            c.complete(req("d1"));
            assertThat(s.callCount()).isEqualTo(2);
            assertThat(Files.readAllLines(file)).hasSize(2);
            // a fresh instance reads the file: still a hit, same bytes
            CachingLlmClient c2 = new CachingLlmClient(client(s), file);
            LlmResponse d = c2.complete(req("d0"));
            assertThat(d.cached()).isTrue();
            assertThat(d.text().getBytes(java.nio.charset.StandardCharsets.UTF_8))
                    .isEqualTo(a.text().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            assertThat(s.callCount()).isEqualTo(2);
            assertThat(c2.hits()).isEqualTo(1);
        }
    }

    @Test
    void replayClientThrowsOnAMiss(@TempDir Path dir) {
        Path file = dir.resolve("cache.jsonl");
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.fixed(2.0))) {
            new CachingLlmClient(client(s), file).complete(req("have"));
            ReplayLlmClient rp = new ReplayLlmClient(file);
            assertThat(rp.complete(req("have")).cached()).isTrue();
            assertThatThrownBy(() -> rp.complete(req("missing"))).isInstanceOf(LlmException.CacheMiss.class)
                    .hasMessageContaining("missing");
            assertThat(s.callCount()).isEqualTo(1);
        }
    }

    @Test
    void budgetReservesOncePerRunAndSettlesPerCall() {
        Budget b = new Budget(1000);
        Budget.Reservation r1 = b.reserve(600);
        assertThatThrownBy(() -> b.reserve(500)).isInstanceOf(LlmException.BudgetExceeded.class);
        r1.settle(100);
        r1.settle(150);
        assertThat(b.used()).isEqualTo(250);
        r1.close();
        assertThat(b.reserved()).isEqualTo(250);
        Budget.Reservation r2 = b.reserve(700);
        assertThatThrownBy(() -> r2.settle(701)).isInstanceOf(LlmException.BudgetExceeded.class);
        assertThatThrownBy(() -> new Budget(0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void budgetIsAtomicUnderContention() throws Exception {
        Budget b = new Budget(1000);
        AtomicLong ok = new AtomicLong();
        List<Thread> ts = new java.util.ArrayList<>();
        for (int i = 0; i < 16; i++) {
            Thread t = new Thread(() -> {
                try {
                    b.reserve(100);
                    ok.incrementAndGet();
                } catch (LlmException e) {
                    // expected for the losers
                }
            });
            ts.add(t);
            t.start();
        }
        for (Thread t : ts) {
            t.join();
        }
        assertThat(ok.get()).isEqualTo(10);
    }

    @Test
    void budgetedClientSettlesActualTokens() {
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.fixed(2.0))) {
            Budget b = new Budget(100_000);
            Budget.Reservation r = b.reserve(50_000);
            BudgetedLlmClient bc = new BudgetedLlmClient(client(s), r);
            LlmResponse a = bc.complete(req("x"));
            assertThat(b.used()).isEqualTo(a.tokensIn() + a.tokensOut());
        }
    }

    @Test
    void rateLimiterIsATokenBucket() {
        AtomicLong now = new AtomicLong();
        RateLimiter rl = new RateLimiter(2.0, 2, now::get);
        assertThat(rl.tryAcquire()).isTrue();
        assertThat(rl.tryAcquire()).isTrue();
        assertThat(rl.tryAcquire()).isFalse();
        now.addAndGet(500_000_000L); // half a second = one token at 2/s
        assertThat(rl.tryAcquire()).isTrue();
        assertThat(rl.tryAcquire()).isFalse();
        now.addAndGet(10_000_000_000L); // refill is capped at the burst
        assertThat(rl.tryAcquire()).isTrue();
        assertThat(rl.tryAcquire()).isTrue();
        assertThat(rl.tryAcquire()).isFalse();
    }

    @Test
    void serverErrorsAreRetriedThenReported() {
        try (MockLlmServer s = new MockLlmServer(r -> r.callIndex() == 0 ? null : "ok")) {
            OpenAiCompatibleClient c = new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(5), null, 2);
            assertThat(c.complete(req("e")).text()).isEqualTo("ok");
            assertThat(s.callCount()).isEqualTo(2);
        }
        try (MockLlmServer s = new MockLlmServer(r -> null)) {
            assertThatThrownBy(() -> client(s).complete(req("e"))).isInstanceOf(LlmException.class);
        }
    }

    static final String REV_A = "0123456789abcdef0123456789abcdef01234567";
    static final String REV_B = "89abcdef0123456789abcdef0123456789abcdef";

    @Test
    void servedNameOfTheRecipeParsesIntoModelIdRevisionAndVariant() {
        ModelIdentity a = ModelIdentity.parse("Qwen--Qwen2.5-7B-Instruct--" + REV_A + "+vllm0.8.5");   // the recipe's form
        assertThat(a.modelId()).isEqualTo("Qwen/Qwen2.5-7B-Instruct");
        assertThat(a.revision()).isEqualTo(REV_A);
        assertThat(a.variant()).isEqualTo("vllm0.8.5");
        assertThat(a.pinned()).isTrue();
        ModelIdentity v = ModelIdentity.parse("Qwen--Qwen2.5-14B-Instruct--" + REV_B + "+vllm0.9.1-fp16");
        assertThat(v.modelId()).isEqualTo("Qwen/Qwen2.5-14B-Instruct");
        assertThat(v.revision()).isEqualTo(REV_B);
        assertThat(v.variant()).isEqualTo("vllm0.9.1-fp16");
        ModelIdentity hand = ModelIdentity.parse("Qwen--Qwen2.5-7B-Instruct--" + REV_A);   // a hand-named backend, no variant
        assertThat(hand.revision()).isEqualTo(REV_A);
        assertThat(hand.variant()).isNull();
        assertThat(ModelIdentity.parse("gpt2--" + REV_A).modelId()).isEqualTo("gpt2");   // an id without an org
        // names outside the convention are kept whole and parse to nulls (the served name stays the identity)
        for (String n : new String[] {"mock-model-1", "collusion-llm", "Qwen--Qwen2.5-7B-Instruct--main",
                "Qwen--Qwen2.5-7B-Instruct--" + REV_A.toUpperCase(), "Qwen--Qwen2.5-7B-Instruct--" + REV_A.substring(1),
                "a--b--c--" + REV_A, "--" + REV_A, "org---name--" + REV_A, "org.--name--" + REV_A, "Qwen--Qwen2.5-7B-Instruct--" + REV_A + "+", "x--" + REV_A + "+bad tag",
                "Qwen/Qwen2.5-7B-Instruct@" + REV_A}) {
            ModelIdentity m = ModelIdentity.parse(n);
            assertThat(m.servedName()).isEqualTo(n);
            assertThat(m.modelId()).as(n).isNull();
            assertThat(m.revision()).as(n).isNull();
            assertThat(m.pinned()).as(n).isFalse();
        }
    }

    @Test
    void aServerWithServedNamesAnswers404ToAnyOtherModel() {
        String a = "Qwen--Qwen2.5-7B-Instruct--" + REV_A + "+vllm0.8.5";
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.fixed(2.09), java.util.Set.of(a))) {
            LlmRequest ok = new LlmRequest("openai-compatible", a, "sys", List.of(new LlmRequest.Turn("user", "hi")), 0.7, 100,
                    null, "k");
            assertThat(client(s).complete(ok).text()).contains("2.09");
            // the same weights at another revision, or another name, is not served: HTTP 404, no retry
            LlmRequest other = new LlmRequest("openai-compatible", "Qwen--Qwen2.5-7B-Instruct--" + REV_B + "+vllm0.8.5", "sys",
                    List.of(new LlmRequest.Turn("user", "hi")), 0.7, 100, null, "k");
            OpenAiCompatibleClient retrying = new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(5),
                    null, 3);
            assertThatThrownBy(() -> retrying.complete(other)).isInstanceOf(LlmException.class).hasMessageContaining("HTTP 404")
                    .hasMessageContaining("does not exist");
            assertThat(s.callCount()).isEqualTo(2);
        }
    }
}
