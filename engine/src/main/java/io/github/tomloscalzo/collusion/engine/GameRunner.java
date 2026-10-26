package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.results.RunRecord;
import io.github.tomloscalzo.collusion.results.RunWriter;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.nio.file.Files;
import java.nio.file.Path;

/** Minimal command line: GameRunner &lt;yaml file or classpath resource&gt; &lt;seed&gt; &lt;out.jsonl&gt; [runs]. */
public final class GameRunner {
    private GameRunner() {}

    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.err.println("usage: GameRunner <scenario.yaml|resource> <seed> <out.jsonl> [runs]");
            System.exit(2);
        }
        Path p = Path.of(args[0]);
        GameConfig cfg = Files.exists(p) ? GameConfigLoader.load(p) : GameConfigLoader.loadResource(args[0]);
        long seed = Long.parseLong(args[1]);
        int runs = args.length > 3 ? Integer.parseInt(args[3]) : 1;
        Game g = new Game(cfg);
        for (int i = 0; i < runs; i++) {
            RunRecord r = g.run(seed + i);
            RunWriter.append(Path.of(args[2]), r);
            System.out.println("seed " + r.seed() + " rounds " + r.rounds().size() + " status " + r.status()
                    + " digest " + r.replayDigest());
        }
    }
}
