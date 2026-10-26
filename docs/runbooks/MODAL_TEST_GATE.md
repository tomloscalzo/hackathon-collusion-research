# Modal test gate: run the engine's Maven tests on Modal CPU

The engine's test gate (`mvn -q -o test` in `engine/`, about 554 tests) is CPU-bound on the local machine. `tools/ci/modal_test.py` runs the same command on a Modal CPU container and gives back the result. It does not change engine code or tests, and it needs no key: the Modal token in `~/.modal.toml` is used by the Modal CLI library.

## The command agents should use

```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python -X utf8 tools/ci/modal_test.py <worktree_path> [--cpu 16] [--memory-gb 16] [--timeout-min 40]
```

- `<worktree_path>` is the repository checkout (or worktree) root, the folder that holds `engine/`.
- The exit code is Maven's: 0 = all tests passed, 1 = a test or compile failure, 2 = infrastructure failure (Modal error, bad path). A failing gate prints the tail of Maven's output.
- The last line is `RESULT exit=.. tests=.. failures=.. errors=.. skipped=.. mvn=..s wall=..s est.cost=$..`.
- The surefire XML reports come back in `<worktree>/engine/target/modal-surefire/surefire-reports/`.

## What it sends and runs

- A tarball of the whole worktree except `.git`, any `target`, `__pycache__`, and the top-level `results/` folder (about 3 MB). The tests read `tools/analysis.py`, `docs/interfaces/check_schemas.py` and the trial tools through relative paths, and call `python`, so the whole tree is sent, not only `engine/`.
- The image is Debian with JDK 17, Maven and the Python version of the calling interpreter. The engine's Maven dependencies (and the surefire/JUnit provider) are pre-fetched at image build by running `mvn dependency:go-offline` and a one-test build against `engine/pom.xml`. The image is cached by Modal and is rebuilt only when `engine/pom.xml` or the build recipe changes, so the first run after a pom change takes about 30 s longer.
- The function has `cpu=16`, 16 GB and a 40-minute timeout by default. Maven runs offline, as locally.

## Cost per run

Cost is the container's running time times Modal's CPU price (about $0.0000131 per core-second) plus memory (about $0.0000022 per GiB-second). The script prints an estimate that counts only the Maven time. For 16 cores and 16 GB and a Maven time of about 100 s that is about $0.02 to $0.03 per run, plus a few seconds of container start. Check the current prices at modal.com/pricing. Lower `--cpu` saves little (the suite is mostly short tests); 16 is the default.

## Verified on 2026-10-25

- Main (554 tests): exit 0, 554 run, 0 failures, 0 errors, Maven 99 s, wall 125 s (including upload and container start). The same suite locally (affinity 0xFF0): 554 run, 0 failures, 0 errors, 900 s.
- A scratch copy with one deliberately failing test: exit 1, 555 run, 1 failure, reported with the test name.

## A/B verification against local Maven (2026-10-25)

Procedure: export the same commit (`f337697`, the merge that adds the gate) twice with `git archive` into separate folders; run `mvn -o test` and `mvn -o -DskipTests package` locally (JDK 17, affinity 0xFF0) in one, and `tools/ci/modal_test.py` on the other; compare the per-test list and the surefire XML after stripping properties blocks, times, timestamps, hostnames, absolute paths and log clock times.

Verdict: **IDENTICAL EXCEPT environment and timestamp items.** 554 tests on each side with the same names, all passing. 82 of 85 report XML files are identical after normalisation. The other three differ only in the order of 65 parallel-test digest lines (same set, so the golden digests match across Windows and Linux), an OS-specific file-system error message in a warning, and a printed timing. Local: 770 s for the tests, 26 s for the package. Modal: Maven 112 s, wall 147 s, about $0.027.

Not covered: the gate does not build or return a jar, so jars were not compared; the tests write no other deterministic files into `target/`. Full report (not in the repo): `work_scratch/modal_ab/AB_REPORT.md`.
