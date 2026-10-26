package io.github.tomloscalzo.collusion.agents.llm;

import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.Observation;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Token and call estimate made before any call (no network): prompt tokens are estimated as characters / 4 of the
 * actually rendered prompts (system + turn with a synthetic history of the window length); completion tokens are an
 * assumption (default 120 for a game decision, 60 for a vignette answer). A repair retry rate (default 2%) adds calls.
 */
public final class CostEstimator {
    public static final double CHARS_PER_TOKEN = 4.0;

    private CostEstimator() {}

    public record Estimate(String kind, long calls, long tokensIn, long tokensOut, double avgTokensInPerCall) {
        public long totalTokens() {
            return tokensIn + tokensOut;
        }
    }

    public static long tokens(String text) {
        return (long) Math.ceil(text.length() / CHARS_PER_TOKEN);
    }

    public static Estimate game(GameConfig cfg, Condition cond, int paraphrase, int runs, int rounds, int outTokensPerCall,
                                double repairRate) {
        GameContext ctx = GameContext.of(cfg, GameContext.firstLlmSeat(cfg));
        PromptBuilder pb = new PromptBuilder(cond, paraphrase);
        long sys = tokens(pb.gameSystem(ctx));
        double sp = ctx.sP();
        long perRunIn = 0;
        for (int r = 1; r <= rounds; r++) {
            int h = ctx.historyWindow() <= 0 ? r - 1 : Math.min(r - 1, ctx.historyWindow());
            List<Observation.PastRound> hist = new ArrayList<>();
            for (int k = r - h; k < r; k++) {
                Map<String, Double> riv = new java.util.TreeMap<>();
                for (String pid : ctx.partnerIds()) {
                    riv.put(pid, sp);
                }
                hist.add(new Observation.PastRound(k, sp, null, true, riv, sp, 50.0, sp, false));
            }
            Observation obs = new Observation(r, ctx.seatId(), List.of(ctx.seatId()), hist, 0.5);
            String plan = "Keep quoting " + String.format(java.util.Locale.ROOT, "%.2f", sp)
                    + " while the other market maker does the same; reconsider if it deviates.";
            perRunIn += sys + tokens(pb.gameTurn(ctx, obs, plan));
        }
        long calls = Math.round((double) runs * rounds * (1.0 + repairRate));
        long in = Math.round(perRunIn * (double) runs * (1.0 + repairRate));
        long out = Math.round((double) runs * rounds * outTokensPerCall * (1.0 + repairRate));
        return new Estimate("game", calls, in, out, calls == 0 ? 0 : (double) in / calls);
    }

    public static Estimate vignette(GameConfig cfg, Condition cond, int paraphrase, int levels, int callsPerRow, int passes,
                                    int outTokensPerCall, double repairRate) {
        GameContext ctx = GameContext.of(cfg, GameContext.firstLlmSeat(cfg));
        PromptBuilder pb = new PromptBuilder(cond, paraphrase);
        long perCall = tokens(PromptBuilder.VIGNETTE_SYSTEM) + tokens(pb.vignette(ctx, 0.5, Optional.empty()));
        long calls = Math.round((double) levels * callsPerRow * passes * (1.0 + repairRate));
        return new Estimate("vignette", calls, calls * perCall, calls * outTokensPerCall, (double) perCall);
    }
}
