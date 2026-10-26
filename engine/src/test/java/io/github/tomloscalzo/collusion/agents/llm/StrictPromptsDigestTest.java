package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Byte-freeze of every prompt rendered under COMPETITIVE_STRICT (PR #119), crossed with label, guardrail and notice,
 * for all 12 paraphrases: game system prompt, game turn and vignette. The digest was computed on main at 14af731,
 * before COMPETITIVE_MYOPIC was added, so adding a further elicitation value must leave it unchanged.
 */
class StrictPromptsDigestTest {
    static final String MAIN_DIGEST = "e5a39e52992247142018a3ece98b7d030c675972d5cb85db97deb42832ade8b5";

    static String digest() throws Exception {
        GameContext ctx = GameContext.of(PromptTest.cfg(), "llm");
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        for (String e : List.of("COMPETITIVE_STRICT")) {
            for (String l : List.of("NEUTRAL", "LEGAL")) {
                for (String g : List.of("off", "on")) {
                    for (String n : List.of("off", "on")) {
                        Condition c = Condition.parse("elicitation=" + e + ",label=" + l + ",guardrail=" + g + ",notice=" + n);
                        for (int p = 0; p < 12; p++) {
                            PromptBuilder pb = new PromptBuilder(c, p);
                            for (String s : List.of(pb.gameSystem(ctx), pb.gameTurn(ctx, PromptTest.obs(5, 4), "plan x"),
                                    pb.vignette(ctx, 0.3, java.util.Optional.empty()), c.canonical(), pb.paraphraseId())) {
                                md.update(s.getBytes(StandardCharsets.UTF_8));
                                md.update((byte) 0);
                            }
                        }
                    }
                }
            }
        }
        return HexFormat.of().formatHex(md.digest());
    }

    @Test
    void strictPromptsAreByteIdenticalToMain() throws Exception {
        assertThat(digest()).isEqualTo(MAIN_DIGEST);
    }
}
