package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.agents.llm.ParaphraseFile;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class LlmCliTest {
    static Map<String, String> o(String... kv) {
        Map<String, String> m = new TreeMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put(kv[i], kv[i + 1]);
        }
        return m;
    }

    @Test
    void gameRunWritesSummaryManifestCallsAndReplaysToTheSameDigest(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("runs.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            LlmCommands.run(o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model", "mock-model-1",
                    "seed", "11", "runs", "2", "out", out.toString(), "paraphrase", "4", "condition", "elicitation=E1,notice=on",
                    "arm", "e1-notice", "analysis-script", "../tools/analysis.py"));
        }
        // per-run JSONL: the fields tools/analysis.py reads
        var lines = Files.readAllLines(out);
        assertThat(lines).hasSize(2);
        JsonNode l0 = Canonical.MAPPER.readTree(lines.get(0));
        assertThat(l0.get("arm").asText()).isEqualTo("e1-notice");
        assertThat(l0.get("paraphrase").asInt()).isEqualTo(4);
        assertThat(l0.get("seed").asLong()).isEqualTo(11);
        assertThat(l0.get("pAdhere").asDouble()).isEqualTo(1.0);
        assertThat(l0.has("meanCi")).isTrue();
        assertThat(l0.has("pCollude")).isTrue();
        assertThat(l0.has("responder")).isTrue();
        assertThat(l0.get("replayDigest").asText()).hasSize(64);
        assertThat(l0.get("llm").get("model").asText()).isEqualTo("mock-model-1");

        // call records
        var calls = Files.readAllLines(Path.of(out + ".calls.jsonl"));
        assertThat(calls.size()).isGreaterThanOrEqualTo(2);
        JsonNode c0 = Canonical.MAPPER.readTree(calls.get(0));
        assertThat(c0.get("requestHash").asText()).hasSize(64);
        assertThat(c0.has("tokensIn")).isTrue();
        assertThat(c0.has("latencyMs")).isTrue();
        assertThat(c0.get("parseStatus").asText()).isEqualTo("OK");

        // manifest: model snapshot, temperature, template and paraphrase hashes, budget used
        JsonNode m = Canonical.MAPPER.readTree(Files.readString(Path.of(out + ".manifest.json")));
        JsonNode llm = m.get("llm");
        assertThat(llm.get("modelSnapshot").asText()).isEqualTo("mock-model-1");
        assertThat(llm.get("temperature").asDouble()).isEqualTo(0.7);
        for (var e : ParaphraseFile.allHashes().entrySet()) {
            assertThat(llm.get("templateHashes").get(e.getKey()).asText()).isEqualTo(e.getValue());
        }
        assertThat(llm.get("paraphraseItemHashes").size()).isEqualTo(36);
        assertThat(llm.get("budgetUsedTokens").asLong()).isPositive();
        assertThat(llm.get("analysisScriptSha256").asText()).matches("[0-9a-f]{64}");
        assertThat(llm.has("apiKey")).isFalse();
        assertThat(m.get("tool").asText()).contains("LLM");

        // replay from the cache alone: server is closed, digests equal
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
        // a cache that lacks the calls: replay reports problems instead of calling anything
        Path empty = dir.resolve("empty.jsonl");
        Files.writeString(empty, "");
        assertThat(LlmCommands.replay(o("cache", empty.toString(), "run", out.toString()))).isEqualTo(2);
    }

    @Test
    void vignetteCommandAndReplay(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("v.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.vignetteSwitch(0.5))) {
            LlmCommands.vignette(o("scenario", "scenarios/ripe-game.yaml", "base-url", s.baseUrl(), "model", "mock-model-1",
                    "rows", "11", "draws", "2", "seed", "5", "out", out.toString(), "paraphrase", "1"));
            assertThat(s.callCount()).isEqualTo(22);
        }
        JsonNode v = Canonical.MAPPER.readTree(Files.readAllLines(out).get(0));
        assertThat(v.get("bHat").asDouble()).isBetween(0.3, 0.7);
        assertThat(v.get("refusals").asInt()).isZero();
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
    }

    @Test
    void costCommandMakesNoCall() {
        LlmCommands.cost(o("scenario", "scenarios/ripe-game.yaml", "runs", "200", "rounds", "25", "rows", "11", "draws", "3",
                "passes", "10", "usd-per-mtok-in", "0.2", "usd-per-mtok-out", "0.6"));
    }

    static final String REV_A = "0123456789abcdef0123456789abcdef01234567";
    static final String REV_B = "89abcdef0123456789abcdef0123456789abcdef";
    // the deploy recipe's served names: the same weights at two revisions, under vLLM 0.8.5
    static final String MODEL_A = "Qwen--Qwen2.5-7B-Instruct--" + REV_A + "+vllm0.8.5";
    static final String MODEL_B = "Qwen--Qwen2.5-7B-Instruct--" + REV_B + "+vllm0.8.5";

    static Map<String, String> runOpts(String base, String model, Path out, Path cache) {
        return o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", base, "model", model, "seed", "3",
                "runs", "2", "paraphrase", "2", "arm", "ripe", "out", out.toString(), "cache", cache.toString());
    }

    @Test
    void twoRevisionsOfOneModelNeverShareCacheEntriesAndKeepTheirIdentityInEveryRecord(@TempDir Path dir) throws Exception {
        Path cache = dir.resolve("shared.cache.jsonl");   // one cache file for both, on purpose
        Path a = dir.resolve("a.jsonl");
        Path b = dir.resolve("b.jsonl");
        // like vLLM --served-model-name: the server answers only these names; revision B undercuts, revision A adheres
        try (MockLlmServer s = new MockLlmServer(r -> r.model().equals(MODEL_B) ? Behaviours.decisionJson(2.08, "undercut")
                : Behaviours.decisionJson(2.09, "hold"), java.util.Set.of(MODEL_A, MODEL_B))) {
            LlmCommands.run(runOpts(s.baseUrl(), MODEL_A, a, cache));
            int callsA = s.callCount();
            // identical scenario, seeds, paraphrase, condition and arm: only the served name differs
            LlmCommands.run(runOpts(s.baseUrl(), MODEL_B, b, cache));
            JsonNode mb = Canonical.MAPPER.readTree(Files.readString(Path.of(b + ".manifest.json"))).get("llm");
            assertThat(mb.get("cacheHits").asLong()).isZero();                       // nothing of A was reused
            assertThat(mb.get("cacheMisses").asLong()).isEqualTo(s.callCount() - callsA);
            assertThat(s.requests().stream().map(MockLlmServer.MockRequest::model).distinct()).containsExactlyInAnyOrder(MODEL_A, MODEL_B);
        }
        // the shared cache holds disjoint key sets, each line labelled with its served name
        var hashes = new java.util.HashMap<String, java.util.Set<String>>();
        for (String l : Files.readAllLines(cache)) {
            JsonNode n = Canonical.MAPPER.readTree(l);
            hashes.computeIfAbsent(n.get("modelSnapshot").asText(), k -> new java.util.HashSet<>()).add(n.get("hash").asText());
        }
        assertThat(hashes.keySet()).containsExactlyInAnyOrder(MODEL_A, MODEL_B);
        assertThat(hashes.get(MODEL_A)).doesNotContainAnyElementsOf(hashes.get(MODEL_B));
        // run lines and manifests carry the full identity
        for (Path p : new Path[] {a, b}) {
            String model = p == a ? MODEL_A : MODEL_B;
            for (String l : Files.readAllLines(p)) {
                JsonNode n = Canonical.MAPPER.readTree(l);
                assertThat(n.get("llm").get("model").asText()).isEqualTo(model);
                assertThat(n.get("llm").get("provider").asText()).isEqualTo("openai-compatible");
            }
            JsonNode m = Canonical.MAPPER.readTree(Files.readString(Path.of(p + ".manifest.json"))).get("llm");
            assertThat(m.get("modelSnapshot").asText()).isEqualTo(model);
            assertThat(m.get("modelId").asText()).isEqualTo("Qwen/Qwen2.5-7B-Instruct");
            assertThat(m.get("modelRevision").asText()).isEqualTo(p == a ? REV_A : REV_B);
            assertThat(m.get("modelVariant").asText()).isEqualTo("vllm0.8.5");
            assertThat(m.get("baseUrlHost").asText()).isEqualTo("127.0.0.1");
        }
        assertThat(Canonical.MAPPER.readTree(Files.readAllLines(a).get(0)).get("pAdhere").asDouble()).isEqualTo(1.0);
        assertThat(Canonical.MAPPER.readTree(Files.readAllLines(b).get(0)).get("pAdhere").asDouble()).isLessThan(1.0);
        // each run file replays from the shared cache with no network, each against its own entries
        assertThat(LlmCommands.replay(o("cache", cache.toString(), "run", a.toString()))).isZero();
        assertThat(LlmCommands.replay(o("cache", cache.toString(), "run", b.toString()))).isZero();
        // replay rebuilds every request from llm.model: under a served name with no cache entries nothing replays.
        // (The game digest hashes the rounds only, so a line relabelled to another cached model whose replies give
        // the same rounds would still replay OK: replay checks reproducibility, not which model a line names; F25.)
        Path relabelled = dir.resolve("relabelled.jsonl");
        Files.writeString(relabelled, Files.readString(a).replace(MODEL_A, "Qwen--Qwen2.5-7B-Instruct--" + "f".repeat(40)
                + "+vllm0.8.5"));
        assertThat(LlmCommands.replay(o("cache", cache.toString(), "run", relabelled.toString()))).isEqualTo(2);
    }

    @Test
    void aModelNameTheServerDoesNotServeAbortsAtTheFirstCallAndWritesNoManifest(@TempDir Path dir) {
        Path out = dir.resolve("r.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09), java.util.Set.of(MODEL_A))) {
            assertThatThrownBy(() -> LlmCommands.run(runOpts(s.baseUrl(), MODEL_B, out, dir.resolve("c.jsonl"))))
                    .isInstanceOf(LlmException.class).hasMessageContaining("HTTP 404");
            assertThat(s.callCount()).isEqualTo(1);
        }
        assertThat(Files.exists(out)).isFalse();
        assertThat(Files.exists(Path.of(out + ".manifest.json"))).isFalse();
    }

    @Test
    void aModelNameOutsideTheRecipeConventionIsRecordedWholeWithNullRevision(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("r.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            LlmCommands.run(runOpts(s.baseUrl(), "mock-model-1", out, dir.resolve("c.jsonl")));
        }
        JsonNode m = Canonical.MAPPER.readTree(Files.readString(Path.of(out + ".manifest.json"))).get("llm");
        assertThat(m.get("modelSnapshot").asText()).isEqualTo("mock-model-1");
        assertThat(m.get("modelId").isNull()).isTrue();
        assertThat(m.get("modelRevision").isNull()).isTrue();
        // spaces, control and invisible Unicode characters would make two identities print alike: refused before any
        // file is written
        for (String bad : new String[] {"mock-model-1 ", " mock-model-1", "mock model", "m\tx", "", "mock-model-1\u00a0",
                "mock\u200bmodel", "\ufeffmock-model-1", "mod\u00e8le"}) {
            Path o2 = dir.resolve("bad.jsonl");
            assertThatThrownBy(() -> LlmCommands.run(runOpts("http://127.0.0.1:9", bad, o2, dir.resolve("c2.jsonl"))))
                    .as("'" + bad + "'").isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--model");
            assertThat(Files.exists(o2)).isFalse();
        }
    }

    @Test
    void remoteBaseUrlIsRefusedByTheCommandsToo(@TempDir Path dir) {
        assertThatThrownBy(() -> LlmCommands.run(o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url",
                "https://api.example.com", "model", "m", "out", dir.resolve("r.jsonl").toString(), "api-key-env", "NOPE")))
                .isInstanceOf(LlmException.RemoteNotAllowed.class);
        assertThat(Files.exists(dir.resolve("r.jsonl"))).isFalse();
    }
}
