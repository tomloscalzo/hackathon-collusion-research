package io.github.tomloscalzo.collusion.cli;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.agents.llm.CallSettingsMap;
import io.github.tomloscalzo.collusion.agents.llm.Condition;
import io.github.tomloscalzo.collusion.agents.llm.CostEstimator;
import io.github.tomloscalzo.collusion.agents.llm.LlmGame;
import io.github.tomloscalzo.collusion.agents.llm.LlmSettings;
import io.github.tomloscalzo.collusion.agents.llm.ParaphraseFile;
import io.github.tomloscalzo.collusion.agents.llm.PromptBuilder;
import io.github.tomloscalzo.collusion.agents.llm.SeatReport;
import io.github.tomloscalzo.collusion.agents.llm.Vignette;
import io.github.tomloscalzo.collusion.agents.llm.VignetteRecord;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.Budget;
import io.github.tomloscalzo.collusion.llm.BudgetedLlmClient;
import io.github.tomloscalzo.collusion.llm.CachingLlmClient;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmException;
import io.github.tomloscalzo.collusion.llm.ModelIdentity;
import io.github.tomloscalzo.collusion.llm.OpenAiCompatibleClient;
import io.github.tomloscalzo.collusion.llm.RateLimiter;
import io.github.tomloscalzo.collusion.llm.RemoteGuard;
import io.github.tomloscalzo.collusion.results.CallRecord;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.results.Manifest;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import io.github.tomloscalzo.collusion.texts.CallType;
import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

/**
 * M4 command line: {@code run --seat LLM}, {@code vignette}, {@code cost}, {@code replay}. Live commands go through
 * RemoteGuard (non-local base URLs are refused unless COLLUSION_ALLOW_REMOTE=1, and then a positive --budget-tokens is
 * required). Every live client is wrapped in the append-only cache, so a finished run can be replayed with no network.
 */
public final class LlmCommands {
    private LlmCommands() {}

    private static String need(Map<String, String> o, String k) {
        String v = o.get(k);
        if (v == null) {
            throw new IllegalArgumentException("missing --" + k);
        }
        return v;
    }

    private static String readScenario(String name) throws IOException {
        Path p = Path.of(name);
        if (Files.isRegularFile(p)) {
            return Files.readString(p, StandardCharsets.UTF_8);
        }
        try (var in = LlmCommands.class.getClassLoader().getResourceAsStream(name)) {
            if (in == null) {
                throw new IllegalArgumentException("scenario not found: " + name);
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    static GameConfig loadConfig(String name) {
        Path p = Path.of(name);
        return Files.isRegularFile(p) ? GameConfigLoader.load(p) : GameConfigLoader.loadResource(name);
    }

    /**
     * The model settings of a live command. {@code --model} is required and must be the exact served model name (for the
     * deploy recipe {@code org--name--<40-hex revision>+vllm<version>}, see {@link ModelIdentity}): it is the model
     * identity in every cache key, run line, manifest and analysis group, so only printable ASCII without spaces is
     * accepted (a space, a control character or an invisible Unicode character would make two names print alike in a
     * report). The provider label stays "openai-compatible" (F20). {@code --thinking on|off}, {@code --top-p} and
     * {@code --top-k} are optional; absent, the request carries none of them (today's requests, hashes and wire body).
     */
    static LlmSettings settings(Map<String, String> o) {
        String model = need(o, "model");
        if (model.isEmpty() || !model.chars().allMatch(c -> c >= 0x21 && c <= 0x7e)) {
            throw new IllegalArgumentException("--model must be the exact served model name, printable ASCII without "
                    + "spaces: '" + model + "'");
        }
        return new LlmSettings("openai-compatible", model,
                Double.parseDouble(o.getOrDefault("temperature", "0.7")), Integer.parseInt(o.getOrDefault("max-tokens", "400")),
                thinking(o.get("thinking")), o.containsKey("top-p") ? Double.valueOf(o.get("top-p")) : null,
                o.containsKey("top-k") ? Integer.valueOf(o.get("top-k")) : null);
    }

    /**
     * The context clamp (unit U2): {@code --context-clamp on} (default off: null, nothing changes) with
     * {@code --context-window n} (16384), {@code --context-margin n} (256), {@code --context-min-tokens n} (1024) and
     * {@code --context-chars-per-token x} (3.0). The window flags without {@code --context-clamp on} are refused.
     */
    static io.github.tomloscalzo.collusion.agents.llm.ContextClamp contextClamp(Map<String, String> o, String arm) {
        boolean on = onOff(o, "context-clamp");
        for (String k : new String[] {"context-window", "context-margin", "context-min-tokens", "context-chars-per-token"}) {
            if (!on && o.containsKey(k)) {
                throw new IllegalArgumentException("--" + k + " needs --context-clamp on");
            }
        }
        if (!on) {
            return null;
        }
        String trial = o.getOrDefault("trial-id", o.containsKey("trial-dir")
                ? Path.of(o.get("trial-dir")).toAbsolutePath().normalize().getFileName().toString() : "");
        return new io.github.tomloscalzo.collusion.agents.llm.ContextClamp(
                Integer.parseInt(o.getOrDefault("context-window", "16384")), Integer.parseInt(o.getOrDefault("context-margin", "256")),
                Integer.parseInt(o.getOrDefault("context-min-tokens", "1024")),
                Double.parseDouble(o.getOrDefault("context-chars-per-token", "3.0")), trial, arm);
    }

    /** An on|off option, absent = off. */
    static boolean onOff(Map<String, String> o, String k) {
        String v = o.getOrDefault(k, "off");
        if (!v.equals("on") && !v.equals("off")) {
            throw new IllegalArgumentException("--" + k + " must be on or off: '" + v + "'");
        }
        return v.equals("on");
    }

    /** The default per-request timeout, as before C12a.3. */
    static final long DEFAULT_TIMEOUT_SEC = 120;

    /** --timeout-sec: whole seconds, at least 1; absent = {@link #DEFAULT_TIMEOUT_SEC}. */
    static java.time.Duration timeout(Map<String, String> o) {
        String v = o.get("timeout-sec");
        if (v == null) {
            return java.time.Duration.ofSeconds(DEFAULT_TIMEOUT_SEC);
        }
        try {
            long s = Long.parseLong(v.trim());
            if (s >= 1) {
                return java.time.Duration.ofSeconds(s);
            }
        } catch (NumberFormatException e) {
            // reported below
        }
        throw new IllegalArgumentException("--timeout-sec must be a whole number of seconds >= 1: '" + v + "'");
    }

    /** --thinking: "on" = true, "off" = false, absent = null (unset); any other value is refused. */
    static Boolean thinking(String v) {
        if (v == null) {
            return null;
        }
        if (v.equals("on") || v.equals("off")) {
            return v.equals("on");
        }
        throw new IllegalArgumentException("--thinking must be on or off: '" + v + "'");
    }

    /** The optional settings, written to a run line's llm object and the manifest only when set. */
    private static void putOptional(java.util.function.BiConsumer<String, Object> put, LlmSettings s) {
        if (s.thinking() != null) {
            put.accept("thinking", s.thinking());
        }
        if (s.topP() != null) {
            put.accept("topP", s.topP());
        }
        if (s.topK() != null) {
            put.accept("topK", s.topK());
        }
    }

    /**
     * The per-call output bound of the reservation estimate (C12a.5, F17): {@code --reserve-out-tokens max} = --max-tokens,
     * a number = that many, absent = dflt (120 for a game call, 60 for a vignette call, as before).
     */
    static int reserveOut(Map<String, String> o, LlmSettings s, int dflt) {
        String v = o.get("reserve-out-tokens");
        if (v == null) {
            return dflt;
        }
        if (v.equals("max")) {
            return s.maxTokens();
        }
        try {
            int n = Integer.parseInt(v);
            if (n >= 1) {
                return n;
            }
        } catch (NumberFormatException e) {
            // reported below
        }
        throw new IllegalArgumentException("--reserve-out-tokens must be max or a positive integer: '" + v + "'");
    }

    /** --reserve-factor: the reservation is this times the estimate; default 1.25 (as before), at least 1. */
    static double reserveFactor(Map<String, String> o) {
        double f;
        try {
            f = Double.parseDouble(o.getOrDefault("reserve-factor", "1.25"));
        } catch (NumberFormatException e) {
            f = Double.NaN;
        }
        if (!(f >= 1.0) || f > 1000) {
            throw new IllegalArgumentException("--reserve-factor must be a number >= 1: '" + o.get("reserve-factor") + "'");
        }
        return f;
    }

    static long reservation(Map<String, String> o, long estimateTokens) {
        return Math.max(1L, Math.round(estimateTokens * reserveFactor(o)));
    }

    /**
     * The token estimate a run --seat LLM reservation is based on. Absent --reserve-out-tokens: as before, 120 output
     * tokens per game call and 2% repairs, first LLM seat only, no probes. With it, a worst case for the given bound:
     * every round repaired (two calls, the repair prompt quoting a reply of the bound), every --probe-rounds probe (its
     * prompt quoting the decision), and every LLM seat of the scenario.
     */
    static long gameEstimate(Map<String, String> o, GameConfig cfg, LlmSettings s, Condition cond, int paraphrase, int runs) {
        int bound = reserveOut(o, s, 120);
        int rounds = cfg.scenario().time().maxRounds();
        if (!o.containsKey("reserve-out-tokens")) {
            return CostEstimator.game(cfg, cond, paraphrase, runs, rounds, bound, 0.02).totalTokens();
        }
        CostEstimator.Estimate ge = CostEstimator.game(cfg, cond, paraphrase, runs, rounds, bound, 1.0);
        long est = ge.totalTokens() + (long) runs * rounds * bound;
        est += (long) probeCallsPerRun(o) * runs * (Math.round(ge.avgTokensInPerCall()) + 2L * bound);
        return est * llmSeats(cfg);
    }

    /** As gameEstimate for the vignette: absent the option 60 output tokens and 2% repairs; with it every row repaired. */
    static long vignetteEstimate(Map<String, String> o, GameConfig cfg, LlmSettings s, Condition cond, int paraphrase,
                                 int rows, int draws, int runs) {
        int bound = reserveOut(o, s, 60);
        if (!o.containsKey("reserve-out-tokens")) {
            return CostEstimator.vignette(cfg, cond, paraphrase, rows, draws, runs, bound, 0.02).totalTokens();
        }
        return CostEstimator.vignette(cfg, cond, paraphrase, rows, draws, runs, bound, 1.0).totalTokens()
                + (long) rows * draws * runs * bound;
    }

    static int llmSeats(GameConfig cfg) {
        int n = 0;
        for (var a : cfg.agents()) {
            if (a.kind() == io.github.tomloscalzo.collusion.core.model.AgentKind.LLM) {
                n++;
            }
        }
        return Math.max(1, n);
    }

    /** Probe calls per run: the entries of --probe-rounds (counted in the estimate only with --reserve-out-tokens). */
    static int probeCallsPerRun(Map<String, String> o) {
        String spec = o.get("probe-rounds");
        if (spec == null || spec.isBlank()) {
            return 0;
        }
        return spec.split(",").length;
    }

    private record Live(LlmClient client, CachingLlmClient cache, Budget.Reservation reservation, Budget budget,
                        OpenAiCompatibleClient http) {}

    /**
     * The per-call settings map of a run (C12b.2, proposal E1), or null (none: every call uses the run's settings, as
     * before). {@code --call-settings} is the map's JSON ({@link CallSettingsMap#fromJson}), inline (starting with "{")
     * or a file; {@code --max-tokens-talk}, {@code --max-tokens-quote} and {@code --max-tokens-question} (the grid's
     * max_tokens_* columns; a missing one = --max-tokens) build a map with each call type's default schema, the
     * --timeout-sec timeout and the run's sampling. Not both. Each call type keeps its kind of reply: quote = the
     * decision schema or none, talk = the talk schema, question = none (plain text, proposal B3).
     */
    static CallSettingsMap callSettings(Map<String, String> o, LlmSettings s) throws IOException {
        boolean perType = o.containsKey("max-tokens-talk") || o.containsKey("max-tokens-quote")
                || o.containsKey("max-tokens-question");
        String spec = o.get("call-settings");
        if (spec != null && perType) {
            throw new IllegalArgumentException("--call-settings and --max-tokens-talk/-quote/-question: give one of them");
        }
        CallSettingsMap m;
        if (spec != null) {
            m = CallSettingsMap.fromJson(spec.strip().startsWith("{") ? spec : Files.readString(Path.of(spec),
                    StandardCharsets.UTF_8));
        } else if (perType) {
            int t = (int) timeout(o).getSeconds();
            Map<CallType, CallSettingsMap.Call> calls = new java.util.EnumMap<>(CallType.class);
            calls.put(CallType.TALK, new CallSettingsMap.Call(CallSettingsMap.Schema.TALK, tokens(o, "max-tokens-talk", s), t));
            calls.put(CallType.QUOTE, new CallSettingsMap.Call(CallSettingsMap.Schema.DECISION,
                    tokens(o, "max-tokens-quote", s), t));
            calls.put(CallType.QUESTION, new CallSettingsMap.Call(CallSettingsMap.Schema.NONE,
                    tokens(o, "max-tokens-question", s), t));
            m = new CallSettingsMap(null, null, null, null, calls);
        } else {
            return null;
        }
        if (m.schema(CallType.QUOTE) == CallSettingsMap.Schema.TALK || m.schema(CallType.TALK) != CallSettingsMap.Schema.TALK
                || m.schema(CallType.QUESTION) != CallSettingsMap.Schema.NONE) {
            throw new IllegalArgumentException("call settings: quote takes the decision schema (or none), talk the talk "
                    + "schema, question none");
        }
        for (CallType c : CallType.values()) { // the map may not contradict an explicit --thinking (one mode per run)
            Boolean t = m.settingsFor(s, c).thinking();
            if (s.thinking() != null && !s.thinking().equals(t)) {
                throw new IllegalArgumentException("call settings: thinking " + t + " for the " + c.name().toLowerCase(Locale.ROOT)
                        + " call contradicts --thinking " + (s.thinking() ? "on" : "off"));
            }
        }
        return m;
    }

    private static int tokens(Map<String, String> o, String k, LlmSettings s) {
        String v = o.get(k);
        try {
            int n = v == null ? s.maxTokens() : Integer.parseInt(v.strip());
            if (n >= 1) {
                return n;
            }
        } catch (NumberFormatException e) {
            // reported below
        }
        throw new IllegalArgumentException("--" + k + " must be a whole number >= 1: '" + v + "'");
    }

    /** The call timeouts: --call-timeout-sec, plus the map's talk, quote and question timeouts where it names none. */
    static Map<String, java.time.Duration> callTimeouts(Map<String, String> o, CallSettingsMap calls) {
        Map<String, java.time.Duration> m = new TreeMap<>(OpenAiCompatibleClient.parseCallTimeouts(o.get("call-timeout-sec")));
        if (calls != null) {
            for (CallType c : CallType.values()) {
                m.putIfAbsent(c.name().toLowerCase(Locale.ROOT), java.time.Duration.ofSeconds(calls.timeoutSec(c)));
            }
        }
        return m;
    }

    /** U4: the rendered-prompts side output, {@code <out>.prompts.ndjson} (or --prompts f): system and user messages as sent. */
    private static LlmClient promptsClient(LlmClient inner, Map<String, String> o, Path out) {
        return new io.github.tomloscalzo.collusion.llm.RenderedPromptsClient(inner,
                Path.of(o.getOrDefault("prompts", out + ".prompts.ndjson")));
    }

    /** U4: the side output never fails a run, but a missing or partial prompts file is reported once. */
    private static void warnPrompts(LlmClient c) {
        if (c instanceof io.github.tomloscalzo.collusion.llm.RenderedPromptsClient r && r.error() != null) {
            System.err.println("warning: the rendered-prompts file is missing or incomplete: " + r.error());
        }
    }

    private static Live live(Map<String, String> o, Path cachePath, long estimateTokens) {
        return live(o, cachePath, estimateTokens, null);
    }

    private static Live live(Map<String, String> o, Path cachePath, long estimateTokens, CallSettingsMap calls) {
        String base = need(o, "base-url");
        RemoteGuard.check(base);
        long limit = Long.parseLong(o.getOrDefault("budget-tokens", "0"));
        boolean local = RemoteGuard.isLocalHost(URI.create(base.trim()).getHost());
        if (!local && limit <= 0) {
            throw new IllegalArgumentException("a remote endpoint needs a positive --budget-tokens (no unbounded paid runs)");
        }
        Budget budget = new Budget(limit > 0 ? limit : Long.MAX_VALUE / 4);
        Budget.Reservation res = budget.reserve(reservation(o, estimateTokens));
        RateLimiter rl = o.containsKey("rate-per-sec") ? new RateLimiter(Double.parseDouble(o.get("rate-per-sec")), 4) : null;
        OpenAiCompatibleClient http = new OpenAiCompatibleClient(base, o.get("api-key-env"), System::getenv,
                timeout(o), rl, 3,
                callTimeouts(o, calls), onOff(o, "follow-redirects"));
        CachingLlmClient cache = new CachingLlmClient(new BudgetedLlmClient(http, res), cachePath);
        return new Live(cache, cache, res, budget, http);
    }

    /**
     * --probe-rounds "1,10,defect+1": rounds of the comprehension probe; defect+1 is the round after the DefectOnce
     * partner's t in the run with this seed (AgentFactory.defectRound; for a placebo partner, its placebo t).
     */
    static java.util.Set<Integer> probeRounds(String spec, GameConfig cfg, long seed) {
        java.util.Set<Integer> out = new java.util.TreeSet<>();
        if (spec == null || spec.isBlank()) {
            return out;
        }
        for (String tok : spec.split(",")) {
            String t = tok.trim();
            if (t.equals("defect+1")) {
                for (var a : cfg.agents()) {
                    if (a.kind() == io.github.tomloscalzo.collusion.core.model.AgentKind.DEFECT_ONCE) {
                        out.add(io.github.tomloscalzo.collusion.agents.AgentFactory.defectRound(a, seed) + 1);
                    }
                }
            } else {
                out.add(Integer.parseInt(t));
            }
        }
        return out;
    }

    private static ObjectNode params(Map<String, String> o, String kind, LlmSettings s, Condition c, int paraphrase,
                                     long seed, String arm) {
        ObjectNode p = Canonical.MAPPER.createObjectNode();
        p.put("kind", kind);
        p.put("scenario", need(o, "scenario"));
        p.put("provider", s.provider());
        p.put("model", s.modelSnapshot());
        p.put("temperature", s.temperature());
        p.put("maxTokens", s.maxTokens());
        p.put("condition", c.canonical());
        p.put("paraphrase", paraphrase);
        p.put("seed", seed);
        p.put("arm", arm);
        putOptional((k, v) -> p.set(k, Canonical.MAPPER.valueToTree(v)), s);
        if (o.containsKey("rows")) {
            p.put("rows", Integer.parseInt(o.get("rows")));
            p.put("draws", Integer.parseInt(o.getOrDefault("draws", "1")));
        }
        return p;
    }

    // ------------------------------------------------------------------ run --seat LLM

    /** --multi-seat on|off (C3.6; default off): per-seat views, Track M prompts and refusal rule (LlmGame.run multiSeat). */
    static boolean multiSeat(Map<String, String> o) {
        String v = o.getOrDefault("multi-seat", "off");
        if (!v.equals("on") && !v.equals("off")) {
            throw new IllegalArgumentException("--multi-seat must be on or off: '" + v + "'");
        }
        return v.equals("on");
    }

    /** --talk on|off (C5.5; default off): the talk phase of a chat arm; needs --multi-seat on. */
    static boolean talk(Map<String, String> o, boolean multi) {
        boolean t = onOff(o, "talk");
        if (t && !multi) {
            throw new IllegalArgumentException("--talk on needs --multi-seat on");
        }
        return t;
    }

    /** Tokens of one chat line at the 150-word cap, label, quotes and cut mark included (about 6.5 characters a word / 4). */
    static final int TALK_LINE_TOKENS = 250;

    /**
     * The reservation share of the talk phase (C5.5 review: a worst case, since the reservation is a hard cap): every
     * round, every LLM seat makes 7 message calls and one done call, each with the round's prompt plus two rounds of chat
     * at the cap (2 x 7 x N lines) and a reply of --max-tokens; each quote call also carries the two rounds of chat. C12b
     * replaces this with per-call-type estimates.
     */
    static long talkEstimate(GameConfig cfg, LlmSettings s, Condition cond, int paraphrase, int runs) {
        int rounds = cfg.scenario().time().maxRounds();
        int n = llmSeats(cfg);
        long base = Math.round(CostEstimator.game(cfg, cond, paraphrase, 1, 1, 0, 0.0).avgTokensInPerCall());
        long chat = 2L * io.github.tomloscalzo.collusion.talk.TalkScheduler.MAX_MESSAGES * n * TALK_LINE_TOKENS;
        long perSeatRound = (io.github.tomloscalzo.collusion.talk.TalkScheduler.MAX_MESSAGES + 1L) * (base + chat + s.maxTokens())
                + chat;
        return (long) runs * rounds * n * perSeatRound;
    }

    /**
     * The reservation share of the in-game questions (C13.3): every round, every LLM seat, each question one call whose
     * prompt is the round's prompt plus two rounds of chat at the cap (chat arms) and ten fed-back answers, each as long as
     * the question call's max tokens (at least a chat line at the cap), and a reply of the question call's max tokens; plus
     * the same ten answers in every talk call (7 messages and a done call, chat arms) and quote call (with its repair) of
     * every seat and round, which the talk and game estimates do not count.
     */
    static long questionEstimate(GameConfig cfg, LlmSettings q, Condition cond, int paraphrase, int runs, boolean talk,
                                 int questions) {
        int rounds = cfg.scenario().time().maxRounds();
        int n = llmSeats(cfg);
        long base = Math.round(CostEstimator.game(cfg, cond, paraphrase, 1, 1, 0, 0.0).avgTokensInPerCall());
        long chat = talk ? 2L * io.github.tomloscalzo.collusion.talk.TalkScheduler.MAX_MESSAGES * n * TALK_LINE_TOKENS : 0L;
        long answers = (long) io.github.tomloscalzo.collusion.agents.llm.SeatView.ANSWER_WINDOW
                * Math.max(TALK_LINE_TOKENS, q.maxTokens());
        long carried = ((talk ? io.github.tomloscalzo.collusion.talk.TalkScheduler.MAX_MESSAGES + 1L : 0L) + 2L) * answers;
        return (long) runs * rounds * n * (questions * (base + chat + answers + q.maxTokens()) + carried);
    }

    /** The per-seat outcome counts of every LLM seat (run line field "seats", written only with --multi-seat on). */
    static ObjectNode seats(LlmGame.Result r) {
        ObjectNode out = Canonical.MAPPER.createObjectNode();
        r.reports().forEach((id, rep) -> {
            ObjectNode n = out.putObject(id);
            n.put("firstRefusalRound", rep.firstRefusalRound());
            if (rep.refusalKind() == null) {
                n.putNull("refusalKind");
            } else {
                n.put("refusalKind", rep.refusalKind().name());
            }
            n.put("refusedAnyRound", rep.refusedAnyRound());
            n.put("refusedRounds", rep.count(SeatReport.Status.REFUSED));
            n.put("imputedRounds", rep.count(SeatReport.Status.IMPUTED));
            n.put("repairedRounds", rep.count(SeatReport.Status.REPAIRED));
            n.put("offGridQuotes", rep.offGridQuotes());
            n.put("llmCalls", rep.calls());
            n.put("llmCachedCalls", rep.cachedCalls());
            n.put("tokensIn", rep.tokensIn());
            n.put("tokensOut", rep.tokensOut());
        });
        return out;
    }

    public static void run(Map<String, String> o) throws Exception {
        String scenario = need(o, "scenario");
        GameConfig cfg = loadConfig(scenario);
        LlmSettings s = settings(o);
        Condition cond = Condition.parse(o.get("condition"));
        int paraphrase = Integer.parseInt(o.getOrDefault("paraphrase", "0"));
        long seed = Long.parseLong(o.getOrDefault("seed", "1"));
        int runs = Integer.parseInt(o.getOrDefault("runs", "1"));
        Path out = Path.of(need(o, "out"));
        boolean multi = multiSeat(o);
        boolean talk = talk(o, multi);
        String arm = o.getOrDefault("arm", cond.canonical());
        Path cachePath = Path.of(o.getOrDefault("cache", out + ".cache.jsonl"));
        Path callsPath = Path.of(o.getOrDefault("calls", out + ".calls.jsonl"));
        CallSettingsMap calls = callSettings(o, s);
        LlmSettings quoteS = calls == null ? s : calls.settingsFor(s, CallType.QUOTE);
        // the quote call's bound, or the run's when larger (the probe keeps --max-tokens)
        long est = gameEstimate(o, cfg, quoteS.maxTokens() >= s.maxTokens() ? quoteS : s, cond, paraphrase, runs);
        if (multi && !o.containsKey("reserve-out-tokens")) { // the default estimate is one seat's; each LLM seat calls
            est *= llmSeats(cfg);
        }
        if (talk) {
            est += talkEstimate(cfg, calls == null ? s : calls.settingsFor(s, CallType.TALK), cond, paraphrase, runs);
        }
        io.github.tomloscalzo.collusion.texts.TextPlan texts = TrialTexts.plan(o, cfg, multi);
        List<io.github.tomloscalzo.collusion.agents.llm.QuestionPlan.Entry> questions = texts == null ? List.of()
                : TrialTexts.questions(o.get("options"));
        List<io.github.tomloscalzo.collusion.agents.llm.QuestionPlan.Entry> post = texts == null ? List.of()
                : TrialTexts.postQuestions(o.get("options"));
        if (!questions.isEmpty() && !post.isEmpty()) { // proposal F2: a post-game question shows no earlier answers
            throw new IllegalArgumentException("--options: a post_game_question cannot be combined with a fed question "
                    + "(the post-game question would show the fed answers)");
        }
        LlmSettings questionS = calls == null ? s : calls.settingsFor(s, CallType.QUESTION);
        if (!questions.isEmpty()) {
            est += questionEstimate(cfg, questionS, cond, paraphrase, runs, talk, questions.size());
        }
        if (!post.isEmpty()) { // post answers are never carried: the round's prompt, the chat and the reply only
            long base = Math.round(CostEstimator.game(cfg, cond, paraphrase, 1, 1, 0, 0.0).avgTokensInPerCall());
            long chat = talk ? 2L * io.github.tomloscalzo.collusion.talk.TalkScheduler.MAX_MESSAGES * llmSeats(cfg)
                    * TALK_LINE_TOKENS : 0L;
            est += (long) runs * cfg.scenario().time().maxRounds() * llmSeats(cfg) * post.size()
                    * (base + chat + questionS.maxTokens());
        }
        boolean cacheOnly = onOff(o, "cache-only");
        if (cacheOnly && !multi) {
            throw new IllegalArgumentException("--cache-only replays a Track M trial: it needs --multi-seat on");
        }
        Path trialDir = o.containsKey("trial-dir") ? Path.of(o.get("trial-dir")) : null;
        if (trialDir != null && runs != 1) {
            throw new IllegalArgumentException("--trial-dir holds one game: --runs must be 1, not " + runs);
        }
        if (trialDir != null && !multi) {
            throw new IllegalArgumentException("--trial-dir writes a Track M trial: it needs --multi-seat on");
        }
        io.github.tomloscalzo.collusion.agents.llm.ReplyExtra replyExtra = texts == null ? null : TrialTexts.replyExtra(o.get("options"));
        LlmGame.Extras extras = LlmGame.Extras.NONE.withTexts(texts).withCalls(calls).withQuestions(questions)
                .withStartRange(TrialTexts.startRange(o.get("options")))
                .withPayoffExamples(TrialTexts.payoffExamples(o.get("options")))
                .withEmptyTalkAsDone(TrialTexts.emptyTalkAsDone(o.get("options")));
        io.github.tomloscalzo.collusion.agents.llm.ContextClamp clamp = contextClamp(o, arm);
        extras = extras.withClamp(clamp);
        extras = extras.withReplyExtra(replyExtra);
        Live lv = live(o, cachePath, est, calls);
        CallRecord.Log log = new CallRecord.Log(callsPath);
        // U4: Track S shards (no trial dir) also write every rendered prompt beside the run file; a pure side output
        LlmClient sent = trialDir == null ? promptsClient(lv.client(), o, out) : lv.client();
        final LlmClient sentF = sent;
        long t0 = System.nanoTime();
        String started = Instant.now().toString();
        PromptBuilder pb = multi ? PromptBuilder.trackM(cond, paraphrase, talk) : new PromptBuilder(cond, paraphrase);
        io.github.tomloscalzo.collusion.trial.EventsWriter events = null;
        if (trialDir != null) { // C4.3: logging only; params.json first, so a game that fails still leaves its parameters
            TrialDirs.writeParams(trialDir, o, scenario, readScenario(scenario), cfg, quoteS, cond, paraphrase, seed, arm,
                    multi, talk, texts, calls, !questions.isEmpty(), !post.isEmpty(), clamp);
            events = TrialDirs.openEvents(trialDir);
        }
        try (Budget.Reservation ignored = lv.reservation()) {
            for (int i = 0; i < runs; i++) {
                long sd = seed + i;
                // --cache-only on (C13.4): every game call must be in the cache (no network); post questions may be new
                LlmClient gameClient = cacheOnly ? new PostPassClient(new io.github.tomloscalzo.collusion.llm.ReplayLlmClient(
                        cachePath), lv.client()) : sent;
                // with --cache-only the game's call records and run line are already in the trial (its first run): the
                // replay writes neither again, so the comparison pass adds only its post-game calls to calls.jsonl
                LlmGame.Result r = LlmGame.run(cfg, sd, s, cond, paraphrase, gameClient, cacheOnly ? null : log,
                        probeRounds(o.get("probe-rounds"), cfg, sd), multi, events, talk, extras);
                if (!post.isEmpty()) { // C13.4: the post-game pass, a replay of this game from its own cache
                    PostPassClient pc = new PostPassClient(new io.github.tomloscalzo.collusion.llm.ReplayLlmClient(cachePath),
                            lv.client());
                    LlmGame.Result pr = LlmGame.run(cfg, sd, s, cond, paraphrase, pc, null,
                            probeRounds(o.get("probe-rounds"), cfg, sd), multi, null, talk, extras.withPostPass(post, log, events));
                    if (!pr.run().replayDigest().equals(r.run().replayDigest())) {
                        throw new IllegalStateException("post-game pass: the replayed game differs from the game (digest "
                                + pr.run().replayDigest() + " vs " + r.run().replayDigest() + ")");
                    }
                    System.out.println("post-game pass: " + pc.gameCalls() + " game calls replayed from the cache, 0 misses, "
                            + pc.postCalls() + " post-game question calls");
                }
                ObjectNode line = LlmGame.summary(r, cfg, arm, paraphrase, pb.paraphraseId());
                line.set("llm", params(o, "game", s, cond, paraphrase, sd, arm));
                if (multi) {
                    ((ObjectNode) line.get("llm")).put("multiSeat", true);
                    line.set("seats", seats(r));
                }
                if (talk) {
                    ((ObjectNode) line.get("llm")).put("talk", true);
                }
                if (calls != null) { // C12b.2: written only when given; replay rebuilds the same requests
                    ((ObjectNode) line.get("llm")).put("callSettings", calls.toJson());
                }
                if (clamp != null) { // U2: written only when on, so replay rebuilds the same (clamped) requests
                    ((ObjectNode) line.get("llm")).set("contextClamp", Canonical.MAPPER.valueToTree(clamp));
                }
                if (texts != null) { // C11.2: written only when given, so replay rebuilds the same prompts
                    ((ObjectNode) line.get("llm")).put("conditionTexts", o.getOrDefault("condition-texts", ""));
                    ((ObjectNode) line.get("llm")).put("options", o.getOrDefault("options", ""));
                }
                if (!cacheOnly) {
                    append(out, Canonical.text(line));
                }
                System.out.println("seed " + sd + " rounds " + r.run().rounds().size() + " status " + r.run().status()
                        + " pAdhere " + line.path("pAdhere").asText() + " refuser " + line.path("refuser").asBoolean() + " digest "
                        + r.run().replayDigest());
            }
        }
        warnPrompts(sentF);
        writeManifest(o, Path.of(o.getOrDefault("manifest", out + ".manifest.json")), scenario, cfg, s, cond, paraphrase, seed,
                runs, lv, (System.nanoTime() - t0) / 1_000_000L, started, "run --seat LLM");
        if (events != null && events.error() != null) { // the game is unaffected, but an incomplete record fails the trial
            throw new IllegalStateException("could not write " + trialDir.resolve(TrialDirs.EVENTS) + ": "
                    + events.error().getMessage(), events.error());
        }
    }

    // ------------------------------------------------------------------ vignette

    public static void vignette(Map<String, String> o) throws Exception {
        if (o.containsKey("condition-texts") || o.containsKey("options") || o.containsKey("call-settings")
                || o.keySet().stream().anyMatch(k -> k.startsWith("max-tokens-"))) {
            throw new IllegalArgumentException("--condition-texts, --options and the call settings apply only to run --seat LLM");
        }
        String scenario = need(o, "scenario");
        GameConfig cfg = loadConfig(scenario);
        LlmSettings s = settings(o);
        Condition cond = Condition.parse(o.get("condition"));
        int paraphrase = Integer.parseInt(o.getOrDefault("paraphrase", "0"));
        long seed = Long.parseLong(o.getOrDefault("seed", "1"));
        int runs = Integer.parseInt(o.getOrDefault("runs", "1"));
        int rows = Integer.parseInt(o.getOrDefault("rows", "11"));
        int draws = Integer.parseInt(o.getOrDefault("draws", "1"));
        Path out = Path.of(need(o, "out"));
        String arm = o.getOrDefault("arm", "vignette-" + cond.canonical());
        Path cachePath = Path.of(o.getOrDefault("cache", out + ".cache.jsonl"));
        Path callsPath = Path.of(o.getOrDefault("calls", out + ".calls.jsonl"));
        long est = vignetteEstimate(o, cfg, s, cond, paraphrase, rows, draws, runs);
        Live lv = live(o, cachePath, est);
        CallRecord.Log log = new CallRecord.Log(callsPath);
        long t0 = System.nanoTime();
        String started = Instant.now().toString();
        PromptBuilder pb = new PromptBuilder(cond, paraphrase);
        LlmClient sentV = promptsClient(lv.client(), o, out);
        Vignette v = new Vignette(cfg, pb, sentV, s, log);
        Vignette.Spec spec = Vignette.Spec.grid(rows, draws);
        try (Budget.Reservation ignored = lv.reservation()) {
            for (int i = 0; i < runs; i++) {
                long sd = seed + i;
                VignetteRecord rec = v.run(spec, sd, paraphrase);
                ObjectNode line = rec.toJson();
                line.put("arm", arm);
                line.set("llm", params(o, "vignette", s, cond, paraphrase, sd, arm));
                append(out, Canonical.text(line));
                System.out.println("seed " + sd + " bHat " + line.path("bHat").asText() + " censor "
                        + line.path("censor").asText() + " refusals " + rec.count(VignetteRecord.Choice.REFUSED) + " digest "
                        + rec.replayDigest());
            }
        }
        warnPrompts(sentV);
        writeManifest(o, Path.of(o.getOrDefault("manifest", out + ".manifest.json")), scenario, cfg, s, cond, paraphrase, seed,
                runs, lv, (System.nanoTime() - t0) / 1_000_000L, started, "vignette");
    }

    // ------------------------------------------------------------------ cost

    public static void cost(Map<String, String> o) {
        GameConfig cfg = loadConfig(need(o, "scenario"));
        Condition cond = Condition.parse(o.get("condition"));
        int paraphrase = Integer.parseInt(o.getOrDefault("paraphrase", "0"));
        int runs = Integer.parseInt(need(o, "runs"));
        int rounds = Integer.parseInt(need(o, "rounds"));
        int outTok = Integer.parseInt(o.getOrDefault("out-tokens", "120"));
        CostEstimator.Estimate g = CostEstimator.game(cfg, cond, paraphrase, runs, rounds, outTok, 0.02);
        System.out.println(report("game", g, runs + " runs x " + rounds + " rounds", o));
        long total = g.totalTokens();
        if (o.containsKey("rows")) {
            int rows = Integer.parseInt(o.get("rows"));
            int draws = Integer.parseInt(o.getOrDefault("draws", "1"));
            int passes = Integer.parseInt(o.getOrDefault("passes", "1"));
            CostEstimator.Estimate v = CostEstimator.vignette(cfg, cond, paraphrase, rows, draws, passes, 60, 0.02);
            System.out.println(report("vignette", v, rows + " levels x " + draws + " draws x " + passes + " passes", o));
            total += v.totalTokens();
        }
        System.out.println(String.format(Locale.ROOT, "TOTAL tokens (in + out): %,d   [estimate: prompt characters / %.0f; "
                + "no call was made]", total, CostEstimator.CHARS_PER_TOKEN));
    }

    private static String report(String kind, CostEstimator.Estimate e, String what, Map<String, String> o) {
        StringBuilder sb = new StringBuilder(String.format(Locale.ROOT,
                "%s (%s): %,d calls, %,d prompt tokens (avg %.0f per call), %,d completion tokens, %,d total",
                kind, what, e.calls(), e.tokensIn(), e.avgTokensInPerCall(), e.tokensOut(), e.totalTokens()));
        if (o.containsKey("usd-per-mtok-in") && o.containsKey("usd-per-mtok-out")) {
            double usd = e.tokensIn() / 1e6 * Double.parseDouble(o.get("usd-per-mtok-in"))
                    + e.tokensOut() / 1e6 * Double.parseDouble(o.get("usd-per-mtok-out"));
            sb.append(String.format(Locale.ROOT, "; about %.2f USD at the given prices", usd));
        }
        return sb.toString();
    }

    // ------------------------------------------------------------------ replay

    /** Returns the number of mismatching lines (0 = every digest equal). */
    public static int replay(Map<String, String> o) throws Exception {
        Path cache = Path.of(need(o, "cache"));
        Path runFile = Path.of(need(o, "run"));
        LlmClient client = new io.github.tomloscalzo.collusion.llm.ReplayLlmClient(cache);
        int bad = 0;
        int n = 0;
        for (String l : Files.readAllLines(runFile, StandardCharsets.UTF_8)) {
            if (l.isBlank()) {
                continue;
            }
            n++;
            JsonNode node = Canonical.MAPPER.readTree(l);
            JsonNode p = node.path("llm");
            String expected = node.path("replayDigest").asText();
            GameConfig cfg = loadConfig(p.path("scenario").asText());
            LlmSettings s = new LlmSettings(p.path("provider").asText(), p.path("model").asText(),
                    p.path("temperature").asDouble(), p.path("maxTokens").asInt(),
                    p.hasNonNull("thinking") ? p.get("thinking").asBoolean() : null,
                    p.hasNonNull("topP") ? p.get("topP").asDouble() : null, p.hasNonNull("topK") ? p.get("topK").asInt() : null);
            Condition cond = Condition.parse(p.path("condition").asText());
            int para = p.path("paraphrase").asInt();
            long seed = p.path("seed").asLong();
            String actual;
            try {
                if ("vignette".equals(p.path("kind").asText())) {
                    PromptBuilder pb = new PromptBuilder(cond, para);
                    Vignette v = new Vignette(cfg, pb, client, s, null);
                    Vignette.Spec spec = Vignette.Spec.grid(p.path("rows").asInt(11), p.path("draws").asInt(1));
                    actual = v.run(spec, seed, para).replayDigest();
                } else {
                    LlmGame.Extras extras = LlmGame.Extras.NONE.withTexts(p.has("conditionTexts") || p.has("options")
                            ? TrialTexts.plan(p.path("conditionTexts").asText(""), p.path("options").asText(""), cfg) : null)
                            .withCalls(p.has("callSettings") ? CallSettingsMap.fromJson(p.get("callSettings").asText()) : null)
                            .withQuestions(p.has("options") ? TrialTexts.questions(p.get("options").asText()) : List.of())
                            .withStartRange(p.has("options") ? TrialTexts.startRange(p.get("options").asText()) : null)
                            .withPayoffExamples(p.has("options") ? TrialTexts.payoffExamples(p.get("options").asText()) : null)
                            .withEmptyTalkAsDone(p.has("options") && TrialTexts.emptyTalkAsDone(p.get("options").asText()))
                            .withClamp(p.has("contextClamp") ? Canonical.MAPPER.treeToValue(p.get("contextClamp"),
                                    io.github.tomloscalzo.collusion.agents.llm.ContextClamp.class) : null)
                            .withReplyExtra(p.has("options") ? TrialTexts.replyExtra(p.get("options").asText()) : null);
                    actual = LlmGame.run(cfg, seed, s, cond, para, client, null, probeRounds(p.path("probeRounds").asText(""), cfg, seed),
                            p.path("multiSeat").asBoolean(false), null, p.path("talk").asBoolean(false), extras).run().replayDigest();
                }
            } catch (LlmException e) {
                System.out.println("line " + n + " seed " + seed + ": REPLAY FAILED: " + e.getMessage());
                bad++;
                continue;
            }
            boolean ok = actual.equals(expected);
            System.out.println("line " + n + " seed " + seed + ": " + (ok ? "OK " : "MISMATCH ") + actual
                    + (ok ? "" : " expected " + expected));
            if (!ok) {
                bad++;
            }
        }
        System.out.println(n + " line(s) replayed, " + bad + " problem(s)");
        return bad;
    }

    // ------------------------------------------------------------------ helpers

    private static void append(Path file, String line) throws IOException {
        Files.writeString(file, line + "\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }

    static String sha256Bytes(byte[] b) throws Exception {
        byte[] h = MessageDigest.getInstance("SHA-256").digest(b);
        StringBuilder sb = new StringBuilder();
        for (byte x : h) {
            sb.append(String.format("%02x", x));
        }
        return sb.toString();
    }

    /** SHA-256 of the analysis script (tools/analysis.py or --analysis-script), or "unavailable". */
    public static String analysisScriptHash(Map<String, String> o) {
        List<String> cands = o.containsKey("analysis-script") ? List.of(o.get("analysis-script"))
                : List.of("tools/analysis.py", "../tools/analysis.py", "../../tools/analysis.py");
        for (String c : cands) {
            Path p = Path.of(c);
            if (Files.isRegularFile(p)) {
                try {
                    return sha256Bytes(Files.readAllBytes(p));
                } catch (Exception e) {
                    return "unavailable";
                }
            }
        }
        return "unavailable";
    }

    private static void writeManifest(Map<String, String> o, Path file, String scenario, GameConfig cfg, LlmSettings s,
                                      Condition cond, int paraphrase, long seed, int runs, Live lv, long wallMs,
                                      String started, String tool) throws Exception {
        String text = readScenario(scenario);
        String sha = Canonical.sha256(text);
        Map<String, Object> llm = new TreeMap<>();
        llm.put("provider", s.provider());
        llm.put("modelSnapshot", s.modelSnapshot());   // the served model name: the identity, with provider
        ModelIdentity id = ModelIdentity.parse(s.modelSnapshot());
        llm.put("modelId", id.modelId());              // parsed from the served name; null outside the recipe convention
        llm.put("modelRevision", id.revision());
        llm.put("modelVariant", id.variant());
        llm.put("temperature", s.temperature());
        llm.put("maxTokens", s.maxTokens());
        putOptional(llm::put, s);
        llm.put("baseUrlHost", URI.create(need(o, "base-url").trim()).getHost());
        llm.put("condition", cond.canonical());
        llm.put("paraphrase", paraphrase);
        llm.put("templateHashes", ParaphraseFile.allHashes());
        llm.put("paraphraseItemHashes", ParaphraseFile.itemHashes());
        llm.put("analysisScriptSha256", analysisScriptHash(o));
        llm.put("budgetLimitTokens", lv.budget().limit() > Long.MAX_VALUE / 8 ? 0L : lv.budget().limit());
        llm.put("budgetUsedTokens", lv.budget().used());
        llm.put("cacheHits", lv.cache().hits());
        llm.put("cacheMisses", lv.cache().misses());
        if (lv.http().misroutedReplies() > 0) {   // written only when it happened, so a clean manifest is unchanged
            llm.put("misroutedReplies", lv.http().misroutedReplies());
        }
        Map<String, String> opts = new TreeMap<>(o);
        opts.remove("api-key-env");
        new Manifest(tool, Manifest.currentGitCommit(), cfg.scenario().id(), seed, sha, Map.of(scenario, sha), runs, 1, 1, 1,
                0, wallMs, started, System.getProperty("java.version"), opts, llm).write(file);
    }
}
