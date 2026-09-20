# Reproducibility

A stranger with this repository and a working Python 3.12 should reproduce every
Fidelity-0 result below. If they cannot, that is a bug.

## Environment

```bash
git clone <this repository>
cd aether
uv venv --python 3.12
uv pip install -e ".[dev]"
```

Dependencies are pinned by lower bound in `pyproject.toml`: numpy, scipy, matplotlib,
pyyaml, pandas, pyarrow. No compiled extensions, no GPU, no network access at runtime.

OpenFOAM v2606 is required only for Fidelity 1, which is not yet active. Nothing below
needs it.

## Commands

```bash
make test           # 38 verification tests: analytical benchmarks, convergence, ordering
make baseline       # one nominal entry, prints the performance vector, writes figures
make burn-vs-bake   # M1 + M1b: the full result, reports and figures
make figures        # regenerate every figure from the last run
make lint           # ruff
make all            # test -> baseline -> burn-vs-bake

# M7 (spec §27/§28/§39). Both refuse until `make doe && make optimize` are current.
make robust         # robust NSGA-II + the verification of its shortcut. HOURS - background it
make uncertainty    # propagation + Sobol' attribution + the §39 table; folds in the latest robust run
make m7             # robust, then uncertainty, in the order the report needs
make uncertainty-smoke  # tiny N, proves the chain, publishes nothing
make uncertainty-time   # measure the per-evaluation cost the study is sized from
```

## Expected runtime

Measured on an Apple M4, single-threaded. Nothing here is parallelised yet.

| Command | Wall time |
|---|---|
| `make test` | ~25 s |
| `make baseline` | ~3 s |
| `make burn-vs-bake` | ~4 min (27 one-dimensional + 140 grid evaluations) |
| `make doe` | ~6 min on 6 worker processes (~9300 coupled evaluations; M4, added 2026-09-20) |
| `make optimize` | ~13 min on 6 worker processes (3 methods × 7 seeds × 1000 evaluations) |
| `make ablation` | M5, added 2026-09-20. **Not yet run to completion**; estimated ~2–3 h, almost all LLM latency (≈ 5 min per call, ≤ 80 calls). Needs the Claude Code CLI installed and signed in; reads no API key. |
| `make ablation-replay RUN_ID=…` | re-runs a recorded M5 study with **no LLM access**; a few minutes (evaluations and GP fits only) |
| `make cfd-design-points` | M3, added 2026-09-20. **Needs OpenFOAM.** Coarse mesh, 56 design points + 2 scale-check cases, 4 serial solvers side by side: **~55 min** measured on a fanless Apple M4 (4 performance + 6 efficiency cores) while the M2 benchmark and an interactive session were also running; roughly 2–5 min per case. A later patience pass for force-unconverged cases and the 8-point medium-mesh subset (`LEVEL=medium SUBSET=mesh-check`) add about an hour. `LEVEL=medium` for the whole design is estimated at ~8 h (not run). Resumable: finished cases are loaded, never re-run. |
| `make aero-surface RUN_ID=…` | ~20 s (GP fit, 5-fold CV, four figures); no OpenFOAM |
| `make m3-coupled RUN_ID=…` | ~1 min (about 60 coupled evaluations + report); no OpenFOAM. Needs `results/M4/M4-OPT-…/candidates.parquet` for the M4-front designs |
| `make adaptive` | M6, added 2026-09-20. **Not yet run.** **Needs OpenFOAM, gate G4 = PASS, and a DOE/M4 re-run on `cfd_surface_v1`** (it refuses otherwise). Estimated **3.3–5.1 h**: 160–182 coarse-mesh CFD cases, 3 serial solvers side by side, from M3's measured 214 s median per case / 304 s mean per attempt; F0 evaluations add ~15 min and overlap. Makes ≤ 30 live `claude -p` calls unless `SKIP_LLM=1`. Run it in the background; if the source guard aborts it, `REUSE_CFD=<run>` reuses the finished CFD cases. |
| `make adaptive-report RUN_ID=…` | seconds; figures + report from the run's files |
| `make adaptive-smoke` | ~10 min: 1 seed, 2 real CFD promotions, one at a time. Not a result; writes only into `results/M6/<run>/` |
| `make adaptive-dry-run` | ~4 min, no OpenFOAM: the whole M6 pipeline with a FAKE analytic F1. Not a result |
| `make uncertainty` | M7, added 2026-09-20. **Not yet run.** Refuses until `make doe && make optimize` have been re-run (the current screening is void for today's design space). Estimated **~15 min** on 6 workers: 4 designs x 3000 nested draws + 2 designs x 2816 Saltelli points + the §39 table, projected from a per-evaluation cost the script MEASURES at launch and prints beside the value declared in `configs/uncertainty.yaml`. |
| `make robust` | M7. **Not yet run.** Estimated **~1 h** on 6 workers: 3 seeds x 30000 inner evaluations (24 candidates x 32 common random draws per generation, ~39 generations) plus 8 x 1000 full-Monte-Carlo evaluations to verify the shortcut. Background it. |
| `make uncertainty-smoke` | ~2 min: the robust and propagation chains end to end at tiny sample sizes. Not a result; writes only into `results/M7/<run>/` and publishes nothing. |
| `make uncertainty-time` | seconds; measures and prints the per-evaluation cost the study is sized from. |

A single `evaluate_design` call takes roughly 1.5 s, dominated by the TPS solve
(~2800 implicit timesteps over 140 cells).

## What is deterministic

Everything. There is no random sampling anywhere in the Fidelity-0 chain, so repeated
runs on the same commit produce bit-identical `candidates.csv`. Timestamped run IDs and
directory names differ, and the report headers record the git commit and whether the
working tree was dirty.

**Stochastic studies (M4 onwards) take and record an explicit seed**, which is what
"deterministic" means for them: same seed plus same evaluator source gives the same
`candidates.csv`. M7's seeds are all in `configs/uncertainty.yaml` (propagation, Sobol'
design, robust inner sample, robust optimiser, shortcut verification and the §39 table each
have their own) and the whole config is snapshotted into the run directory. Two further
guarantees, both enforced by code rather than by care:

* **One evaluator per study.** Worker processes import `src/aether` when they are spawned,
  so an edit to the physics during a long run would silently split one candidate log
  between two models (NR-18). Every M5, M6 and M7 runner hashes the package at launch,
  re-checks after every logged batch, and on a change writes `ABORTED.md` into the run
  directory and stops - after the evaluations already paid for are on disk.
* **One design space per study.** The active-variable list comes from a DOE screening, and
  a screening is only valid for the model it was made on. M7 refuses to start when the
  screening is void for today's design space, and prints the reasons.

## Provenance of every result

Each run writes `results/<milestone>/<run-id>/`:

- `candidates.csv` — every candidate evaluated, including infeasible ones
- `joint_grid.csv` — the 2-D grid, for M1
- `config_snapshot.yaml` — an immutable copy of the config plus `RunMeta`
  (run ID, config hash, git commit, dirty flag, UTC timestamp, version)

Reports in `reports/milestones/` are generated from those files, never hand-edited.
Every number in a report is read from data. If you edit a report by hand, the next
`make burn-vs-bake` will overwrite you, which is the intended behaviour.

## Reproducing the headline numbers

```bash
make burn-vs-bake
```

should reproduce, on the committed baseline configuration:

- Spearman ρ(q''_max, T_bond,max) = **−1.000** over the 27-point sweep
- **0 of 27** candidates feasible with geometry frozen
- **21 of 140** feasible on the 2-D grid
- peak-flux-only optimum: q'' = 37.0 W/cm², T_bond = 444.1 K
- joint O1 optimum: q'' = 44.3 W/cm², T_bond = 411.6 K
