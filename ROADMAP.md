# Roadmap

Scope is frozen (spec §2, §42). This roadmap sequences the frozen scope; it does not extend
it. No new physics subsystem is added unless it is needed to resolve a demonstrated
validation failure in O1.

Updated 2026-09-21, at commit `de2a834`. All simulation work is done. **What remains is
almost entirely the student's**, and the project is not complete by spec §53 until it is
done (`docs/final_quality_gate.md`).

## Done

- **M0** Repository, provenance, config schema, test harness, plotting standards.
- **M1 / M1b** Burn-vs-bake demonstration. H0 supported in the tested domain; H1 supported at
  Fidelity 0. Legacy-model numbers (constant C_D).
- **§44** Thermal Penetration Index: built, tested against a criterion declared first,
  discarded (NR-10).
- **Sourcing pass**: Sutton–Graves constant re-derived and deliberately unchanged (NR-12);
  upper-atmosphere table checked at five altitudes; trajectory validated against a published
  comparison; bondline allowable sourced; the 12 g limit found to match no document.
- **M2** OpenFOAM validation. Gate G4 PASS, having first read LIMITED (NR-25).
- **M3** CFD drag surface `cfd_surface_v2` (69 usable cases, Mach 3–27, coarse mesh) and the
  effective-nose-radius correction (NR-15). Gate G5 PASS as a software gate; surface LIMITED.
- **M4** DOE and Pareto optimisation at Fidelity 1. H1 supported, narrowly (NR-29, NR-30).
- **M5** AI ablation: helped at 50 and 100 evaluations, no measured difference at 200.
- **M6** Adaptive fidelity: **H2 not supported** (NR-35).
- **M7** Uncertainty propagation, attribution, robust design, §39 table with a like-for-like
  robust column.
- **M8 support package** and synthetic software check (NR-11). *Not the experiment.*
- **M9 draft**: `reports/final/AETHER_paper.md`, the filled submission package,
  `reports/final/HANDOFF.md`.

## What remains, in order

Time estimates are the ones already in the repository; where none exists, none is given.

### 1. Read the code (student; about 16 hours, four to six sittings)

Order and per-file hours in `docs/ai_usage_proposed_update.md`. Tier 1, about 6 hours, is
`evaluate.py`, `tps/conduction1d.py`, `geometry/stagnation_gradient.py` with its theory note,
and `heating/sutton_graves.py` with its theory note. Move each `AI_USAGE.md` row to
*student-reviewed* on the day its file is finished. Attempt the matching defence question
before opening the file. Closes quality-gate item 12, with step 6.

### 2. Make the three waiting decisions (student)

- **The deceleration limit**: option A (keep 12 g, relabel as an emergency envelope) or
  option B (NASA-STD-3001 duration curve; needs a new pulse-duration metric; empties the M1b
  grid at 8 g). `ASSUMPTIONS.md`, under A-LIM-1b.
- **The twenty-two AI-proposed decisions** in `AI_USAGE.md`: approve or reject each.
- **The coarse-mesh drag surface**, and with it G4's after-the-fact restart rule: accept, or
  run the all-medium design (estimated about 8 h of CFD, `REPRODUCIBILITY.md`).

Option B, or rejecting the surface, means new computation and a new pre-declared study, not
an edit to existing results.

### 3. Run the thermal coupon experiment (student; physical)

`experiments/thermal_coupon/protocol.md`. Choose polymer, heater and sensors; size the
matched-energy pair with `design_cases.py` before printing; print coupon, spare and holder;
two-point sensor calibration; calorimetric flux calibration; steady-state contact-resistance
run; cool-down run; long step run (two to three diffusion times, about an hour for a 10 mm
coupon, the largest single time cost). **Declare the tolerance and commit it before the
validation runs.** Freeze, predict both cases, commit and push; run each case at least twice;
compare. Then fill paper §14.3, move matrix row M8, and record whatever went wrong. Closes
quality-gate item 8 and strengthens item 4.

### 4. Ask one person for a technical review (student)

`docs/external_reviews/`. R1 (assumptions) needs no CFD background. Record criticism,
response, changes made and unresolved issues. Do not name a reviewer without permission.
Closes quality-gate item 9.

### 5. Small repository fixes (student or assistant, on request)

**Fixed in the 2026-09-21 consistency sweep**, not re-listed here in detail:
`REPRODUCIBILITY.md`'s test count, Fidelity-1 status, ablation-completion status and the
`make uncertainty-report` warning; `VALIDATION_MATRIX.md`'s M1 row, closing "Supported / Not
supported" paragraphs, M6/M7 harness-row wording and the §44 NR-05→NR-10 pointer; every
`1.65` sigma-inflation mention outside a dated historical record (now says `cfd_surface_v2`
uses 1.21); `AI_USAGE.md` standing rule 5's line counts (re-measured: 23,869 / 6,587); the
twenty-two-vs-fourteen AI-proposed-decision count, reconciled across `AI_USAGE.md`,
`docs/final_quality_gate.md`, `docs/submission_package/authorship_and_ai_disclosure.md`,
`reports/final/HANDOFF.md` and `reports/final/AETHER_paper.md`.

**Still open:**
- `docs/defense_questions.md`: several main answers still describe the Fidelity-0 state
  (out of scope for the 2026-09-21 sweep, which only fixed the sigma-inflation answer).
- Check four method citations against library copies: Celik et al. (2008) against
  `cfd/gci.py`; Billig's exponent (3.24 or 3.2); Carslaw and Jaeger §2.9; the Saltelli and
  Jansen estimators.
- The contradictory Tauber TP-2914 provenance record is **not resolved** — a dated note was
  added to both `docs/engineering_notebook/2026-09-20_effective_nose_radius.md` and
  `docs/validation/sourcing_report.md` stating the contradiction and that no claim rests on
  it, per NR- style practice of not picking a side without opening the document. Only opening
  TP-2914 closes it.

### 6. Revise and own the paper (student)

The paper and the submission package are AI drafts. Rewrite in his own words, checking each
number against the file named beside it. Then record the 90-second explainer and the video in
his own voice.

### 7. Release

Choose a public location or an archive with a DOI; tag a clean commit; state that commit in
the paper, the brief and the poster. The milestone reports' dirty-tree flags can only be
cured by re-running from that clean commit.

## Not planned, and why

- **Running the `ai_adaptive` arm.** Needs the student's authorisation for live LLM calls. M6
  found that extra CFD buys nothing in this design space, so the arm would very likely be
  uninformative here.
- **Re-scoring M6 against a reachable target.** That would be a new pre-declared study. The
  criterion as written has returned its verdict and stays.
- **Freeing the shoulder ratio.** Not before the model has a corner-heating correlation or a
  sourced minimum corner radius; otherwise the box bound is the answer (NR-29).
- **Quantifying gate G2′** (catalycity, hot wall, radiation) and closing the rest of G1A′.
  Both matter more than anything else left in the model and both are blocked on sources that
  could not be obtained.
- **Crank–Nicolson.** An open item since M1. At a measured median of 0.150 s per coupled
  evaluation it was not the bottleneck of any study that ran.
