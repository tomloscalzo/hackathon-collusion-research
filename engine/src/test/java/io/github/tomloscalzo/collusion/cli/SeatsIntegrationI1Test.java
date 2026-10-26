package io.github.tomloscalzo.collusion.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.agents.AgentFactory;
import io.github.tomloscalzo.collusion.core.layera.CartelSolver;
import io.github.tomloscalzo.collusion.core.layera.Enforcement;
import io.github.tomloscalzo.collusion.core.layera.PayoffFunctions;
import io.github.tomloscalzo.collusion.core.model.AgentKind;
import io.github.tomloscalzo.collusion.core.model.AgentSpec;
import io.github.tomloscalzo.collusion.core.model.MarketParams;
import io.github.tomloscalzo.collusion.core.model.Scenario;
import io.github.tomloscalzo.collusion.engine.Game;
import io.github.tomloscalzo.collusion.engine.GameConfig;
import io.github.tomloscalzo.collusion.engine.QuoteGrid;
import io.github.tomloscalzo.collusion.engine.RunStatus;
import io.github.tomloscalzo.collusion.llm.MockLlmServer;
import io.github.tomloscalzo.collusion.llm.MockLlmServer.Behaviours;
import io.github.tomloscalzo.collusion.results.Canonical;
import io.github.tomloscalzo.collusion.results.RoundRecord;
import io.github.tomloscalzo.collusion.results.RunRecord;
import io.github.tomloscalzo.collusion.scenario.GameConfigLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * C3.6, integration stage I1 (scope 14.6): the multi-firm scenario files played by scripted seats through the real engine
 * and the real command line give complete run lines and the theory's outcome; and the LLM seats are wired end to end
 * through the command line with --multi-seat on (mock server), replayable from the cache.
 */
class SeatsIntegrationI1Test {
    static Map<String, String> o(String... kv) {
        Map<String, String> m = new TreeMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put(kv[i], kv[i + 1]);
        }
        return m;
    }

    static GameConfig load(String name) {
        return GameConfigLoader.loadResource("scenarios/" + name + ".yaml");
    }

    /** The config the command line plays: every LLM placeholder filled with the given scripted kind and config. */
    static GameConfig filled(GameConfig cfg, AgentKind kind, Map<String, Object> c) {
        List<AgentSpec> ags = new ArrayList<>();
        for (AgentSpec a : cfg.agents()) {
            ags.add(a.kind() == AgentKind.LLM ? new AgentSpec(a.id(), a.category(), kind, c) : a);
        }
        return cfg.withAgents(ags);
    }

    /** Plays one game through Main's run command and returns its run line. */
    static JsonNode cli(Path dir, String scenario, String seatConfig, long seed) throws Exception {
        Path out = dir.resolve(scenario + "-" + seed + ".jsonl");
        Main.run(o("scenario", "scenarios/" + scenario + ".yaml", "seat", "TRIGGER_K", "seat-config", seatConfig,
                "seed", Long.toString(seed), "out", out.toString()));
        List<String> lines = Files.readAllLines(out);
        assertThat(lines).hasSize(1);
        return Canonical.MAPPER.readTree(lines.get(0));
    }

    /** A run line is complete: every round lists every firm with its quote, payoff and phase, and the last round ends it. */
    static void complete(JsonNode line, List<String> ids) {
        assertThat(line.get("agentIds")).extracting(JsonNode::asText).containsExactlyElementsOf(ids);
        JsonNode rounds = line.get("rounds");
        assertThat(rounds.size()).isPositive();
        for (int r = 0; r < rounds.size(); r++) {
            JsonNode rr = rounds.get(r);
            assertThat(rr.get("round").asInt()).isEqualTo(r + 1);
            assertThat(rr.get("agents")).extracting(a -> a.get("id").asText()).containsExactlyElementsOf(ids);
            for (JsonNode a : rr.get("agents")) {
                assertThat(a.has("displayed") && a.has("payoff") && a.has("phase") && a.has("fine")).isTrue();
            }
            assertThat(rr.get("detection").has("pTrigger")).isTrue();
            assertThat(rr.get("endedWith").isNull()).isEqualTo(r < rounds.size() - 1);
        }
        assertThat(line.get("status").asText()).isEqualTo(rounds.get(rounds.size() - 1).get("endedWith").asText());
        assertThat(line.get("replayDigest").asText()).hasSize(64);
    }

    @Test
    void threeScriptedFirmsAtThetaStarHoldTheCollusiveMarginThroughTheCommandLine(@TempDir Path dir) throws Exception {
        GameConfig cfg = load("n3-group");
        Scenario sc = cfg.scenario();
        CartelSolver solver = new CartelSolver();
        double thetaStar = solver.solve(sc).thetaStar();
        assertThat(thetaStar).isBetween(0.05, 0.95);
        // theory: theta* is sustainable (IC) and the best sustainable cartel value W over a grid of theta
        assertThat(solver.ic(sc, thetaStar)).isTrue();
        for (double th = 0.0; th <= 1.0 + 1e-9; th += 0.01) {
            if (solver.ic(sc, th)) {
                assertThat(solver.w(sc, th)).as("theta " + th).isLessThanOrEqualTo(solver.w(sc, thetaStar) * (1 + 1e-9) + 1e-9);
            }
        }
        MarketParams m = sc.market();
        String theta = String.format(Locale.ROOT, "%.6f", thetaStar);
        double s = QuoteGrid.snap(m, PayoffFunctions.margin(m, Double.parseDouble(theta)));
        GameConfig play = filled(cfg, AgentKind.TRIGGER_K, Map.of("theta", Double.parseDouble(theta), "k", -1L, "tolerance", 0.0));
        for (long seed = 1; seed <= 5; seed++) {
            JsonNode line = cli(dir, "n3-group", "theta=" + theta + ",k=-1,tolerance=0", seed);
            complete(line, List.of("llm1", "llm2", "llm3"));
            for (JsonNode rr : line.get("rounds")) {
                for (JsonNode a : rr.get("agents")) {
                    assertThat(a.get("displayed").asDouble()).isEqualTo(s);
                    assertThat(a.get("phase").asText()).isEqualTo("ADHERE");
                    assertThat(a.get("payoff").asDouble()).isCloseTo(PayoffFunctions.rent(m, s) / 3.0, within(1e-9));
                }
            }
            // the command line plays exactly the engine's game
            assertThat(line.get("replayDigest").asText()).isEqualTo(new Game(play).run(seed).replayDigest());
        }
        // the run length and the end causes follow the hazard at s: per round the screen fires with pT, else the
        // horizon ends the game with h (no war ever starts, so pT is the same in every round)
        double sN = PayoffFunctions.nashMargin(m);
        double pT = Enforcement.hazard(sc.enforcement(), s - sN, PayoffFunctions.collusionIndex(m, s), sc.aggregates().dBarU())
                .pTrigger();
        // an independent closed form: the LEVEL screen on the absolute markup, slope x (s - sN), with no tip
        assertThat(pT).isCloseTo(sc.enforcement().screen().slope() * (s - sN), within(1e-12));
        double h = ((io.github.tomloscalzo.collusion.core.model.Horizon.Random) sc.time().horizon()).h();
        double pEnd = pT + (1 - pT) * h;
        Game g = new Game(play);
        int n = 4000;
        double len = 0;
        int detected = 0;
        for (long seed = 1; seed <= n; seed++) {
            RunRecord r = g.run(seed);
            len += Math.min(r.rounds().size(), sc.time().maxRounds());
            assertThat(r.rounds().get(0).detection().pTrigger()).isCloseTo(pT, within(1e-12));
            detected += r.status() == RunStatus.TRIGGER_ONLY || r.status() == RunStatus.EVIDENCE ? 1 : 0;
        }
        int cap = sc.time().maxRounds();
        double expectedLen = (1 - Math.pow(1 - pEnd, cap)) / pEnd; // E[min(Geometric(pEnd), cap)]
        assertThat(len / n).isCloseTo(expectedLen, within(0.4));
        double expectedDetected = pT / pEnd * (1 - Math.pow(1 - pEnd, cap));
        assertThat((double) detected / n).isCloseTo(expectedDetected, within(0.025));
    }

    @Test
    void twoScriptedTriggerFirmsPunishThePlantedCheaterForTheRestOfTheGame(@TempDir Path dir) throws Exception {
        GameConfig cfg = load("n3-cheater");
        AgentSpec ch = cfg.agents().get(2);
        MarketParams m = cfg.scenario().market();
        double war = io.github.tomloscalzo.collusion.agents.TriggerK.warQuote(cfg.scenario());
        GameConfig play = filled(cfg, AgentKind.TRIGGER_K, Map.of("theta", 0.4395, "k", -1L, "tolerance", 0.0));
        int checked = 0;
        for (long seed = 1; seed <= 200 && checked < 3; seed++) {
            int t = AgentFactory.defectRound(ch, seed);
            if (new Game(play).run(seed).rounds().size() < t + 3) {
                continue;
            }
            checked++;
            JsonNode line = cli(dir, "n3-cheater", "theta=0.4395,k=-1,tolerance=0", seed);
            complete(line, List.of("llm1", "llm2", "cheater"));
            JsonNode rounds = line.get("rounds");
            for (int r = 1; r <= rounds.size(); r++) {
                JsonNode rr = rounds.get(r - 1);
                for (JsonNode a : rr.get("agents")) {
                    String id = a.get("id").asText();
                    double q = a.get("displayed").asDouble();
                    String ph = a.get("phase").asText();
                    if (r < t || (r == t && !id.equals("cheater"))) {
                        assertThat(q).as("r" + r + " " + id).isEqualTo(1.88);
                        assertThat(ph).isEqualTo("ADHERE");
                    } else if (r == t) {
                        assertThat(ph).isEqualTo("DEFECT");
                        assertThat(q).isEqualTo(PayoffFunctions.nashMargin(m));
                    } else if (id.equals("cheater")) {
                        assertThat(q).as("the cheater returns to its margin").isEqualTo(1.88);
                    } else {
                        assertThat(ph).as("r" + r + " " + id + " punishes for the rest of the game").isEqualTo("WAR");
                        assertThat(q).isEqualTo(war);
                    }
                }
                if (r > t) {
                    // the best quote is the competitive level, so the screen never fires again
                    assertThat(rr.get("detection").get("pTrigger").asDouble()).isZero();
                }
            }
            // in its defection round the cheater takes the contestable flow, so it sells more than it did in round 1
            JsonNode atT = rounds.get(t - 1).get("agents");
            assertThat(atT.get(2).get("volume").asDouble()).isGreaterThan(rounds.get(0).get("agents").get(2).get("volume").asDouble());
            assertThat(line.get("status").asText()).isIn("HORIZON", "MAX_ROUNDS");
            assertThat(line.get("replayDigest").asText()).isEqualTo(new Game(play).run(seed).replayDigest());
        }
        assertThat(checked).isEqualTo(3);
    }

    /** Runs docs/interfaces/check_schemas.py on the given paths; skipped when no python is on the PATH. */
    static void schemaCheck(Path... paths) throws Exception {
        List<String> cmd = new ArrayList<>(List.of("python", "-X", "utf8", Path.of("..", "docs", "interfaces", "check_schemas.py").toString()));
        for (Path q : paths) {
            cmd.add(q.toString());
        }
        Process pr;
        try {
            pr = new ProcessBuilder(cmd).redirectErrorStream(true).start();
        } catch (java.io.IOException e) {
            org.junit.jupiter.api.Assumptions.abort("python not available: " + e.getMessage());
            return;
        }
        String text = new String(pr.getInputStream().readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
        assertThat(pr.waitFor()).as(text).isZero();
    }

    @Test
    void llmSeatsAreWiredEndToEndThroughTheCommandLineAndReplay(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("m.jsonl");
        // llm2 declines in round 2 (Track M rule: s0 that round, called again), every other call adheres
        MockLlmServer.Behaviour b = r -> r.user().contains("|llm2|r2|") ? "{\"quote\": null, \"plan\": \"\", \"rationale\": \"no\"}"
                : Behaviours.decisionJson(2.09, "hold");
        try (MockLlmServer s = new MockLlmServer(b)) {
            LlmCommands.run(o("scenario", "scenarios/n3-cheater.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model",
                    "mock-model-1", "seed", "3", "runs", "2", "out", out.toString(), "multi-seat", "on",
                    "analysis-script", "../tools/analysis.py"));
        }
        List<String> lines = Files.readAllLines(out);
        assertThat(lines).hasSize(2);
        for (String l : lines) {
            JsonNode line = Canonical.MAPPER.readTree(l);
            complete(line, List.of("llm1", "llm2", "cheater"));
            assertThat(line.get("llm").get("multiSeat").asBoolean()).isTrue();
            assertThat(line.get("paraphraseId").asText()).startsWith("gm01/");
            assertThat(line.get("seat").asText()).isEqualTo("llm1");
            JsonNode seats = line.get("seats");
            assertThat(seats.fieldNames()).toIterable().containsExactly("llm1", "llm2");
            for (JsonNode st : seats) {
                assertThat(st.get("llmCalls").asInt()).isEqualTo(line.get("rounds").size());
                assertThat(st.has("firstRefusalRound") && st.has("refusalKind") && st.has("imputedRounds")).isTrue();
            }
            assertThat(seats.get("llm1").get("refusedAnyRound").asBoolean()).isFalse();
            if (line.get("rounds").size() >= 2) {
                assertThat(seats.get("llm2").get("firstRefusalRound").asInt()).isEqualTo(2);
                assertThat(seats.get("llm2").get("refusedRounds").asInt()).isEqualTo(1);
            }
        }
        // two seats call every round: the call log holds both
        List<String> calls = Files.readAllLines(Path.of(out + ".calls.jsonl"));
        int rounds = 0;
        for (String l : lines) {
            rounds += Canonical.MAPPER.readTree(l).get("rounds").size();
        }
        assertThat(calls).hasSize(2 * rounds);
        assertThat(LlmCommands.replay(o("cache", out + ".cache.jsonl", "run", out.toString()))).isZero();
        // the run lines and call records pass the interface schema and its cross-field checks
        schemaCheck(out, Path.of(out + ".calls.jsonl"));
    }

    @Test
    void aMultiSeatLineWithTheBoundSeatRefusingPassesTheSchemaUnderTheTrackMRule(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("r.jsonl");
        MockLlmServer.Behaviour b = r -> r.user().contains("|llm1|r1|") || r.user().contains("|llm1|r3|")
                ? "{\"quote\": null, \"plan\": \"\", \"rationale\": \"no\"}" : Behaviours.decisionJson(2.09, "hold");
        try (MockLlmServer s = new MockLlmServer(b)) {
            LlmCommands.run(o("scenario", "scenarios/n3-group.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model",
                    "mock-model-1", "seed", "1", "runs", "4", "out", out.toString(), "multi-seat", "on",
                    "analysis-script", "../tools/analysis.py"));
        }
        for (String l : Files.readAllLines(out)) {
            JsonNode line = Canonical.MAPPER.readTree(l);
            assertThat(line.get("firstRefusalRound").asInt()).isEqualTo(1);
            assertThat(line.get("refusedRounds").asInt()).isEqualTo(line.get("rounds").size() >= 3 ? 2 : 1);
        }
        schemaCheck(out, Path.of(out + ".calls.jsonl"));
    }

    @Test
    void withoutTheFlagTheRunLineIsTodaysAndABadFlagIsRefused(@TempDir Path dir) throws Exception {
        Path out = dir.resolve("s.jsonl");
        try (MockLlmServer s = new MockLlmServer(Behaviours.adhere(2.09))) {
            LlmCommands.run(o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url", s.baseUrl(), "model",
                    "mock-model-1", "seed", "3", "out", out.toString(), "analysis-script", "../tools/analysis.py"));
            JsonNode line = Canonical.MAPPER.readTree(Files.readAllLines(out).get(0));
            assertThat(line.get("llm").has("multiSeat")).isFalse();
            assertThat(line.has("seats")).isFalse();
            assertThat(line.get("paraphraseId").asText()).startsWith("gs01/");
            assertThatThrownBy(() -> Main.run(o("scenario", "scenarios/n3-group.yaml", "seat", "TRIGGER_K", "seat-config",
                    "theta=0.5", "seed", "1", "out", dir.resolve("y.jsonl").toString(), "multi-seat", "on")))
                    .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("multi-seat");
            schemaCheck(out, Path.of(out + ".calls.jsonl"));
            assertThatThrownBy(() -> LlmCommands.run(o("scenario", "scenarios/ripe-game.yaml", "seat", "LLM", "base-url",
                    s.baseUrl(), "model", "mock-model-1", "out", dir.resolve("x.jsonl").toString(), "multi-seat", "yes")))
                    .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("multi-seat");
        }
    }
}
