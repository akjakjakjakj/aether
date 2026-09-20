# 17. Negative results

*Draft. Does not depend on any pending run.*

Twenty-four entries are kept in full in `docs/negative_results.md`, including the ones that
are embarrassing and the ones whose evidence is a scratch run that no longer exists, labelled
as such. This section reports the ones that changed what the project claims, and it is placed
before the conclusion rather than in an appendix because several of the numbers elsewhere in
this paper cannot be read correctly without it.

They are grouped by what kind of failure they were, because the categories are the useful
part: a model exploited by its own optimiser is a different problem from a tool that produced
a plausible number, and both are different from an organisational failure that would have
produced a complete and well-formatted report.

---

## 17.1 The model had holes, and the optimiser found them

### An unbounded nose-flattening lever

Sutton–Graves gives q″ ∝ 1/√R_n, and the evaluator took the effective nose radius to be the
cap radius. Nose radius enters nothing else at Fidelity 0, so flattening the nose lowered
both objectives and cost nothing. Every one of the 64 designs on the combined feasible front
ended at a bluntness ratio between 1.18 and 1.20 against a cap of 1.2, and 54 of them within
1% of it. Removing the cap put 17 of the resulting 25 front designs beyond it, out to about
1.26, which is simply where the nose cap stops fitting inside the body and the geometry
validator refuses the shape. The cone half-angle, which changes no objective at all at this
fidelity, was dragged to its 70° upper bound on 49 of 64 front designs purely because a wide
cone is the only valid geometry for a nose that flat.

The exploit was anticipated by arithmetic before the run and fenced off with a constraint at
1.2, roughly the Apollo proportion. That was the wrong kind of fix and was recorded as one at
the time: **a constraint at the edge of validity is a fence, not a model**, and "the optimiser
chose a bluntness of 1.2" meant only "the fence is at 1.2".

The size of what the fence was hiding, measured once the corrected model existed:

| Bluntness change | Legacy R_eff = R_n | Corrected |
|---|---|---|
| 1.2 → 1.26 (where geometry refuses) | −2.41% peak flux | **−0.92%** |
| 1.2 → 1.35 (box edge) | −5.72% | **−2.15%** |
| 1.2 → infinitely flat | **−98.90%** | **−21.31%** |

An infinitely flat nose removing 98.9% of the stagnation heat flux is not a small
extrapolation error. It is the wrong answer by construction, because 1/√R_n sends heating to
zero as R_n → ∞ while a real flat-faced body has a perfectly finite stagnation velocity
gradient.

**The repair, and three things it produced.** Two primary sources supply a measured effective
radius, and the substitution of an effective radius into a correlation of this form is the
original authors' rather than this project's. Re-evaluating all 64 front designs under both
models in one process: the effective radius is 0.685 to 0.693 of the cap radius, peak heat
flux rises 20.2 to 20.8%, peak bondline temperature by 6.7 to 9.1 K, and all 64 remain
feasible against the bondline allowable.

1. **All 64 designs landed on a tabulated point**, at K = 0.417 to 0.425 and R_c/R_b = 0.200,
   essentially exactly one of the nine measured bodies. The correction therefore rests on
   interpolating almost nothing. That was luck rather than design, and it is the single best
   thing about the result.
2. **The stated uncertainty got worse, honestly.** The two primaries disagree by about 20% at
   exactly the geometry the front occupies, which is about ±10% on heat flux, larger than the
   heating constant's own ±4%. It is now the dominant stated uncertainty on the heating chain
   and is carried rather than resolved by preferring a source.
3. **The fix moved the exploit rather than removing it.** Under the corrected model a rounder
   corner *raises* stagnation heating, so an optimiser will want a sharp shoulder, worth 1.45%
   of peak flux across the shoulder-ratio range, which is more than bluntness still has to
   offer. A sharp shoulder is exactly where real vehicles are damaged, and this model is
   stagnation-point-only and says nothing about shoulder heating. The fence at 1.2 has been
   replaced by a lower bound on shoulder ratio doing the same job for the same reason. That is
   written down before the next run rather than found in an audit afterwards.

The correction also **voids the screening decision** that froze shoulder ratio on a
total-order sensitivity index of exactly zero. That index is no longer zero, so the design of
experiments must be re-derived rather than reused.

### A heat shield heavier than the vehicle

Drag area grows with D² while vehicle mass was a fixed configuration value, so ballistic
coefficient and both objectives improve monotonically with diameter, and nothing in the model
charged for the structure that a larger diameter implies. Anticipated by arithmetic and then
confirmed: over a 3000-point Latin Hypercube, taking only the two pre-existing constraints,
the non-dominated set was four designs at 3.9 to 4.5 m diameter whose forebody TPS stack alone
weighed **1.29 to 2.81 times the entire vehicle**, and 482 of 1328 evaluable samples violate
mass closure.

A mass-closure constraint at 1.0 was added, which is a logical necessity rather than a design
judgement. **It only excludes the impossible**: the front then sits *on* it, at a shield about
99% of vehicle mass, which no real vehicle could be. A sourced mass budget, or a mass model in
which vehicle mass grows with size, is needed before the large-diameter end of the front means
anything.

This is the same defect as the earlier open item that both two-variable optima sat on the
diameter bound, seen from the other side: widen an arbitrary box and the optimiser walks
straight out of the physically possible.

### "Negligible above 86 km" was false for the second objective

The assumptions file asserted that atmospheric density above 86 km, where the model is a
log-interpolated transcribed table, contributes negligibly. Over the same Latin Hypercube the
share of integrated external heat load accruing there has a **median of 9.5% and a maximum of
27%**; it exceeds 5% in 1105 of 1328 evaluable designs; and among *feasible* designs it is
never below 5.0%, with a median of 10.8%. It rises with diameter, correlation 0.83, so exactly
the low-ballistic-coefficient designs both objectives favour spend longest up there.

Peak heat flux occurs well below 86 km and is unaffected. The **bondline** responds to the
integrated load, so up to a fifth of what drives the second objective is computed from an
interpolated table and from a continuum stagnation-heating correlation applied where the flow
is transitional to rarefied. Nothing was tuned; the share became a per-candidate diagnostic,
and finishing the atmosphere validation row moved from housekeeping to a prerequisite for
trusting bondline differences of a few kelvin between front designs.

---

## 17.2 A metric was proposed, tested against a threshold declared first, and discarded

The specification asked for a project-defined Thermal Penetration Index, a weighted double
integral over TPS depth and time of temperature exceedance above a reference temperature. It
was implemented, verified against closed-form cases, and evaluated over the 140-design
two-dimensional grid against a redundancy criterion written into a configuration file
**before** the run.

It failed that criterion decisively. The index's ranking of designs is **99.94%
reconstructible by rank regression on peak bondline temperature and integrated heat load**;
Spearman ρ against peak bondline temperature alone is **+0.9992**; 91 of 9730 ordered design
pairs, 0.94%, are ranked differently; and an index-minimising optimiser selects the **same
design** as a bondline-minimising one. All 16 declared combinations of reference temperature
and weighting family exceed the threshold together, so it is not an artefact of one setting.

Verdict: **discard**. The implementation and the study are kept, because the metric is not
wrong, it is redundant, and the evidence that it is redundant is worth more than the metric
would have been. No claim of a new aerospace standard is made anywhere, which the
specification explicitly forbids.

**The pre-registered prediction was half wrong, and the wrong half is the interesting one.**
The theory document, written before the run, predicted the outcome and gave a mechanism: that
the integrand would be dominated by the outer millimetre or two, because the surface sits at
thousands of kelvin while the reference temperature is a few hundred.

The outcome was predicted correctly. **The mechanism was not.** The exceedance does peak at
the surface, in the shallowest cell of the mesh for every one of the 140 designs, but it does
not dominate: the outermost 20% of the depth carries only 27.6 to 40.6% of the integral,
against the 20% a uniform profile would give. It declines smoothly by a factor of a few across
15 mm. It is not a surface spike.

The real mechanism is **shape invariance**. Normalised to unit length, the exceedance profiles
of all 140 designs have a minimum pairwise cosine similarity of **0.9366** and a mean of
0.9891. Every design produces very nearly the same depth profile, scaled by a different
factor. Any weighted depth integral of a shape-invariant profile is that scale factor and
nothing more, which is why all 16 weighting choices fail together rather than some of them
rescuing the metric. **A metric cannot separate designs along a dimension in which the designs
do not differ.**

The theory document's prediction section is left exactly as written, with the addendum beside
it, because editing a pre-registration after seeing the answer destroys the only thing it was
for.

That distinction changes what future work should try. Had the predicted mechanism been the
true one, a more aggressive depth weighting would have been worth attempting. Because the
profiles are shape-invariant on this stack, the thing that would have to change is the
**stack**: an interior bondline behind a second insulator, a temperature-dependent
conductivity, or a charring layer. That is a prediction about future work, not a defence of
the metric.

---

## 17.3 Tools that produced a plausible number instead of an error

These are grouped together because they share a property: none of them failed loudly, and
each was caught by a different mechanism.

**The Pareto front implementation was wrong, and a figure caught it.** The first version
returned all 21 feasible designs as non-dominated and the plotted front zigzagged. The
dominance test had inverted control flow: on finding a point that dominated candidate *i* it
continued, keeping *i*, instead of marking it dominated. A two-objective Pareto front is
necessarily monotone, so a zigzag is geometrically impossible and **the plot falsified the
code**. The test suite had not caught it because no test asserted monotonicity. This is the
clearest example in the project of a figure functioning as a test, and it is why the plotting
standard requires real axes and real units; a prettier, less quantitative chart would have
hidden it.

**A variance estimator produced impossible confidence intervals.** The first sensitivity
analysis reported first-order confidence intervals on the bondline as wide as [−0.41, 1.15].
A variance share cannot be negative or exceed one. The Saltelli first-order estimator
multiplies by f(B), and for an output with a roughly 400 K mean and a few tens of kelvin of
spread its variance is dominated by the mean. The indices are invariant to a constant shift,
so the output is now centred before estimation; the same 6144 evaluations, re-analysed, gave
[0.30, 0.45] on the leading variable. Total-order indices are differences and were unaffected,
so **no screening decision changed**. The estimator is now pinned against a test function with
analytically known indices.

**A configuration value silently became a string.** PyYAML follows YAML 1.1, in which a float
requires a signed exponent, so `2.5e6` parses as text. The hypervolume code coerced it through
numpy and computed correctly, and the run then died in a figure caption after 21 000
evaluations. Nothing was lost, because every candidate is appended to the log as it is
evaluated and the summary is written before any figure, and a report-only rebuild recovered
everything. Both of these are the kind of fault that produces a plausible number rather than
an error, and the second is the argument for an append-only candidate log.

**A surrogate classifier returned NaN and an optimiser quietly stopped optimising.** A
Gaussian process classifier's Laplace approximation produced a negative latent variance once
the search clustered near the front, so its predicted probabilities were NaN for the whole
candidate pool. NaN times an acquisition value is NaN, the argmax of an all-NaN acquisition is
not finite, and the loop's guard fell through to space-filling samples: the prediction log
held 20 records for 180 model-driven evaluations, and the hypervolume curve went flat from 50
evaluations on. **The hypervolume did not show the fault**, because on this problem the front
is found early and a broken optimiser and a working one score alike at 200 evaluations. It was
visible only in *where the budget went*, which is why the ablation report carries a budget-use
figure and a no-physics share per method.

A second fault in the same optimiser: after convergence, expected improvement inside the
feasible region is essentially zero for most of the pool, while in the invalid region the
objective models revert to their prior mean with a large variance, so expected improvement
there is huge and even a 1% probability of feasibility wins the product. The optimiser spent
60% of its budget on capsules that cannot exist, and its classifier was correctly telling it
so. A probability floor was added.

**A convex hull membership test depended on which triangulation it got.** After an arm in a
development run absorbed one new training point, 6 of its next 20 designs were rejected as
extrapolations, while the arm that bought nothing had none in 100 evaluations. A convex hull
cannot shrink when a point is added. The rejected designs all had a variable frozen at a value
that is also the top of the surface's input range, written as a length and divided back to
0.10000000000000002, a unit coordinate of 1 + 2.2×10⁻¹⁶, sitting exactly **on** a hull facet.
At the default tolerance, membership was decided by triangulation luck: 48 of 48 query points
inside the 56-point hull, 1 of 48 inside the 57-point hull, 48 of 48 inside both at a
tolerance of 1e-12 or larger.

The consequence had it gone unnoticed is what makes it worth reporting. This was the
extrapolation guard, not adaptive-fidelity code, and in an adaptive-fidelity study it would
have been metric gaming in reverse: **promotion punished by phantom hull rejections**, biasing
the study against every arm that buys CFD, in a study whose entire question is whether buying
CFD selectively pays. It was found because an aborted development run's candidate log was read
rather than discarded.

---

## 17.4 The failure that was organisational

A two-hour matched-budget study was launched as a detached job. While it ran, a concurrent
work-stream changed the evaluator's physics. The runner had snapshotted its *configuration* at
launch, so a configuration edit could not have reached it, but worker processes import the
package when they are spawned, so an edit to the *source* can split one candidate log between
two physics models with nothing in the log to say which row is which. The run's header said
only "dirty tree". It was killed part-way through; no summary was ever written and no number
from it was inspected. The directory is kept with a note saying it must not be analysed.

**"Config snapshot plus git commit plus dirty flag" is not provenance for a long run in a
repository that several people or processes edit at once.** The dirty flag is read once, at
launch, and says nothing about what changes afterwards. A matched-budget comparison whose
methods were evaluated by different physics is not a comparison.

Three changes followed. Every long-running study now hashes each source file in the physics
package at launch, records the hash in the summary and the report header, and re-checks it
before and after every method-and-seed pair and after every logged batch; on a mismatch it
logs the batch already paid for, writes an abort marker and stops. A study refuses to start if
the screening it would take its active variables from was made on a different design space.
And **the report generator no longer contains pre-written findings**: its first version stated
as prose that every front leans on two particular constraints, which was true of one heating
model and false of the one that replaced it an hour later. Interpretive sentences are now
emitted by code from the audit tables, or not at all.

The guard then proved itself twice by aborting two development runs correctly, because a
different work-stream was editing a different sub-package. That produced a further refinement:
a sub-package can be excluded from the hash, but the guard refuses to continue if an excluded
sub-package has actually been imported into the process, so an exclusion cannot hide a real
dependency, and exclusions are rejected outright in study mode.

**This failure is kept prominently because it was organisational rather than numerical, and
because it would have produced a complete, plausible, well-formatted report.**

---

## 17.5 The experiment's traps, found before anything was built

The whole calibration-and-validation chain for the physical experiment was exercised on
synthetic data generated by this project's own solver with known parameters, before a coupon
was printed. Four traps surfaced, each of which would have been invisible in the real
experiment, because the calibration would have fitted beautifully and the parameters would
still have been wrong.

1. **Contact resistance is weakly identifiable under a prescribed flux.** Fitting all five
   parameters freely, it came back 186% to 531% wrong and dragged conductivity and specific
   heat 5 to 12% low with it. The cause is structural: with the flux prescribed, contact
   resistance does not change how much heat enters the solid at all, only the temperature of
   the flux-application plane. A least-squares fit given a parameter that barely affects the
   residual will use it to absorb everything else. It is now measured in a dedicated
   steady-state run and held fixed during calibration.
2. **A short calibration step leaves conductivity and specific heat degenerate.** With a step
   of about one diffusion time, both came back about 12% low while their *ratio*, the
   diffusivity, was recovered to 0.4%. A transient shorter than the diffusion time only ever
   sees diffusivity; separating the two needs the steady depth gradient dT/dx = q″/k, which
   needs the step held long enough to establish it. The protocol now requires two to three
   diffusion times, about an hour for a 10 mm coupon, which is the single largest time cost in
   the procedure.
3. **Peak metrics are estimator-dependent, and the obvious fix does not work.** The maximum of
   a noisy record is biased high by roughly σ√(2 ln N), over a kelvin at realistic sensor
   noise, in the direction that makes a *correct* model look as though it under-predicts the
   peak. Averaging the near-peak plateau barely helped, leaving +1.36 K of bias, because the
   plateau window is *selected by the noisy maximum* and the selection bias survives the
   average. Smoothing the record first, applied identically to the prediction so that any
   rounding cancels in the difference, cut it to +0.08 K.
4. **The "seeded" synthetic data was not reproducible between processes.** The per-run seed
   used Python's string hash, which is salted per interpreter, so the twin generated different
   data in every process while looking deterministic within one. It surfaced only because trap
   3's marginal assertion passed on one salt and failed on the next: a test that should have
   been catching a bug was itself the bug. A fixture that claims to be seeded and is not turns
   every downstream test into an intermittent one, which is worse than having no fixture.

With the first two fixes in place the synthetic chain recovers conductivity, specific heat and
both loss coefficients to better than 0.5%, fitting at a coarser mesh than the one that
generated the data, and predicts an unseen pulse to better than 0.1 K against the noise-free
truth. A test asserts the weak identifiability itself rather than the fix, so the finding
cannot be silently forgotten.

---

## 17.6 A validation exercise that changed nothing

Three long-standing citations were opened for the first time. The expectation, written down
beforehand, was that at least one of the numbers would be wrong and would have to change.

**Not one number changed.** The baseline reproduces bit-identically before and after.

- The heating constant re-derives to +0.39% of the value in use, and was deliberately not
  changed, because each substitution needed to reach the equation's familiar form carries more
  error than that and applying all of them gives −4.01% in the opposite direction. Adopting
  the fresh number would have shifted every heat flux in the repository for worse
  justification while looking like the conscientious outcome of a validation exercise.
- The upper-atmosphere table, suspected of having been transcribed from a different
  atmospheric model entirely, agrees with the primary to every printed digit at all five
  altitudes checked.
- The trajectory integrator reproduces a published closed-form-versus-numerical disagreement
  to within 0.92 percentage points.

A validation exercise that ends in "the value was right" is easy to under-value, and the
pressure to adopt the freshly derived constant because it *felt* like the more rigorous number
was real. The opposite case appeared in the same pass: a deceleration limit nobody had
questioned turns out to correspond to no document at all, and its defensible replacement would
empty the feasible region of the headline study. That is now visible instead of buried.

---

## 17.7 Why these are kept

Two reasons, and they are different.

The first is that several numbers elsewhere in this paper cannot be read correctly without
them. The optimisation fronts are superseded because of §17.1. The absence of a thermal
penetration index from the objective list is explained by §17.2. The absence of a
matched-budget optimiser comparison is explained by §17.4.

The second is that **a repository which only shows what worked is a marketing document.**
Every entry here is a place where a plausible, well-formatted, entirely wrong answer was
available, and in most cases the mechanism that caught it was not the test suite. It was a
figure with real axes, a confidence interval that fell outside its own possible range, a
budget that went somewhere unexpected, or a guard that fired when it was inconvenient.
