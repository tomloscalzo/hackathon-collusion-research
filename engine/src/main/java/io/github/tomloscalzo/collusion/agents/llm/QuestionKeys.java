package io.github.tomloscalzo.collusion.agents.llm;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Draw keys of the introspection question calls (C13.1; interface proposal v5, D3 and F):
 * {@code question|<name>|<fed|post>|<scenario>|s<seed>|<seat>|r<round>|a0}. "fed" is the in-game question whose answer is
 * shown back to its own seat; "post" is the post-game pass, whose answers are never fed back. The name and mode sit at
 * fixed places and the prefix is "question", which no other call uses (game, probe, vig, talk), so a question key never
 * equals, and never changes, a {@code game|...} key: the game keys are built elsewhere and are not touched. Each
 * (question, mode, seat, round) has its own key. The attempt is always 0 (questions are not retried). Pure.
 */
public final class QuestionKeys {
    /** Which kind of question call a key belongs to. */
    public enum Mode {
        FED, POST;

        public String tag() { return name().toLowerCase(java.util.Locale.ROOT); }

        public static Mode ofTag(String tag) {
            for (Mode m : values()) {
                if (m.tag().equals(tag)) {
                    return m;
                }
            }
            throw new IllegalArgumentException("question mode must be fed or post: '" + tag + "'");
        }
    }

    /** The parts of a question key. */
    public record Parts(String name, Mode mode, String scenario, long seed, String seat, int round) {}

    public static final String PREFIX = "question";
    private static final Pattern NAME = Pattern.compile("[A-Za-z0-9][A-Za-z0-9_.-]*");
    private static final Pattern KEY = Pattern.compile(
            "question\\|([^|]+)\\|(fed|post)\\|([^|]+)\\|s(-?\\d+)\\|([^|]+)\\|r(\\d+)\\|a0");

    private QuestionKeys() {}

    public static String key(String name, Mode mode, String scenario, long seed, String seat, int round) {
        if (!validName(name)) {
            throw new IllegalArgumentException("question name must be letters, digits, _ . - : '" + name + "'");
        }
        if (mode == null) {
            throw new IllegalArgumentException("question mode is required");
        }
        noBar("scenario", scenario);
        noBar("seat", seat);
        if (round < 1) {
            throw new IllegalArgumentException("round must be at least 1: " + round);
        }
        return PREFIX + "|" + name + "|" + mode.tag() + "|" + scenario + "|s" + seed + "|" + seat + "|r" + round + "|a0";
    }

    /** Reads a question key back; throws for any other string (a game, talk or probe key included). */
    public static Parts parse(String key) {
        Matcher m = KEY.matcher(key == null ? "" : key);
        if (!m.matches()) {
            throw new IllegalArgumentException("not a question draw key: '" + key + "'");
        }
        return new Parts(m.group(1), Mode.ofTag(m.group(2)), m.group(3), Long.parseLong(m.group(4)), m.group(5),
                Integer.parseInt(m.group(6)));
    }

    /** True for a name a key can carry: letters, digits, underscore, dot and hyphen, starting with a letter or digit. */
    public static boolean validName(String name) {
        return name != null && NAME.matcher(name).matches();
    }

    public static boolean isQuestionKey(String key) {
        return key != null && key.startsWith(PREFIX + "|");
    }

    private static void noBar(String what, String v) {
        if (v == null || v.isEmpty() || v.indexOf('|') >= 0) {
            throw new IllegalArgumentException(what + " must be non-empty and contain no '|': '" + v + "'");
        }
    }
}
