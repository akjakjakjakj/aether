# Negative results and things that broke

Kept deliberately. A repository that only shows what worked is a marketing document.

---

### NR-01 — The radiating boundary condition diverged

**What happened.** The first TPS implementation solved the surface energy balance
`q_net = q_conv − εσ(T_s⁴ − T_sink⁴)` by damped fixed-point iteration. At realistic
entry heat fluxes (~2 MW/m²) the surface temperature overflowed to infinity and the
linear solve failed with `array must not contain infs or NaNs`.

**Why.** Fixed-point iteration on a T⁴ law has a local gain of `4εσT³ · R_half`. At
T ≈ 2000 K that gain exceeds 1, so the iteration is divergent, and damping only slows
the divergence.

**Fix.** Newton-linearise the radiation term about the current surface estimate,
`q_rad ≈ q_rad(T*) + h_rad(T_s − T*)` with `h_rad = 4εσT*³`, which makes the surface
flux affine in the unknown and folds it directly into the tridiagonal system. `h_rad`
only ever *adds* to the diagonal, so the scheme is unconditionally stable.

**Kept because** the failure mode is instructive: an explicit-looking treatment of a
strongly nonlinear boundary condition is not merely inaccurate, it is unstable.

---

### NR-02 — Truncating the thermal solve hid ~50 K of bondline heating

**What happened.** The first version ended the conduction solve when the trajectory
reached its terminal altitude. The bondline peak came out ~50 K too low for a 20 mm
stack.

**Why.** The bondline peak *lags* the heat pulse. Heat already inside the TPS keeps
diffusing inward after aeroheating has stopped, so the peak occurs minutes after the
vehicle has finished decelerating.

**Fix.** The evaluator now continues the conduction solve at zero incident flux for a
configurable soak period (default 1200 s), with re-radiation still active. It is inside
`evaluate_design`, not in a study script, so it cannot be forgotten.

**Kept because** this would have systematically understated the project's own headline
result. It is now a regression test: `test_bondline_peak_lags_the_heat_pulse`.

---

### NR-03 — The first TPS stack was too thick to show anything

**What happened.** With a 40 mm insulator the bondline rose from 300 K to 308.8 K over
the whole entry. The burn-vs-bake effect was invisible.

**Why.** The diffusion length √(αt) for α ≈ 8.9×10⁻⁷ m²/s over a 245 s entry is about
15 mm. Behind 40 mm of insulator the bondline simply never hears about the entry.

**Fix.** The stack was sized to 15 mm, where the bondline is a live constraint. This is
also the realistic design point: nobody flies a heat shield with 2.5× more thickness
than the thermal problem requires, because it is all mass.

**Kept because** it is worth stating plainly that the effect *can* be designed away by
brute-force insulation, at a mass cost. The result is about where the interesting
trade lives, not a claim that every vehicle is at risk.

---

### NR-04 — The Pareto front implementation was wrong

**What happened.** The first `pareto_front` returned all 21 feasible designs as
non-dominated, and the plotted "front" zigzagged.

**Why.** The dominance test had inverted control flow: when it found a point that
dominated candidate *i*, it `continue`d — keeping *i* — instead of marking it dominated.

**How it was caught.** By looking at the rendered figure. A two-objective Pareto front
is necessarily monotone; a zigzag is geometrically impossible, so the plot falsified the
code. The test suite had not caught it because no test asserted monotonicity.

**Fix.** Rewritten as a direct dominance check, plus a monotonicity assertion.

**Kept because** it is the clearest example in this project of a figure functioning as a
test. It is also why the plotting standard requires real axes and real units — a
prettier, less quantitative chart would have hidden it.

---

### NR-05 — The first CFD run died in seven iterations with a negative temperature

**What happened.** First end-to-end run of the M2 pipeline: full sphere, Mach 3, 4800-cell
wedge mesh, slip wall, uniform freestream as the initial condition, local time stepping at
max Courant 0.5. `rhoCentralFoam` stopped with a floating-point exception inside `sqrt` after
7 iterations. At Courant 0.2 it died after 17 iterations and at 0.05 after 71 — the same
*pseudo-time* each time, which says the blow-up is a developing flow feature, not a time-step
instability.

**Isolation (spec §36 order).** Geometry and mesh: `checkMesh` passed. Boundary conditions:
unchanged from the tutorials. Initial conditions: fields written one iteration before the
crash showed T = 4.4 K and p = 7.8 Pa (freestream 220 K, 1000 Pa) in the cell directly behind
the sphere on the axis. Removing the function objects made no difference.

**Why.** An impulsive start asks the gas at the back of a slip-wall body to leave at Mach 3
with nothing to replace it. The expansion runs to a near-vacuum and the energy equation
returns a negative temperature.

**Fix.** `setFields` initialises the gas in the body's shadow (downstream of the
maximum-radius station, within 1.2 body radii of the axis) at rest, at freestream p and T. It
changes the starting transient only.

**Side finding.** After the crash the calling shell hung: on this macOS build the solver's
crash handler waits on stdin. `run_foam` now closes stdin and enforces a timeout on every
OpenFOAM call, and `tests/test_cfd_openfoam.py` checks that a crashing command returns a failed
step instead of hanging.

**Evidence.** Scratch run, not preserved (the prototype directory was cleaned before the
decision to keep prototypes). The fix is in `cfd/templates/rhoCentralFoam_axisym/system/setFieldsDict`.

---

### NR-06 — An inviscid wake never settles: the full-body sphere was abandoned

**What happened.** With NR-05 fixed, the full-body sphere ran. Over 20 000 iterations the
forebody drag coefficient sat within about ±0.1% of a constant, but the **afterbody
contribution kept climbing** (roughly 0.09 at 3000 iterations, 0.12 at 20 000, still rising),
and the density residual stopped falling at about a quarter of its starting value.

**Why.** In the Euler equations nothing physical fixes the base pressure of a bluff body. The
recirculation behind the sphere exists only through numerical dissipation, so its pressure is
a property of the mesh and the scheme, and under local time stepping it drifts on a
timescale far longer than the forebody's. Even a converged value would not have been
trustworthy.

**Decision.** The production domain is **forebody only** — nose to the maximum-radius station,
closed by an outflow plane where the flow is supersonic (the pipeline measures the minimum
outflow Mach number on every case). Consequences, accepted and written down: base drag is not
computed by Fidelity 1 (ASSUMPTIONS A-CFD-5), and the sphere's measured *total* drag cannot be
compared like-for-like, so that part of the benchmark is LIMITED.

**Evidence.** The first observation was a scratch run, not preserved; the numbers above are
from that run and are approximate. The configuration is re-run inside the audited pipeline as
the `spherefullbody_*` case of every validation run, and its measured drift is printed in
`reports/milestones/M2_cfd_validation.md` under "What did not work".
`extent: full` remains available in the mesher for exactly this purpose.

---

### NR-07 — Max Courant 0.5 leaves a limit cycle in the drag coefficient

**What happened.** Forebody sphere, Mach 3, 80×60 mesh, max Courant 0.5 (the value used by
OpenFOAM's own `rhoCentralFoam` local-time-stepping tutorial). After 6000 iterations C_D was
still oscillating with a peak-to-peak of 0.157% of its mean over the last 2000 iterations,
against a declared limit of 0.1%, and the density residual had not dropped at all.

**Fix.** Max Courant 0.2: peak-to-peak 0.029%, criterion met, residual down by about a factor
of ten before it plateaus. The mean C_D moved by under 0.1% between the two settings
(0.84597 → 0.84516), so the oscillation was noise about the right answer, not a different
answer.

**Still true after the fix.** The density residual **plateaus about one decade down** and does
not go to machine zero. With a TVD limiter the captured shock keeps flickering between
neighbouring cells. Force convergence is therefore the criterion of record, and the report
says so rather than showing a residual plot cropped to look better.

**Evidence.** `results/M2/prototypes-20260920/forebody_coarse80x60_M3_Co0p5/` and
`.../forebody_coarse80x60_M3_Co0p2/` (`case_result.json`, `force_history.csv`).

---

### NR-08 — MPI made the solver slower

**What happened.** To budget the fine mesh, 300 iterations of the 76 800-cell case were timed
with 1 rank and with 8 MPI ranks (scotch decomposition). One rank: 45 s. Eight ranks: 73 s.

**Why (probable, not verified).** A 2-D explicit solver on 9600 cells per rank does very
little arithmetic per iteration relative to its halo exchanges and its per-iteration
function-object reductions; the native macOS build's MPI adds latency on top.

**Decision.** Production runs are serial. The cost per design point is reported per mesh level
in the M2 report so M3 can budget. If M3 needs throughput, the right lever is running several
serial cases side by side, not decomposing one.

**Evidence.** `results/M2/prototypes-20260920/mpi_timing/`.

---

### NR-09 — A fixed iteration count missed the convergence criterion by a hair

**What happened.** First launch of the real validation study (run `M2-20260920T123535Z`).
`sphere_M3_coarse` ran its planned 10 000 iterations and **failed the declared force
criterion**: peak-to-peak 0.063% (limit 0.1%, fine) but half-window drift 0.0219% against a
limit of 0.02%. C_D was still creeping down in the fifth decimal place. The Mach 6 coarse case,
same settings, passed.

**What was NOT done.** The drift limit was not moved from 0.02% to 0.025%. It was declared
before the run; a criterion that is relaxed the first time it bites is not a criterion.

**Fix.** The pipeline now runs until converged: if the criterion is not met at the planned
iteration count it continues from the latest time in blocks of half the planned count, at most
three times, and re-tests. A case that still misses after the last extension is reported as
not converged. The number of extensions each case needed is in the report's case table, so the
cost of convergence is visible rather than hidden.

**Evidence.** `results/M2/M2-20260920T123535Z/` (aborted run, kept; see its README).

---

### NR-10 — The Thermal Penetration Index was discarded: it restates the bondline peak

**What happened.** Spec §44 proposed a Thermal Penetration Index — a weighted double
integral, over TPS depth and over time, of temperature exceedance above a reference
temperature. It was implemented (`src/aether/scoring/tpi.py`), verified against
closed-form cases, and evaluated over the M1b design grid (140 coupled evaluations) with
a redundancy criterion declared in `configs/tpi_study.yaml` **before** the run.

It failed that criterion decisively. TPI's ranking of designs is **99.94% reconstructible
by rank regression on (peak bondline temperature, integrated heat load)**; Spearman ρ
against peak bondline temperature alone is **+0.9992**; 91 of 9730 ordered design pairs
(0.94%) are ranked differently; and a TPI-minimising optimiser selects the **same design**
as a bondline-minimising one. All 16 declared combinations of reference temperature and
weighting family exceeded the threshold, so it is not an artefact of one setting.

**Why — and a pre-registered prediction that was half wrong.** `docs/theory/tpi.md` §5,
written before the run, predicted the outcome and gave a mechanism: that the integrand
`max(T − T_ref, 0)` would be *dominated by the outer millimetre or two*, because the
surface sits at thousands of kelvin while `T_ref` is a few hundred.

The outcome was predicted correctly. **The mechanism was not.** The exceedance does peak
at the surface — in the shallowest cell, 0.06 mm deep, for every one of the 140 designs —
but it does not dominate: the outermost 20% of the TPS depth carries only **27.6–40.6%**
of the integral, against the 20% a uniform profile would give. The profile falls smoothly
by a factor of a few across 15 mm. It is not a surface spike.

The real mechanism is **shape invariance**. Normalised to unit length, the exceedance
profiles of all 140 designs have a minimum pairwise cosine similarity of **0.9366** (mean
0.9891). Every design produces very nearly the *same* depth profile, scaled by a different
factor. Any weighted depth integral of a shape-invariant profile is that scale factor and
nothing more — which is why all 16 weighting/T_ref combinations fail together rather than
some of them rescuing the metric. A metric cannot separate designs along a dimension in
which the designs do not differ.

This is left recorded rather than quietly corrected in the theory document, because the
prediction and the diagnostic that refuted it are both part of the result. The §5 text is
unchanged; §6 of that document is the addendum.

**What was done.** The verdict is **DISCARD** and §44 is closed. The implementation and
the study are kept: the metric is not wrong, it is redundant, and the evidence that it is
redundant is worth more than the metric would have been. No claim of a new aerospace
standard is made anywhere, which §44 explicitly forbids.

**Kept because** the temptation with a project-defined metric is to adopt it and report
its number alongside the others, where nobody checks whether it carries information. The
useful move was to define the falsification criterion first, in a config file, and then
let it fire. `VALIDATION_MATRIX.md` records the row as `LIMITED`, not `FAIL`: this is a
result about one stack and one two-variable design space, and a charring ablator or a
temperature-dependent conductivity could decouple the two.

It is also the clearest example in this repository of a *diagnostic* being worth more
than a *verdict*. The verdict was predicted correctly for the wrong reason, and only the
shape-invariance statistic exposed that. Had the surface-domination mechanism been the
true one, a more aggressive depth weighting would have been worth trying; because the
profiles are shape-invariant, the thing that would have to change is the stack, not the
weighting. Two different pieces of future work, distinguishable only by a number nobody
would have computed if the prediction had simply been marked "confirmed".

**Evidence.** `reports/milestones/TPI_study.md`, `results/TPI/<run>/summary.json`,
`reports/figures/TPI_*.{png,pdf}`.

---

### NR-11 — Four traps in the coupon calibration and metrics, found by the synthetic twin

**What happened.** Before any coupon was printed, the M8 analysis chain was exercised
end to end on synthetic data generated by the project's own solver with known parameters
(`tests/test_thermal_coupon.py`). Two parameter-recovery failures showed up that would
have quietly corrupted the real experiment.

**Trap 1 — contact resistance is weakly identifiable under a prescribed flux.** Fitting
all five parameters freely, the heater-to-coupon contact resistance came back **+186% to
+531% wrong** depending on the run set, and it dragged conductivity and specific heat
~5–12% low with it. The cause is structural, not numerical: with the heater flux
*prescribed*, contact resistance does not change how much heat enters the solid at all.
It only raises the temperature of the flux-application plane, and so shows up faintly
through the surface-loss term. A least-squares fit given a parameter that barely affects
the residual will use it to absorb everything else.

**Trap 2 — a short calibration step leaves k and cp degenerate.** With a step run of
about one diffusion time (900 s for a 10 mm coupon), conductivity and specific heat both
came back ~12% low while their *ratio* — the thermal diffusivity — was recovered to 0.4%.
A transient shorter than the diffusion time only ever sees α; separating k from ρcp needs
the steady depth gradient, `dT/dx = q″/k`, and that needs the step held long enough for
the gradient to establish.

**What was done.**
- `protocol.md` §7 measures contact resistance in a **dedicated steady-state run** and
  the calibration is run with `--fix contact_resistance_m2k_w=<measured>`.
- `protocol.md` §8 requires the step run to last **at least 2–3 diffusion times** — about
  an hour for a 10 mm coupon, which is the single biggest time cost in the protocol.
- With both in place the synthetic twin recovers conductivity, specific heat and both
  loss coefficients to **better than 0.5%**, fitting at a coarser mesh (40 cells) than
  the one that generated the data (60 cells), and predicts an unseen triangular pulse to
  better than 0.1 K against the noise-free truth.
- A test asserts the weak identifiability rather than the fix, so the finding cannot be
  silently forgotten: `test_contact_resistance_is_weakly_identified_and_the_fit_says_so`
  checks that the fit's own reported uncertainty flags it.

**Trap 3 — §47's peak metrics are estimator-dependent, and the obvious fix does not
work.** The maximum of a noisy record is biased high by roughly σ√(2 ln N) — over a
kelvin with 0.4 K sensor noise and a few hundred samples — in the direction that makes a
*correct* model look like it under-predicts the peak. Argmax on a flat peak scatters by
tens of seconds.

The obvious remedy, averaging the near-peak plateau, **barely helped**: it left +1.36 K
of bias at the surface sensor. The reason is that the plateau window is *selected by the
noisy maximum*, so it contains only the samples that happened to sit within a couple of
sigma of the luckiest one, and the selection bias survives the average. Smoothing the
record first — a centred moving average over 3% of the record, applied identically to
the prediction so any rounding cancels in the difference — cut the residual bias to
+0.08 K. `compare_model.py` reports the raw and the smoothed-plateau estimator side by
side and says which to quote.

**Trap 4 — the "seeded" synthetic data was not reproducible between processes.** The
per-run noise seed was `seed + abs(hash(name)) % 10000`, and Python salts `hash()` of a
string per interpreter unless `PYTHONHASHSEED` is pinned. So the synthetic twin generated
*different* data in every process while looking deterministic within one. It surfaced only
because trap 3's marginal assertion passed on one salt and failed on the next — that is,
a test that should have been catching a bug was itself the bug. Replaced with a SHA-256
derived offset, and a test now asserts that regenerating a run reproduces the file on
disk byte for byte. **A fixture that claims to be seeded and is not turns every downstream
test into an intermittent one**, which is worse than having no fixture at all.

**Kept because** every one of these would have been invisible in the real experiment: the
calibration would have fitted beautifully, the parameters would have been wrong, and the
blind case would have failed for reasons nobody could diagnose. The synthetic twin costs
a few seconds of CPU and found all three before a single coupon was printed. That is the
argument for building it.

---

### NR-12 — The Sutton–Graves constant was re-derived from the primary and deliberately not changed

**What happened.** The long-standing open item "re-derive k = 1.7415×10⁻⁴ from NASA TR
R-376" was closed by downloading the report, reading its equation, units and Table II off
300 dpi page renders, and carrying the algebra through
(`docs/theory/sutton_graves_constant.md`). The derivation lands on **k = 1.74826×10⁻⁴**,
which is **+0.39%** away from the constant every result in this repository was computed
with. The constant was **not** changed.

**Why not — and this is the part worth recording.** The first instinct on seeing a 0.39%
gap is that the more carefully-derived number is the better one. It is not, because the
derivation is less accurate than the gap it is measuring. TR R-376's equation is written
in stagnation pressure and enthalpy; reaching the V³ form needs three substitutions the
report does not make, and each carries more error than 0.39%:

- replacing the stagnation pressure by ρV² (Newtonian C_p = 2) rather than the exact
  perfect-gas value C_p,max = 1.83937 is worth **−4.10%** on k;
- the cold-wall assumption is worth **−1.10%** at the baseline condition and −4.1% at the
  primary's hot-wall case;
- dropping the freestream static enthalpy is worth **+0.81%**.

Applying all three corrections gives 1.6717×10⁻⁴ — **−4.01%**, a *larger* disagreement in
the *opposite* direction. And the primary's own correlation carries 3.3% average / 9.8%
maximum error for air before any of this. So the code's value sits between two defensible
derivations and the evidence cannot discriminate between them.

**What was also not found.** The exact digits 1.7415 could not be reconstructed from the
primary by any route tried (eq. 42's leading 0.1106 gives 1.73728×10⁻⁴; eq. 41 at
N_Pr,w = 0.71 gives 1.71805×10⁻⁴). Their provenance in the secondary literature remains
unsourced, and the sourcing report keeps it as an open item.

**Kept because** the tempting move was the wrong one in a way that is invisible from the
result alone. Changing the constant would have shifted every heat flux, every surface
temperature and every bondline temperature in the repository by 0.4%, invalidated every
stored result, and produced a number with *worse* justification than the one it replaced —
all while looking like the conscientious outcome of a validation exercise. The useful
output of the derivation was not a new constant; it was a quantified statement that this
correlation cannot be trusted to better than a few percent, which is now in A-HEAT-1 where
it can be propagated rather than assumed away.

`test_constant_is_exactly_the_value_every_result_was_computed_with` pins the value so the
decision cannot be quietly reversed.

---

### NR-13 — With mass fixed and diameter free, the optimum was a heat shield heavier than the vehicle

**What happened.** M4 opened the full capsule geometry to the optimiser while vehicle mass
stayed a fixed 350 kg config value. Drag area grows with D², so ballistic coefficient — and
with it both objectives — improves monotonically with diameter, and nothing in the model
charged for the structure that a larger diameter implies. This was anticipated by arithmetic
before any run (TPS stack areal mass 31.2 kg/m² × forebody wetted area against 350 kg) and
then confirmed on the DOE's Latin Hypercube (run `M4-DOE-20260920T131334Z`, 3000 samples):
taking only the two pre-M4 constraints (12 g, 450 K), the non-dominated set was four
designs at 3.9–4.5 m diameter whose forebody TPS stack alone weighed **1.29 to 2.81 times
the entire vehicle**. 482 of the 1328 evaluable samples violate mass closure.

**Why it matters.** This is the same defect as the M1b open item "both optima sit on the
3.0 m diameter bound" (A-LIM-3), seen from the other side: widen the arbitrary box and the
optimiser walks straight out of the physically possible.

**What was done.** `evaluate_design` now computes `heatshield_mass_fraction` for every full
capsule and checks it against `limits.max_heatshield_mass_fraction`, set to 1.0 in
`configs/design_space.yaml` — a logical necessity, not a judgment (ASSUMPTIONS A-OPT-6).
The offending candidates stay in the log as infeasible with the reason recorded. The limit
is `null` (skipped) in `configs/baseline.yaml`, so no M1/M1b/TPI number changes.

**What this does not fix.** 1.0 only excludes the impossible. The M4 front still sits *on*
this constraint (shield ≈ 99% of vehicle mass), which no real vehicle could be. A sourced
mass budget, or a mass model in which vehicle mass grows with size, is needed before the
large-diameter end of the front means anything. Open item.

### NR-14 — "Density above 86 km contributes negligibly" is false for the bondline objective

**What happened.** The M4 metric-gaming audit records, for every design, the share of the
integrated external heat load that accrues above 86 km — the region where the atmosphere is
a log-interpolated transcribed table, flagged `extrapolated` and `LIMITED` (A-ATM-2, gate
G1A′). A-ATM-2 asserts the contribution there is negligible. Over the DOE Latin Hypercube
(run `M4-DOE-20260920T131334Z`) the share has a **median of 9.5% and a maximum of 27%**;
it exceeds 5% in 1105 of 1328 evaluable designs, and among *feasible* designs it is never
below 5.0% (median 10.8%, maximum 19.5%). It rises with diameter (linear correlation 0.83):
exactly the low-ballistic-coefficient, shallow designs that both objectives favour spend
the longest at high altitude.

**Why it matters.** Peak heat flux occurs well below 86 km and is unaffected. The *bondline*
responds to the integrated load, so up to a fifth of what drives the second objective is
computed from the log-interpolated upper-atmosphere table (gate G1A′; a concurrent check
on 2026-09-20 verified five of its rows against a primary copy of USSA-76, the remaining
rows and the interpolation between rows are still unchecked) — and from a continuum stagnation-heating correlation applied at altitudes where the flow is
transitional to rarefied, which Sutton–Graves does not describe. The optimiser is not
exploiting this deliberately, but it is pushed towards the region where the model is least
supported.

**What was done.** Nothing was tuned. The share is now a per-candidate diagnostic
(`diag__heat_load_fraction_above_86km`), reported for the front in the M4 report against a
5% audit threshold declared in `configs/design_space.yaml`. A-ATM-2's "negligible" is
contradicted by this entry; fully closing G1A′ moves from housekeeping to a prerequisite for trusting bondline differences of a
few kelvin between front designs. Open item.

### NR-15 — The nose-radius lever has no ceiling in the model, so the front sits on a placeholder

**What happened.** Sutton–Graves gives q″ ∝ 1/√R_n and the evaluator takes
`effective_nose_radius_m = nose_radius_m` (A-GEO-3). Nose radius enters nothing else at
Fidelity 0, so flattening the nose lowers both objectives and costs nothing. This was
expected before the run; the M4 optimisation (run `M4-OPT-20260920T132037Z`) confirmed it.
Every one of the 64 designs on the combined feasible front has a bluntness ratio R_n/D
between 1.18 and 1.20 against a cap of 1.2, and 54 of them are within 1% of it. Remove the
cap and 17 of the 25 designs on the resulting front lie beyond it, out to about 1.26 —
which is simply where, with a 70° cone and the frozen shoulder ratio, the nose cap stops
fitting inside the body and `CapsuleGeometry.validate()` refuses the shape.
The cone half-angle — which changes no objective at all at this fidelity — is dragged to
its 70° upper bound on 49 of 64 front designs purely because a wide cone is the only valid
geometry for a nose that flat.

**Why it matters.** For a shallow spherical segment the stagnation-point velocity gradient,
and therefore the heating, is increasingly governed by the body radius and the corner, not
by the cap's radius of curvature; the real benefit saturates. The model has no such
saturation, so the optimiser's preferred nose is decided by where the model stops being
valid, not by physics.

**What was done.** `evaluate_design` checks `limits.max_bluntness_ratio` (1.2 in
`configs/design_space.yaml`, `null` elsewhere) as a constraint. The box deliberately extends
past the cap so the rejected region is explored and logged rather than hidden. The value 1.2
is a **placeholder** at roughly the Apollo command-module proportion, recalled rather than
sourced (ASSUMPTIONS A-OPT-5).

**What this does not fix.** A constraint at the edge of validity is a fence, not a model. The
fix is a corner-radius correction inside `CapsuleGeometry.effective_nose_radius_m`, from the
blunt-body stagnation-velocity-gradient literature; with it the cap can go. Until then,
"the optimiser chose a bluntness of 1.2" means only "the fence is at 1.2". Open item.

**Follow-up, same day.** The Apollo proportion has since been checked: R_n/D = 1.20 is
verified in NASA/TM-2005-213457 (`docs/validation/sourcing_report.md`, item 7). The cap's
*value* is therefore sourced as the edge of flown experience; that it is a fence rather than
a model is unchanged.

### NR-16 — Two tooling traps in the M4 pipeline, each caught by its own output

**An uncentred Sobol' estimator.** The first DOE analysis reported first-order confidence
intervals on the bondline as wide as [−0.41, 1.15]. The Saltelli-2010 first-order estimator
multiplies by f(B); for an output with a ~400 K mean and a few tens of K of spread its
variance is dominated by the mean. The indices are invariant to a constant shift, so the
output is now centred before estimation. Same 6144 evaluations, re-analysed: the interval on
the leading variable became [0.30, 0.45]. Total-order indices — the ones the freeze rule
uses — are differences and were unaffected, so no screening decision changed.
`test_sobol_indices_recover_the_ishigami_analytical_values` pins the estimator.

**`2.5e6` is a string.** PyYAML follows YAML 1.1, in which a float needs a signed exponent;
`2.5e6` parses as text. The hypervolume code coerced it through `numpy` and computed
correctly, and the run then died in a figure caption after 21 000 evaluations. Nothing was
lost — every candidate is appended to the log as it is evaluated and `summary.json` is
written before any figure — and `--report-only` rebuilt the report from the log. The config
now says `2.5e+6` and the driver coerces the reference and ideal points to float on load.

**Kept because** both are the kind of fault that produces a plausible number rather than an
error, and the second is the argument for the append-only candidate log.
