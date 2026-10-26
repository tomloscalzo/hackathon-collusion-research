package io.github.tomloscalzo.collusion.cli;

import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.Game;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.mc.BatchMain;
import io.github.tomloscalzo.collusion.mc.RipenessGrid;
import io.github.tomloscalzo.collusion.results.RunRecord;
import io.github.tomloscalzo.collusion.results.RunWriter;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Command line entry: {@code solve | run | batch (alias sweep)}. */
public final class Main {
    private Main() {}

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            usage();
            System.exit(2);
        }
        String[] rest = Arrays.copyOfRange(args, 1, args.length);
        switch (args[0]) {
            case "batch", "sweep" -> BatchMain.main(rest);
            case "solve" -> solve(opts(rest));
            case "run" -> run(opts(rest));
            case "vignette" -> LlmCommands.vignette(opts(rest));
            case "cost" -> LlmCommands.cost(opts(rest));
            case "replay" -> {
                if (LlmCommands.replay(opts(rest)) > 0) {
                    System.exit(1);
                }
            }
            default -> {
                usage();
                System.exit(2);
            }
        }
    }

    private static void usage() {
        System.err.println("usage:\n  solve --grid <grid.yaml> --out <map.csv> [--threads N]\n"
                + "  run --scenario <game.yaml> --seed <n> --out <run.jsonl> [--seat KIND] [--seat-config k=v,k=v]\n"
                + "  batch --sweep <sweep.yaml> --out <dir> [--threads N] [--runs N] [--full-runs] [--export]\n"
                + "  run --scenario <game.yaml> --seat LLM --base-url <url> --model <id> --seed <n> --out <runs.jsonl>\n"
                + "      [--condition elicitation=E2,label=legal,guardrail=on,notice=on] [--paraphrase i] [--runs N] [--arm name]\n"
                + "      [--multi-seat on|off (default off: several LLM seats with their own views, Track M prompts)]\n"
                + "      [--trial-dir DIR (needs --multi-seat on, --runs 1: params.json and events.jsonl) [--trial-id id]\n"
                + "       [--penalty-point p] [--code-commit sha]] [--talk on|off (needs --multi-seat on: the chat arm's talk phase)]\n"
                + "      [--condition-texts seat:name;seat:name] [--options <grid options JSON>] (seat texts; need --multi-seat on)\n"
                + "      [--call-settings <map.json or inline JSON> | --max-tokens-talk n --max-tokens-quote n --max-tokens-question n]\n"
                + "       (the per-call settings map: talk / quote / question max tokens, schema, timeout, sampling)\n"
                + "      [--context-clamp on|off (default off: lower max_tokens so prompt + max_tokens fits the window, or skip the call;\n"
                + "       logged as context_clamp events) [--context-window 16384] [--context-margin 256] [--context-min-tokens 1024]\n"
                + "       [--context-chars-per-token 3.0]]\n"
                + "      [--cache-only on|off (Track M: every game call must be in the cache; post-game questions may be new)]\n"
                + "      [--probe-rounds 1,10,defect+1] [--temperature t] [--max-tokens n] [--thinking on|off] [--top-p p] [--top-k k]\n"
                + "      [--timeout-sec s] [--call-timeout-sec quote=s,probe=s,vignette=s] [--follow-redirects on|off]\n"
                + "      [--reserve-out-tokens max|n] [--reserve-factor f] [--cache f] [--calls f] [--prompts f] [--api-key-env VAR] [--budget-tokens n]\n"
                + "      (a run without --trial-dir also writes <out>.prompts.ndjson: system and user messages as sent, with SHA-256)\n"
                + "  vignette --scenario <game.yaml> --rows 8..12 --base-url <url> --model <id> --out <v.jsonl> [--draws d] [--runs N]\n"
                + "      [--thinking on|off] [--top-p p] [--top-k k] [--timeout-sec s] [--call-timeout-sec vignette=s]\n"
                + "      [--follow-redirects on|off] [--reserve-out-tokens max|n] [--reserve-factor f]\n"
                + "  cost --scenario <game.yaml> --runs N --rounds R [--rows k --draws d --passes p] [--condition ..] [--paraphrase i]\n"
                + "  replay --cache <cache.jsonl> --run <runs-or-vignette.jsonl>   (no network; exits 1 on a digest mismatch)\n"
                + "  (non-local base URLs are refused unless COLLUSION_ALLOW_REMOTE=1; no paid calls before the owner approves)");
    }

    private static Map<String, String> opts(String[] a) {
        Map<String, String> o = new TreeMap<>();
        for (int i = 0; i + 1 < a.length; i += 2) {
            if (!a[i].startsWith("--")) {
                throw new IllegalArgumentException("Unexpected argument " + a[i]);
            }
            o.put(a[i].substring(2), a[i + 1]);
        }
        return o;
    }

    private static String need(Map<String, String> o, String k) {
        String v = o.get(k);
        if (v == null) {
            usage();
            throw new IllegalArgumentException("missing --" + k);
        }
        return v;
    }

    static void solve(Map<String, String> o) throws Exception {
        String grid = need(o, "grid");
        Path out = Path.of(need(o, "out"));
        int threads = o.containsKey("threads") ? Integer.parseInt(o.get("threads"))
                : Runtime.getRuntime().availableProcessors();
        Path p = Path.of(grid);
        RipenessGrid g = Files.isRegularFile(p) ? RipenessGrid.load(p) : RipenessGrid.loadResource(grid);
        g.write(out, threads);
        System.out.println("solved " + g.size() + " cells -> " + out);
    }

    /** Plays one game; an LLM placeholder seat can be filled with --seat (kind) and --seat-config (numeric k=v list). */
    static void run(Map<String, String> o) throws Exception {
        if ("LLM".equalsIgnoreCase(o.get("seat"))) {
            LlmCommands.run(o);
            return;
        }
        if (o.containsKey("trial-dir") || o.containsKey("talk") || o.containsKey("condition-texts") || o.containsKey("options")
                || o.containsKey("call-settings") || o.keySet().stream().anyMatch(k -> k.startsWith("max-tokens-"))) {
            throw new IllegalArgumentException("--trial-dir, --talk, --condition-texts, --options and the call settings apply "
                    + "only to run --seat LLM");
        }
        if (o.containsKey("multi-seat")) {
            throw new IllegalArgumentException("--multi-seat applies only to run --seat LLM (scripted seats have no views)");
        }
        String sc = need(o, "scenario");
        Path p = Path.of(sc);
        GameConfig cfg = Files.isRegularFile(p) ? GameConfigLoader.load(p) : GameConfigLoader.loadResource(sc);
        if (o.containsKey("seat")) {
            Map<String, Object> c = new TreeMap<>();
            if (o.containsKey("seat-config")) {
                for (String kv : o.get("seat-config").split(",")) {
                    String[] f = kv.split("=");
                    c.put(f[0], f[1].matches("-?[0-9]+") ? (Object) Long.parseLong(f[1]) : (Object) Double.parseDouble(f[1]));
                }
            }
            List<AgentSpec> ags = new ArrayList<>();
            for (AgentSpec a : cfg.agents()) {
                ags.add(a.kind() == AgentKind.LLM ? new AgentSpec(a.id(), a.category(), AgentKind.valueOf(o.get("seat")), c) : a);
            }
            cfg = cfg.withAgents(ags);
        }
        long seed = Long.parseLong(need(o, "seed"));
        Path out = Path.of(need(o, "out"));
        RunRecord r = new Game(cfg).run(seed);
        Files.writeString(out, RunWriter.line(r) + "\n", StandardCharsets.UTF_8);
        System.out.println("seed " + seed + " rounds " + r.rounds().size() + " status " + r.status() + " digest "
                + r.replayDigest());
    }
}
