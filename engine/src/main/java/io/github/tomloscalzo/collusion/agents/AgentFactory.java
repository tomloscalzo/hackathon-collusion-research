package io.github.tomloscalzo.collusion.agents;

import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.ObservationPolicy;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;
import java.util.Map;
import java.util.Set;

/** Builds a fresh scripted agent from its spec; unknown or missing config keys are errors. k &lt; 0 means infinite. */
public final class AgentFactory {
    private AgentFactory() {}

    public static Agent create(AgentSpec spec, Scenario sc, ObservationPolicy op) {
        return create(spec, sc, op, null);
    }

    /**
     * seeds is needed only by agents with their own random stream (NOISE, stream noise:&lt;id&gt;) and by a DEFECT_ONCE
     * agent whose t is drawn from the run seed (tMin/tMax, see {@link #defectRound}).
     */
    public static Agent create(AgentSpec spec, Scenario sc, ObservationPolicy op, SeedPolicy seeds) {
        Map<String, Object> c = spec.config();
        double inc = sc.market().quoteIncrement();
        switch (spec.kind()) {
            case TRIGGER_K -> {
                allow(spec, Set.of("theta", "k", "tolerance", "hiddenFillFromRound", "hiddenFillDelta", "falseSignalAtRound"));
                return new TriggerK(spec.id(), sc, op, req(spec, "theta"), (int) opt(c, "k", -1),
                        opt(c, "tolerance", 0.0), (int) opt(c, "hiddenFillFromRound", 0), opt(c, "hiddenFillDelta", inc),
                        (int) opt(c, "falseSignalAtRound", 0));
            }
            case TIT_FOR_TAT -> {
                allow(spec, Set.of("theta", "injectAtRound"));
                return new ScriptedAgents.TitForTat(spec.id(), sc, req(spec, "theta"), (int) opt(c, "injectAtRound", 0));
            }
            case PENANCE -> {
                allow(spec, Set.of("theta", "k", "tolerance"));
                return new ScriptedAgents.Penance(spec.id(), sc, req(spec, "theta"), (int) req(spec, "k"),
                        opt(c, "tolerance", 0.0));
            }
            case DEFECT_ONCE -> {
                allow(spec, Set.of("theta", "t", "tMin", "tMax", "placebo"));
                int t = defectRound(spec, seeds == null ? 1L : seeds.masterSeed());
                if (!c.containsKey("t") && seeds == null) {
                    throw new IllegalArgumentException("Agent " + spec.id() + ": DEFECT_ONCE with tMin/tMax needs a SeedPolicy");
                }
                if (!c.containsKey("t") && sc.time().maxRounds() < (long) whole(spec, "tMax") + 3L) {
                    throw new IllegalArgumentException("Agent " + spec.id() + ": maxRounds " + sc.time().maxRounds()
                            + " must be at least tMax + 3 (spec 5.6: t + 3 is always reachable)");
                }
                return new ScriptedAgents.DefectOnce(spec.id(), sc, req(spec, "theta"), t, placebo(spec));
            }
            case ALWAYS_COMPETE -> {
                allow(spec, Set.of());
                return new ScriptedAgents.AlwaysCompete(spec.id(), sc);
            }
            case UNDERCUTTER -> {
                allow(spec, Set.of("open", "step"));
                double step = opt(c, "step", 1);
                if (step < 1 || step != StrictMath.rint(step)) {
                    throw new IllegalArgumentException("Agent " + spec.id() + ": step must be a whole number of ticks >= 1");
                }
                return new ScriptedAgents.Undercutter(spec.id(), sc, req(spec, "open"), (int) step);
            }
            case COPIER -> {
                allow(spec, Set.of("open"));
                return new ScriptedAgents.Copier(spec.id(), sc, req(spec, "open"));
            }
            case LOGIT -> {
                allow(spec, Set.of("lambda0", "sigma", "partnerTheta", "partnerK", "partnerTolerance"));
                return new LogitAgent(spec.id(), sc, opt(c, "lambda0", 0.0), opt(c, "sigma", 0.0),
                        req(spec, "partnerTheta"), (int) opt(c, "partnerK", 3), opt(c, "partnerTolerance", 0.0));
            }
            case NOISE -> {
                allow(spec, Set.of());
                if (seeds == null) {
                    throw new IllegalArgumentException("Agent " + spec.id() + ": NOISE needs a SeedPolicy");
                }
                return new NoiseAgent(spec.id(), sc, seeds.stream(NoiseAgent.streamName(spec.id())));
            }
            case LLM -> throw new IllegalArgumentException("Agent " + spec.id()
                    + ": the LLM seat is a placeholder (filled by LlmAgent in M4 or by a scripted agent in a sweep cell)");
            default -> throw new IllegalArgumentException("Unknown agent kind " + spec.kind());
        }
    }

    /**
     * The defection round of a DEFECT_ONCE spec in the run with this seed (spec 5.6, BR-15): the fixed {@code t} when the
     * config has one; otherwise {@code tMin + floorMod(runSeed - 1, tMax - tMin + 1)}, a fixed balanced cycle over
     * tMin..tMax in the run seed, not a random draw (with 6..10: seeds 1, 2, 3, 4, 5 give 6, 7, 8, 9, 10, and every block
     * of five consecutive seeds gives each t once). Seed s plays the role of the reference bands' seed index s - 1
     * (probeTs[seedIndex mod 5], FactorialDesign.probeT). The rule uses the run seed only, so the probe and the placebo
     * control of one (paraphrase, seed) cell get the same t. For a placebo spec it is the placebo round. t is never
     * disclosed.
     */
    public static int defectRound(AgentSpec spec, long runSeed) {
        Map<String, Object> c = spec.config();
        boolean fixed = c.containsKey("t");
        boolean drawn = c.containsKey("tMin") || c.containsKey("tMax");
        if (fixed == drawn) {
            throw new IllegalArgumentException("Agent " + spec.id() + ": DEFECT_ONCE takes either t or both tMin and tMax");
        }
        if (fixed) {
            return (int) req(spec, "t");
        }
        int lo = whole(spec, "tMin");
        int hi = whole(spec, "tMax");
        if (lo < 4 || hi < lo) {
            throw new IllegalArgumentException("Agent " + spec.id() + ": DEFECT_ONCE needs 4 <= tMin <= tMax (the inclusion "
                    + "rule reads the three rounds before t)");
        }
        return (int) (lo + Math.floorMod(runSeed - 1L, (long) hi - lo + 1L));
    }

    /** A numeric config value that must be a whole number in the int range (tMin, tMax). */
    private static int whole(AgentSpec spec, String key) {
        double v = req(spec, key);
        if (v != StrictMath.rint(v) || v < Integer.MIN_VALUE || v > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("Agent " + spec.id() + ": " + key + " must be a whole number");
        }
        return (int) v;
    }

    /** True when a DEFECT_ONCE spec is the never-defecting placebo control ({@code placebo: 1}; 0 or absent: not). */
    public static boolean placebo(AgentSpec spec) {
        Object v = spec.config().get("placebo");
        if (v == null) {
            return false;
        }
        if (!(v instanceof Number n) || (n.doubleValue() != 0.0 && n.doubleValue() != 1.0)) {
            throw new IllegalArgumentException("Agent " + spec.id() + ": placebo must be 0 or 1");
        }
        return n.doubleValue() == 1.0;
    }

    private static void allow(AgentSpec spec, Set<String> keys) {
        for (String k : spec.config().keySet()) {
            if (!keys.contains(k)) {
                throw new IllegalArgumentException("Agent " + spec.id() + ": unknown config key '" + k + "'");
            }
        }
    }

    private static double req(AgentSpec spec, String key) {
        Object v = spec.config().get(key);
        if (!(v instanceof Number n)) {
            throw new IllegalArgumentException("Agent " + spec.id() + ": numeric config '" + key + "' is required");
        }
        return n.doubleValue();
    }

    private static double opt(Map<String, Object> c, String key, double dflt) {
        Object v = c.get(key);
        if (v == null) {
            return dflt;
        }
        if (!(v instanceof Number n)) {
            throw new IllegalArgumentException("Config '" + key + "' must be numeric");
        }
        return n.doubleValue();
    }

    /** Convenience: the margin s(theta) for the scenario market. */
    public static double margin(Scenario sc, double theta) {
        return PayoffFunctions.margin(sc.market(), theta);
    }
}
