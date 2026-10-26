package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

/** C3.4: the Track M system templates (prompts/game_system_m.json) are neutral about the number of firms (proposal A1). */
class NeutralTemplatesTest {
    private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\{([A-Z_]+)}}");
    /** The frozen set of game_system plus the proposal's A1, A3 and A5 additions. */
    private static final Set<String> ALLOWED = Set.of("ELICITATION", "GRID", "PAYOFFS", "PARTNER_RULE", "AUDIT", "CONTINUATION",
            "CONDITION_NOTES", "FORMAT", "RIVALS", "TALK_RULES", "SEAT_NOTES");
    private static final Set<String> REQUIRED = Set.of("ELICITATION", "GRID", "PAYOFFS", "PARTNER_RULE", "AUDIT", "CONTINUATION",
            "CONDITION_NOTES", "FORMAT", "RIVALS", "TALK_RULES", "SEAT_NOTES");
    private static final List<String> CAP_LEAKS = List.of("40 rounds", "round 40", "maxRounds", "at most 40", "hard cap");
    private static final List<String> FIRM_COUNT_WORDS = List.of("two-firm", "two firm", "one rival", "single rival", "one competitor",
            "only one other", "one other market maker", "second market maker", "a rival", "the rival", "duopoly", "scripted", "its own", "both firms", "the other firm");

    private static String rivals(int n) {
        return n == 2 ? "exactly one other market maker does" : (n - 1) + " other market makers do";
    }

    private static String render(String text, int n) {
        Matcher m = PLACEHOLDER.matcher(text);
        StringBuilder sb = new StringBuilder();
        while (m.find()) {
            String v = m.group(1).equals("RIVALS") ? rivals(n) : "<" + m.group(1) + ">";
            m.appendReplacement(sb, Matcher.quoteReplacement(v));
        }
        m.appendTail(sb);
        return sb.toString();
    }

    @Test
    void fileParsesWithFiveDistinctWordingsAndLeavesFrozenFilesAlone() {
        ParaphraseFile f = ParaphraseFile.load("game_system_m");
        assertThat(f.size()).isEqualTo(5);
        assertThat(f.distinctTexts()).isEqualTo(5);
        assertThat(f.items().stream().map(ParaphraseFile.Item::tone).collect(java.util.stream.Collectors.toSet()))
                .contains("plain", "cautious", "explore");
        // the frozen set stays exactly three files; game_system_m is registered beside them (C3.5)
        assertThat(ParaphraseFile.TEMPLATES).containsExactly("game_system", "game_turn", "vignette");
        assertThat(ParaphraseFile.allHashes()).containsOnlyKeys("game_system", "game_turn", "vignette", "game_system_m", "game_turn_m_tacit", "game_turn_m",
                "game_talk", "talk_rules")
                .containsEntry("game_system_m", f.sha256());
        assertThat(f.sha256()).isNotEqualTo(ParaphraseFile.load("game_system").sha256());
    }

    @Test
    void everyWordingKeepsTheSpecifiedPlaceholderSetAndRendersForTwoThreeAndFourFirms() {
        for (var item : ParaphraseFile.load("game_system_m").items()) {
            Set<String> found = new TreeSet<>();
            Matcher m = PLACEHOLDER.matcher(item.text());
            while (m.find()) {
                found.add(m.group(1));
            }
            assertThat(ALLOWED).as(item.id()).containsAll(found);
            assertThat(found).as(item.id()).containsAll(REQUIRED);
            Set<String> rendered = new HashSet<>();
            for (int n = 2; n <= 4; n++) {
                String r = render(item.text(), n);
                rendered.add(r);
                assertThat(r).as(item.id() + " N=" + n).doesNotContain("{{").doesNotContain("}}");
                assertThat(r).as(item.id() + " N=" + n).contains(rivals(n));
                for (String leak : CAP_LEAKS) {
                    assertThat(r.toLowerCase()).as(item.id() + " cap leak " + leak).doesNotContain(leak.toLowerCase());
                }
                assertThat(r).as(item.id() + " no cap number").doesNotContainPattern("\\b40\\b");
            }
            assertThat(rendered).as(item.id() + " differs by N").hasSize(3);
        }
    }

    @Test
    void noWordingHardCodesTheNumberOfFirmsOrDescribesTheRivalsKind() {
        for (var item : ParaphraseFile.load("game_system_m").items()) {
            String lower = item.text().toLowerCase();
            for (String w : FIRM_COUNT_WORDS) {
                assertThat(lower).as(item.id() + " contains '" + w + "'").doesNotContain(w.toLowerCase());
            }
            assertThat(item.text()).as(item.id()).doesNotContain("M2").doesNotContain("Harbor Point");
        }
    }
}
