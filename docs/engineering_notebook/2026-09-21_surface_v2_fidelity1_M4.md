# 2026-09-21 — After G4 PASS: drag surface v2, the evaluator at Fidelity 1, and M4 on the final physics

*Written at the end of the session from the run logs and result files named below. The
"Hypothesis / Expected" sections record what was expected before each step ran; where an
expectation was wrong, it is left wrong.*

## Question

Gate G4 passed (NR-25). Three things had been waiting on it: (1) can the six capsule cases M3
had to reject (NR-21) be recovered with the lever that cured M2's fine meshes, and can the
surface be taken above Mach 20, where most of the heat load is; (2) does anything still carry a
hand-typed `IN_PROGRESS`; (3) what happens to the Pareto front, to the metric-gaming exploits
and to H1 when drag finally depends on shape and the nose model is the corrected one?

## Hypothesis

1. All six NR-21 cases are M2-style bounded limit cycles and a lower Courant number will
   recover them. *(Wrong for two of six.)*
2. Mach 27 will run for blunt shapes (the equations only contain M and γ) and may fail for
   some shape at start-up, as Mach 20 did in NR-19. *(Right about blunt shapes; the failure
   was not a start-up problem.)*
3. Extending to Mach 27 will change C_D by about the 1–2% seen between Mach 10 and 20.
   *(It was smaller: ≤ 0.74%.)*
4. With shape acting on drag, the screening will free the shoulder ratio and the front will
   pile onto its sharp bound — the exploit the last round predicted. *(Wrong, and the way it was
   wrong is the most useful finding of the day.)*
5. H1 will survive, because the trade-off is driven by entry steepness, which Fidelity 1 does
   not change.

## Action

1. `design_points.py`: a Courant pass (M2's block numbers, copied) and a Mach-extension block,
   both declared in `configs/cfd_design_points.yaml` with the date and what had been seen.
   Points are appended; a test pins that no v1 id, fill point or held-out point moves. v1's
   tables were frozen into `results/M3/M3-DP-20260920T1610Z/v1_tables/` first.
2. Five typed gate labels (design_points, surface_build, m3_coupled, the figure captions, the
   M3 driver's run note — the brief knew of three) replaced by reads of
   `gate_assessment.json`. `cfd_surface_v2` registered beside v1; a test greps the source for a
   typed status.
3. GCI hook extended to pass the rebuilt file's labelled iterative columns through.
4. Surface rebuilt, `make m3-coupled`, design space switched to `cfd_surface_v2`, legacy
   bit-identity tests re-run.
5. `make doe` (with a new pre-flight: hull coverage measured, Saltelli sub-box verified inside
   the hull), hypervolume reference checked against the DOE and the decision written to a file
   BEFORE `make optimize`, then `make optimize`, the audit, and labelled probes.

## Expected vs observed

| | expected | observed |
|---|---|---|
| NR-21 retries | 6 of 6 | **4 of 6** (dp001, dp032, dp043, dp053). First pass said 6 of 6; dp011 and dp061 had passed in ONE window after windows that failed — block means alternating by 0.45%. Rule made explicit (two passes in a row), cases resumed, both failed. NR-27. |
| hull | wider | valid shapes inside the hull **92.0% → 99.8%** (dp001, the slender Mach-20 corner, did that) |
| Mach 27 | blunt shapes run | **9 of 14**. Slender 20° cones die 28–85 iterations after the hand-over to van Leer whatever the start length (1500/6000) or Courant number (0.2/0.1); first-order alone is stable. Only the limiter is left to change, and that is the validated scheme — not changed. NR-28. |
| C_D change Mach 20 → 27 | 1–2% | baseline +0.007%, M4-front shape +0.10%, 60° cone −0.74% |
| heat load above the top node | small | **53.7–66.5% → 0.0–2.9%** |
| surface CV | similar | k-fold RMSE 0.0249 → **0.0130**; held-out 7 → 8 usable, RMSE 0.0270 → 0.0234; sigma inflation 1.65 → 1.21 (max of pooled 1.13 and core-only 1.21); held-out z-spread 1.70 — still overconfident on n = 8 |
| G5 | PASS | PASS (software gate; scope stated in the matrix) |
| screening | shoulder freed | **frozen again** (S_T upper bound 0.0048) |
| front on the sharp shoulder | yes | **no — but only because of the freeze.** Probes: R_c/D 0.10 → 0.02 is worth −16.6 to −19.9 kW/m² (≈7%) and −3.1 to −3.9 K at the front. NR-29. |
| hypervolume | — | NSGA-II 0.3467 ± 0.0055, scalarised DE 0.2997 ± 0.0150, LHS 0.2874 ± 0.0214; combined front 78 designs, 0.3514 |
| H1 | survives | peak-flux-only 2.295×10⁵ W/m² / 418.4 K; knee 2.510×10⁵ W/m² / 403.5 K; bondline-only 2.783×10⁵ W/m² / 391.7 K |

## Evidence

`results/M3/M3-DP-20260920T1610Z/` (`attempts_coarse.csv`, `cases/*_Co0p*/restart_blocks.json`,
`driver_coarse_v2.log` vs `driver_coarse_v2_consecutive.log`, `surface_summary_coarse.json`,
`diagnostic_window_mean_agreement_coarse.csv`, `coupled/`, `v1_tables/`);
`results/M3/mach27-startup-exp/`; `data/aero/cfd_surface_v2/` (hash `b63b68a40321f38b`);
`results/M4/M4-DOE-20260920T204844Z/` (`f1_hull_coverage.json`, `hv_reference_check.json`,
`screening.json`); `results/M4/M4-OPT-20260920T205252Z/` (`summary.json`, `audit_probes.csv`);
`results/M6/M6-DRY-20260920T210333Z/` (dry run, not a result); reports M3 and M4 and their
archived predecessors; NR-27…NR-30.

## Interpretation

* **The pipeline can game its own metric.** The most dangerous moment of the day was a log that
  read "6 of 6 USABLE". Nothing had been tuned; the restart code simply stopped at the first
  passing window, and a slowly oscillating case will always offer one eventually. A convergence
  criterion judged on one window is a lottery ticket if you are allowed to keep drawing.
* **A sensitivity index is not an exploitability index.** The freeze rule kept the sharp-shoulder
  exploit out of M4 by accident: diameter's variance drowned a lever worth 7% at the optimum.
  The rule is kept — changing it after seeing this would be tuning — but it is now labelled for
  what it is, and any study that frees the shoulder needs a corner-heating model first.
* **Fidelity 1 did not make shape matter where the optimiser lives.** C_D at peak heating varies
  by 0.1% across the front. Diameter is set by the mass fence (TPS = 98.9% of vehicle mass at
  the knee — not a capsule), bluntness by the CFD hull standing where the old cap stood, cone
  angle by a 1.4° validity window. The front is a flight-path-angle burn-versus-bake curve at a
  fenced geometry. H1 holds in absolute terms for that reason and for no grander one.
* **Mach 27 closed an extrapolation in Mach, not the model-form error.** The ±5% band stays.

## Next

* M5, M6, M7 pass their precondition checks (`scripts/check_study_preconditions.py`; M6 dry run
  completes on v2). They hash `src/aether` at launch: tree hash at the end of this session
  `c0a44bb0c14acd88` — launch them only while nothing edits `src/`.
* The thing that would change the M4 picture is not more optimisation: it is a sourced mass
  budget (A-OPT-6) and a corner-heating model (NR-29). Both are sourcing tasks.
* M7 must propagate the ±20% effective-nose-radius band before anyone leans on the 14.9 K.
* Not touched this session and now stale in places: `docs/defense_questions.md`,
  `docs/final_quality_gate.md` (both still describe every optimisation number as Fidelity 0),
  `PROJECT_STATUS.md`, `AI_USAGE.md`.
