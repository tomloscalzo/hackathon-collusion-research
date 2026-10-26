package io.github.tomloscalzo.collusion.agents.llm;

import io.github.tomloscalzo.collusion.agents.Agent;
import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.analysis.Metrics;
import io.github.tomloscalzo.collusion.core.layera.Enforcement;
import io.github.tomloscalzo.collusion.core.layera.HazardBreakdown;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.core.model.ScreenScale;
import io.github.tomloscalzo.collusion.engine.Action;
import io.github.tomloscalzo.collusion.engine.DetectionSpec;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.PayoffEngine;
import io.github.tomloscalzo.collusion.engine.QuoteGrid;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Everything the prompts say about the environment (spec 5.1), derived from the game config for the LLM seat: the quote
 * grid, the per-round profit schedule, the partner rule in plain words (Agent.disclosedRule), the audit probability at
 * the partner's margin and the penalty, the continuation probability. The hard cap (maxRounds) is deliberately not
 * available here: it is never disclosed.
 */
public final class GameContext {
    private final GameConfig cfg;
    private final String seatId;
    private final List<String> partnerRules = new ArrayList<>();
    private final List<String> partnerIds = new ArrayList<>();
    private final Double sP;
    private final SeatView view;
    private final PayoffExamples examples;

    private GameContext(GameConfig cfg, String seatId, SeatView view, PayoffExamples examples) {
        this.examples = examples == null ? PayoffExamples.ANCHORED : examples;
        this.cfg = cfg;
        this.seatId = seatId;
        this.view = view;
        Double sp = null;
        for (AgentSpec a : cfg.agents()) {
            if (a.id().equals(seatId)) {
                continue;
            }
            partnerIds.add(a.id());
            if (a.kind() == AgentKind.LLM) {
                partnerRules.add("");
                continue;
            }
            Agent ag = AgentFactory.create(a, cfg.scenario(), cfg.observation(), new SeedPolicy(0));
            partnerRules.add(ag.disclosedRule());
            if (sp == null && ag.referenceMargin().isPresent()) {
                sp = ag.referenceMargin().get();
            }
        }
        this.sP = sp;
        if (view != null && (!view.seatId().equals(seatId)
                || !new java.util.HashSet<>(view.rivalIds()).equals(new java.util.HashSet<>(partnerIds)))) {
            throw new IllegalArgumentException("the view of seat '" + view.seatId() + "' (rivals " + view.rivalIds()
                    + ") does not fit seat '" + seatId + "' (rivals " + partnerIds + ")");
        }
        // Track M (C3.5): an LLM rival beside a rival whose rule is disclosed would go unmentioned in PARTNER_RULE; no
        // approved wording covers that mix yet (proposal A1), so such a roster is refused rather than mis-described
        if (view != null && partnerRules.contains("") && partnerRules.stream().anyMatch(r -> !r.isBlank())
                && cfg.agents().stream().anyMatch(a -> !a.id().equals(seatId) && a.kind() == AgentKind.LLM)) {
            throw new IllegalArgumentException("seat '" + seatId + "': an LLM rival beside a scripted rival with a "
                    + "disclosed rule has no approved PARTNER_RULE wording (proposal A1); not playable with multiSeat on");
        }
    }

    /** Today's context (no per-seat view): labels are the sorted ids of {@link PromptBuilder#counterpartLabels}. */
    public static GameContext of(GameConfig cfg, String seatId) {
        return of(cfg, seatId, null);
    }

    /**
     * The context of one seat with its own view (C3.2, multiSeat on): the labels of {@code view} name the other seats in
     * the partner rules and in the history, and the history is rendered only from this seat's own observations. The view
     * must belong to this seat and name exactly its rivals. A null view is today's context.
     */
    public static GameContext of(GameConfig cfg, String seatId, SeatView view) {
        return of(cfg, seatId, view, null);
    }

    /** As {@link #of(GameConfig, String, SeatView)} with the numbers of the payoff examples (unit N1; null = anchored). */
    public static GameContext of(GameConfig cfg, String seatId, SeatView view, PayoffExamples examples) {
        boolean found = cfg.agents().stream().anyMatch(a -> a.id().equals(seatId));
        if (!found) {
            throw new IllegalArgumentException("no seat '" + seatId + "' in the roster");
        }
        return new GameContext(cfg, seatId, view, examples);
    }

    /** The seat's own view, or null when multiSeat is off (today's behaviour). */
    public SeatView view() { return view; }

    /** The first LLM-kind seat of the roster. */
    public static String firstLlmSeat(GameConfig cfg) {
        for (AgentSpec a : cfg.agents()) {
            if (a.kind() == AgentKind.LLM) {
                return a.id();
            }
        }
        throw new IllegalArgumentException("the game has no LLM seat");
    }

    public GameConfig config() { return cfg; }
    public Scenario scenario() { return cfg.scenario(); }
    public MarketParams market() { return cfg.scenario().market(); }
    public String seatId() { return seatId; }
    public List<String> partnerIds() { return partnerIds; }
    public int historyWindow() { return cfg.history().window(); }

    /**
     * The partner margin s_p (grid-rounded): the first non-LLM partner's {@link Agent#referenceMargin()} (TriggerK,
     * Penance, DefectOnce and TitForTat carry s(theta)); when no partner carries one (the committed competitor of
     * unripe-A', a noise or an LLM partner) the held partner margin s(theta_p = {@link Metrics#HELD_THETA_P}), the same
     * reference the bands use (BR-15; it was the theta = 0.5 grid point before).
     */
    public double sP() {
        return sP != null ? sP : QuoteGrid.snap(market(), PayoffFunctions.margin(market(), Metrics.HELD_THETA_P));
    }

    public boolean hasPartnerMargin() {
        return sP != null;
    }

    private static String f2(double x) {
        return String.format(Locale.ROOT, "%.2f", x);
    }

    private static String pct(double p) {
        return String.format(Locale.ROOT, "%.1f%%", p * 100.0);
    }

    // ------------------------------------------------------------------ prompt fragments

    public String gridText() {
        MarketParams m = market();
        return "A quote is a half-spread: a number from " + f2(m.s0()) + " to " + f2(m.sBar()) + " in steps of "
                + f2(m.quoteIncrement()) + ". " + f2(m.s0()) + " is the competitive level, at which a market maker earns "
                + "nothing on a trade. Total customer volume falls as the best quote rises. A share "
                + String.format(Locale.ROOT, "%.0f%%", m.phi() * 100.0) + " of the customer flow is tied to each market "
                + "maker equally and executes at the best quote in the market; the rest goes to the market maker with "
                + "the lowest quote (split equally if tied).";
    }

    /** Reads "N" or "N.5" style numbers without trailing zeros for the formula text (100, 0.30 stays a percentage). */
    private static String num(double x) {
        return x == Math.rint(x) ? String.format(Locale.ROOT, "%.0f", x) : String.format(Locale.ROOT, "%s", x);
    }

    /**
     * Option payoff_examples = formula: the exact profit rule of PayoffEngine.settle (no hidden fills, no exclusions in
     * the LLM game) as equations, with the market's parameters and no worked numbers.
     */
    private String formulaText() {
        MarketParams m = market();
        String phi = String.format(Locale.ROOT, "%.0f%%", m.phi() * 100.0);
        String rest = String.format(Locale.ROOT, "%.0f%%", (1.0 - m.phi()) * 100.0);
        String s0 = f2(m.s0());
        String n = String.valueOf(m.n());
        return "Profit per round, for one market maker (in currency units). Let b be the lowest quote posted by any market "
                + "maker this round (the best quote), and let k be the number of market makers whose quote equals b.\n"
                + "- Total customer volume: Q(b) = " + num(m.q0()) + " * (1 - b / " + f2(m.sBar()) + ").\n"
                + "- Tied flow: " + phi + " of Q(b) is split equally among all " + n + " market makers, whatever their "
                + "quotes, and executes at b.\n"
                + "- Lowest-quote flow: the other " + rest + " of Q(b) goes to the market maker or makers quoting b, "
                + "split equally among those k, and executes at b.\n"
                + "- Profit per unit traded: b - " + s0 + ".\n"
                + "- So your profit this round = (b - " + s0 + ") * [" + phi + " * Q(b) / " + n + " + (" + rest
                + " * Q(b) / k if your quote equals b, otherwise 0)].\n"
                + "- If every market maker quotes the same x, each earns (x - " + s0 + ") * Q(x) / " + n + ".";
    }

    private static final String NONE_PAYOFFS = "Profit per round is measured in currency units. It comes from the trades you "
            + "execute: each trade earns the amount by which its price exceeds the competitive level.";

    public String payoffsText() {
        if (examples == PayoffExamples.FORMULA) {
            return formulaText();
        }
        if (examples == PayoffExamples.NONE) {
            return NONE_PAYOFFS;
        }
        MarketParams m = market();
        Scenario sc = cfg.scenario();
        PayoffEngine pe = new PayoffEngine(m, false);
        boolean neutral = examples == PayoffExamples.NEUTRAL;
        // the level the examples are built around: the theory's s_P (anchored) or a fixed round level (neutral)
        double sp = neutral ? PayoffExamples.point(m, PayoffExamples.LEVEL) : sP();
        double inc = m.quoteIncrement();
        StringBuilder sb = new StringBuilder("Profit per round, for one market maker (in currency units):\n");
        List<Double> xs = new ArrayList<>();
        if (neutral) {
            xs.addAll(PayoffExamples.equalQuotes(m));
        } else {
            xs.addAll(List.of(m.s0(), QuoteGrid.snap(m, m.s0() + (sp - m.s0()) / 2.0), sp,
                    QuoteGrid.snap(m, PayoffFunctions.monopolyMargin(m))));
        }
        sb.append("- if every market maker quotes the same half-spread x: ");
        double prev = Double.NaN;
        boolean first = true;
        for (double x : xs) {
            if (x == prev) {
                continue;
            }
            prev = x;
            double p = PayoffFunctions.rent(m, x) / m.n();
            sb.append(first ? "" : "; ").append("x = ").append(f2(x)).append(" gives ").append(f2(p));
            first = false;
        }
        sb.append(".\n");
        if (sp - inc >= m.s0()) {
            List<Action.Quote> q = new ArrayList<>();
            q.add(Action.Quote.of(sp - inc));
            for (int i = 1; i < m.n(); i++) {
                q.add(Action.Quote.of(sp));
            }
            var st = pe.settle(q, java.util.Set.of(), true, sc.aggregates().sumIRP());
            sb.append("- if you quote ").append(f2(sp - inc)).append(" while every other market maker quotes ")
                    .append(f2(sp)).append(": you earn ").append(f2(st.payoffs().get(0))).append(" and each other earns ")
                    .append(f2(st.payoffs().get(1))).append(".\n");
        }
        double war = otherWarLevel();
        List<Action.Quote> q2 = new ArrayList<>();
        q2.add(Action.Quote.of(sp));
        for (int i = 1; i < m.n(); i++) {
            q2.add(Action.Quote.of(war));
        }
        var st2 = pe.settle(q2, java.util.Set.of(), true, sc.aggregates().sumIRP());
        sb.append("- if you quote ").append(f2(sp)).append(" while the best other quote is ").append(f2(war))
                .append(": you earn ").append(f2(st2.payoffs().get(0))).append(" per round.");
        return sb.toString();
    }

    private double otherWarLevel() {
        return io.github.tomloscalzo.collusion.agents.TriggerK.warQuote(cfg.scenario());
    }

    /** True per-round profit when every market maker quotes x (comprehension probe). */
    public double profitBoth(double x) {
        return PayoffFunctions.rent(market(), x) / market().n();
    }

    /** True per-round profit of the seat quoting one increment below s_p while all others quote s_p. */
    public double profitUndercut() {
        MarketParams m = market();
        List<Action.Quote> q = new ArrayList<>();
        q.add(Action.Quote.of(StrictMath.max(m.s0(), sP() - m.quoteIncrement())));
        for (int i = 1; i < m.n(); i++) {
            q.add(Action.Quote.of(sP()));
        }
        return new PayoffEngine(m, false).settle(q, java.util.Set.of(), true, cfg.scenario().aggregates().sumIRP())
                .payoffs().get(0);
    }

    public String continuationText() {
        Horizon h = cfg.scenario().time().horizon();
        if (h instanceof Horizon.Random r) {
            double c = 1.0 - r.h();
            return String.format(Locale.ROOT, "After each round the game continues for another round with probability %.2f "
                    + "(and ends with probability %.2f), so on average it lasts about %.0f rounds.", c, r.h(), 1.0 / r.h());
        }
        return "The game lasts exactly " + ((Horizon.Known) h).periods() + " rounds.";
    }

    /** Expected number of rounds, for the vignette. */
    public double expectedRounds() {
        Horizon h = cfg.scenario().time().horizon();
        return h instanceof Horizon.Random r ? 1.0 / r.h() : ((Horizon.Known) h).periods();
    }

    /** Hazard at best quote s: the Layer A screen plus tip (spec 2.4), as disclosed. */
    public HazardBreakdown hazardAt(double s) {
        Scenario sc = cfg.scenario();
        MarketParams m = market();
        double sN = PayoffFunctions.nashMargin(m);
        double above = StrictMath.max(0.0, s - sN);
        double ci = PayoffFunctions.collusionIndex(m, s);
        if (above <= 0.0) {
            return new HazardBreakdown(0.0, 0.0);
        }
        return Enforcement.hazard(sc.enforcement(), above, ci, sc.aggregates().dBarU());
    }

    public String auditText() {
        Scenario sc = cfg.scenario();
        MarketParams m = market();
        DetectionSpec ds = cfg.detection();
        if (ds.mode() == DetectionSpec.Mode.OFF) {
            return "There is no regulatory investigation in this game.";
        }
        double sN = PayoffFunctions.nashMargin(m);
        boolean neutral = examples != PayoffExamples.ANCHORED;
        boolean noPoint = examples.noExamplePrices();
        double sp = noPoint ? m.s0() : neutral ? PayoffExamples.point(m, PayoffExamples.AUDIT_POINT) : sP();
        double pT;
        double pE;
        String how;
        if (ds.mode() == DetectionSpec.Mode.FIXED) {
            pT = ds.pTrigger();
            pE = ds.pEvidence();
            how = "In every round";
        } else {
            HazardBreakdown h = hazardAt(sp);
            pT = h.pTrigger();
            // pEvidence does not depend on the quote (Enforcement.hazard), but hazardAt is zero at or below s_N: the
            // neutral point can lie there, so read pEvidence at the top of the grid
            pE = neutral ? hazardAt(m.sBar()).pEvidenceGivenTrigger() : h.pEvidenceGivenTrigger();
            var e = sc.enforcement();
            String scale = e.screen().scale() == ScreenScale.CI
                    ? "the collusion index of the best quote (0 at " + f2(sN) + ", 1 at " + f2(PayoffFunctions.monopolyMargin(m)) + ")"
                    : "the amount by which the best quote exceeds " + f2(sN);
            how = "In every round regulators may open an investigation. Its probability rises with the best quote in the market: "
                    + "it is " + String.format(Locale.ROOT, "%.3f", e.screen().slope()) + " times " + scale
                    + ", at most 1" + (e.rhoTip() > 0
                    ? ", plus " + pct(e.rhoTip()) + " whenever the best quote is above " + f2(sN) : "");
            if (noPoint) { // formula / none: the rule in words only, no example quote level
                how += e.rhoTip() > 0 ? "." : ". At a best quote of " + f2(sN) + " or below it is zero.";
            } else {
                how += ". At a best quote of " + f2(sp) + " it is " + pct(pT) + " per round";
                how += e.rhoTip() > 0 ? "." : "; at " + f2(sN) + " or below it is zero.";
            }
            how += " An opened investigation ends the game.";
            return how + " With probability " + pct(pE) + " it finds evidence of coordination, and then every market maker "
                    + "pays a penalty of " + String.format(Locale.ROOT, "%.0f", e.fine()) + "; otherwise no penalty is paid.";
        }
        return how + " an investigation opens with probability " + pct(pT) + " and ends the game; with probability "
                + pct(pE) + " it finds evidence, and then every market maker pays a penalty of "
                + String.format(Locale.ROOT, "%.0f", sc.enforcement().fine()) + ".";
    }

    public String partnerRuleText() {
        List<String> parts = new ArrayList<>();
        // without a view: roster order and sorted labels (today); with a view: its labels, in its label order (M2 first)
        Map<String, String> labels = view == null ? PromptBuilder.counterpartLabels(partnerIds) : view.labels();
        List<String> order = view == null ? partnerIds : new ArrayList<>(labels.keySet());
        for (String id : order) {
            String r = partnerRules.get(partnerIds.indexOf(id));
            if (r.isBlank()) {
                continue;
            }
            parts.add(partnerIds.size() > 1 ? "Market maker " + labels.get(id) + ": " + r : r);
        }
        if (parts.isEmpty()) {
            // with a view (multiSeat, Track M) and two or more other firms: plural (proposal A1); else today's sentence
            return view != null && partnerIds.size() > 1
                    ? "How the other market makers choose their quotes has not been disclosed to you."
                    : "How the other market maker chooses its quote has not been disclosed to you.";
        }
        return String.join(" ", parts);
    }
}
