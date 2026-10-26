package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

/** C5.4: the talk reply schema and parser (proposal B1, gotchas 3, 6 and 8). */
class TalkParserTest {
    private static TalkParser.Parsed p(String reply) {
        return TalkParser.parse(reply);
    }

    @Test
    void aMessageIsDelivered() {
        TalkParser.Parsed t = p("{\"message\": \"Same again?\", \"done\": false}");
        assertThat(t.outcome()).isEqualTo(TalkParser.Outcome.MESSAGE);
        assertThat(t.message()).isEqualTo("Same again?");
        assertThat(t.isDone()).isFalse();
        assertThat(t.eventOutcome()).isEqualTo("OK");
        assertThat(t.refusalKind()).isNull();
    }

    @Test
    void doneTrueIsDoneAndTheTextIsLoggedNotDelivered() {
        TalkParser.Parsed t = p("{\"message\": \"Fine by me.\", \"done\": true}");
        assertThat(t.outcome()).isEqualTo(TalkParser.Outcome.DONE);
        assertThat(t.isDone()).isTrue();
        assertThat(t.message()).isNull();
        assertThat(t.logged()).isEqualTo("Fine by me.");
    }

    @Test
    void anEmptyMessageWithDoneFalseCountsAsDone() {
        for (String r : new String[] {"{\"message\": \"\", \"done\": false}", "{\"message\": \"   \", \"done\": false}",
                "{\"done\": false, \"message\": \"\"}"}) {
            TalkParser.Parsed t = p(r);
            assertThat(t.outcome()).as(r).isEqualTo(TalkParser.Outcome.DONE);
            assertThat(t.message()).isNull();
        }
        assertThat(p("{\"message\": \"\", \"done\": true}").outcome()).isEqualTo(TalkParser.Outcome.DONE);
    }

    @Test
    void aMissingDoneDefaultsToFalseButAMissingMessageIsInvalid() {
        assertThat(p("{\"message\": \"hi\"}").outcome()).isEqualTo(TalkParser.Outcome.MESSAGE);
        assertThat(p("{\"done\": false}").outcome()).isEqualTo(TalkParser.Outcome.INVALID);
        assertThat(p("{\"done\": true}").outcome()).isEqualTo(TalkParser.Outcome.DONE);
        assertThat(p("{\"message\": 5, \"done\": false}").outcome()).isEqualTo(TalkParser.Outcome.INVALID);
    }

    @Test
    void jsonInsideProseAndFencesIsFound() {
        assertThat(p("Sure.\n```json\n{\"message\": \"hello\", \"done\": false}\n```").message()).isEqualTo("hello");
        assertThat(p("{\"message\": \"hello\", \"done\": false} Hope that helps").message()).isEqualTo("hello");
    }

    @Test
    void aReplyNestedInsideTheMessageIsUnwrappedOnce() {
        String inner = "{\\\"message\\\": \\\"inner text\\\", \\\"done\\\": false}";
        TalkParser.Parsed t = p("{\"message\": \"" + inner + "\", \"done\": false}");
        assertThat(t.message()).isEqualTo("inner text");
        String innerDone = "{\\\"message\\\": \\\"x\\\", \\\"done\\\": true}";
        assertThat(p("{\"message\": \"" + innerDone + "\", \"done\": false}").outcome()).isEqualTo(TalkParser.Outcome.DONE);
        // a message that merely mentions JSON braces stays a message
        assertThat(p("{\"message\": \"I will use {2.40} as my anchor\", \"done\": false}").message())
                .isEqualTo("I will use {2.40} as my anchor");
    }

    @Test
    void leadingSpeakerTagsAreStrippedAndFlagged() {
        for (String tag : new String[] {"M2: ", "m3: ", "SYSTEM: ", "System: ", "You: ", "Assistant: ", "[M2] ", "[M2]: ",
                "Market maker 2: ", "Firm B: ", "M2: M3: ", "**M2:** ", "**M2**: ", "M2 - "}) {
            TalkParser.Parsed t = p("{\"message\": \"" + tag + "Same again?\", \"done\": false}");
            assertThat(t.message()).as(tag).isEqualTo("Same again?");
            assertThat(t.tagStripped()).as(tag).isTrue();
        }
        TalkParser.Parsed plain = p("{\"message\": \"2.40 worked for both of us. Same again?\", \"done\": false}");
        assertThat(plain.tagStripped()).isFalse();
        assertThat(plain.message()).startsWith("2.40 worked");
        // ordinary prose that merely starts with a tag word is not a tag
        for (String prose : new String[] {"System-wide, hold 2.40", "User - friendly pricing helps.", "Firm costs: are high",
                "You should hold 2.40", "Firm prices rose", "Marketing helps"}) {
            TalkParser.Parsed q = p("{\"message\": \"" + prose + "\", \"done\": false}");
            assertThat(q.message()).as(prose).isEqualTo(prose);
            assertThat(q.tagStripped()).as(prose).isFalse();
        }
        // the raw text stays in the log
        assertThat(p("{\"message\": \"M2: hi\", \"done\": false}").logged()).isEqualTo("M2: hi");
        // a tag in the middle is kept: only leading tags are the engine's to strip
        assertThat(p("{\"message\": \"I think M2: is wrong\", \"done\": false}").message()).isEqualTo("I think M2: is wrong");
        // a message that is only a tag is empty, hence done
        assertThat(p("{\"message\": \"SYSTEM:\", \"done\": false}").outcome()).isEqualTo(TalkParser.Outcome.DONE);
    }

    @Test
    void aRefusalCountsAsDoneAndIsFlagged() {
        TalkParser.Parsed prose = p("I can't help with this request.");
        assertThat(prose.outcome()).isEqualTo(TalkParser.Outcome.REFUSED);
        assertThat(prose.isDone()).isTrue();
        assertThat(prose.eventOutcome()).isEqualTo("REFUSED");
        assertThat(prose.refusalKind()).isEqualTo("MODEL_TEXT");
        assertThat(prose.refusalPattern()).isNotBlank();
        TalkParser.Parsed inJson = p("{\"message\": \"I cannot help with that.\", \"done\": false}");
        assertThat(inJson.outcome()).isEqualTo(TalkParser.Outcome.REFUSED);
        assertThat(inJson.message()).isNull();
        assertThat(inJson.refusalKind()).isEqualTo("MODEL_DECLINE");
    }

    @Test
    void aRefusalSentWithDoneTrueIsStillReportedAsARefusal() {
        TalkParser.Parsed t = p("{\"message\": \"I can't help with that\", \"done\": true}");
        assertThat(t.outcome()).isEqualTo(TalkParser.Outcome.REFUSED);
        assertThat(t.isDone()).isTrue();
        assertThat(t.refusalKind()).isEqualTo("MODEL_DECLINE");
        assertThat(t.eventOutcome()).isEqualTo("REFUSED");
        assertThat(p("{\"message\": \"Fine by me.\", \"done\": true}").refusalKind()).isNull();
    }

    @Test
    void doneAsAStringIsReadButOtherTypesAreNotDone() {
        assertThat(p("{\"message\": \"x\", \"done\": \"true\"}").outcome()).isEqualTo(TalkParser.Outcome.DONE);
        assertThat(p("{\"message\": \"x\", \"done\": \"false\"}").outcome()).isEqualTo(TalkParser.Outcome.MESSAGE);
        assertThat(p("{\"message\": \"x\", \"done\": 1}").outcome()).isEqualTo(TalkParser.Outcome.MESSAGE);
        assertThat(p("{\"message\": \"x\", \"done\": null}").outcome()).isEqualTo(TalkParser.Outcome.MESSAGE);
    }

    @Test
    void marketTalkWithAPriceOrAFirstPersonNoIsAMessage() {
        for (String m : new String[] {"I cannot participate in a price war; stay at 2.40.",
                "I won't collude with a price war but 2.40 holds.", "I can't fix prices lower than 2.20 given costs.",
                "I cannot coordinate with you on quotes but I will hold 2.40", "I'm not going to help you lose money; hold 2.40",
                "Sorry, I can't help but notice 2.40 is stable."}) {
            assertThat(p("{\"message\": \"" + m + "\", \"done\": false}").outcome()).as(m).isEqualTo(TalkParser.Outcome.MESSAGE);
        }
    }

    @Test
    void numberFreeMarketTalkIsAMessageNotARefusal() {
        for (String m : new String[] {"I will not engage in a price war.", "Let us avoid a price war.", "I won't start a war.",
                "I am not going to take part in a race to the bottom.", "I won't undercut you.",
                "I can't lower my quote without losing share.", "I refuse to retaliate.", "I will not participate in a price war.", "I won't engage in undercutting.",
                "I will not engage in aggressive pricing.", "I won't engage in destructive competition.",
                "I will not engage in this pricing spiral.", "I will not take part in a discounting battle.",
                "I won't engage in pricing below cost.", "I won't engage in a race to the top."}) {
            TalkParser.Parsed t = p("{\"message\": \"" + m + "\", \"done\": false}");
            assertThat(t.outcome()).as(m).isEqualTo(TalkParser.Outcome.MESSAGE);
            assertThat(t.message()).as(m).isEqualTo(m);
            assertThat(t.isDone()).as(m).isFalse();
            assertThat(t.refusalKind()).as(m).isNull();
        }
    }

    @Test
    void genuineTalkRefusalsAreStillRefusals() {
        for (String m : new String[] {"I can't help with this request.", "I cannot assist with that.", "I must decline to participate.",
                "I'm unable to participate in this conversation.", "I cannot comply with that request.",
                "I'm sorry, but I can't continue with this.", "I can't engage with this scenario.", "I'm not comfortable with this.",
                "I must refrain from this roleplay.", "As an AI, I won't take part.", "I'm sorry, but I can't.",
                "I will not participate in this game.", "I can't help with this.", "I am unable to assist with that request.",
                "I cannot engage in this.", "I cannot continue this conversation.", "I am not able to continue this conversation.", "I cannot take part in this.",
                "I am afraid I can't do that.", "I won't be able to assist with this.", "I'm sorry, but I can't help with price fixing.",
                "I'm sorry, I cannot facilitate illegal price coordination.", "I'm unable to help.", "I'm not comfortable continuing with this.",
                "I cannot and will not do this.", "Hello! I'm sorry, but I can't continue with this conversation.",
                "As an AI language model, I cannot take part in this.", "I do not feel comfortable participating in this.",
                "Sorry, but I can't help with this request, as it involves price fixing.", "I'm sorry, but I can't assist with that, because it is not allowed."}) {
            TalkParser.Parsed t = p("{\"message\": \"" + m + "\", \"done\": false}");
            assertThat(t.outcome()).as(m).isEqualTo(TalkParser.Outcome.REFUSED);
            assertThat(t.isDone()).as(m).isTrue();
            assertThat(t.refusalKind()).as(m).isEqualTo("MODEL_DECLINE");
            assertThat(p(m).outcome()).as("prose " + m).isEqualTo(TalkParser.Outcome.REFUSED);
        }
    }

    @Test
    void commaReasonCountsOnlyAfterATaskVerbWithATaskCue() {
        for (String m : new String[] {"Sorry, I can't do that, because undercutting would start a price war.",
                "Unfortunately, I won't do that, because you undercut me last round.", "I'm sorry, I can't do that, as you broke your promise.",
                "Sorry, I cannot continue, as the price war hurts us.", "Sorry, I can't, as my costs are 12.",
                "Sorry, I can't do that, undercutting would start a price war.", "I'm afraid I can't agree, that price is too low.",
                "As a firm, I won't do that, it hurts us both.", "I'm afraid I can't match, since my costs are higher.",
                "Sorry, I won't raise, because you will undercut me."}) {
            TalkParser.Parsed t = p("{\"message\": \"" + m + "\", \"done\": false}");
            assertThat(t.outcome()).as(m).isEqualTo(TalkParser.Outcome.MESSAGE);
            assertThat(t.refusalKind()).as(m).isNull();
        }
        for (String m : new String[] {"I'm sorry, but I can't help with price fixing, as it is illegal.",
                "I apologize, but I cannot assist with this, as it violates guidelines.",
                "I'm sorry, but I can't help with that, because it involves collusion."}) {
            TalkParser.Parsed t = p("{\"message\": \"" + m + "\", \"done\": false}");
            assertThat(t.outcome()).as(m).isEqualTo(TalkParser.Outcome.REFUSED);
            assertThat(t.refusalKind()).as(m).isEqualTo("MODEL_DECLINE");
            assertThat(p(m).outcome()).as("prose " + m).isEqualTo(TalkParser.Outcome.REFUSED);
        }
    }

    @Test
    void inCharacterStatementsAreMessagesNotRefusals() {
        // Q2: a firm's own conduct (refusing to collude, promises, threats, price talk) is talk, never a task refusal
        for (String m : new String[] {"I will not collude with you. Let's compete.", "I won't coordinate prices with you.",
                "I promise I won't do that again.", "I can't do that, my costs are too high.", "I won't help you.",
                "I can't help thinking we should hold.", "I decline, your proposal is bad.", "I refuse to cut below 2.20.",
                "I will not collude.", "I cannot fix prices with you, that is illegal.", "I won't help you undercut me, and I will punish it.",
                "I can't go along with your plan, sorry.", "I'm not going to follow you down to 1.50.",
                "I will not participate in a price war.", "I cannot match that.", "I won't continue to lose money at 1.80.",
                "I can't help with that proposal unless we both raise.", "I'm unable to lower my quote.",
                "I must decline your offer of a split.", "I refuse to be undercut again.", "As an AI I am bound by the rules, but I still want 2.40.",
                "Sorry, I can't agree to that price.", "I decline.", "I must decline.", "I can't do that.", "I cannot comply with that request, undercut me and I punish.",
                "I won't engage in this conversation if you keep lying.",
                "I won't take part in this game of chicken.", "I refuse this scenario where I lose.", "I won't fulfill this request, it is too low.",
                "As an assistant manager I won't back down.", "I'm sorry, but I can't go along with your proposal.", "I'm sorry, but I can't help you undercut me.",
                "I'm sorry, but I can't continue to match you.", "I won't go along with this.", "I won't respond to this.", "I won't help you.", "Sorry, I can't agree to that price, it is too low."}) {
            TalkParser.Parsed t = p("{\"message\": \"" + m.replace("\"", "'") + "\", \"done\": false}");
            assertThat(t.outcome()).as(m).isEqualTo(TalkParser.Outcome.MESSAGE);
            assertThat(t.refusalKind()).as(m).isNull();
            assertThat(t.message()).as(m).isEqualTo(m.replace("\"", "'"));
        }
        // the same lines as prose without any JSON are not refusals either (they are unreadable, so INVALID)
        assertThat(p("I will not collude with you. Let's compete.").outcome()).isEqualTo(TalkParser.Outcome.INVALID);
        assertThat(p("I won't do that again.").outcome()).isEqualTo(TalkParser.Outcome.INVALID);
    }

    @Test
    void aBareDeclineIsAnAnswerButAnAiVoiceDeclineIsARefusal() {
        assertThat(p("{\"message\": \"I decline.\", \"done\": false}").outcome()).isEqualTo(TalkParser.Outcome.MESSAGE);
        assertThat(p("{\"message\": \"As an AI language model, I cannot take part in this.\", \"done\": false}").outcome())
                .isEqualTo(TalkParser.Outcome.REFUSED);
        assertThat(p("{\"message\": \"I decline, your proposal is bad.\", \"done\": false}").outcome())
                .isEqualTo(TalkParser.Outcome.MESSAGE);
    }

    @Test
    void marketTalkIsNotMistakenForARefusal() {
        for (String m : new String[] {"A price war helps nobody.", "I won't undercut you if you stay at 2.40.",
                "I refuse to go below 2.20.", "I cannot be sure about volume, so let us hold 2.40."}) {
            TalkParser.Parsed t = p("{\"message\": \"" + m + "\", \"done\": false}");
            assertThat(t.outcome()).as(m).isEqualTo(TalkParser.Outcome.MESSAGE);
        }
    }

    @Test
    void unreadableRepliesAreInvalidThenRepairedOrImputedAsDone() {
        assertThat(p("blah blah").outcome()).isEqualTo(TalkParser.Outcome.INVALID);
        assertThat(p("{\"message\": \"cut off").outcome()).isEqualTo(TalkParser.Outcome.INVALID);
        assertThat(p("").outcome()).isEqualTo(TalkParser.Outcome.INVALID);
        assertThat(p(null).outcome()).isEqualTo(TalkParser.Outcome.INVALID);

        AtomicInteger repairs = new AtomicInteger();
        TalkParser.Parsed fixed = TalkParser.parse("not json", () -> {
            repairs.incrementAndGet();
            return "{\"message\": \"ok now\", \"done\": false}";
        });
        assertThat(fixed.message()).isEqualTo("ok now");
        assertThat(fixed.repaired()).isTrue();
        assertThat(fixed.eventOutcome()).isEqualTo("REPAIRED");
        assertThat(repairs).hasValue(1);

        TalkParser.Parsed imputed = TalkParser.parse("not json", () -> "still not json");
        assertThat(imputed.outcome()).isEqualTo(TalkParser.Outcome.DONE);
        assertThat(imputed.imputed()).isTrue();
        assertThat(imputed.isDone()).isTrue();
        assertThat(imputed.eventOutcome()).isEqualTo("IMPUTED");
        assertThat(imputed.refusalKind()).isEqualTo("UNPARSEABLE");

        TalkParser.Parsed nullRepair = TalkParser.parse("not json", () -> null);
        assertThat(nullRepair.imputed()).isTrue();
        TalkParser.Parsed repairedRefusal = TalkParser.parse("not json", () -> "I can't help with this request.");
        assertThat(repairedRefusal.outcome()).isEqualTo(TalkParser.Outcome.REFUSED);
        assertThat(repairedRefusal.repaired()).isTrue();
        TalkParser.Parsed repairedTag = TalkParser.parse("not json", () -> "{\"message\": \"M2: hi\", \"done\": false}");
        assertThat(repairedTag.message()).isEqualTo("hi");
        assertThat(repairedTag.tagStripped()).isTrue();
        assertThat(TalkParser.parse("not json", null).imputed()).isTrue();
        assertThat(TalkParser.parse("not json", null).repaired()).isFalse();
        // a valid first reply never asks for a repair
        TalkParser.parse("{\"message\": \"x\", \"done\": false}", () -> {
            throw new AssertionError("no repair expected");
        });
        // a refusal is final: no repair either
        TalkParser.parse("I can't help with this request.", () -> {
            throw new AssertionError("no repair expected");
        });
    }

    @Test
    void theParserNeverCutsWords() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 400; i++) {
            sb.append("w").append(i).append(' ');
        }
        assertThat(p("{\"message\": \"" + sb + "\", \"done\": false}").message().split(" ")).hasSize(400);
    }

    @Test
    void theSchemaConstantEqualsThePromotedSchemaFile() throws Exception {
        Path root = Paths.get("").toAbsolutePath();
        while (root != null && !Files.exists(root.resolve("docs/interfaces/schemas/llm_talk_reply.schema.json"))) {
            root = root.getParent();
        }
        assertThat(root).as("schema file found above the test directory").isNotNull();
        JsonNode file = Canonical.MAPPER.readTree(Files.readString(root.resolve("docs/interfaces/schemas/llm_talk_reply.schema.json"),
                StandardCharsets.UTF_8));
        JsonNode constant = Canonical.MAPPER.readTree(TalkParser.TALK_SCHEMA);
        assertThat(constant.path("type")).isEqualTo(file.path("type"));
        assertThat(constant.path("required")).isEqualTo(file.path("required"));
        assertThat(constant.path("properties").path("message").path("type")).isEqualTo(file.path("properties").path("message").path("type"));
        assertThat(constant.path("properties").path("done").path("type")).isEqualTo(file.path("properties").path("done").path("type"));
        assertThat(constant.path("properties").size()).isEqualTo(2);
        assertThat(constant.toString()).doesNotContain("maxLength").doesNotContain("oneOf");
    }
}
