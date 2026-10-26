package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.agents.llm.CallSettingsMap;
import io.github.tomloscalzo.collusion.agents.llm.LlmSettings;
import io.github.tomloscalzo.collusion.agents.llm.PromptBuilder;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.MockRequest;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * C12b.2 (scope 14.6 C12b, proposal E1, B2): the per-call settings map wired. Each call type's max tokens, schema and
 * sampling reach its requests; a map that only restates the run's settings changes nothing; params.json and the run line
 * record it and replay rebuilds it; Track S quote calls take it too (the probe keeps the run's settings). R1: its
 * instruction is in R1 quote calls only, the reply format is unchanged, and no reasoning reaches any prompt.
 */
class CallSettingsWiredTest {
    static final String R1 = "Before you reply, think privately about what decisions you are making and why.";
    static final String CANARY = "REASONING-CANARY-";

    /** Talk: one message then done; quotes 2.09; seat llm2's round-2 quote is malformed once (a repair turn). */
    static Reply reply(MockRequest r) {
        String seat = r.user().split("\\|")[3];
        String text;
        if (r.user().startsWith("talk|")) {
            text = r.lastUser().contains("You have sent 0 of") ? "{\"message\": \"Hold 2.09?\", \"done\": false}"
                    : "{\"message\": \"\", \"done\": true}";
        } else if (r.user().endsWith("|llm2|r2|a0")) {
            text = "{\"quote\": 2.09, \"plan\": ";
        } else {
            text = "{\"quote\": 2.09, \"plan\": \"hold\", \"rationale\": \"why\"}";
        }
        if (r.rawBody().contains("\"enable_thinking\":false")) { // thinking off: no reasoning, as the server does
            return Reply.text(text);
        }
        return Reply.text(text).withReasoning(CANARY + seat + "-" + r.callIndex(), 7);
    }

    record Run(List<MockRequest> requests, Path out, Path trial) {}

    static Run run(Path dir, String name, String scenario, boolean multi, String... extra) throws Exception {
        Path out = dir.resolve(name + ".jsonl");
        Path trial = dir.resolve(name);
        List<String> kv = new ArrayList<>(List.of("scenario", scenario, "seat", "LLM", "model", "mock-model-1", "seed", "2",
                "out", out.toString(), "analysis-script", "../tools/analysis.py"));
        if (multi) {
            kv.addAll(List.of("multi-seat", "on", "talk", "on", "trial-dir", trial.toString(), "code-commit", "abc1234"));
        }
        kv.addAll(List.of(extra));
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(CallSettingsWiredTest::reply))) {
            kv.addAll(List.of("base-url", s.baseUrl()));
            LlmCommands.run(TrialDirCliTest.o(kv.toArray(String[]::new)));
            return new Run(s.requests(), out, trial);
        }
    }

    static JsonNode p0(Run r) throws Exception {
        return Canonical.MAPPER.readTree(Files.readString(r.trial().resolve("params.json")));
    }

    static JsonNode body(MockRequest r) throws Exception {
        return Canonical.MAPPER.readTree(r.rawBody());
    }

    @Test
    void eachCallTypeGetsItsOwnTokensSchemaAndSampling(@TempDir Path dir) throws Exception {
        String map = "{\"thinking\":true,\"temperature\":0.6,\"top_p\":0.95,\"top_k\":20,\"calls\":{"
                + "\"talk\":{\"max_tokens\":1024,\"timeout_sec\":140,\"temperature\":0.7,\"top_p\":0.8},"
                + "\"quote\":{\"max_tokens\":2560,\"timeout_sec\":140},"
                + "\"question\":{\"max_tokens\":2048,\"timeout_sec\":140}}}";
        Run r = run(dir, "m", "scenarios/n3-group.yaml", true, "call-settings", map);
        int talk = 0;
        int quote = 0;
        for (MockRequest q : r.requests()) {
            JsonNode b = body(q);
            boolean t = q.user().startsWith("talk|");
            talk += t ? 1 : 0;
            quote += t ? 0 : 1;
            assertThat(b.get("max_tokens").asInt()).as(q.user()).isEqualTo(t ? 1024 : 2560);
            assertThat(b.get("temperature").asDouble()).isEqualTo(t ? 0.7 : 0.6);
            assertThat(b.get("top_p").asDouble()).isEqualTo(t ? 0.8 : 0.95);
            assertThat(b.get("top_k").asInt()).isEqualTo(20);
            assertThat(b.get("chat_template_kwargs").get("enable_thinking").asBoolean()).isTrue();
            assertThat(b.get("response_format").get("json_schema").get("name").asText()).isEqualTo(t ? "talk" : "decision");
            assertThat(b.get("response_format").get("json_schema").get("schema")).isEqualTo(Canonical.MAPPER.readTree(
                    t ? io.github.tomloscalzo.collusion.agents.llm.TalkParser.TALK_SCHEMA : PromptBuilder.DECISION_SCHEMA));
        }
        assertThat(p0(r).get("sampling").get("temperature").asDouble()).isEqualTo(0.6);
        assertThat(p0(r).get("sampling").get("top_p").asDouble()).isEqualTo(0.95);
        assertThat(p0(r).get("sampling").get("top_k").asInt()).isEqualTo(20);
        // a quote schema of none: no response_format on quote calls, the talk calls keep theirs
        Run none = run(dir, "n", "scenarios/n3-group.yaml", true, "call-settings", map.replace(
                "\"quote\":{\"max_tokens\":2560,", "\"quote\":{\"schema\":\"none\",\"max_tokens\":2560,"));
        for (MockRequest q : none.requests()) {
            assertThat(body(q).has("response_format")).as(q.user()).isEqualTo(q.user().startsWith("talk|"));
        }
        // the map's timeouts reach the client: a quote call slower than its 1 s map timeout fails
        String slow = map.replace("\"quote\":{\"max_tokens\":2560,\"timeout_sec\":140}", "\"quote\":{\"max_tokens\":2560,\"timeout_sec\":1}");
        Path out = dir.resolve("slow.jsonl");
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(q -> q.user().startsWith("game|")
                ? Reply.text("{\"quote\": 2.09, \"plan\": \"p\", \"rationale\": \"r\"}").withDelayMs(2500) : reply(q)))) {
            assertThatThrownBy(() -> LlmCommands.run(TrialDirCliTest.o("scenario", "scenarios/n3-group.yaml", "seat", "LLM",
                    "model", "mock-model-1", "seed", "2", "out", out.toString(), "analysis-script", "../tools/analysis.py",
                    "multi-seat", "on", "talk", "on", "call-settings", slow, "base-url", s.baseUrl())))
                    .hasMessageContaining("timed out");
        }
        assertThat(talk).isPositive();
        assertThat(quote).isPositive();
        JsonNode p = Canonical.MAPPER.readTree(Files.readString(r.trial().resolve("params.json")));
        assertThat(CallSettingsMap.fromJson(Canonical.text(p.get("settings"))).toJson())
                .isEqualTo(CallSettingsMap.fromJson(map).toJson());
        assertThat(p.get("thinking").asBoolean()).isTrue(); // the effective value of the run, not the unset --thinking
        assertThat(p.get("sampling").get("max_tokens").asInt()).isEqualTo(2560);
        JsonNode llm = Canonical.MAPPER.readTree(Files.readAllLines(r.out()).get(0)).get("llm");
        assertThat(llm.get("callSettings").asText()).isEqualTo(CallSettingsMap.fromJson(map).toJson());
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", r.out() + ".cache.jsonl", "run", r.out().toString()))).isZero();
        SeatsIntegrationI1Test.schemaCheck(r.out(), Path.of(r.out() + ".calls.jsonl"));
    }

    @Test
    void theGridColumnFlagsSetMaxTokensPerCallTypeAndAMapThatRestatesTheRunChangesNothing(@TempDir Path dir) throws Exception {
        Run plain = run(dir, "a", "scenarios/n3-group.yaml", true, "max-tokens", "300");
        Run same = run(dir, "b", "scenarios/n3-group.yaml", true, "max-tokens", "300", "max-tokens-talk", "300",
                "max-tokens-quote", "300", "max-tokens-question", "300");
        assertThat(same.requests().stream().map(MockRequest::rawBody).toList())
                .isEqualTo(plain.requests().stream().map(MockRequest::rawBody).toList());
        JsonNode pa = Canonical.MAPPER.readTree(Files.readString(plain.trial().resolve("params.json")));
        assertThat(pa.has("settings")).isFalse();
        assertThat(Canonical.MAPPER.readTree(Files.readAllLines(plain.out()).get(0)).get("llm").has("callSettings")).isFalse();
        Run split = run(dir, "c", "scenarios/n3-group.yaml", true, "max-tokens-talk", "320", "max-tokens-quote", "400",
                "thinking", "off", "temperature", "0.7", "top-p", "0.8", "top-k", "20");
        for (MockRequest q : split.requests()) {
            JsonNode b = body(q);
            assertThat(b.get("max_tokens").asInt()).isEqualTo(q.user().startsWith("talk|") ? 320 : 400);
            assertThat(b.get("chat_template_kwargs").get("enable_thinking").asBoolean()).isFalse();
        }
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", split.out() + ".cache.jsonl", "run", split.out().toString())))
                .isZero();
    }

    @Test
    void trackSQuoteCallsTakeTheMapAndTheProbeKeepsTheRunSettings(@TempDir Path dir) throws Exception {
        Run r = run(dir, "s", "scenarios/ripe-game.yaml", false, "max-tokens-quote", "777", "probe-rounds", "1");
        assertThat(r.requests()).anyMatch(q -> q.user().startsWith("probe|"));
        for (MockRequest q : r.requests()) {
            assertThat(body(q).get("max_tokens").asInt()).as(q.user()).isEqualTo(q.user().startsWith("probe|") ? 400 : 777);
            assertThat(body(q).has("chat_template_kwargs")).isFalse();
        }
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", r.out() + ".cache.jsonl", "run", r.out().toString()))).isZero();
    }

    @Test
    void theMapsTimeoutsGoToTheClientUnlessACallTimeoutIsGiven() throws Exception {
        LlmSettings s = new LlmSettings("openai-compatible", "m", 0.7, 400);
        CallSettingsMap m = LlmCommands.callSettings(TrialDirCliTest.o("call-settings", "{\"calls\":{\"talk\":{\"max_tokens\":1,"
                + "\"timeout_sec\":30},\"quote\":{\"max_tokens\":1,\"timeout_sec\":140},\"question\":{\"max_tokens\":1,"
                + "\"timeout_sec\":90}}}"), s);
        Map<String, Duration> t = LlmCommands.callTimeouts(TrialDirCliTest.o("call-timeout-sec", "quote=50,probe=20"), m);
        assertThat(t).containsEntry("quote", Duration.ofSeconds(50)).containsEntry("talk", Duration.ofSeconds(30))
                .containsEntry("question", Duration.ofSeconds(90)).containsEntry("probe", Duration.ofSeconds(20));
        assertThat(LlmCommands.callTimeouts(TrialDirCliTest.o(), null)).isEmpty();
        assertThat(LlmCommands.callSettings(TrialDirCliTest.o(), s)).isNull();
    }

    @Test
    void malformedOrSenselessMapsAreRefused(@TempDir Path dir) throws Exception {
        LlmSettings s = new LlmSettings("openai-compatible", "m", 0.7, 400);
        String calls = "\"talk\":{\"max_tokens\":1,\"timeout_sec\":1},\"question\":{\"max_tokens\":1,\"timeout_sec\":1}";
        for (String[] bad : new String[][] {
            {"call-settings", "{\"calls\":{" + calls + ",\"quote\":{\"max_tokens\":1,\"timeout_sec\":1,\"schema\":\"talk\"}}}"},
            {"call-settings", "{\"calls\":{\"talk\":{\"max_tokens\":1,\"timeout_sec\":1,\"schema\":\"decision\"},"
                    + "\"quote\":{\"max_tokens\":1,\"timeout_sec\":1},\"question\":{\"max_tokens\":1,\"timeout_sec\":1}}}"},
            {"call-settings", "{\"calls\":{" + calls.replace("\"question\":{", "\"question\":{\"schema\":\"decision\",")
                    + ",\"quote\":{\"max_tokens\":1,\"timeout_sec\":1}}}"},
            {"call-settings", "{\"calls\":{}}"},
            {"call-settings", "{not json"},
            {"call-settings", "{}", "max-tokens-quote", "5"},
            {"max-tokens-talk", "0"},
            {"call-settings", "{\"calls\":{\"talk\":{\"max_tokens\":1,\"timeout_sec\":1,\"schema\":\"none\"},"
                    + "\"quote\":{\"max_tokens\":1,\"timeout_sec\":1},\"question\":{\"max_tokens\":1,\"timeout_sec\":1}}}"},
            {"max-tokens-quote", "lots"},
        }) {
            assertThatThrownBy(() -> LlmCommands.callSettings(TrialDirCliTest.o(bad), s)).as(String.join(" ", bad))
                    .isInstanceOf(IllegalArgumentException.class);
        }
        LlmSettings off = new LlmSettings("openai-compatible", "m", 0.7, 400, false, null, null);
        assertThatThrownBy(() -> LlmCommands.callSettings(TrialDirCliTest.o("call-settings", "{\"thinking\":true,\"calls\":{"
                + calls + ",\"quote\":{\"max_tokens\":1,\"timeout_sec\":1}}}"), off))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("contradicts --thinking off");
        Path f = dir.resolve("map.json");
        Files.writeString(f, "{\"calls\":{\"talk\":{\"max_tokens\":9,\"timeout_sec\":1},\"quote\":{\"max_tokens\":8,"
                + "\"timeout_sec\":1},\"question\":{\"max_tokens\":7,\"timeout_sec\":1}}}");
        assertThat(LlmCommands.callSettings(TrialDirCliTest.o("call-settings", f.toString()), s).call(
                io.github.tomloscalzo.collusion.texts.CallType.QUOTE).maxTokens()).isEqualTo(8);
        // the file tools/trial/trial_cmd.py writes (C14.1): sorted keys, thinking at the top
        Path t = dir.resolve("call_settings.json");
        Files.writeString(t, "{\"calls\": {\"question\": {\"max_tokens\": 2048, \"timeout_sec\": 140}, \"quote\": {\"max_tokens\": "
                + "2560, \"timeout_sec\": 140}, \"talk\": {\"max_tokens\": 1024, \"timeout_sec\": 140}}, \"temperature\": 0.6, "
                + "\"thinking\": true, \"top_k\": 20, \"top_p\": 0.95}\n");
        LlmSettings q = LlmCommands.callSettings(TrialDirCliTest.o("call-settings", t.toString()), s)
                .settingsFor(s, io.github.tomloscalzo.collusion.texts.CallType.TALK);
        assertThat(q.maxTokens()).isEqualTo(1024);
        assertThat(q.thinking()).isTrue();
        assertThat(q.topK()).isEqualTo(20);
        // other commands refuse the call settings rather than ignore them
        assertThatThrownBy(() -> Main.run(TrialDirCliTest.o("scenario", "scenarios/ripe-game.yaml", "seed", "1", "out",
                dir.resolve("x.jsonl").toString(), "max-tokens-quote", "9"))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LlmCommands.vignette(TrialDirCliTest.o("scenario", "scenarios/ripe-game.yaml",
                "call-settings", t.toString()))).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void theR1InstructionIsOnlyInR1QuoteCallsTheFormatIsUnchangedAndNoReasoningReachesAPrompt(@TempDir Path dir)
            throws Exception {
        Run ctl = run(dir, "r0", "scenarios/n3-group.yaml", true, "condition-texts", "all:private_chat");
        Run r1 = run(dir, "r1", "scenarios/n3-group.yaml", true, "condition-texts", "all:private_chat", "options",
                "{\"quote_instruction\":\"r1_reflect\",\"reply_field\":false}");
        assertThat(r1.requests()).hasSameSizeAs(ctl.requests());
        for (int i = 0; i < r1.requests().size(); i++) {
            MockRequest a = ctl.requests().get(i);
            MockRequest b = r1.requests().get(i);
            assertThat(b.user()).isEqualTo(a.user());
            boolean quote = b.user().startsWith("game|");
            // the system prompt (with the reply format line) and the schema are the control's
            assertThat(b.system()).isEqualTo(a.system()).contains(PromptBuilder.decisionFormat(
                    LlmCommands.loadConfig("scenarios/n3-group.yaml").scenario().market()));
            assertThat(body(b).get("response_format")).isEqualTo(body(a).get("response_format"));
            assertThat(body(b).get("response_format").get("json_schema").get("schema"))
                    .isEqualTo(Canonical.MAPPER.readTree(quote ? PromptBuilder.DECISION_SCHEMA
                            : io.github.tomloscalzo.collusion.agents.llm.TalkParser.TALK_SCHEMA));
            // the instruction is in the quote turn (also as the repair's first turn) and nowhere else; the rest is equal
            assertThat(b.turns().get(0).content().contains(R1)).as(b.user()).isEqualTo(quote);
            assertThat(b.turns().stream().skip(1).noneMatch(t -> t.content().contains(R1))).isTrue();
            assertThat(b.turns().size()).isEqualTo(a.turns().size());
            for (int k = 0; k < b.turns().size(); k++) {
                assertThat(b.turns().get(k).content().replace(R1 + " Then reply in the format given above.\n\n", ""))
                        .isEqualTo(a.turns().get(k).content());
            }
        }
        // the repair turn quotes the reply text, never its reasoning; no reasoning in any prompt of either run
        assertThat(r1.requests()).anyMatch(q -> q.user().endsWith("|llm2|r2|a1"));
        for (Run run : List.of(ctl, r1)) {
            for (MockRequest q : run.requests()) {
                assertThat(q.rawBody()).as(q.user()).doesNotContain(CANARY);
            }
        }
        // the reasoning is recorded in events.jsonl
        assertThat(Files.readString(r1.trial().resolve("events.jsonl"))).contains(CANARY);
    }
}
