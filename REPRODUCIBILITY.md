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
```

## Expected runtime

Measured on an Apple M4, single-threaded. Nothing here is parallelised yet.

| Command | Wall time |
|---|---|
| `make test` | ~25 s |
| `make baseline` | ~3 s |
| `make burn-vs-bake` | ~4 min (27 one-dimensional + 140 grid evaluations) |

A single `evaluate_design` call takes roughly 1.5 s, dominated by the TPS solve
(~2800 implicit timesteps over 140 cells).

## What is deterministic

Everything. There is no random sampling anywhere in the Fidelity-0 chain, so repeated
runs on the same commit produce bit-identical `candidates.csv`. Timestamped run IDs and
directory names differ, and the report headers record the git commit and whether the
working tree was dirty.

When Latin Hypercube sampling and stochastic optimisers arrive (M4, M7), every study
must take and record an explicit seed. That is not yet needed and therefore not yet
implemented.

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
