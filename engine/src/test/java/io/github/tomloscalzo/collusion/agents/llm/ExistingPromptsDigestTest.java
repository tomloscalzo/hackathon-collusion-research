package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Byte-freeze of every prompt rendered under the elicitation values that existed before COMPETITIVE_STRICT
 * (SPONTANEOUS, E1, E2, COMPETITIVE), crossed with label, guardrail and notice, for all 12 paraphrases: game system
 * prompt, game turn and vignette. The digest was computed on main at 3c9979f, before COMPETITIVE_STRICT was added, so
 * adding a new elicitation value must leave it unchanged.
 */
class ExistingPromptsDigestTest {
    static final String MAIN_DIGEST = "d7ef2874e7be39720f1e56f437886bd00e3b0071e165e3f95966c675467a5028";

    static String digest() throws Exception {
        GameContext ctx = GameContext.of(PromptTest.cfg(), "llm");
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        for (String e : List.of("SPONTANEOUS", "E1", "E2", "COMPETITIVE")) {
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
    void existingElicitationPromptsAreByteIdenticalToMain() throws Exception {
        assertThat(digest()).isEqualTo(MAIN_DIGEST);
    }
}
