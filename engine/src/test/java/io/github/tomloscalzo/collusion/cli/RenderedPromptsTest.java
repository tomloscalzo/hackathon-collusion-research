package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.RenderedPromptsClient;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * U4: every run keeps its rendered prompts. Track S shards write {@code <out>.prompts.ndjson} (system prompt and every user
 * message as sent, with SHA-256); it is a pure side output (same requests, cache keys, call records, digest). Track M
 * already logs the full prompt of every call in events.jsonl: checked here against the same requests.
 */
class RenderedPromptsTest {
    private static List<JsonNode> read(Path p) throws Exception {
        List<JsonNode> out = new ArrayList<>();
        for (String l : Files.readAllLines(p, StandardCharsets.UTF_8)) {
            out.add(Canonical.MAPPER.readTree(l));
        }
        return out;
    }

    private static LlmRequest req(String system, String user, String drawKey) {
        return new LlmRequest("p", "m", system, List.of(new LlmRequest.Turn("user", user)), 0.7, 100, null, drawKey);
    }

    private static final LlmResponse RESP = new LlmResponse("hi", 1, 2, 3L, false, "h", "stop", null, null);

    @Test
    void wrapperForwardsTheSameRequestAndReturnsTheSameResponse(@TempDir Path dir) {
        List<LlmRequest> seen = new ArrayList<>();
        LlmClient inner = r -> {
            seen.add(r);
            return RESP;
        };
        RenderedPromptsClient c = new RenderedPromptsClient(inner, dir.resolve("p.jsonl"));
        LlmRequest r1 = req("sys é", "u1", "k1");
        assertThat(c.complete(r1)).isSameAs(RESP);
        assertThat(seen).hasSize(1);
        assertThat(seen.get(0)).isSameAs(r1);
    }

    @Test
    void writesSystemAndEveryUserMessageWithSha256AndDedupesByHash(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("p.jsonl");
        LlmRequest two = new LlmRequest("p", "m", "SYS", List.of(new LlmRequest.Turn("user", "U1"),
                new LlmRequest.Turn("assistant", "A1"), new LlmRequest.Turn("user", "U2")), 0.7, 100, null, "k", null, null,
                null);
        RenderedPromptsClient c = new RenderedPromptsClient(r -> RESP, f);
        c.complete(two);
        c.complete(two);
        c.complete(req("SYS", "other", "k2"));
        List<JsonNode> lines = read(f);
        assertThat(lines).hasSize(2);
        JsonNode n = lines.get(0);
        assertThat(n.get("hash").asText()).isEqualTo(CanonicalRequest.sha256(two));
        assertThat(n.get("system").asText()).isEqualTo("SYS");
        assertThat(n.get("systemSha256").asText()).isEqualTo(Canonical.sha256("SYS"));
        assertThat(n.get("turns")).hasSize(3);
        assertThat(n.get("turns").get(2).get("content").asText()).isEqualTo("U2");
        assertThat(n.get("turns").get(2).get("role").asText()).isEqualTo("user");
        assertThat(n.get("turns").get(2).get("sha256").asText()).isEqualTo(Canonical.sha256("U2"));
        // a rerun on the same file adds nothing
        new RenderedPromptsClient(r -> RESP, f).complete(two);
        assertThat(read(f)).hasSize(2);
    }

    @Test
    void aWriteFailureNeverReachesTheGame(@TempDir Path dir) throws Exception {
        Path asDir = dir.resolve("p.jsonl");
        Files.createDirectories(asDir); // cannot be opened as a file
        RenderedPromptsClient c = new RenderedPromptsClient(r -> RESP, asDir);
        assertThat(c.complete(req("s", "u", "k"))).isSameAs(RESP);
        assertThat(c.error()).isNotNull();
    }

    @Test
    void trackSRunWritesOneLinePerDistinctCallMatchingTheWireCacheAndCallLog(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("runs.jsonl");
        List<String> wire = new ArrayList<>();
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            LlmCommands.run(LlmCliTest.o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model",
                    "mock-model-1", "seed", "11", "runs", "2", "out", out.toString(), "paraphrase", "4", "condition",
                    "elicitation=E1,notice=on", "arm", "e1-notice", "analysis-script", "../tools/analysis.py"));
            s.requests().forEach(q -> wire.add(q.rawBody()));
        }
        List<JsonNode> prompts = read(Path.of(out + ".prompts.ndjson"));
        Set<String> promptHashes = new TreeSet<>();
        prompts.forEach(p -> promptHashes.add(p.get("hash").asText()));
        assertThat(promptHashes).hasSize(prompts.size());
        // same keys as the cache and the call log: nothing about the requests changed
        Set<String> cacheHashes = new TreeSet<>();
        read(Path.of(out + ".cache.jsonl")).forEach(c -> cacheHashes.add(c.get("hash").asText()));
        Set<String> callHashes = new TreeSet<>();
        read(Path.of(out + ".calls.jsonl")).forEach(c -> callHashes.add(c.get("requestHash").asText()));
        assertThat(promptHashes).isEqualTo(cacheHashes).isEqualTo(callHashes);
        // the text is what the server received: every system and user message of the file is in some wire body
        for (JsonNode p : prompts) {
            String sys = p.get("system").asText();
            assertThat(sys).isNotBlank();
            assertThat(p.get("systemSha256").asText()).isEqualTo(Canonical.sha256(sys));
            assertThat(p.get("turns").size()).isGreaterThanOrEqualTo(1);
            boolean found = false;
            for (String w : wire) {
                JsonNode msgs = Canonical.MAPPER.readTree(w).get("messages");
                if (msgs.get(0).get("content").asText().equals(sys) && msgs.size() == p.get("turns").size() + 1) {
                    boolean same = true;
                    for (int i = 0; i < p.get("turns").size(); i++) {
                        JsonNode t = p.get("turns").get(i);
                        same &= msgs.get(i + 1).get("content").asText().equals(t.get("content").asText())
                                && Canonical.sha256(t.get("content").asText()).equals(t.get("sha256").asText());
                    }
                    found |= same;
                }
            }
            assertThat(found).as("prompt of %s was sent as is", p.get("drawKey").asText()).isTrue();
        }
        // the digest still replays from the cache alone (no prompts file needed)
        assertThat(LlmCommands.replay(LlmCliTest.o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
    }

    @Test
    void aRerunFromTheCacheKeepsTheSamePromptsWithoutDuplicates(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("runs.jsonl");
        Set<String> first = null;
        for (int i = 0; i < 2; i++) {
            try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
                LlmCommands.run(LlmCliTest.o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", s.baseUrl(),
                        "model", "mock-model-1", "seed", "11", "out", out.toString(), "analysis-script", "../tools/analysis.py"));
                if (i == 1) {
                    assertThat(s.requests()).as("second run is served by the cache").isEmpty();
                }
            }
            List<JsonNode> lines = read(Path.of(out + ".prompts.ndjson"));
            Set<String> hashes = new TreeSet<>();
            lines.forEach(l -> hashes.add(l.get("hash").asText()));
            assertThat(hashes).hasSize(lines.size());
            if (first == null) {
                first = hashes;
            } else {
                assertThat(hashes).isEqualTo(first);
            }
        }
    }

    @Test
    void theSideOutputChangesNothing(@TempDir Path dir) throws Exception {
        // two identical runs, the second with --prompts naming a directory (the side output cannot be written): same run
        // line, wire bodies and cache
        Map<String, List<String>> res = new LinkedHashMap<>();
        for (String name : List.of("ok", "broken")) {
            Path d = dir.resolve(name);
            Files.createDirectories(d);
            Path out = d.resolve("runs.jsonl");
            Path prompts = name.equals("ok") ? d.resolve("x.prompts.ndjson") : d;
            List<String> all = new ArrayList<>();
            try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
                LlmCommands.run(LlmCliTest.o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", s.baseUrl(),
                        "model", "mock-model-1", "seed", "11", "out", out.toString(), "prompts", prompts.toString(),
                        "analysis-script", "../tools/analysis.py"));
                s.requests().forEach(q -> all.add(q.rawBody()));
            }
            all.add(Files.readString(out));
            all.addAll(Files.readAllLines(Path.of(out + ".cache.jsonl")));
            res.put(name, all);
        }
        assertThat(Files.exists(dir.resolve("ok/x.prompts.ndjson"))).isTrue();
        assertThat(res.get("broken")).isEqualTo(res.get("ok"));
    }

    @Test
    void trackMEventsHoldTheFullPromptOfEveryCall(@TempDir Path dir) throws Exception {
        long seed = TrialDirCliTest.longSeed(dir);
        // untouched run, no trial dir: the rendered-prompts file; the same game with a trial dir: events.jsonl
        TrialDirCliTest.Played plain = TrialDirCliTest.play(dir.resolve("a"), seed);
        Path trial = dir.resolve("b/trial");
        TrialDirCliTest.Played logged = TrialDirCliTest.play(dir.resolve("b"), seed, "trial-dir", trial.toString());
        assertThat(logged.line()).isEqualTo(plain.line());
        assertThat(Files.exists(Path.of(dir.resolve("b/m.jsonl") + ".prompts.ndjson")))
                .as("Track M keeps its prompts in events.jsonl only").isFalse();
        Map<String, String> promptByHash = new LinkedHashMap<>();
        for (JsonNode p : read(Path.of(dir.resolve("a/m.jsonl") + ".prompts.ndjson"))) {
            StringBuilder sb = new StringBuilder("[system]\n").append(p.get("system").asText());
            for (JsonNode t : p.get("turns")) {
                sb.append("\n\n[").append(t.get("role").asText()).append("]\n").append(t.get("content").asText());
            }
            promptByHash.put(p.get("hash").asText(), sb.toString());
        }
        int checked = 0;
        for (JsonNode e : TrialDirCliTest.events(trial)) {
            if (e.has("request_hash")) {
                assertThat(e.get("prompt").asText()).as("event %s", e.get("seq"))
                        .isEqualTo(promptByHash.get(e.get("request_hash").asText()));
                checked++;
            }
        }
        assertThat(checked).isEqualTo(plain.callHashes().size());
        assertThat(promptByHash.keySet()).containsExactlyInAnyOrderElementsOf(new TreeSet<>(plain.callHashes()));
    }
}
