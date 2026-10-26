import io.github.tomloscalzo.collusion.agents.llm.Condition;
import io.github.tomloscalzo.collusion.agents.llm.GameContext;
import io.github.tomloscalzo.collusion.agents.llm.PromptBuilder;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Local helper for the interface document (not part of the engine build): renders the paraphrase-0 prompts for ripe-game so the interface doc can quote real text. */
public class PromptDump {
    public static void main(String[] a) {
        GameConfig cfg = GameConfigLoader.loadResource(a.length > 0 ? a[0] : "scenarios/ripe-game.yaml");
        GameContext ctx = GameContext.of(cfg, GameContext.firstLlmSeat(cfg));
        PromptBuilder pb = new PromptBuilder(Condition.neutral(), 0);
        System.out.println("=== SYSTEM (paraphrase 0, neutral)\n" + pb.gameSystem(ctx));
        Map<String, Double> riv = new java.util.TreeMap<>();
        for (String id : ctx.partnerIds()) {
            riv.put(id, 2.09);
        }
        List<String> ids = cfg.agents().stream().map(s -> s.id()).toList();
        Observation obs = new Observation(3, ctx.seatId(), ids, List.of(
                new Observation.PastRound(1, 2.09, null, false, Map.of(), null, 30.82, 2.09, false),
                new Observation.PastRound(2, 2.09, null, true, riv, 2.09, 30.82, 2.09, false)), 0.5);
        System.out.println("=== TURN (round 3)\n" + pb.gameTurn(ctx, obs, "hold 2.09"));
        System.out.println("=== VIGNETTE (b/G = +0.5)\n" + pb.vignette(ctx, 0.5, Optional.empty()));
        System.out.println("=== FORMAT\n" + PromptBuilder.decisionFormat(cfg.scenario().market()));
    }
}
