package io.github.tomloscalzo.collusion.mc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;

class MonteCarloRunnerTest {
    @Test
    void resultsAreIdenticalForOneAndEightThreads() {
        FactorialDesign d = FactorialDesign.parse(Sweeps.TINY, null);
        for (FactorialDesign.Cell cell : d.cells()) {
            CellRunner cr = new CellRunner(d, cell, false, true);
            List<CellRunner.RunResult> one;
            List<CellRunner.RunResult> eight;
            try (MonteCarloRunner p1 = new MonteCarloRunner(1); MonteCarloRunner p8 = new MonteCarloRunner(8)) {
                one = p1.map(40, cr::run);
                eight = p8.map(40, cr::run);
            }
            assertThat(eight).hasSize(40);
            for (int i = 0; i < 40; i++) {
                assertThat(eight.get(i).index()).isEqualTo(i);
                assertThat(eight.get(i).line()).isEqualTo(one.get(i).line());
                assertThat(eight.get(i).roundsCsv()).isEqualTo(one.get(i).roundsCsv());
            }
            assertThat(CellSummary.row(cell, eight)).isEqualTo(CellSummary.row(cell, one));
        }
    }

    @Test
    void failuresPropagate() {
        try (MonteCarloRunner p = new MonteCarloRunner(4)) {
            assertThatThrownBy(() -> p.map(100, i -> {
                if (i == 37) {
                    throw new IllegalStateException("boom");
                }
                return i;
            })).isInstanceOf(IllegalStateException.class).hasMessageContaining("boom");
        }
    }
}
