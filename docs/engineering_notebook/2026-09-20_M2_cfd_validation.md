# 2026-09-20 — M2: can this CFD be trusted for anything, and for what exactly?

## Question

Spec §17 forbids CFD data in the optimisation loop until four things exist: mesh independence,
force convergence, a published blunt-body comparison, and written model-form limits. Can an
automated `rhoCentralFoam` pipeline meet all four on a sphere — and what is it then allowed to
be used for in M3?

## Hypothesis

An inviscid, calorically-perfect, axisymmetric computation should reproduce (a) the exact
Rayleigh-pitot stagnation pressure to about 1%, (b) the published inviscid stand-off distance
to a few percent, (c) published sphere drag to a few percent, with C_D converging at an
observed order between 1 and 2 because the captured shock is locally first order.

Expected difficulty, written down before starting: the wake. An Euler wake has no physical
base pressure.

## Action

1. Recorded the installed OpenFOAM: **v2512**, not the v2606 the spec names. Nothing was
   installed. (ASSUMPTIONS A-CFD-6.)
2. Got reference values **from the documents themselves**, not from memory: Bailey & Hiatt
   AEDC-TR-70-291 Table II (sphere total C_D), Clark's forebody expression quoted in its §4.5,
   and Van Dyke & Gordon NASA TR R-1 Table III (inviscid stand-off). Page images of the tables
   were read directly. Billig's original paper is paywalled; the formula was confirmed from
   three secondary sources, one of which prints a different exponent (3.2 vs 3.24). Everything
   that could not be verified is listed as such in `data/reference/sphere_supersonic.yaml`
   and not used.
3. Built `src/aether/cfd/`: outline → block-structured mesh sized from Billig's shock shape →
   `blockMesh` + `extrudeMesh` wedge → `checkMesh` → `setFields` → `rhoCentralFoam` with local
   time stepping → force / stagnation-line / surface / outflow sampling → metrics → GCI →
   gate. The mesher takes any (x, r) outline.
4. Ran a coarse prototype before freezing the config. It failed four different ways
   (NR-05 … NR-08), each isolated in the order spec §36 prescribes.
5. Froze `configs/cfd_validation.yaml`: criterion, tolerances, mesh sequence, forebody-only
   domain. Launched the study. The first real case missed the drift limit by a hair (NR-09);
   the limit stayed, the pipeline learned to run until converged, and the study was restarted
   under a new run ID.

## Expected

See Hypothesis. Also expected: residuals that stall (TVD limiter), so the convergence
criterion was defined on the force, not on the residual.

## Observed

All numbers are in the generated report, `reports/milestones/M2_cfd_validation.md`, and the
tables beside it under `results/M2/<run-id>/`. They are deliberately not retyped here.
Qualitatively:

- The full-body wake did what was feared: forebody drag settled, afterbody drag kept drifting.
- Max Courant 0.5 (the tutorial value) left a limit cycle in C_D; 0.2 removed it.
- The density residual drops about a decade and then plateaus. It does not reach machine zero.
- Eight MPI ranks were slower than one.

## Evidence

- `reports/milestones/M2_cfd_validation.md` (generated) and `reports/figures/M2_*.{png,pdf}`
- `results/M2/<run-id>/` — per-case force histories, samples, dictionaries, log tails, GCI and
  benchmark tables, `gate_assessment.json`
- `results/M2/prototypes-20260920/` and `results/M2/M2-20260920T123535Z/` — the failures
- `docs/negative_results.md` NR-05 … NR-09
- `tests/test_cfd_*.py`

## Interpretation

The decision that matters is the **forebody-only domain**. It converts an ill-posed steady
problem into a well-posed one and it is the honest scope of an Euler solver on a bluff body —
but it means Fidelity 1 delivers C_D,fore, not C_D. The sphere's measured total drag therefore
cannot be compared like-for-like, and the brief's comparison (c) is LIMITED: it is made against
the forebody pressure-drag expression in the same AEDC report instead.

One disclosure. The benchmark tolerances were written into the config after the coarse
prototype had already produced numbers (its forebody C_D, stagnation pressure and stand-off
were on screen). The tolerances chosen are conventional round values with a stated basis each,
and none was changed after any validation-run result; but "pre-declared" here means *before the
validation runs*, not *before any CFD number had ever been seen*.

What the gate means if it passes: the pipeline computes what the Euler equations say about a
blunt forebody, to a quantified discretisation uncertainty. It does not mean the Euler
equations are the right model for entry — that argument is in
`docs/validation/M2_model_form_limits.md`, and heating stays with Sutton–Graves regardless.

## Next

- M3 must add an explicit, separately-uncertain base-drag assumption before any CFD-derived
  C_D enters the trajectory (A-CFD-5). This is the main open risk.
- Run the project capsule (`aether.geometry.capsule`) through `run_case`; check the minimum
  outflow Mach number and the flow-field figure for each new geometry class.
- Budget design points from the wall-time table in the report; run serial cases side by side
  rather than decomposing one.
- If the OpenFOAM install changes, re-run `make cfd-validate`.
