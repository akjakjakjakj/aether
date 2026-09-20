# Final paper — outline and claim budget

Spec §40. Source structure for a 15–25 page paper. Twenty required sections, in the
specification's order.

**This file is not the paper.** For each section it records three things:

- **Claims allowed** — exactly what that section may assert, and the evidence file behind
  each. A claim not on the list does not go in the section. This is a budget, not a summary.
- **Figures** — which figures belong there, by file.
- **Limitations that must appear** — the caveats that travel with the claims. A section that
  states its claims without them is not a shorter version of the section; it is a different
  and less honest one.

Sections that do **not** depend on a pending run are drafted in
[`sections/`](sections/). Sections that do are specified here and left undrafted, because
drafting a results section before the result exists is how a result gets written to fit the
prose.

---

## Status of the underlying work, as of this outline

| Study | State | What that means for the paper |
|---|---|---|
| M1 / M1b burn-vs-bake | **Final** | Drafted. Legacy heating model, and for these geometries that label costs nothing (see §7) |
| §44 TPI study | **Final**, verdict DISCARD | Drafted inside Negative Results |
| G1A, G1A′, G1B, G2, G3, G3b, G-GEO, G-GEO2 | **Final** | Drafted |
| M2 CFD validation (gate G4) | `IN_PROGRESS` | Specified, not drafted. Mesh independence incomplete, no published benchmark compared |
| M3 drag surface, gate G5 | `LIMITED`, PROVISIONAL, registered and off | Specified, not drafted |
| M4 DOE and Pareto | Superseded; screening **void** | Specified, not drafted. The fronts on disk were computed under the legacy heating model behind a bluntness cap since removed |
| M5 AI ablation | Harness built, **no study run** | Specified, not drafted |
| M6 adaptive fidelity | Harness built, **no study run** | Specified, not drafted |
| M7 uncertainty and robust | Harness built, **no study run** | Specified, not drafted |
| M8 thermal coupon | Support package built, **no measurement** | Specified, not drafted |

---

## Global rules for the whole paper

1. **§37 language.** "The model predicts", "within tested assumptions", "candidate",
   "simulation suggests", "validated against X within Y%". Never "flight ready", "solves
   re-entry", "proves optimal", "eliminates heating".
2. **No number is typed by hand.** Every figure in the paper is read from a result file, and
   the file is named in the caption or in a table footnote.
3. **Fidelity is labelled on every result.** A reader must never have to work out whether a
   number came from a constant drag coefficient or from the CFD surface.
4. **`LIMITED` is never written as `PASS`**, in prose or in a table.
5. **Citations are tiered.** ✅ T1 opened and read; 🟡 T2 reputable secondary; a claim with no
   verified source is not made. The tier appears in the reference list, not in the body.
6. **No claim about admissions value appears anywhere in this paper.** Spec §51.
7. **Negative results are a section, not an appendix**, and they are referenced from the
   sections whose numbers they explain.

---

## 1. Abstract

**Drafted:** `docs/submission_package/abstract.md` (the same text serves both).

**Claims allowed.** The question; the method in one clause; the M1/M1b result; one sentence
of the Fidelity-1 result `[PENDING FINAL RUN]`; the §37 closing sentence.

**Must appear.** "Model predictions within a documented set of assumptions; no flight or
experimental validation is claimed."

**Must not appear.** Spearman ρ, any margin ratio, any mention of AI in the first sentence.

---

## 2. Introduction

**Drafted:** [`sections/01_introduction.md`](sections/01_introduction.md).

**Claims allowed.**

| Claim | Evidence |
|---|---|
| TPS is conventionally sized against peak heat flux for material selection and against integrated heat load for thickness | NASA TFAWS 2012 Aerothermodynamics Course, quoted in `docs/theory/tpi.md` §2.1 (🟡 T2, opened and read) |
| The accepted in-depth design criterion is a *maximum* at a *single plane*, the bondline | same source, quoted in `docs/theory/tpi.md` §2.2 |
| The entry-angle trade between peak heat rate and total heat load is a known trade | same source, verbatim: "The selection of γ becomes a trade between peak heat rate (TPS material selection), and total heat load (TPS thickness and mass)" |
| The bondline allowable is set by the structural substrate, and flown vehicles differ | `docs/validation/sourcing_report.md` §3 (Apollo 589 K, Shuttle 450 K, Orion 533 K, all ✅ T1) |
| What is *not* established is whether a joint optimisation finds designs a sequential one misses | this is the gap the paper addresses; stated as a gap, not as a claim of novelty |

**Figures.** None, or `reports/figures/M1_temperature_field.png` if an orienting figure is
wanted.

**Limitations that must appear.** That the framing came from a project specification rather
than from an observation made in this work (`docs/research_story.md`, first entry). The
introduction is where that belongs, not a footnote.

---

## 3. Related Work

**Drafted:** [`sections/02_related_work.md`](sections/02_related_work.md).

**Claims allowed.** Only what a verified source says. Five threads: stagnation-point heating
correlations; blunt-body stagnation velocity gradients; ballistic entry trajectory solutions;
TPS sizing criteria and bondline allowables; cumulative thermal-exposure metrics.

**Must appear.** That no named prior metric of the TPI's exact shape was found **in the
sources searched**, stated as a negative search result and not as a novelty claim
(`docs/theory/tpi.md` §3). Spec §44 forbids claiming TPI as a new aerospace standard.

**Must not appear.** Any citation not verified in `docs/validation/sourcing_report.md` or
`docs/theory/*`, or opened during drafting. Four method citations used by the code have **no
recorded provenance** and are flagged in the draft rather than cited silently.

---

## 4. Hypotheses

**Drafted:** [`sections/03_hypotheses.md`](sections/03_hypotheses.md).

**Claims allowed.** H0, H1, H2 exactly as frozen in `CLAUDE.md` §4; what each would take to
falsify; which are currently addressed and which are not.

**Must appear.** That H2 has **not been tested**, and that its pre-declared criterion
includes a `NOT_TESTABLE` verdict if the no-CFD arm reaches the target (A-AF-9). That H0's
M1 evidence is a statement about a one-parameter family.

---

## 5. Methods

Two parts. The reduced-order half is drafted; the Fidelity-1 half waits on §8.

**Drafted (reduced order):**
[`sections/04_methods_reduced_order.md`](sections/04_methods_reduced_order.md).

**Claims allowed (reduced order).**

| Claim | Evidence |
|---|---|
| Atmosphere: USSA-76 computed exactly 0–86 km; transcribed table log-interpolated 86–150 km; refuses above 150 km | `ASSUMPTIONS.md` A-ATM-1..3 |
| Trajectory: point-mass 3-DOF planar, non-rotating spherical Earth, inverse-square gravity | A-TRAJ-1..5 |
| Heating: Sutton–Graves with an effective nose radius from measured stagnation velocity gradients | A-HEAT-1..4, A-GEO-3, A-GEO-3a |
| TPS: 1-D transient multilayer conduction, finite volume, backward Euler, harmonic interface conductivity, Newton-linearised radiating surface, post-entry soak-out | A-TPS-1..9 |
| One canonical evaluator; no study bypasses it | spec §19; gate G5 fingerprint evidence |

**Claims allowed (Fidelity 1) — not drafted.** The CFD model and the drag surface. All of it
is conditional on §8.

**Limitations that must appear.** A-HEAT-4 (stagnation point only, silent about the shoulder
and afterbody); A-TPS-7 (material properties are placeholders, not a qualified material);
A-TRAJ-2 (constant C_D at Fidelity 0); A-ATM-2 with NR-14 (the "negligible above 86 km"
claim is false for the bondline objective).

---

## 6. Verification and Validation

**Drafted (G1–G3 only):**
[`sections/05_verification_validation_G1_G3.md`](sections/05_verification_validation_G1_G3.md).

**Claims allowed (drafted part).**

| Claim | Evidence |
|---|---|
| G1A `PASS`: atmosphere 0–86 km within 0.01% on T and 0.1% on p against published layer-base values | `VALIDATION_MATRIX.md` G1A |
| G1A′ split verdict: exact agreement to every printed digit at 90/100/110/120/150 km against a primary copy; `LIMITED` for the 86/95/130 km rows, the pressure column, and the interpolation between rows | G1A′; `ASSUMPTIONS.md` A-ATM-2 |
| G1B `PASS`: nine published figures reproduced to within 0.92 percentage points against a 1.0-point allowance | G1B; `tests/test_trajectory_allen_eggers.py` |
| G2 `PASS`: constant re-derived from the primary to 0.39%, against the primary's own 3.3% stated error, and deliberately not changed | G2; `docs/theory/sutton_graves_constant.md`; NR-12 |
| G3 `PASS`: 0.002% against the analytical solution, energy residual ~1e-14, grid and timestep convergence demonstrated | G3; `tests/test_tps.py` |
| G-GEO2 `PASS` implementation / `LIMITED` physics for the effective-nose-radius model | G-GEO2 |

**Figures.** A validation-matrix table rendered as a figure; the Allen–Eggers comparison
table; the conduction benchmark residual plot if one exists.

**Limitations that must appear, verbatim in substance.** The closing argument of
`VALIDATION_MATRIX.md`: each 2026-09-20 upgrade is narrower than its row title. G1A′
validates a *transcription* at five altitudes. G1B validates the *integration* under an
exponential atmosphere and constant gravity, not the production configuration. G2 validates
the *constant*, not the correlation, and G2′ where catalycity alone is worth about a factor
of two is untouched.

**Not drafted.** G4 and G5, which are §8's business.

---

## 7. Burn-vs-Bake Result

**Drafted:** [`sections/06_burn_vs_bake.md`](sections/06_burn_vs_bake.md).

**Claims allowed.**

| Claim | Evidence |
|---|---|
| Over the tested entry-angle range both metrics are strictly monotone with opposite signs; no interior angle improves both | `reports/milestones/M1_burn_vs_bake.md` |
| Endpoint pair: −38.3% peak flux, +114.1 K bondline | same |
| 818 counterexample pairs of 1640, thresholds declared in advance | `reports/milestones/M1_signature_counterexample.md` |
| With geometry frozen, 0 of 41 candidates feasible | M1 report §"The feasibility squeeze" |
| Opening the diameter axis recovers 21 of 140; joint optimum runs 32.5 K cooler at +19.6% peak flux | M1 report §M1b |
| The mechanism is a diffusive timescale comparable to the entry duration | M1 §Mechanism; NR-03 |

**Figures.** `M1_anticorrelation`, `M1_trade_space`, `M1_mechanism`,
`M1_integrated_vs_bondline`, `M1b_feasible_region`, `M1b_optimiser_comparison`.

**Limitations that must appear.**

- Spearman ρ = −1.000 is close to tautological over a one-parameter sweep and is **not**
  independent evidence.
- Margin ratios are not quoted; the absolute 32.5 K is, because the ratio swings 37.5× to
  1.6× with the allowable.
- Both M1b optima sit on the diameter bound, so the bound rather than the physics is
  selecting them.
- **Legacy heating model, and precisely what that does and does not mean.** M1 and M1b were
  computed with `effective_nose_radius_m = nose_radius_m`, which was later found wrong for
  shallow spherical caps (NR-15) and replaced. For M1 and M1b the replacement changes
  nothing, because both use a hemisphere-nosed body (R_n = D/2, hence K = R_b/R_n = 1) where
  the two models agree identically (A-GEO-3). The numbers are unaffected. The M4 fronts,
  which used shallow caps, move by 20.2–20.8% in peak flux, and that is why they are
  superseded.
- The 12 g deceleration limit corresponds to no documented sustained-g curve, and it decides
  the feasible region.

---

## 8. CFD

**Not drafted.** Gate G4 is `IN_PROGRESS`.

**Claims allowed once G4 is PASS.** The model (`rhoCentralFoam`, axisymmetric Euler,
calorically perfect air, forebody-only domain); force convergence against the declared
criterion; mesh independence with a GCI; a published blunt-body comparison; the model-form
limits document as the §17 condition-4 deliverable.

**Claims that remain forbidden regardless of G4.** Heating of any kind; shock-layer
temperature, density or species as flight quantities; flight shock stand-off; total drag
including the base as a CFD result; lift, moments or stability; subsonic and transonic
flight; rarefied flow. `docs/validation/M2_model_form_limits.md` is the authority.

**Figures.** `M2_force_convergence`, `M2_residuals`, `M2_benchmark`, plus a GCI table when
one exists.

**Limitations that must appear.** OpenFOAM v2512, not the v2606 the specification names
(A-CFD-6). The residual plateaus about a decade down and force convergence is the criterion
of record. The forebody-only domain and the consequence that base drag is an assumption with
a band, not a computation (NR-06, A-CFD-5).

---

## 9. Coupled Model

**Not drafted.** Gate G5 is `LIMITED` and cannot be better than the PROVISIONAL surface it
stands on.

**Claims allowed.** The evaluator's structure and its determinism and provenance guarantees
(identical result fingerprints across repeat runs; recorded surface hash, source run, mesh
level, gate status at build and at evaluation, extrapolation flag, and the share of heat load
and flight time outside the CFD Mach range). The measured constant-versus-surface comparison.
The finding that shape acquires aerodynamic consequence only once the drag model can see it.

**Figures.** `M3_design_coverage`, `M3_cd_vs_mach`, `M3_surface_cv`,
`M3_constant_vs_surface`, `M3_shape_sweep`, `M3_base_drag_fraction`, `M3_capsule_family`.

**Limitations that must appear.** PROVISIONAL, coarse mesh, discretisation band pending the
GCI; 55% of the baseline's heat load above Mach 20 on a held value with a measured 1.80%
change between Mach 10 and 20; GP error bars inflated by a measured factor of 1.65; failed
CFD cases shrink the usable hull (NR-21); base drag bounded rather than predicted.

---

## 10. Optimization

**Not drafted.** The M4 fronts on disk are superseded and the screening is void.

**Claims allowed after `make doe && make optimize`.** The screening decision and why each
variable was frozen or kept; the fronts per method with seed spread; the knee design against
the peak-flux-only optimum; the metric-gaming audit and its counterfactual table.

**Figures.** `M4_doe_oat`, `M4_doe_lhs`, `M4_doe_sobol`, `M4_hypervolume`,
`M4_pareto_front`, `M4_front_variables`, all regenerated.

**Limitations that must appear.** Hypervolume depends on a reference point fixed before any
run (A-OPT-4) whose bondline axis inherits the allowable. A design stopped by a box bound is
an optimum of the box. Screening is a property of the drag model it was made on. The
scalarised-DE baseline's result is about that declared configuration under that budget, not
about differential evolution in general. Hypervolume differences with overlapping seed ranges
mean *no measured difference*.

---

## 11. AI / Surrogate Comparison

**Not drafted. `[PENDING FINAL RUN]` — no study exists.**

**Claims allowed.** Only what A-AI-7's pre-declared criterion returns: "AI helped", "AI
hurt", or "no measured difference". Plus the budget accounting, the schema-rejection count,
the no-physics share per method, and the qualitative audit of what the agent actually
proposed.

**Must appear.** What the agent sees and does not see (A-AI-5); the asymmetry that the LLM
reads validator failure messages while numeric optimisers see only a fixed violation
(A-AI-2); that n = 5 seeds means only near-complete separation can reject, so a null is weak
evidence of equivalence (A-AI-7); that variable names carry aerospace meaning so prior
knowledge cannot be separated from reasoning-from-data.

**Must appear even though it is inconvenient.** NR-17: two faults in the Bayesian optimiser
were fixed after looking at one seed of one method, before the study ran, and that seed was
removed from the study seeds. NR-18: an earlier run was aborted and must not be analysed.

---

## 12. Adaptive Fidelity

**Not drafted. `[PENDING FINAL RUN]` — no study exists.**

**Claims allowed.** Only what A-AF-9 returns: `SUPPORTED`, `CONTRADICTED`,
`NO_MEASURED_DIFFERENCE`, `NOT_SUPPORTED` or `NOT_TESTABLE`. The last is a real outcome: if
the no-CFD arm reaches the target, H2 is not testable on this problem and that is what gets
written.

**Must appear.** Scoring is on pooled truth, not on an arm's own possibly flattering surface
(A-AF-7). CFD calls are spent *while* the search runs, so "calls to reach the target"
conflates CFD with search progress, and the figure shows both axes. Eight calls per arm-seed
is coarse. NR-23, the hull-tolerance bug, which would have punished promotion.

---

## 13. Uncertainty

**Not drafted. `[PENDING FINAL RUN]` — no study exists.**

**Claims allowed.** The p-box as the primary result, with aleatory and epistemic carried
separately (A-UQ-1); the Sobol' attribution over uncertain inputs; chance-constraint
feasibility; the nominal-versus-robust comparison; the shortcut verification result, read
*first*.

**Must appear.** That the reported uncertainty is a **lower bound**, because G2′ (catalycity,
hot wall, radiation) has no distribution attached and catalycity alone is worth about a
factor of two. That 7 of 9 active inputs are engineering judgment. That the chance
constraint's probability resolution is 1/S, so α = 0.05 at S = 32 means at most one violating
draw in 32. That "0 of n violated" is reported with its confidence bound, never as zero.

---

## 14. Physical Experiment

**Not drafted. `[PENDING FINAL RUN]` — no coupon has been printed and no measurement
exists.**

**Claims allowed now.** The design of the experiment; the calibrate → freeze → predict →
archive → measure → compare chain; the four traps the synthetic twin found before anything
was built (NR-11); the parameter-recovery performance against synthetic data, stated as a
check on the software and nothing else.

**Claims allowed after the experiment.** RMSE, peak error, time-to-peak error, residuals and
uncertainty coverage against a tolerance declared **before** the runs.

**Must appear.** That the experiment is a thermal-transient validation experiment, not a
re-entry simulator. That contact resistance is weakly identifiable under a prescribed flux
and is therefore measured separately and fixed. That peak metrics are estimator-dependent and
which estimator is quoted.

---

## 15. Discussion

**Not drafted.** Depends on the results.

**Claims allowed.** What the results mean for the design question; where the mechanism is
robust and where only the direction survives; what would change the answer; what the
epistemic attribution says about which measurement to buy next.

**Must appear.** The separation the whole paper turns on: the *mechanism* is verified, the
*magnitudes* are model-dependent. And the honest statement that the single highest-value
follow-up on the dominant heating uncertainty already has a name and a DOI and is paywalled.

---

## 16. Limitations

**Not drafted.** Assembled from `ASSUMPTIONS.md` at the end, so it cannot drift from it.

**Must contain at minimum.** Fidelity of every reported number; gate statuses including every
`LIMITED` row and what specifically is missing from each; the unsourced constraint limits and
the open deceleration-limit decision with its measured effect on the feasible region;
placeholder material properties; stagnation-point-only heating; no ablation; no angle of
attack; no experiment; the effective-nose-radius model's ±10% from two disagreeing primaries;
the project's own interpolation between nine data points; and that most of the code was
AI-generated with some components not yet reviewed.

---

## 17. Negative Results

**Drafted:** [`sections/07_negative_results.md`](sections/07_negative_results.md).

**Claims allowed.** Any of the 24 entries in `docs/negative_results.md`, quoted with their
measured numbers.

**Must appear.** The three that carry the most weight: NR-15 (the optimiser exploiting the
heating model, and the fix moving the exploit), NR-12 (the constant deliberately not
changed), NR-10 (a metric discarded against a pre-declared criterion, with the pre-registered
mechanism half wrong). Plus NR-18 as the process failure and NR-04 as the figure that
functioned as a test.

---

## 18. Conclusion

**Not drafted.** Depends on the results.

**Claims allowed.** A restatement of what was established and at what fidelity; H0, H1 and
H2's status against their own criteria; the one sentence a reader should leave with.

**Must not appear.** Any claim beyond the fidelity actually reached; any recommendation for a
real vehicle; any statement that the work "proves" anything.

---

## 19. Reproducibility

**Drafted (AI-usage part only):**
[`sections/08_reproducibility_ai_usage.md`](sections/08_reproducibility_ai_usage.md).

**Claims allowed (drafted part).** What was AI-generated and what was reviewed; which defects
AI-generated code introduced; what AI did not contribute; how a language-model-in-the-loop
study is made reproducible without model access.

**Claims allowed (remaining part).** Environment, commands, runtimes, determinism guarantees,
provenance of every result, the archive location. Source:
`docs/submission_package/reproducibility_links.md` and `REPRODUCIBILITY.md`.

**Must appear.** That reports are generated and hand-editing one is overwritten. That a
replay reproduces the recorded run, not the model. That aborted and rejected runs are shipped
with the repository.

---

## 20. References

**Drafted with the Related Work section**, tiered.

**Rule.** Every entry carries an NTRS ID, a DOI or a URL. Every entry is one that was opened
and read, or is explicitly marked as secondary. Four method citations used by the code have
no recorded provenance and are listed separately as **to be verified before submission**
rather than cited as if they had been checked.

---

## Assembly checklist

- [ ] Every `[PENDING FINAL RUN]` filled or the section removed with a stated reason.
- [ ] Every number traced to a result file named in the text.
- [ ] Every figure regenerated from the final runs, not carried over.
- [ ] Fidelity labelled on every result.
- [ ] No `LIMITED` row described as passed.
- [ ] Limitations section reconciled line by line against `ASSUMPTIONS.md`.
- [ ] Reference list reconciled against `docs/validation/sourcing_report.md`; the four
      unverified method citations resolved.
- [ ] Tauber (NASA TP-2914) provenance discrepancy resolved (see
      `sections/02_related_work.md`).
- [ ] The 27-versus-41 sweep-size discrepancy between `REPRODUCIBILITY.md` and the M1 report
      resolved.
- [ ] AI disclosure present and at full size.
- [ ] Working tree clean at the cited commit.
