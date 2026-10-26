package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.texts.TextLibrary;
import io.github.tomloscalzo.collusion.texts.TextPlan;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * U8: renders, from the real code and the real text files, the first quote prompt and the first talk prompt of the D-set cell
 * (2 firms, private chat) for every D level and all five wordings, and checks that the score instruction is in the quote
 * prompt only, once, after the rationale (last) in the format line and the schema. Set the environment variable DSET_PROMPTS_DIR to also write the
 * prompts as files for reading (one per level and wording, plus index.md).
 */
class DSetPromptRenderTest {
    record Level(String id, String threat, String field, String text) {}

    static final List<Level> LEVELS = List.of(new Level("null", null, null, null),
            new Level("cot_monitor_threat_a", "cot_monitor_threat_a", null, null),
            new Level("cot_monitor_threat_b", "cot_monitor_threat_b", null, null),
            new Level("score_conflict", null, "conflict_score", "score_conflict"),
            new Level("score_temptation_a", null, "temptation_score", "score_temptation_a"),
            new Level("score_temptation_b", null, "temptation_score", "score_temptation_b"),
            new Level("score_placebo", null, "placebo_score", "score_placebo"));

    @Test
    void everyLevelAndWordingRendersWithTheInstructionOnlyInTheQuotePrompt() throws Exception {
        TextLibrary lib = TextLibrary.loadResources("prompts/seat_texts.json", "prompts/questions.json");
        GameConfig cfg = TalkPhaseTest.load("slice-m-p3");
        List<String> seats = cfg.agents().stream().map(a -> a.id()).toList();
        String dir = System.getenv("DSET_PROMPTS_DIR");
        StringBuilder index = new StringBuilder("# D-set rendered prompts (U8)\n\nCell: slice-m-p3, 2 LLM firms, private chat (private_chat notice), "
                + "round 1, seat " + seats.get(0) + ". One file per level and wording: the first quote-call prompt (system + user turn) and "
                + "the first talk-call prompt.\n\n| level | wording | file | quote system chars | quote user chars |\n|---|---|---|---|---|\n");
        for (Level lv : LEVELS) {
            for (int w = 0; w < 5; w++) {
                List<TextPlan.Assignment> as = new ArrayList<>(List.of(new TextPlan.Assignment("all", "private_chat")));
                if (lv.threat() != null) {
                    as.add(new TextPlan.Assignment("all", lv.threat()));
                }
                ReplyExtra extra = lv.field() == null ? null : ReplyExtra.fromOptions(Canonical.MAPPER.readTree(
                        "{\"reply_extra\":{\"name\":\"" + lv.field() + "\",\"kind\":\"integer\",\"min\":1,\"max\":5,\"position\":\"last\",\"text\":\"" + lv.text()
                                + "\"}}"), lib);
                ReplyExtraTest.Client c = new ReplyExtraTest.Client(extra == null ? "" : "\"" + lv.field() + "\": 3, ");
                LlmGame.run(cfg, 5, TalkPhaseTest.SETTINGS, Condition.neutral(), w, c, null, java.util.Set.of(), true, null, true,
                        LlmGame.Extras.NONE.withTexts(TextPlan.of(lib, seats, as)).withReplyExtra(extra));
                LlmRequest quote = c.requests.stream().filter(r -> r.drawKey().startsWith("game|") && r.drawKey().contains("|" + seats.get(0)
                        + "|r1|a0")).findFirst().get();
                LlmRequest talk = c.requests.stream().filter(r -> r.drawKey().startsWith("talk|") && r.drawKey().contains("|" + seats.get(0)
                        + "|r1|t0")).findFirst().get();
                String instr = lv.text() == null ? null : lib.get(lv.text()).text();
                String threat = lv.threat() == null ? null : lib.get(lv.threat()).text();
                for (LlmRequest r : List.of(quote, talk)) { // the briefing is in every call's system prompt
                    assertThat(r.system().contains("monitored")).as(lv.id() + " w" + w).isEqualTo(threat != null);
                    if (threat != null) {
                        assertThat(r.system()).contains(threat);
                    }
                }
                if (instr != null) {
                    assertThat(count(quote.system(), instr)).isEqualTo(1);
                    assertThat(quote.system()).contains("\"rationale\": \"<your reasons, briefly>\", \"" + lv.field() + "\": <integer from 1 to 5>}")
                            .doesNotContain("<number>, \"" + lv.field());
                    assertThat(quote.responseSchema()).contains("\"rationale\":{\"type\":\"string\"},\"" + lv.field() + "\":{\"type\":\"integer\"")
                            .endsWith("\"rationale\",\"" + lv.field() + "\"]}");
                    assertThat(quote.system().indexOf(instr)).isGreaterThan(quote.system().indexOf("\"" + lv.field() + "\""));
                    assertThat(quote.system()).endsWith(instr);
                    assertThat(talk.system()).doesNotContain(instr).doesNotContain(lv.field());
                    assertThat(quote.turns().get(0).content()).doesNotContain(instr);
                    assertThat(talk.turns().get(0).content()).doesNotContain(instr);
                } else {
                    assertThat(quote.system()).doesNotContain("No one will see this answer");
                }
                String name = lv.id() + "__w" + w + ".md";
                if (dir != null) {
                    String body = "# Level " + lv.id() + ", wording " + w + "\n\n## Quote call: system prompt\n\n```\n" + quote.system()
                            + "\n```\n\n## Quote call: user turn\n\n```\n" + quote.turns().get(0).content() + "\n```\n\n## Quote call: response schema\n\n```\n"
                            + quote.responseSchema() + "\n```\n\n## Talk call: system prompt\n\n```\n" + talk.system()
                            + "\n```\n\n## Talk call: user turn\n\n```\n" + talk.turns().get(0).content() + "\n```\n";
                    Files.createDirectories(Path.of(dir));
                    Files.writeString(Path.of(dir).resolve(name), body, StandardCharsets.UTF_8);
                }
                index.append("| ").append(lv.id()).append(" | gm0").append(w + 1).append(" | ").append(name).append(" | ")
                        .append(quote.system().length()).append(" | ").append(quote.turns().get(0).content().length()).append(" |\n");
            }
        }
        if (dir != null) {
            Files.writeString(Path.of(dir).resolve("index.md"), index.toString(), StandardCharsets.UTF_8);
        }
    }

    static int count(String s, String t) {
        int n = 0;
        for (int i = s.indexOf(t); i >= 0; i = s.indexOf(t, i + 1)) {
            n++;
        }
        return n;
    }
}
