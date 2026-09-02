# Architecture

## The one rule

Every study, sweep, DOE and optimiser goes through **`evaluate_design(config)`**. Nothing
integrates a trajectory or a TPS stack directly. That single contract is what makes
results from different studies comparable, and it is the one place where the Fidelity-1
aerodynamic surrogate can be substituted without touching a single caller.

```
config (YAML)
    │
    ▼
evaluate_design ──────────────────────────────────────────────┐
    │                                                          │
    ├─ atmosphere.USStandardAtmosphere1976   ρ, T, p, a, μ (h)  │
    │                                                          │
    ├─ trajectory.integrate_entry            3-DOF, solve_ivp   │
    │      └─ Cd:  constant  (Fidelity 0)                       │
    │             surrogate Cd(M, α, X)  ← Fidelity 1, GATED    │
    │                                                          │
    ├─ heating.heat_flux_sutton_graves       q''(t) = k√(ρ/Rₙ)V³ │
    │                                                          │
    ├─ [soak-out extension: q'' = 0 for 1200 s]                 │
    │                                                          │
    ├─ tps.solve_tps                         T(x,t), 1-D FV,    │
    │                                        backward Euler,    │
    │                                        Newton-linearised  │
    │                                        radiating surface  │
    │                                                          │
    └─ scoring.compute_metrics ──────────────► PerformanceVector┘
```

## Why the pieces are shaped the way they are

**Atmosphere returns a state object, not a bare float.** Callers need density *and* the
`extrapolated` flag together. Returning a float would make silent extrapolation easy,
which is the exact failure this module is written to prevent.

**Trajectory takes a `cd_model` callable.** The Fidelity-1 hook is a parameter, not a
future refactor. Swapping constant C_D for a CFD response surface is a one-argument
change.

**TPS solves the radiating boundary implicitly.** A T⁴ surface law under a fixed-point
sweep diverges at entry heat fluxes — it did, on the first run of this code. The
radiation term is Newton-linearised into the tridiagonal system each step, which is both
stable and unconditionally so, since the linearised radiative coefficient only
strengthens the diagonal.

**The soak-out phase is inside the evaluator, not in a study script.** The bondline peak
lags the heat pulse; a study that forgot to extend the solve would silently understate
the headline result by ~50 K. Making it structural rather than optional removes the
opportunity for that mistake.

**Interface conductivities are harmonic, not arithmetic.** Across a low-k / high-k
boundary an arithmetic mean leaks heat that physically cannot cross. This is tested.

## Fidelity hierarchy

| Level | What it is | Cost | Status |
|---|---|---|---|
| 0 | Reduced-order: USSA-76 + 3-DOF + Sutton–Graves + 1-D conduction | ~1 s per design | **Active** |
| 1 | OpenFOAM v2606 compressible aerodynamics → C_D response surface | minutes–hours per case | Scaffolded, **gated by G4** |
| 2 | Selected higher-fidelity validation cases | — | Not started |

**The gate is not advisory.** No CFD-derived quantity enters the optimisation loop until
mesh independence, force convergence, a published blunt-body benchmark comparison, and a
written statement of model-form limitations all exist (spec §17). Until then Fidelity 1
produces evidence for the validation matrix, not inputs to a design decision.

## Layout

```
src/aether/
  atmosphere/   USSA-76, exact below 86 km, flagged interpolation above
  trajectory/   3-DOF planar entry, event handling, provenance
  heating/      Sutton-Graves + integrated load
  tps/          1-D multilayer FV conduction + analytical benchmark
  scoring/      canonical PerformanceVector
  studies/      burn_vs_bake, joint_sweep, Pareto extraction
  utils/        constants (each with a source), run IDs, config snapshots
  evaluate.py   THE canonical evaluator
  viz.py        figure standards: units, captions, run IDs, PDF + PNG
configs/        YAML; physical limits live here, never in source
scripts/        thin CLI drivers only - no physics
tests/          verification: analytical benchmarks and convergence
reports/        milestones/, figures/ - regenerated, never hand-edited
results/<run>/  candidates.csv + config_snapshot.yaml (immutable provenance)
```

Production logic lives in `src/`. A script that grows physics is a bug.

## Provenance

Every run writes a `RunMeta`: run ID, config hash, git commit, **and whether the working
tree was dirty**. A result produced from uncommitted code says so, in the report header.
