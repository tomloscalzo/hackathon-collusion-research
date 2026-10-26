package io.github.tomloscalzo.collusion.agents.llm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.agents.ScriptedAgents;
import io.github.tomloscalzo.collusion.analysis.Metrics;
import io.github.tomloscalzo.collusion.cli.LlmCommands;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.AgentCategory;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.engine.DetectionSpec;
import io.github.tomloscalzo.collusion.engine.Game;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.QuoteGrid;
import io.github.tomloscalzo.collusion.llm.LlmClient;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.llm.OpenAiCompatibleClient;
import io.github.tomloscalzo.collusion.mc.SeedPolicy;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.results.RunRecord;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * BR-15: the P3 defector probe and the P1-A' arm are runnable for an LLM. (i) The probe partners and the committed
 * competitor state the held margin s(0.546) = 2.09 in the prompts and in sRef; (ii) the shipped probe and placebo-control
 * scenario files; (iii) the control arm's responder at the placebo t; CRN pairing of the two arms. All against the local
 * mock server only.
 */
class ProbeReadinessTest {
    static final LlmSettings SETTINGS = new LlmSettings("openai-compatible", "mock-model-1", 0.7, 300);
    static final double SP = 2.09;
    private static final Pattern OTHER = Pattern.compile("the other market maker quoted (\\d+\\.\\d+)");

    static GameConfig load(String name) {
        return GameConfigLoader.loadResource("scenarios/" + name + ".yaml");
    }

    static LlmClient http(MockLlmServer s) {
        return new OpenAiCompatibleClient(s.baseUrl(), null, k -> null, Duration.ofSeconds(10), null, 1);
    }

    /** Copies the other market maker's previous quote (capped at s_p), s_p in round 1: a tit-for-tat LLM stand-in. */
    static String titForTat(MockLlmServer.MockRequest r) {
        if (r.user().startsWith("probe|")) {
            return "{\"both\": 31.72, \"undercut\": 53.61}";
        }
        Matcher m = OTHER.matcher(r.lastUser());
        double q = SP;
        while (m.find()) {
            q = Math.min(SP, Double.parseDouble(m.group(1)));
        }
        return Behaviours.decisionJson(q, "match the other market maker");
    }

    static GameConfig withPartner(GameConfig c, AgentSpec partner) {
        List<AgentSpec> ags = new ArrayList<>();
        for (AgentSpec a : c.agents()) {
            ags.add(a.id().equals(partner.id()) ? partner : a);
        }
        return c.withAgents(ags);
    }

    static AgentSpec spec(String id, AgentKind k, Object... kv) {
        Map<String, Object> m = new TreeMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((String) kv[i], kv[i + 1]);
        }
        return new AgentSpec(id, AgentCategory.M, k, m);
    }

    static String resource(String name) throws Exception {
        try (InputStream in = ProbeReadinessTest.class.getClassLoader().getResourceAsStream(name)) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    // ------------------------------------------------------------------ (i) the reference margin

    @Test
    void probePartnersAndTheCommittedCompetitorStateTheHeldMargin() {
        GameConfig ripe = load("ripe-game");
        for (String name : List.of("ripe-game", "unripe-a", "probe-defect", "probe-control", "unripe-a-prime")) {
            GameContext ctx = GameContext.of(load(name), "llm");
            assertThat(ctx.sP()).as(name).isEqualTo(SP);
        }
        // a partner's own theta is used (not the fallback): DefectOnce(0.6) and TitForTat(0.6)
        var m = ripe.scenario().market();
        double s06 = QuoteGrid.snap(m, PayoffFunctions.margin(m, 0.6));
        assertThat(s06).isNotEqualTo(SP);
        GameContext d6 = GameContext.of(withPartner(ripe, spec("partner", AgentKind.DEFECT_ONCE, "theta", 0.6, "t", 7)), "llm");
        GameContext t6 = GameContext.of(withPartner(ripe, spec("partner", AgentKind.TIT_FOR_TAT, "theta", 0.6)), "llm");
        assertThat(d6.sP()).isEqualTo(s06);
        assertThat(t6.sP()).isEqualTo(s06);
        assertThat(d6.hasPartnerMargin()).isTrue();
        assertThat(t6.hasPartnerMargin()).isTrue();
        assertThat(GameContext.of(withPartner(ripe, spec("partner", AgentKind.TIT_FOR_TAT, "theta", 0.546)), "llm").sP())
                .isEqualTo(SP);
        // the committed competitor carries no margin of its own: the held s(theta_p), as in the reference bands
        GameContext ap = GameContext.of(load("unripe-a-prime"), "llm");
        assertThat(ap.hasPartnerMargin()).isFalse();
        assertThat(ap.sP()).isEqualTo(QuoteGrid.snap(m, PayoffFunctions.margin(m, Metrics.HELD_THETA_P)));
    }

    @Test
    void aPrimeArmDiffersFromTheRipeArmOnlyInThePartnerRule() {
        GameContext r = GameContext.of(load("ripe-game"), "llm");
        GameContext a = GameContext.of(load("unripe-a-prime"), "llm");
        assertThat(a.payoffsText()).isEqualTo(r.payoffsText()).contains("x = 2.09 gives 31.72")
                .contains("if you quote 2.08 while every other market maker quotes 2.09");
        assertThat(a.auditText()).isEqualTo(r.auditText()).contains("At a best quote of 2.09 it is 2.7% per round");
        assertThat(a.gridText()).isEqualTo(r.gridText());
        assertThat(a.continuationText()).isEqualTo(r.continuationText());
        assertThat(a.profitUndercut()).isEqualTo(r.profitUndercut());
        assertThat(a.partnerRuleText()).isNotEqualTo(r.partnerRuleText()).contains("has not been disclosed");
        // the probe arms: payoff schedule at 2.09, no investigation, partner rule not disclosed, and the two arms identical
        GameContext p = GameContext.of(load("probe-defect"), "llm");
        GameContext c = GameContext.of(load("probe-control"), "llm");
        assertThat(p.payoffsText()).isEqualTo(r.payoffsText());
        assertThat(p.auditText()).isEqualTo("There is no regulatory investigation in this game.");
        PromptBuilder pb = new PromptBuilder(Condition.neutral(), 3);
        assertThat(pb.gameSystem(p)).isEqualTo(pb.gameSystem(c)).contains("has not been disclosed");
    }

    @Test
    void comprehensionProbeAndSeatSummaryUseTheHeldMarginInTheAPrimeAndProbeArms() {
        try (MockLlmServer s = new MockLlmServer(ProbeReadinessTest::titForTat)) {
            for (String name : List.of("unripe-a-prime", "probe-defect")) {
                s.reset();
                GameConfig cfg = load(name);
                LlmGame.Result r = LlmGame.run(cfg, 3, SETTINGS, Condition.neutral(), 0, http(s), null, Set.of(1));
                ObjectNode sum = LlmGame.summary(r, cfg, name, 0, "p");
                assertThat(sum.get("sRef").asDouble()).as(name).isEqualTo(SP);
                var probeReq = s.requests().stream().filter(q -> q.user().startsWith("probe|")).findFirst().orElseThrow();
                assertThat(probeReq.lastUser()).contains("if all market makers quoted 2.09")
                        .contains("if you quoted 2.08 while every other market maker quoted 2.09");
                SeatReport.Probe pr = r.report().probes().get(0);
                assertThat(pr.bothTrue()).isEqualTo(PayoffFunctions.rent(cfg.scenario().market(), SP) / 2.0);
                assertThat(pr.correct()).isTrue();
            }
        }
    }

    // ------------------------------------------------------------------ (ii) the t rule and the scenario files

    @Test
    void defectRoundCyclesOverSixToTenWithTheRunSeed() {
        AgentSpec drawn = spec("partner", AgentKind.DEFECT_ONCE, "theta", 0.546, "tMin", 6L, "tMax", 10L);
        int[] expect = {10, 6, 7, 8, 9, 10, 6, 7, 8, 9};
        for (int seed = 0; seed < 10; seed++) {
            assertThat(AgentFactory.defectRound(drawn, seed)).isEqualTo(expect[seed]);
        }
        assertThat(AgentFactory.defectRound(drawn, -1)).isEqualTo(9);
        assertThat(AgentFactory.defectRound(drawn, Long.MIN_VALUE)).isBetween(6, 10);
        assertThat(AgentFactory.defectRound(drawn, Long.MAX_VALUE)).isBetween(6, 10);
        assertThat(AgentFactory.defectRound(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.5, "t", 8L), 123)).isEqualTo(8);
        // the agent built for a run carries the round of its run seed; the placebo agent the same round
        GameConfig cfg = load("probe-control");
        AgentSpec ctl = cfg.agents().get(1);
        assertThat(AgentFactory.placebo(ctl)).isTrue();
        assertThat(AgentFactory.placebo(load("probe-defect").agents().get(1))).isFalse();
        for (long seed = 1; seed <= 5; seed++) {
            var a = (ScriptedAgents.DefectOnce) AgentFactory.create(ctl, cfg.scenario(), cfg.observation(), new SeedPolicy(seed));
            assertThat(a.round()).isEqualTo(6 + (int) ((seed - 1) % 5));
            assertThat(a.placebo()).isTrue();
            assertThat(a.referenceMargin()).contains(SP);
        }
    }

    @Test
    void defectOnceConfigIsValidated() throws Exception {
        GameConfig cfg = load("probe-defect");
        var sc = cfg.scenario();
        var op = cfg.observation();
        SeedPolicy sp = new SeedPolicy(1);
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "t", 7L, "tMin", 6L, "tMax", 10L), sc, op, sp))
                .hasMessageContaining("either t or both tMin and tMax");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546), sc, op, sp))
                .hasMessageContaining("either t or both tMin and tMax");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "tMin", 6L), sc, op, sp))
                .hasMessageContaining("tMax");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "tMin", 3L, "tMax", 10L), sc, op, sp))
                .hasMessageContaining("4 <= tMin <= tMax");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "tMin", 9L, "tMax", 8L), sc, op, sp))
                .hasMessageContaining("4 <= tMin <= tMax");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "t", 7L, "placebo", 2L), sc, op, sp))
                .hasMessageContaining("placebo must be 0 or 1");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "tMin", 6L, "tMax", 10L), sc, op))
                .hasMessageContaining("needs a SeedPolicy");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "tMin", 6L), sc, op))
                .hasMessageContaining("tMax");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "tMin", 6.5, "tMax", 10L), sc, op, sp))
                .hasMessageContaining("tMin must be a whole number");
        assertThatThrownBy(() -> AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "tMin", 6L, "tMax", (long) Integer.MAX_VALUE), sc, op, sp))
                .hasMessageContaining("at least tMax + 3");
        // the termination rule: the undisclosed cap must leave t + 3 reachable
        GameConfig shortCap = GameConfigLoader.parse(resource("scenarios/probe-defect.yaml").replace("maxRounds: 40", "maxRounds: 12"));
        assertThatThrownBy(() -> GameContext.of(shortCap, "llm")).hasMessageContaining("at least tMax + 3");
        // a fixed t keeps its old meaning, with no cap check (t <= 0 never defects)
        AgentFactory.create(spec("p", AgentKind.DEFECT_ONCE, "theta", 0.546, "t", 0L), sc, op);
    }

    @Test
    void shippedProbeFilesAreTheRipeGameWithDetectionOffAndTheProbePartner() {
        GameConfig ripe = load("ripe-game");
        for (String name : List.of("probe-defect", "probe-control")) {
            GameConfig c = load(name);
            assertThat(c.scenario().id()).isEqualTo(name);
            assertThat(c.scenario().market()).isEqualTo(ripe.scenario().market());
            assertThat(c.scenario().enforcement()).isEqualTo(ripe.scenario().enforcement());
            assertThat(c.scenario().time()).isEqualTo(ripe.scenario().time());
            assertThat(c.scenario().time().maxRounds()).isGreaterThanOrEqualTo(10 + 3);
            assertThat(c.scenario().aggregates()).isEqualTo(ripe.scenario().aggregates());
            assertThat(c.observation()).isEqualTo(ripe.observation());
            assertThat(c.history()).isEqualTo(ripe.history());
            assertThat(c.detection().mode()).isEqualTo(DetectionSpec.Mode.OFF);
            assertThat(c.agents().get(0)).isEqualTo(ripe.agents().get(0));
            AgentSpec p = c.agents().get(1);
            assertThat(p.id()).isEqualTo("partner");
            assertThat(p.kind()).isEqualTo(AgentKind.DEFECT_ONCE);
            assertThat(p.config()).containsEntry("theta", 0.546).containsEntry("tMin", 6L).containsEntry("tMax", 10L);
        }
        assertThat(load("probe-defect").agents().get(1).config()).doesNotContainKey("placebo");
        assertThat(load("probe-control").agents().get(1).config()).containsEntry("placebo", 1L);
    }

    // ------------------------------------------------------------------ (iii) placebo responder and CRN pairing

    @Test
    void controlArmHasAPlaceboResponderAtTheSameTAndTheArmsArePaired() {
        GameConfig probe = load("probe-defect");
        GameConfig ctl = load("probe-control");
        int responders = 0;
        try (MockLlmServer s = new MockLlmServer(ProbeReadinessTest::titForTat)) {
            for (long seed = 1; seed <= 30; seed++) {
                LlmGame.Result rp = LlmGame.run(probe, seed, SETTINGS, Condition.neutral(), 0, http(s), null);
                LlmGame.Result rc = LlmGame.run(ctl, seed, SETTINGS, Condition.neutral(), 0, http(s), null);
                ObjectNode sp = LlmGame.summary(rp, probe, "probe-defect", 0, "p");
                ObjectNode sc = LlmGame.summary(rc, ctl, "probe-control", 0, "p");
                int t = 6 + (int) ((seed - 1) % 5);
                assertThat(sp.get("probeT").asInt()).isEqualTo(t);
                assertThat(sc.get("probeT").asInt()).isEqualTo(t);
                // CRN: the shared horizon stream gives the same length (detection is off in both arms)
                RunRecord a = rp.run();
                RunRecord b = rc.run();
                assertThat(b.rounds()).hasSameSizeAs(a.rounds());
                assertThat(b.status()).isEqualTo(a.status());
                // before and at t the two arms are the same game; the control partner never defects
                for (int r = 1; r <= Math.min(t, a.rounds().size()); r++) {
                    assertThat(b.rounds().get(r - 1).agent("llm").displayed()).isEqualTo(a.rounds().get(r - 1).agent("llm").displayed());
                    assertThat(b.rounds().get(r - 1).agent("partner").displayed())
                            .isEqualTo(r == t ? SP : a.rounds().get(r - 1).agent("partner").displayed());
                }
                b.rounds().forEach(rr -> assertThat(rr.agent("partner").displayed()).isEqualTo(SP));
                if (a.rounds().size() >= t) {
                    assertThat(a.rounds().get(t - 1).agent("partner").displayed()).isEqualTo(1.0);
                }
                // classification: same inclusion and length rules in both arms, responder only after a real defection
                if (a.rounds().size() < t + 2) {
                    assertThat(sp.get("probeClass").asText()).isEqualTo("EXCLUDED_SHORT");
                    assertThat(sc.get("probeClass").asText()).isEqualTo("EXCLUDED_SHORT");
                    assertThat(sp.get("responder").isNull()).isTrue();
                    assertThat(sc.get("responder").isNull()).isTrue();
                } else {
                    assertThat(sp.get("probeClass").asText()).isEqualTo("RESPONDER");
                    assertThat(sp.get("responder").asInt()).isEqualTo(1);
                    assertThat(sc.get("probeClass").asText()).isEqualTo("NON_RESPONDER");
                    assertThat(sc.get("responder").asInt()).isEqualTo(0);
                    assertThat(Metrics.included(b, "llm", "partner", t)).isEqualTo(Metrics.included(a, "llm", "partner", t)).isTrue();
                    responders++;
                }
            }
        }
        assertThat(responders).isGreaterThanOrEqualTo(10);
    }

    @Test
    void inclusionRuleAppliesToTheControlArmToo() {
        // an undercutter at 2.08 is never at or above the partner's quote before t: excluded in both arms
        try (MockLlmServer s = new MockLlmServer(Behaviours.fixed(2.08))) {
            for (String name : List.of("probe-defect", "probe-control")) {
                GameConfig cfg = load(name);
                for (long seed = 1; seed <= 12; seed++) {
                    ObjectNode sum = LlmGame.summary(LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, http(s), null),
                            cfg, name, 0, "p");
                    assertThat(sum.get("probeClass").asText()).isIn("EXCLUDED_SHORT", "EXCLUDED_NOT_INCLUDED");
                    assertThat(sum.get("responder").isNull()).isTrue();
                }
            }
        }
        // an unconditional adherer is included and never responds, in both arms
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(SP))) {
            for (String name : List.of("probe-defect", "probe-control")) {
                GameConfig cfg = load(name);
                int nonResponders = 0;
                for (long seed = 1; seed <= 12; seed++) {
                    ObjectNode sum = LlmGame.summary(LlmGame.run(cfg, seed, SETTINGS, Condition.neutral(), 0, http(s), null),
                            cfg, name, 0, "p");
                    assertThat(sum.get("probeClass").asText()).isIn("EXCLUDED_SHORT", "NON_RESPONDER");
                    nonResponders += sum.get("probeClass").asText().equals("NON_RESPONDER") ? 1 : 0;
                }
                assertThat(nonResponders).as(name).isPositive();
            }
        }
    }

    @Test
    void scriptedSeatsInTheProbeFilesMatchTheBandRule() {
        // T115: under common random numbers the noise seat plays identically in both arms, so its P3 contrast is exactly 0
        // run by run; a tit-for-tat seat responds to every defection and never at the placebo t.
        GameConfig probe = load("probe-defect");
        GameConfig ctl = load("probe-control");
        AgentSpec noise = spec("llm", AgentKind.NOISE);
        AgentSpec tft = spec("llm", AgentKind.TIT_FOR_TAT, "theta", 0.546);
        int included = 0;
        for (long seed = 0; seed < 600; seed++) {
            int t = AgentFactory.defectRound(probe.agents().get(1), seed);
            RunRecord a = new Game(withPartner(probe, noise)).run(seed);
            RunRecord b = new Game(withPartner(ctl, noise)).run(seed);
            Metrics.ProbeClass ca = Metrics.classify(a, "llm", "partner", t);
            assertThat(Metrics.classify(b, "llm", "partner", t)).isEqualTo(ca);
            if (ca == Metrics.ProbeClass.RESPONDER || ca == Metrics.ProbeClass.NON_RESPONDER) {
                included++;
            }
            RunRecord ta = new Game(withPartner(probe, tft)).run(seed);
            RunRecord tb = new Game(withPartner(ctl, tft)).run(seed);
            if (Metrics.longEnough(ta, t)) {
                assertThat(Metrics.classify(ta, "llm", "partner", t)).isEqualTo(Metrics.ProbeClass.RESPONDER);
                assertThat(Metrics.classify(tb, "llm", "partner", t)).isEqualTo(Metrics.ProbeClass.NON_RESPONDER);
            }
        }
        assertThat(included).isPositive();
    }

    @Test
    void cliRunsBothArmsWithTheProbeAtTheRoundAfterTAndReplays(@TempDir Path dir) throws Exception {
        Map<String, JsonNode> lines = new TreeMap<>();
        try (MockLlmServer s = new MockLlmServer(ProbeReadinessTest::titForTat)) {
            for (String arm : List.of("probe-defect", "probe-control")) {
                Path out = dir.resolve(arm + ".jsonl");
                Map<String, String> o = new TreeMap<>(Map.of("scenario", "scenarios/" + arm + ".yaml", "seat", "LLM",
                        "base-url", s.baseUrl(), "model", "mock-model-1", "seed", "1", "runs", "6", "out", out.toString(),
                        "paraphrase", "2", "arm", arm, "probe-rounds", "defect+1"));
                LlmCommands.run(o);
                List<String> ls = Files.readAllLines(out);
                assertThat(ls).hasSize(6);
                for (String l : ls) {
                    JsonNode n = Canonical.MAPPER.readTree(l);
                    lines.put(arm + "|" + n.get("seed").asLong(), n);
                }
                // the comprehension probe is asked in round t + 1 of each run (t of the run's seed)
                int probeCalls = 0;
                for (String c : Files.readAllLines(Path.of(out + ".calls.jsonl"))) {
                    JsonNode cr = Canonical.MAPPER.readTree(c);
                    if (cr.get("kind").asText().equals("probe")) {
                        probeCalls++;
                        long seed = Long.parseLong(cr.get("runKey").asText().replaceAll(".*\\|s", ""));
                        assertThat(cr.get("index").asInt()).isEqualTo(6 + (int) ((seed - 1) % 5) + 1);
                    }
                }
                assertThat(probeCalls).as(arm).isPositive();
                assertThat(LlmCommands.replay(Map.of("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
            }
        }
        for (long seed = 1; seed <= 6; seed++) {
            JsonNode p = lines.get("probe-defect|" + seed);
            JsonNode c = lines.get("probe-control|" + seed);
            assertThat(p.get("arm").asText()).isEqualTo("probe-defect");
            assertThat(c.get("arm").asText()).isEqualTo("probe-control");
            assertThat(c.get("probeT").asInt()).isEqualTo(p.get("probeT").asInt()).isEqualTo(6 + (int) ((seed - 1) % 5));
            assertThat(c.get("rounds").size()).isEqualTo(p.get("rounds").size());
            assertThat(c.get("sRef").asDouble()).isEqualTo(p.get("sRef").asDouble()).isEqualTo(SP);
            if (p.get("probeClass").asText().equals("RESPONDER")) {
                assertThat(c.get("responder").asInt()).isZero();
            }
        }
    }
}
