package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.texts.CallType;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** C12b.1: the per-call settings map (talk / quote / question), proposal group E1. */
class CallSettingsMapTest {
    private static final LlmSettings BASE = new LlmSettings("openai-compatible", "m", 0.7, 400);

    /** A grid row as make_grid.py writes it for qwen3_14b with thinking on (design file profile t1). */
    private static Map<String, String> row(String thinking) {
        Map<String, String> r = new HashMap<>();
        boolean on = "1".equals(thinking);
        r.put("thinking", thinking);
        r.put("temperature", on ? "0.6" : "0.7");
        r.put("top_p", on ? "0.95" : "0.8");
        r.put("top_k", "20");
        r.put("max_tokens_talk", on ? "1024" : "320");
        r.put("max_tokens_quote", on ? "2560" : "400");
        r.put("max_tokens_question", on ? "2048" : "400");
        r.put("timeout_sec", on ? "140" : "120");
        return r;
    }

    @Test
    void gridRowGivesEachCallTypeItsOwnTokenLimitAndSchema() {
        CallSettingsMap m = CallSettingsMap.fromGridRow(row("1"));
        assertThat(m.settingsFor(BASE, CallType.TALK).maxTokens()).isEqualTo(1024);
        assertThat(m.settingsFor(BASE, CallType.QUOTE).maxTokens()).isEqualTo(2560);
        assertThat(m.settingsFor(BASE, CallType.QUESTION).maxTokens()).isEqualTo(2048);
        assertThat(m.schema(CallType.TALK)).isEqualTo(CallSettingsMap.Schema.TALK);
        assertThat(m.schema(CallType.QUOTE)).isEqualTo(CallSettingsMap.Schema.DECISION);
        assertThat(m.schema(CallType.QUESTION)).isEqualTo(CallSettingsMap.Schema.NONE);
        assertThat(m.timeoutSec(CallType.QUOTE)).isEqualTo(140);
        for (CallType c : CallType.values()) {
            LlmSettings s = m.settingsFor(BASE, c);
            assertThat(s.thinking()).isTrue();
            assertThat(s.temperature()).isEqualTo(0.6);
            assertThat(s.topP()).isEqualTo(0.95);
            assertThat(s.topK()).isEqualTo(20);
            assertThat(s.modelSnapshot()).isEqualTo("m");
        }
    }

    @Test
    void thinkingOffRowGivesTheOffValues() {
        CallSettingsMap m = CallSettingsMap.fromGridRow(row("0"));
        assertThat(m.settingsFor(BASE, CallType.TALK).maxTokens()).isEqualTo(320);
        assertThat(m.settingsFor(BASE, CallType.QUOTE).thinking()).isFalse();
        assertThat(m.settingsFor(BASE, CallType.QUESTION).topP()).isEqualTo(0.8);
        assertThat(m.timeoutSec(CallType.TALK)).isEqualTo(120);
    }

    @Test
    void blankSamplingCellsStayUnsetSoTodaysRequestsAreUnchanged() {
        Map<String, String> r = row("");
        r.put("temperature", "");
        r.put("top_p", "");
        r.put("top_k", "");
        CallSettingsMap m = CallSettingsMap.fromGridRow(r);
        LlmSettings s = m.settingsFor(new LlmSettings("openai-compatible", "m", 0.7, 55), CallType.QUOTE);
        assertThat(s.thinking()).isNull();
        assertThat(s.topP()).isNull();
        assertThat(s.topK()).isNull();
        assertThat(s.temperature()).isEqualTo(0.7);
        assertThat(s.maxTokens()).isEqualTo(400);
    }

    @Test
    void aCallOverrideBeatsTheRunValueForThatCallOnly() {
        CallSettingsMap m = CallSettingsMap.fromJson("""
                {"thinking": true, "temperature": 0.6, "top_p": 0.95, "top_k": 20, "calls": {
                  "talk": {"max_tokens": 300, "timeout_sec": 120, "thinking": false, "temperature": 0.7},
                  "quote": {"max_tokens": 2560, "timeout_sec": 140},
                  "question": {"schema": "none", "max_tokens": 2048, "timeout_sec": 140}}}""");
        assertThat(m.settingsFor(BASE, CallType.TALK).thinking()).isFalse();
        assertThat(m.settingsFor(BASE, CallType.TALK).temperature()).isEqualTo(0.7);
        assertThat(m.settingsFor(BASE, CallType.TALK).topP()).isEqualTo(0.95);
        assertThat(m.settingsFor(BASE, CallType.QUOTE).thinking()).isTrue();
        assertThat(m.settingsFor(BASE, CallType.QUOTE).temperature()).isEqualTo(0.6);
    }

    @Test
    void jsonRoundTripsAndOmitsUnsetValues() {
        CallSettingsMap m = CallSettingsMap.fromGridRow(row("1"));
        String json = m.toJson();
        assertThat(CallSettingsMap.fromJson(json).toJson()).isEqualTo(json);
        for (CallType c : CallType.values()) {
            assertThat(CallSettingsMap.fromJson(json).settingsFor(BASE, c)).isEqualTo(m.settingsFor(BASE, c));
        }
        Map<String, String> r = row("");
        r.put("top_p", "");
        r.put("top_k", "");
        r.put("temperature", "");
        assertThat(CallSettingsMap.fromGridRow(r).toJson()).doesNotContain("thinking", "top_p", "top_k", "temperature");
        assertThat(json).contains("\"schema\":\"talk\"").contains("\"max_tokens\":1024");
    }

    @Test
    void badInputIsRefusedNamingTheProblem() {
        Map<String, String> r = row("1");
        r.remove("max_tokens_talk");
        assertThatThrownBy(() -> CallSettingsMap.fromGridRow(r)).hasMessageContaining("max_tokens_talk");
        Map<String, String> r2 = row("1");
        r2.put("timeout_sec", "");
        assertThatThrownBy(() -> CallSettingsMap.fromGridRow(r2)).hasMessageContaining("timeout_sec");
        Map<String, String> r3 = row("true");
        assertThatThrownBy(() -> CallSettingsMap.fromGridRow(r3)).hasMessageContaining("thinking must be 0 or 1");
        Map<String, String> r4 = row("1");
        r4.put("top_p", "1.5");
        assertThatThrownBy(() -> CallSettingsMap.fromGridRow(r4)).hasMessageContaining("top-p");
        Map<String, String> r5 = row("1");
        r5.put("max_tokens_quote", "0");
        assertThatThrownBy(() -> CallSettingsMap.fromGridRow(r5)).hasMessageContaining(">= 1");
        Map<String, String> r6 = row("1");
        r6.put("temperature", "-1");
        assertThatThrownBy(() -> CallSettingsMap.fromGridRow(r6)).hasMessageContaining("temperature");
        Map<String, String> r7 = row("1");
        r7.put("top_k", "x");
        assertThatThrownBy(() -> CallSettingsMap.fromGridRow(r7)).hasMessageContaining("top_k");

        assertThatThrownBy(() -> CallSettingsMap.fromJson("{\"calls\":{}}")).hasMessageContaining("talk");
        assertThatThrownBy(() -> CallSettingsMap.fromJson("{\"oops\":1,\"calls\":{}}")).hasMessageContaining("unknown key 'oops'");
        assertThatThrownBy(() -> CallSettingsMap.fromJson("[]")).hasMessageContaining("object");
        assertThatThrownBy(() -> CallSettingsMap.fromJson("{\"calls\":{\"talk\":{\"max_tokens\":1,\"timeout_sec\":1,\"schema\":\"x\"}}}"))
                .hasMessageContaining("unknown schema");
        assertThatThrownBy(() -> CallSettingsMap.fromJson("{\"calls\":{\"talk\":{\"max_tokens\":\"9\",\"timeout_sec\":1}}}"))
                .hasMessageContaining("max_tokens must be an integer");
    }

    @Test
    void settingsForNeverChangesTheBaseAndKeepsItsIdentity() {
        LlmSettings base = new LlmSettings("p", "snap", 0.3, 55, Boolean.TRUE, 0.5, 7);
        Map<String, String> r = row("");
        r.put("temperature", "");
        r.put("top_p", "");
        r.put("top_k", "");
        LlmSettings s = CallSettingsMap.fromGridRow(r).settingsFor(base, CallType.TALK);
        assertThat(s).isEqualTo(new LlmSettings("p", "snap", 0.3, 320, Boolean.TRUE, 0.5, 7));
        assertThat(base.maxTokens()).isEqualTo(55);
    }

    @Test
    void perCallTopPTopKAndSchemaOverridesApplyAndAreValidated() {
        String calls = "\"calls\": {\"talk\": {\"schema\": \"none\", \"max_tokens\": 9, \"timeout_sec\": 5, \"top_p\": 0.5, \"top_k\": 3},"
                + "\"quote\": {\"max_tokens\": 9, \"timeout_sec\": 5}, \"question\": {\"max_tokens\": 9, \"timeout_sec\": 5}}";
        CallSettingsMap m = CallSettingsMap.fromJson("{\"top_p\": 0.9, \"top_k\": 20, " + calls + "}");
        assertThat(m.schema(CallType.TALK)).isEqualTo(CallSettingsMap.Schema.NONE);
        assertThat(m.settingsFor(BASE, CallType.TALK).topP()).isEqualTo(0.5);
        assertThat(m.settingsFor(BASE, CallType.TALK).topK()).isEqualTo(3);
        assertThat(m.settingsFor(BASE, CallType.QUOTE).topP()).isEqualTo(0.9);
        assertThat(m.settingsFor(BASE, CallType.QUOTE).topK()).isEqualTo(20);
        assertThatThrownBy(() -> CallSettingsMap.fromJson("{" + calls.replace("0.5", "2") + "}"))
                .hasMessageContaining("top-p");
        assertThatThrownBy(() -> CallSettingsMap.fromJson("{" + calls.replace("\"timeout_sec\": 5, \"top_p\"", "\"timeout_sec\": 0, \"top_p\"") + "}"))
                .hasMessageContaining(">= 1");
        assertThatThrownBy(() -> CallSettingsMap.fromJson("{" + calls.replace("\"top_k\": 3", "\"bogus\": 3") + "}"))
                .hasMessageContaining("unknown key 'bogus'");
        assertThatThrownBy(() -> CallSettingsMap.fromJson("{" + calls.replace("\"max_tokens\": 9, \"timeout_sec\": 5, \"top_p\"", "\"max_tokens\": 4294967297, \"timeout_sec\": 5, \"top_p\"") + "}"))
                .hasMessageContaining("max_tokens must be an integer");
    }
}
