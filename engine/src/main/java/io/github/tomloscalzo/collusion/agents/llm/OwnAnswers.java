package io.github.tomloscalzo.collusion.agents.llm;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Renders a seat's own earlier question answers for its later prompts (C13.2; interface proposal v5, A6 and F1): the
 * {@code {{OWN_ANSWERS}}} block of talk, quote and question turns. Only the seat's own last
 * {@link SeatView#ANSWER_WINDOW} answers (from {@link SeatView#recentAnswers}) are shown, oldest first, each in full
 * (no cut); nothing of another seat is ever passed in, because a {@link SeatView} holds only its own seat's answers.
 * Before the first answer the block is the empty string, so a game without questions renders exactly as it does today.
 * Pure; not yet used by the prompt builder (the question wiring, C13.3, calls it).
 *
 * <p>Shape (the proposal's DRAFT; one question per arm, so the question is stated once):
 * <pre>
 * After earlier rounds you were asked: "{{QUESTION}}"
 * Your answers (oldest first; at most the last 10 are shown):
 * - After round 3: "&lt;answer&gt;"
 * - After round 4: "&lt;answer&gt;"
 * </pre>
 * If the shown answers were given to more than one question, each line names its own question instead:
 * {@code - After round 3, asked "<question>": "<answer>"} under the header line "Your earlier answers (oldest first; at
 * most the last 10 are shown):".
 */
public final class OwnAnswers {
    private OwnAnswers() {}

    /** The block for this seat, or "" when it has answered nothing yet. No trailing line break. */
    public static String render(SeatView view) {
        return render(view.recentAnswers());
    }

    /** The block for these answers (already limited to the window by the caller; more than the window is refused). */
    public static String render(List<SeatView.Answer> answers) {
        if (answers.size() > SeatView.ANSWER_WINDOW) {
            throw new IllegalArgumentException("at most " + SeatView.ANSWER_WINDOW + " answers are shown: " + answers.size());
        }
        if (answers.isEmpty()) {
            return "";
        }
        Set<String> questions = new LinkedHashSet<>();
        for (SeatView.Answer a : answers) {
            questions.add(a.question());
        }
        StringBuilder b = new StringBuilder();
        boolean single = questions.size() == 1;
        if (single) {
            b.append("After earlier rounds you were asked: \"").append(answers.get(0).question()).append("\"\n")
                    .append("Your answers (oldest first; at most the last ").append(SeatView.ANSWER_WINDOW).append(" are shown):");
        } else {
            b.append("Your earlier answers (oldest first; at most the last ").append(SeatView.ANSWER_WINDOW).append(" are shown):");
        }
        for (SeatView.Answer a : answers) {
            b.append("\n- After round ").append(a.round());
            if (!single) {
                b.append(", asked \"").append(a.question()).append('"');
            }
            b.append(": \"").append(a.answer()).append('"');
        }
        return b.toString();
    }
}
