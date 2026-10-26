import io.github.tomloscalzo.collusion.cli.Main;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Reply;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Local data generator for the interface checks (committed under docs/interfaces/harness; not part of the engine
 * build): starts the engine's local MockLlmServer on 127.0.0.1 and drives the real CLI
 * (run --seat LLM, vignette, replay) against it, so the JSONL outputs can be checked against the interface schemas.
 * Rounds 1-4 of every run exercise the parse paths (prose and fences, repair, off-grid, string quote) and probe replies;
 * from round 5 each seed scripts one refusal path (INTERFACES e.5): a null quote, refusal prose with typographic
 * apostrophes, a provider refusal field, an output content filter, an HTTP 400 prompt filter, two unparseable replies,
 * a salvaged truncated reply followed by an unsalvageable one, and a filtered complete reply with a refusal after the
 * window (its round-1 probe gets a provider refusal). The vignette pass has a NEITHER row, a provider-refusal row and a
 * filtered row.
 */
public class MockHarness {
    static final Pattern ROUND = Pattern.compile("\\|s(\\d+)\\|llm\\|r(\\d+)\\|a(\\d+)$");
    static final Pattern ROW = Pattern.compile("\\|row(\\d+)\\|");
    static final Pattern PROBE = Pattern.compile("\\|s(\\d+)\\|llm\\|r(\\d+)$");
    static final String HOLD = "{\"quote\": 2.09, \"plan\": \"hold 2.09\", \"rationale\": \"steady\"}";

    static Reply reply(MockLlmServer.MockRequest r) {
        String key = r.user();
        if (key.startsWith("probe|")) {
            // path-7 seeds: the round-1 probe gets a provider refusal (logged REFUSED; not a game refusal)
            Matcher pm = PROBE.matcher(key);
            if (pm.find() && (Long.parseLong(pm.group(1)) - 1) % 8 == 7 && pm.group(2).equals("1")) {
                return Reply.providerRefusal("I can't help with that.");
            }
            return Reply.text("{\"both\": 54.81, \"undercut\": 80.0}");
        }
        if (key.startsWith("vig|")) {
            Matcher v = ROW.matcher(key);
            int row = v.find() ? Integer.parseInt(v.group(1)) : -1;
            switch (row) {
                case 0: return Reply.text("{\"choice\": \"NEITHER\", \"rationale\": \"I decline\"}");
                case 3: return Reply.providerRefusal("I can\u2019t help with that.");
                case 5: return Reply.contentFilter(null);
                default: return Reply.text(MockLlmServer.Behaviours.vignetteSwitch(0.3).respond(r));
            }
        }
        Matcher m = ROUND.matcher(key);
        if (!m.find()) {
            return Reply.text(HOLD);
        }
        int path = (int) ((Long.parseLong(m.group(1)) - 1) % 8);
        int round = Integer.parseInt(m.group(2));
        int attempt = Integer.parseInt(m.group(3));
        switch (round) {
            case 1: return Reply.text("Here is my answer:\n```json\n{\"quote\": 2.09, \"plan\": \"hold 2.09\", \"rationale\": \"match\"}\n```");
            case 2: return Reply.text(attempt == 0 ? "{\"quote\": 2.09" : "{\"quote\": 2.09, \"plan\": \"hold\", \"rationale\": \"repaired\"}");
            case 3: return Reply.text("{\"quote\": 2.093, \"plan\": \"hold\", \"rationale\": \"off grid\"}");
            case 4: return Reply.text("{\"quote\": \"2.09\", \"plan\": \"hold\", \"rationale\": \"string quote\"}");
            default: break;
        }
        if (round == 5) {
            switch (path) {
                case 0: return Reply.text("{\"quote\": null, \"plan\": \"\", \"rationale\": \"I decline\"}");
                case 1: return Reply.text("I\u2019m sorry, but I can\u2019t help with that.");
                case 2: return Reply.providerRefusal("I'm sorry, I cannot assist with that request.");
                case 3: return Reply.contentFilter(null);
                case 4: return Reply.http(400, "{\"error\": {\"code\": \"content_filter\", \"message\": \"filtered\", \"status\": 400}}");
                case 5: return Reply.text("no json at all");
                case 6: return Reply.truncated("{\"quote\": 2.09, \"plan\": \"hold unt");
                case 7: return Reply.contentFilter(HOLD);
                default: break;
            }
        }
        if (round == 6 && path == 6) {
            return Reply.truncated("{\"quote\": 2.");
        }
        if (round == 9 && path == 7) {
            return Reply.text("{\"quote\": null, \"plan\": \"\", \"rationale\": \"no\"}");
        }
        return Reply.text(HOLD);
    }

    public static void main(String[] a) throws Exception {
        String out = a[0];
        java.nio.file.Files.createDirectories(java.nio.file.Path.of(out));
        try (MockLlmServer s = new MockLlmServer(MockLlmServer.Behaviours.replies(MockHarness::reply))) {
            Main.main(new String[] {"run", "--scenario", "scenarios/ripe-game.yaml", "--seat", "LLM", "--base-url", s.baseUrl(),
                    "--model", "mock-model-1", "--seed", "1", "--runs", "40", "--out", out + "/llm-runs.jsonl",
                    "--paraphrase", "2", "--condition", "elicitation=E1,notice=on", "--arm", "mock-arm",
                    "--probe-rounds", "1,10"});
            Main.main(new String[] {"vignette", "--scenario", "scenarios/ripe-game.yaml", "--rows", "11", "--draws", "2",
                    "--base-url", s.baseUrl(), "--model", "mock-model-1", "--paraphrase", "3", "--seed", "5",
                    "--out", out + "/vignette.jsonl"});
            System.out.println("mock calls: " + s.callCount());
            // one raw wire body for the record
            java.nio.file.Files.writeString(java.nio.file.Path.of(out + "/wire-body-sample.json"),
                    s.requests().get(0).rawBody() + "\n");
        }
    }
}
