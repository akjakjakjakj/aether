# AI usage disclosure

This project was built with AI assistance (Claude, via Claude Code). Hiding that would
be dishonest and would also make the work impossible to defend. This file records what
was AI-generated, what was reviewed, and what the student must be able to explain
unaided.

## Categories

- **AI-generated, student-reviewed** — written by the model, read line by line and
  understood by the student.
- **AI-proposed, student-approved** — an engineering or modelling decision suggested by
  the model and accepted by the student after considering it.
- **Student-authored** — the student's own decision or writing.
- **External** — from a cited published source.

## Current state (2026-09-02, after M1)

| Item | Category | Note |
|---|---|---|
| Research question and hypotheses H0/H1/H2 | External / student-approved | Framed in the capstone specification (`CLAUDE.md`, `docs/AETHER_Capstone_Specification.md`), which the student received and accepted as the frozen scope. |
| USSA-76 implementation | AI-generated, **review pending** | Layer constants are from the published standard. The >86 km table is transcribed and unverified — see VALIDATION_MATRIX G1A′. |
| 3-DOF equations of motion | External | Standard planar entry equations. The student must be able to derive dγ/dt, including the V²cos γ / r centrifugal term. |
| Sutton–Graves implementation | AI-generated, **review pending** | Constant re-derived from NASA TR R-376 on 2026-09-20 and deliberately **not changed** (+0.39%, against the primary's own 3.3% stated error). The report contains neither the equation form nor the constant; see `docs/theory/sutton_graves_constant.md` and NR-12. Gate G2 is `PASS`; gate G2′ (model form: catalycity, hot wall, radiation) is untouched. |
| 1-D conduction solver (FV, backward Euler, harmonic interfaces) | AI-generated, **review pending** | The student must be able to explain why the scheme is conservative and why backward Euler was chosen. |
| Newton linearisation of the radiating boundary | AI-proposed, student-approved | Proposed in response to an actual divergence: a fixed-point sweep on T⁴ blew up on the first run. Recorded in `docs/negative_results.md` NR-01. |
| Post-entry soak-out phase | AI-proposed, student-approved | Proposed after observing that truncating the thermal solve at the trajectory's end understated the bondline peak by ~50 K. NR-02. |
| Sizing the TPS to 15 mm | AI-proposed, student-approved | At the original 40 mm the bondline never responded within the entry, which would have hidden the effect under a design margin nobody would actually fly. NR-03. |
| Verification tests | AI-generated, student-reviewed | The analytical benchmark (Carslaw & Jaeger §2.9) is external. |
| `pareto_front` dominance test | AI-generated, **defect found and fixed** | The first implementation was wrong and produced a non-monotone "front". Caught by looking at the figure. NR-04. |
| Figures and reports | AI-generated from data | No number in any report is typed by hand; all are read from the result files. |

## Standing rules for this project

1. **No result is reported that the student cannot explain.** `docs/defense_questions.md`
   is the checklist.
2. **Review status is tracked honestly.** Rows above marked *review pending* are exactly
   that. They will be changed only when the student has actually read and understood
   the code, not when the milestone is declared done.
3. **The AI does not decide physics.** Every modelling choice that changes a result is
   recorded here with the reason it was accepted.
4. **Negative results stay.** Four AI-introduced problems are recorded in
   `docs/negative_results.md` rather than quietly fixed, because the debugging is part
   of the research record.
5. **The size of the unreviewed surface is itself reported.** As of 2026-09-21 the package
   is 23869 lines of Python with 6587 lines of tests, nearly all added in one day, and the
   student has read almost none of it line by line. A reading order (~16 hours) is in
   `docs/ai_usage_proposed_update.md`.

## Current state (2026-09-20, after M2–M7 harnesses)

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

## Current state (2026-09-21, after the M4–M7 study runs and the paper draft)

Every row below is **review pending** or **student-approved pending**. None of the rows in
the two tables above has moved since it was written.

| Item | Category | Note |
|---|---|---|
| **Gate G4 Courant restarts and the solution-of-record rule** (run `M2-20260920T123901Z`; NR-25) | AI-proposed, **student-approved pending** | Both fine-mesh cases missed the force criterion and the gate read LIMITED. The criterion was kept; the cases were continued at max Courant 0.1 and passed; the gate reads PASS. **The restart rule, the two-block minimum and the of-record rule were written after the original results had been seen.** Whether that history permits downstream use of the CFD is the student's call, and everything in M3–M7 stands on it. |
| **Drag surface rebuilt as `cfd_surface_v2`** (69 usable cases, Mach 27 node, Courant pass, two-consecutive-blocks rule; NR-27, NR-28) and the evaluator switched to Fidelity 1 | AI-generated, **review pending**; the coarse-mesh choice is AI-proposed, **student-approved pending** | The two-consecutive-blocks rule was written during the run after an interim look; it is stricter and removed two points the looser reading would have admitted. Sigma inflation factor stored with v2 is 1.21 (the 1.65 in the table above describes v1). |
| **M4 re-run at Fidelity 1** (runs `M4-DOE-20260920T204844Z`, `M4-OPT-20260920T205252Z`), its metric-gaming audit and the audit probes (`scripts/run_m4_audit_probes.py`) | AI-run study, AI-generated report, **review pending** | Source of the H1 headline (knee −14.9 K, +21.5 kW/m²) and of the finding that the front is an entry-angle curve at a fenced geometry (NR-29, NR-30). |
| **Leaving the shoulder ratio frozen and labelling the freeze a fence** (NR-29) | AI-proposed decision, **student-approved pending** | The frozen lever is worth about 7% of peak flux at the front. The rule was not re-tuned after seeing that, because that would have been tuning. The student should be able to say why a Sobol' index missed it. |
| **M5 study run** (`M5-ABL-20260920T211134Z`; 67 live LLM calls to `claude-sonnet-5`; replays `M5-REPLAY-20260920T224633Z`, `M5-REPLAY-20260921T013046Z`) | AI-run study, AI-generated report, **review pending** | The pre-declared rule was applied as written: AI helped at 50 and 100 evaluations, no measured difference at 200. An AI system launched a study of an AI system; the prompts, responses and replay are what make that checkable. |
| **M5 qualitative audit** (`reports/milestones/M5_qualitative_audit.md` and `results/M5/M5-ABL-20260920T211134Z/audit/*.py`) | AI-written (hand-written by the assistant, not generated from `summary.json`), **review pending** | The only hand-written section of the M5 report, and the only handle on the priors-versus-data question. It is one AI model's reading of another's output. The student should read at least the rounds of seeds 37 and 41 himself. |
| **M6 study run** (`M6-AF-20260920T211148Z`, `SKIP_LLM=1`, 125 OpenFOAM cases) and `M6_addendum_posthoc.md` | AI-run study; generated report plus AI-written addendum, **review pending** | H2 NOT_SUPPORTED. The decision not to run the `ai_adaptive` arm (live LLM calls not authorised) and the decision to leave the unreachable criterion as written and not re-score it (NR-35) are AI-proposed, **student-approved pending**. |
| **M7 study runs** (`M7-ROBUST-20260920T211216Z`, `M7-UQ-20260920T233048Z`), `scripts/analyse_m7_paired.py` and `M7_addendum_posthoc.md` | AI-run studies; generated report plus AI-written addendum, **review pending** | The paired same-draw analysis (−14.31 K, s.d. 1.45 K, 3000 of 3000) is post hoc: it reads stored files and evaluates nothing, but it was not pre-declared. The branch-bootstrap convergence check is likewise post hoc and is reported beside the pre-declared row bootstrap, never instead of it. |
| **Report-generator fixes** for M5, M6 and M7 (NR-31, NR-34, NR-35 follow-ups), `scripts/check_report_regeneration.py`, `tests/test_report_regeneration.py`, `reports/milestones/REPORT_REGENERATION_2026-09-21.md` | AI-generated, **review pending** | The defects were introduced by AI-generated generators (pre-written sentences true of an older model; a projection stored under a `measured_*` key; a figure with another panel's axis labels) and found by the assistant reading reports against their own JSON and figures. The checker shows no stored value moved (2,551 and 13,744 values compared). |
| **Like-for-like re-propagation of the robust knee** (`scripts/run_m7_robust_likeforlike.py`, run `M7-LFL-20260921T011854Z`) | AI-proposed and AI-run, **student-approved pending** | Made after the study, under a later source hash, guarded by reproducing 120 of the study's own evaluations to 3.5e-14 relative. It supersedes the original 500-draw robust cell in the §39 table; the original is kept. Superseding a cell after the fact is a decision, even a well-guarded one. |
| **Final paper** (`reports/final/AETHER_paper.md`) | **AI-drafted, not yet revised by the student** | Drafted on 2026-09-21 from the result files and generated reports at commit `de2a834`, revising eight earlier AI-drafted sections. Where it says "I did not change the constant" or "I have left the criterion as written", the decision was AI-proposed and is among those awaiting approval. **The student must revise it, check each number against its file, and own it before it goes anywhere.** |
| **Submission package fill, `docs/final_quality_gate.md`, `PROJECT_STATUS.md`, `README.md`, `ROADMAP.md`, the 2026-09-21 entries of `docs/research_story.md`, the filled answers in `docs/defense_questions.md`, `reports/final/HANDOFF.md`** | **AI-drafted, review pending** | All written by the assistant on 2026-09-21 from the same files. The research-story entries are the assistant's account of what happened; the student should correct anything that does not match his own understanding. The spoken scripts in particular should be rewritten in his own words. |

## What the AI did *not* contribute

The research question, the choice of hypotheses, the frozen scope, and the decision that
the bondline rather than the surface is the interesting failure mode. Those came from
the project specification.
