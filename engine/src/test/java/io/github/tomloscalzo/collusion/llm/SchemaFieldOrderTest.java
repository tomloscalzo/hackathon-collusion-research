package io.github.tomloscalzo.collusion.llm;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.agents.llm.PromptBuilder;
import io.github.tomloscalzo.collusion.agents.llm.ReplyExtra;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** U21 (owner-approved): the wire order of the response-schema fields for a reply with an extra field. */
class SchemaFieldOrderTest {
    static LlmRequest req(String schema) {
        return new LlmRequest("openai-compatible", "mock-model-1", "sys", List.of(new LlmRequest.Turn("user", "hello")), 0.7, 100,
                schema, "game|x|s1|llm|r1|a0");
    }

    static List<String> wireOrder(String schema) throws Exception {
        JsonNode body = Canonical.MAPPER.readTree(OpenAiCompatibleClient.body(req(schema)));
        List<String> names = new ArrayList<>();
        body.path("response_format").path("json_schema").path("schema").path("properties").fieldNames().forEachRemaining(names::add);
        return names;
    }

    static ReplyExtra extra(String name, ReplyExtra.Kind kind, boolean last) {
        return new ReplyExtra(name, kind, 1, 5, 600, "t", "text", last);
    }

    @Test
    void theDefaultDecisionSchemaIsByteIdenticalToTheSortedCanonicalBody() throws Exception {
        String body = OpenAiCompatibleClient.body(req(PromptBuilder.DECISION_SCHEMA));
        assertThat(body).isEqualTo(Canonical.text(Canonical.MAPPER.readTree(body)));
        assertThat(wireOrder(PromptBuilder.DECISION_SCHEMA)).containsExactly("plan", "quote", "rationale");
    }

    @Test
    void otherSchemasAreByteIdenticalToTheSortedCanonicalBody() throws Exception {
        for (String s : List.of(PromptBuilder.CHOICE_SCHEMA, io.github.tomloscalzo.collusion.agents.llm.TalkParser.TALK_SCHEMA,
                "{\"type\":\"object\"}", "{\"type\":\"object\",\"properties\":{\"zz\":{},\"aa\":{}}}",
                "{\"type\":\"object\",\"properties\":{\"quote\":{},\"aa\":{}}}")) {
            String body = OpenAiCompatibleClient.body(req(s));
            assertThat(body).isEqualTo(Canonical.text(Canonical.MAPPER.readTree(body)));
        }
    }

    @Test
    void aLastScoreComesAfterTheRationaleWhateverItsName() throws Exception {
        for (String name : List.of("conflict_score", "placebo_score", "temptation_score", "aaa", "zzz")) {
            assertThat(wireOrder(extra(name, ReplyExtra.Kind.INTEGER, true).decisionSchema()))
                    .containsExactly("plan", "quote", "rationale", name);
        }
    }

    @Test
    void anAfterQuoteFieldComesRightAfterTheQuote() throws Exception {
        for (String name : List.of("confidant_answer", "public_answer")) {
            assertThat(wireOrder(extra(name, ReplyExtra.Kind.TEXT, false).decisionSchema()))
                    .containsExactly("plan", "quote", name, "rationale");
        }
    }

    @Test
    void onlyThePropertiesOrderDiffersFromTheSortedBodyAndTheRequestHashIsUnaffected() throws Exception {
        String schema = extra("conflict_score", ReplyExtra.Kind.INTEGER, true).decisionSchema();
        LlmRequest r = new LlmRequest("openai-compatible", "mock-model-1", "has \"properties\":{} inside \\ text",
                List.of(new LlmRequest.Turn("user", "hello")), 0.7, 100, schema, "game|x|s1|llm|r1|a0");
        String body = OpenAiCompatibleClient.body(r);
        String sorted = Canonical.text(Canonical.MAPPER.readTree(body));
        String sortedProps = "\"properties\":{\"conflict_score\":{\"maximum\":5,\"minimum\":1,\"type\":\"integer\"},"
                + "\"plan\":{\"type\":\"string\"},\"quote\":{\"type\":[\"number\",\"null\"]},\"rationale\":{\"type\":\"string\"}}";
        String wireProps = "\"properties\":{\"plan\":{\"type\":\"string\"},\"quote\":{\"type\":[\"number\",\"null\"]},"
                + "\"rationale\":{\"type\":\"string\"},\"conflict_score\":{\"maximum\":5,\"minimum\":1,\"type\":\"integer\"}}";
        assertThat(sorted).contains(sortedProps);
        assertThat(body).isEqualTo(sorted.replace(sortedProps, wireProps));
        assertThat(CanonicalRequest.sha256(r)).isEqualTo(Canonical.sha256(CanonicalRequest.text(r)));
        assertThat(CanonicalRequest.text(r)).doesNotContain(wireProps);
    }
}
