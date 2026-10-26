package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.texts.TextLibrary;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * U8: the generic optional extra field of the quote reply (ReplyExtra). Off (the default) = every prompt, schema and request
 * byte-identical; on = a named integer (range) or text field right after the quote in the format line and the schema, the
 * instruction text at the end of the format line, the answer parsed and logged and never shown in a later prompt.
 */
class ReplyExtraTest {
    static final TextLibrary LIB = TextLibrary.parse("""
            {"version": 1, "texts": [
              {"name": "score_x", "slot": "REPLY_FIELD", "text": "CANARY-INSTRUCTION give a number. No one will see this answer."},
              {"name": "not_a_field", "slot": "SEAT_NOTES", "text": "x"}
            ]}""");

    static ReplyExtra fromJson(String json) {
        try {
            return ReplyExtra.fromOptions(Canonical.MAPPER.readTree("{\"reply_extra\":" + json + "}"), LIB);
        } catch (java.io.IOException e) {
            throw new IllegalStateException(e);
        }
    }

    static final String INT = "{\"name\":\"conflict_score\",\"kind\":\"integer\",\"min\":1,\"max\":5,\"text\":\"score_x\"}";
    static final String TXT = "{\"name\":\"note_to_self\",\"kind\":\"text\",\"max_chars\":12,\"text\":\"score_x\"}";

    @Test
    void absentOptionIsNull() throws Exception {
        assertThat(ReplyExtra.fromOptions(Canonical.MAPPER.readTree("{}"), LIB)).isNull();
    }

    @Test
    void optionIsValidatedStrictly() {
        for (String bad : new String[] {
                "{\"name\":\"s\",\"kind\":\"integer\",\"min\":1,\"max\":5}",                                   // no text
                "{\"name\":\"s\",\"kind\":\"integer\",\"min\":1,\"max\":5,\"text\":\"ghost\"}",               // unknown text
                "{\"name\":\"s\",\"kind\":\"integer\",\"min\":1,\"max\":5,\"text\":\"not_a_field\"}",         // wrong slot
                "{\"name\":\"s\",\"kind\":\"float\",\"text\":\"score_x\"}",                                   // kind
                "{\"name\":\"quote\",\"kind\":\"integer\",\"min\":1,\"max\":5,\"text\":\"score_x\"}",         // taken name
                "{\"name\":\"Bad Name\",\"kind\":\"integer\",\"min\":1,\"max\":5,\"text\":\"score_x\"}",
                "{\"name\":\"s\",\"kind\":\"integer\",\"min\":5,\"max\":1,\"text\":\"score_x\"}",             // empty range
                "{\"name\":\"s\",\"kind\":\"integer\",\"min\":1,\"text\":\"score_x\"}",                       // no max
                "{\"name\":\"s\",\"kind\":\"integer\",\"min\":1,\"max\":5,\"max_chars\":9,\"text\":\"score_x\"}",
                "{\"name\":\"s\",\"kind\":\"text\",\"min\":1,\"text\":\"score_x\"}",
                "{\"name\":\"s\",\"kind\":\"integer\",\"min\":1,\"max\":5,\"text\":\"score_x\",\"extra\":1}",   // unknown key
                "\"conflict\""}) {
            assertThatThrownBy(() -> fromJson(bad)).as(bad).isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void schemaPutsTheFieldRightAfterTheQuoteAndRequiresIt() throws Exception {
        JsonNode s = Canonical.MAPPER.readTree(fromJson(INT).decisionSchema());
        List<String> keys = new ArrayList<>();
        s.get("properties").fieldNames().forEachRemaining(keys::add);
        assertThat(keys).containsExactly("quote", "conflict_score", "plan", "rationale");
        assertThat(s.get("properties").get("conflict_score").toString()).isEqualTo("{\"type\":\"integer\",\"minimum\":1,\"maximum\":5}");
        assertThat(s.get("required").toString()).isEqualTo("[\"quote\",\"conflict_score\",\"plan\",\"rationale\"]");
        JsonNode t = Canonical.MAPPER.readTree(fromJson(TXT).decisionSchema());
        assertThat(t.get("properties").get("note_to_self").toString()).isEqualTo("{\"type\":\"string\"}");
        assertThat(fromJson(INT).decisionSchema()).isEqualTo("{\"type\":\"object\",\"properties\":{\"quote\":{\"type\":[\"number\",\"null\"]},"
                + "\"conflict_score\":{\"type\":\"integer\",\"minimum\":1,\"maximum\":5},\"plan\":{\"type\":\"string\"},"
                + "\"rationale\":{\"type\":\"string\"}},\"required\":[\"quote\",\"conflict_score\",\"plan\",\"rationale\"]}");
        // the default schema is untouched
        assertThat(PromptBuilder.DECISION_SCHEMA).doesNotContain("conflict_score");
    }

    static final String INT_LAST = INT.replace("}", ",\"position\":\"last\"}");
    static final String TXT_LAST = TXT.replace("}", ",\"position\":\"last\"}");

    @Test
    void positionLastPutsTheFieldAfterTheRationaleInSchemaAndFormatLine() throws Exception {
        JsonNode s = Canonical.MAPPER.readTree(fromJson(INT_LAST).decisionSchema());
        List<String> keys = new ArrayList<>();
        s.get("properties").fieldNames().forEachRemaining(keys::add);
        assertThat(keys).containsExactly("quote", "plan", "rationale", "conflict_score"); // guided decoding writes in this order
        assertThat(s.get("properties").get("conflict_score").toString()).isEqualTo("{\"type\":\"integer\",\"minimum\":1,\"maximum\":5}");
        assertThat(s.get("required").toString()).isEqualTo("[\"quote\",\"plan\",\"rationale\",\"conflict_score\"]");
        GameContext g = GameContext.of(TalkPhaseTest.load("n3-group"), "llm1");
        String plain = PromptBuilder.decisionFormat(g.market());
        String with = PromptBuilder.decisionFormat(g.market(), fromJson(INT_LAST));
        assertThat(with).contains("\"rationale\": \"<your reasons, briefly>\", \"conflict_score\": <integer from 1 to 5>}. The quote is")
                .doesNotContain("<number>, \"conflict_score\"")
                .endsWith(plain.substring(plain.indexOf("The quote is a multiple")) + " CANARY-INSTRUCTION give a number. No one will see this answer.");
        // the answer is still read and stripped wherever it sits
        ReplyExtra e = fromJson(INT_LAST);
        assertThat(e.parse("{\"quote\":2,\"plan\":\"p\",\"rationale\":\"r\",\"conflict_score\":4}")).isEqualTo(new ReplyExtra.Answer(4, true));
        assertThat(e.strip("{\"quote\":2,\"plan\":\"p\",\"rationale\":\"r\",\"conflict_score\":4}")).doesNotContain("conflict_score");
    }

    @Test
    void positionDefaultsToAfterQuoteAndTextKindKeepsItsPlace() throws Exception {
        String explicit = INT.replace("}", ",\"position\":\"after_quote\"}");
        assertThat(fromJson(explicit)).isEqualTo(fromJson(INT));
        assertThat(fromJson(INT).last()).isFalse();
        assertThat(fromJson(TXT).last()).isFalse();
        assertThat(fromJson(TXT).decisionSchema()).contains("\"quote\":{\"type\":[\"number\",\"null\"]},\"note_to_self\"");
        assertThat(fromJson(TXT_LAST).last()).isTrue(); // opt-in only; the R2s/R3s cells do not set it
        for (String bad : new String[] {INT.replace("}", ",\"position\":\"first\"}"), INT.replace("}", ",\"position\":3}")}) {
            assertThatThrownBy(() -> fromJson(bad)).as(bad).isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void integerParsingAcceptsOnlyWholeNumbersInRange() {
        ReplyExtra e = fromJson(INT);
        assertThat(e.parse("{\"quote\":2,\"conflict_score\":3,\"plan\":\"p\"}")).isEqualTo(new ReplyExtra.Answer(3, true));
        assertThat(e.parse("{\"quote\":2,\"conflict_score\":3.0}")).isEqualTo(new ReplyExtra.Answer(3, true));
        assertThat(e.parse("noise {\"quote\":2,\"conflict_score\":\" 5 \"} noise")).isEqualTo(new ReplyExtra.Answer(5, true));
        for (String bad : new String[] {"{\"conflict_score\":0}", "{\"conflict_score\":6}", "{\"conflict_score\":2.5}",
                "{\"conflict_score\":\"high\"}", "{\"conflict_score\":null}", "{\"quote\":2}", "{\"conflict_score\":true}",
                "{\"conflict_score\":1e12}", "no json", ""}) {
            assertThat(e.parse(bad)).as(bad).isEqualTo(new ReplyExtra.Answer(null, false));
        }
        assertThat(e.parse(null)).isEqualTo(new ReplyExtra.Answer(null, false));
    }

    @Test
    void textParsingTrimsAndCaps() {
        ReplyExtra e = fromJson(TXT);
        assertThat(e.parse("{\"note_to_self\":\"  short \"}")).isEqualTo(new ReplyExtra.Answer("short", true));
        assertThat(e.parse("{\"note_to_self\":\"abcdefghijklmnopqrstuvwxyz\"}")).isEqualTo(new ReplyExtra.Answer("abcdefghijkl", true));
        assertThat(e.parse("{\"note_to_self\":\"   \"}").valid()).isFalse();
        assertThat(e.parse("{\"note_to_self\":4}").valid()).isFalse();
    }

    @Test
    void formatLineGetsTheFieldAfterTheQuoteAndTheInstructionAtTheEnd() {
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        GameContext g = GameContext.of(cfg, "llm1");
        String plain = PromptBuilder.decisionFormat(g.market());
        String with = PromptBuilder.decisionFormat(g.market(), fromJson(INT));
        assertThat(with).contains("{\"quote\": <number>, \"conflict_score\": <integer from 1 to 5>, \"plan\":")
                .endsWith(plain.substring(plain.indexOf("The quote is a multiple")) + " CANARY-INSTRUCTION give a number. No one will see this answer.");
        assertThat(PromptBuilder.decisionFormat(g.market(), fromJson(TXT))).contains("\"note_to_self\": \"<text, at most 12 characters>\"");
    }

    /** A client that answers every quote with the given extra-field value and records the requests. */
    static final class Client implements LlmClient {
        final List<LlmRequest> requests = new ArrayList<>();
        final String field;

        Client(String field) {
            this.field = field;
        }

        @Override
        public synchronized LlmResponse complete(LlmRequest r) {
            requests.add(r);
            String text = r.drawKey().startsWith("talk|") ? "{\"message\": \"\", \"done\": true}"
                    : "{\"quote\": 2.09, " + field + "\"plan\": \"plan-ok\", \"rationale\": \"why\"}";
            return new LlmResponse(text, 10, 10, 0L, false, CanonicalRequest.sha256(r), "stop");
        }
    }

    static List<LlmRequest> play(boolean talk, ReplyExtra extra, String field) {
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        Client c = new Client(field);
        LlmGame.run(cfg, 5, TalkPhaseTest.SETTINGS, Condition.neutral(), 0, c, null, java.util.Set.of(), true, null, talk,
                LlmGame.Extras.NONE.withReplyExtra(extra));
        return c.requests;
    }

    @Test
    void offIsByteIdenticalAndOnChangesOnlyTheQuoteCallsSystemPromptAndSchema() {
        for (boolean talk : new boolean[] {true, false}) {
            List<LlmRequest> off = play(talk, null, "");
            assertThat(off).isNotEmpty();
            List<LlmRequest> on = play(talk, fromJson(INT), "\"conflict_score\": 4, ");
            assertThat(on).hasSameSizeAs(off);
            for (int i = 0; i < off.size(); i++) {
                boolean quote = off.get(i).drawKey().startsWith("game|");
                if (quote) {
                    assertThat(on.get(i).system()).contains("\"conflict_score\": <integer from 1 to 5>").contains("CANARY-INSTRUCTION");
                    assertThat(on.get(i).responseSchema()).contains("conflict_score");
                    assertThat(off.get(i).responseSchema()).doesNotContain("conflict_score");
                    assertThat(off.get(i).system()).doesNotContain("CANARY-INSTRUCTION");
                } else { // talk calls: neither the field nor its instruction, and the talk schema is the talk schema
                    assertThat(on.get(i).responseSchema()).isEqualTo(off.get(i).responseSchema());
                    assertThat(on.get(i).system()).isEqualTo(off.get(i).system());
                }
                assertThat(on.get(i).turns()).as("user turns are untouched by the field: never fed back").isEqualTo(off.get(i).turns());
            }
            assertThat(play(talk, null, "")).as("off is deterministic").isEqualTo(off);
        }
    }

    @Test
    void anAnswerIsNeverShownInALaterPrompt() {
        List<LlmRequest> on = play(false, fromJson(TXT), "\"note_to_self\": \"SELF-CANARY\", ");
        assertThat(on).isNotEmpty();
        for (LlmRequest r : on) {
            assertThat(r.system()).doesNotContain("SELF-CANARY");
            r.turns().forEach(t -> assertThat(t.content()).doesNotContain("SELF-CANARY"));
        }
    }

    @Test
    void theProbeAndTheRepairNeverCarryTheAnswerToALaterCall() {
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        Client c = new Client("\"note_to_self\": \"SELF-CANARY\", ");
        LlmGame.run(cfg, 5, TalkPhaseTest.SETTINGS, Condition.neutral(), 0, c, null, java.util.Set.of(1), true, null, false,
                LlmGame.Extras.NONE.withReplyExtra(fromJson(TXT)));
        List<LlmRequest> probes = c.requests.stream().filter(r -> r.drawKey().startsWith("probe|")).toList();
        assertThat(probes).isNotEmpty();
        for (LlmRequest r : probes) {
            assertThat(r.turns()).anyMatch(t -> t.content().contains("plan-ok")); // the decision itself is still re-sent
            r.turns().forEach(t -> assertThat(t.content()).doesNotContain("SELF-CANARY"));
        }
    }

    @Test
    void trackSRefusesTheField() {
        assertThatThrownBy(() -> new PromptBuilder(Condition.neutral(), 0).withReplyExtra(fromJson(INT)))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("Track M");
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        assertThatThrownBy(() -> LlmGame.run(cfg, 5, TalkPhaseTest.SETTINGS, Condition.neutral(), 0, new Client(""), null,
                java.util.Set.of(), false, null, false, LlmGame.Extras.NONE.withReplyExtra(fromJson(INT))))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("multiSeat");
    }
}
