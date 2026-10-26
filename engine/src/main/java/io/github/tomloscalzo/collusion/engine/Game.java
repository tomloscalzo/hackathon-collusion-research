package io.github.tomloscalzo.collusion.engine;

import io.github.tomloscalzo.collusion.agents.Agent;
import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.Horizon;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.mc.RandomStream;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;
import io.github.tomloscalzo.collusion.results.RoundRecord;
import io.github.tomloscalzo.collusion.results.RoundRecord.AgentRound;
import io.github.tomloscalzo.collusion.results.RoundRecord.DetectionRound;
import io.github.tomloscalzo.collusion.results.RunRecord;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * The round loop. Per round the engine draws a fixed number of values from each named stream: signal:id (1),
 * choice:id (1), demand:id (2), detection (2), horizon (1), whatever the branch taken, so rosters and run lengths do not
 * shift any other stream. Order inside a round: observation draws, decisions, settlement, demand noise, detection
 * (a trigger ends the run), horizon, cap.
 */
public final class Game {
    private final GameConfig cfg;
    private final SeatFactory seatFactory;
    private java.util.function.Consumer<RoundRecord> roundListener;
    private java.util.function.Consumer<List<Observation>> beforeDecisions;

    public Game(GameConfig cfg) {
        this(cfg, null);
    }

    /** seatFactory (may be null) builds the agents of kind LLM, which AgentFactory cannot (M4). */
    public Game(GameConfig cfg, SeatFactory seatFactory) {
        this.cfg = cfg;
        this.seatFactory = seatFactory;
    }

    /**
     * Logging hook (C4.3): called with each round's record right after the round is settled, before the next round
     * starts (also after the last round). It draws from no engine stream and cannot change this round's record; from
     * C13.3 it also makes the in-game question calls, whose answers the seats see in later prompts (so later decisions may
     * change), and an exception thrown in it ends the game as any failed call does. Null (the default) = none.
     */
    public Game onRound(java.util.function.Consumer<RoundRecord> listener) {
        this.roundListener = listener;
        return this;
    }

    /**
     * Pre-decision hook (C5.5, the talk phase): called once per round with every seat's observation of that round (roster
     * order), after the round's draws and before any seat decides. The observations are the ones the seats then decide
     * on; the hook draws from no engine stream. Null (the default) = none.
     */
    public Game beforeDecisions(java.util.function.Consumer<List<Observation>> hook) {
        this.beforeDecisions = hook;
        return this;
    }

    public RunRecord run(long seed) {
        Scenario sc = cfg.scenario();
        MarketParams m = sc.market();
        var op = cfg.observation();
        int n = cfg.agents().size();
        SeedPolicy seeds = new SeedPolicy(seed);
        List<String> ids = new ArrayList<>();
        List<Agent> agents = new ArrayList<>();
        List<RandomStream> demand = new ArrayList<>();
        List<RandomStream> signal = new ArrayList<>();
        List<RandomStream> choice = new ArrayList<>();
        boolean allMembers = true;
        for (AgentSpec a : cfg.agents()) {
            ids.add(a.id());
            agents.add(a.kind() == io.github.tomloscalzo.collusion.core.model.AgentKind.LLM && seatFactory != null
                    ? seatFactory.create(a, cfg, seeds, seed) : AgentFactory.create(a, sc, op, seeds));
            demand.add(seeds.stream(SeedPolicy.demand(a.id())));
            signal.add(seeds.stream(SeedPolicy.signal(a.id())));
            choice.add(seeds.stream(SeedPolicy.choice(a.id())));
            allMembers &= a.category() == AgentCategory.M;
        }
        RandomStream detStream = seeds.stream("detection");
        RandomStream horStream = seeds.stream("horizon");
        PayoffEngine pe = new PayoffEngine(m, true);
        DetectionProcess det = new DetectionProcess(sc, cfg.detection());
        double delta = sc.delta();
        double fine = sc.enforcement().fine();

        List<RoundRecord> rounds = new ArrayList<>();
        List<boolean[]> vis = new ArrayList<>();
        int evaluations = 0;
        int seen = 0;
        int falseAlarms = 0;
        RunStatus status = RunStatus.MAX_ROUNDS;
        double terminal = 0.0;
        int maxRounds = sc.time().maxRounds();

        for (int t = 1; t <= maxRounds; t++) {
            boolean[] v = new boolean[n];
            double[] cdraw = new double[n];
            for (int i = 0; i < n; i++) {
                v[i] = DeviationSignal.quotesVisible(signal.get(i), op.o());
                cdraw[i] = choice.get(i).nextDouble();
            }
            if (t > 1) {
                vis.add(v);
            }
            List<Observation> obs = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                obs.add(observation(i, t, ids, rounds, vis, cdraw[i]));
            }
            if (beforeDecisions != null) {
                beforeDecisions.accept(java.util.Collections.unmodifiableList(obs));
            }
            List<Decision> decisions = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                decisions.add(agents.get(i).decide(obs.get(i)));
            }
            List<Action.Quote> quotes = new ArrayList<>();
            boolean punishing = false;
            Set<Integer> excluded = new HashSet<>();
            for (int i = 0; i < n; i++) {
                Decision d = decisions.get(i);
                quotes.add(sanitize(m, d.action(), ids.get(i)));
                punishing |= d.punishing();
                for (String x : d.excludeFromContestable()) {
                    int idx = ids.indexOf(x);
                    if (idx < 0) {
                        throw new IllegalStateException("Unknown agent to exclude: " + x);
                    }
                    excluded.add(idx);
                }
            }
            PayoffEngine.Settlement st = pe.settle(quotes, excluded, allMembers, sc.aggregates().sumIRP());
            double[] z = new double[n];
            for (int i = 0; i < n; i++) {
                z[i] = demand.get(i).nextGaussian();
            }
            double uTrig = detStream.nextDouble();
            double uEv = detStream.nextDouble();
            double uHor = horStream.nextDouble();
            DetectionProcess.Step ds = det.step(st.insideQuote(), punishing, uTrig, uEv);

            RunStatus ended = null;
            if (ds.triggered()) {
                ended = ds.evidence() ? RunStatus.EVIDENCE : RunStatus.TRIGGER_ONLY;
            } else if (sc.time().horizon() instanceof Horizon.Random r ? uHor < r.h()
                    : t >= ((Horizon.Known) sc.time().horizon()).periods()) {
                ended = RunStatus.HORIZON;
            } else if (t >= maxRounds) {
                ended = RunStatus.MAX_ROUNDS;
            }

            List<AgentRound> ars = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                Decision d = decisions.get(i);
                Action.Quote q = quotes.get(i);
                Agent a = agents.get(i);
                if (d.signalEvaluated()) {
                    evaluations++;
                    if (d.signalSeen()) {
                        seen++;
                        if (!truthDeviation(a, i, quotes, rounds)) {
                            falseAlarms++;
                        }
                    }
                }
                double f = ds.evidence() && cfg.agents().get(i).category() == AgentCategory.M ? fine : 0.0;
                double vol = st.volumes().get(i);
                ars.add(new AgentRound(ids.get(i), q.displayed(), q.hiddenFill(),
                        PayoffFunctions.collusionIndex(m, q.displayed()), vol, z[i], vol + op.demandNoiseSd() * z[i],
                        st.fillPrices().get(i), st.payoffs().get(i), f, d.signalEvaluated(), d.signalSeen(),
                        t > 1 && v[i], d.phase(), st.excluded().get(i), d.info()));
            }
            rounds.add(new RoundRecord(t, ars, st.insideQuote(), PayoffFunctions.collusionIndex(m, st.insideQuote()),
                    new DetectionRound(ds.pTrigger(), ds.pEvidence(), ds.tipActive(), ds.triggered(), ds.evidence()),
                    ended));
            if (roundListener != null) {
                roundListener.accept(rounds.get(rounds.size() - 1));
            }
            if (ended != null) {
                status = ended;
                if (delta < 1.0) {
                    if (ended == RunStatus.TRIGGER_ONLY) {
                        terminal = sc.enforcement().piPost() / (1.0 - delta);
                    } else if (ended == RunStatus.EVIDENCE) {
                        terminal = PayoffFunctions.piNash(m) / (1.0 - delta);
                    }
                }
                break;
            }
        }
        return new RunRecord(sc.id(), seed, ids, rounds, status, terminal, evaluations, seen, falseAlarms,
                sc.aggregates().dBarU(), 0.0);
    }

    /** True if some rival effectively quoted below the agent reference minus tolerance in the previous round. */
    private boolean truthDeviation(Agent a, int self, List<Action.Quote> unused, List<RoundRecord> rounds) {
        var ref = a.signalReference();
        if (ref.isEmpty() || rounds.isEmpty()) {
            return false;
        }
        RoundRecord last = rounds.get(rounds.size() - 1);
        for (int j = 0; j < last.agents().size(); j++) {
            if (j == self) {
                continue;
            }
            AgentRound r = last.agents().get(j);
            double eff = r.hiddenFill() == null ? r.displayed() : Math.min(r.displayed(), r.hiddenFill());
            if (eff < ref.get().margin() - ref.get().tolerance() - 1e-9) {
                return true;
            }
        }
        return false;
    }

    private Action.Quote sanitize(MarketParams m, Action.Quote q, String id) {
        if (q == null || Double.isNaN(q.displayed())) {
            throw new IllegalStateException("Agent " + id + " returned no valid quote");
        }
        double d = QuoteGrid.snap(m, q.displayed());
        Double h = null;
        if (q.hiddenFill() != null && !Double.isNaN(q.hiddenFill())) {
            double hs = QuoteGrid.snap(m, q.hiddenFill());
            if (hs < d - 1e-12) {
                h = hs;
            }
        }
        return new Action.Quote(d, h);
    }

    private Observation observation(int i, int t, List<String> ids, List<RoundRecord> rounds, List<boolean[]> vis,
                                    double choiceDraw) {
        int w = cfg.history().window();
        int from = w <= 0 ? 0 : Math.max(0, rounds.size() - w);
        List<Observation.PastRound> hist = new ArrayList<>();
        var op = cfg.observation();
        for (int r = from; r < rounds.size(); r++) {
            RoundRecord rec = rounds.get(r);
            AgentRound me = rec.agents().get(i);
            boolean visible = vis.get(r)[i];
            Map<String, Double> rivals = new TreeMap<>();
            if (visible) {
                for (AgentRound o : rec.agents()) {
                    if (!o.id().equals(me.id())) {
                        rivals.put(o.id(), o.displayed());
                    }
                }
            }
            hist.add(new Observation.PastRound(rec.round(), me.displayed(), me.hiddenFill(), visible, rivals,
                    visible ? rec.insideQuote() : null, op.showOwnVolume() ? me.observedVolume() : null,
                    op.showFillPrice() ? me.fillPrice() : null, me.excluded()));
        }
        return new Observation(t, ids.get(i), ids, hist, choiceDraw);
    }
}
