package io.github.tomloscalzo.collusion.talk;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

/** C5.1: the 150-word cut and its marking (scope 4.2, gotcha 2). */
class WordCapTest {
    private static String words(int n) {
        StringBuilder sb = new StringBuilder();
        for (int i = 1; i <= n; i++) {
            sb.append(i == 1 ? "" : " ").append("w").append(i);
        }
        return sb.toString();
    }

    @Test
    void atOrUnderTheCapIsUntouched() {
        for (int n : new int[] {0, 1, 149, 150}) {
            WordCap.Capped c = WordCap.apply(words(n));
            assertThat(c.text()).isEqualTo(words(n));
            assertThat(c.truncated()).isFalse();
            assertThat(c.words()).isEqualTo(n);
            assertThat(c.marked()).isEqualTo(words(n));
        }
    }

    @Test
    void oneWordOverIsCutAndMarked() {
        WordCap.Capped c = WordCap.apply(words(151));
        assertThat(c.text()).isEqualTo(words(150));
        assertThat(c.truncated()).isTrue();
        assertThat(c.words()).isEqualTo(151);
        assertThat(c.marked()).startsWith(words(150)).endsWith(WordCap.MARK).contains(WordCap.MARK);
        assertThat(WordCap.MARK).contains("150");
    }

    @Test
    void fourHundredWordsKeepTheFirst150() {
        WordCap.Capped c = WordCap.apply(words(400));
        assertThat(c.text().split(" ")).hasSize(150);
        assertThat(c.text()).endsWith("w150");
        assertThat(c.words()).isEqualTo(400);
    }

    @Test
    void whitespaceIsKeptInsideAndTrimmedAtTheEnds() {
        String body = "a\n\nb\t c";
        WordCap.Capped c = WordCap.apply("  " + body + "  ", 10);
        assertThat(c.text()).isEqualTo(body);
        assertThat(c.truncated()).isFalse();
        WordCap.Capped cut = WordCap.apply("one\n\ntwo   three four", 2);
        assertThat(cut.text()).isEqualTo("one\n\ntwo");
        assertThat(cut.truncated()).isTrue();
    }

    @Test
    void wordCountMatchesPythonSplitIncludingNoBreakSpace() {
        // derive.py counts str.split(), which also splits on U+00A0
        assertThat(WordCap.count("a b c")).isEqualTo(3);
        assertThat(WordCap.apply("a b c", 2).text()).isEqualTo("a b");
    }

    @Test
    void everyPythonWhitespaceCharacterSeparatesWords() {
        // the characters str.split() splits on, beyond the ASCII space
        String[] seps = {"", "", "", "", "", " ", " ", " ", " ",
                " ", " ", " ", "　"};
        for (String sep : seps) {
            assertThat(WordCap.count("a" + sep + "b")).as("U+%04X", (int) sep.charAt(0)).isEqualTo(2);
        }
        assertThat(WordCap.count("a​b")).isEqualTo(1); // zero-width space is not whitespace in Python either
    }

    @Test
    void nullAndBlankAreEmpty() {
        assertThat(WordCap.apply(null).text()).isEmpty();
        assertThat(WordCap.apply("   \n ").words()).isZero();
        assertThat(WordCap.apply(null).truncated()).isFalse();
    }

    @Test
    void capMustBePositive() {
        assertThatThrownBy(() -> WordCap.apply("x", 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void defaultCapIs150() {
        assertThat(WordCap.MAX_WORDS).isEqualTo(150);
    }
}
