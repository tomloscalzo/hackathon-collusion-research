package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.agents.llm.PayoffExamplesTest;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Unit N1: option payoff_examples from the command line: validated, rendered, recorded in params.json and run.jsonl, replayed. */
class PayoffExamplesCliTest {
    @Test
    void neutralIsRenderedRecordedAndReplays(@TempDir Path dir) throws Exception {
        List<MockLlmServer.MockRequest> reqs = TextSlotsCliTest.run(dir, "n", "options", "{\"payoff_examples\":\"neutral\"}");
        assertThat(reqs).isNotEmpty();
        String undercut = PayoffExamplesTest.NEUTRAL_3.split("\n")[1];
        assertThat(reqs).allSatisfy(r -> assertThat(r.system()).contains(undercut).doesNotContain("x = 2.09"));
        JsonNode p = Canonical.MAPPER.readTree(Files.readString(dir.resolve("n").resolve("params.json")));
        assertThat(p.get("payoff_examples").asText()).isEqualTo("neutral");
        Path out = dir.resolve("n.jsonl");
        JsonNode llm = Canonical.MAPPER.readTree(Files.readAllLines(out).get(0)).get("llm");
        assertThat(llm.get("options").asText()).isEqualTo("{\"payoff_examples\":\"neutral\"}");
        assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
    }

    @Test
    void formulaAndNoneAreRenderedRecordedAndPrintNoExamplePrices(@TempDir Path dir) throws Exception {
        for (String v : List.of("formula", "none")) {
            List<MockLlmServer.MockRequest> reqs = TextSlotsCliTest.run(dir, v, "options", "{\"payoff_examples\":\"" + v + "\"}");
            assertThat(reqs).isNotEmpty();
            String expect = v.equals("formula") ? PayoffExamplesTest.FORMULA_3 : PayoffExamplesTest.NONE_PAYOFFS;
            assertThat(reqs).allSatisfy(r -> {
                assertThat(r.system()).contains(expect).doesNotContain("x = 2.09").doesNotContain("you earn");
                PayoffExamplesTest.assertNoQuoteLevels(r.system());
            });
            PayoffExamplesTest.assertNoQuoteLevels(reqs.get(0).lastUser());
            JsonNode p = Canonical.MAPPER.readTree(Files.readString(dir.resolve(v).resolve("params.json")));
            assertThat(p.get("payoff_examples").asText()).isEqualTo(v);
            Path out = dir.resolve(v + ".jsonl");
            assertThat(LlmCommands.replay(TrialDirCliTest.o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
        }
    }

    @Test
    void anchoredAndAbsentGiveTheSameBodiesAndNoParamsKey(@TempDir Path dir) throws Exception {
        List<String> plain = TextSlotsCliTest.run(dir, "a").stream().map(MockLlmServer.MockRequest::rawBody).toList();
        List<String> anchored = TextSlotsCliTest.run(dir, "b", "options", "{\"payoff_examples\":\"anchored\"}").stream()
                .map(MockLlmServer.MockRequest::rawBody).toList();
        assertThat(anchored).isEqualTo(plain);
        assertThat(plain).anySatisfy(b -> assertThat(b).contains("x = 2.09"));
        for (String n : List.of("a", "b")) {
            assertThat(Canonical.MAPPER.readTree(Files.readString(dir.resolve(n).resolve("params.json"))).has("payoff_examples"))
                    .isFalse();
        }
    }

    @Test
    void anInvalidValueIsRefused(@TempDir Path dir) {
        for (String v : List.of("\"fancy\"", "1", "true", "null", "\"\"")) {
            assertThatThrownBy(() -> TextSlotsCliTest.run(dir, "x" + v.hashCode(), "options", "{\"payoff_examples\":" + v + "}"))
                    .as(v).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("payoff_examples");
        }
    }
}
