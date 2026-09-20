# Research story

Dated record of how the question actually developed. Not rewritten to make the result
look predetermined.

---

**2026-08-29 — The question arrives framed.** The capstone specification was issued with
O1 already locked: jointly minimise peak external heat flux and maximum internal
TPS/bondline thermal exposure. The framing — that "cooler is not necessarily safer" —
came from the specification, not from an observation made here. Stating that plainly
matters for the authorship question.

**2026-09-02 — Fidelity 0 built and verified.** Atmosphere, trajectory, heating and
conduction implemented and tested. The conduction solver was verified against the
Carslaw & Jaeger semi-infinite analytical solution to 0.002% before it was used for
anything. Two implementation failures on the way (NR-01, NR-02), one of which would have
understated the project's own result.

**2026-09-02 — The first honest attempt showed nothing.** With a 40 mm TPS the bondline
moved by 9 K across the entire entry. This was not a null result about the physics; it
was a statement that the stack was over-insulated relative to the entry duration.
Resizing to 15 mm — the point where the bondline is actually a design constraint — is
recorded as NR-03, along with the observation that heavy insulation *can* buy the
problem away, at a mass cost.

**2026-09-02 — The result was stronger than the hypothesis required.** H0 asks for the
existence of *one* counterexample pair. What came back was Spearman ρ = −1.000 over the
whole tested domain: peak heat flux and bondline temperature are perfectly
anti-ordered across every candidate. The hypothesis was written to be falsifiable by
finding nothing; instead the entire domain is a counterexample. The reporting was
changed to lead with the rank correlation rather than the single "strongest pair",
because quoting the two endpoints of a monotone sweep as a dramatic pair would overstate
how special they are.

**2026-09-02 — An unplanned result: no feasible design existed at all.** Zero of 27
trajectories satisfied both the deceleration and bondline limits. This was not
anticipated. It reframes M1: the point is not merely that the two metrics disagree, but
that with geometry frozen there is no valid answer for either of them to select. That
observation is what motivated running the geometry axis (M1b) immediately rather than
deferring it to M4.

**2026-09-02 — H1 tested earlier than planned, and supported.** The 2-D grid recovered a
feasible region and produced the comparison the project exists to make: a peak-flux-only
optimiser lands 5.9 K from the bondline allowable, a joint optimiser lands 38.4 K from
it. Both optima sit on the diameter bound, which means the bound is currently doing the
selecting — recorded as an open item rather than presented as a clean optimum.

**2026-09-20 — A metric was proposed by the specification, built, and thrown away.** Spec
§44 asked for a project-defined Thermal Penetration Index: a weighted double integral of
temperature exceedance over TPS depth and over time. It was implemented, verified against
closed-form cases, and evaluated over the 140-design M1b grid. The falsification criterion
was written into `configs/tpi_study.yaml` before the run: discard if TPI's ranking of
designs is 98% reconstructible by rank regression on the metrics the project already
reports. Measured rank R² was 0.9994, Spearman ρ against peak bondline temperature alone
+0.9992, and a TPI-minimising optimiser picked the same design as a bondline-minimising
one. All 16 declared combinations of reference temperature and weighting family failed
together. Verdict DISCARD (NR-10; `reports/milestones/TPI_study.md`, run
`TPI-20260920T124732Z`, committed as `1ea5317`).

The pre-registered prediction in `docs/theory/tpi.md` §5 got the outcome right and the
mechanism wrong, which is the part worth keeping. It predicted the depth integral would be
dominated by the outer millimetre or two. The exceedance does peak in the shallowest cell
of the mesh for all 140 designs, but the outermost 20% of the stack carries only 27.6–40.6%
of the integral against the 20% a uniform profile would give. The real mechanism is shape
invariance: normalised to unit length, the 140 exceedance profiles have a minimum pairwise
cosine similarity of 0.9366. Every design produces nearly the same depth profile, scaled.
No weighting can separate designs along a dimension in which the designs do not differ.
Had the predicted mechanism been the true one, a harder depth weighting would have been
worth trying; because it is not, the thing that would have to change is the stack. The §5
text is left unedited and §6 is the addendum.

**2026-09-20 — Three citations were opened for the first time, and two of them did not say
what the code said they said.** A sourcing pass went after every number flagged as an
unsourced placeholder (`docs/validation/sourcing_report.md`, commit `c238735`; tests and
matrix updates in `4de6054`).

*The heating constant.* `A-HEAT-1` cited NASA TR R-376 for `q̇ = k√(ρ/R_n)V³` with
k = 1.7415×10⁻⁴. The report was downloaded and read off 300 dpi page renders. **It contains
neither that equation form nor that constant.** TR R-376 is written entirely in stagnation
pressure and enthalpy: `q̇ = K√(p_s/R)(h_s − h_w)` with K(air) = 0.1113 (Table II, p. 39).
The V³ form is a later simplification requiring three substitutions the report does not
make. Carrying the algebra through in the report's own units gives k = 1.74826×10⁻⁴,
+0.39% from the value every result in this repository was computed with. The constant was
**not** changed (NR-12). The reason is that the derivation is less accurate than the gap it
is measuring: replacing Newtonian stagnation pressure with the exact perfect-gas value is
worth −4.10%, the cold-wall assumption −1.10%, the dropped freestream enthalpy +0.81%, and
applying all three gives −4.01% in the opposite direction, while the primary's own fit
carries 3.3% average and 9.8% maximum error for air. The useful output was not a better
number but a bound: treat this correlation as ±4% at best, and propagate it. The exact
digits 1.7415 could not be reconstructed from the primary by any route tried and remain
unsourced.

*The deceleration limit.* `configs/baseline.yaml` carried "12 g", unsourced. **No document
states a flat 12 g.** NASA-STD-3001 Vol 2 Rev F Table 6.5-1 gives a duration-dependent
sustained +Ax curve, and for a deconditioned crew, which is the entry-relevant case, it
reads 10.0 g at 10 s, 8.0 g at 30 s, 5.0 g at 90 s, 4.0 g beyond 150 s. The baseline
trajectory spends 25.5 s above 10 g and 40.0 s above 8 g while "passing" the flat 12 g with
+0.9% margin. Measured on the stored M1b grid, moving the limit to 10 g leaves 4 of 140
designs feasible and moving it to 8 g leaves **none**. The number was not changed, because
which reading the project adopts decides whether this is a crewed vehicle at all, and that
is a student decision rather than an audit's. Both options and this table are written into
`ASSUMPTIONS.md` as an open decision (A-LIM-1b).

*The bondline allowable.* The same pass found that the 450 K placeholder is real. It is
449.8 K = 350 °F, the Space Shuttle Orbiter's aluminium primary-structure design limit
(NASA CR-159900 p. 1, NTRS 19790012947). It is a substrate limit rather than a universal
bondline constant, so it is the right number only because this project's structure layer is
aluminium-like; Apollo's stainless interface is 589 K and Orion's composite-over-titanium
533 K (A-LIM-1a). One placeholder turned out to be a real engineering limit and one turned
out to be nothing at all, and there was no way to tell which was which without opening the
documents.

**2026-09-20 — The baseline was re-run before and after the sourcing pass, and not one
number moved.** Peak heat flux 160.28 W/cm², peak bondline 494.8 K, max 11.89 g, bit
identical. The expectation written into the notebook beforehand was that at least one of
the three numbers would be wrong and would have to change. A validation exercise that ends
in "the value was right" is easy to under-value, and the pressure to adopt the
freshly-derived 1.74826×10⁻⁴ because it felt like the more rigorous number was real.

**2026-09-20 — The optimiser found the holes in the heating model before a reader did.**
M4 opened the full capsule geometry and the entry angle to Sobol' screening and three
optimisers at Fidelity 0 (commit `715ac9f`). Two exploits were anticipated by arithmetic
and written down before the first run; both appeared.

*A heat shield heavier than the vehicle.* Drag area grows with D² while vehicle mass stayed
a fixed 350 kg config value, so both objectives improve monotonically with diameter and
nothing charged for the structure a larger diameter implies. On the DOE's 3000-point Latin
Hypercube (run `M4-DOE-20260920T131334Z`), taking only the two pre-M4 constraints, the
non-dominated set was four designs at 3.9–4.5 m diameter whose forebody TPS stack alone
weighed **1.29 to 2.81 times the entire vehicle**; 482 of 1328 evaluable samples violate
mass closure. A `heatshield_mass_fraction ≤ 1` constraint was added (NR-13). It excludes
only the impossible: the front still sits on it, at a shield about 99% of vehicle mass,
which no real vehicle could be.

*An unbounded nose-flattening lever.* Sutton–Graves gives q″ ∝ 1/√R_n and the evaluator
took `effective_nose_radius_m = nose_radius_m`, so flattening the nose lowered both
objectives and cost nothing. Every one of the 64 designs on the combined feasible front
ended up at a bluntness ratio between 1.18 and 1.20 against a cap of 1.2, and 54 of them
within 1% of it. The cap was a placeholder at roughly the Apollo proportion. As NR-15 said
at the time, a constraint at the edge of validity is a fence, not a model, and "the
optimiser chose a bluntness of 1.2" meant only "the fence is at 1.2".

*What was not anticipated, in the same audit.* A-ATM-2 asserted that density above 86 km
contributes negligibly. That is true of peak heat flux and false of the bondline. Over the
same Latin Hypercube the share of integrated external heat load accruing above 86 km has a
median of 9.5% and a maximum of 27%, and among feasible designs it is never below 5.0%. It
rises with diameter (correlation 0.83), so exactly the low-ballistic-coefficient designs
both objectives favour are the ones that spend longest where the atmosphere model is a
log-interpolated transcribed table and Sutton–Graves is being applied to transitional flow.
Nothing was tuned; the share became a per-candidate diagnostic (NR-14).

**2026-09-20 — The fence came down, and the exploit moved to the shoulder.** Spec §42
freezes new physics except to resolve a demonstrated O1 validation failure, and NR-15 was
that case. Two primaries were opened and read: Zoby & Sullivan (NASA TM X-1067, 1965)
define an effective radius by declaring a blunt body's stagnation velocity gradient to be
that of a hemisphere of some other radius, and Ellison (NASA TN D-5121, 1969) Table I
*measures* R_b/R_eff on nine models at Mach 8. Neither publishes a formula, so the
interpolation between their points is this project's own and is labelled as such
(commit `e3c48cb`; `docs/theory/effective_nose_radius.md`).

The hypothesis written before the search was that the relation would exist as a velocity
gradient and would have to be converted, making the conversion an inference. That was wrong
in a useful direction: Zoby & Sullivan define the effective radius themselves, and Zoby
later published a Sutton–Graves-form correlation with R_eff substituted in (NASA TN D-4799
eq. 1). The substitution is the original author's, not this project's.

Measured on the 64 front designs, re-evaluated under both models in one process: R_eff is
0.685–0.693 of the cap radius, peak flux rises 20.2–20.8% and peak bondline by 6.7–9.1 K,
and all 64 remain feasible. Every one of them lands essentially on Ellison's tabulated
(K = 0.417, R_c/R_b = 0.2) point, so the correction rests on interpolating almost nothing.
That was luck rather than design. The size of what the fence was hiding: under the legacy
model an infinitely flat nose removed **98.90%** of the stagnation heat flux; under the
corrected model it removes 21.31%. The first is not a small extrapolation error, it is the
wrong answer by construction, because 1/√R_n sends heating to zero as R_n → ∞ while a real
flat-faced body has a perfectly finite velocity gradient. `max_bluntness_ratio` is now
`null` and what stops the nose flattening is geometry: `CapsuleGeometry.validate()` refusing
a cap that no longer fits inside the body. NR-15 is closed.

Two things came out of it that matter more than the headline number. **The stated
uncertainty got worse, honestly.** Ellison p. 5 states his data disagree with Zoby &
Sullivan by about 20% at K = 0.417, which is exactly where the front sits. That is ±10% on
heat flux, larger than the Sutton–Graves constant's own ±4%, and it is now the dominant
stated uncertainty on the heating chain. It is carried, not resolved by preferring one
source. **And the fix moved the exploit rather than removing it.** Under the corrected
model a rounder corner *raises* stagnation heating, so an optimiser will want a sharp
shoulder, worth 1.45% of peak flux across `shoulder_ratio`'s box, which is more than
bluntness still has on offer. A sharp shoulder is exactly where real vehicles are damaged,
and this model is stagnation-point-only (A-HEAT-4) and says nothing about shoulder heating.
The fence at 1.2 has been replaced by a lower bound on `shoulder_ratio` doing the same job
for the same reason. That is written down before the next run rather than found in the
audit afterwards. It also voids M4's screening decision, which froze `shoulder_ratio` on a
Sobol' total-order index of exactly zero: that index is no longer zero, so the DOE must be
re-derived rather than reused.

**2026-09-20 — The constant drag coefficient was hiding two errors of opposite sign.** M3
built a CFD-derived drag surface, `C_D,fore` as a Gaussian process over log(Mach) and three
forebody shape ratios, from 56 usable OpenFOAM cases (commit `e0b40c0`). Compared on the
same designs, the baseline capsule's constant C_D = 1.20 becomes 0.8904 from the surface,
which raises its peak heat flux by 16.51% and its bondline by 9.51 K; the M4-front shapes'
C_D rises to about 1.363, which lowers their peak flux by about 6% and their bondline by
2.4–3.1 K. So switching fidelity does not shift the design space uniformly. It penalises
the slender-to-moderate shapes, whose deceleration was being over-estimated, and mildly
rewards the blunt ones. The interesting result is not any C_D value; it is that one
placeholder number was wrong in two directions at once, and the direction depended on the
shape. At constant C_D the forebody shape had no aerodynamic consequence at all; with the
surface, C_D at peak heating spans 0.495–1.394 over twelve swept shapes, which moves peak
heat flux between −6.89% and +60.88%. Capsule shape becomes a design variable only when the
drag model can see it, which is the argument for Fidelity 1 and the reason M4's fronts are
superseded rather than reinterpreted.

The surface is PROVISIONAL and says so: gate G4 was IN_PROGRESS when it was built, it is on
the coarse mesh rather than the medium mesh the brief asked for, its discretisation band is
pending the M2 GCI, and 55% of the baseline's heat load accrues above Mach 20 where the
Mach-20 value is simply held. It is registered and switched off.

**2026-09-20 — A live study was aborted because the physics changed underneath it.** The
first full M5 ablation run (`M5-ABL-20260920T141724Z`) was launched as a detached two-hour
job. While it ran, a concurrent work-stream moved `src/aether/evaluate.py` to the
velocity-gradient effective nose radius. The runner had snapshotted its *config* at launch,
so the config edit could not reach it, but worker processes import `src/aether` when they
are spawned, so an edit to the *source* can split one candidate log between two physics
models with nothing in the log to say which row is which. The run's header said only "dirty
tree". It was killed part-way through the agent phase, four seeds with four recorded LLM
calls each; no `summary.json` was ever written and no number from it was inspected. The
directory is kept with a README saying it must not be analysed (NR-18).

The failure was organisational rather than numerical, and it would have produced a
complete, plausible, well-formatted report. What changed: every M5, M6 and M7 runner now
hashes each `.py` file under `src/aether` at launch, records the hash in the summary and the
report header, and re-checks it before and after every (method, seed) and after every logged
batch; on a mismatch it logs the batch already paid for, writes `ABORTED.md` and stops. The
runner also refuses to start if the DOE screening it would take its active variables from
was made on a different design space. And the report generator no longer contains
pre-written findings: its first version stated in prose that every front leans on the
bluntness and mass fences, which was true of M4's model and false of the one that replaced
it an hour later. Interpretive sentences are now emitted by code from the audit table, or
not at all. The guard proved itself twice more the same day by aborting two M6 development
runs correctly (NR-24).

**2026-09-20 — Buying one CFD point made evaluable designs into extrapolations.** In the
first M6 dry run (`M6-DRY-20260920T174426Z`, itself aborted by the source guard), an arm
that had absorbed one new training point had 6 of its next 20 designs rejected with "47 of
48 query points lie outside the convex hull", while the arm that bought nothing had none in
100 evaluations. A convex hull cannot shrink when a point is added, so this was not
geometry. The rejected designs all had `shoulder_ratio` frozen at 0.10, which is also the
top of the surface's input range; `DesignSpace` writes the ratio as a length and `shape_of`
divides it back, giving 0.10000000000000002, a unit coordinate of 1 + 2.2×10⁻¹⁶, exactly on
a hull facet. Qhull's default tolerance then made membership depend on which triangulation
it had: the same 48 query points were 48/48 inside the 56-point hull and 1/48 inside the
57-point hull, and 48/48 inside both with an explicit tolerance of 1e-12 or larger
(NR-23, commit `7d29c19`).

This was M3's extrapolation guard, not M6 code. In M6 it would have been metric gaming in
reverse: promotion punished by phantom hull rejections, biasing the study against every arm
that buys CFD, in a study whose entire question is whether buying CFD selectively pays. It
was found because an aborted development run's candidate log was read rather than
discarded.

**2026-09-20 — State at the end of the day.** M1 and M1b stand as the only final results,
and they are Fidelity-0 results whose absolute levels rest on placeholders. Every other
milestone has a built, tested harness and no study behind it: M4's fronts are superseded by
the nose-radius correction and its screening is void, M5 has no run, M6 and M7 refuse to
start until the DOE and the front are regenerated, M2's gate G4 is IN_PROGRESS, and M8 has
no measurement. That is the honest position, and it is written here rather than in a
results section because there are no results to put in one yet.

## Assumptions rejected along the way

- *That the trajectory solve could end at terminal altitude.* False; the bondline peak
  lags (NR-02).
- *That a plausible-looking Pareto plot indicates a correct Pareto implementation.*
  False; the plot is what exposed the bug (NR-04).
- *That a thicker heat shield is a conservative modelling choice.* It is conservative for
  the vehicle and **anti-conservative for the study** — it hides the effect being
  measured (NR-03).

Added 2026-09-20:

- *That a citation attached to a number means somebody checked the number.* NASA TR R-376
  contains neither the equation form nor the constant the code attributes to it (NR-12),
  and no document states the 12 g deceleration limit at all (A-LIM-1b). Both citations had
  been in the repository for weeks.
- *That "negligible above 86 km" was a safe simplification.* True for peak heat flux, false
  for the bondline, which draws 5–20% of its heat load from the flagged region (NR-14).
- *That flattening the nose was a real design lever.* It was a property of using the cap
  radius in a correlation that wants a velocity gradient. The lever collapses from 98.9% to
  21.3% of peak flux under the corrected model (NR-15).
- *That a constant drag coefficient errs in one direction.* C_D = 1.20 over-predicted drag
  for the baseline and under-predicted it for the blunt front shapes, so fidelity is not a
  uniform shift (M3 §10).
- *That a config snapshot plus a git commit and a dirty flag is provenance for a long run.*
  The dirty flag is read once, at launch, and says nothing about what changes afterwards
  (NR-18).
- *That a project-defined metric is worth reporting alongside the others.* It is worth
  reporting only if its ordering of designs contains something the existing metrics do not,
  and that has to be tested against a threshold declared first (NR-10).
- *That geometric membership tests are exact.* Whether a design at a box edge was evaluable
  depended on a floating-point residue of 2.2×10⁻¹⁶ and on which triangulation Qhull
  happened to build (NR-23).
