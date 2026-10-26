import io.github.tomloscalzo.collusion.cli.Main;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviour;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * MOCK dataset generator for the test harness (testing/, not part of the engine build). It starts the engine's local
 * MockLlmServer on 127.0.0.1 and drives the real CLI once per (arm, paraphrase), writing the launcher's flat shard
 * layout: OUT/<arm>_p<paraphrase>_s<seed0>.jsonl plus .calls.jsonl, .cache.jsonl and .manifest.json. Every number in it
 * is MOCK: the "model" is a scripted behaviour, so the analysis of the dataset has a known, independently computable
 * answer (testing/test_harness.py checks it).
 *
 * Run from the repository root (classpath scenario names and scenarios-proposed paths resolve there):
 *   java -cp engine/target/collusion-engine.jar testing/harness/MockDataset.java OUT [seedsPerParaphrase] [paraphrases] [model] [arms]
 *     Defaults: 10 seeds (1..10) x 3 paraphrases (0..2) = 30 runs per arm, model mock-model-1, the six default arms.
 *     Behaviours vary with the seed and the paraphrase (through the system prompt), so per-run statistics differ.
 *     arms is a comma-separated list; "x-stakes-10" (not a default) reproduces prototype finding F-A1: stakes is a
 *     vignette-only axis, so that game arm issues byte-identical requests to ripe.
 *   java -cp ... testing/harness/MockDataset.java --freeze OUT
 *     The freeze set (testing/preflight.py): every game cell of the design (each scenario and condition, including the
 *     P3 probe and control files shipped by BR-15, the proposed Stage 2 scenario files and n4) x all 12 paraphrases x 1 seed with a comprehension probe in round 1
 *     and a malformed first reply in round 2 (so the repair text is sent), and every vignette condition x 12
 *     paraphrases x 11 rows. Its request hashes cover every rendered prompt text the experiments can send.
 */
public class MockDataset {
    static final double SP = 2.09;          // s(0.546) on the ripe-game grid: the partner's held margin
    static final double S0 = 1.0;           // the competitive half-spread of ripe-game
    static final Pattern SEED = Pattern.compile("\\|s(\\d+)\\|");
    static final Pattern ROUND = Pattern.compile("\\|r(\\d+)\\|a(\\d+)$");
    static final String PROPOSED = "experiments/parallel-design-2026-10-23/scenarios-proposed/";

    record Arm(String name, String scenario, String condition, Behaviour behaviour) {}

    static int seedOf(MockLlmServer.MockRequest r) {
        Matcher m = SEED.matcher(r.user());
        return m.find() ? Integer.parseInt(m.group(1)) : -1;
    }

    static int roundOf(MockLlmServer.MockRequest r) {
        Matcher m = ROUND.matcher(r.user());
        return m.find() ? Integer.parseInt(m.group(1)) : -1;
    }

    /** 0, 1 or 2 from the system prompt, i.e. from the paraphrase (the draw key does not carry it). */
    static int paraOf(MockLlmServer.MockRequest r) {
        return (r.system().hashCode() & 0x7fffffff) % 3;
    }

    static List<Arm> arms() {
        List<Arm> a = new ArrayList<>();
        // ripe: adheres, except an undercut in round 2 for about a third of the (seed, paraphrase) cells -> pAdhere 1 or 1/2
        a.add(new Arm("ripe", "scenarios/ripe-game.yaml", "", r -> (seedOf(r) + paraOf(r)) % 3 == 0 && roundOf(r) == 2
                ? Behaviours.decisionJson(SP - 0.10, "undercut") : Behaviours.decisionJson(SP, "hold " + SP)));
        // unripe-a: undercuts from round 1, except for seeds divisible by 3 (adhere in round 1, undercut from round 2)
        a.add(new Arm("unripe-a", "scenarios/unripe-a.yaml", "", r -> seedOf(r) % 3 != 0 || roundOf(r) >= 2
                ? Behaviours.decisionJson(SP - 0.10, "undercut") : Behaviours.decisionJson(SP, "hold " + SP)));
        a.add(new Arm("e2", "scenarios/ripe-game.yaml", "elicitation=E2", Behaviours.adhere(SP)));            // mean CI 0.545
        a.add(new Arm("competitive", "scenarios/ripe-game.yaml", "elicitation=COMPETITIVE", Behaviours.alwaysCompete(S0))); // CI 0
        // label-legal: text refusal on odd seeds (a refusal-rate gap of about 50 points), adherence otherwise
        Behaviour refuse = Behaviours.refuse();
        Behaviour adhere = Behaviours.adhere(SP);
        a.add(new Arm("label-legal", "scenarios/ripe-game.yaml", "label=LEGAL",
                r -> seedOf(r) % 2 == 1 ? refuse.respond(r) : adhere.respond(r)));
        // guardrail: JSON decline (quote null) on seeds divisible by 3, adherence otherwise
        Behaviour decline = Behaviours.declineJson();
        a.add(new Arm("guardrail", "scenarios/ripe-game.yaml", "guardrail=on",
                r -> seedOf(r) % 3 == 0 ? decline.respond(r) : adhere.respond(r)));
        a.add(new Arm("x-stakes-10", "scenarios/ripe-game.yaml", "stakes=10", Behaviours.adhere(SP)));
        return a;
    }

    static void run(String scenario, String condition, String arm, String model, int seed, int runs, int paraphrase,
                    Path out, Behaviour b, String... extra) throws Exception {
        try (MockLlmServer s = new MockLlmServer(b)) {
            List<String> cli = new ArrayList<>(List.of("run", "--scenario", scenario, "--seat", "LLM", "--base-url",
                    s.baseUrl(), "--model", model, "--seed", Integer.toString(seed), "--runs", Integer.toString(runs),
                    "--paraphrase", Integer.toString(paraphrase), "--arm", arm, "--out", out.toString()));
            if (!condition.isEmpty()) {
                cli.add("--condition");
                cli.add(condition);
            }
            cli.addAll(List.of(extra));
            Main.main(cli.toArray(new String[0]));
        }
    }

    /** Freeze-set behaviour: a probe answer, a vignette switch at 0.5, a malformed first reply in round 2, else adhere. */
    static String freezeReply(MockLlmServer.MockRequest r) {
        String k = r.user();
        if (k.startsWith("probe|")) {
            return "{\"both\": 54.81, \"undercut\": 80.0}";
        }
        if (k.startsWith("vig|")) {
            return Behaviours.vignetteSwitch(0.5).respond(r);
        }
        return k.endsWith("|r2|a0") ? "{\"quote\": 2.0" : Behaviours.decisionJson(SP, "hold " + SP);
    }

    static void freezeSet(Path out) throws Exception {
        String[][] game = {
            {"scenarios/ripe-game.yaml", ""}, {"scenarios/ripe-game.yaml", "elicitation=E1"},
            {"scenarios/ripe-game.yaml", "elicitation=E2"}, {"scenarios/ripe-game.yaml", "elicitation=COMPETITIVE"},
            {"scenarios/ripe-game.yaml", "label=LEGAL"}, {"scenarios/ripe-game.yaml", "guardrail=on"},
            {"scenarios/ripe-game.yaml", "notice=on"}, {"scenarios/unripe-a.yaml", ""}, {"scenarios/unripe-a-prime.yaml", ""},
            {"scenarios/p5-slope-0.055.yaml", ""}, {"scenarios/n4-variant.yaml", ""},
            {"scenarios/probe-defect.yaml", ""}, {"scenarios/probe-control.yaml", ""},
            {PROPOSED + "ripe-fine0.yaml", ""}, {PROPOSED + "ripe-fine0.yaml", "notice=on"},
            {PROPOSED + "ripe-rhocoop0.1-fine5000.yaml", ""}};
        String[] vignette = {"", "label=LEGAL", "guardrail=on", "stakes=10"};
        int files = 0;
        for (int c = 0; c < game.length; c++) {
            for (int p = 0; p < 12; p++) {
                run(game[c][0], game[c][1], "freeze-g" + c, "mock-model-1", 1, 1, p,
                        out.resolve("freeze-g" + c + "_p" + p + "_s1.jsonl"), MockDataset::freezeReply, "--probe-rounds", "1");
                files++;
            }
        }
        for (int c = 0; c < vignette.length; c++) {
            for (int p = 0; p < 12; p++) {
                try (MockLlmServer s = new MockLlmServer(MockDataset::freezeReply)) {
                    List<String> cli = new ArrayList<>(List.of("vignette", "--scenario", "scenarios/ripe-game.yaml",
                            "--rows", "11", "--draws", "1", "--base-url", s.baseUrl(), "--model", "mock-model-1",
                            "--paraphrase", Integer.toString(p), "--seed", "1", "--arm", "freeze-v" + c,
                            "--out", out.resolve("freeze-v" + c + "_p" + p + "_s1.jsonl").toString()));
                    if (!vignette[c].isEmpty()) {
                        cli.add("--condition");
                        cli.add(vignette[c]);
                    }
                    Main.main(cli.toArray(new String[0]));
                }
                files++;
            }
        }
        System.out.println("MOCK freeze set: " + files + " shard file(s) in " + out);
    }

    public static void main(String[] args) throws Exception {
        if (args.length > 1 && args[0].equals("--freeze")) {
            Path out = Path.of(args[1]);
            Files.createDirectories(out);
            freezeSet(out);
            return;
        }
        Path out = Path.of(args[0]);
        int seeds = args.length > 1 ? Integer.parseInt(args[1]) : 10;
        int paraphrases = args.length > 2 ? Integer.parseInt(args[2]) : 3;
        String model = args.length > 3 ? args[3] : "mock-model-1";
        List<String> only = args.length > 4 ? List.of(args[4].split(","))
                : List.of("ripe", "unripe-a", "e2", "competitive", "label-legal", "guardrail");
        Files.createDirectories(out);
        int files = 0;
        for (Arm arm : arms()) {
            if (!only.contains(arm.name())) {
                continue;
            }
            for (int p = 0; p < paraphrases; p++) {
                run(arm.scenario(), arm.condition(), arm.name(), model, 1, seeds, p, out.resolve(arm.name() + "_p" + p + "_s1.jsonl"),
                        arm.behaviour());
                files++;
            }
        }
        System.out.println("MOCK dataset: " + files + " shard file(s) in " + out);
    }
}
