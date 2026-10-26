package io.github.tomloscalzo.collusion.texts;

import java.util.List;
import java.util.Objects;

/**
 * One named text of the text data file (CONTRACTS.md): {name, slot, text, placebo_for?, about_rule?, true_statement?, role_play?}.
 * rolePlay marks a text that states a made-up situation as a role-play (disclosed in the ethics appendix; not an untrue statement of the experiment's facts).
 * ownerApprovedIdleNotice (owner_approved_idle_notice; unit M2/W2) marks an untrue idle watchdog text the owner approved by name; only then may a QUESTION text be untrue.
 * The text may be empty (a blank control). trueStatement is false only on the one untrue notice (not-monitored).
 */
public record SeatText(String name, Slot slot, String text, List<String> placeboFor, boolean aboutRule, boolean trueStatement,
                       boolean rolePlay, boolean ownerApprovedIdleNotice) {
    public SeatText {
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(slot, "slot");
        Objects.requireNonNull(text, "text");
        placeboFor = List.copyOf(placeboFor);
    }
}
