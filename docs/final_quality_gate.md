# Final quality gate (spec §53)

Twelve items that must be demonstrated before the capstone can be declared complete. The
specification closes with the sentence this file exists to enforce: *do not declare the
capstone complete merely because all planned software modules exist.*

> ## The project is NOT complete by §53.
>
> Assessed 2026-09-21 at commit `de2a834`, after every simulation study had run and the
> paper had been drafted. Three of the twelve items are **NOT MET**, and all three need the
> student in person:
>
> - **item 8, blind experimental prediction**: no coupon has been printed and no measurement
>   exists;
> - **item 9, external technical criticism**: no review has been requested or received;
> - **item 12, clear student intellectual ownership**: the code is unread, twenty-two
>   AI-proposed decisions are unapproved, and the paper is an AI draft the student has not
>   revised.
>
> No amount of further computation or drafting changes any of the three. Until they move,
> the honest description of the repository is: simulation studies complete, paper drafted,
> project not complete.

This assessment was written by the AI assistant from the repository's files. The student
should re-assess it himself; item 12 in particular is not something an assistant can grade.

Status vocabulary matches `VALIDATION_MATRIX.md`:

- **MET**: demonstrated, with evidence on disk.
- **PARTIAL**: demonstrated in a narrower sense than the item asks for, with the narrowing
  stated.
- **NOT MET**: not demonstrated.

**Score: 6 MET, 3 PARTIAL, 3 NOT MET.** On 2026-09-20 it was 4, 4 and 4. Items 3, 5 and 7
moved up because gate G4 closed and the M4 and M7 studies ran; item 6 moved from NOT MET to
PARTIAL. Items 8, 9 and 12 have not moved.

---

## 1. Non-obvious research question

**Status: MET.**

Whether minimising peak external heat flux can select a design that is worse where the heat
shield fails. The trade between peak heat rate and total heat load is standard and documented
in NASA training material; the consequence for the in-depth response is not, and the accepted
in-depth criterion is a maximum at a single plane. The question is about a regime: it is
trivially false for a thick enough stack, where the bondline moved 8.8 K over a whole entry.

**Evidence.** `docs/research_story.md`; `docs/theory/tpi.md` §§2.1–2.2;
`docs/negative_results.md` NR-03; `reports/final/AETHER_paper.md` §2.

**What remains.** Nothing. The standing honesty note: the framing came from the project
specification, and the research story and the paper's introduction both say so.

---

## 2. Falsifiable hypotheses

**Status: MET.**

H0, H1 and H2 were frozen before any model was built, each with a stated falsification
condition. The strongest evidence that the conditions were real is that one of them fired:
**H2 returned `NOT_SUPPORTED`** under a criterion written into a configuration file before
the run, and the criterion was left as written even after it turned out to have been sized
against an unreachable target (NR-35). H0 was falsified once, at a 40 mm stack. The TPI
redundancy criterion was declared first and then fired. The M5 rule returned "no measured
difference" at 200 evaluations on its effect-size leg although the significance leg
rejected, and was applied as written.

**Evidence.** `CLAUDE.md` §4; `reports/final/AETHER_paper.md` §4;
`configs/tpi_study.yaml`; `configs/ai_ablation.yaml` (A-AI-7);
`configs/adaptive_fidelity.yaml` (A-AF-9); `reports/milestones/M6_adaptive_fidelity.md`.

**What remains.** Nothing.

---

## 3. Verified implementation

**Status: MET, with one history a reader must be given.** (Was PARTIAL.)

The reduced-order chain is verified as before: conduction solver 0.002% against an
analytical solution with an energy residual near 1e-14; geometry, effective nose radius,
Sobol' estimator and the uncertainty chain each pinned against closed forms. The test suite
stood at 497 passed, 1 skipped at the 2026-09-21 report regeneration.

The CFD mesh study that was missing on 2026-09-20 now exists: three meshes at Mach 3 and 6,
forebody C_D monotone, GCI_fine 0.098% and 0.187%, observed order 1.13 and 0.88.

**The history.** Gate G4 first read `LIMITED`, because both fine-mesh cases ended in a
bounded limit cycle outside the peak-to-peak limit. The criterion was not changed; the cases
were continued at a lower Courant limit and met it in two consecutive blocks. The restart
rule and the solution-of-record rule were written after the original results had been seen
(NR-25). A reader who does not accept that should read this item as PARTIAL. Both gate
assessments are on disk.

**Not covered by this item:** whether the drag is right on capsules. That is matrix row M3,
which is `LIMITED` (coarse mesh, sphere-derived discretisation band, perfect gas, assumed
base drag).

**Evidence.** `VALIDATION_MATRIX.md` rows G1A–G5; `reports/milestones/M2_cfd_validation.md`;
`results/M2/M2-20260920T123901Z/gate_assessment.json` and
`gate_assessment_20260921_0057_before_restarts.json`;
`reports/milestones/REPORT_REGENERATION_2026-09-21.md` (test count).

**What remains.** Optional: apply the Courant restart to the five capsule cases that still
fail the force criterion; run the design points on the medium mesh (estimated about 8 h in
`REPRODUCIBILITY.md`, not run).

---

## 4. Independent validation

**Status: PARTIAL.** (Unchanged.)

Every `PASS` in the matrix is against a published number, an analytical solution or an
independently implemented closed form, and the CFD benchmark that was missing on 2026-09-20
is done: stagnation pressure within 0.14% and 0.44% of the Rayleigh-pitot value, stand-off
within 0.95% and 0.65% of Van Dyke and Gordon, forebody C_D within 0.32% and 1.82% of Clark's
expression, on a sphere at Mach 3 and 6.

It stays PARTIAL for three reasons. **Nothing is validated against a physical measurement.**
The heating model form (gate G2′: catalycity, hot wall, radiation) is `LIMITED` and was not
attempted, and catalycity alone is worth about a factor of two. And the CFD is validated on a
sphere at two Mach numbers, while the surface is used on capsules up to Mach 27 with a
declared ±5% perfect-gas band that this project has not validated. Four method citations the
validated rows lean on have not been checked against their primaries (Celik et al., Billig,
Carslaw and Jaeger §2.9, the Saltelli and Jansen estimators).

**Evidence.** `VALIDATION_MATRIX.md`; `reports/milestones/M2_cfd_validation.md` Condition 3;
`docs/validation/sourcing_report.md` item 9; `reports/final/AETHER_paper.md` §6, §20 second
block.

**What remains.** The physical experiment (item 8). Checking the four method citations
against library copies. Quantifying G2′, catalycity first.

---

## 5. Signature burn-vs-bake result, or honest rejection

**Status: MET, at Fidelity 0 and Fidelity 1, and under the declared uncertainties.**

Fidelity 0: over a 41-point sweep both metrics are strictly monotone in entry angle with
opposite signs (−38.3% peak flux, +114.1 K bondline between the ends; 818 counterexample
pairs of 1640). The Spearman ρ = −1.000 is disclaimed as tautological for a one-parameter
sweep. Fidelity 1: the knee of the 78-design front runs 14.9 K cooler at the bondline than
the peak-flux-only optimum for +21.5 kW/m². Under uncertainty, paired on shared draws:
−14.31 K, s.d. 1.45 K, negative in 3000 of 3000 draws and 24 of 24 epistemic branches.

It is MET because of how it is reported as much as because it exists. The Fidelity-1 result
is stated as a trade in entry angle at a geometry fixed by fences: 50 of 78 front designs
within 1% of an unsourced mass-fraction limit (the knee's shield is 346 kg of 350 kg), 28 of
78 on the CFD-hull edge, C_D at peak heating varying by about 0.1% across the front, and a
frozen shoulder lever worth about 7%. It is not reported as a located capsule shape.

**Evidence.** `reports/milestones/M1_burn_vs_bake.md`, `M1_signature_counterexample.md`,
`M4_pareto_optimisation.md` §10–§11a, `M7_addendum_posthoc.md` §1–§2; NR-29, NR-30.

**What remains.** Nothing for the item. What would make the result about shape: a mass model,
a heating model that sees the shoulder, CFD anchors beyond R_n/D = 1.2.

---

## 6. Fair AI ablation

**Status: PARTIAL.** (Was NOT MET.)

The study ran once on the final model (`M5-ABL-20260920T211134Z`, 200 evaluations × 5 seeds,
67 live LLM calls, none failed or malformed), a strict replay with no model access reproduced
every per-seed hypervolume exactly, and a hand-written audit of all 67 agent rounds exists.
The pre-declared rule was applied as written: AI helped at 50 and 100 evaluations, no
measured difference at 200. The asymmetries are disclosed (named variables carry prior
knowledge; the agent reads validator failure messages), as are the two pre-study changes to
the Bayesian optimiser and the earlier aborted run.

PARTIAL because spec §46 lists five methods and the fifth, **AI plus adaptive fidelity, has
no result**: in M5 its row is labelled not meaningful (0 of 360 promotion decisions granted),
and in M6 the arm was declared and not run. Also n = 5, one model, one easy problem; the
early lead cannot be separated from contamination; and a little under half of the final lead
is precision on placeholder limits (NR-32).

**Evidence.** `reports/milestones/M5_ai_ablation.md`, `M5_qualitative_audit.md`;
`results/M5/M5-ABL-20260920T211134Z/` (+ `audit/`); replays `M5-REPLAY-20260920T224633Z`,
`M5-REPLAY-20260921T013046Z`; NR-17, NR-18, NR-31, NR-32.

**What remains.** Running the `ai_adaptive` arm needs the student's authorisation for live
LLM calls, and on this design space it would very likely be uninformative for the reason
M6 found. If M5 is ever re-run: carry the agent's own observations forward between rounds,
and report hypervolume with a constraint stand-off beside the raw value.

---

## 7. Uncertainty analysis

**Status: MET, as a lower bound.** (Was NOT MET.)

Four designs × 3000 nested draws (24 epistemic branches × 125 aleatory draws), Sobol'
attribution on two designs, robust NSGA-II over 3 seeds × 30,000 inner evaluations, and a
pre-declared shortcut verification that PASSED (bias −1.61% / +0.32%, Spearman 1.000 /
1.000, largest probability error 2.60%). Mean, standard deviation, percentiles and
constraint-violation probability with Wilson intervals are reported for every final
candidate, and the §39 table has a like-for-like robust column (`M7-LFL-20260921T011854Z`).

Four qualifications travel with it. Every spread is a **lower bound**, because G2′ has no
distribution. Seven of twelve inputs are engineering judgment, including the two that
dominate the bondline (TPS conductivity and the multiplier on heating above 86 km). The
pre-declared row bootstrap understates sampling error about tenfold; on a branch bootstrap
the baseline mean marginally misses the 1% tolerance (NR-34). And the robust optimiser used
its chance allowance to the last of 32 fixed draws, with one of 8 re-scored designs reading
5.7% against the 5% limit on fresh draws (NR-33).

**Evidence.** `reports/milestones/M7_uncertainty_robust.md`, `M7_addendum_posthoc.md`;
`results/M7/M7-UQ-20260920T233048Z/`, `M7-ROBUST-20260920T211216Z/`,
`M7-LFL-20260921T011854Z/`; `REPORT_REGENERATION_2026-09-21.md`.

**What remains.** More epistemic branches if absolute statistics matter. A measured
conductivity and a sourced high-altitude treatment would do more than any further sampling.

---

## 8. Blind experimental prediction

**Status: NOT MET. Needs the student. No coupon has been printed and no measurement
exists.** (Unchanged.)

The support package is complete and the calibrate → freeze → predict → archive → measure →
compare chain has been verified against synthetic data generated by this project's own
solver, which is a check on the software and nothing else. That check found four traps
(NR-11) and changed the protocol.

**Evidence.** `VALIDATION_MATRIX.md` row M8 (`IN_PROGRESS`); `experiments/thermal_coupon/`
(README, `protocol.md`, `blind_validation/`); `tests/test_thermal_coupon.py`; paper §14 with
its marked results slot.

**What remains, and it is physical work.** Decide polymer, heater and sensors. Print the
coupon, a spare to section, and the holder. Two-point sensor calibration; calorimetric flux
calibration; the dedicated steady-state contact-resistance run; the cool-down run; the long
step run (two to three diffusion times, about an hour). **Declare the tolerance and commit
it.** Freeze, predict both cases, commit and push. Run each validation case at least twice.
Compare. Fill the paper's §14.3 and move row M8.

---

## 9. External technical criticism, if available

**Status: NOT MET. Needs the student. No review has been requested or received.**
(Unchanged.)

Three review forms and a cover note exist. There are no reviewer names in the repository and
no invented, paraphrased or reconstructed reviews.

**Evidence.** `docs/external_reviews/` (README, R1, R2, R3, cover note template), all empty.

**What remains.** Ask someone. R1 (assumptions) needs no CFD background. The material a
reviewer would most usefully attack is now written down in one place: paper §10.3–§10.4 and
§16.

---

## 10. Negative results

**Status: MET.**

Thirty-five entries (NR-01 to NR-35), each written when it was found. Eleven were added
since the last assessment, and they include the ones that cut against the project's own
results: a gate that first read LIMITED (NR-25); a convergence pass that nearly admitted two
drifting cases (NR-27); the frozen shoulder lever (NR-29); the front as a flight-path-angle
curve at a fenced geometry (NR-30); three generated reports carrying sentences from an older
model, one with a mislabelled figure (NR-31, NR-34); the agent polishing placeholder limits
(NR-32); nominal optima violating a constraint in 30–47% of draws (NR-33); and H2 not
supported against an unreachable target (NR-35). Failed and aborted runs stay on disk.

**Evidence.** `docs/negative_results.md`; `reports/final/AETHER_paper.md` §17.

**What remains.** The experiment will produce more. Write them when they happen.

---

## 11. Stranger reproducibility

**Status: PARTIAL.** (Unchanged.)

Deterministic Fidelity-0 chain; seeded stochastic studies; immutable config snapshots;
generated reports; a source-hash guard on long runs; an LLM study that replays with no model
access, twice, with zero prompt mismatches; and a checker that proved the 2026-09-21 report
regeneration moved no stored value.

Defects, all small, none fixed by this assessment:

1. **No public location.** The repository is not public or archived at a release commit.
   `[PENDING — STUDENT]`
2. **Dirty-tree flags.** The M1, TPI, M2, M4, M5, M6 and M7 report headers all record a dirty
   working tree. Honest, and should not be true of final artefacts; curing it means re-running
   from a clean commit.
3. **`REPRODUCIBILITY.md` was partly stale; fixed in the 2026-09-21 consistency sweep.** It
   said `make test` was "38 verification tests" (now: 498, 497 passed / 1 skipped), that
   OpenFOAM was "required only for Fidelity 1, which is not yet active" (Fidelity 1 is
   active; OpenFOAM is needed only to build or extend a surface, not to evaluate one), that
   `make ablation` was "not yet run to completion" (it ran: `M5-ABL-20260920T211134Z`), and
   it warned against `make uncertainty-report` (that warning was lifted on 2026-09-21, now
   stated). Its runtime table was already current.
4. **The 27-versus-41 discrepancy** is resolved in `REPRODUCIBILITY.md` and the submission
   package (41), and survives only in the dated 2026-09-02 entry of `docs/research_story.md`,
   which is not rewritten.
5. OpenFOAM v2512 was used, not the v2606 the specification names.

**Evidence.** `REPRODUCIBILITY.md`; `docs/submission_package/reproducibility_links.md`;
`reports/milestones/REPORT_REGENERATION_2026-09-21.md`.

**What remains.** Item 3's stale lines are fixed; choose a public location; tag a clean commit.

---

## 12. Clear student intellectual ownership

**Status: NOT MET. Needs the student. This is the item nobody else can discharge.**
(Unchanged, and the surface has grown.)

Re-measured 2026-09-21 (`AI_USAGE.md` rule 5): 23,869 lines of Python with 6,587 lines of
tests, up from the 2026-09-20 count of 21,150 / 5,908, nearly all added in one day and
almost none read line by line. Every row added to
`AI_USAGE.md` since M1 is *review pending*. Twenty-two AI-proposed decisions await approval;
several change a physical model or decide what will happen in a laboratory. Since the last
assessment the assistant has also run the M4 to M7 studies, written two post-hoc addenda and
the agent audit, fixed the report generators, **and drafted the final paper and the whole
submission package**. None of that has been revised by the student.

**Evidence.** `AI_USAGE.md`; `docs/ai_usage_proposed_update.md`;
`docs/defense_questions.md`; `reports/final/HANDOFF.md`.

**What remains.** About **16 hours** of reading, in the order given in
`docs/ai_usage_proposed_update.md`, moving rows to *student-reviewed* on the day each file
is finished. Approve or reject the twenty-two decisions. Rewrite the paper in his own words,
checking each number against its file. Be able to say, from memory, the five sentences at
the end of `reports/final/HANDOFF.md`.

---

## Summary

| # | Item | Status | Blocked on |
|---|---|---|---|
| 1 | Non-obvious research question | **MET** | — |
| 2 | Falsifiable hypotheses | **MET** | — |
| 3 | Verified implementation | **MET**, with the G4 history | — (a reader rejecting NR-25's restart rule reads PARTIAL) |
| 4 | Independent validation | PARTIAL | the experiment; G2′; four unchecked method citations |
| 5 | Burn-vs-bake result | **MET**, F0, F1 and under uncertainty | — |
| 6 | Fair AI ablation | PARTIAL | AI + adaptive-fidelity arm has no result; n = 5, one model |
| 7 | Uncertainty analysis | **MET**, as a lower bound | — |
| 8 | Blind experimental prediction | **NOT MET** | **the student**, physically |
| 9 | External technical criticism | **NOT MET** | **the student**, asking someone |
| 10 | Negative results | **MET** | — |
| 11 | Stranger reproducibility | PARTIAL | stale lines, dirty-tree flags, public location |
| 12 | Student intellectual ownership | **NOT MET** | **the student**, about 16 hours plus the paper |

Everything that computation could close has been closed or has returned its answer. What is
left is the student's own hands and one other person's criticism.

---

## Things only the student can do

Ordered by how much of the gate they unlock. Detail and time estimates:
`reports/final/HANDOFF.md`.

1. **Read the code.** About 16 hours. Unlocks item 12.
2. **Run the thermal coupon.** Unlocks item 8 and strengthens item 4.
3. **Decide the deceleration limit.** Option A relabels 12 g as an emergency envelope; option
   B adopts the NASA-STD-3001 duration curve, which on the Fidelity-0 grid leaves 4 of 140
   designs at 10 g and none at 8 g, and needs a pulse-duration metric the evaluator does not
   compute.
4. **Ask one person for a review.** Unlocks item 9.
5. **Approve or reject the twenty-two AI-proposed decisions**, and decide whether to accept a
   drag surface built on the coarse mesh.
6. **Revise and own the paper.**
