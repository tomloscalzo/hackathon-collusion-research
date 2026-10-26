package io.github.tomloscalzo.collusion.talk;

/**
 * The talk word cap (scope 4.2): a message over 150 words is cut after the 150th word and marked. A word is a maximal run
 * of non-whitespace characters, with Unicode whitespace (including U+00A0) separating words, so counts agree with
 * Python's str.split() as used by tools/trial/derive.py. Pure functions; nothing here knows the game, the prompts or the cache.
 */
public final class WordCap {
    public static final int MAX_WORDS = 150;
    /** Appended by {@link Capped#marked()} when a message was cut; also the text other seats may be shown. */
    public static final String MARK = "[message cut at 150 words]";

    private WordCap() {}

    /** text: the message as delivered (cut, trimmed); words: the original word count; truncated: it was cut. */
    public record Capped(String text, int words, boolean truncated) {
        /** The delivered text with the cut marked in words, for display; unchanged when not cut. */
        public String marked() {
            return truncated ? text + " " + MARK : text;
        }
    }

    public static Capped apply(String message) {
        return apply(message, MAX_WORDS);
    }

    public static Capped apply(String message, int max) {
        if (max < 1) {
            throw new IllegalArgumentException("max words must be >= 1");
        }
        if (message == null) {
            return new Capped("", 0, false);
        }
        int n = 0;
        int start = -1;
        int end = -1; // end of the last kept word
        boolean inWord = false;
        for (int i = 0; i < message.length(); i++) {
            boolean ws = isSpace(message.charAt(i));
            if (!ws && !inWord) {
                inWord = true;
                if (start < 0) {
                    start = i;
                }
                n++;
            } else if (ws && inWord) {
                inWord = false;
                if (n <= max) {
                    end = i;
                }
            }
        }
        if (inWord && n <= max) {
            end = message.length();
        }
        if (n == 0) {
            return new Capped("", 0, false);
        }
        return new Capped(message.substring(start, end), n, n > max);
    }

    public static int count(String message) {
        return apply(message, Integer.MAX_VALUE).words();
    }

    private static boolean isSpace(char c) {
        return Character.isWhitespace(c) || Character.isSpaceChar(c) || c == '\u0085';
    }
}
