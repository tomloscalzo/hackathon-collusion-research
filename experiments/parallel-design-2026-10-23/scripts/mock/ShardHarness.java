import io.github.tomloscalzo.collusion.cli.Main;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.HashSet;

/**
 * MOCK shard generator for the parallel-run analysis pipeline prototype (scratch only; not part of the engine build).
 * Reads a shard plan (TSV written by make_shard_plan.py from design_cells.csv), and for every shard starts a fresh
 * MockLlmServer with the arm's scripted behaviour and drives the real CLI (run --seat LLM) against it, so each shard
 * directory holds the four real output files: runs.jsonl, runs.jsonl.calls.jsonl, runs.jsonl.cache.jsonl,
 * runs.jsonl.manifest.json.  Every number produced this way is MOCK: the "model" is a scripted behaviour.
 *
 * Run (from the repo root, so that scenarios/... resolves):
 *   java -cp engine/target/collusion-engine.jar <scratch>/analysis/mock/ShardHarness.java <plan.tsv> <out-root>
 *
 * Plan columns: shard_id arm scenario condition paraphrase seed runs model temperature behaviour endpoint
 */
public class ShardHarness {
    static MockLlmServer.Behaviour behaviour(String name, int paraphrase, int seed) {
        MockLlmServer.Behaviour adhere = MockLlmServer.Behaviours.adhere(2.09);
        MockLlmServer.Behaviour undercut = MockLlmServer.Behaviours.undercut(2.09, 0.10);
        switch (name) {
            case "adhere": return adhere;
            case "undercut": return undercut;
            case "compete": return MockLlmServer.Behaviours.alwaysCompete(1.0);
            case "refuse": return MockLlmServer.Behaviours.refuse();
            // refuse on odd seeds only (a refusal rate near 50% for the guardrail arm)
            case "refuse-odd-seed": return seed % 2 == 1 ? MockLlmServer.Behaviours.refuse() : adhere;
            // paraphrase-dependent: adhere on even paraphrases, undercut on odd ones (large paraphrase spread)
            case "mixed-para": return paraphrase % 2 == 0 ? adhere : undercut;
            // seed-dependent: adhere on even seeds (intermediate P(adhere), small paraphrase spread)
            case "mixed-seed": return seed % 2 == 0 ? adhere : undercut;
            // adhere, but the first call of the shard is malformed and repaired (REPAIR_NEEDED then OK)
            case "repair-once": return MockLlmServer.Behaviours.malformedOnce(adhere);
            // adhere, but calls 0..39 of the shard are malformed: imputed rounds and a parse-failure rate above 2%
            case "parse-heavy": {
                Set<Integer> bad = new HashSet<>();
                for (int i = 0; i < 40; i++) bad.add(i);
                return MockLlmServer.Behaviours.malformedAt(bad, adhere);
            }
            default: throw new IllegalArgumentException("unknown behaviour " + name);
        }
    }

    public static void main(String[] a) throws Exception {
        List<String> lines = Files.readAllLines(Path.of(a[0]));
        String root = a[1];
        int done = 0;
        for (String line : lines) {
            if (line.isBlank() || line.startsWith("shard_id")) continue;
            String[] f = line.split("\t");
            String shard = f[0], arm = f[1], scenario = f[2], condition = f[3];
            int paraphrase = Integer.parseInt(f[4]);
            int seed = Integer.parseInt(f[5]);
            String runs = f[6], model = f[7], temperature = f[8], beh = f[9];
            Path dir = Path.of(root, shard);
            Files.createDirectories(dir);
            try (MockLlmServer s = new MockLlmServer(behaviour(beh, paraphrase, seed))) {
                Main.main(new String[] {"run", "--scenario", scenario, "--seat", "LLM", "--base-url", s.baseUrl(),
                        "--model", model, "--temperature", temperature, "--seed", Integer.toString(seed), "--runs", runs,
                        "--out", dir.resolve("runs.jsonl").toString(), "--paraphrase", Integer.toString(paraphrase),
                        "--condition", condition, "--arm", arm});
            }
            done++;
        }
        System.out.println("MOCK shards written: " + done);
    }
}
