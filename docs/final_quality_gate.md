# Final quality gate (spec §53)

Twelve items that must be demonstrated before the capstone can be declared complete. The
specification closes with the sentence this file exists to enforce: *do not declare the
capstone complete merely because all planned software modules exist.*

**Assessed 2026-09-20.** Status vocabulary matches `VALIDATION_MATRIX.md`:

- **MET** — demonstrated, with evidence on disk.
- **PARTIAL** — demonstrated in a narrower sense than the item asks for, with the narrowing
  stated.
- **NOT MET** — not demonstrated. Not a criticism; several items are gated on work that has
  deliberately not been run.

**Score: 4 MET, 4 PARTIAL, 4 NOT MET.** Of the eight that are not MET, **five need the
student personally** and cannot be discharged by any amount of further computation.

---

## 1. Non-obvious research question

**Status: MET.**

The question is whether minimising peak external heat flux can select a design that is worse
where the heat shield actually fails. It is non-obvious in a specific and checkable sense:
the trade between peak heat rate and total heat load is standard and documented in NASA
training material, while the consequence for the *in-depth* response is not, and the accepted
in-depth design criterion is a maximum at a single plane rather than anything cumulative. The
project's own falsification of a nearby idea supports the non-obviousness: it is trivially
false for a sufficiently thick stack, where the bondline moved 8.8 K over an entire entry, so
the question is about a regime rather than a universal.

**Evidence.** `docs/research_story.md`; `docs/theory/tpi.md` §§2.1–2.2 (the sourced statement
of conventional practice); `docs/negative_results.md` NR-03.

**What remains.** Nothing for this item. One honesty note that belongs with it and is already
recorded: the framing came from the project specification, not from an observation made
during the work, and both `docs/research_story.md` and the paper's introduction say so.

---

## 2. Falsifiable hypotheses

**Status: MET.**

H0, H1 and H2 were frozen before any model was built. Each has a stated falsification
condition, and the conditions are not decorative:

- H0's counterexample search has detection thresholds declared in advance, at least 1.0% flux
  reduction and at least 1.0 K bondline penalty, so noise cannot be reported as physics. It is
  falsifiable and was in fact falsified once, at a 40 mm stack.
- H1's comparison fixes the definition of "joint" without weights, using the front's knee,
  and reports an absolute difference rather than a ratio, so neither can be adjusted after the
  fact.
- H2's criterion includes a **`NOT_TESTABLE`** verdict if the arm that buys no CFD reaches
  the target, because "fewer calls" is meaningless if no calls were needed.

The same discipline appears outside the three hypotheses: the TPI redundancy criterion was
declared in a config file before the run and then fired.

**Evidence.** `CLAUDE.md` §4; `reports/final/sections/03_hypotheses.md`;
`configs/tpi_study.yaml`; `configs/ai_ablation.yaml` A-AI-7; `configs/adaptive_fidelity.yaml`
A-AF-9.

**What remains.** Nothing for this item.

---

## 3. Verified implementation

**Status: PARTIAL.**

The reduced-order chain is verified. The CFD is not.

**Verified.** The conduction solver matches an analytical solution to 0.002% at the surface,
checked at four depths, with demonstrated grid and timestep convergence and an energy residual
around 1e-14. The geometry module passes 42 tests including closed-form limits, an independent
numerical cross-check of its own volume, and watertightness verified by reading the exported
file back. The effective-nose-radius model passes 49 tests including exactness at every
tabulated point and both analytic limits. The Sobol' estimator is pinned against a function
with analytically known indices. The uncertainty chain is checked against a toy linear model
whose mean, variance and percentiles are analytic, and its shortcut verification has tests
proving it *fails* on an injected bias.

**Not verified.** Mesh independence for the CFD. The M2 report prints "GCI not available:
fewer than three successful mesh levels at any Mach." Three downstream consumers refuse rather
than guess, which is the right behaviour but is not a substitute.

**Evidence.** `VALIDATION_MATRIX.md` rows G1A, G1B, G2, G3, G3b, G-GEO, G-GEO2 against row
G4; `tests/` (24 files, 5908 lines).

**What remains.** Complete the three-level mesh study and produce a GCI. This is compute, not
judgement.

---

## 4. Independent validation

**Status: PARTIAL.**

Every `PASS` in the matrix is against a published number, an analytical solution, or an
independently implemented closed form. That is real independent validation and it is the
project's strongest suit. **None of it is against a physical measurement.**

The three 2026-09-20 upgrades are each narrower than their row titles, and the narrowing is
recorded rather than rounded up: the atmosphere row validates a *transcription* at five
altitudes; the trajectory row validates the *integration* under an exponential atmosphere and
constant gravity, not the production configuration; the heating row validates the *constant*,
not the correlation, and the model-form row where catalycity alone is worth about a factor of
two is untouched and marked *not attempted*.

**Evidence.** `VALIDATION_MATRIX.md` and its closing section "The three 2026-09-20 upgrades,
and what they did *not* buy"; `docs/validation/sourcing_report.md`.

**What remains.** Three things, in order of value: (a) the CFD benchmark against a published
blunt-body case, which is gate G4 condition 3 and is not done; (b) quantifying the heating
model form, catalycity first, which is the largest unquantified term in the project and is
blocked on reading two review papers whose provenance record is itself contradictory (see
item 12); (c) the physical experiment, which is item 8.

---

## 5. Signature burn-vs-bake result, or honest rejection

**Status: MET, at Fidelity 0.**

Over a 41-point sweep both metrics are strictly monotone in entry angle with opposite signs:
the shallowest entry cuts peak heat flux 38.3% and runs the bondline 114.1 K hotter, and no
interior angle improves both. An automated pair search with pre-declared thresholds found 818
counterexample pairs of 1640 tested. Opening the diameter axis recovers 21 feasible designs of
140, where a joint optimiser selects a design 32.5 K cooler at the bondline than a
peak-flux-only optimiser.

The item is MET rather than PARTIAL because of how the result is *reported*, not only because
it exists. The Spearman ρ = −1.000 is explicitly disclaimed as close to tautological over a
one-parameter sweep. The margin is reported as an absolute 32.5 K rather than as a ratio that
would swing from 37.5× to 1.6× with the allowable. The feasibility squeeze, zero of 41
candidates valid, is reported as an unanticipated result rather than buried. And the active
diameter bound is flagged as meaning the bound rather than the physics is selecting the
optima.

**Evidence.** `reports/milestones/M1_burn_vs_bake.md`;
`reports/milestones/M1_signature_counterexample.md`;
`reports/final/sections/06_burn_vs_bake.md`.

**What remains.** The Fidelity-1 version. These are legacy-heating-model numbers, and for
these particular geometries that label costs nothing, because both use a hemisphere nose where
the legacy and corrected models agree identically. The shallow-cap optimisation fronts are a
different matter and are superseded.

---

## 6. Fair AI ablation

**Status: NOT MET. The study has not been run.**

What exists: a harness with a strict response schema where out-of-bounds proposals are
rejected and never clipped; hard per-seed and study-wide call caps; every prompt and response
persisted with a strict replay that reproduces the candidate log exactly; exact permutation
and signed-rank tests checked against their known extreme values; and success criteria
declared in a config file before any run, including "no measured difference" as an explicit
third outcome.

What also exists, and matters for the fairness claim: the two asymmetries are disclosed rather
than removed. No optimiser gets the free analytic geometry-validity check, but the language
model still reads the validator's failure message for designs it paid for, while the numeric
optimisers see only a fixed violation. And variable names carry aerospace meaning, so prior
knowledge cannot be separated from reasoning over the supplied data.

Two disclosures against the study's own interest are already recorded: two faults in the
Bayesian optimiser were fixed after looking at one seed of one method, before the study ran,
and that seed was removed from the study seeds; and an earlier run was aborted when the
physics changed underneath it and must not be analysed.

**Evidence.** `VALIDATION_MATRIX.md` row M5 (`IN_PROGRESS`); `ASSUMPTIONS.md` A-AI-1…A-AI-9;
`docs/negative_results.md` NR-17, NR-18; `results/M5/M5-ABL-20260920T141724Z/README.md`.

**What remains.** Re-run `make doe && make optimize` under the corrected heating model, then
`make ablation` once, then write the qualitative audit against that run ID and run the replay.
Blocked on the CFD gate for the fidelity the study should ideally use.

---

## 7. Uncertainty analysis

**Status: NOT MET. The study has not been run.**

The harness is built and every piece of it that can be checked against a closed form has been:
Wilson intervals against their own algebra, Clopper–Pearson at zero events against
1 − α^(1/n), percentiles against the order statistic that defines them, and the whole
propagation chain against a toy linear model with analytic moments. Aleatory and epistemic
uncertainty are separated by the sample shape rather than by a post-hoc split. Every input
carries a source line and a tier, and the loader refuses a judgement-tier input whose source
line does not say so, and refuses the run outright when a required piece of evidence does not
exist.

The runner currently **refuses to start**, correctly, because the design-of-experiments
screening is void for the current design space.

**Two honest qualifications that will survive the run.** Seven of nine active inputs are
engineering judgement. And every distribution the study produces is a **lower bound** on the
real uncertainty, because the heating model form, where catalycity alone is worth about a
factor of two, has no distribution attached and is not in the inventory at all.

**Evidence.** `VALIDATION_MATRIX.md` row M7; `docs/theory/uncertainty.md`;
`ASSUMPTIONS.md` A-UQ-*; `results/M7/M7-SMOKE-*` (labelled, publishing nothing).

**What remains.** `make doe && make optimize`, then `make robust`, then `make uncertainty`.
Read the shortcut verification first; if it misses its declared tolerances the front is the
output of an unverified approximation and must be read that way.

---

## 8. Blind experimental prediction

**Status: NOT MET. Needs the student. No coupon has been printed and no measurement exists.**

The support package is complete: printable holder, dimensioned sensor drawing, data schema,
safety and calibration protocol, calibration and comparison code, and the archived-prediction
machinery the specification requires. The calibrate → freeze → predict → archive → measure →
compare chain has been verified end to end against **synthetic data generated by this
project's own solver**, which is a check on the software and nothing else.

That check was not wasted. It found four traps that would have been invisible in the real
experiment, because the calibration would have fitted beautifully and the parameters would
still have been wrong: contact resistance is weakly identifiable under a prescribed flux; a
short calibration step leaves conductivity and specific heat degenerate; peak metrics are
estimator-dependent and the obvious remedy does not work; and the "seeded" synthetic fixture
was not reproducible between processes.

**Evidence.** `VALIDATION_MATRIX.md` row M8 (`IN_PROGRESS`);
`experiments/thermal_coupon/`; `docs/negative_results.md` NR-11.

**What remains, and it is physical work.** Print the coupon and holder. Instrument it. Run the
dedicated steady-state contact-resistance measurement. Run the calibration step for two to
three diffusion times, about an hour per run. **Declare the comparison tolerance before the
runs**, per the protocol. Freeze the model, generate and archive the prediction for the unseen
heating history, then run that case and compare. The single biggest schedule item is the
calibration step duration, which is not compressible.

---

## 9. External technical criticism, if available

**Status: NOT MET. Needs the student. No review has been requested or received.**

Three review forms exist (assumptions, CFD and validation, final research defence), each with
sections for criticism, student response, changes made and unresolved issues, together with a
cover note carrying a 30-minute reading guide and an explicit warning list of the weaknesses
already known, so a reviewer does not spend an hour rediscovering them.

There are no reviewer names in the repository and no invented, paraphrased or reconstructed
reviews. If a section is empty, it is empty.

**Evidence.** `docs/external_reviews/` (README, three forms, cover note template).

**What remains.** Ask someone. The specification says "if available", so this item can be
honestly closed as unavailable, but that would be the weakest of the twelve outcomes and it is
the cheapest to improve. R1 needs no CFD background: a physics teacher or an engineer in any
discipline can attack the assumptions, and the assumptions are where the project is most
likely to be wrong. One review done properly beats three skimmed.

---

## 10. Negative results

**Status: MET.**

Twenty-four entries, including the ones that are embarrassing and the ones whose evidence is a
scratch run that no longer exists, labelled as such rather than quietly omitted. Failed and
rejected runs stay on disk: an aborted study directory with a README saying it must not be
analysed, two aborted dry runs, an abandoned validation run, and six rejected CFD cases that
are listed in the milestone report and are not in the surface.

Three carry the most weight and are in the paper rather than an appendix: the optimiser
exploiting the heating model and the fix moving the exploit to the shoulder; the heating
constant deliberately not changed after being re-derived; and a project-defined metric
discarded against a criterion declared beforehand, whose pre-registered mechanism turned out
to be half wrong in the more interesting half.

**Evidence.** `docs/negative_results.md` (NR-01…NR-24);
`reports/final/sections/07_negative_results.md`.

**What remains.** Nothing for this item. Keep adding as the remaining studies run. The rule
that has made this work is that a negative result is written when it is found, not at the end.

---

## 11. Stranger reproducibility

**Status: PARTIAL.**

Strong for the Fidelity-0 chain, which is deterministic with no random sampling, so repeated
runs on one commit give bit-identical candidate files. Every run writes an immutable config
snapshot with its run ID, config hash, git commit, dirty-tree flag and timestamp. Reports are
generated from result files and hand-editing one is overwritten by the next run. Two
guarantees are enforced by code rather than care: a long run hashes the physics package at
launch and aborts if it changes, and a study refuses to start on a screening made for a
different model. The language-model study is replayable without model access.

Weaker where it is honest to be weak: CFD needs OpenFOAM, and the version actually used is
v2512, not the v2606 the specification names. Wall times were measured on one laptop, often
while other work was running.

**Evidence.** `REPRODUCIBILITY.md`; `docs/submission_package/reproducibility_links.md`.

**What remains.** Three concrete defects, none of them large:

1. **A numeric discrepancy.** `REPRODUCIBILITY.md` describes the sweep as 27 points while the
   M1 report says 41 candidates over the same range. One is stale. Resolve against the
   committed config and the stored candidate file, and fix the wrong one. This is exactly the
   kind of thing a stranger trips over first.
2. **Several reports carry a "dirty working tree" flag** in their header, which is honest but
   should not be true of the final artefacts.
3. **No public location yet.** The repository needs to be public or archived with a DOI at a
   specific clean commit before anything cites it.

---

## 12. Clear student intellectual ownership

**Status: NOT MET. Needs the student. This is the item nobody else can discharge.**

The infrastructure for it is unusually good. `AI_USAGE.md` classifies work into four
categories and tracks review status honestly. `docs/defense_questions.md` carries 49 questions
with model answers, evidence paths and follow-ups, and marks the ones that depend on unrun
studies rather than inventing answers. `docs/research_story.md` records how the question
actually developed, including the entry stating that the framing came from a specification
rather than from an observation made here.

And the substance is not there yet, for one measurable reason. The package is **21 150 lines
of Python with 5908 lines of tests**, nearly all added on 2026-09-20, and almost none of it
has been read line by line. Rows in `AI_USAGE.md` marked *review pending* are exactly that.
Fourteen AI-proposed decisions await real approval rather than inheritance, several of which
change a physical model or decide what will happen in a laboratory.

**Evidence.** `AI_USAGE.md`; `docs/ai_usage_proposed_update.md` (every new component, all
unreviewed, with a prioritised reading order); `docs/defense_questions.md`.

**What remains.** The reading order in `docs/ai_usage_proposed_update.md` puts about **16
hours** of real reading between the current state and "I can explain every result and every
physical decision". That is four to six sittings. It is not negotiable down by reading faster;
it is negotiable down only by deciding that some results will not be defended, which is a
worse trade.

Two things to do while reading rather than afterwards: move rows from *review pending* to
*student-reviewed* on the day each file is finished, because a batch update at the end is a
guess; and attempt the matching defence question before opening the file, then check, because
reading code to confirm an answer sticks and reading it to absorb one does not.

---

## Summary

| # | Item | Status | Blocked on |
|---|---|---|---|
| 1 | Non-obvious research question | **MET** | — |
| 2 | Falsifiable hypotheses | **MET** | — |
| 3 | Verified implementation | PARTIAL | CFD mesh study (compute) |
| 4 | Independent validation | PARTIAL | CFD benchmark; heating model form; the experiment |
| 5 | Burn-vs-bake result | **MET** at Fidelity 0 | Fidelity-1 re-run |
| 6 | Fair AI ablation | NOT MET | DOE re-run, then one study |
| 7 | Uncertainty analysis | NOT MET | DOE re-run, then two studies |
| 8 | Blind experimental prediction | NOT MET | **the student**, physically |
| 9 | External technical criticism | NOT MET | **the student**, asking someone |
| 10 | Negative results | **MET** | — |
| 11 | Stranger reproducibility | PARTIAL | three small fixes, then archiving |
| 12 | Student intellectual ownership | NOT MET | **the student**, ~16 hours |

**The one sentence this file exists to make unavoidable:** every remaining item except two is
either compute or the student's own hands, and the two hardest, the experiment and the
reading, cannot be bought with either more model time or a better report.

---

## Five things only the student can do

Ordered by how much of the gate they unlock.

1. **Read the code.** About 16 hours, order given in `docs/ai_usage_proposed_update.md`.
   Unlocks item 12 and most of a viva.
2. **Run the thermal coupon.** Print, instrument, calibrate against the protocol's timing
   requirement, declare the tolerance first, freeze, archive the prediction, measure. Unlocks
   item 8 and materially strengthens item 4.
3. **Decide the deceleration limit.** Option A relabels 12 g as an emergency envelope and
   keeps a feasible region of 15% of the grid; option B adopts the documented
   duration-dependent curve and empties it. It is the single assumption with the most leverage
   over the feasible region, and it is an engineering choice about what vehicle this is.
4. **Ask one person for a review.** R1 needs no specialist background. Unlocks item 9, which
   is currently the cheapest NOT MET on the list.
5. **Approve or reject the fourteen AI-proposed decisions** in
   `docs/ai_usage_proposed_update.md`. Several change a physical model; inheriting them
   silently is the failure mode item 12 exists to prevent.
