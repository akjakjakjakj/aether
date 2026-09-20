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
| 1 | OpenFOAM compressible aerodynamics (Euler, perfect gas, forebody only; installed build v2512, spec names v2606) → **forebody** C_D response surface | minutes–hours per case, see M2 report | Pipeline built; **status = row G4 of VALIDATION_MATRIX.md** |
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
  scoring/      canonical PerformanceVector; tpi.py (spec 44, DISCARDED - see the study)
  cfd/          Fidelity 1: outline -> mesh -> rhoCentralFoam -> metrics -> GCI -> gate G4
                design_points.py (M3): seeded (Mach, forebody shape) design, acceptance rules,
                shock-clearance check + domain re-run, 4 serial cases side by side
  aerodynamics/ drag-model registry; base_drag.py (assumed band), cfd_surface.py
                (`cfd_surface_v1`: GP of C_D,fore + base band, hull guard, G4 guard, GCI hook),
                surface_build.py (held-out + k-fold validation, persistence), plots.py
  studies/      burn_vs_bake, joint_sweep, Pareto extraction, tpi_study
  utils/        constants (each with a source), run IDs, config snapshots
  evaluate.py   THE canonical evaluator
  viz.py        figure standards: units, captions, run IDs, PDF + PNG
configs/        YAML; physical limits live here, never in source
cfd/templates/  OpenFOAM dictionary templates; cfd/generated/ holds run cases (gitignored)
data/reference/ published reference values, each with how it was verified
scripts/        thin CLI drivers only - no physics
tests/          verification: analytical benchmarks and convergence
reports/        milestones/, figures/ - regenerated, never hand-edited
results/<run>/  candidates.csv + config_snapshot.yaml (immutable provenance)
experiments/thermal_coupon/   M8 support package: CAD, protocol, data schema,
                calibration + blind-prediction chain. NOT part of the aether package -
                it imports solve_tps and is driven by its own scripts.
```

Production logic lives in `src/`. A script that grows physics is a bug.

## Fidelity 1 in one paragraph

`aether.cfd.run_case(name, outline, flow, mesh, solver, criterion, ...)` takes **any**
axisymmetric (x, r) outline — which is what `geometry.capsule.CapsuleGeometry.profile()`
returns — and produces a `CaseResult` plus CSV evidence. A CFD failure is a result, not an
exception: crashed, non-converged and mesh-failed cases are recorded with their reason. What
the numbers may be used for is fixed by `docs/validation/M2_model_form_limits.md`: forebody
pressure drag and pressure distributions yes, heating never, base drag not computed.

## Provenance

Every run writes a `RunMeta`: run ID, config hash, git commit, **and whether the working
tree was dirty**. A result produced from uncommitted code says so, in the report header.

## M4 in one paragraph

`aether.optimization` never touches physics. `DesignSpace` (from `configs/design_space.yaml`)
maps an optimiser's vector to an evaluator config; `BudgetedEvaluator` is the only caller of
`evaluate_design` on behalf of any DOE or optimiser — it charges one budget unit per distinct
design, caches repeats for free, runs batches across worker processes and appends **every**
candidate (invalid geometry included, with the reason) to `results/M4/<run>/candidates.csv`.
`aether.aerodynamics.build_cd_model` turns the config's `vehicle.aero.model` into the
`cd_model` callable the trajectory takes and reports the fidelity level, which is stamped on
every candidate row. `make doe` writes `screening.json`; `make optimize` frees exactly the
variables it left active. Moving M4 to Fidelity 1 is: register the response-surface model,
change `vehicle.aero.model`, re-run both targets.

## M3 in one paragraph

`scripts/run_cfd_design_points.py` runs the planned CFD cases through the unchanged M2
`run_case` and writes `results/M3/<run>/design_points_<level>.csv`; `scripts/build_aero_surface.py`
fits and cross-validates the GP and persists it as a training table plus pinned kernel
hyper-parameters in `data/aero/cfd_surface_v1/`; `scripts/run_m3_coupled.py` runs gate G5 and
the constant-C_D vs surface comparison and generates the report. The trajectory never calls
CFD or the GP inside a time step: for one capsule the builder tabulates the surface on a Mach
grid once and hands the integrator a smooth 1-D interpolant, so a Fidelity-1 evaluation costs
the same as a Fidelity-0 one. **`cfd_surface_v1` is registered but off**: no config selects
it, and while gate G4 is not PASS the builder raises `GateNotPassedError` unless the config
says `allow_provisional: true` (used only by the G5 study and tests). A shape outside the CFD
hull comes back from `evaluate_design` as a rejected candidate, never an extrapolated number.
Every Fidelity-1 result carries `aero_provenance` (surface hash, source run, mesh level, G4
status at build and at evaluation, uncertainty draw) and `aero_*` diagnostics (share of heat
load and flight time outside the CFD Mach range).

## M5 in one paragraph

The ablation adds methods, not a second meter. `bo_parego` (`optimization/bayes.py`), the LLM
agent (`optimization/ai_agent.py`) and its adaptive-fidelity variant all take the same
`BudgetedEvaluator` as M4's optimisers and are driven by `scripts/run_ai_ablation.py` from
`configs/ai_ablation.yaml`, which *reads* the design space, objectives and hypervolume points
from `configs/design_space.yaml` instead of repeating them. `aether.surrogate` holds the GPs:
`GPSurrogate.predict` raises outside the convex hull of its training inputs unless the caller
asks for a flagged guess, and `validation.py` scores held-out accuracy and interval coverage.
The agent sees structured JSON only and answers in a strict schema; its output is parsed with
`json.loads`, validated field by field, and rejected — never clipped — when out of bounds. LLM
access is a subprocess call to the Claude Code CLI in an empty directory with tools and
project context disabled; every prompt and raw response lands in
`results/M5/<run>/llm/<method>/seed_<n>/`, and `ReplayClient` re-runs a recorded study with no
LLM access. `optimization/fidelity.py` is the §26 promotion policy; with `available=(0,)` it
records promotions as requested-not-granted, and M6 changes that tuple. `optimization/ablation.py`
does the exact small-sample statistics, surrogate/agent scoring and the per-method gaming audit
from the persisted logs only. The runner takes its active variables only from the DOE's
`screening.json`, refuses to start if that screening was made on a different design space, and
hashes `src/aether` at launch: if the source changes mid-study it logs what was paid for,
writes `ABORTED.md` and stops (NR-18).
