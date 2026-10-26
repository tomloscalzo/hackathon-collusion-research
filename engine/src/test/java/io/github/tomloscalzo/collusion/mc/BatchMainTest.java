package io.github.tomloscalzo.collusion.mc;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.tomloscalzo.collusion.results.Canonical;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class BatchMainTest {
    @TempDir
    Path tmp;

    @Test
    void endToEndManifestSummaryBandsAndResume() throws IOException {
        Path sweep = tmp.resolve("tiny.yaml");
        Files.writeString(sweep, Sweeps.TINY, StandardCharsets.UTF_8);
        Path out = tmp.resolve("out");

        var r1 = BatchMain.execute(sweep, out, 4, null, false, true, false);
        assertThat(r1.cellsRun()).isEqualTo(4);
        assertThat(r1.cellsSkipped()).isZero();

        JsonNode m = Canonical.MAPPER.readTree(out.resolve("manifest.json").toFile());
        assertThat(m.get("gitCommit").asText()).matches("[0-9a-f]{7,64}|unknown");
        assertThat(m.get("masterSeed").asLong()).isEqualTo(7L);
        assertThat(m.get("threads").asInt()).isEqualTo(4);
        assertThat(m.get("sweepSha256").asText()).isEqualTo(Canonical.sha256(Sweeps.TINY));
        assertThat(m.get("scenarioHashes").has("scenarios/ripe-game.yaml")).isTrue();
        assertThat(m.get("scenarioHashes").has("scenarios/unripe-a.yaml")).isTrue();
        assertThat(m.get("wallTimeMs").asLong()).isGreaterThanOrEqualTo(0);
        assertThat(m.get("cellsTotal").asInt()).isEqualTo(4);

        List<String> rows = Files.readAllLines(out.resolve("summary.csv"));
        assertThat(rows).hasSize(5);
        assertThat(rows.get(0)).contains("mcse_p_adhere").contains("short_run_share").contains("p_collude")
                .contains("false_alarm_rate").contains("run_length_median");
        List<String> runLines = Files.readAllLines(out.resolve("runs").resolve("c0000.jsonl"));
        assertThat(runLines).hasSize(20);
        JsonNode first = Canonical.MAPPER.readTree(runLines.get(0));
        assertThat(first.get("replayDigest").asText()).hasSize(64);
        assertThat(first.get("ownCi").size()).isEqualTo(first.get("rounds").asInt());
        assertThat(Files.readAllLines(out.resolve("export").resolve("decisions-c0000.csv")).size()).isGreaterThan(20);
        assertThat(Files.readAllLines(out.resolve("bands.csv"))).hasSize(3); // header + one contrast x two seat blocks

        String before = Files.readString(out.resolve("summary.csv"));
        var r2 = BatchMain.execute(sweep, out, 2, null, false, true, false);
        assertThat(r2.cellsRun()).isZero();
        assertThat(r2.cellsSkipped()).isEqualTo(4);
        assertThat(Files.readString(out.resolve("summary.csv"))).isEqualTo(before);

        List<String> cut = new ArrayList<>(rows.subList(0, 4));
        Files.writeString(out.resolve("summary.csv"), String.join("\n", cut) + "\n");
        var r3 = BatchMain.execute(sweep, out, 3, null, false, true, false);
        assertThat(r3.cellsRun()).isEqualTo(1);
        assertThat(r3.cellsSkipped()).isEqualTo(3);
        assertThat(Files.readAllLines(out.resolve("summary.csv"))).isEqualTo(rows);
    }

    @Test
    void outputsAreIdenticalForOneAndEightThreads() throws IOException {
        Path sweep = tmp.resolve("tiny.yaml");
        Files.writeString(sweep, Sweeps.TINY, StandardCharsets.UTF_8);
        BatchMain.execute(sweep, tmp.resolve("t1"), 1, null, false, false, false);
        BatchMain.execute(sweep, tmp.resolve("t8"), 8, null, false, false, false);
        assertThat(Files.readString(tmp.resolve("t8").resolve("summary.csv")))
                .isEqualTo(Files.readString(tmp.resolve("t1").resolve("summary.csv")));
        assertThat(Files.readString(tmp.resolve("t8").resolve("bands.csv")))
                .isEqualTo(Files.readString(tmp.resolve("t1").resolve("bands.csv")));
        for (int c = 0; c < 4; c++) {
            String f = "c000" + c + ".jsonl";
            assertThat(Files.readString(tmp.resolve("t8").resolve("runs").resolve(f)))
                    .isEqualTo(Files.readString(tmp.resolve("t1").resolve("runs").resolve(f)));
        }
    }

    @Test
    void probeCellsReportResponderRates() throws IOException {
        Path sweep = tmp.resolve("probe.yaml");
        Files.writeString(sweep, Sweeps.PROBE);
        BatchMain.execute(sweep, tmp.resolve("p"), 4, null, false, false, false);
        List<String> rows = Files.readAllLines(tmp.resolve("p").resolve("summary.csv"));
        int ri = List.of(rows.get(0).split(",")).indexOf("responder_rate");
        // tit-for-tat copies the one-round defection: responder with a defecting partner, never at the placebo t
        assertThat(Double.parseDouble(rows.get(1).split(",")[ri])).isEqualTo(1.0);
        assertThat(Double.parseDouble(rows.get(2).split(",")[ri])).isEqualTo(0.0);
        assertThat(Files.readAllLines(tmp.resolve("p").resolve("bands.csv")).get(1)).startsWith("P3,responder,");
    }
}
