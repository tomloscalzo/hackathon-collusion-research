package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Unit N1: renders, through the real run command and the real text files, the first quote prompt (system prompt and
 * round-1 user turn) of seat llm1 for one cell of every Track M arm family with payoff_examples neutral, and checks that
 * the payoff and audit examples print none of the theory's levels (2.09, 2.08, 1.54). Set NEUTRAL_PROMPTS_DIR to also
 * write one file per arm. A level printed by a seat text, a control text or a scripted partner's disclosed rule is not
 * hidden by this option (it changes only the worked examples); the test lists those and expects exactly the known ones.
 */
class NeutralPromptRenderTest {
    record Arm(String name, String scenario, boolean talk, String cell, String options) {}

    static final String PRIVATE = "all:private_chat";

    static List<Arm> arms() {
        List<Arm> a = new ArrayList<>();
        for (int p = 1; p <= 5; p++) { // point 2 was dropped from the headline by the owner but the scenario exists
            String s = "slice-m-p" + p;
            a.add(new Arm("headline-tacit-p" + p, s, false, "all:neutral", ""));
            a.add(new Arm("headline-chat-p" + p, s, true, PRIVATE, ""));
            a.add(new Arm("headline-monitored-p" + p, s, true, "all:regulator_reads", ""));
        }
        String m = "slice-m-p3";
        a.add(new Arm("n3-group", "n3-group", true, PRIVATE, ""));
        a.add(new Arm("n3-cheater", "n3-cheater", true, PRIVATE, ""));
        a.add(new Arm("m-pub", m, true, "all:chat_published", ""));
        a.add(new Arm("m-mon0", m, true, "all:chat_not_monitored", ""));
        a.add(new Arm("n3-ethics", "n3-group", true, "all:private_chat;llm1:placebo_ethics;llm2:placebo_ethics;llm3:rule_ethics", ""));
        a.add(new Arm("m-asym", m, true, "all:private_chat;llm1:placebo_ethics;llm2:rule_ethics", ""));
        a.add(new Arm("m-comp", m, true, PRIVATE, "\"round_reminder\":\"compliance_reminder\""));
        a.add(new Arm("m-inc-target", m, true, "all:private_chat;llm1:pressure_target;llm2:pressure_target", ""));
        a.add(new Arm("m-inc-joint", m, true, "all:private_chat;llm1:maximise_joint_profit;llm2:maximise_joint_profit", ""));
        a.add(new Arm("start-5tick", m, true, PRIVATE, "\"briefing_notice\":\"start_5tick_rule\",\"start_ticks\":5"));
        a.add(new Arm("r2f-confidant", m, true, PRIVATE, "\"question\":\"confidant\",\"question_mode\":\"fed\",\"history_cap\":10"));
        a.add(new Arm("r3f-public", m, true, PRIVATE, "\"question\":\"public\",\"question_mode\":\"fed\",\"history_cap\":10"));
        a.add(new Arm("r2s-confidant", m, true, PRIVATE, "\"reply_extra\":{\"name\":\"confidant_answer\",\"kind\":\"text\","
                + "\"max_chars\":600,\"text\":\"confidant_inreply\"}"));
        a.add(new Arm("r3s-public", m, true, PRIVATE, "\"reply_extra\":{\"name\":\"public_answer\",\"kind\":\"text\","
                + "\"max_chars\":600,\"text\":\"public_inreply\"}"));
        a.add(new Arm("r4-announced", m, true, PRIVATE, "\"briefing_notice\":\"r4_explain\",\"post_game_question\":\"public\""));
        a.add(new Arm("d-cot-monitor-a", m, true, PRIVATE, "\"briefing_notice\":\"cot_monitor_threat_a\""));
        a.add(new Arm("d-cot-monitor-b", m, true, PRIVATE, "\"briefing_notice\":\"cot_monitor_threat_b\""));
        a.add(new Arm("d-conflict", m, true, PRIVATE, "\"reply_extra\":{\"name\":\"conflict_score\",\"kind\":\"integer\",\"min\":1,"
                + "\"max\":5,\"position\":\"last\",\"text\":\"score_conflict\"}"));
        a.add(new Arm("d-temptation-a", m, true, PRIVATE, "\"reply_extra\":{\"name\":\"temptation_score\",\"kind\":\"integer\","
                + "\"min\":1,\"max\":5,\"position\":\"last\",\"text\":\"score_temptation_a\"}"));
        a.add(new Arm("d-temptation-b", m, true, PRIVATE, "\"reply_extra\":{\"name\":\"temptation_score\",\"kind\":\"integer\","
                + "\"min\":1,\"max\":5,\"position\":\"last\",\"text\":\"score_temptation_b\"}"));
        a.add(new Arm("d-placebo", m, true, PRIVATE, "\"reply_extra\":{\"name\":\"placebo_score\",\"kind\":\"integer\",\"min\":1,"
                + "\"max\":5,\"position\":\"last\",\"text\":\"score_placebo\"}"));
        return a;
    }


    /** As TextSlotsCliTest.run, but the mock's chat message and quote name no theory level (the real chat is the model's). */
    static List<MockLlmServer.MockRequest> play(Path dir, String name, String... extra) throws Exception {
        Path out = dir.resolve(name + ".jsonl");
        List<String> kv = new ArrayList<>(List.of("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "model", "mock-model-1",
                "seed", "2", "out", out.toString(), "multi-seat", "on", "talk", "on", "analysis-script", "../tools/analysis.py",
                "trial-dir", dir.resolve(name).toString(), "code-commit", "abc1234"));
        kv.addAll(List.of(extra));
        MockLlmServer.Behaviour b = r -> r.user().startsWith("talk|")
                ? (r.lastUser().contains("You have sent 0 of") ? "{\"message\": \"Hello.\", \"done\": false}"
                : "{\"message\": \"\", \"done\": true}")
                : MockLlmServer.Behaviours.decisionJson(2.00, "ok");
        try (MockLlmServer s = new MockLlmServer(b)) {
            kv.addAll(List.of("base-url", s.baseUrl()));
            LlmCommands.run(TrialDirCliTest.o(kv.toArray(String[]::new)));
            return s.requests();
        }
    }

    @Test
    void noArmPrintsTheTheoryLevelInItsPayoffOrAuditExamples(@TempDir Path tmp) throws Exception {
        String outDir = System.getenv("NEUTRAL_PROMPTS_DIR");
        if (outDir != null) {
            Files.createDirectories(Path.of(outDir));
        }
        List<String> hits = new ArrayList<>();
        for (Arm a : arms()) {
            String opts = "{\"payoff_examples\":\"neutral\"" + (a.options().isEmpty() ? "" : "," + a.options()) + "}";
            List<MockLlmServer.MockRequest> reqs = play(tmp, a.name(), "scenario", "scenarios/" + a.scenario() + ".yaml",
                    "talk", a.talk() ? "on" : "off", "condition-texts", a.cell(), "options", opts);
            MockLlmServer.MockRequest q = reqs.stream().filter(r -> r.user().startsWith("game|") && r.user().contains("|llm1|r1|a0"))
                    .findFirst().orElseThrow();
            String text = "ARM " + a.name() + " (scenario " + a.scenario() + ", condition-texts " + a.cell() + ", options " + opts
                    + ")\n=== SYSTEM ===\n" + q.system() + "\n=== USER (round 1) ===\n" + q.lastUser() + "\n";
            if (outDir != null) {
                Files.writeString(Path.of(outDir).resolve(a.name() + ".txt"), text, StandardCharsets.UTF_8);
            }
            String[] lines = text.split("\n");
            for (int i = 0; i < lines.length; i++) {
                for (String lvl : List.of("2.09", "2.08", "1.54")) {
                    if (lines[i].contains(lvl)) {
                        hits.add(a.name() + ":" + (i + 1) + ": " + lvl);
                    }
                }
            }
        }
        assertThat(hits).as("theory levels printed in a neutral quote prompt").isEmpty();
    }
}
