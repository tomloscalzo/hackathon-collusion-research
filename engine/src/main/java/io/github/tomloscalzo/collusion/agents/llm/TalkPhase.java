package io.github.tomloscalzo.collusion.agents.llm;

import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.talk.TalkScheduler;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Consumer;

/**
 * The talk phase of a chat arm (C5.5; scope 4.2, proposal A3, A4): before the quotes of every round the LLM seats talk in
 * one chat, in the order of a {@link TalkScheduler} seeded by the run seed (first speaker rotating by round), each with at
 * most 7 messages of at most 150 words ({@code WordCap}, the cut marked), until every seat is done or at its cap. A done,
 * a refusal or an unreadable reply after the repair is "done" for the rest of the round (decision 5).
 *
 * <p>Every seat reads the same chat under the game's one label assignment ({@link SeatView#shared}): another seat's
 * messages appear under its label, its own as "You". The conversation block holds the previous round's chat in full and
 * this round's (gotcha 1: no older rounds). Each message is quoted on one line (line breaks become spaces), so text inside
 * a message can never look like another speaker's line (gotcha 8).
 */
public final class TalkPhase {
    /** One chat entry: text is the message as delivered, or null for "done". */
    public record Entry(String seat, String text) {}

    private final TalkScheduler scheduler;
    private final Map<String, String> labels;
    private final Map<String, LlmAgent> agents = new LinkedHashMap<>();
    private final Map<Integer, List<Entry>> chats = new HashMap<>();
    private Consumer<LlmAgent.TalkTurn> listener = t -> { };

    /** llmSeats in roster order; labels = every seat's label in the game ({@link SeatView#gameLabels}). */
    public TalkPhase(List<String> llmSeats, long runSeed, Map<String, String> labels) {
        if (llmSeats.size() < 2) {
            throw new IllegalArgumentException("the talk phase needs at least two LLM seats: " + llmSeats);
        }
        this.scheduler = new TalkScheduler(llmSeats, runSeed);
        this.labels = Map.copyOf(labels);
        for (String s : llmSeats) {
            if (!labels.containsKey(s)) {
                throw new IllegalArgumentException("no label for seat " + s);
            }
        }
    }

    public TalkScheduler scheduler() {
        return scheduler;
    }

    void register(String seat, LlmAgent agent) {
        if (!scheduler.order().contains(seat)) {
            throw new IllegalArgumentException("not a talking seat: " + seat);
        }
        agents.put(seat, agent);
    }

    /** Called with every finished talk turn, in order (C5.6 logs it). */
    public TalkPhase onTurn(Consumer<LlmAgent.TalkTurn> l) {
        this.listener = l;
        return this;
    }

    /** One round's talk; obs = every seat's observation of the round (Game.beforeDecisions), roster order. */
    public void run(List<Observation> obs) {
        int round = obs.get(0).round();
        Map<String, Observation> bySeat = new HashMap<>();
        obs.forEach(o -> bySeat.put(o.selfId(), o));
        List<Entry> log = new ArrayList<>();
        chats.put(round, log);
        chats.remove(round - 2);
        TalkScheduler.Round rr = scheduler.round(round);
        for (Optional<String> next = rr.nextSpeaker(); next.isPresent(); next = rr.nextSpeaker()) {
            String seat = next.get();
            LlmAgent a = agents.get(seat);
            if (a == null) {
                throw new IllegalStateException("talking seat " + seat + " has no agent");
            }
            LlmAgent.TalkTurn t = a.talk(bySeat.get(seat), rr.turn(), rr.messages(seat));
            rr.record(seat, t.done() ? TalkScheduler.Move.DONE : TalkScheduler.Move.MESSAGE);
            log.add(new Entry(seat, t.delivered()));
            listener.accept(t);
        }
    }

    /** The round's chat so far (empty before it starts). */
    public List<Entry> chat(int round) {
        return List.copyOf(chats.getOrDefault(round, List.of()));
    }

    /**
     * The CONVERSATION block for reader in round: the previous round's chat in full (from round 2 on), then this round's,
     * "so far" in a talk turn and complete in the quote turn.
     */
    public String conversation(String reader, int round, boolean quoteTurn) {
        List<String> parts = new ArrayList<>();
        if (round > 1) {
            parts.add("Conversation in round " + (round - 1) + ":\n" + lines(reader, chat(round - 1)));
        }
        parts.add("Conversation in round " + round + (quoteTurn ? ":" : " so far:") + "\n" + lines(reader, chat(round)));
        return String.join("\n\n", parts);
    }

    private String lines(String reader, List<Entry> chat) {
        if (chat.isEmpty()) {
            return "(no messages yet)";
        }
        List<String> out = new ArrayList<>();
        for (Entry e : chat) {
            String who = e.seat().equals(reader) ? "You" : labels.get(e.seat());
            out.add(who + ": " + (e.text() == null ? "[done]" : "\"" + oneLine(e.text()) + "\""));
        }
        return String.join("\n", out);
    }

    static String oneLine(String text) {
        return text.strip().replaceAll("(?U)\\s+", " "); // Unicode whitespace too (U+2028 is a line break)
    }
}
