# 2026-09-20 — M4 at Fidelity 0: which variables matter, and what does an optimiser do with them?

## Question

M1b showed, on a two-variable grid, that a joint objective picks a cooler-bondline design than
peak-flux-only. Does that survive when the whole capsule geometry and the entry angle are
opened up, the irrelevant variables are screened out properly (spec §21), and real optimisers
are turned loose under a fixed evaluation budget (spec §22)? And — since the CFD gate is still
closed — how much of this can be built *now* so that Fidelity 1 is a config change?

## Hypothesis

Written before any M4 run:

1. With a constant C_D the trajectory sees only mass, diameter and entry state, and heating
   sees only nose radius. So shoulder radius, both cone angles and length should have
   **exactly zero** effect on every objective — not small, zero. If a sweep shows anything
   else, the evaluator has a bug.
2. Diameter and bluntness both improve both objectives monotonically. An optimiser will
   therefore push them until something stops it, and if the only thing that stops it is a
   box bound, that is an exploit of the model, not a design. Expected exploits, by
   arithmetic: (a) a heat shield heavier than the 350 kg vehicle once D exceeds roughly
   3.5 m; (b) an arbitrarily flat nose, because `effective_nose_radius_m = nose_radius_m`
   has no saturation.
3. The genuine trade-off will be carried almost entirely by flight-path angle, between the
   deceleration limit on the steep side and either the bondline limit or the box on the
   shallow side.
4. The problem left after screening will be low-dimensional and easy, so the three
   optimisers should differ little in final hypervolume; any difference should show up in
   how fast they get there.

## Action

1. Measured the cost of one `evaluate_design` call first, and profiled it: a fraction of a
   second, dominated by the banded conduction solves. That decided Sobol' over Morris.
2. Extended `evaluate_design` — still the only evaluation path — to take a full
   `CapsuleGeometry`, call `validate()`, and return an invalid capsule as an infeasible
   result with the validator's message (NaN metrics, no physics run). Sutton–Graves now takes
   `effective_nose_radius_m`, the trajectory takes `reference_area_m2`, and drag comes from
   `aerodynamics.build_cd_model`, which reads `vehicle.aero.model` and returns the fidelity
   level that is stamped on every candidate. Legacy two-parameter configs take the old branch
   and reproduce bit-identically (tested).
3. Built `src/aether/optimization/`: design space from YAML, budget wrapper, append-only
   candidate log, Pareto/hypervolume/spacing/knee utilities (the canonical `pareto_front`
   moved here from `studies/joint_sweep.py`, re-exported there), Saltelli/Jansen Sobol'
   estimators with bootstrap CIs, NSGA-II (pymoo, ask/tell, parent IDs tracked through SBX),
   scalarised DE over a weight sweep, LHS floor.
4. Declared everything in `configs/design_space.yaml` before running: ranges, roles, the
   freeze rule, the hypervolume reference point, budget, seven seeds.
5. `make doe`: one-at-a-time sweeps, 3000-point LHS over the full ten-variable box, Saltelli
   design on an all-valid sub-box. Then `make optimize` on the variables the screening left
   free.
6. Inspected the winning designs by hand, variable by variable, and ran the audit.

## Expected

See Hypothesis. Also expected: a large fraction of the ratio-parametrised box to be
geometrically invalid at small cone half-angles, because a blunt nose needs a wide cone.

## Observed

Numbers are in the generated report, `reports/milestones/M4_pareto_optimisation.md`, and in
`results/M4/<run-id>/summary.json`. They are deliberately not retyped here. Qualitatively:

- Hypothesis 1 held exactly: the four shape variables produce a range of 0 in both objectives
  and in max g. But cone half-angle is **not** removable — it decides which bluntness ratios
  are geometrically possible, so the screening rule (which looks at validity as well as at
  the objectives) kept it active. Freezing it at the baseline 25° would silently have capped
  bluntness near 0.54.
- More than half the full-box LHS is geometrically invalid, nearly all for that reason.
- Both predicted exploits appeared. Without the mass-closure constraint every non-dominated
  LHS design carried a heat shield heavier than the vehicle (NR-13). With it, the front sits
  *on* that constraint and on the bluntness cap (NR-15).
- One thing not predicted: for the designs both objectives favour, a tenth to a fifth of the
  external heat load accrues above 86 km, in the flagged part of the atmosphere model. A-ATM-2
  calls that region negligible. It is, for peak flux. It is not, for the bondline (NR-14).
- Hypothesis 3 held: the front is traced by entry angle alone, from the shallow box bound to
  the 12 g limit. The bondline allowable is not active anywhere on it.
- Hypothesis 4 was half right. NSGA-II ended clearly above the other two with a tight seed
  spread. The scalarised-DE baseline did **not** beat the LHS floor: splitting the budget
  over five weights leaves about nine generations per weight, and in a box where only a few
  percent of random designs are feasible that is not enough to converge. The settings were
  declared before the run and were not retuned afterwards.
- No design was still warming at the bondline when the soak-out window closed.
- The first Sobol' pass gave first-order confidence intervals on the bondline as wide as
  [−0.4, 1.1]. Cause: the Saltelli first-order estimator multiplies by f(B), and the bondline
  is a ~400 K mean with a few tens of K of spread, so the estimator's variance is dominated by
  the mean. Centring the output (the indices are shift-invariant) fixed it without a single
  new evaluation. Total-order indices, which the freeze rule uses, were never affected.
- The first DOE run drove the machine's load average above 30 with six workers: each worker
  had its own BLAS thread pool. Pinning one thread per worker removed it and made the
  throughput of the optimisation runs roughly double the DOE's.

## Evidence

- `reports/milestones/M4_pareto_optimisation.md` (generated), `reports/figures/M4_*.{png,pdf}`
- `results/M4/M4-DOE-*/` and `results/M4/M4-OPT-*/`: `candidates.csv|.parquet` (every
  candidate, invalid ones included), `summary.json`, `screening.json`, `config_snapshot.yaml`
- `tests/test_pareto.py`, `tests/test_optimization.py`
- `docs/negative_results.md` NR-13, NR-14, NR-15; `ASSUMPTIONS.md` A-OPT-1 … A-OPT-11

## Interpretation

The honest summary of M4 at Fidelity 0 is that the optimisation problem is nearly
one-dimensional. Diameter and bluntness are free improvements that run until a constraint
stops them, and both of the constraints that stop them exist only to fence off a hole in the
model. (They were anticipated and put in before the first run, not discovered by it; the
evidence that they were needed is the counterfactual in the report's audit, computed from
the same candidate log with each constraint ignored in turn.) One is a logical necessity (mass closure at 1.0), the other a placeholder
(bluntness 1.2). Only the entry angle trades the two objectives against each other. The
burn-vs-bake trade-off itself survives inside the feasible region — shallower is lower-flux
and hotter-bondline, as in M1 — but its size along the front is what the report says and no
more, and the absolute level of the front is set by placeholders.

That is a result about the *model*, and it is the argument for Fidelity 1: capsule shape will
only become a design variable when C_D depends on it. The infrastructure is the durable
product of this session; the fronts are not.

One disclosure. The hypervolume reference flux (2.5 MW/m²) was written into the config before
any optimiser ran but after the evaluator had been timed on four hand-picked designs, so the
order of magnitude of the flux was already known. It was checked afterwards against the DOE
(no feasible LHS design exceeds it) and not changed.

## Next

1. When G4 is PASS and the M3 response surface exists: register it in
   `src/aether/aerodynamics`, set `vehicle.aero.model`, `make doe && make optimize`. Expect the
   screening to change — that is the point.
2. Replace the bluntness cap with a sourced corner-radius correction in
   `CapsuleGeometry.effective_nose_radius_m`.
3. Replace the mass-closure limit of 1.0 with a sourced mass budget or a size-dependent mass
   model; then un-defer insulator thickness together with a mass objective.
4. Finish G1A′ (remaining rows and the interpolation of the >86 km table); decide whether
   Sutton–Graves should be switched off above the continuum limit.
5. M5 plugs a fourth method into `optimization.METHODS` and inherits the budget meter as is.
