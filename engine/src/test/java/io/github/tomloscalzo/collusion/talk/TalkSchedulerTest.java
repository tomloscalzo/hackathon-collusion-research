package io.github.tomloscalzo.collusion.talk;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** C5.2: the talk scheduler (turns, rotation, done, the 7-message cap) and the seeded labels (gotcha 5). */
class TalkSchedulerTest {
    private static final List<String> SEATS = List.of("a", "b", "c");
    private static final TalkScheduler.Move MSG = TalkScheduler.Move.MESSAGE;
    private static final TalkScheduler.Move DONE = TalkScheduler.Move.DONE;

    /** Plays a round where every seat answers from a script (seat to moves, the last move repeats). */
    private static List<String> play(TalkScheduler s, int round, Map<String, List<TalkScheduler.Move>> script) {
        TalkScheduler.Round r = s.round(round);
        List<String> log = new ArrayList<>();
        Map<String, Integer> used = new HashMap<>();
        while (r.nextSpeaker().isPresent()) {
            String seat = r.nextSpeaker().get();
            List<TalkScheduler.Move> moves = script.get(seat);
            int i = used.merge(seat, 1, Integer::sum) - 1;
            TalkScheduler.Move m = moves.get(Math.min(i, moves.size() - 1));
            log.add(seat + ":" + m + "@" + r.turn());
            r.record(seat, m);
        }
        return log;
    }

    private static TalkScheduler fixed(List<String> seats) {
        return new TalkScheduler(seats, 0, false);
    }

    @Test
    void firstSpeakerRotatesByRound() {
        TalkScheduler s = fixed(SEATS);
        assertThat(s.firstSpeaker(1)).isEqualTo("a");
        assertThat(s.firstSpeaker(2)).isEqualTo("b");
        assertThat(s.firstSpeaker(3)).isEqualTo("c");
        assertThat(s.firstSpeaker(4)).isEqualTo("a");
        assertThat(fixed(List.of("a", "b")).firstSpeaker(2)).isEqualTo("b");
    }

    @Test
    void speakersTakeTurnsInOrderStartingFromTheFirstSpeaker() {
        List<String> log = play(fixed(SEATS), 2, Map.of("a", List.of(MSG), "b", List.of(MSG), "c", List.of(MSG)));
        assertThat(log.subList(0, 6)).containsExactly("b:MESSAGE@0", "c:MESSAGE@1", "a:MESSAGE@2", "b:MESSAGE@3",
                "c:MESSAGE@4", "a:MESSAGE@5");
    }

    @Test
    void sevenMessagesPerFirmThenTheRoundEnds() {
        TalkScheduler.Round r = fixed(List.of("a", "b")).round(1);
        int turns = 0;
        while (r.nextSpeaker().isPresent()) {
            r.record(r.nextSpeaker().get(), MSG);
            turns++;
        }
        assertThat(turns).isEqualTo(14);
        assertThat(r.messages("a")).isEqualTo(7);
        assertThat(r.messages("b")).isEqualTo(7);
        assertThat(r.endReason()).isEqualTo(TalkScheduler.End.CAP);
    }

    @Test
    void doneIsFinalForTheRoundAndTheOtherFirmKeepsTalking() {
        List<String> log = play(fixed(List.of("a", "b")), 1, Map.of("a", List.of(MSG, DONE), "b", List.of(MSG)));
        // a speaks, b speaks, a says done; then b alone until b has sent 7 messages; a never speaks again
        assertThat(log.get(2)).isEqualTo("a:DONE@2");
        assertThat(log.subList(3, log.size())).allMatch(l -> l.startsWith("b:MESSAGE"));
        assertThat(log.stream().filter(l -> l.startsWith("a:")).count()).isEqualTo(2);
        assertThat(log.stream().filter(l -> l.startsWith("b:")).count()).isEqualTo(7);
    }

    @Test
    void roundEndsWhenEveryoneIsDone() {
        TalkScheduler.Round r = fixed(SEATS).round(1);
        for (String seat : SEATS) {
            assertThat(r.nextSpeaker()).contains(seat);
            r.record(seat, DONE);
        }
        assertThat(r.nextSpeaker()).isEmpty();
        assertThat(r.endReason()).isEqualTo(TalkScheduler.End.ALL_DONE);
        assertThat(r.turn()).isEqualTo(3);
    }

    @Test
    void doneDoesNotCountAsOneOfTheSevenMessages() {
        TalkScheduler.Round r = fixed(List.of("a", "b")).round(1);
        r.record("a", MSG);
        r.record("b", DONE);
        assertThat(r.messages("a")).isEqualTo(1);
        assertThat(r.messages("b")).isZero();
        assertThat(r.isDone("b")).isTrue();
        assertThat(r.isDone("a")).isFalse();
    }

    @Test
    void turnIndexCountsEveryCallIncludingDone() {
        TalkScheduler.Round r = fixed(List.of("a", "b")).round(1);
        r.record("a", MSG);
        r.record("b", DONE);
        assertThat(r.turn()).isEqualTo(2);
        assertThat(r.nextSpeaker()).contains("a");
    }

    @Test
    void recordFromTheWrongSeatOrAfterTheEndIsRejected() {
        TalkScheduler.Round r = fixed(List.of("a", "b")).round(1);
        assertThatThrownBy(() -> r.record("b", MSG)).isInstanceOf(IllegalStateException.class);
        r.record("a", DONE);
        r.record("b", DONE);
        assertThatThrownBy(() -> r.record("a", MSG)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void anAdversarialSeatCannotExceedTheBound() {
        // nobody ever says done: total turns are bounded by seats x 7
        for (int n = 2; n <= 4; n++) {
            List<String> seats = List.of("a", "b", "c", "d").subList(0, n);
            TalkScheduler.Round r = fixed(seats).round(1);
            int turns = 0;
            while (r.nextSpeaker().isPresent()) {
                r.record(r.nextSpeaker().get(), MSG);
                turns++;
            }
            assertThat(turns).isEqualTo(n * 7);
        }
    }

    @Test
    void mixOfDoneAndCappedEndsAsCapAndTheWorstCaseIsEightPerSeat() {
        // a sends 7 messages then would say done, but is capped first; b says done at once: not ALL_DONE
        TalkScheduler.Round r = fixed(List.of("a", "b")).round(1);
        r.record("a", MSG);
        r.record("b", DONE);
        while (r.nextSpeaker().isPresent()) {
            r.record("a", MSG);
        }
        assertThat(r.messages("a")).isEqualTo(7);
        assertThat(r.endReason()).isEqualTo(TalkScheduler.End.CAP);
        // worst case: every seat sends 6 messages and then done is asked of nobody extra; with done after 7 it is 8 calls
        TalkScheduler.Round w = fixed(List.of("a", "b")).round(1);
        for (int i = 0; i < 6; i++) {
            w.record("a", MSG);
            w.record("b", MSG);
        }
        w.record("a", DONE);
        w.record("b", DONE);
        assertThat(w.nextSpeaker()).isEmpty();
        assertThat(w.endReason()).isEqualTo(TalkScheduler.End.ALL_DONE);
        assertThat(w.turn()).isEqualTo(14);
    }

    @Test
    void rotationHoldsUnderTheSeededOrder() {
        TalkScheduler s = new TalkScheduler(SEATS, 5);
        for (int r = 1; r <= 6; r++) {
            int i = s.order().indexOf(s.firstSpeaker(r));
            assertThat(s.firstSpeaker(r + 1)).isEqualTo(s.order().get((i + 1) % 3));
            assertThat(s.round(r).nextSpeaker()).contains(s.firstSpeaker(r));
        }
    }

    @Test
    void labelsAndFirstSpeakerAreSeededNotFixed() {
        Set<String> firstSeats = new HashSet<>();
        Set<List<String>> orders = new HashSet<>();
        for (long seed = 0; seed < 60; seed++) {
            TalkScheduler s = new TalkScheduler(SEATS, seed);
            firstSeats.add(s.firstSpeaker(1));
            orders.add(s.order());
            assertThat(s.order()).containsExactlyInAnyOrderElementsOf(SEATS);
            assertThat(s.labels().values()).containsExactlyInAnyOrder("M1", "M2", "M3");
            assertThat(s.labels().keySet()).containsExactlyInAnyOrderElementsOf(SEATS);
        }
        assertThat(firstSeats).containsExactlyInAnyOrder("a", "b", "c");
        assertThat(orders).hasSize(6);
        assertThat(new TalkScheduler(SEATS, 7).order()).isEqualTo(new TalkScheduler(SEATS, 7).order());
        assertThat(new TalkScheduler(SEATS, 7).labels()).isEqualTo(new TalkScheduler(SEATS, 7).labels());
    }

    @Test
    void sameSeedGivesSameRounds() {
        Map<String, List<TalkScheduler.Move>> script = Map.of("a", List.of(MSG), "b", List.of(DONE), "c", List.of(MSG, DONE));
        assertThat(play(new TalkScheduler(SEATS, 11), 3, script)).isEqualTo(play(new TalkScheduler(SEATS, 11), 3, script));
    }

    @Test
    void needsAtLeastTwoDistinctSeats() {
        assertThatThrownBy(() -> new TalkScheduler(List.of("a"), 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new TalkScheduler(List.of("a", "a"), 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
