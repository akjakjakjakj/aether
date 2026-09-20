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

**Follow-up, 2026-09-20 — the fence is gone, and the entry was right about the direction
but wrong about the size.** The correction the entry asked for has been found in the
literature and implemented, so this is what the fence was hiding.

*The relation.* Zoby & Sullivan (NASA TM X-1067, 1965) define an effective radius by
declaring the blunt body's stagnation velocity gradient to be that of a hemisphere of some
other radius — `R_b/R_eff = (dU/dS)_BB / (dU/dS)_hemi`, their eq. (5) — and Ellison
(NASA TN D-5121, 1969) table I *measures* `R_b/R_eff` on nine models at M = 8 over
`K = R_b/R_n` ∈ {0, 0.417, 0.707} and `R_c/R_b` ∈ {0, 0.2, 0.4}. Both documents were
opened and read; Ellison's table was transcribed from the page. Neither publishes a
formula, so the interpolation between their points is this project's own and is labelled
as such (A-GEO-3a, `docs/theory/effective_nose_radius.md`).

*How badly the old model was wrong, measured.* The entry said the benefit of flattening
"saturates". It does, and the unsaturated version was not a little wrong:

| bluntness change | Δ peak flux, legacy `R_eff = R_n` | Δ peak flux, corrected |
|---|---|---|
| 1.2 → 1.26 (where geometry refuses) | −2.41% | **−0.92%** |
| 1.2 → 1.35 (box edge) | −5.72% | **−2.15%** |
| 1.2 → infinitely flat | **−98.90%** | **−21.31%** |

An infinitely flat nose removing 98.9% of the stagnation heat flux is not a small
extrapolation error; it is the wrong answer by construction, because `1/√R_n` sends
heating to zero as `R_n → ∞` while the real flat-faced body has a perfectly finite
velocity gradient. That was the lever the fence was holding shut.

*Effect on the 64 front designs.* Re-evaluated through `evaluate_design` under both models
in one process (`scripts/reevaluate_m4_front.py`; output in
`results/M4/nose-model-recheck/`). Every one of them lands at `K` = 0.417–0.425 and
`R_c/R_b` = 0.200 — essentially **on** Ellison's tabulated (0.417, 0.2) point — so none is
extrapolated. `R_eff` is 0.685–0.693 of the cap radius; peak flux rises **20.2–20.8%**
(0.202–0.244 → 0.243–0.294 MW/m²) and peak bondline by **6.7–9.1 K** (386.9–412.0 →
393.7–421.2 K). All 64 remain feasible against the 450 K allowable, and no constraint is
newly violated. Under the legacy setting the same script reproduces the logged M4 values
to 2.4×10⁻⁵ relative on flux and 8.7×10⁻⁴ K on bondline — the residue of the run's own
`git_dirty: true`, not of this change.

*The fence.* `max_bluntness_ratio` is now `null`. It was never a design limit; it was the
edge of a model's validity, and the model no longer has that edge anywhere the optimiser
can reach (`K ≤ 1` covers every bluntness ≥ 0.5). What stops the nose flattening now is
`CapsuleGeometry.validate()` refusing a cap that does not fit inside the body — a geometry
bound, returned as an infeasible candidate that stays in the log. **NR-15 is closed.**

*What this entry did not anticipate, and what replaces it as the open item.* The
correction makes the corner radius matter, and it matters in the direction an optimiser
will exploit: a **sharper** shoulder gives a larger `R_eff` and less stagnation heating,
worth 1.45% of peak flux across `shoulder_ratio`'s box. Two consequences. First, M4 froze
`shoulder_ratio` on a Sobol total-order index of exactly zero; that screening decision is
void and must be re-derived on the next `make doe`, not reused. Second — and this is the
new open item — a sharp shoulder is precisely where real vehicles are damaged, and this
model is stagnation-point-only (A-HEAT-4) and says nothing about shoulder heating at all.
The fence at 1.2 has been replaced by a lower bound on `shoulder_ratio` that is doing
exactly the same job for exactly the same reason: keeping an optimiser out of a region the
model cannot see. It is written down here *before* the run rather than discovered in the
audit afterwards.

*Residual uncertainty, from the primaries themselves.* Ellison, p. 5, verbatim: "The data
of the present investigation agree with the results of Zoby and Sullivan (ref. 6) within
10 percent for K = 0 and K = 0.707; however, for K = 0.417 and R = 0, the disagreement is
about 20 percent." K = 0.417 is where the whole front sits. That is ±10% on heat flux —
larger than A-HEAT-1's ±4% on the Sutton–Graves constant — and it is now the dominant
stated uncertainty on the heating chain. Ellison is the conservative of the two and is
what the model uses. This is a real disagreement in the literature and is carried, not
resolved by picking a side.

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

### NR-17 — The first Bayesian optimiser converged in 50 evaluations and then spent 60% of its budget on capsules that cannot exist

**What happened.** The M5 GP/ParEGO optimiser (expected improvement × probability of
feasibility) was smoke-tested on one seed (11, 200 evaluations) before the ablation ran. Two
faults, both of which produced a plausible hypervolume rather than an error.

*A classifier that returned NaN.* Validity ("does this design return physics at all") was
first modelled with scikit-learn's `GaussianProcessClassifier`. Once the batch started
clustering near the front its Laplace approximation produced a negative latent variance and
`predict_proba` returned NaN for the whole pool. NaN × EI is NaN, `argmax` of an all-NaN
acquisition is not finite, and the loop's guard quietly fell through to space-filling
samples: the prediction log held 20 records for 180 model-driven evaluations, and the
hypervolume curve went flat at 0.351 from 50 evaluations on. Replaced by least-squares GP
classification (regress the labels ±1 with the same `GPSurrogate`, probit-squash the
predictive distribution) — cruder, cannot return NaN, and scored on held-out designs.

*EI × PoF chasing its own prior.* With the classifier fixed, the run reached a normalised
hypervolume of 0.3766 at 50 evaluations and 0.3851 at 200 — the value of M4's pooled front
of 21 000 evaluations — but only **49 of its 200 designs returned physics**. The classifier
was calibrated (of 75 picks it rated under 5% likely to be valid, none was). The acquisition
picked them anyway: after convergence, Monte-Carlo EI inside the feasible region is exactly
zero for most of the pool, while in the invalid region the objective GPs — trained on valid
designs only — revert to their prior mean with a large variance, so EI there is huge and
even a 1% probability of feasibility wins the product. A floor was added: pool points the
model itself rates below 5% probability of feasibility are excluded unless nothing else is
left (`min_probability_feasible`, A-AI-3). Same seed afterwards: hypervolume unchanged to
four decimals (0.3851), share of picks rated ≥ 0.7 likely valid up from 36 to 95 of 180.

**Why it matters.** (1) The hypervolume did not show either fault: the front on this problem
is found early, so a broken optimiser and a working one score alike at 200 evaluations. The
faults were visible only in *where the budget went*, which is why the M5 report carries a
budget-use figure and a no-physics share per method. (2) Both fixes were made after looking
at one seed of one method and before the study ran; that is disclosed in the report's
limitations. No setting of any method was changed after the ablation's results were seen.

**Provenance of the numbers above.** They were read off a console during a scratch run
(seed 11, physics as it stood before the effective-nose-radius change) whose script and
candidate log lived in a session scratch directory that no longer exists. They are real
observations but they are **not reproducible from anything on disk** and must not be quoted
as results; the mechanism is what is recorded here. Seed 11 was removed from the M5 study
seeds because this test informed a design change (A-AI-3).

**Kept because** an optimiser that silently stops optimising, and a metric that cannot tell,
is the failure this project's audit sections exist to catch.

### NR-18 — The physics changed under a live study, and nothing in the runner noticed

**What happened.** The first full M5 run (`M5-ABL-20260920T141724Z`) was launched as a
detached two-hour job. While it ran, a concurrent work-stream changed the evaluator:
`src/aether/evaluate.py` moved to a velocity-gradient effective nose radius and
`configs/design_space.yaml` now defaults to `effective_nose_radius_model: velocity_gradient`
with `max_bluntness_ratio: null`. The runner had snapshotted its *config* at launch, so the
config edit could not reach it — but worker processes import `src/aether` when they are
spawned (the pool starts them on demand, not all at launch), so an edit to
the *source* can split one candidate log between two physics models with nothing in the log
to say which row is which. The run's header said only "dirty tree". The coordinator killed
it part-way through the agent phase (four seeds, four recorded LLM calls each); four orphaned
CLI calls were still running and were stopped. No `summary.json` was ever written and no
number from the run was inspected. The directory is kept, with a README saying it must not
be analysed. The same change made `shoulder_ratio` non-inert, which voids the M4 screening
the run's active-variable list came from.

**Why it matters.** "Config snapshot + git commit + dirty flag" is not provenance for a
long run in a repository several agents edit at once: the dirty flag is read once, at
launch, and says nothing about what changes afterwards. A matched-budget comparison whose
methods were evaluated by different physics is not a comparison.

**What changed.**
1. `scripts/run_ai_ablation.py` hashes every `.py` file under `src/aether` at launch
   (`source_tree_hash`), records the hash in `summary.json` and the report header, and
   re-checks it before and after every (method, seed) and after every logged batch. On a
   mismatch it writes `ABORTED.md` into the run directory and raises `SourceChanged` — the
   batch already paid for is logged first, then the run stops.
2. The runner refuses to start if the DOE screening it would take its active variables from
   was made on a different design space or base config (`screening_is_current`): the
   active-variable list is a property of the model it was screened on. It is read from
   `screening.json` and nowhere else; the initial-design size follows the number of active
   variables instead of assuming four.
3. The generated report no longer contains pre-written findings. Its first version stated,
   as prose, that every front leans on the bluntness and mass fences — true of M4's model,
   false of the one that replaced it an hour later. Interpretive sentences are now emitted
   by code from the gaming-audit table, or not at all.

**Kept because** the failure was organisational, not numerical, and would have produced a
complete, plausible, well-formatted report.

---

### NR-19 — An impulsive start at Mach 20 kills the second-order scheme; a first-order start does not

**What happened.** M3 coarse smoke test, before any design point was run. The flattest
capsule in the design (R_n/D = 1.35, 70° cone, R_c/D = 0.02) at Mach 20 died after 22
iterations with a floating-point exception inside `sqrt` — a negative temperature, the same
symptom as NR-05 but with no wake in the domain to blame.

**Isolation (spec §36 order).** Geometry valid; `checkMesh` "Mesh OK" but with 67° maximum
non-orthogonality (a near-flat face seen from a block centre lying almost in its plane —
recorded, not fixed). Boundary and initial conditions as M2. Then three variants of the
identical case, side by side: max Courant 0.05 died at iteration 566; the Minmod limiter died
at 150; **first-order (upwind) reconstruction ran 1500 iterations without trouble**, and
switching it back to van Leer afterwards ran on to 5000.

**Why (probable).** At Mach 20 the kinetic energy is over 99% of the total energy, so the
internal energy is a small difference of large numbers; while the bow shock is still forming
from a uniform Mach-20 field against a wall, a second-order reconstruction of ρ, U and T
across it undershoots into negative temperature. A lower Courant number does not help because
the transient is the same in pseudo-time — exactly as in NR-05.

**Fix.** `run_case(..., startup_first_order_iterations=N)`: N upwind iterations, then the
declared limiter. Default 0, so every M2 case is untouched. M3 applies it to every design
point (A-CFD-13). The converged solution is obtained and judged with the M2 scheme; only the
path to it changed.

**Evidence.** `cfd/generated/M3-startup-exp/` (heavy fields, gitignored) and
`results/M3/smoke-coarse/attempts.csv`.

---

### NR-20 — A sphere's domain does not fit a cone: two ways the M2 inflow boundary was wrong for capsules

**What happened.** Same smoke test. M2's agent had flagged that a wide cone might push its
shock onto the inflow boundary; it happened, and a second case nobody had flagged happened too.

1. *Wide-angle cone, small nose* (R_n/D = 0.25, 70°, Mach 20). The boundary was sized from
   max(R_n, R_b) with Billig's **sphere** stand-off. A 70° cone's shock is detached and stands
   off like a disk's, not like its small nose sphere's. The drag kept falling for 5600
   iterations as the shock walked upstream, then the solver crashed.
2. *Slender cone* (R_n/D = 0.25, 20°, Mach 20). M2 opens the boundary at the Mach angle plus
   6°: 8.9° at Mach 20. A 20° cone's shock lies at about 22°. The boundary cut through the
   shock along most of the body.

**Fix.** Boundary placement only (A-CFD-14): the sizing radius grows to 2 R_b between cone
angles 40° and 70°, and attached-shock cones open the boundary at Rasmussen's cone-shock
angle + 5°. Placement is never trusted: every case is checked automatically — stand-off
against the distance to the boundary on the axis, and the outermost outflow faces must still
be at freestream Mach number — and a failed check **or a solver crash** triggers a re-run in a
larger domain, with every attempt kept as a row of `attempts_<level>.csv`.

**Cost, stated.** A larger domain with the same cell count is a coarser mesh near the body, so
a re-run case is not quite the same discretisation as its neighbours.

**Evidence.** `results/M3/smoke-coarse/`, `results/M3/smoke-coarse-2/` (smoke runs, killed
once they had shown what they had to show; partial tables kept).

---

### NR-21 — Five design points never met the force criterion, and waiting longer did not help

**What happened.** First pass of the M3 coarse design (run `M3-DP-20260920T1610Z`): 7 of 56
cases missed the declared force-convergence criterion after M2's three extensions. A
"patience pass" then gave each of them one more attempt with up to nine extensions — the
criterion itself untouched, which is NR-09's rule. Two converged (`dp015`, the M4-front shape
at Mach 20, and `dp051`). **Five did not, at up to 55 000 iterations:**

| point | Mach | shape (R_n/D, cone, R_c/D) | final peak-to-peak (limit 0.1%) | final drift (limit 0.02%) |
|---|---|---|---|---|
| dp001 | 20 | 0.25, 20°, 0.02 | 0.60% | 0.025% |
| dp011 | 20 | 0.80, 52.5°, 0.02 | 0.23% | 0.14% |
| dp032 | 18.4 | 0.47, 35.3°, 0.096 | 0.109% | 0.002% |
| dp043 | 14.5 | 0.40, 29.2°, 0.021 | 0.109% | 0.006% |
| dp053 | 9.9 | 1.14, 69.1°, 0.036 | 0.34% | 0.22% |

(Values from `attempts_coarse.csv`, patience-pass rows.)

**What it looks like.** Not slow convergence: `dp032` and `dp043` sit at 0.109% with
essentially zero drift — a steady limit cycle a hair outside a 0.1% band, the same signature
as NR-07 (captured shock flickering between neighbouring cells under a TVD limiter), here at
high Mach on a coarse mesh. `dp011` and `dp053` both have a small shoulder radius with the
sonic line sitting on it, and drift as well as oscillate. The mean C_D of every one of them
moved by less than 0.05% between the first pass and the patience pass.

**What was NOT done.** The criterion was not widened to 0.12% to let two of them in, and the
cases were not dropped from the record. They are REJECTED, they are listed in the milestone
report, and `cfd_surface_v1` does not contain them. A separate, labelled INCLUSIVE surface
that does contain them exists only to measure what the strict rule costs (report §10): on the
designs compared, very little.

**Consequence.** Each rejected hull anchor removes its corner from the usable design space
under Fidelity 1 (A-AERO-1): here the slender, small-shoulder corner at Mach 20 (`dp001`) and
the validity-boundary point at R_n/D = 0.8, R_c/D = 0.02 (`dp011`).

**Later the same day.** The six late anchors of NR-22 added a sixth: `dp061` (R_n/D 1.15, 68.1°,
R_c/D 0.10, Mach 20) ended at 0.49% peak-to-peak and 0.21% drift after nine extensions, while
its neighbour `dp059` met the criterion on the patience pass. And on the **medium** mesh two of
the eight mesh-check cases (`dp003`, `dp019`, both Mach 20) sat at 0.12% peak-to-peak with
near-zero drift — the same limit cycle, so refinement from coarse to medium does not remove it.
Final count: 56 usable, 6 rejected of 62.

**Disclosure.** The patience rule was added after the first pass had been seen. It is written
into `configs/cfd_design_points.yaml` with that statement.

**Evidence.** `results/M3/M3-DP-20260920T1610Z/attempts_coarse.csv`, `cases/<point>_coarse_a*`
and `cases/<point>_coarse_c0` (force histories, log tails).

---

### NR-22 — The hull anchor meant for the M4 front missed it

**What happened.** A GP may not extrapolate, the guard is the convex hull of the CFD points,
and the M4 front lives in a corner of the shape box squeezed against the geometric-validity
boundary. One anchor was placed for it, at "validity boundary + 0.5°" for R_n/D = 1.2,
R_c/D = 0.10 — a cone angle of 69.18°. The front actually spans 68.75–70.0° at R_n/D
1.177–1.198. After the first pass, four of the five M4-front designs used in the G5 comparison
came back flagged **outside the hull**: the surface built specifically to re-evaluate the
front could not, by its own rule, evaluate most of it.

**Why.** The anchor was placed from a reading of `configs/design_space.yaml`'s comment, not
from the front's actual shape range, which was on disk
(`results/M4/nose-model-recheck/front_under_both_models.csv`) and was not opened until the
flags appeared.

**Fix.** Three "late anchors" enclosing the front's shape range, at both ends of the Mach
range, appended after the fill so no existing point is renumbered. Chosen from the front's
shape range, not from any CFD value; added after the first pass, and the config says so.

**Outcome.** With the late anchors in, all five M4-front designs of the G5 comparison fall
inside the hull. A side effect, also recorded: six near-duplicate points in one corner made the
GP more overconfident (k-fold z-score spread rose from about 1.1 to about 1.65); the measured
spread is now stored with the surface and applied as a sigma inflation factor.

**Kept because** the extrapolation guard did its job — it turned a design-of-experiments
mistake into a visible flag instead of a quietly extrapolated number.

**Evidence.** `results/M3/M3-DP-20260920T1610Z/coupled/constant_vs_surface.csv`
(`aero_shape_extrapolated`), `configs/cfd_design_points.yaml` → `design.late_anchors`.

---

### NR-23 — Buying one CFD point made evaluable designs "extrapolations": the hull guard depended on the triangulation

**What happened.** First M6 dry run (fake analytic F1, development seed, `results/M6/M6-DRY-20260920T174426Z`,
aborted by the source guard and not analysed beyond this). After an arm absorbed ONE new training
point, 6 of its next 20 designs came back `aero surface extrapolation: 47 of 48 query points lie
outside the convex hull` — while the arm that bought nothing had 0 such rejections in 100
evaluations. A convex hull cannot shrink when a point is added.

**Isolation.** The rejected designs all had `shoulder_ratio` frozen at its reference 0.10, which
is also the top of the surface's input range. `DesignSpace` writes the ratio as a length
(0.10 × D) and `shape_of` divides it back: 0.10000000000000002, i.e. a unit coordinate of
1 + 2.2e-16 — exactly ON a hull facet. `TrainingHull.contains` called `Delaunay.find_simplex` with
Qhull's default tolerance, under which a point 2e-16 outside a facet is inside for one
triangulation and outside for another. Same 48 query points, same design: 48/48 inside the
56-point hull, 1/48 inside the 57-point hull; 48/48 inside both with an explicit tolerance of
1e-12 or larger.

**Why it matters.** This is M3's extrapolation guard (A-AERO-1), not M6 code: whether a design with
a variable at a box edge was evaluable under `cfd_surface_v1` was decided by triangulation luck.
In M6 it would have been a metric-gaming route in reverse — promotion PUNISHED by phantom hull
rejections — and would have biased the study against every arm that buys CFD.

**Fix.** `TrainingHull.contains` passes an explicit `tol = 1e-9` (unit-cube edge lengths;
`surrogate/gp.py: HULL_TOLERANCE`). Physically nothing; makes membership of boundary points
independent of the triangulation. Regression test:
`test_hull_membership_of_a_boundary_design_does_not_depend_on_the_triangulation`. M3's persisted
surface and its hash are untouched (the hull is rebuilt from the training table on load); a
design that M3/G5 reported as inside stays inside.

**Evidence.** `results/M6/M6-DRY-20260920T174426Z/candidates.csv` (`hull_rejected`,
`surface_version`), `surfaces/adaptive/seed_11/v000|v001`.

---

### NR-24 — The source guard aborted two M6 development runs, correctly, because of someone else's edits

**What happened.** While M6 was being built, a second work-stream (M7) was editing
`src/aether/uncertainty/` and, early on, `evaluate.py`. The NR-18 source guard — now shared by the
M5 and M6 runners (`optimization/guards.py`) — aborted two M6 dry runs (`M6-DRY-20260920T174426Z` after scoring, `M6-DRY-20260920T174923Z`
mid-run) with `ABORTED.md`. Neither was analysed, except that the first exposed NR-23.

**What it showed.** (1) The guard works on a runner it was not written for. (2) A whole-tree hash
makes it impossible to smoke-test one milestone while another is being written. (3) A 4-hour CFD
study that the guard kills at hour 3 would lose three hours of solver time.

**What changed.** (1) `SourceGuard(exclude=…)`: top-level sub-packages can be left out of the hash,
and `check()` then also refuses to continue if any excluded sub-package has been IMPORTED into the
process — the exclusion cannot hide a real dependency. Used by the smoke and dry-run overlays for
`uncertainty` only; **rejected in `mode: study`**, which is guarded on the whole tree. (2) CFD cases
are written to `cfd_cases.csv` as they finish, and `--reuse-cfd RUN_ID` / `make adaptive
REUSE_CFD=…` lets a re-launched study reuse them (same backend, mesh level and CFD configs only;
every arm is still charged). **The study should be launched when no other work-stream is editing
`src/aether`.**

**Also recorded.** The first real smoke test (`M6-SMOKE-20260920T175847Z`) spent 0 of its 2 CFD
calls: it used the greedy arm, which promotes only believed-feasible designs, and this problem
shows none in its first ~60 evaluations. Not a bug — greedy cannot act before something is
feasible — but a smoke test that exercises nothing is not a smoke test; the overlay now uses the
random arm.

---

### NR-25 — Both fine-mesh sphere cases ended in a limit cycle and failed the force criterion; the Courant number, not the criterion, was changed

**What happened.** Run `M2-20260920T123901Z`. All six benchmark cases ran. The coarse and medium
cases met the declared force criterion. **Both fine cases did not**: after the planned 40 000
iterations and all three extensions (100 000 iterations; 14 247 s and 8 911 s on a loaded
machine) `sphere_M3_fine` sat at 0.282% peak-to-peak and `sphere_M6_fine` at 0.223%, against a
declared 0.1%, with drifts of 0.0007% and 0.0016% against a declared 0.02%. Gate G4 was
**LIMITED** on that evidence (`gate_assessment_20260921_0057_before_restarts.json`, kept).

**What it was.** Not slow convergence: a bounded oscillation about a fixed mean, so more
iterations could never have cured it. Measured (`<case>_cyclediag/`, force every iteration, the
pressure field every 2 iterations): period 33 iterations at Mach 3 and 40 at Mach 6, i.e. 6.7 and
8 *cell-transit times* (under local time stepping there is no global time, so "flow-through
times" are not defined). The density residual of the fine cases ends ABOVE its starting value,
while the coarse one falls by a factor of 30. The fluctuation is **not** shock jitter on the
axis: the stagnation region is the quietest part of the shock layer (relative pressure
fluctuation 1e-4 and below); it grows along the body to about 1% rms near the supersonic outflow,
in ray-like bands that start at the captured shock, and 90% of its variance is spread over about
40% of the cells. That is the picture of disturbances shed where the captured shock flickers
between cells and then convected downstream; this reading of the map was not separately tested.

**What was NOT done.** The 0.1% limit was not moved, the window was not lengthened, and the
criterion was not re-read as "drift only". The non-converged fine cases were not deleted or
overwritten; they are tabulated, plotted in the warning colour and labelled NOT MET.

**What was done (spec §36, step 6; NR-07's lever one level finer).** Each fine case was continued
from its final solution as a NEW case at max Courant 0.1 and at 0.05 (`sphere_M*_fine_Co0p1`,
`_Co0p05`), in blocks of 5000 iterations, at least two blocks, verdict at the end of the last
block. All four met the unchanged criterion at the end of BOTH blocks:

| case | peak-to-peak, block 1 → block 2 | drift, block 2 | window-mean C_D vs the Co 0.2 case |
|---|---|---|---|
| sphere_M3_fine_Co0p1 | 0.044% → 0.033% | 0.0002% | −0.035% |
| sphere_M3_fine_Co0p05 | 0.018% → 0.011% | 0.0009% | −0.035% |
| sphere_M6_fine_Co0p1 | 0.056% → 0.077% | 0.0015% | −0.026% |
| sphere_M6_fine_Co0p05 | 0.048% → 0.038% | 0.0003% | −0.027% |

(`<case>/restart_blocks.json`, `limit_cycle.csv`.) The amplitude scales with the Courant number
and the clean 33/40-iteration line disappears from the spectrum. The two Courant numbers agree
with each other to 0.001% in C_D, and both differ from the Co 0.2 window mean by about 0.03%:
**the mean of the limit cycle was not the fixed point.** That is small against every tolerance,
but it is a third of the fine–medium difference, and it moved the observed order of C_D from
0.67/0.60 to 1.13/0.88 and the GCI_fine from 0.27%/0.36% to 0.10%/0.19%.

**Caveats, stated rather than hidden.** (1) The restart rule, the two-block minimum and the rule
for which solution is "of record" (the largest Courant number that met the criterion) were all
written AFTER the original results had been seen; the two-block minimum was added while block 1
was running, after an interim look. Each makes the test stricter or is outcome-neutral, but none
is pre-declared. (2) The Mach 6 margin is thin: 0.077% of an allowed 0.1%, and it went UP
between blocks. (3) p0/p∞ and Δ/R come from the last iteration's field, not a window mean; across
the two restarts on the same mesh p0/p∞ differs by 0.4% at Mach 3, as much as between mesh
levels, so its "oscillatory" mesh convergence moved from Mach 3 to Mach 6 when the fine solution
changed. It is judged against the exact Rayleigh-pitot value, never by its GCI. (4) The fine
level now runs at a different Courant number from the coarse and medium levels. For a converged
local-time-stepping solution the steady residual does not contain the time step, so this should
not matter, and the Co 0.1 / 0.05 agreement supports that; it is recorded as A-CFD-15.

**Consequence.** `gate_assessment.json` now reads PASS. A reader who does not accept a restart
rule written after the fact should read the gate as LIMITED; the evidence for both readings is
in the run directory. M3 saw the same signature in 6 of 62 capsule cases (NR-21); the same cure
has NOT been tried there.

**Evidence.** `results/M2/M2-20260920T123901Z/` — `level_candidates.csv`, `limit_cycle.csv`,
`gci.csv` vs `gci_original_fine_cases.csv` and `gci_20260921_0057_before_restarts.csv`,
`sphere_M*_fine*/`, `sphere_M*_fine_cyclediag/`; `reports/figures/M2_force_convergence.png`,
`M2_limit_cycle.png`; `tests/test_cfd_validation_gate.py`.

---

### NR-26 — The pipeline demonstration died in the sphere's domain, and two stages crashed on their own bookkeeping

**The demo.** `capsuledemo_M6_x2` (60° blunted cone, Mach 6, medium mesh) crashed at iteration
8000 with a floating-point exception in `sqrt` (a negative temperature or energy). Its domain was
the one M2 sizes for a sphere, from the Billig stand-off of the NOSE radius. The retry
(`capsuledemo_M6_x2_a1`) reuses M3's capsule machinery unchanged — blunt-cone sizing radius
(0.6 m → 1.0 m), first-order start, on- and off-axis clearance checks, automatic enlargement — and
is USABLE at the first enlarged attempt: criterion met after one extension, outflow supersonic,
p0/p∞ within 0.4% of Rayleigh-pitot. Because that retry changes two things at once, a third case
(`capsuledemo_M6_x2_isolate_startup`) keeps the sphere-sized domain and adds ONLY the first-order
start: **it crashes the same way**, so the domain is the cause and the impulsive start is not.
On the axis the sphere-sized boundary would have left room (the converged stand-off is about half
the distance to it), so the shock must meet the boundary off the axis; that was not observed,
because a crashed case writes no field. Same lesson as NR-20, now reproduced inside M2.

**The bookkeeping.** (1) The demo stage's driver printed columns a failed case does not have and
died with a `KeyError` — a failure that hid a failure. The driver now prints whatever columns
exist. (2) The negative stage had earlier died with `FileExistsError` on a case directory left by
a killed driver. A generated case directory without a `case_result.json` is now set aside as
`<case>__aborted_<time>` (never deleted, never resumed), logged in `aborted_attempts.json`, and
the case re-run; a finished case, including a failed one, is loaded. In this run the full-body
case had in fact finished, and was loaded. (3) A resumed restart's `case_result.json` times only
its last session; the report takes restart wall times from the archived solver logs instead.

**The negative case did its job.** `spherefullbody_M3_x1` ran to 25 000 iterations with all three
extensions and **failed** the criterion on total C_D (afterbody C_D still drifting), as NR-06
says it must. A gate that this case passed would be worthless.

**Evidence.** `results/M2/M2-20260920T123901Z/pipeline_demo.csv`, `capsuledemo_M6_x2*/`,
`negative_cases.csv`, `driver_demo_20260921_0057_crash.log`; `tests/test_cfd_validation_gate.py`.
