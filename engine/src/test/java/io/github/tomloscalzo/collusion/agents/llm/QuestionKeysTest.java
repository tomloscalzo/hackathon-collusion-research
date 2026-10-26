package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.llm.OpenAiCompatibleClient;
import io.github.tomloscalzo.collusion.texts.TextLibrary;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** C13.1: question draw keys (proposal D3, F) and the question plan read from the trial options. */
class QuestionKeysTest {
    private static final String QUESTIONS = "{\"texts\":["
            + "{\"name\":\"confidant\",\"slot\":\"QUESTION\",\"text\":\"What would you tell a confidant?\"},"
            + "{\"name\":\"public\",\"slot\":\"QUESTION\",\"text\":\"What would you say publicly?\"},"
            + "{\"name\":\"note\",\"slot\":\"SEAT_NOTES\",\"text\":\"A note.\"}]}";

    private static TextLibrary lib() {
        return TextLibrary.parse(QUESTIONS);
    }

    @Test
    void theKeyHasTheDocumentedShape() {
        assertThat(QuestionKeys.key("confidant", QuestionKeys.Mode.FED, "ripe-game", 7, "llm1", 3))
                .isEqualTo("question|confidant|fed|ripe-game|s7|llm1|r3|a0");
        assertThat(QuestionKeys.key("public", QuestionKeys.Mode.POST, "ripe-game", 7, "llm2", 40))
                .isEqualTo("question|public|post|ripe-game|s7|llm2|r40|a0");
    }

    @Test
    void keysAreUniquePerQuestionModeSeatRoundSeedAndScenario() {
        Set<String> seen = new HashSet<>();
        int n = 0;
        for (String name : List.of("confidant", "public")) {
            for (QuestionKeys.Mode mode : QuestionKeys.Mode.values()) {
                for (String seat : List.of("llm1", "llm2", "llm3")) {
                    for (int r = 1; r <= 40; r++) {
                        for (long seed : new long[] {1, 2}) {
                            for (String sc : List.of("a", "b")) {
                                seen.add(QuestionKeys.key(name, mode, sc, seed, seat, r));
                                n++;
                            }
                        }
                    }
                }
            }
        }
        assertThat(seen).hasSize(n);
    }

    @Test
    void aQuestionKeyNeverEqualsOrShiftsAGameKey() {
        // the game key as LlmAgent builds it: "game|" + scenario + "|s" + seed + "|" + seat + "|r" + round + "|a" + attempt
        String game = "game|ripe-game|s7|llm1|r3|a0";
        String q = QuestionKeys.key("confidant", QuestionKeys.Mode.FED, "ripe-game", 7, "llm1", 3);
        assertThat(q).isNotEqualTo(game).doesNotStartWith("game|");
        assertThat(QuestionKeys.isQuestionKey(q)).isTrue();
        assertThat(QuestionKeys.isQuestionKey(game)).isFalse();
        assertThatThrownBy(() -> QuestionKeys.parse(game)).hasMessageContaining("not a question draw key");
        assertThatThrownBy(() -> QuestionKeys.parse("talk|ripe-game|s7|llm1|r3|t0|a0")).hasMessageContaining("not a question");
        // the client routes it as a question call, not a quote
        assertThat(OpenAiCompatibleClient.callType(q)).isEqualTo("question");
        assertThat(OpenAiCompatibleClient.callType(game)).isEqualTo("quote");
        // fed and post of the same question and round differ, even though their prompts may match
        assertThat(q).isNotEqualTo(QuestionKeys.key("confidant", QuestionKeys.Mode.POST, "ripe-game", 7, "llm1", 3));
    }

    @Test
    void parseReadsAKeyBack() {
        String q = QuestionKeys.key("r3.public-2", QuestionKeys.Mode.POST, "n3-group", 101, "llm3", 12);
        assertThat(QuestionKeys.parse(q)).isEqualTo(new QuestionKeys.Parts("r3.public-2", QuestionKeys.Mode.POST, "n3-group", 101, "llm3", 12));
    }

    @Test
    void badPartsAreRefused() {
        QuestionKeys.Mode f = QuestionKeys.Mode.FED;
        assertThatThrownBy(() -> QuestionKeys.key("a|b", f, "s", 1, "x", 1)).hasMessageContaining("question name");
        assertThatThrownBy(() -> QuestionKeys.key("", f, "s", 1, "x", 1)).hasMessageContaining("question name");
        assertThatThrownBy(() -> QuestionKeys.key(null, f, "s", 1, "x", 1)).hasMessageContaining("question name");
        assertThatThrownBy(() -> QuestionKeys.key("q", null, "s", 1, "x", 1)).hasMessageContaining("mode");
        assertThatThrownBy(() -> QuestionKeys.key("q", f, "s|t", 1, "x", 1)).hasMessageContaining("scenario");
        assertThatThrownBy(() -> QuestionKeys.key("q", f, "s", 1, "x|y", 1)).hasMessageContaining("seat");
        assertThatThrownBy(() -> QuestionKeys.key("q", f, "s", 1, "x", 0)).hasMessageContaining("round");
        assertThatThrownBy(() -> QuestionKeys.Mode.ofTag("later")).hasMessageContaining("fed or post");
    }

    @Test
    void planReadsTheIntrospectionOptionsOfTheDesign() {
        // R2/R3 (trackm_design.yaml): question + question_mode fed + history_cap 10
        List<QuestionPlan.Entry> r2 = QuestionPlan.fromOptionsJson(lib(), "{\"question\":\"confidant\",\"question_mode\":\"fed\",\"history_cap\":10}");
        assertThat(r2).hasSize(1);
        assertThat(r2.get(0).name()).isEqualTo("confidant");
        assertThat(r2.get(0).mode()).isEqualTo(QuestionKeys.Mode.FED);
        assertThat(r2.get(0).fedBack()).isTrue();
        assertThat(r2.get(0).text()).isEqualTo("What would you tell a confidant?");
        assertThat(r2.get(0).drawKey("ripe-game", 101, "llm2", 5)).isEqualTo("question|confidant|fed|ripe-game|s101|llm2|r5|a0");
        // R4: briefing_notice (not ours) + post_game_question
        List<QuestionPlan.Entry> r4 = QuestionPlan.fromOptionsJson(lib(), "{\"briefing_notice\":\"r4_explain\",\"post_game_question\":\"public\"}");
        assertThat(r4).hasSize(1);
        assertThat(r4.get(0).mode()).isEqualTo(QuestionKeys.Mode.POST);
        assertThat(r4.get(0).fedBack()).isFalse();
        // default mode is fed; both can be asked together (optional post pass on a fed arm)
        assertThat(QuestionPlan.fromOptionsJson(lib(), "{\"question\":\"public\",\"post_game_question\":\"public\"}"))
                .extracting(QuestionPlan.Entry::mode).containsExactly(QuestionKeys.Mode.FED, QuestionKeys.Mode.POST);
    }

    @Test
    void noOptionsOrNoQuestionOptionMeansNoQuestionCalls() {
        assertThat(QuestionPlan.fromOptionsJson(lib(), null)).isEmpty();
        assertThat(QuestionPlan.fromOptionsJson(lib(), "")).isEmpty();
        assertThat(QuestionPlan.fromOptionsJson(lib(), "{}")).isEmpty();
        assertThat(QuestionPlan.fromOptionsJson(lib(), "{\"round_reminder\":\"compliance_reminder\",\"quote_instruction\":\"r1_reflect\"}")).isEmpty();
    }

    @Test
    void badOptionsAreRefused() {
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{\"question\":\"nope\"}")).hasMessageContaining("unknown question 'nope'");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{\"question\":\"note\"}")).hasMessageContaining("not a question");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{\"question\":\"public\",\"question_mode\":\"later\"}"))
                .hasMessageContaining("fed or post");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{\"question\":\"public\",\"history_cap\":5}")).hasMessageContaining("history_cap");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{\"question_mode\":\"fed\"}")).hasMessageContaining("without a question");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "[1]")).hasMessageContaining("object");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{nope")).hasMessageContaining("not valid JSON");
        TextLibrary blank = TextLibrary.parse("{\"texts\":[{\"name\":\"q\",\"slot\":\"QUESTION\",\"text\":\" \"}]}");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(blank, "{\"question\":\"q\"}")).hasMessageContaining("no text");
    }

    @Test
    void aQuestionNameThatCannotBeInAKeyIsRefusedAtPlanTime() {
        TextLibrary odd = TextLibrary.parse("{\"texts\":[{\"name\":\"my q\",\"slot\":\"QUESTION\",\"text\":\"Q?\"},"
                + "{\"name\":\"a|b\",\"slot\":\"QUESTION\",\"text\":\"Q?\"}]}");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(odd, "{\"question\":\"my q\"}")).hasMessageContaining("draw key");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(odd, "{\"post_game_question\":\"a|b\"}")).hasMessageContaining("draw key");
    }

    @Test
    void theSameQuestionInTheSameModeTwiceIsACollision() {
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(),
                "{\"question\":\"public\",\"question_mode\":\"post\",\"post_game_question\":\"public\"}"))
                .hasMessageContaining("asked twice");
    }

    @Test
    void historyCapMustBeTheNumberTenAndNeedsAQuestion() {
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{\"question\":\"public\",\"history_cap\":\"10\"}")).hasMessageContaining("history_cap");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{\"question\":\"public\",\"history_cap\":10.5}")).hasMessageContaining("history_cap");
        assertThatThrownBy(() -> QuestionPlan.fromOptionsJson(lib(), "{\"history_cap\":10}")).hasMessageContaining("without a question");
    }

    @Test
    void parseRoundTripsFedNegativeSeedsAndPrefixNamesStayDistinct() {
        String k = QuestionKeys.key("q", QuestionKeys.Mode.FED, "sc", -5, "llm1", 1);
        assertThat(QuestionKeys.parse(k)).isEqualTo(new QuestionKeys.Parts("q", QuestionKeys.Mode.FED, "sc", -5, "llm1", 1));
        assertThat(QuestionKeys.key("q", QuestionKeys.Mode.FED, "sc", 1, "llm1", 1))
                .isNotEqualTo(QuestionKeys.key("q2", QuestionKeys.Mode.FED, "sc", 1, "llm1", 1));
        assertThatThrownBy(() -> QuestionKeys.parse("question|q|later|sc|s1|llm1|r1|a0")).hasMessageContaining("not a question");
        assertThatThrownBy(() -> QuestionKeys.parse("question|q|fed|sc|s1|llm1|r1")).hasMessageContaining("not a question");
        assertThatThrownBy(() -> QuestionKeys.parse(null)).hasMessageContaining("not a question");
    }
}
