package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.engine.Observation;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** C3.1: what one seat may see (proposal group A2 labels, group F/A6 own answers), tested in isolation. */
class SeatViewTest {
    static final List<String> ROSTER = List.of("llm", "partner", "partner2", "partner3");

    @Test
    void sortedLabelsAreExactlyTodaysCounterpartLabels() {
        for (String self : ROSTER) {
            List<String> rivals = new ArrayList<>(ROSTER);
            rivals.remove(self);
            SeatView v = SeatView.sorted(self, ROSTER);
            assertThat(v.labels()).containsExactlyEntriesOf(PromptBuilder.counterpartLabels(rivals));
            assertThat(v.rivalIds()).containsExactlyElementsOf(rivals);
        }
        SeatView two = SeatView.sorted("llm", List.of("partner", "llm"));
        assertThat(two.labels()).containsExactlyEntriesOf(Map.of("partner", "M2"));
        assertThat(two.label("partner")).isEqualTo("M2");
    }

    @Test
    void labelsNeverNameTheSeatItselfAndAreM2Upwards() {
        SeatView v = SeatView.seeded("partner2", ROSTER, 7L);
        assertThat(v.seatId()).isEqualTo("partner2");
        assertThat(v.labels()).doesNotContainKey("partner2");
        assertThat(v.labels().keySet()).containsExactlyInAnyOrder("llm", "partner", "partner3");
        assertThat(v.labels().values()).containsExactly("M2", "M3", "M4");
        assertThatThrownBy(() -> v.label("partner2")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> v.label("nobody")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void seededLabelsAreDeterministicPerSeedAndSeatAndVaryWithTheSeed() {
        assertThat(SeatView.seeded("llm", ROSTER, 42L).labels())
                .containsExactlyEntriesOf(SeatView.seeded("llm", ROSTER, 42L).labels());
        // the roster order given does not matter, only the ids
        assertThat(SeatView.seeded("llm", List.of("partner3", "llm", "partner", "partner2"), 42L).labels())
                .containsExactlyEntriesOf(SeatView.seeded("llm", ROSTER, 42L).labels());
        // golden pin: a change of random source or stream name would silently re-label seats across runs and caches
        assertThat(SeatView.seeded("llm", ROSTER, 42L).labels())
                .containsExactly(Map.entry("partner3", "M2"), Map.entry("partner", "M3"), Map.entry("partner2", "M4"));
        Set<Map<String, String>> seen = new HashSet<>();
        for (long seed = 0; seed < 60; seed++) {
            seen.add(SeatView.seeded("llm", ROSTER, seed).labels());
        }
        assertThat(seen).hasSize(6); // all 3! assignments occur: the seed, not the id order, sets the labels (gotcha 5)
        // two seats of the same game draw their own assignment (stream named per seat)
        boolean differs = false;
        for (long seed = 0; seed < 20 && !differs; seed++) {
            List<String> a = new ArrayList<>(SeatView.seeded("partner", ROSTER, seed).labels().keySet());
            List<String> b = new ArrayList<>(SeatView.seeded("partner2", ROSTER, seed).labels().keySet());
            a.remove("partner2");
            b.remove("partner");
            differs = !a.equals(b);
        }
        assertThat(differs).isTrue();
    }

    @Test
    void rosterMustContainTheSeatOnceAndAtLeastOneRival() {
        assertThatThrownBy(() -> SeatView.sorted("ghost", ROSTER)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SeatView.sorted("llm", List.of("llm"))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SeatView.sorted("llm", List.of("llm", "partner", "partner")))
                .isInstanceOf(IllegalArgumentException.class);
    }

    static Observation obs(String self, Map<String, Double> rivalQuotes) {
        var pr = new Observation.PastRound(1, 2.0, null, true, rivalQuotes, 2.0, null, null, false);
        return new Observation(2, self, ROSTER, List.of(pr), 0.5);
    }

    @Test
    void ownObservationAcceptsOnlyThisSeatsObservation() {
        SeatView v = SeatView.sorted("partner", ROSTER);
        Observation mine = obs("partner", Map.of("llm", 2.0, "partner2", 2.1, "partner3", 2.2));
        assertThat(v.ownObservation(mine)).isSameAs(mine);
        assertThatThrownBy(() -> v.ownObservation(obs("llm", Map.of("partner", 2.0))))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("llm");
        // a quote attributed to the seat itself, or to an id outside the roster, is not a rival's
        assertThatThrownBy(() -> v.ownObservation(obs("partner", Map.of("partner", 2.0))))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> v.ownObservation(obs("partner", Map.of("stranger", 2.0))))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void ownAnswersAreKeptPerViewAndOnlyTheLastTenAreShownOldestFirst() {
        SeatView a = SeatView.sorted("llm", ROSTER);
        SeatView b = SeatView.sorted("partner", ROSTER);
        assertThat(a.recentAnswers()).isEmpty();
        for (int r = 1; r <= 13; r++) {
            a.recordAnswer(r, "Q?", "CANARY-llm-" + r);
        }
        b.recordAnswer(1, "Q?", "CANARY-partner-1");
        List<SeatView.Answer> shown = a.recentAnswers();
        assertThat(SeatView.ANSWER_WINDOW).isEqualTo(10);
        assertThat(shown).hasSize(10);
        assertThat(shown.get(0)).isEqualTo(new SeatView.Answer(4, "Q?", "CANARY-llm-4"));
        assertThat(shown.get(9).answer()).isEqualTo("CANARY-llm-13");
        assertThat(shown).extracting(SeatView.Answer::answer).noneMatch(s -> s.contains("partner"));
        assertThat(b.recentAnswers()).extracting(SeatView.Answer::answer).containsExactly("CANARY-partner-1");
        assertThatThrownBy(() -> shown.add(new SeatView.Answer(1, "x", "y")))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void answersMustComeInRoundOrderAndBeNonNull() {
        SeatView v = SeatView.sorted("llm", ROSTER);
        v.recordAnswer(3, "Q?", "a");
        v.recordAnswer(3, "Q2?", "b"); // two questions after the same round are allowed
        assertThatThrownBy(() -> v.recordAnswer(2, "Q?", "c")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> v.recordAnswer(0, "Q?", "c")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> v.recordAnswer(4, null, "c")).isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> v.recordAnswer(4, "Q?", null)).isInstanceOf(NullPointerException.class);
        assertThat(v.recentAnswers()).hasSize(2);
    }
}
