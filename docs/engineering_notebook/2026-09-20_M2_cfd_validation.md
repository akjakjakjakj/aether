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

---

## 2026-09-21 — addendum: the run finished, and the fine mesh did not converge

(The agent that wrote the entry above was lost in a session restart after the benchmark had
completed. This addendum is by its successor. Numbers are in the generated report and the run
directory; only the ones needed to follow the argument are repeated.)

### Observed

- All six benchmark cases ran. Coarse and medium met the declared force criterion. **Both fine
  cases missed it** after 100 000 iterations: peak-to-peak 0.28% (Mach 3) and 0.22% (Mach 6)
  against 0.1%, with drift a factor of ten or more inside its limit. The gate file said
  **LIMITED**. The hypothesis "an observed order between 1 and 2" failed too: 0.67 and 0.60.
- The oscillation is a clean cycle of 33–40 iterations (about 7–8 cell-transit times). It is not
  on the axis: the stagnation region is the quietest part of the shock layer, and the pressure
  fluctuation grows along the body to about 1% rms at the supersonic outflow
  (`M2_limit_cycle.png`). The fine-mesh density residual ends above where it started.
- Restarted from the final solutions at max Courant 0.1 and 0.05 (new cases, originals kept),
  all four meet the **unchanged** criterion in two consecutive 5000-iteration blocks. The Co 0.1
  and 0.05 values of C_D agree to 0.001%; both sit 0.03% below the Co 0.2 window mean.
- With the converged fine values the observed order of C_D is 1.13 / 0.88 and GCI_fine 0.10% /
  0.19%. The gate file now says **PASS**.
- The negative case (full-body sphere) failed the criterion, as it must. The pipeline demo died in
  the sphere-sized domain, ran USABLE in M3's blunt-cone domain, and an isolation case showed the
  domain, not the impulsive start, was the cause.
- p0/p∞ is a last-iteration snapshot: two solutions on the same fine mesh differ by 0.4% at
  Mach 3, so its "oscillatory" mesh convergence moved from Mach 3 to Mach 6 when the fine
  solution changed.

### Interpretation

The criterion did its job twice: it refused a fine solution that *looked* converged (tiny drift,
plausible mean), and the mean it refused was in fact off by 0.03% — not much, but a third of the
difference the observed order is computed from, which is why the order jumped from 0.6–0.7 to
about 1 once the fine level was really converged. The lesson is A-CFD-15: the stable Courant
number is a property of the mesh level, and NR-07 had already said so at the level below.

What the PASS is worth has to be read with how it was reached. The criterion, the tolerances and
the mesh rule are untouched. But the restart rule, the two-block minimum and the choice of which
fine solution is "of record" were all written after the LIMITED result had been seen. They are
the textbook next step (spec §36 puts the Courant number sixth, before solver settings and
physics), each makes the test harder or is neutral, and the evidence for the LIMITED reading is
kept beside the evidence for the PASS reading — but "pre-declared" cannot be claimed for them,
and the Mach 6 margin (0.077% of 0.1%) is thin.

The observed order is weakly determined: moving the fine value across its own ±0.04% iterative
band moves p between 0.5 and 1.4 at Mach 6. The GCI should be read as "a few tenths of a
percent", not to two significant figures.

### Next

- **Student to decide** whether a PASS reached through a post-hoc restart rule is accepted as
  PASS for downstream use. The proposal below is separate from that and is NOT applied.
- M3's six rejected capsule cases (NR-21) show the same limit-cycle signature; the same
  lower-Courant restart is the obvious thing to try there. Not done here (results/M3 untouched).
- The M3 GCI hook reads the coarse-level band from `gci.csv`; that value changed (0.84% → 0.63%)
  when the fine solution changed. Surfaces built before this should be rebuilt, not patched.
- p0/p∞ and Δ/R should be window-averaged like the force (needs periodic sampling in the case
  template). Until then their GCI rows are indicative only.
- Someone with library access should read Celik et al. (2008) against `gci.py`, and Billig (1967)
  for the exponent (sourcing report item 9).

### PROPOSAL — for the student to approve or reject. NOT applied to the gate logic.

**Amendment for statistically stationary solutions.** A case that misses the peak-to-peak limit
may be accepted as *stationary* (not *converged*) if, over a window of at least 20 dominant
periods: (a) the drift between half-window means is within the existing 0.02% limit, (b) the
peak-to-peak is bounded below a declared ceiling (say 0.5%) and not growing between two
consecutive windows, and (c) half the peak-to-peak is carried as an explicit iterative
uncertainty on that case's C_D, added to the discretisation band rather than dropped.

*For:* it describes what shock-capturing TVD solutions actually do; it never discards
information (the amplitude becomes an error bar); M3 would recover most of its six rejected hull
anchors; the columns it needs already exist in `gci.csv`.

*Against — and this milestone is the evidence:* the two fine cases would have passed it, and
their means were **biased** by 0.03%, not merely noisy; an error bar of ±0.14% would have covered
that here, but nothing guarantees it in general. A lower Courant number removed the problem
outright at a cost of 25 minutes. An amendment written the day its author's cases fail is
exactly the kind of rule spec §30 exists to prevent. If adopted at all, it should apply only
after a lower-Courant restart has been tried and has failed, and never to a benchmark case that
decides a gate.
