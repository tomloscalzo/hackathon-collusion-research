package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.Observation;
import io.github.tomloscalzo.collusion.llm.CanonicalRequest;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.LlmRequest;
import io.github.tomloscalzo.collusion.llm.LlmResponse;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

/** C3.2: per-seat views in the game loop, behind the multiSeat switch of LlmGame.run (off by default). */
class MultiSeatViewTest {
    static final LlmSettings SETTINGS = new LlmSettings("openai-compatible", "mock-model-1", 0.7, 300);
    static final Pattern KEY = Pattern.compile("game\\|[^|]+\\|s\\d+\\|([^|]+)\\|r(\\d+)\\|a\\d");

    static GameConfig load(String name) {
        return GameConfigLoader.loadResource("scenarios/" + name + ".yaml");
    }

    /** A recording in-process client: each seat always quotes its own fixed number, so the quotes tell seats apart. */
    static final class Recorder implements LlmClient {
        final List<LlmRequest> requests = new ArrayList<>();
        final Map<String, Double> quotes;

        Recorder(Map<String, Double> quotes) {
            this.quotes = quotes;
        }

        @Override
        public synchronized LlmResponse complete(LlmRequest r) {
            requests.add(r);
            Matcher m = KEY.matcher(r.drawKey());
            double q = m.matches() ? quotes.getOrDefault(m.group(1), 2.09) : 2.09;
            String text = String.format(Locale.ROOT, "{\"quote\": %.2f, \"plan\": \"hold\", \"rationale\": \"r\"}", q);
            return new LlmResponse(text, 10, 10, 0L, false, CanonicalRequest.sha256(r), "stop");
        }

        String seat(LlmRequest r) {
            Matcher m = KEY.matcher(r.drawKey());
            assertThat(m.matches()).as(r.drawKey()).isTrue();
            return m.group(1);
        }
    }

    static List<String> ids(GameConfig cfg) {
        return cfg.agents().stream().map(AgentSpec::id).toList();
    }

    static LlmGame.Result play(GameConfig cfg, long seed, Recorder rec, boolean multiSeat) {
        return LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, rec, null, Set.of(), multiSeat);
    }

    /** First seed (from 1) whose game lasts at least minRounds rounds. */
    static long longSeed(GameConfig cfg, int minRounds) {
        for (long seed = 1; seed < 300; seed++) {
            if (play(cfg, seed, new Recorder(Map.of()), false).run().rounds().size() >= minRounds) {
                return seed;
            }
        }
        throw new AssertionError("no long enough run");
    }

    @Test
    void theDefaultEntryPointIsMultiSeatOffAndUnchanged() {
        GameConfig cfg = load("ripe-game");
        long seed = longSeed(cfg, 4);
        Recorder a = new Recorder(Map.of());
        Recorder b = new Recorder(Map.of());
        LlmGame.Result ra = LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, a, null, Set.of());
        LlmGame.Result rb = play(cfg, seed, b, false);
        assertThat(a.requests).isEqualTo(b.requests);
        assertThat(ra.run().replayDigest()).isEqualTo(rb.run().replayDigest());
    }

    @Test
    void withOneRivalTheSwitchChangesNoPromptNoHashAndNoDigest() {
        // paraphrase 0: from C3.5 on the switch uses game_system_m, whose gm01 renders as gs01 for two firms
        for (String sc : List.of("ripe-game", "probe-defect", "unripe-a-prime")) {
            GameConfig cfg = load(sc);
            long seed = longSeed(cfg, 4);
            Recorder off = new Recorder(Map.of());
            Recorder on = new Recorder(Map.of());
            LlmGame.Result r0 = play(cfg, seed, off, false);
            LlmGame.Result r1 = play(cfg, seed, on, true);
            assertThat(on.requests).as(sc).isEqualTo(off.requests);
            assertThat(on.requests.stream().map(CanonicalRequest::sha256).toList())
                    .isEqualTo(off.requests.stream().map(CanonicalRequest::sha256).toList());
            assertThat(r1.run().replayDigest()).isEqualTo(r0.run().replayDigest());
        }
    }

    @Test
    void severalLlmSeatsEachSeeOnlyTheirOwnRoundsUnderTheirOwnSeededLabels() {
        GameConfig cfg = load("n3-group");
        Map<String, Double> q = Map.of("llm1", 2.01, "llm2", 2.02, "llm3", 2.03);
        long seed = longSeed(cfg, 4);
        Recorder rec = new Recorder(q);
        LlmGame.Result r = play(cfg, seed, rec, true);
        assertThat(r.run().rounds().size()).isGreaterThanOrEqualTo(4);
        Set<String> hashes = new HashSet<>();
        Set<String> seats = new HashSet<>();
        for (LlmRequest req : rec.requests) {
            assertThat(hashes.add(CanonicalRequest.sha256(req))).as("unique fingerprint " + req.drawKey()).isTrue();
            String seat = rec.seat(req);
            seats.add(seat);
            SeatView v = SeatView.shared(seat, ids(cfg), seed); // the game's one label assignment (C5.5)
            String user = req.turns().get(0).content();
            for (String other : v.rivalIds()) {
                // the other quotes are listed in this seat's label order (M2 first), each under this seat's label
                assertThat(user).doesNotContain("you quoted " + String.format(Locale.ROOT, "%.2f", q.get(other)));
            }
            Matcher m = KEY.matcher(req.drawKey());
            m.matches();
            if (Integer.parseInt(m.group(2)) > 1) {
                List<String> parts = new ArrayList<>();
                for (Map.Entry<String, String> e : v.labels().entrySet()) {
                    parts.add("market maker " + e.getValue() + " " + String.format(Locale.ROOT, "%.2f", q.get(e.getKey())));
                }
                assertThat(user).contains("you quoted " + String.format(Locale.ROOT, "%.2f", q.get(seat))
                        + "; other quotes: " + String.join(", ", parts) + "; best quote 2.01");
            }
        }
        assertThat(seats).containsExactlyInAnyOrder("llm1", "llm2", "llm3");
    }

    @Test
    void theSeedSetsTheLabelsSoSomeSeatsDifferFromTheSortedOrderAndTheGameCarriesIt() {
        GameConfig cfg = load("n3-group");
        Map<String, Double> q = Map.of("llm1", 2.01, "llm2", 2.02, "llm3", 2.03);
        boolean differs = false;
        for (long seed = 1; seed <= 20 && !differs; seed++) {
            for (String seat : ids(cfg)) {
                if (!SeatView.shared(seat, ids(cfg), seed).labels().equals(SeatView.sorted(seat, ids(cfg)).labels())) {
                    Recorder on = new Recorder(q);
                    Recorder off = new Recorder(q);
                    play(cfg, seed, on, true);
                    play(cfg, seed, off, false);
                    if (on.requests.size() > 3) { // round 2 exists: the history lines must differ
                        assertThat(on.requests).isNotEqualTo(off.requests);
                        differs = true;
                    }
                    break;
                }
            }
        }
        assertThat(differs).isTrue();
    }

    @Test
    void scriptedRivalsKeepTheirRulesUnderTheSeatsLabelsInLabelOrder() {
        GameConfig cfg = load("n4-variant");
        for (long seed = 1; seed <= 10; seed++) {
            SeatView v = SeatView.seeded("llm", ids(cfg), seed);
            GameContext g = GameContext.of(cfg, "llm", v);
            String rule = g.partnerRuleText();
            int prev = -1;
            for (String label : v.labels().values()) {
                int at = rule.indexOf("Market maker " + label + ": ");
                assertThat(at).as(rule).isGreaterThan(prev);
                prev = at;
            }
            assertThat(rule).doesNotContainIgnoringCase("partner");
            // same text as today apart from the order of the per-firm sentences (all three rules are identical here)
            assertThat(rule).isEqualTo(GameContext.of(cfg, "llm").partnerRuleText());
        }
        assertThat(GameContext.of(cfg, "llm").view()).isNull();
    }

    @Test
    void eachLabelCarriesThatRivalsOwnRule() {
        GameConfig base = load("n4-variant");
        List<AgentSpec> ags = new ArrayList<>();
        double[] theta = {0.0, 0.546, 0.3, 0.8};
        for (int i = 0; i < base.agents().size(); i++) {
            AgentSpec a = base.agents().get(i);
            ags.add(i == 0 ? a : new AgentSpec(a.id(), a.category(), a.kind(),
                    Map.of("theta", theta[i], "k", -1L, "tolerance", 0.0)));
        }
        GameConfig cfg = base.withAgents(ags);
        for (long seed = 1; seed <= 10; seed++) {
            SeatView v = SeatView.seeded("llm", ids(cfg), seed);
            String rule = GameContext.of(cfg, "llm", v).partnerRuleText();
            for (AgentSpec a : ags.subList(1, ags.size())) {
                String own = io.github.tomloscalzo.collusion.agents.AgentFactory.create(a, cfg.scenario(), cfg.observation())
                        .disclosedRule();
                assertThat(rule).contains("Market maker " + v.label(a.id()) + ": " + own);
            }
        }
    }

    /** SHA-256 over every request hash of an off-path game, joined by newlines (pinned; checked against main by review). */
    static String requestDigest(GameConfig cfg, long seed, Map<String, Double> q) {
        Recorder rec = new Recorder(q);
        LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, rec, null, Set.of()); // the form every caller uses
        return io.github.tomloscalzo.collusion.results.Canonical.sha256(String.join("\n",
                rec.requests.stream().map(CanonicalRequest::sha256).toList()));
    }

    @Test
    void offPathRequestHashesArePinned() {
        assertThat(requestDigest(load("ripe-game"), 7, Map.of())).isEqualTo("8ec2a79cdafe9b6e02dcc69493374633d1c7437f22036f5d28662ea6e432f5f0");
        assertThat(requestDigest(load("n3-group"), 7, Map.of("llm1", 2.01, "llm2", 2.03, "llm3", 2.02))).isEqualTo("6e719f807ffb6bee0d19ab6b8d5bdef2a825bcdb4e98aba5929f431eb5d5edba");
    }

    @Test
    void historyListsOtherQuotesInTheViewsLabelOrder() {
        GameConfig cfg = load("n4-variant");
        List<String> ids = ids(cfg);
        Map<String, Double> riv = new TreeMap<>(Map.of("partner", 2.05, "partner2", 2.06, "partner3", 2.07));
        Observation o = new Observation(2, "llm", ids,
                List.of(new Observation.PastRound(1, 2.09, null, true, riv, 2.05, 30.0, 2.05, false)), 0.5);
        for (long seed = 1; seed <= 10; seed++) {
            SeatView v = SeatView.seeded("llm", ids, seed);
            String h = PromptBuilder.historyText(o, v.labels());
            List<String> parts = new ArrayList<>();
            v.labels().forEach((id, l) -> parts.add("market maker " + l + " " + String.format(Locale.ROOT, "%.2f", riv.get(id))));
            assertThat(h).contains("other quotes: " + String.join(", ", parts) + "; best quote 2.05");
            String turn = new PromptBuilder(Condition.neutral(), 0).gameTurn(GameContext.of(cfg, "llm", v), o, "");
            assertThat(turn).contains("other quotes: " + String.join(", ", parts));
        }
        // the sorted labels reproduce today's history text exactly
        assertThat(PromptBuilder.historyText(o, SeatView.sorted("llm", ids).labels())).isEqualTo(PromptBuilder.historyText(o));
    }

    @Test
    void aViewRefusesAnotherSeatsObservationAndAMismatchedView() {
        GameConfig cfg = load("n3-group");
        List<String> ids = ids(cfg);
        GameContext g = GameContext.of(cfg, "llm1", SeatView.seeded("llm1", ids, 3));
        Observation foreign = new Observation(1, "llm2", ids, List.of(), 0.5);
        assertThatThrownBy(() -> new PromptBuilder(Condition.neutral(), 0).gameTurn(g, foreign, ""))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("llm2");
        assertThatThrownBy(() -> GameContext.of(cfg, "llm1", SeatView.seeded("llm2", ids, 3)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GameContext.of(cfg, "llm1", SeatView.seeded("llm1", List.of("llm1", "llm2"), 3)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
