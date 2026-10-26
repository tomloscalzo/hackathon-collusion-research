package io.github.tomloscalzo.collusion.texts;

import java.util.ArrayList;
import java.util.Collection;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Which texts a trial's seats get, and what each seat, call type and slot resolves to (C11.1). Built from the grid's
 * {@code condition_texts} cell (seat:name;seat:name, seat "all" = every LLM seat) plus any option-chosen texts (a
 * round reminder, a quote instruction, a question), against a roster of seat ids. Construction checks that every name
 * exists, every named seat is in the roster, and no seat has two texts in a single-valued slot. A text is used only in the
 * call types its slot allows ({@link Slot#defaultCalls}; ROUND_NOTES can be changed with the four-argument {@code of}).
 * Resolving gives "" when the seat has no text there. Texts may hold {{NAME}} placeholders, filled from the values given
 * to {@link #resolve}; TALK_RULES also fills {{TALK_NOTICE}} from the seat's own notice. A placeholder left unfilled is an
 * error. Pure and deterministic; nothing here changes any existing prompt.
 */
public final class TextPlan {
    public static final String ALL = "all";
    private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\{([A-Z_0-9]+)}}");

    /** A text name and the seat it applies to (a seat id, or {@link #ALL}). */
    public record Assignment(String seat, String name) {}

    private final TextLibrary library;
    private final List<Assignment> assignments;
    private final Set<CallType> roundNotesCalls;

    private TextPlan(TextLibrary library, List<Assignment> assignments, Set<CallType> roundNotesCalls) {
        this.library = library;
        this.assignments = List.copyOf(assignments);
        this.roundNotesCalls = roundNotesCalls;
    }

    /** Parses the grid cell "seat:name;seat:name" (empty = no assignments). */
    public static List<Assignment> parseCell(String cell) {
        List<Assignment> out = new ArrayList<>();
        if (cell == null || cell.isBlank()) {
            return out;
        }
        for (String part : cell.split(";")) {
            int i = part.indexOf(':');
            if (i <= 0 || i == part.length() - 1) {
                throw new IllegalArgumentException("condition_texts entry '" + part + "' is not seat:name");
            }
            out.add(new Assignment(part.substring(0, i).strip(), part.substring(i + 1).strip()));
        }
        return out;
    }

    public static TextPlan of(TextLibrary library, Collection<String> roster, List<Assignment> assignments) {
        return of(library, roster, assignments, Slot.ROUND_NOTES.defaultCalls());
    }

    public static TextPlan of(TextLibrary library, Collection<String> roster, List<Assignment> assignments,
                              Set<CallType> roundNotesCalls) {
        Objects.requireNonNull(library, "library");
        Objects.requireNonNull(roundNotesCalls, "roundNotesCalls");
        Map<String, List<SeatText>> perSeatSlot = new HashMap<>();
        for (Assignment a : assignments) {
            SeatText t = library.get(a.name());
            if (!ALL.equals(a.seat()) && !roster.contains(a.seat())) {
                throw new IllegalArgumentException("text '" + a.name() + "' is for seat '" + a.seat() + "', not in the roster " + roster);
            }
            for (String seat : roster) {
                if (ALL.equals(a.seat()) || seat.equals(a.seat())) {
                    List<SeatText> l = perSeatSlot.computeIfAbsent(seat + "|" + t.slot(), k -> new ArrayList<>());
                    if (l.contains(t)) {
                        throw new IllegalArgumentException("seat '" + seat + "' gets text '" + t.name() + "' twice");
                    }
                    if (!l.isEmpty() && !t.slot().allowsMultiple()) {
                        throw new IllegalArgumentException("seat '" + seat + "' has two texts for " + t.slot() + ": '"
                                + l.get(0).name() + "' and '" + t.name() + "'");
                    }
                    l.add(t);
                }
            }
        }
        Set<CallType> calls = EnumSet.noneOf(CallType.class);
        calls.addAll(roundNotesCalls);
        return new TextPlan(library, assignments, calls);
    }

    /** The texts of this seat in the slot, in assignment order (no call type filter). */
    public List<SeatText> texts(Slot slot, String seat) {
        List<SeatText> out = new ArrayList<>();
        for (Assignment a : assignments) {
            SeatText t = library.get(a.name());
            if (t.slot() == slot && (ALL.equals(a.seat()) || a.seat().equals(seat))) {
                out.add(t);
            }
        }
        return out;
    }

    /** True when the slot is used in this call type. */
    public boolean appliesTo(Slot slot, CallType call) {
        return slot == Slot.ROUND_NOTES ? roundNotesCalls.contains(call) : slot.defaultCalls().contains(call);
    }

    /** The text for this seat, slot and call type, or "" (several texts in one slot are joined with a line break). */
    public String resolve(Slot slot, String seat, CallType call, Map<String, String> values) {
        if (!appliesTo(slot, call)) {
            return "";
        }
        List<String> parts = new ArrayList<>();
        for (SeatText t : texts(slot, seat)) {
            String s = t.text();
            if (slot == Slot.TALK_RULES) {
                s = s.replace("{{TALK_NOTICE}}", resolve(Slot.TALK_NOTICE, seat, call, values)).strip();
            }
            s = fill(t.name(), s, values);
            s = s.strip();
            if (!s.isEmpty()) {
                parts.add(s);
            }
        }
        return String.join("\n", parts);
    }

    private static String fill(String name, String text, Map<String, String> values) {
        Matcher m = PLACEHOLDER.matcher(text);
        StringBuilder b = new StringBuilder();
        while (m.find()) {
            String v = values.get(m.group(1));
            if (v == null) {
                throw new IllegalStateException("text '" + name + "': no value for placeholder {{" + m.group(1) + "}}");
            }
            m.appendReplacement(b, Matcher.quoteReplacement(v));
        }
        m.appendTail(b);
        return b.toString();
    }

    public TextLibrary library() { return library; }

    public List<Assignment> assignments() { return assignments; }
}
