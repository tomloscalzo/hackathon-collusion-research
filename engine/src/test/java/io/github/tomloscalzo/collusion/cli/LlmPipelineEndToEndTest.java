package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviour;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The LLM path end to end through the real CLI commands against the local mock (no network): a multi-run command, its
 * cache, call log and manifest; a rerun served entirely from the cache; cache isolation (a changed prompt, model or
 * sampling setting never hits a stale entry); refusal paths that complete and replay; concurrent shards that are
 * byte-identical to sequential ones; and replay that fails loudly when the recorded parameters do not match the cache.
 */
class LlmPipelineEndToEndTest {
    static final double SP = 2.09;

    static Map<String, String> o(String... kv) {
        Map<String, String> m = new TreeMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put(kv[i], kv[i + 1]);
        }
        return m;
    }

    /** The options of one `run --seat LLM` shard; extra key/value pairs override the defaults. */
    static Map<String, String> shard(String baseUrl, Path out, String... extra) {
        Map<String, String> m = o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", baseUrl, "model",
                "mock-model-1", "seed", "1", "runs", "2", "paraphrase", "0", "arm", "ripe", "out", out.toString());
        m.putAll(o(extra));
        return m;
    }

    static List<JsonNode> jsonl(Path p) throws IOException {
        List<JsonNode> out = new ArrayList<>();
        if (!Files.exists(p)) {
            return out;
        }
        for (String l : Files.readAllLines(p, StandardCharsets.UTF_8)) {
            if (!l.isBlank()) {
                out.add(Canonical.MAPPER.readTree(l));
            }
        }
        return out;
    }

    static JsonNode manifest(Path out) throws IOException {
        return Canonical.MAPPER.readTree(Files.readString(Path.of(out + ".manifest.json")));
    }

    static Path cacheOf(Path out) {
        return Path.of(out + ".cache.jsonl");
    }

    static Path callsOf(Path out) {
        return Path.of(out + ".calls.jsonl");
    }

    @Test
    void multiRunCommandCachesAndAnIdenticalRerunFromThatCacheMakesNoCall(@TempDir Path dir) throws Exception {
        Path out1 = dir.resolve("first.jsonl");
        Path out2 = dir.resolve("rerun.jsonl");
        int calls1;
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) {
            LlmCommands.run(shard(s.baseUrl(), out1, "runs", "4", "seed", "5"));
            calls1 = s.callCount();
            s.reset();
            LlmCommands.run(shard(s.baseUrl(), out2, "runs", "4", "seed", "5", "cache", cacheOf(out1).toString()));
            assertThat(s.callCount()).as("HTTP calls of the rerun").isZero();
        }
        List<JsonNode> a = jsonl(out1);
        List<JsonNode> b = jsonl(out2);
        assertThat(a).hasSize(4);
        Set<String> digests = new HashSet<>();
        int llmCalls = 0;
        for (int i = 0; i < 4; i++) {
            assertThat(a.get(i).get("seed").asLong()).isEqualTo(5 + i);           // --seed + i
            assertThat(a.get(i).get("llm").get("seed").asLong()).isEqualTo(5 + i);
            assertThat(a.get(i).get("pAdhere").asDouble()).isEqualTo(1.0);
            digests.add(a.get(i).get("replayDigest").asText());
            llmCalls += a.get(i).get("llmCalls").asInt();
            assertThat(a.get(i).get("llmCachedCalls").asInt()).isZero();
            // the rerun reproduces every run exactly, and knows that every call was a cache hit
            assertThat(b.get(i).get("replayDigest").asText()).isEqualTo(a.get(i).get("replayDigest").asText());
            assertThat(b.get(i).get("rounds")).isEqualTo(a.get(i).get("rounds"));
            assertThat(b.get(i).get("llmCachedCalls").asInt()).isEqualTo(b.get(i).get("llmCalls").asInt());
        }
        assertThat(digests).as("seed-sensitive digests").hasSize(4);
        assertThat(llmCalls).isEqualTo(calls1);
        // the call log has one line per call; the cache one line per distinct request; the manifest counts agree
        List<JsonNode> calls = jsonl(callsOf(out1));
        assertThat(calls).hasSize(calls1).allMatch(c -> !c.get("cached").asBoolean());
        assertThat(jsonl(callsOf(out2))).hasSize(calls1).allMatch(c -> c.get("cached").asBoolean());
        List<JsonNode> cache = jsonl(cacheOf(out1));
        assertThat(cache).hasSize(calls1);
        assertThat(cache).allMatch(c -> c.get("modelSnapshot").asText().equals("mock-model-1"));
        assertThat(Files.exists(cacheOf(out2))).as("a hit-only rerun appends nothing and creates no cache").isFalse();
        JsonNode m1 = manifest(out1).get("llm");
        JsonNode m2 = manifest(out2).get("llm");
        assertThat(m1.get("cacheMisses").asLong()).isEqualTo(calls1);
        assertThat(m1.get("cacheHits").asLong()).isZero();
        assertThat(m2.get("cacheHits").asLong()).isEqualTo(calls1);
        assertThat(m2.get("cacheMisses").asLong()).isZero();
        assertThat(m2.get("budgetUsedTokens").asLong()).as("cache hits spend nothing").isZero();
        assertThat(m1.get("baseUrlHost").asText()).isEqualTo("127.0.0.1");
        // replay from the cache alone, for both run files
        assertThat(LlmCommands.replay(o("cache", cacheOf(out1).toString(), "run", out1.toString()))).isZero();
        assertThat(LlmCommands.replay(o("cache", cacheOf(out1).toString(), "run", out2.toString()))).isZero();
    }

    @Test
    void aChangedPromptModelOrSamplingSettingNeverHitsAStaleCacheEntry(@TempDir Path dir) throws Exception {
        Path base = dir.resolve("base.jsonl");
        String cache = cacheOf(base).toString();
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) {
            LlmCommands.run(shard(s.baseUrl(), base));
            // positive control: the unchanged command, pointed at the same cache, is served entirely from it
            s.reset();
            Path same = dir.resolve("same.jsonl");
            LlmCommands.run(shard(s.baseUrl(), same, "cache", cache));
            assertThat(s.callCount()).isZero();
            assertThat(jsonl(callsOf(same))).isNotEmpty().allMatch(c -> c.get("cached").asBoolean());
            // every variant below changes the request; reusing the old cache by mistake must not serve a single entry
            String[][] variants = {
                {"condition", "label=legal"}, {"condition", "guardrail=on"}, {"condition", "notice=on"},
                {"condition", "elicitation=E2"}, {"paraphrase", "1"}, {"model", "mock-model-2"}, {"temperature", "0.3"},
                {"max-tokens", "300"}, {"scenario", "scenarios/unripe-a.yaml"}};
            int k = 0;
            for (String[] v : variants) {
                s.reset();
                Path out = dir.resolve("variant" + (k++) + ".jsonl");
                LlmCommands.run(shard(s.baseUrl(), out, "cache", cache, v[0], v[1]));
                List<JsonNode> calls = jsonl(callsOf(out));
                assertThat(calls).as(v[0] + "=" + v[1]).isNotEmpty().allMatch(c -> !c.get("cached").asBoolean());
                assertThat(s.callCount()).as(v[0] + "=" + v[1]).isEqualTo(calls.size());
                assertThat(manifest(out).get("llm").get("cacheHits").asLong()).isZero();
            }
        }
    }

    /**
     * Pins the documented hazard that the arms_distinct gate and testing/provenance_guard.py exist for: stakes is a
     * vignette-only axis (INTERFACES e.2), so a game arm that differs from the baseline only in stakes issues byte-identical
     * requests and, given the same cache, is served the baseline's replies (prototype finding F-A1).
     */
    @Test
    void aGameArmThatDiffersOnlyInStakesIssuesTheBaselinesRequests(@TempDir Path dir) throws Exception {
        Path base = dir.resolve("ripe.jsonl");
        Path stakes = dir.resolve("stakes.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) {
            LlmCommands.run(shard(s.baseUrl(), base));
            LlmCommands.run(shard(s.baseUrl(), stakes, "condition", "stakes=10", "arm", "x-stakes-10"));
        }
        Set<String> a = new HashSet<>();
        jsonl(callsOf(base)).forEach(c -> a.add(c.get("requestHash").asText()));
        Set<String> b = new HashSet<>();
        jsonl(callsOf(stakes)).forEach(c -> b.add(c.get("requestHash").asText()));
        assertThat(b).isNotEmpty().isEqualTo(a);
    }

    @Test
    void refusalPathsCompleteTheCommandAreRecordedAndReplay(@TempDir Path dir) throws Exception {
        Behaviour[] behaviours = {Behaviours.refuse(), Behaviours.declineJson()};
        int k = 0;
        for (Behaviour bh : behaviours) {
            Path out = dir.resolve("refuse" + (k++) + ".jsonl");
            try (MockLlmServer s = new MockLlmServer(bh)) {
                LlmCommands.run(shard(s.baseUrl(), out, "arm", "guardrail", "condition", "guardrail=on", "runs", "3"));
            }
            List<JsonNode> lines = jsonl(out);
            assertThat(lines).hasSize(3);
            for (JsonNode l : lines) {
                assertThat(l.get("refuser").asBoolean()).isTrue();
                // absorbing refusal (INTERFACES e.5): round 1 is REFUSED, every later round AFTER_REFUSAL with no call
                assertThat(l.get("refusedRounds").asInt()).isEqualTo(1);
                assertThat(l.get("firstRefusalRound").asInt()).isEqualTo(1);
                assertThat(l.get("llmCalls").asInt()).isEqualTo(1);
                assertThat(l.get("statRounds").asInt()).as("refused rounds never enter the statistics").isZero();
                assertThat(l.get("pAdhere").isNull()).isTrue();
                int round = 0;
                for (JsonNode r : l.get("rounds")) {
                    round++;
                    for (JsonNode ag : r.get("agents")) {
                        if (ag.get("id").asText().equals("llm")) {
                            assertThat(ag.get("phase").asText()).isEqualTo(round == 1 ? "REFUSED" : "AFTER_REFUSAL");
                        }
                    }
                }
            }
            assertThat(jsonl(callsOf(out))).isNotEmpty().allMatch(c -> c.get("parseStatus").asText().equals("REFUSED"));
            assertThat(Files.exists(Path.of(out + ".manifest.json"))).isTrue();
            assertThat(LlmCommands.replay(o("cache", cacheOf(out).toString(), "run", out.toString()))).isZero();
        }
    }

    @Test
    void concurrentShardsAreByteIdenticalToSequentialOnes(@TempDir Path dir) throws Exception {
        String[][] shards = {
            {"arm", "ripe", "paraphrase", "0"}, {"arm", "ripe", "paraphrase", "1"},
            {"arm", "label-legal", "paraphrase", "0", "condition", "label=legal"},
            {"arm", "e2", "paraphrase", "2", "condition", "elicitation=E2"}, {"arm", "unripe-a", "paraphrase", "3",
                "scenario", "scenarios/unripe-a.yaml"}};
        Files.createDirectories(dir.resolve("seq"));
        Files.createDirectories(dir.resolve("par"));
        // a reply that depends only on the request (never on arrival order), so concurrency cannot change any answer
        Behaviour byRequest = r -> r.user().contains("|r1|") ? Behaviours.decisionJson(SP, "hold") :
                Behaviours.decisionJson(r.user().hashCode() % 3 == 0 ? SP - 0.10 : SP, "react");
        try (MockLlmServer s = new MockLlmServer(byRequest)) {
            for (int i = 0; i < shards.length; i++) {
                LlmCommands.run(shard(s.baseUrl(), dir.resolve("seq/s" + i + ".jsonl"), with(shards[i], "runs", "3")));
            }
        }
        try (MockLlmServer s = new MockLlmServer(byRequest)) {
            ExecutorService ex = Executors.newFixedThreadPool(shards.length);
            List<Future<?>> fs = new ArrayList<>();
            for (int i = 0; i < shards.length; i++) {
                int j = i;
                fs.add(ex.submit(() -> {
                    LlmCommands.run(shard(s.baseUrl(), dir.resolve("par/s" + j + ".jsonl"), with(shards[j], "runs", "3")));
                    return null;
                }));
            }
            for (Future<?> f : fs) {
                f.get();
            }
            ex.shutdown();
        }
        for (int i = 0; i < shards.length; i++) {
            Path a = dir.resolve("seq/s" + i + ".jsonl");
            Path b = dir.resolve("par/s" + i + ".jsonl");
            assertThat(Files.readString(b)).as("run lines " + i).isEqualTo(Files.readString(a));
            assertThat(Files.readString(cacheOf(b))).as("cache " + i).isEqualTo(Files.readString(cacheOf(a)));
            assertThat(withoutLatency(jsonl(callsOf(b)))).as("calls " + i).isEqualTo(withoutLatency(jsonl(callsOf(a))));
            assertThat(manifest(b).get("llm")).as("manifest llm " + i).isEqualTo(manifest(a).get("llm"));
            assertThat(LlmCommands.replay(o("cache", cacheOf(b).toString(), "run", b.toString()))).isZero();
        }
    }

    static String[] with(String[] kv, String... more) {
        String[] out = new String[kv.length + more.length];
        System.arraycopy(kv, 0, out, 0, kv.length);
        System.arraycopy(more, 0, out, kv.length, more.length);
        return out;
    }

    static List<JsonNode> withoutLatency(List<JsonNode> calls) {
        for (JsonNode c : calls) {
            ((ObjectNode) c).remove("latencyMs");
        }
        return calls;
    }

    @Test
    void replayFailsLoudlyWhenTheRecordedParametersDoNotMatchTheCache(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("r.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) {
            LlmCommands.run(shard(s.baseUrl(), out, "runs", "1"));
        }
        String cache = cacheOf(out).toString();
        JsonNode line = jsonl(out).get(0);
        assertThat(LlmCommands.replay(o("cache", cache, "run", out.toString()))).isZero();
        Object[][] mutations = {{"paraphrase", 1}, {"condition", "elicitation=SPONTANEOUS,guardrail=off,label=LEGAL,notice=off,stakes=1"},
            {"model", "another-model"}, {"provider", "vllm-local"}, {"temperature", 0.3}, {"maxTokens", 300},
            {"scenario", "scenarios/unripe-a.yaml"}};
        int k = 0;
        for (Object[] m : mutations) {
            ObjectNode copy = line.deepCopy();
            ObjectNode llm = (ObjectNode) copy.get("llm");
            if (m[1] instanceof Integer i) {
                llm.put((String) m[0], i);
            } else if (m[1] instanceof Double d) {
                llm.put((String) m[0], d);
            } else {
                llm.put((String) m[0], (String) m[1]);
            }
            Path f = dir.resolve("mut" + (k++) + ".jsonl");
            Files.writeString(f, Canonical.text(copy) + "\n");
            assertThat(LlmCommands.replay(o("cache", cache, "run", f.toString()))).as("replay with llm." + m[0] + " changed")
                    .isEqualTo(1);
        }
    }
}
