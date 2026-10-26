package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** C13.2: a seat's own last 10 questions and answers, rendered for its later prompts (proposal A6, F1). */
class OwnAnswersTest {
    private static final List<String> ROSTER = List.of("llm1", "llm2");

    @Test
    void emptyBeforeTheFirstAnswer() {
        assertThat(OwnAnswers.render(SeatView.sorted("llm1", ROSTER))).isEmpty();
        assertThat(OwnAnswers.render(List.of())).isEmpty();
    }

    @Test
    void theBlockHasTheDraftShapeWithTheQuestionStatedOnce() {
        SeatView v = SeatView.sorted("llm1", ROSTER);
        v.recordAnswer(3, "What would you say publicly?", "I held the price.");
        v.recordAnswer(4, "What would you say publicly?", "Same again.");
        assertThat(OwnAnswers.render(v)).isEqualTo("After earlier rounds you were asked: \"What would you say publicly?\"\n"
                + "Your answers (oldest first; at most the last 10 are shown):\n"
                + "- After round 3: \"I held the price.\"\n"
                + "- After round 4: \"Same again.\"");
    }

    @Test
    void onlyTheLastTenAreShownOldestFirstAndInFull() {
        SeatView v = SeatView.sorted("llm1", ROSTER);
        String longAnswer = "word ".repeat(400).strip();
        for (int r = 1; r <= 12; r++) {
            v.recordAnswer(r, "Q?", r == 12 ? longAnswer : "answer-" + r);
        }
        String block = OwnAnswers.render(v);
        assertThat(block).doesNotContain("answer-1\"").doesNotContain("answer-2\"");
        assertThat(block).contains("- After round 3: \"answer-3\"").contains("- After round 11: \"answer-11\"");
        assertThat(block.indexOf("answer-3\"")).isLessThan(block.indexOf("answer-11\""));
        assertThat(block).endsWith("- After round 12: \"" + longAnswer + "\"");
        assertThat(block.lines().filter(l -> l.startsWith("- After round")).count()).isEqualTo(SeatView.ANSWER_WINDOW);
    }

    @Test
    void anotherSeatsAnswersNeverAppear() {
        SeatView a = SeatView.sorted("llm1", ROSTER);
        SeatView b = SeatView.sorted("llm2", ROSTER);
        a.recordAnswer(1, "Q?", "CANARY-A secret");
        b.recordAnswer(1, "Q?", "CANARY-B secret");
        assertThat(OwnAnswers.render(a)).contains("CANARY-A").doesNotContain("CANARY-B");
        assertThat(OwnAnswers.render(b)).contains("CANARY-B").doesNotContain("CANARY-A");
        SeatView c = SeatView.sorted("llm1", List.of("llm1", "llm2", "llm3"));
        assertThat(OwnAnswers.render(c)).isEmpty();
    }

    @Test
    void severalQuestionsNameTheirQuestionOnEachLine() {
        SeatView v = SeatView.sorted("llm1", ROSTER);
        v.recordAnswer(2, "Q one?", "A one");
        v.recordAnswer(2, "Q two?", "A two");
        assertThat(OwnAnswers.render(v)).isEqualTo("Your earlier answers (oldest first; at most the last 10 are shown):\n"
                + "- After round 2, asked \"Q one?\": \"A one\"\n"
                + "- After round 2, asked \"Q two?\": \"A two\"");
    }

    @Test
    void multiLineAnswersAreKeptAsGiven() {
        SeatView v = SeatView.sorted("llm1", ROSTER);
        v.recordAnswer(1, "Q?", "line one\nline two");
        assertThat(OwnAnswers.render(v)).endsWith("- After round 1: \"line one\nline two\"");
    }

    @Test
    void moreThanTheWindowIsRefused() {
        List<SeatView.Answer> many = new ArrayList<>();
        for (int i = 1; i <= SeatView.ANSWER_WINDOW + 1; i++) {
            many.add(new SeatView.Answer(i, "Q?", "a"));
        }
        assertThatThrownBy(() -> OwnAnswers.render(many)).hasMessageContaining("at most 10");
    }

    @Test
    void exactlyTenAreAllShownAndQuotesAreKeptAsGiven() {
        SeatView v = SeatView.sorted("llm1", ROSTER);
        for (int r = 1; r <= SeatView.ANSWER_WINDOW; r++) {
            v.recordAnswer(r, "Say \"why\"?", "a" + r);
        }
        String block = OwnAnswers.render(v);
        assertThat(block).startsWith("After earlier rounds you were asked: \"Say \"why\"?\"");
        assertThat(block.lines().filter(l -> l.startsWith("- After round")).count()).isEqualTo(10);
        assertThat(block).contains("- After round 1: \"a1\"");
    }

    @Test
    void aQuestionRepeatedNonAdjacentlyStillCountsAsTwoQuestions() {
        SeatView v = SeatView.sorted("llm1", ROSTER);
        v.recordAnswer(1, "Q?", "x");
        v.recordAnswer(2, "R?", "y");
        v.recordAnswer(3, "Q?", "z");
        assertThat(OwnAnswers.render(v)).startsWith("Your earlier answers").contains("- After round 3, asked \"Q?\": \"z\"");
    }
}
