package io.github.tomloscalzo.collusion.texts;

import java.util.EnumSet;
import java.util.Set;

/**
 * The places a seat text can fill (interface proposal v5, A5), with the call types each appears in by default and whether a
 * seat may have more than one text in it. SEAT_NOTES and TALK_RULES are in the system prompt, so in every call; TALK_NOTICE
 * is read through TALK_RULES (and alone); ROUND_NOTES is in talk and quote turns (the plan can change that per call type);
 * QUOTE_INSTRUCTION only in the quote turn; QUESTION is the text of a question (questions.json), only in a question call;
 * REPLY_FIELD is the instruction of an optional extra quote-reply field (U8, ReplyExtra), only in the quote call.
 */
public enum Slot {
    TALK_NOTICE(EnumSet.allOf(CallType.class), false),
    TALK_RULES(EnumSet.allOf(CallType.class), false),
    SEAT_NOTES(EnumSet.allOf(CallType.class), true),
    ROUND_NOTES(EnumSet.of(CallType.TALK, CallType.QUOTE), true),
    QUOTE_INSTRUCTION(EnumSet.of(CallType.QUOTE), false),
    QUESTION(EnumSet.of(CallType.QUESTION), false),
    /** The instruction of an optional extra reply field (U8, ReplyExtra): appended to the reply-format line of the system prompt. */
    REPLY_FIELD(EnumSet.of(CallType.QUOTE), false);

    private final Set<CallType> defaultCalls;
    private final boolean multiple;

    Slot(Set<CallType> defaultCalls, boolean multiple) {
        this.defaultCalls = defaultCalls;
        this.multiple = multiple;
    }

    public Set<CallType> defaultCalls() { return defaultCalls; }

    /** True when several texts may fill the slot for one seat (they are joined with a line break, in assignment order). */
    public boolean allowsMultiple() { return multiple; }
}
