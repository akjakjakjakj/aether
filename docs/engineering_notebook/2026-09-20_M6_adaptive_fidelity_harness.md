# 2026-09-20 — M6: adaptive-fidelity harness (built and smoke-tested; study NOT run)

## Question
Who should get the next CFD case? Spec §26 asks for a policy that promotes a candidate from the
cheap evaluator to OpenFOAM on predicted Pareto value, uncertainty, novelty and cost, and H2 asks
whether that saves CFD calls against unguided use of the same budget.

## Hypothesis
(H2, untested here.) A policy that spends CFD where a design matters AND the drag surface is
untrusted reaches a given fraction of the reference hypervolume with fewer calls than random
promotion, greedy promote-the-best, or an up-front space-filling design.

## Action
- Defined the fidelities as the coordinator specified: F0 = `evaluate_design` on the arm's current
  GP drag surface; F1 = a real OpenFOAM case through M3's design-point runner, added to the arm's
  training set, surface refitted, candidate re-evaluated (A-AF-1).
- Built `optimization/adaptive.py` (two-budget evaluator, CFD ledger and case store, versioned arm
  surfaces, the promotion controller with five strategies), `adaptive_analysis.py` (pooled-truth
  scoring, H2 rule), `adaptive_study.py`, report and figure generators, `configs/adaptive_fidelity.yaml`
  with the policy numbers, study size and success criterion declared, `scripts/run_adaptive_fidelity.py`,
  `make adaptive | adaptive-report | adaptive-smoke | adaptive-dry-run`.
- Factored the NR-18 source-hash and stale-screening guards out of the M5 runner into
  `optimization/guards.py`; both runners use it.
- Wired the M5 LLM agent's `requested_fidelity` into the same promotion queue through the
  `decide_batch` hook it already had; tested from a fake CLI and a strict replay, no live call.
- Thought through how an arm could win without being better (flattering surface, never
  promoting, hull rejection, luck, false claims, free information, truth favouring whoever bought
  CFD) and designed the scoring against each; the list is the docstring of `adaptive_analysis.py`.

## Expected
The pipeline runs end to end with a fake F1; a real promotion goes through M3's runner, the
surface refits and the candidate's objectives move a little.

## Observed
- 24 deterministic tests pass with a fake F1 of known analytic truth.
- Dry runs (fake F1, development seeds 11 and 23, provisional surface) run all five arms, the
  scoring, the hold-out step, three figures and the report. They are not results.
- **Buying one CFD point turned evaluable designs into "extrapolations"** (NR-23): a design with a
  variable at a box edge sits 2e-16 outside a hull facet, and Qhull's default tolerance made its
  membership depend on the triangulation. Fixed with an explicit tolerance in `TrainingHull`.
- The source guard aborted two dry runs because another work-stream was editing
  `src/aether/uncertainty` (NR-24). Added a verified exclusion for smoke/dry runs only, and
  `--reuse-cfd` so an aborted study does not lose its finished CFD cases.
- First real smoke attempt spent 0 CFD calls (greedy arm, nothing feasible in 40 evaluations).
  Second attempt, random arm (`M6-SMOKE-20260920T180010Z`): 2 OpenFOAM cases, one at a time, both
  USABLE by M3's unchanged rules; surface 56 → 57 → 58 points; both promoted candidates
  re-evaluated; 38 + 2 = 40 evaluations, 2/2 calls.

## Evidence
`tests/test_adaptive_fidelity.py`; `results/M6/M6-SMOKE-20260920T180010Z/` (`promotion_log.json`,
`cfd_calls.csv`, `cfd_cases.csv`, `cfd/cases/`, `surfaces/random/seed_11/v000..v002`);
`results/M6/_dev/*.log`; NR-23, NR-24; ASSUMPTIONS A-AF-1..10.

## Interpretation
The harness does what it says. Nothing here says anything about H2. Two things learnt that the
study design now reflects: CFD calls are spent WHILE the search runs, so "calls to reach the
target" conflates CFD with search progress (the figure shows both axes and the report says so);
and on the current surface the development dry runs never produced an out-of-hull candidate, so
hull extension may simply not come up — if the no-CFD arm reaches the target the pre-declared
verdict is NOT_TESTABLE, not a win for anybody.

## Next
Coordinator: after G4 = PASS, rebuild the surface under the PASS gate, switch
`configs/design_space.yaml` to `cfd_surface_v1`, re-run `make doe` and `make optimize`, then
`make adaptive` in the background (4–5 h) with no other work-stream editing `src/aether`.
