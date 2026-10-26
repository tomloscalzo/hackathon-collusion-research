package io.github.tomloscalzo.collusion.agents.llm;

import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import io.github.tomloscalzo.collusion.mc.RandomStream;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;
import io.github.tomloscalzo.collusion.results.CallRecord;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.function.Consumer;

/**
 * The vignette arm (spec 4.1, 5.2): a binary choice with a two-sided price list of 8-12 payment levels (units of the gross
 * collusive gain G). One row per call with a fresh context (a single stateless request), rows in a random order per seed
 * (stream vignette:order, T11), callsPerRow draws per row. The same scenario numbers as the game are stated, the penalty
 * contingent on the best quote (T16). A reply is parsed to COLLUDE / COMPETE / REFUSED; an unparseable reply gets one
 * repair retry and is then INVALID (excluded and counted). A provider refusal field (finishReason "refusal") or a provider
 * filter (finishReason "content_filter", unless the text still parses to a valid choice) makes the row REFUSED with no
 * repair. A refused row is dropped from the pass's b-hat only; the pass is a refuser only when no row is valid and at
 * least one is refused (INTERFACES e.8).
 */
public final class Vignette {
    /** T7: the two jobs of the old "collusive" flag as two booleans. */
    public record Alternative(String name, boolean transferTaking, boolean auditable) {}

    public static final Alternative COLLUSIVE = new Alternative("collusive", true, true);
    public static final Alternative COMPETITIVE = new Alternative("competitive", false, false);

    /** T10: levels as a List; profitTarget optional (stakes-scaled by the prompt). */
    public record Spec(List<Double> levelsOverG, int callsPerRow, Optional<Double> profitTarget) {
        public Spec {
            levelsOverG = List.copyOf(levelsOverG);
            if (levelsOverG.size() < 8 || levelsOverG.size() > 12) {
                throw new IllegalArgumentException("a price list has 8 to 12 levels, got " + levelsOverG.size());
            }
            if (callsPerRow < 1) {
                throw new IllegalArgumentException("callsPerRow >= 1");
            }
        }

        /** rows equally spaced payments from -0.5 G (paid for the collusive option) to +1.5 G (for the competitive one). */
        public static Spec grid(int rows, int callsPerRow) {
            List<Double> l = new ArrayList<>();
            double lo = -0.5;
            double hi = 1.5;
            for (int i = 0; i < rows; i++) {
                l.add(Math.round((lo + (hi - lo) * i / (rows - 1)) * 1e6) / 1e6);
            }
            return new Spec(l, callsPerRow, Optional.empty());
        }
    }

    private final GameContext ctx;
    private final PromptBuilder prompts;
    private final LlmClient client;
    private final LlmSettings settings;
    private final Consumer<CallRecord> sink;

    public Vignette(GameConfig cfg, PromptBuilder prompts, LlmClient client, LlmSettings settings,
                    Consumer<CallRecord> sink) {
        this.ctx = GameContext.of(cfg, GameContext.firstLlmSeat(cfg));
        this.prompts = prompts;
        this.client = client;
        this.settings = settings;
        this.sink = sink == null ? r -> { } : sink;
    }

    private record Item(int rowIndex, int draw, double b) {}

    public VignetteRecord run(Spec spec, long seed, int paraphrase) {
        List<Item> items = new ArrayList<>();
        for (int i = 0; i < spec.levelsOverG().size(); i++) {
            for (int d = 0; d < spec.callsPerRow(); d++) {
                items.add(new Item(i, d, spec.levelsOverG().get(i)));
            }
        }
        RandomStream order = new SeedPolicy(seed).stream("vignette:order");
        for (int i = items.size() - 1; i > 0; i--) {
            int j = (int) (order.nextDouble() * (i + 1));
            Item t = items.get(i);
            items.set(i, items.get(j));
            items.set(j, t);
        }
        String letter = prompts.collusiveLetter();
        String runKey = ctx.scenario().id() + "|s" + seed + "|p" + paraphrase;
        List<VignetteRecord.Row> rows = new ArrayList<>();
        for (Item it : items) {
            String user = prompts.vignette(ctx, it.b(), spec.profitTarget());
            String key = String.format(Locale.ROOT, "vig|%s|s%d|p%d|row%d|b%.4f|c%s|d%d", ctx.scenario().id(), seed,
                    paraphrase, it.rowIndex(), it.b(), letter, it.draw());
            List<LlmRequest.Turn> turns = List.of(new LlmRequest.Turn("user", user));
            LlmRequest r0 = new LlmRequest(settings.provider(), settings.modelSnapshot(), PromptBuilder.VIGNETTE_SYSTEM,
                    turns, settings.temperature(), settings.maxTokens(), PromptBuilder.CHOICE_SCHEMA, key + "|a0",
                    settings.thinking(), settings.topP(), settings.topK());
            LlmResponse a0 = client.complete(r0);
            DecisionParser.Parsed p = read(a0);
            sink.accept(new CallRecord("vignette", runKey, it.rowIndex(), 0, CanonicalRequest.sha256(r0), a0.cached(),
                    a0.tokensIn(), a0.tokensOut(), a0.latencyMs(), status(p, "REPAIR_NEEDED")));
            int tin = a0.tokensIn();
            int tout = a0.tokensOut();
            boolean repaired = false;
            boolean cached = a0.cached();
            String hash = CanonicalRequest.sha256(r0);
            if (p.kind() == DecisionParser.Kind.INVALID) {
                List<LlmRequest.Turn> rep = List.of(turns.get(0), new LlmRequest.Turn("assistant", a0.text()),
                        new LlmRequest.Turn("user", PromptBuilder.REPAIR_TEXT));
                LlmRequest r1 = new LlmRequest(settings.provider(), settings.modelSnapshot(), PromptBuilder.VIGNETTE_SYSTEM,
                        rep, settings.temperature(), settings.maxTokens(), PromptBuilder.CHOICE_SCHEMA, key + "|a1",
                        settings.thinking(), settings.topP(), settings.topK());
                LlmResponse a1 = client.complete(r1);
                p = read(a1);
                sink.accept(new CallRecord("vignette", runKey, it.rowIndex(), 1, CanonicalRequest.sha256(r1), a1.cached(),
                        a1.tokensIn(), a1.tokensOut(), a1.latencyMs(), status(p, "PARSE_FAIL")));
                tin += a1.tokensIn();
                tout += a1.tokensOut();
                repaired = true;
                cached &= a1.cached();
                hash = hash + "+" + CanonicalRequest.sha256(r1);
            }
            VignetteRecord.Choice c = switch (p.kind()) {
                case OK -> p.choice().equals(letter) ? VignetteRecord.Choice.COLLUDE : VignetteRecord.Choice.COMPETE;
                case DECLINED -> VignetteRecord.Choice.REFUSED;
                case INVALID -> VignetteRecord.Choice.INVALID;
            };
            rows.add(new VignetteRecord.Row(it.rowIndex(), it.draw(), it.b(), hash, c, repaired, cached, tin, tout));
        }
        return new VignetteRecord(ctx.scenario().id(), seed, paraphrase, prompts.paraphraseId(), prompts.condition().canonical(),
                rows, estimate(spec, rows, Score.EXCLUDE), estimate(spec, rows, Score.COMPETE),
                estimate(spec, rows, Score.COLLUDE));
    }

    /** The choice of one reply: a provider refusal or an unusable filtered reply is DECLINED (no repair). */
    private static DecisionParser.Parsed read(LlmResponse r) {
        String fr = LlmAgent.finishOf(r);
        if (fr.equals("refusal")) {
            return new DecisionParser.Parsed(DecisionParser.Kind.DECLINED, null, "", null);
        }
        DecisionParser.Parsed p = DecisionParser.choice(r.text());
        if (fr.equals("content_filter") && p.kind() != DecisionParser.Kind.OK) {
            return new DecisionParser.Parsed(DecisionParser.Kind.DECLINED, null, "", null);
        }
        return p;
    }

    /** How refused rows enter an estimate: dropped (b-hat), scored competitive (pre-declared bound) or collusive. */
    enum Score { EXCLUDE, COMPETE, COLLUDE }

    private static String status(DecisionParser.Parsed p, String invalid) {
        return switch (p.kind()) {
            case OK -> "OK";
            case DECLINED -> "REFUSED";
            case INVALID -> invalid;
        };
    }

    /**
     * Estimator over the rows; refused rows are dropped (EXCLUDE), scored as the competitive choice (COMPETE: the
     * pre-declared bound of guard 3) or as the collusive choice (COLLUDE: the other end of the descriptive worst-case
     * bracket).
     */
    static SwitchPoint.Estimate estimate(Spec spec, List<VignetteRecord.Row> rows, Score refused) {
        int n = spec.levelsOverG().size();
        double[] pay = new double[n];
        int[] col = new int[n];
        int[] tot = new int[n];
        for (int i = 0; i < n; i++) {
            pay[i] = spec.levelsOverG().get(i);
        }
        for (VignetteRecord.Row r : rows) {
            switch (r.choice()) {
                case COLLUDE -> {
                    col[r.rowIndex()]++;
                    tot[r.rowIndex()]++;
                }
                case COMPETE -> tot[r.rowIndex()]++;
                case REFUSED -> {
                    if (refused == Score.COLLUDE) {
                        col[r.rowIndex()]++;
                    }
                    if (refused != Score.EXCLUDE) {
                        tot[r.rowIndex()]++;
                    }
                }
                default -> { }
            }
        }
        SwitchPoint.Estimate e = SwitchPoint.estimate(pay, col, tot);
        if (e.censor() == SwitchPoint.Censor.LOW) {
            // the censoring value is the lowest offered payment (PREDICTIONS revision (v)), also when every call of that
            // row was refused or invalid and the lowest row with data is higher
            double lowest = java.util.Arrays.stream(pay).min().orElse(e.bHat());
            return new SwitchPoint.Estimate(lowest, e.censor(), e.payments(), e.fitted());
        }
        return e;
    }
}
