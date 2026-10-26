package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.texts.TextLibrary;
import io.github.tomloscalzo.collusion.texts.TextPlan;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * C11.2 (scope 14.6 C11): the seat text slots wired into the Track M prompts. Each slot's text appears only in the
 * designated seats, call types and prompt parts; blank or absent texts render the prompts exactly as before; a tacit arm
 * refuses a text it has no place for; Track S has no slots.
 */
class TextSlotsWiredTest {
    /** Canary texts, one per slot (and a TALK_RULES text of its own). */
    static final TextLibrary LIB = TextLibrary.parse("""
            {"version": 1, "texts": [
              {"name": "tn_a", "slot": "TALK_NOTICE", "text": "CANARY-NOTICE-A"},
              {"name": "tn_b", "slot": "TALK_NOTICE", "text": "CANARY-NOTICE-B"},
              {"name": "sn", "slot": "SEAT_NOTES", "text": "CANARY-SEAT-NOTE"},
              {"name": "sn2", "slot": "SEAT_NOTES", "text": "CANARY-SECOND-NOTE"},
              {"name": "rn", "slot": "ROUND_NOTES", "text": "CANARY-ROUND-NOTE"},
              {"name": "qi", "slot": "QUOTE_INSTRUCTION", "text": "CANARY-QUOTE-INSTRUCTION"},
              {"name": "tr", "slot": "TALK_RULES", "text": "CANARY-OWN-RULES {{TALK_NOTICE}}"},
              {"name": "comp", "slot": "SEAT_NOTES", "text": "Compete at {{COMPETITIVE_HALF_SPREAD}}."},
              {"name": "blank_sn", "slot": "SEAT_NOTES", "text": ""},
              {"name": "blank_rn", "slot": "ROUND_NOTES", "text": ""},
              {"name": "blank_qi", "slot": "QUOTE_INSTRUCTION", "text": ""},
              {"name": "blank_tn", "slot": "TALK_NOTICE", "text": ""}
            ]}""");
    static final List<String> SEATS = List.of("llm1", "llm2", "llm3");

    static TalkPhaseTest.Mock mock() {
        return new TalkPhaseTest.Mock(m -> m.group(5).equals("0") ? TalkPhaseTest.msg("hello", false)
                : TalkPhaseTest.msg("", true));
    }

    static TalkPhaseTest.Mock play(GameConfig cfg, boolean talk, TextPlan plan) {
        TalkPhaseTest.Mock m = mock();
        LlmGame.run(cfg, 5, TalkPhaseTest.SETTINGS, Condition.neutral(), 0, m, null, java.util.Set.of(), true, null, talk,
                LlmGame.Extras.NONE.withTexts(plan));
        return m;
    }

    static TextPlan plan(String cell) {
        return TextPlan.of(LIB, SEATS, TextPlan.parseCell(cell));
    }

    static String user(LlmRequest r) {
        return r.turns().get(r.turns().size() - 1).content();
    }

    @Test
    void eachSlotsTextAppearsOnlyInItsSeatsCallTypesAndPromptParts() {
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        TalkPhaseTest.Mock m = play(cfg, true, plan("llm1:tn_a;llm3:tn_a;llm2:tn_b;llm1:sn;llm1:sn2;llm2:rn;llm3:qi"));
        assertThat(m.requests).anyMatch(TalkPhaseTest::isTalk).anyMatch(r -> !TalkPhaseTest.isTalk(r));
        for (LlmRequest r : m.requests) {
            String seat = TalkPhaseTest.seat(r);
            boolean talk = TalkPhaseTest.isTalk(r);
            String all = r.system() + "\n" + user(r);
            // TALK_NOTICE: in the system prompt's talk rules; seat llm2 has its own notice (one per seat)
            assertThat(r.system().contains("CANARY-NOTICE-A")).as(r.drawKey()).isEqualTo(!seat.equals("llm2"));
            assertThat(r.system().contains("CANARY-NOTICE-B")).as(r.drawKey()).isEqualTo(seat.equals("llm2"));
            // SEAT_NOTES: llm1's system prompt only (every call type), both notes in assignment order
            assertThat(r.system().contains("CANARY-SEAT-NOTE\nCANARY-SECOND-NOTE")).as(r.drawKey()).isEqualTo(seat.equals("llm1"));
            assertThat(user(r)).doesNotContain("CANARY-SEAT-NOTE");
            // ROUND_NOTES: llm2's talk and quote turns, never the system prompt
            assertThat(user(r).contains("CANARY-ROUND-NOTE")).as(r.drawKey()).isEqualTo(seat.equals("llm2"));
            assertThat(r.system()).doesNotContain("CANARY-ROUND-NOTE");
            // QUOTE_INSTRUCTION: llm3's quote turns only, just above the request line
            assertThat(all.contains("CANARY-QUOTE-INSTRUCTION")).as(r.drawKey()).isEqualTo(seat.equals("llm3") && !talk);
            if (seat.equals("llm3") && !talk) {
                assertThat(user(r)).endsWith("CANARY-QUOTE-INSTRUCTION\n\nChoose your quote for this round.");
            }
            assertThat(r.system()).contains("Before the quotes of each round").doesNotContain("{{");
        }
    }

    @Test
    void aSeatsOwnTalkRulesTextReplacesTheDefaultWordingAndCarriesItsNotice() {
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        TalkPhaseTest.Mock m = play(cfg, true, plan("llm1:tr;all:tn_a"));
        for (LlmRequest r : m.requests) {
            boolean one = TalkPhaseTest.seat(r).equals("llm1");
            assertThat(r.system().contains("CANARY-OWN-RULES CANARY-NOTICE-A")).isEqualTo(one);
            assertThat(r.system().contains("Before the quotes of each round, the market makers can talk in a chat. Each "
                    + "market maker may send")).isEqualTo(!one);
            assertThat(r.system()).contains("CANARY-NOTICE-A");
        }
    }

    @Test
    void blankOrAbsentTextsRenderEveryPromptExactlyAsBefore() {
        for (boolean talk : new boolean[] {true, false}) {
            GameConfig cfg = TalkPhaseTest.load("n3-group");
            List<String> before = play(cfg, talk, null).requests.stream().map(CanonicalRequest::sha256).toList();
            String blanks = talk ? "all:blank_sn;all:blank_rn;all:blank_qi;all:blank_tn" : "all:blank_sn;llm2:blank_rn";
            List<String> after = play(cfg, talk, plan(blanks)).requests.stream().map(CanonicalRequest::sha256).toList();
            List<String> none = play(cfg, talk, plan("")).requests.stream().map(CanonicalRequest::sha256).toList();
            assertThat(after).as("talk " + talk).isEqualTo(before);
            assertThat(none).as("talk " + talk).isEqualTo(before);
        }
    }

    @Test
    void theRealTextFilesBlankControlsAlsoLeaveThePromptsUnchanged() {
        // m-comp-neutral = headline-chat (owner decision: neutral_reminder is blank); neutral is blank too
        TextLibrary real = TextLibrary.loadResources("prompts/seat_texts.json", "prompts/questions.json");
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        List<String> before = play(cfg, true, null).requests.stream().map(CanonicalRequest::sha256).toList();
        TextPlan p = TextPlan.of(real, SEATS, TextPlan.parseCell("all:neutral;all:neutral_reminder"));
        assertThat(play(cfg, true, p).requests.stream().map(CanonicalRequest::sha256).toList()).isEqualTo(before);
        // a real notice changes exactly the system prompt
        TextPlan mon = TextPlan.of(real, SEATS, TextPlan.parseCell("all:regulator_reads"));
        TalkPhaseTest.Mock m = play(cfg, true, mon);
        assertThat(m.requests).allMatch(r -> r.system().contains("A regulator reads all messages in this chat, as they are sent."));
    }

    @Test
    void placeholdersInATextAreFilledFromTheScenario() {
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        TalkPhaseTest.Mock m = play(cfg, true, plan("llm1:comp"));
        String expected = String.format(java.util.Locale.ROOT, "Compete at %.2f.", cfg.scenario().market().s0());
        assertThat(m.requests).filteredOn(r -> TalkPhaseTest.seat(r).equals("llm1")).isNotEmpty()
                .allMatch(r -> r.system().contains(expected));
    }

    @Test
    void aTacitArmRefusesATextItHasNoPlaceForButTakesSeatNotes() {
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        for (String cell : new String[] {"llm2:rn", "all:qi", "all:tn_a", "llm1:tr"}) {
            assertThatThrownBy(() -> play(cfg, false, plan(cell))).as(cell).isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("tacit");
        }
        TalkPhaseTest.Mock m = play(cfg, false, plan("llm3:sn"));
        assertThat(m.requests).allMatch(r -> r.system().contains("CANARY-SEAT-NOTE") == TalkPhaseTest.seat(r).equals("llm3"));
    }

    @Test
    void trackSHasNoTextSlots() {
        GameConfig cfg = TalkPhaseTest.load("n3-group");
        assertThatThrownBy(() -> LlmGame.run(cfg, 5, TalkPhaseTest.SETTINGS, Condition.neutral(), 0, mock(), null,
                java.util.Set.of(), false, null, false, LlmGame.Extras.NONE.withTexts(plan("llm1:sn"))))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("multiSeat");
    }
}
