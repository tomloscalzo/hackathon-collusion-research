package io.github.tomloscalzo.collusion.talk;

import io.github.tomloscalzo.collusion.results.Canonical;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Who speaks when in a round's talk phase (scope 4.2, gotchas 5 and 7). Pure logic: the caller asks {@link Round#nextSpeaker},
 * makes the call, and reports the {@link Move}; nothing here calls a model or touches prompts.
 *
 * <p>Rules. Seats speak in a fixed cyclic order, starting from a first speaker that rotates by one seat each round. A seat
 * may send at most {@link #MAX_MESSAGES} messages per round. A seat that says "done" is finished for the rest of that
 * round: it is never asked again (done is final), and the others carry on. A seat that has sent its 7 messages is also
 * finished, without a further call. The phase ends when no seat is left, so a round has at most seats x 7 message turns
 * plus one done turn per seat. "Done" is not a message: it does not count towards the 7.
 *
 * <p>Seeded assignment (gotcha 5): with {@code shuffle} on (the default), the seed fixes which seat gets which label (M1,
 * M2, ... in {@link #order()}) and which seat speaks first in round 1, using SHA-256 of the seed and seat, so the same seed
 * always gives the same assignment and no seat is favoured by its position in the seat list.
 */
public final class TalkScheduler {
    public static final int MAX_MESSAGES = 7;

    public enum Move { MESSAGE, DONE }

    public enum End { ACTIVE, ALL_DONE, CAP }

    private final List<String> order;
    private final int offset;

    public TalkScheduler(List<String> seats, long seed) {
        this(seats, seed, true);
    }

    public TalkScheduler(List<String> seats, long seed, boolean shuffle) {
        if (seats.size() < 2 || seats.stream().distinct().count() != seats.size()) {
            throw new IllegalArgumentException("talk needs at least two distinct seats");
        }
        List<String> o = new ArrayList<>(seats);
        int off = 0;
        if (shuffle) {
            o.sort(Comparator.comparing((String s) -> Canonical.sha256("label|" + seed + "|" + s)));
            off = Integer.remainderUnsigned(Integer.parseUnsignedInt(Canonical.sha256("first|" + seed).substring(0, 8), 16),
                    o.size());
        }
        this.order = Collections.unmodifiableList(o);
        this.offset = off;
    }

    /** The seats in speaking and label order. */
    public List<String> order() {
        return order;
    }

    /**
     * Seat to its position label: M1 for the first seat of {@link #order()}, M2 for the next, and so on. NOT the labels
     * the prompts show: from C5.5 the game's display labels are SeatView.gameLabels (one seeded assignment over the whole
     * roster, scripted seats included); this order only sets who speaks when. Do not log these as speaker labels.
     */
    public Map<String, String> labels() {
        Map<String, String> m = new LinkedHashMap<>();
        for (int i = 0; i < order.size(); i++) {
            m.put(order.get(i), "M" + (i + 1));
        }
        return m;
    }

    /** Rounds are numbered from 1; the first speaker moves on by one seat each round. */
    public String firstSpeaker(int round) {
        return order.get(Math.floorMod(offset + round - 1, order.size()));
    }

    public Round round(int round) {
        return new Round(round);
    }

    /** The state of one round's talk phase. */
    public final class Round {
        private final Map<String, Integer> messages = new HashMap<>();
        private final Map<String, Boolean> done = new HashMap<>();
        private int cursor;
        private int turn;

        private Round(int round) {
            this.cursor = order.indexOf(firstSpeaker(round));
        }

        private boolean finished(String seat) {
            return done.getOrDefault(seat, false) || messages(seat) >= MAX_MESSAGES;
        }

        /** The seat to call next, or empty when the phase is over. */
        public Optional<String> nextSpeaker() {
            for (int i = 0; i < order.size(); i++) {
                String seat = order.get((cursor + i) % order.size());
                if (!finished(seat)) {
                    return Optional.of(seat);
                }
            }
            return Optional.empty();
        }

        /** Reports what the seat just did; the seat must be the one {@link #nextSpeaker} named. */
        public void record(String seat, Move move) {
            if (!nextSpeaker().filter(seat::equals).isPresent()) {
                throw new IllegalStateException("not " + seat + "'s turn (next: " + nextSpeaker().orElse("nobody, the phase is over") + ")");
            }
            if (move == Move.DONE) {
                done.put(seat, true);
            } else {
                messages.merge(seat, 1, Integer::sum);
            }
            turn++;
            cursor = (order.indexOf(seat) + 1) % order.size();
        }

        /**
         * Number of calls so far, done turns included: the 0-based index of the next call, for the draw key t&lt;turn&gt;.
         * A done call is a call but not a chat entry, so the position in the chat is the number of messages instead.
         */
        public int turn() {
            return turn;
        }

        public int messages(String seat) {
            return messages.getOrDefault(seat, 0);
        }

        public boolean isDone(String seat) {
            return done.getOrDefault(seat, false);
        }

        public End endReason() {
            if (nextSpeaker().isPresent()) {
                return End.ACTIVE;
            }
            return order.stream().allMatch(this::isDone) ? End.ALL_DONE : End.CAP;
        }
    }
}
