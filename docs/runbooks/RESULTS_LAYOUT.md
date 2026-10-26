# Results layout: the `runs/` directory

Every batch of games lives in one **run root** directly under the runs directory (a sibling of the repository checkout, not inside the repository; run outputs are never committed):

```
runs/<YYYY-MM-DD>_<track>_<stage>/
```

- `YYYY-MM-DD`: the day the root was created (the first launch).
- `track`: `m` (Track M, chat/multi-seat) or `s` (Track S, single-seat elicitation).
- `stage`: a short lowercase slug with no spaces, for example `smoke`, `pilot`, `wave1`, `strict-t0-32b`.

Examples: `runs/2026-10-25_m_pilot/`, `runs/2026-10-26_s_stage0/`. One root = one launch plan (one `--out` of `run_grid.py` / `run_waves.py`); a rerun of the same plan reuses the same root (DONE trials are skipped). A different configuration gets a new root, never a mixed one.

## Inside a root

| Content | Meaning |
|---|---|
| `<arm>/<trial_id>/` (or `trials/<arm>/<trial_id>/`) | Track M trial directory: `params.json`, `events.jsonl`, `run.jsonl`, `cache.jsonl`, `calls.jsonl`, `console.log`, `run_stats.json`, and a `DONE` or `FAILED` marker (none = not finished) |
| `<stage>/<run>.jsonl` with `.manifest.json`, `.cache.jsonl`, `.calls.jsonl`, `.log` | Track S run lines (one line per game); `*.jsonl.partial-*` marks an interrupted run |
| `grid.csv`, `theory.csv`, `collusion-engine.jar` | the plan and the jar that ran it |
| `tables/`, `analysis_*/`, `checks/`, `viewer/` | derived outputs (safe to regenerate) |
| `cost.json` (or `meter.json`, `cost_meter.json`, `spend.json`) | optional cost meter: a JSON object with `spent_usd` (or `total_usd`, `cost_usd`, `spent`) |

## The index

`python -X utf8 tools/trial/runs_registry.py [RUNS_DIR]` scans every root and writes `RUNS_INDEX.csv` and `RUNS_INDEX.md` into the runs directory (default: the nearest `runs/` directory above the repository checkout or worktree). One row per root:

`date, track, stage, arms (;-separated), model, thinking (on/off, ;-separated), commits (first 12 characters), done, failed, trials, cost_usd, status, path`

- `done` / `failed` count `DONE` / `FAILED` trial directories (Track M) or game lines / partial files (Track S); `trials` = done + failed + unfinished.
- `status`: `complete` (all trials DONE), `incomplete` (some unfinished, none failed), `has-failures` (at least one FAILED), `empty`.
- `cost_usd` is blank when the root has no meter file.
- Track S `*.jsonl.partial-*` files count as failed (and so make the root `has-failures`); a run-line file counts one done game per line that parses as a JSON object.
- `path` is the root's directory name relative to the runs directory.

Older ad-hoc roots (`trackm-smoke`, `tracks-t0`, `hc`, ...) are indexed too: the track and stage are guessed from the name (`trackm-` / `tracks-` prefix) and the date is the directory's modification time. They keep their names; new roots follow the pattern above. Anything that is not a directory (logs, model lists) is ignored, and unreadable files never stop the scan. Rerun the command after each launch; it overwrites the two index files.
