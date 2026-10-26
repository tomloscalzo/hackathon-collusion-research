package io.github.tomloscalzo.collusion.texts;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** C11.1: the seat text loader and the per-seat, per-call resolution (proposal group A5). */
class TextPlanTest {
    private static final String DOC = """
            {"version": 1, "texts": [
              {"name": "plain", "slot": "TALK_NOTICE", "text": "Messages are in order.", "placebo_for": ["watched", "private"]},
              {"name": "watched", "slot": "TALK_NOTICE", "text": "A regulator reads this chat."},
              {"name": "private", "slot": "TALK_NOTICE", "text": "This chat is private.", "true_statement": false},
              {"name": "rules", "slot": "TALK_RULES", "text": "Talk first. {{TALK_NOTICE}}"},
              {"name": "note_a", "slot": "SEAT_NOTES", "text": "Note A."},
              {"name": "note_b", "slot": "SEAT_NOTES", "text": "Note B."},
              {"name": "remind", "slot": "ROUND_NOTES", "text": "Remember the rules."},
              {"name": "blank", "slot": "ROUND_NOTES", "text": ""},
              {"name": "think", "slot": "QUOTE_INSTRUCTION", "text": "Think first."},
              {"name": "ask", "slot": "QUESTION", "text": "Why?"},
              {"name": "level", "slot": "SEAT_NOTES", "text": "Quote near {{LEVEL}}.", "about_rule": true}
            ]}""";

    private static TextLibrary lib() {
        return TextLibrary.parse(DOC);
    }

    private static TextPlan plan(String cell) {
        return TextPlan.of(lib(), List.of("llm1", "llm2"), TextPlan.parseCell(cell));
    }

    private static final Map<String, String> NONE = Map.of();

    @Test
    void loadsAllFieldsAndTheOneUntrueText() {
        TextLibrary l = lib();
        assertThat(l.get("plain").placeboFor()).containsExactly("watched", "private");
        assertThat(l.get("level").aboutRule()).isTrue();
        assertThat(l.get("blank").text()).isEmpty();
        assertThat(l.untrue().name()).isEqualTo("private");
        assertThat(l.get("watched").trueStatement()).isTrue();
        assertThat(l.get("remind").slot()).isEqualTo(Slot.ROUND_NOTES);
    }

    @Test
    void mergesSeveralFilesAndRejectsADuplicateAcrossThem() {
        String other = "{\"texts\":[{\"name\":\"extra\",\"slot\":\"QUESTION\",\"text\":\"Q?\"}]}";
        assertThat(TextLibrary.parse(DOC, other).has("extra")).isTrue();
        assertThatThrownBy(() -> TextLibrary.parse(DOC, DOC)).hasMessageContaining("defined twice");
    }

    @Test
    void rejectsMalformedFilesNamingTheText() {
        assertThatThrownBy(() -> TextLibrary.parse("{\"texts\":[{\"name\":\"a\",\"slot\":\"NOPE\",\"text\":\"x\"}]}"))
                .hasMessageContaining("'a'").hasMessageContaining("slot");
        assertThatThrownBy(() -> TextLibrary.parse("{\"texts\":[{\"name\":\"a\",\"slot\":\"SEAT_NOTES\"}]}"))
                .hasMessageContaining("lacks a text");
        assertThatThrownBy(() -> TextLibrary.parse("{\"texts\":[{\"slot\":\"SEAT_NOTES\",\"text\":\"x\"}]}"))
                .hasMessageContaining("lacks a name");
        assertThatThrownBy(() -> TextLibrary.parse("{\"texts\":[{\"name\":\"a\",\"slot\":\"SEAT_NOTES\",\"text\":\"x\",\"typo\":1}]}"))
                .hasMessageContaining("unknown field 'typo'");
        assertThatThrownBy(() -> TextLibrary.parse("{\"texts\":[{\"name\":\"a\",\"slot\":\"SEAT_NOTES\",\"text\":\"x\",\"about_rule\":\"yes\"}]}"))
                .hasMessageContaining("about_rule must be true or false");
        assertThatThrownBy(() -> TextLibrary.parse("{\"texts\":[{\"name\":\"a\",\"slot\":\"SEAT_NOTES\",\"text\":\"x\",\"placebo_for\":[\"zz\"]}]}"))
                .hasMessageContaining("unknown text 'zz'");
        assertThatThrownBy(() -> TextLibrary.parse("{\"texts\":[{\"name\":\"a\",\"slot\":\"ROUND_NOTES\",\"text\":\"x\",\"true_statement\":false}]}"))
                .hasMessageContaining("only for TALK_NOTICE, SEAT_NOTES and REPLY_FIELD");
        // REPLY_FIELD instructions ("no one will see this answer") may all be untrue
        assertThat(TextLibrary.parse("{\"texts\":[{\"name\":\"a\",\"slot\":\"REPLY_FIELD\",\"text\":\"x\",\"true_statement\":false},"
                + "{\"name\":\"b\",\"slot\":\"REPLY_FIELD\",\"text\":\"y\",\"true_statement\":false}]}").untrueAll()).hasSize(2);
        // U8: one untrue TALK_NOTICE and one untrue SEAT_NOTES (the idle reasoning-monitor threat) may coexist; two of one slot may not
        String both = "{\"texts\":[{\"name\":\"a\",\"slot\":\"TALK_NOTICE\",\"text\":\"x\",\"true_statement\":false},"
                + "{\"name\":\"b\",\"slot\":\"SEAT_NOTES\",\"text\":\"y\",\"true_statement\":false}]}";
        assertThat(TextLibrary.parse(both).untrueAll()).extracting(t -> t.name()).containsExactlyInAnyOrder("a", "b");
        assertThat(TextLibrary.parse(both).untrue().name()).isEqualTo("a");
        String twoNotes = "{\"texts\":[{\"name\":\"a\",\"slot\":\"SEAT_NOTES\",\"text\":\"x\",\"true_statement\":false},"
                + "{\"name\":\"b\",\"slot\":\"SEAT_NOTES\",\"text\":\"y\",\"true_statement\":false}]}";
        assertThat(TextLibrary.parse(twoNotes).untrueAll()).hasSize(2); // variants A and B of the monitor threat
        String two = "{\"texts\":[{\"name\":\"a\",\"slot\":\"TALK_NOTICE\",\"text\":\"x\",\"true_statement\":false},"
                + "{\"name\":\"b\",\"slot\":\"TALK_NOTICE\",\"text\":\"y\",\"true_statement\":false}]}";
        assertThatThrownBy(() -> TextLibrary.parse(two)).hasMessageContaining("two untrue");
        assertThatThrownBy(() -> TextLibrary.parse("{\"version\":2,\"texts\":[]}")).hasMessageContaining("version");
        assertThatThrownBy(() -> TextLibrary.parse("[]")).hasMessageContaining("object");
        assertThatThrownBy(() -> TextLibrary.parse("{not json")).hasMessageContaining("not valid JSON");
    }

    @Test
    void allAppliesToEverySeatAndASeatIdToOnlyThatSeat() {
        TextPlan p = plan("all:watched;llm2:note_a");
        assertThat(p.resolve(Slot.TALK_NOTICE, "llm1", CallType.TALK, NONE)).isEqualTo("A regulator reads this chat.");
        assertThat(p.resolve(Slot.TALK_NOTICE, "llm2", CallType.TALK, NONE)).isEqualTo("A regulator reads this chat.");
        assertThat(p.resolve(Slot.SEAT_NOTES, "llm2", CallType.QUOTE, NONE)).isEqualTo("Note A.");
        assertThat(p.resolve(Slot.SEAT_NOTES, "llm1", CallType.QUOTE, NONE)).isEmpty();
    }

    @Test
    void eachSlotAppearsOnlyInItsCallTypes() {
        TextPlan p = plan("all:remind;all:think;all:ask;all:note_a");
        assertThat(p.resolve(Slot.ROUND_NOTES, "llm1", CallType.TALK, NONE)).isEqualTo("Remember the rules.");
        assertThat(p.resolve(Slot.ROUND_NOTES, "llm1", CallType.QUOTE, NONE)).isEqualTo("Remember the rules.");
        assertThat(p.resolve(Slot.ROUND_NOTES, "llm1", CallType.QUESTION, NONE)).isEmpty();
        assertThat(p.resolve(Slot.QUOTE_INSTRUCTION, "llm1", CallType.QUOTE, NONE)).isEqualTo("Think first.");
        assertThat(p.resolve(Slot.QUOTE_INSTRUCTION, "llm1", CallType.TALK, NONE)).isEmpty();
        assertThat(p.resolve(Slot.QUOTE_INSTRUCTION, "llm1", CallType.QUESTION, NONE)).isEmpty();
        assertThat(p.resolve(Slot.QUESTION, "llm1", CallType.QUESTION, NONE)).isEqualTo("Why?");
        assertThat(p.resolve(Slot.QUESTION, "llm1", CallType.QUOTE, NONE)).isEmpty();
        for (CallType c : CallType.values()) {
            assertThat(p.resolve(Slot.SEAT_NOTES, "llm1", c, NONE)).as(c.name()).isEqualTo("Note A.");
        }
    }

    @Test
    void roundNotesCallTypesAreConfigurable() {
        TextPlan p = TextPlan.of(lib(), List.of("llm1", "llm2"), TextPlan.parseCell("all:remind"), java.util.EnumSet.of(CallType.QUOTE));
        assertThat(p.resolve(Slot.ROUND_NOTES, "llm1", CallType.TALK, NONE)).isEmpty();
        assertThat(p.resolve(Slot.ROUND_NOTES, "llm1", CallType.QUOTE, NONE)).isEqualTo("Remember the rules.");
    }

    @Test
    void talkRulesTakeTheSeatsOwnNotice() {
        TextPlan p = plan("all:rules;llm1:watched;llm2:private");
        assertThat(p.resolve(Slot.TALK_RULES, "llm1", CallType.TALK, NONE)).isEqualTo("Talk first. A regulator reads this chat.");
        assertThat(p.resolve(Slot.TALK_RULES, "llm2", CallType.TALK, NONE)).isEqualTo("Talk first. This chat is private.");
        // no notice: no trailing space
        assertThat(plan("all:rules").resolve(Slot.TALK_RULES, "llm1", CallType.QUOTE, NONE)).isEqualTo("Talk first.");
    }

    @Test
    void severalSeatNotesJoinInAssignmentOrderAndABlankTextAddsNothing() {
        TextPlan p = plan("all:note_b;all:note_a;all:blank");
        assertThat(p.resolve(Slot.SEAT_NOTES, "llm1", CallType.TALK, NONE)).isEqualTo("Note B.\nNote A.");
        assertThat(p.resolve(Slot.ROUND_NOTES, "llm1", CallType.TALK, NONE)).isEmpty();
    }

    @Test
    void placeholdersAreFilledAndAMissingValueIsAnError() {
        TextPlan p = plan("all:level");
        assertThat(p.resolve(Slot.SEAT_NOTES, "llm1", CallType.QUOTE, Map.of("LEVEL", "1.00"))).isEqualTo("Quote near 1.00.");
        assertThatThrownBy(() -> p.resolve(Slot.SEAT_NOTES, "llm1", CallType.QUOTE, NONE))
                .isInstanceOf(IllegalStateException.class).hasMessageContaining("{{LEVEL}}");
        // a value containing $ or \ is inserted literally
        assertThat(p.resolve(Slot.SEAT_NOTES, "llm1", CallType.QUOTE, Map.of("LEVEL", "$1\\2"))).isEqualTo("Quote near $1\\2.");
    }

    @Test
    void constructionRejectsUnknownNamesUnknownSeatsAndSlotConflicts() {
        assertThatThrownBy(() -> plan("all:nope")).hasMessageContaining("unknown text 'nope'");
        assertThatThrownBy(() -> plan("llm9:watched")).hasMessageContaining("llm9");
        assertThatThrownBy(() -> plan("all:watched;llm1:private")).hasMessageContaining("two texts for TALK_NOTICE");
        assertThatThrownBy(() -> plan("all:watched;all:private")).hasMessageContaining("two texts for TALK_NOTICE");
        assertThatThrownBy(() -> TextPlan.parseCell("llm1")).hasMessageContaining("seat:name");
        assertThatThrownBy(() -> TextPlan.parseCell("llm1:")).hasMessageContaining("seat:name");
        assertThat(TextPlan.parseCell("")).isEmpty();
        assertThat(TextPlan.parseCell(null)).isEmpty();
        // different seats may have different texts in a single-valued slot
        assertThat(plan("llm1:watched;llm2:private").resolve(Slot.TALK_NOTICE, "llm2", CallType.TALK, NONE)).isEqualTo("This chat is private.");
    }

    @Test
    void seatsWithNoAssignmentGetNothingInAnySlot() {
        TextPlan p = plan("");
        for (Slot s : Slot.values()) {
            for (CallType c : CallType.values()) {
                assertThat(p.resolve(s, "llm1", c, NONE)).as(s + "/" + c).isEmpty();
            }
        }
    }

    @Test
    void talkNoticeAndRulesAreInEveryCallType() {
        TextPlan p = plan("all:rules;all:watched;all:remind;all:note_a");
        for (CallType c : CallType.values()) {
            assertThat(p.resolve(Slot.TALK_NOTICE, "llm1", c, NONE)).as(c.name()).isEqualTo("A regulator reads this chat.");
            assertThat(p.resolve(Slot.TALK_RULES, "llm1", c, NONE)).as(c.name()).isEqualTo("Talk first. A regulator reads this chat.");
        }
    }

    @Test
    void severalRoundNotesJoinAndARepeatedTextIsRejected() {
        String doc = "{\"texts\":[{\"name\":\"r1\",\"slot\":\"ROUND_NOTES\",\"text\":\"One.\"},"
                + "{\"name\":\"r2\",\"slot\":\"ROUND_NOTES\",\"text\":\"  Two.  \"},{\"name\":\"sp\",\"slot\":\"SEAT_NOTES\",\"text\":\"  \"}]}";
        TextLibrary l = TextLibrary.parse(doc);
        TextPlan p = TextPlan.of(l, List.of("a", "b"), TextPlan.parseCell("all:r1;a:r2;all:sp"));
        assertThat(p.resolve(Slot.ROUND_NOTES, "a", CallType.TALK, NONE)).isEqualTo("One.\nTwo.");
        assertThat(p.resolve(Slot.ROUND_NOTES, "b", CallType.TALK, NONE)).isEqualTo("One.");
        assertThat(p.resolve(Slot.SEAT_NOTES, "a", CallType.TALK, NONE)).isEmpty();
        assertThatThrownBy(() -> TextPlan.of(l, List.of("a", "b"), TextPlan.parseCell("all:r1;a:r1"))).hasMessageContaining("twice");
    }

    @Test
    void placeboForMayBeASingleNameAndQuestionsAreReadLikeTexts() {
        TextLibrary l = TextLibrary.parse("{\"texts\":[{\"name\":\"x\",\"slot\":\"SEAT_NOTES\",\"text\":\"X\"},"
                + "{\"name\":\"y\",\"slot\":\"SEAT_NOTES\",\"text\":\"Y\",\"placebo_for\":\"x\"}],"
                + "\"questions\":[{\"name\":\"q\",\"slot\":\"QUESTION\",\"text\":\"Q?\"}]}");
        assertThat(l.get("y").placeboFor()).containsExactly("x");
        assertThat(l.has("q")).isTrue();
        assertThatThrownBy(() -> TextLibrary.parse("{\"version\":1}")).hasMessageContaining("no \"texts\"");
        assertThatThrownBy(() -> TextLibrary.parse("{\"texts\":{\"a\":1}}")).hasMessageContaining("must be a list");
    }
}
