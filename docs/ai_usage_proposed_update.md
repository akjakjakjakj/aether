# Proposed update to AI_USAGE.md

**This is a proposal, not an edit.** `AI_USAGE.md` has not been touched. The coordinator
merges what is below, or some of it, after checking it.

Scope: everything added on 2026-09-20, from the ten commits of that day and the seven
engineering-notebook entries beside them. The existing file's table stops at "Current state
(2026-09-02, after M1)", so none of this is in it.

**Every new row is marked `review pending`.** That is not a formality and it is not
pessimism: the student has not read any of this code line by line. Marking rows reviewed
before that has happened would break the one rule in `AI_USAGE.md` that makes the rest of it
worth anything.

Size of what is proposed: the package went from roughly 1500 lines of Python at M1 to
**21 150 lines across 13 sub-packages**, plus **5908 lines of tests** and **2564 lines** of
experiment analysis code. Almost all of the difference was added in one day, and almost none
of it has been read.

---

## Proposed new table section

Append to `AI_USAGE.md` after the existing "Current state (2026-09-02, after M1)" table,
under a new heading. The format matches the existing three-column table.

### Current state (2026-09-20, after M2–M7 harnesses)

| Item | Category | Note |
|---|---|---|
| **Parametric capsule geometry** (`geometry/capsule.py`, 619 lines; commit `046e0a1`) | AI-generated, **review pending** | Sphere-cone-torus-cone-flat-base forebody, validity bounds, exact closed-form volumes with a quadratured torus term, deterministic binary STL. Watertightness and outward normals are verified by reading the written file back, not inferred from construction. The student must be able to say why `validate()` rejects a cone half-angle of exactly 0, and why a pure spherical segment is represented as a limiting case rather than a shape flag (A-GEO-1, A-GEO-2). |
| **Effective nose radius from stagnation velocity gradients** (`geometry/stagnation_gradient.py`, 282 lines; commit `e3c48cb`) | AI-generated, **review pending** | The single most consequential physics change of the day: it raises peak heat flux on the M4 front by 20.2–20.8%. Interpolates nine measured values from NASA TN D-5121 Table I with an exact hemisphere anchor. **The interpolation is this project's own construction, not a published fit** (A-GEO-3a). Highest reading priority of anything in this table. |
| **Effective-nose-radius model adopted over the cap radius** (`configs/design_space.yaml`) | AI-proposed, **student-approved pending** | This is a *physics* decision, not a code decision, and it was made under the one clause of the frozen scope that permits new physics: resolving a demonstrated validation failure (NR-15). It should be explicitly approved, not inherited. |
| **Sutton–Graves constant re-derived and deliberately NOT changed** (`docs/theory/sutton_graves_constant.md`; commits `c238735`, `4de6054`) | AI-proposed decision, **student-approved pending** | The derivation lands +0.39% from the code's value; adopting it would have moved every heat flux in the repository for worse justification (NR-12). A test pins the value so the decision cannot be quietly reversed. The student should be able to reproduce the three substitution errors and their signs. |
| **Allen–Eggers closed form and the exponential atmosphere** (`trajectory/allen_eggers.py`, `atmosphere/exponential.py`; commit `4de6054`) | AI-generated, **review pending** | Implements a published closed form to validate the integrator against a *published disagreement* rather than against agreement. `ExponentialAtmosphere` is a validation instrument, not a model of the air (A-ATM-5); no config selects it. |
| **Gravity and planet-radius override hooks** (`trajectory/entry3dof.py`; commit `4de6054`) | AI-proposed, **student-approved pending** | Added solely so a reference case computed with constant gravity can be matched. Both default to `None`. `test_production_default_is_unchanged_by_the_validation_hooks` asserts bit-identical default behaviour (A-TRAJ-5). |
| **USSA-76 upper-table primary check** (`tests/test_atmosphere.py`; commit `4de6054`) | AI-generated, student-reviewed **pending** | Five altitudes diffed against a primary copy; exact agreement to every printed digit; nothing changed. A second test fails if the three unchecked rows are ever forgotten. |
| **TPS bench boundary terms** (`tps/conduction1d.py`; commit `3b44563`) | AI-generated, **review pending** | Front- and back-face convective loss, back-face re-radiation, series contact resistance, all defaulting to zero, which reproduces the entry model bit-identically (A-TPS-8, gate G3b). |
| **Thermal-coupon support package** (`experiments/thermal_coupon/`, 2564 lines of analysis code; commit `3b44563`) | AI-generated, **review pending** | Printable holder, sensor drawing, data schema, protocol, calibration, comparison, synthetic twin, archived blind prediction. |
| **Four coupon-protocol decisions** (fix contact resistance from a dedicated steady-state run; hold the calibration step 2–3 diffusion times; quote the smoothed-plateau peak estimator; SHA-256 seeding) | AI-proposed, **student-approved pending** | Each came from a parameter-recovery failure on synthetic data (NR-11). They change what the student will physically do in the lab, which is why they need real approval rather than inheritance. |
| **Thermal Penetration Index** (`scoring/tpi.py`, `studies/tpi_study.py`; commit `1ea5317`) | AI-generated, **review pending** | Implemented, verified against closed-form cases, evaluated over 140 designs, and **discarded** against a redundancy criterion declared before the run (NR-10, verdict DISCARD). |
| **TPI redundancy criterion declared before the run** (`configs/tpi_study.yaml`) | AI-proposed, **student-approved pending** | Rank R² ≥ 0.98 or \|ρ\| ≥ 0.99 against peak bondline temperature. The criterion is the whole method; it must be a decision, not a default. |
| **OpenFOAM CFD pipeline** (`cfd/`, 3084 lines; commit `e0b40c0`) | AI-generated, **review pending** | Outline → block mesh sized from a shock-shape correlation → wedge extrude → `checkMesh` → `setFields` → `rhoCentralFoam` → force, stagnation-line, surface and outflow sampling → metrics → GCI → gate. Includes the fixes for four separate failure modes (NR-05…NR-08) and the run-until-converged logic from NR-09. |
| **Forebody-only domain** (A-CFD-4; commit `e0b40c0`) | AI-proposed, **student-approved pending** | A scope decision with a real cost: base drag is no longer computed and must come from a stated assumption with its own band. Taken because an inviscid wake never reached a steady state (NR-06). |
| **Force-convergence criterion, and the refusal to relax it** (`configs/cfd_validation.yaml`) | AI-proposed, **student-approved pending** | Peak-to-peak ≤ 0.1%, half-window drift ≤ 0.02%. Held when it bit (NR-09) and held again when five design points failed it permanently (NR-21). Rejecting six CFD cases is an engineering decision with consequences for the usable design space. |
| **CFD-derived drag surface and base-drag band** (`aerodynamics/`, 1039 lines; commit `e0b40c0`) | AI-generated, **review pending** | GP over log(Mach) and three shape ratios on 56 usable cases, held-out and k-fold validation, hull extrapolation guard, GCI hook, plus a bounded (not predicted) base-pressure ratio. Registered as PROVISIONAL and **switched off**. |
| **Sigma inflation factor of 1.65** (`aerodynamics/cfd_surface.py`) | AI-proposed, **student-approved pending** | A measured one-number recalibration of overconfident GP error bars. It does not fix the observed bias, and the report says so. |
| **Not adopting the sin²θ input** after it improved k-fold RMSE from 0.0326 to 0.0313 | AI-proposed decision, **student-approved pending** | Refused because the held-out test set had already been seen. This is one of the better methodological decisions in the repository and should be understood, not just inherited. |
| **Design space, budget meter, candidate log, Pareto and hypervolume utilities, Sobol' estimators, NSGA-II, scalarised DE, LHS** (`optimization/`, first tranche; commit `715ac9f`) | AI-generated, **review pending** | Includes the centred Sobol' estimator fix (NR-16) and the budget accounting in which an invalid geometry costs one evaluation and a repeat costs zero (A-OPT-3). |
| **Screening rule, hypervolume reference point, seven seeds, knee definition** (`configs/design_space.yaml`) | AI-proposed, **student-approved pending** | All declared before the run. The hypervolume reference point is disclosed as having been set after the evaluator had been timed on four hand-picked designs. |
| **Heat-shield mass-closure constraint at 1.0** (A-OPT-6; commit `715ac9f`) | AI-proposed, **student-approved pending** | A logical necessity rather than a judgement, added in response to NR-13. It excludes only the impossible, and the front then sits on it. |
| **Bluntness cap 1.2, then relaxed to `null`** (A-OPT-5; commits `715ac9f`, `e3c48cb`) | AI-proposed, **student-approved pending** | Added as a fence around a model failure, then removed once the model no longer had that failure. Both halves need approval; the second supersedes the M4 front. |
| **GP surrogate, ParEGO Bayesian optimiser, LLM engineering agent, replay mode** (`surrogate/` 404 lines, `optimization/` second tranche; commit `8802cb7`) | AI-generated, **review pending** | Includes the least-squares GP validity classifier and the 5% probability-of-feasibility floor, both of which were changed after a smoke test on seed 11 and before any study (NR-17). |
| **Seeds 11 and 23 removed from the M5 study seeds** (A-AI-3) | AI-proposed, **student-approved pending** | Because they informed a design change and a dry run printed their hypervolumes. Removing seen seeds is the right call and should be an explicit one. |
| **M5 success criteria** (`configs/ai_ablation.yaml`, A-AI-7) | AI-proposed, **student-approved pending** | ΔHV ≥ 0.005 **and** exact permutation p < 0.05 after Holm, declared before any run, with "no measured difference" as an explicit third outcome. |
| **Source-tree hash guard and stale-screening guard** (`optimization/guards.py`; commits `8802cb7`, `7d29c19`) | AI-generated, **review pending** | Written in response to a live study whose physics changed underneath it (NR-18). Now shared by three runners. |
| **Adaptive-fidelity harness** (`optimization/adaptive*.py`; commit `7d29c19`) | AI-generated, **review pending** | Two-budget evaluator, CFD ledger, versioned per-arm surfaces, five promotion strategies, pooled-truth scoring, pre-declared H2 rule including `NOT_TESTABLE`. 24 deterministic tests against a fake analytic F1. Study not run. |
| **Explicit hull tolerance `HULL_TOLERANCE = 1e-9`** (`surrogate/gp.py`; commit `7d29c19`) | AI-proposed, **student-approved pending** | Physically nothing; makes hull membership of a boundary design independent of the triangulation (NR-23). Without it, an adaptive-fidelity study would have punished promotion. |
| **Uncertainty propagation and robust design** (`uncertainty/`, 3982 lines across 13 modules; commit `7d29c19`) | AI-generated, **review pending** | Aleatory/epistemic separation by sample shape, nested sampling with common random numbers, p-box, Sobol' attribution, chance constraints, robust NSGA-II, and a shortcut verification with tests proving it *fails* on an injected bias. Study not run. |
| **Uncertainty as a coordinate of the design space** (`uncertainty/space.py`) | AI-proposed, **student-approved pending** | The draw index is appended to the design space as one synthetic variable so that nothing bypasses the canonical evaluator or the budget meter. A design decision worth understanding, because the obvious implementation would have violated spec §19. |
| **The whole M7 input inventory, its tiers, and the refusal policies** (`configs/uncertainty.yaml`) | AI-proposed, **student-approved pending** | Seven of nine active inputs are engineering judgment (T3). The loader refuses a T3 input whose source line does not say "judgment", and refuses the run outright when the GCI term is unavailable. Each distribution is a modelling claim. |
| **Effective-nose-radius uncertainty as a discrete 50/50 model-form switch** (A-UQ-NOSE-1) | AI-proposed, **student-approved pending** | Not Gaussian noise: two primaries disagree and there is no continuum between them. Three ways it is deliberately wider than the source licenses are listed. This is the dominant heating uncertainty. |
| **Figures and generated reports** (`viz.py`, `optimization/report.py`, `cfd/report.py`, `uncertainty/report.py`, `studies/*`) | AI-generated from data | No number in any report is typed by hand. After NR-18, generated reports no longer contain pre-written interpretive prose; interpretation is emitted by code from audit tables or not at all. |
| **Test suite** (5908 lines, 24 files) | AI-generated, **review pending** | Includes several tests that assert a *finding* rather than a fix, so the finding cannot be silently forgotten (weak identifiability of contact resistance; hull-membership independence; the unchecked atmosphere rows). |

### Proposed addition to "Standing rules for this project"

> 5. **The size of the unreviewed surface is itself reported.** As of 2026-09-20 the package
>    is 21 150 lines of Python with 5908 lines of tests, nearly all added in one day, and the
>    author has read almost none of it line by line. That number belongs in the disclosure,
>    because "AI-assisted" without it is uninformative.

### Proposed correction to an existing row

The existing table's Sutton–Graves row reads "Constant not yet re-derived from NASA TR
R-376." **That is now out of date.** Proposed replacement:

> | Sutton–Graves implementation | AI-generated, **review pending** | Constant re-derived from NASA TR R-376 on 2026-09-20 and deliberately **not changed** (+0.39%, against the primary's own 3.3% stated error). The report contains neither the equation form nor the constant; see `docs/theory/sutton_graves_constant.md` and NR-12. Gate G2 is `PASS`; gate G2′ (model form: catalycity, hot wall, radiation) is untouched. |

---

## Reading order, to be able to defend this

Honest framing first. **Reading 21 000 lines is not the task and will not happen.** The task
is to be able to explain every result and every physical decision, which is a much smaller
set of files. Most of the 21 000 lines are harness: study runners, report generators, plotting,
persistence, CLI plumbing. Those matter for reproducibility and almost never for a defence.

The order below is by *defensibility per hour*, not by dependency. Time estimates assume
reading at roughly 100 lines per hour with the theory document open alongside, which is slow
and is the realistic rate for code that implements physics you have not derived yourself.

### Tier 1 — cannot defend the project without these (about 6 hours)

| Order | File | Lines | Hours | Why first |
|---|---|---|---|---|
| 1 | `src/aether/evaluate.py` | 370 | 1.5 | The canonical evaluator. Every result in the project comes out of this one function. Read it with `ASSUMPTIONS.md` open. If you read one file, read this one. |
| 2 | `src/aether/tps/conduction1d.py` | ~470 | 2.0 | The headline claim is about what happens inside the stack, and this is the only `PASS` that claim rests on. Be able to explain the harmonic interface, why backward Euler, the Newton-linearised radiating surface, and what the energy residual measures. |
| 3 | `src/aether/geometry/stagnation_gradient.py` + `docs/theory/effective_nose_radius.md` | 282 + doc | 1.5 | The physics change of the day, worth 20% on peak heat flux. The theory document is the better entry point; read it first, then the code, and check that the code does what the document says. |
| 4 | `src/aether/heating/sutton_graves.py` + `docs/theory/sutton_graves_constant.md` | 129 + doc | 1.0 | Short file, long argument. The constant, its units, and why it was not changed. |

### Tier 2 — needed for the results sections (about 5 hours)

| Order | File | Lines | Hours | Why |
|---|---|---|---|---|
| 5 | `src/aether/trajectory/entry3dof.py` | ~300 | 1.0 | Derive dγ/dt yourself on paper first, then read. The V²cos γ / r term is a standard defence question. |
| 6 | `src/aether/optimization/pareto.py` | ~250 | 1.0 | Dominance, hypervolume, spacing, knee. Small, self-contained, and the site of NR-04. |
| 7 | `src/aether/atmosphere/us76.py` | ~300 | 1.0 | Where the exact region ends and the transcribed table begins, and why that boundary matters for the bondline (NR-14). |
| 8 | `src/aether/optimization/budget.py` + `design_space.py` | ~500 | 1.0 | What an "evaluation" costs and what a design vector is. Every study's accounting rests on these two. |
| 9 | `src/aether/geometry/capsule.py` (`validate()` and `effective_nose_radius_m` only) | ~150 of 619 | 1.0 | Read the validator and the effective-radius property. Skip the STL writer unless asked about it. |

### Tier 3 — read before the studies are run, not after (about 5 hours)

| Order | File | Hours | Why |
|---|---|---|---|
| 10 | `src/aether/surrogate/gp.py` | 1.5 | GP prediction, the hull guard, `HULL_TOLERANCE`. Needed for every §11–13 question. |
| 11 | `src/aether/uncertainty/statistics.py` + `sampling.py` | 1.5 | Wilson, Clopper–Pearson at k = 0, percentiles, nested draws and common random numbers. Small files carrying the answers to several defence questions. |
| 12 | `src/aether/optimization/ai_agent.py` (the prompt builder and the schema validator) | 1.0 | What the agent sees and what is rejected. Needed to answer "what did AI contribute" precisely. |
| 13 | `src/aether/optimization/guards.py` | 1.0 | Short. The response to NR-18, and the best single illustration of what went wrong organisationally. |

### Tier 4 — skim only, unless a question lands on it

`cfd/` (3084 lines), `optimization/adaptive*.py`, `uncertainty/robust.py`, every `report.py`
and `plots.py`, `studies/*`, `experiments/thermal_coupon/analysis/`. Read the **docstrings**
and the configuration files that drive them. For CFD specifically,
`docs/validation/M2_model_form_limits.md` and the generated M2 and M3 reports carry everything
a defence needs; the pipeline code is reproducibility infrastructure.

### Total

**About 16 hours of real reading** to get from "an AI wrote it" to "I can explain every result
and every physical decision". Realistically that is four to six sittings. It is not
negotiable down by reading faster; it is negotiable down only by deciding that some results
will not be defended, which is a worse trade.

### Two things to do while reading, not afterwards

1. **Update `AI_USAGE.md` as you go.** Move a row from *review pending* to *student-reviewed*
   the day you finish the file. A batch update at the end is a guess.
2. **Write your own answer to the matching defence question before reading the code**, then
   check it. `docs/defense_questions.md` is indexed to roughly the same order. Reading code
   to confirm an answer you have already attempted sticks; reading it to absorb an answer
   does not.

---

## What the coordinator should check before merging

- That no row here is marked reviewed. None is.
- That the "AI-proposed, student-approved pending" rows really are decisions rather than
  implementation details. Fourteen are listed; each changes a result, a physical model, a
  declared criterion, or what the student will do in a laboratory.
- That the correction to the existing Sutton–Graves row is applied, since the current text is
  now false.
- That the line counts are current at merge time. They were measured on 2026-09-20.
