package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.MockRequest;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.function.Function;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Unit E1 (owner-approved for gpt-oss only): with --options empty_talk_as_done=on, a talk reply with no message.content (or
 * empty content) and finish_reason stop is "done, nothing more to say this round", logged as an empty_reply_as_done event.
 * Without the option nothing changes (the run fails exactly as before), and a quote call is never covered.
 */
class EmptyTalkAsDoneTest {
    static final String OPT = "{\"empty_talk_as_done\":\"on\"}";
    static final Reply MISSING = new Reply(null, null, "stop", 200, null);

    static Function<MockRequest, Reply> withEmptyTalk(Reply empty, Function<MockRequest, Reply> base) {
        return r -> TruncatedThinkingTest.isTalk(r) && r.user().contains("|llm2|r2|t1|a0") ? empty : base.apply(r);
    }

    @Test
    void anEmptyTalkReplyIsDoneWithTheOptionOn(@TempDir Path dir) throws Exception {
        for (Reply empty : List.of(MISSING, Reply.text(""))) {
            String name = empty.content() == null ? "missing" : "empty";
            TruncatedThinkingTest.Run r = TruncatedThinkingTest.run(dir, name, "scenarios/n3-group.yaml", true,
                    withEmptyTalk(empty, TruncatedThinkingTest.game(q -> Reply.text(TruncatedThinkingTest.DECISION))),
                    "thinking", "on", "options", OPT);
            // no repair call for that turn
            assertThat(r.requests()).filteredOn(q -> q.user().contains("|llm2|r2|t1|")).hasSize(1);
            List<JsonNode> done = TrialDirCliTest.events(r.trial()).stream()
                    .filter(e -> e.get("kind").asText().equals("empty_reply_as_done")).toList();
            assertThat(done).hasSize(1);
            assertThat(done.get(0).get("seat").asText()).isEqualTo("llm2");
            assertThat(done.get(0).get("round").asInt()).isEqualTo(2);
            assertThat(done.get(0).get("draw_key").asText()).contains("|llm2|r2|t1|a0").startsWith("talk|");
            assertThat(done.get(0).get("finish_reason").asText()).isEqualTo("stop");
            JsonNode talk = TrialDirCliTest.events(r.trial()).stream().filter(e -> e.get("kind").asText().equals("talk")
                    && e.get("seat").asText().equals("llm2") && e.get("round").asInt() == 2 && e.get("turn").asInt() == 1)
                    .findFirst().orElseThrow();
            assertThat(talk.get("parsed").get("done").asBoolean()).isTrue();
            assertThat(talk.get("parsed").get("message").asText()).isEmpty();
            assertThat(talk.get("outcome").asText()).isEqualTo("OK");
            assertThat(talk.has("refusal_kind")).isFalse();
            JsonNode params = io.github.tomloscalzo.collusion.results.Canonical.MAPPER.readTree(Files.readString(r.trial().resolve("params.json")));
            assertThat(params.get("empty_talk_as_done").asBoolean()).isTrue();
            // the game went on: round 3 was played by llm2
            assertThat(TruncatedThinkingTest.quoteEvent(r.trial(), "llm2", 3).get("outcome").asText()).isEqualTo("OK");
        }
    }

    @Test
    void anEmptyRepairReplyIsDoneToo(@TempDir Path dir) throws Exception {
        // the live failures: attempt 0 unreadable, the repair call (a1) answered with no content
        Function<MockRequest, Reply> base = TruncatedThinkingTest.game(q -> Reply.text(TruncatedThinkingTest.DECISION));
        Function<MockRequest, Reply> f = r -> TruncatedThinkingTest.isTalk(r) && r.user().contains("|llm2|r2|t1|a0")
                ? Reply.text("this is not json") : TruncatedThinkingTest.isTalk(r) && r.user().contains("|llm2|r2|t1|a1") ? MISSING
                : base.apply(r);
        TruncatedThinkingTest.Run r = TruncatedThinkingTest.run(dir, "repair", "scenarios/n3-group.yaml", true, f, "thinking", "on",
                "options", OPT);
        List<JsonNode> done = TrialDirCliTest.events(r.trial()).stream()
                .filter(e -> e.get("kind").asText().equals("empty_reply_as_done")).toList();
        assertThat(done).hasSize(1);
        assertThat(done.get(0).get("draw_key").asText()).endsWith("|llm2|r2|t1|a1");
        JsonNode talk = TrialDirCliTest.events(r.trial()).stream().filter(e -> e.get("kind").asText().equals("talk")
                && e.get("seat").asText().equals("llm2") && e.get("round").asInt() == 2 && e.get("turn").asInt() == 1)
                .findFirst().orElseThrow();
        assertThat(talk.get("parsed").get("done").asBoolean()).isTrue();
        assertThat(talk.get("outcome").asText()).isEqualTo("REPAIRED");
        assertThat(talk.has("imputed")).isFalse();
        assertThat(TruncatedThinkingTest.quoteEvent(r.trial(), "llm2", 3).get("outcome").asText()).isEqualTo("OK");
        // without the option the same empty repair reply still fails
        assertThatThrownBy(() -> TruncatedThinkingTest.run(dir, "repair_off", "scenarios/n3-group.yaml", true, f, "thinking", "on"))
                .isInstanceOf(LlmException.class).hasMessageContaining("no choices[0].message.content");
    }

    @Test
    void withoutTheOptionAnEmptyTalkReplyFailsAsBefore(@TempDir Path dir) {
        // the Qwen path: the option is never set, the missing content throws exactly as it always did
        assertThatThrownBy(() -> TruncatedThinkingTest.run(dir, "off", "scenarios/n3-group.yaml", true,
                withEmptyTalk(MISSING, TruncatedThinkingTest.game(q -> Reply.text(TruncatedThinkingTest.DECISION))), "thinking", "on"))
                .isInstanceOf(LlmException.class).hasMessageContaining("no choices[0].message.content");
    }

    @Test
    void optionOffIsTheSameAsAbsent(@TempDir Path dir) {
        assertThatThrownBy(() -> TruncatedThinkingTest.run(dir, "offopt", "scenarios/n3-group.yaml", true,
                withEmptyTalk(MISSING, TruncatedThinkingTest.game(q -> Reply.text(TruncatedThinkingTest.DECISION))), "thinking", "on",
                "options", "{\"empty_talk_as_done\":\"off\"}"))
                .isInstanceOf(LlmException.class).hasMessageContaining("no choices[0].message.content");
    }

    @Test
    void anEmptyQuoteReplyIsNotCoveredEvenWithTheOptionOn(@TempDir Path dir) {
        Function<MockRequest, Reply> f = r -> !TruncatedThinkingTest.isTalk(r) && r.user().contains("|llm2|r2|") ? MISSING
                : TruncatedThinkingTest.game(q -> Reply.text(TruncatedThinkingTest.DECISION)).apply(r);
        assertThatThrownBy(() -> TruncatedThinkingTest.run(dir, "quote", "scenarios/n3-group.yaml", true, f, "thinking", "on",
                "options", OPT)).isInstanceOf(LlmException.class).hasMessageContaining("no choices[0].message.content");
    }

    @Test
    void aMissingContentReplyThatDidNotStopStillFailsWithTheOptionOn(@TempDir Path dir) {
        assertThatThrownBy(() -> TruncatedThinkingTest.run(dir, "nostop", "scenarios/n3-group.yaml", true,
                withEmptyTalk(new Reply(null, null, "tool_calls", 200, null),
                        TruncatedThinkingTest.game(q -> Reply.text(TruncatedThinkingTest.DECISION))), "thinking", "on", "options", OPT))
                .isInstanceOf(LlmException.class).hasMessageContaining("no choices[0].message.content");
    }

    @Test
    void anUnknownValueIsRefused(@TempDir Path dir) {
        assertThatThrownBy(() -> TruncatedThinkingTest.run(dir, "bad", "scenarios/n3-group.yaml", true,
                TruncatedThinkingTest.game(q -> Reply.text(TruncatedThinkingTest.DECISION)), "thinking", "on",
                "options", "{\"empty_talk_as_done\":\"maybe\"}")).hasMessageContaining("empty_talk_as_done");
    }
}
