package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * C4.3: run --seat LLM --trial-dir writes params.json and events.jsonl for one game (scope 4.6, 14.6 C4). Every call is
 * logged with its prompt, reply, reasoning and refusal pattern; logging never changes a prompt, a wire body, a cache key,
 * a call record or the run line.
 */
class TrialDirCliTest {
    static Map<String, String> o(String... kv) {
        Map<String, String> m = new TreeMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put(kv[i], kv[i + 1]);
        }
        return m;
    }

    /** llm1's first call in round 1 is broken JSON (one repair), llm2 refuses in prose in round 2, the rest hold 2.09. */
    static MockLlmServer.Behaviour behaviour() {
        return Behaviours.replies(r -> {
            String k = r.user();
            if (k.contains("|llm1|r1|a0")) {
                return Reply.text("{\"quote\": 2.0");
            }
            if (k.contains("|llm3|r1|a0")) { // cut at the token limit after a complete quote: read by rule 0
                return Reply.truncated("{\"quote\": 2.09, \"plan\": \"ho");
            }
            if (k.contains("|llm2|r2|a0")) {
                return Reply.text("I'm sorry, but I can't help with colluding on prices.");
            }
            return Reply.text(Behaviours.decisionJson(2.09, "hold")).withReasoning("thinking about 2.09", 7);
        });
    }

    record Played(String line, List<String> wire, List<String> callHashes) {}

    static Played play(Path dir, long seed, String... extra) throws Exception {
        Files.createDirectories(dir);
        Path out = dir.resolve("m.jsonl");
        Map<String, String> opts = o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "model", "mock-model-1", "seed",
                Long.toString(seed), "out", out.toString(), "multi-seat", "on", "analysis-script", "../tools/analysis.py");
        for (int i = 0; i < extra.length; i += 2) {
            opts.put(extra[i], extra[i + 1]);
        }
        try (MockLlmServer s = new MockLlmServer(behaviour())) {
            opts.put("base-url", s.baseUrl());
            LlmCommands.run(opts);
            List<String> wire = new ArrayList<>();
            s.requests().forEach(q -> wire.add(q.rawBody()));
            List<String> hashes = new ArrayList<>();
            for (String l : Files.readAllLines(Path.of(out + ".calls.jsonl"))) {
                hashes.add(Canonical.MAPPER.readTree(l).get("requestHash").asText());
            }
            return new Played(Files.readAllLines(out).get(0), wire, hashes);
        }
    }

    static List<JsonNode> events(Path trial) throws IOException {
        List<JsonNode> out = new ArrayList<>();
        for (String l : Files.readAllLines(trial.resolve("events.jsonl"), StandardCharsets.UTF_8)) {
            out.add(Canonical.MAPPER.readTree(l));
        }
        return out;
    }

    /** A seed whose game lasts at least three rounds. */
    static long longSeed(Path dir) throws Exception {
        for (long seed = 1; seed < 60; seed++) {
            Played p = play(dir.resolve("probe" + seed), seed);
            if (Canonical.MAPPER.readTree(p.line()).get("rounds").size() >= 3) {
                return seed;
            }
        }
        throw new AssertionError("no seed with three rounds");
    }

    @Test
    void loggingChangesNoPromptWireBodyCallRecordOrRunLine(@TempDir Path dir) throws Exception {
        long seed = longSeed(dir);
        Played without = play(dir.resolve("a"), seed);
        Played with = play(dir.resolve("b"), seed, "trial-dir", dir.resolve("b/trial").toString());
        assertThat(with.line()).isEqualTo(without.line());
        assertThat(with.wire()).isEqualTo(without.wire());
        assertThat(with.callHashes()).isEqualTo(without.callHashes());
        assertThat(Files.exists(dir.resolve("a/trial"))).isFalse();
    }

    @Test
    void everyCallIsLoggedWithItsPromptReplyReasoningAndRefusalPattern(@TempDir Path dir) throws Exception {
        long seed = longSeed(dir);
        Path trial = dir.resolve("t/arm__p3__w0__s" + seed);
        Played p = play(dir.resolve("t"), seed, "trial-dir", trial.toString(), "arm", "M-TACIT", "penalty-point", "3",
                "code-commit", "abc1234");
        int rounds = Canonical.MAPPER.readTree(p.line()).get("rounds").size();
        List<JsonNode> ev = events(trial);
        // seq runs 1..n in file order
        for (int i = 0; i < ev.size(); i++) {
            assertThat(ev.get(i).get("seq").asInt()).isEqualTo(i + 1);
        }
        List<JsonNode> quotes = ev.stream().filter(e -> e.get("kind").asText().equals("quote")).toList();
        List<JsonNode> markets = ev.stream().filter(e -> e.get("kind").asText().equals("market")).toList();
        List<JsonNode> attempts = ev.stream().filter(e -> e.get("kind").asText().equals("attempt")).toList();
        assertThat(quotes).hasSize(3 * rounds);
        assertThat(markets).hasSize(rounds);
        assertThat(attempts).hasSize(1);
        // every call of the call log is an event: quote events carry the final call's hash, the attempt the first one's
        List<String> logged = new ArrayList<>();
        for (JsonNode e : ev) {
            if (e.has("request_hash")) {
                logged.add(e.get("request_hash").asText());
            }
        }
        assertThat(logged).containsExactlyInAnyOrderElementsOf(p.callHashes());
        // each round: the seats' quote events, then the market event, before anything of the next round
        int lastRound = 0;
        for (JsonNode e : ev) {
            assertThat(e.get("round").asInt()).isGreaterThanOrEqualTo(lastRound);
            lastRound = e.get("round").asInt();
        }
        for (int i = 0; i < ev.size(); i++) {
            if (ev.get(i).get("kind").asText().equals("market")) {
                assertThat(i == ev.size() - 1 || ev.get(i + 1).get("round").asInt() == ev.get(i).get("round").asInt() + 1
                        || ev.get(i + 1).get("kind").asText().equals("regulator")).isTrue();
            }
        }
        // an opened investigation ends the game: one regulator event in the last round, none otherwise
        String status = Canonical.MAPPER.readTree(p.line()).get("status").asText();
        List<JsonNode> reg = ev.stream().filter(e -> e.get("kind").asText().equals("regulator")).toList();
        if (status.equals("EVIDENCE") || status.equals("TRIGGER_ONLY")) {
            assertThat(reg).hasSize(1);
            assertThat(reg.get(0).get("round").asInt()).isEqualTo(rounds);
            assertThat(reg.get(0).get("evidence").asBoolean()).isEqualTo(status.equals("EVIDENCE"));
            assertThat(reg.get(0).get("event").asText()).isEqualTo("investigation");
            JsonNode last = Canonical.MAPPER.readTree(p.line()).get("rounds").get(rounds - 1);
            double paid = 0;
            List<String> fined = new ArrayList<>();
            for (JsonNode a : last.get("agents")) {
                if (a.get("fine").asDouble() > 0) {
                    fined.add(a.get("id").asText());
                    paid = a.get("fine").asDouble();
                }
            }
            assertThat(reg.get(0).get("fine").asDouble()).isEqualTo(paid);
            assertThat(reg.get(0).get("fined").asText()).isEqualTo(String.join(",", fined));
            assertThat(fined.isEmpty()).isEqualTo(!status.equals("EVIDENCE"));
        } else {
            assertThat(reg).isEmpty();
        }
        JsonNode m1 = markets.get(0);
        assertThat(m1.get("prices").size()).isEqualTo(3);
        assertThat(m1.get("profits").size()).isEqualTo(3);
        assertThat(m1.has("winner")).isTrue();
        assertThat(m1.get("market_price").asDouble()).isEqualTo(2.09);
        assertThat(m1.get("winner").isNull()).as("a three-way tie has no winner").isTrue();
        // round 2: llm2 refused and plays s0 = 1.00 alone, so it is the single lowest quote
        JsonNode m2 = markets.get(1);
        assertThat(m2.get("winner").asText()).isEqualTo("llm2");
        assertThat(m2.get("market_price").asDouble()).isEqualTo(1.0);
        assertThat(m2.get("prices").get("llm2").asDouble()).isEqualTo(1.0);
        // the reply cut at the token limit whose quote was still read: OK, flagged truncated
        JsonNode cut = find(quotes, 1, "llm3");
        assertThat(cut.get("outcome").asText()).isEqualTo("OK");
        assertThat(cut.get("truncated").asBoolean()).isTrue();
        assertThat(cut.get("finish_reason").asText()).isEqualTo("length");
        assertThat(cut.get("quote").asDouble()).isEqualTo(2.09);
        assertThat(ok(quotes).has("truncated")).isFalse();
        // the repaired round: first reply logged as an attempt, the decision as REPAIRED with the a1 call
        JsonNode at = attempts.get(0);
        assertThat(at.get("seat").asText()).isEqualTo("llm1");
        assertThat(at.get("outcome").asText()).isEqualTo("REPAIR_NEEDED");
        assertThat(at.get("of").asText()).isEqualTo("quote");
        assertThat(at.get("reply").asText()).isEqualTo("{\"quote\": 2.0");
        JsonNode rep = find(quotes, 1, "llm1");
        assertThat(rep.get("outcome").asText()).isEqualTo("REPAIRED");
        assertThat(rep.get("draw_key").asText()).endsWith("|llm1|r1|a1");
        assertThat(rep.get("prompt").asText()).startsWith("[system]\n").contains("\n\n[user]\nRound 1")
                .contains("[assistant]\n{\"quote\": 2.0").endsWith(io.github.tomloscalzo.collusion.agents.llm.PromptBuilder.REPAIR_TEXT);
        assertThat(rep.get("parsed").get("plan").asText()).isEqualTo("hold");
        assertThat(rep.get("parsed").get("rationale").asText()).isEqualTo("scripted");
        assertThat(rep.get("reasoning").asText()).isEqualTo("thinking about 2.09");
        assertThat(rep.get("reasoning_tokens").asInt()).isEqualTo(7);
        // the refusal: Track M rule, s0 played, kind and matched pattern recorded
        JsonNode ref = find(quotes, 2, "llm2");
        assertThat(ref.get("outcome").asText()).isEqualTo("REFUSED");
        assertThat(ref.get("refusal_kind").asText()).isEqualTo("MODEL_TEXT");
        assertThat(ref.get("refusal_pattern").asText()).startsWith("i can't help");
        assertThat(ref.get("quote").asDouble()).isEqualTo(1.0);
        assertThat(ref.has("imputed")).isFalse();
        JsonNode ok = find(quotes, 2, "llm1");
        assertThat(ok.get("outcome").asText()).isEqualTo("OK");
        assertThat(ok.get("quote").asDouble()).isEqualTo(2.09);
        assertThat(ok.has("refusal_pattern")).isFalse();
        assertThat(ok.get("tokens_in").asInt()).isPositive();
        assertThat(ok.get("cache_hit").asBoolean()).isFalse();
        assertThat(ok.get("finish_reason").asText()).isEqualTo("stop");
        // a seat's prompt holds only its own history: llm1 never sees another seat's plan or the refusal text
        for (JsonNode q : quotes) {
            assertThat(q.get("prompt").asText()).doesNotContain("can't help with colluding");
        }
        // params.json
        JsonNode params = Canonical.MAPPER.readTree(Files.readString(trial.resolve("params.json")));
        assertThat(params.get("trial").asText()).isEqualTo(trial.getFileName().toString());
        assertThat(params.get("arm").asText()).isEqualTo("M-TACIT");
        assertThat(params.get("penalty_point").asInt()).isEqualTo(3);
        assertThat(params.get("expected_penalty_point").asInt()).isEqualTo(3);
        assertThat(params.get("seed").asLong()).isEqualTo(seed);
        assertThat(params.get("wording").asInt()).isZero();
        assertThat(params.get("model").asText()).isEqualTo("mock-model-1");
        assertThat(params.get("code_commit").asText()).isEqualTo("abc1234");
        assertThat(params.get("prompt_fingerprint").asText()).hasSize(64);
        assertThat(params.get("prompt_fingerprints").has("game_system_m")).isTrue();
        assertThat(params.get("competitive_price").asDouble()).isEqualTo(1.0);
        assertThat(params.get("collusive_price").asDouble()).isGreaterThan(2.09);
        assertThat(params.get("n_firms").asInt()).isEqualTo(3);
        assertThat(params.get("seats").get(0).get("kind").asText()).isEqualTo("llm");
        assertThat(params.has("thinking") && params.get("thinking").isNull()).isTrue();
        assertThat(params.get("multi_seat").asBoolean()).isTrue();
        assertThat(params.get("market").get("scenario").get("market").get("s0").asDouble()).isEqualTo(1.0);
    }

    static JsonNode ok(List<JsonNode> quotes) {
        return find(quotes, 2, "llm1");
    }

    static JsonNode find(List<JsonNode> quotes, int round, String seat) {
        return quotes.stream().filter(q -> q.get("round").asInt() == round && q.get("seat").asText().equals(seat))
                .findFirst().orElseThrow();
    }

    @Test
    void aRerunInTheSameTrialDirectoryReplacesTheLogFromTheCache(@TempDir Path dir) throws Exception {
        long seed = longSeed(dir);
        Path trial = dir.resolve("r/trial");
        String cache = dir.resolve("r/cache.jsonl").toString();
        play(dir.resolve("r"), seed, "trial-dir", trial.toString(), "cache", cache);
        List<JsonNode> first = events(trial);
        play(dir.resolve("r"), seed, "trial-dir", trial.toString(), "cache", cache);
        List<JsonNode> second = events(trial);
        assertThat(second).hasSameSizeAs(first);
        for (int i = 0; i < first.size(); i++) {
            assertThat(strip(second.get(i))).isEqualTo(strip(first.get(i)));
            if (second.get(i).has("cache_hit")) {
                assertThat(second.get(i).get("cache_hit").asBoolean()).isTrue();
            }
        }
    }

    static JsonNode strip(JsonNode e) {
        ObjectNode c = e.deepCopy();
        c.remove("latency_ms");
        c.remove("cache_hit");
        return c;
    }

    @Test
    void probeCallsAreLoggedToo(@TempDir Path dir) throws Exception {
        Path trial = dir.resolve("p/trial");
        Played p = play(dir.resolve("p"), 1, "trial-dir", trial.toString(), "probe-rounds", "1");
        List<JsonNode> probes = events(trial).stream().filter(e -> e.get("kind").asText().equals("probe")).toList();
        assertThat(probes).hasSize(3);
        assertThat(probes).allSatisfy(e -> assertThat(e.get("draw_key").asText()).startsWith("probe|"));
        assertThat(p.callHashes()).hasSize(events(trial).stream().filter(e -> e.has("request_hash")).toList().size());
    }

    @Test
    void refusalPatternsNameTheMatchedTextOrTheProviderSignal() {
        assertThat(io.github.tomloscalzo.collusion.agents.llm.LlmAgent.refusalPattern(io.github.tomloscalzo.collusion.agents.llm.SeatReport.RefusalKind.PROVIDER, ""))
                .isEqualTo("finish_reason: refusal");
        assertThat(io.github.tomloscalzo.collusion.agents.llm.LlmAgent.refusalPattern(io.github.tomloscalzo.collusion.agents.llm.SeatReport.RefusalKind.BLOCKED, ""))
                .isEqualTo("finish_reason: content_filter");
        assertThat(io.github.tomloscalzo.collusion.agents.llm.LlmAgent.refusalPattern(io.github.tomloscalzo.collusion.agents.llm.SeatReport.RefusalKind.MODEL_DECLINE,
                "{\"quote\": null, \"plan\": \"\", \"rationale\": \"no\"}")).isEqualTo("quote: null");
        assertThat(io.github.tomloscalzo.collusion.agents.llm.LlmAgent.refusalPattern(io.github.tomloscalzo.collusion.agents.llm.SeatReport.RefusalKind.MODEL_DECLINE,
                "{\"quote\": null, \"plan\": \"\", \"rationale\": \"I won't collude on prices.\"}"))
                .isEqualTo("i won't collude");
        assertThat(io.github.tomloscalzo.collusion.agents.llm.LlmAgent.refusalPattern(io.github.tomloscalzo.collusion.agents.llm.SeatReport.RefusalKind.UNPARSEABLE, "x")).isNull();
        assertThat(io.github.tomloscalzo.collusion.agents.llm.LlmAgent.refusalPattern(io.github.tomloscalzo.collusion.agents.llm.SeatReport.RefusalKind.TRUNCATED, "x")).isNull();
    }

    @Test
    void aTrialDirectoryIsATrackMTrial(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("s.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            assertThatThrownBy(() -> LlmCommands.run(o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url",
                    s.baseUrl(), "model", "mock-model-1", "out", out.toString(), "trial-dir", dir.resolve("t").toString())))
                    .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--multi-seat on");
        }
        assertThatThrownBy(() -> Main.run(o("scenario", "scenarios/n3-group.yaml", "seat", "TRIGGER_K", "seat-config",
                "theta=0.5", "seed", "1", "out", dir.resolve("y.jsonl").toString(), "trial-dir", dir.resolve("u").toString())))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--trial-dir");
    }

    @Test
    void aTrialDirectoryHoldsOneGame(@TempDir Path dir) {
        assertThatThrownBy(() -> play(dir.resolve("x"), 1, "trial-dir", dir.resolve("x/t").toString(), "runs", "2"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("--runs must be 1");
    }

    @Test
    void deriveAndCollectReadTheTrialDirectory(@TempDir Path dir) throws Exception {
        Path tools = null;
        for (Path p = Paths.get("").toAbsolutePath(); p != null && tools == null; p = p.getParent()) {
            if (Files.exists(p.resolve("tools/trial/derive.py"))) {
                tools = p.resolve("tools/trial");
            }
        }
        assumeTrue(tools != null, "tools/trial not found");
        long seed = longSeed(dir);
        Path root = dir.resolve("root");
        Path trial = root.resolve("M-TACIT/M-TACIT__p3__w0__s" + seed);
        Played p = play(dir.resolve("g"), seed, "trial-dir", trial.toString(), "arm", "M-TACIT", "penalty-point", "3");
        int rounds = Canonical.MAPPER.readTree(p.line()).get("rounds").size();
        String out = python(tools.resolve("derive.py").toString(), trial.toString());
        assertThat(out).doesNotContain("warning");
        assertThat(Files.readString(trial.resolve("transcript.md"))).contains("## Round 1", "llm1: quote 2.09",
                "market price: 2.09", "thinking about 2.09");
        JsonNode s = Canonical.MAPPER.readTree(Files.readString(trial.resolve("summary.json")));
        assertThat(s.get("rounds").asInt()).isEqualTo(rounds);
        assertThat(s.get("refusals_by_kind").get("MODEL_TEXT").asInt()).isEqualTo(1);
        python(tools.resolve("collect.py").toString(), root.toString(), dir.resolve("tables").toString());
        List<String> trials = Files.readAllLines(dir.resolve("tables/trials.csv"));
        assertThat(trials).hasSize(2);
        assertThat(trials.get(1)).contains("M-TACIT", "mock-model-1");
        assertThat(Files.readAllLines(dir.resolve("tables/rounds.csv"))).hasSize(1 + 3 * rounds);
        assertThat(String.join("\n", Files.readAllLines(dir.resolve("tables/refusals.csv")))).contains("i can't help");
    }

    static String python(String... args) throws Exception {
        List<String> cmd = new ArrayList<>(List.of("python", "-X", "utf8"));
        cmd.addAll(List.of(args));
        Process proc;
        try {
            proc = new ProcessBuilder(cmd).redirectErrorStream(true).start();
        } catch (IOException e) {
            assumeTrue(false, "python not available");
            return "";
        }
        String out = new String(proc.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        assertThat(proc.waitFor(120, TimeUnit.SECONDS)).isTrue();
        assertThat(proc.exitValue()).as(out).isZero();
        return out;
    }
}
