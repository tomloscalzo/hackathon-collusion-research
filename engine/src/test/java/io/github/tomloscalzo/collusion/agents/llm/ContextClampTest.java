package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.llm.LlmRequest;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Unit U2: the arithmetic of the context clamp (estimate, lowering, skipping, validation). */
class ContextClampTest {
    static LlmRequest req(int systemChars, int userChars, int maxTokens) {
        return new LlmRequest("p", "m", "s".repeat(systemChars), List.of(new LlmRequest.Turn("user", "u".repeat(userChars))),
                0.7, maxTokens, "{}", "key|1", true, 0.9, 20);
    }

    static ContextClamp clamp() {
        return new ContextClamp(1000, 100, 200, 3.0, "t1", "arm");
    }

    @Test
    void theEstimateIsConservativeCharactersOverThreePlusOverheads() {
        // 300 + 600 chars = 900 / 3 = 300, + 16 base + 8 * (1 + 1 turn) = 332
        assertThat(clamp().estimate(req(300, 600, 10))).isEqualTo(332);
        assertThat(clamp().estimate(req(301, 600, 10))).isEqualTo(333); // rounds up
    }

    @Test
    void aCallThatFitsIsUntouched() {
        LlmRequest r = req(300, 600, 568); // 332 + 568 = 900 = window - margin
        ContextClamp.Result c = clamp().apply(r, "quote", 0);
        assertThat(c.info()).isNull();
        assertThat(c.req()).isSameAs(r);
        assertThat(c.skipped()).isFalse();
    }

    @Test
    void aCallOverTheLimitIsLoweredToFitAndNothingElseChanges() {
        LlmRequest r = req(300, 600, 569); // one over
        ContextClamp.Result c = clamp().apply(r, "talk", 1);
        assertThat(c.skipped()).isFalse();
        assertThat(c.req().maxTokens()).isEqualTo(568);
        assertThat(c.req()).isEqualTo(new LlmRequest(r.provider(), r.modelSnapshot(), r.system(), r.turns(), r.temperature(), 568,
                r.responseSchema(), r.drawKey(), r.thinking(), r.topP(), r.topK()));
        assertThat(c.info()).isEqualTo(new ContextClamp.Info("talk", 1, 332, 569, 568, false, 1000, 100, 200));
        assertThat(c.info().estPromptTokens() + c.req().maxTokens()).isLessThanOrEqualTo(1000 - 100);
    }

    @Test
    void fewerThanTheMinimumLeftMeansTheCallIsSkipped() {
        // room = 900 - estimate; an estimate of 700 leaves 200 (= min, sent), 701 leaves 199 (skipped)
        ContextClamp at = clamp();
        int chars = (700 - 16 - 16) * 3; // estimate 700
        assertThat(at.estimate(req(0, chars, 5000))).isEqualTo(700);
        ContextClamp.Result sent = at.apply(req(0, chars, 5000), "quote", 0);
        assertThat(sent.skipped()).isFalse();
        assertThat(sent.req().maxTokens()).isEqualTo(200);
        ContextClamp.Result skipped = at.apply(req(0, chars + 3, 5000), "quote", 1);
        assertThat(skipped.skipped()).isTrue();
        assertThat(skipped.info().grantedMaxTokens()).isZero();
        assertThat(skipped.info().requestedMaxTokens()).isEqualTo(5000);
        assertThat(skipped.info().attempt()).isEqualTo(1);
    }

    @Test
    void theMinimumIsRelativeToTheRequestedMaxTokens() {
        // U22: skip only when room < min(minTokens, requested). Default min 1024, window 16384, margin 256.
        ContextClamp d = ContextClamp.of("t", "a");
        for (int room : new int[] {0, 1, 200, 399}) { // thinking-off call requesting 400
            LlmRequest r = req(0, (16384 - 256 - room - 16 - 16) * 3, 400);
            assertThat(d.estimate(r)).isEqualTo(16384 - 256 - room);
            ContextClamp.Result c = d.apply(r, "quote", 0);
            assertThat(c.skipped()).as("room " + room).isTrue();
            assertThat(c.info().grantedMaxTokens()).isZero();
        }
        for (int room : new int[] {400, 401}) { // room >= requested: fits, untouched
            ContextClamp.Result c = d.apply(req(0, (16384 - 256 - room - 16 - 16) * 3, 400), "quote", 0);
            assertThat(c.skipped()).isFalse();
            assertThat(c.info()).isNull();
        }
        // requested 500: room 499 skipped; room 500 fits
        assertThat(d.apply(req(0, (16384 - 256 - 499 - 32) * 3, 500), "quote", 0).skipped()).isTrue();
        assertThat(d.apply(req(0, (16384 - 256 - 500 - 32) * 3, 500), "quote", 0).info()).isNull();
    }

    @Test
    void aLargeRequestStillUsesTheConfiguredMinimum() {
        ContextClamp d = ContextClamp.of("t", "a"); // min 1024
        ContextClamp.Result low = d.apply(req(0, (16384 - 256 - 1023 - 32) * 3, 8192), "quote", 0);
        assertThat(low.skipped()).isTrue(); // room 1023 < min(1024, 8192)
        ContextClamp.Result ok = d.apply(req(0, (16384 - 256 - 1024 - 32) * 3, 8192), "quote", 0);
        assertThat(ok.skipped()).isFalse();
        assertThat(ok.req().maxTokens()).isEqualTo(1024); // granted = min(requested, room)
        assertThat(ok.info().requestedMaxTokens()).isEqualTo(8192);
        assertThat(ok.info().minTokens()).isEqualTo(1024);
    }

    @Test
    void settingsAreValidated() {
        assertThatThrownBy(() -> new ContextClamp(1000, 800, 200, 3.0, "t", "a")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ContextClamp(1000, 100, 0, 3.0, "t", "a")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ContextClamp(1000, 100, 200, 0.0, "t", "a")).isInstanceOf(IllegalArgumentException.class);
        ContextClamp d = ContextClamp.of("t", "a");
        assertThat(d.window()).isEqualTo(16384);
        assertThat(d.minTokens()).isEqualTo(1024);
    }

    @Test
    void theFieldNamesOfTheRecords() {
        ContextClamp.Info i = new ContextClamp.Info("quote", 0, 5, 6, 7, false, 8, 9, 10);
        assertThat(i.toEventFields("t", "a", "k").keySet()).containsExactly("trial", "arm", "call_type", "attempt",
                "est_prompt_tokens", "requested_max_tokens", "granted_max_tokens", "skipped", "window", "margin", "min_tokens",
                "draw_key");
        assertThat(i.toRecord().keySet()).containsExactly("callType", "attempt", "estPromptTokens", "requestedMaxTokens",
                "grantedMaxTokens", "skipped", "window", "margin", "minTokens");
    }
}
