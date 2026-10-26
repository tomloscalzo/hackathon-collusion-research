package io.github.tomloscalzo.collusion.agents.llm;

import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Random;
import java.util.TreeSet;

/**
 * What one seat may see (C3.1; interface proposal v5, A2 and A6): its own id, the neutral display labels M2, M3, ... of
 * the other seats (the seat itself is "you" and never has a label), and its own question answers, of which only the
 * last {@link #ANSWER_WINDOW} are shown. Nothing here holds another seat's plan, rationale, answer or reasoning: each
 * seat has its own view, and {@link #ownObservation} refuses an observation made for another seat.
 *
 * <p>{@link #sorted} gives exactly today's labels ({@link PromptBuilder#counterpartLabels}: rival ids sorted), so a
 * one-seat game renders byte-identically. {@link #seeded} lets the run seed set the labels (gotcha 5), from a stream
 * named "labels:&lt;seat&gt;" that the engine never draws from, so no engine stream moves.
 *
 * <p>Not yet used by the game loop: C3.2 wires it behind the {@code multiSeat} switch. Not thread safe.
 */
public final class SeatView {
    /** At most this many of the seat's own answers are shown in its later prompts (owner decision 4). */
    public static final int ANSWER_WINDOW = 10;

    /** One of the seat's own answers: asked after round {@code round} (1-based). */
    public record Answer(int round, String question, String answer) {
        public Answer {
            Objects.requireNonNull(question, "question");
            Objects.requireNonNull(answer, "answer");
        }
    }

    private final String seatId;
    private final List<String> rivalIds;
    private final Map<String, String> labels;
    private final List<Answer> answers = new ArrayList<>();

    private SeatView(String seatId, List<String> rivalIds, List<String> labelOrder) {
        this.seatId = seatId;
        this.rivalIds = List.copyOf(rivalIds);
        Map<String, String> m = new LinkedHashMap<>();
        int i = 2;
        for (String id : labelOrder) {
            m.put(id, "M" + i++);
        }
        this.labels = Collections.unmodifiableMap(m);
    }

    private SeatView(String seatId, List<String> rivalIds, Map<String, String> labels) {
        this.seatId = seatId;
        this.rivalIds = List.copyOf(rivalIds);
        this.labels = Collections.unmodifiableMap(new LinkedHashMap<>(labels));
    }

    /**
     * The game's one label assignment (C5.5, coordinator decision on gotcha 5): the run seed orders the whole roster
     * (stream "labels", which the engine never draws from) and labels it M1, M2, ... ; every reader sees each other seat
     * under that same label, and itself as "you" (its own label is never shown). So "M3" names the same firm in every
     * seat's prompts and chat. {@link #labels()} is in label order ({@link #rivalIds()} stays in roster order). With N firms a seat sees N - 1 of the labels M1..MN.
     */
    public static SeatView shared(String seatId, Collection<String> rosterIds, long runSeed) {
        List<String> rivals = rivals(seatId, rosterIds);
        Map<String, String> labels = new LinkedHashMap<>();
        gameLabels(rosterIds, runSeed).forEach((id, label) -> {
            if (!id.equals(seatId)) {
                labels.put(id, label);
            }
        });
        return new SeatView(seatId, rivals, labels);
    }

    /** Every seat's label in the game's one assignment ({@link #shared}), in label order (M1 first). */
    public static Map<String, String> gameLabels(Collection<String> rosterIds, long runSeed) {
        if (new TreeSet<>(rosterIds).size() != rosterIds.size()) {
            throw new IllegalArgumentException("duplicate seat id in the roster " + rosterIds);
        }
        List<String> order = new ArrayList<>(new TreeSet<>(rosterIds));
        Collections.shuffle(order, new Random(new SeedPolicy(runSeed).streamSeed("labels")));
        Map<String, String> out = new LinkedHashMap<>();
        for (int i = 0; i < order.size(); i++) {
            out.put(order.get(i), "M" + (i + 1));
        }
        return Collections.unmodifiableMap(out);
    }

    /** Today's labels: the other seats' ids sorted, labelled M2, M3, ... (byte-identical to counterpartLabels). */
    public static SeatView sorted(String seatId, Collection<String> rosterIds) {
        List<String> rivals = rivals(seatId, rosterIds);
        return new SeatView(seatId, rivals, new ArrayList<>(new TreeSet<>(rivals)));
    }

    /**
     * Labels in an order drawn from the run seed and this seat's id; the roster order does not matter. Per reader, so
     * one label may name different firms for different readers: the game uses {@link #shared} since C5.5.
     */
    public static SeatView seeded(String seatId, Collection<String> rosterIds, long runSeed) {
        List<String> rivals = rivals(seatId, rosterIds);
        List<String> order = new ArrayList<>(new TreeSet<>(rivals));
        Collections.shuffle(order, new Random(new SeedPolicy(runSeed).streamSeed("labels:" + seatId)));
        return new SeatView(seatId, rivals, order);
    }

    private static List<String> rivals(String seatId, Collection<String> rosterIds) {
        Objects.requireNonNull(seatId, "seatId");
        if (new TreeSet<>(rosterIds).size() != rosterIds.size()) {
            throw new IllegalArgumentException("duplicate seat id in the roster " + rosterIds);
        }
        if (!rosterIds.contains(seatId)) {
            throw new IllegalArgumentException("no seat '" + seatId + "' in the roster " + rosterIds);
        }
        List<String> out = new ArrayList<>(rosterIds);
        out.remove(seatId);
        if (out.isEmpty()) {
            throw new IllegalArgumentException("seat '" + seatId + "' has no other seat");
        }
        return out;
    }

    public String seatId() { return seatId; }

    /** The other seats' ids, in roster order. */
    public List<String> rivalIds() { return rivalIds; }

    /** Rival id to display label, in label order (M2 first; with {@link #shared}, the lowest rival label first). Unmodifiable. */
    public Map<String, String> labels() { return labels; }

    /** The display label of another seat; the seat itself and unknown ids have none. */
    public String label(String rivalId) {
        String l = labels.get(rivalId);
        if (l == null) {
            throw new IllegalArgumentException("seat '" + seatId + "' has no label for '" + rivalId + "'");
        }
        return l;
    }

    /**
     * Returns obs unchanged when it was made for this seat and every quote it shows belongs to one of this seat's rivals;
     * otherwise throws, so a view can never render another seat's observation.
     */
    public Observation ownObservation(Observation obs) {
        if (!seatId.equals(obs.selfId())) {
            throw new IllegalArgumentException("observation of '" + obs.selfId() + "' given to seat '" + seatId + "'");
        }
        for (Observation.PastRound pr : obs.history()) {
            for (String id : pr.rivalQuotes().keySet()) {
                if (!labels.containsKey(id)) {
                    throw new IllegalArgumentException("round " + pr.round() + " shows a quote of '" + id
                            + "', which is not a rival of seat '" + seatId + "'");
                }
            }
        }
        return obs;
    }

    /** Stores one of this seat's own answers; rounds must not go backwards (several answers per round are allowed). */
    public void recordAnswer(int round, String question, String answer) {
        if (round < 1) {
            throw new IllegalArgumentException("round must be at least 1: " + round);
        }
        if (!answers.isEmpty() && round < answers.get(answers.size() - 1).round()) {
            throw new IllegalArgumentException("answer for round " + round + " after one for round "
                    + answers.get(answers.size() - 1).round());
        }
        answers.add(new Answer(round, question, answer));
    }

    /** The last {@link #ANSWER_WINDOW} answers, oldest first (empty before the first one). Unmodifiable. */
    public List<Answer> recentAnswers() {
        return List.copyOf(answers.subList(Math.max(0, answers.size() - ANSWER_WINDOW), answers.size()));
    }
}
