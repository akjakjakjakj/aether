# 2026-09-20 — M5 at Fidelity 0: does an LLM engineering agent beat conventional optimisers under a matched budget?

## Question

Spec §24/§46: under identical evaluation budgets, how does an LLM agent that proposes designs
from structured data compare with a space-filling floor, NSGA-II and a GP-based Bayesian
optimiser — in hypervolume, in how fast it gets there, in feasible designs found, in design
diversity and in cost? And can the comparison be made auditable (every prompt and response
kept) and reproducible by someone with no LLM access (§50)?

## Hypothesis

Written while the full run was in progress, i.e. **after** two development smoke tests whose
outcomes I had already seen and therefore cannot pretend not to know: one seed of `bo_parego`
(seed 11; NR-17) and one 60-evaluation live run of the agent on a non-study seed (7, two LLM
calls, hypervolume 0.384). The success criteria in `configs/ai_ablation.yaml` were written
before either.

1. M4 showed the landscape is easy: one real trade-off (entry angle) and two free
   improvements that each stop at a placeholder fence. Any model-based method should find
   the fences within tens of evaluations; NSGA-II with a population of 40 gets five
   generations out of 200 evaluations and should trail at 50 and 100.
2. The agent will do well early, and for a reason that is not "reasoning from data" alone:
   the variable names tell a model with aerospace priors which way to push before it has
   seen a feasible design. In the smoke test its first response back-computed the constraint
   limits from the margins and said in so many words that it was using "ballistic-entry
   scaling from prior knowledge, checked against the rows".
3. By 200 evaluations the agent and the Bayesian optimiser will be within seed noise of each
   other, because both will be parked on the same fences and the remaining hypervolume is in
   how finely the entry-angle axis is covered. With n = 5 I do not expect the pre-declared
   test to separate them at 200.
4. The agent's failure mode, if it has one, will be proposals just outside a fence or the
   box (it aims at boundaries on purpose) — which the strict validator turns into lost
   evaluations — and low diversity: it will stop exploring once it believes its own model.

## Action

1. `src/aether/surrogate/`: `GPSurrogate` (Matern-5/2, per-input length scales, optional
   log₁₀ output) with a convex-hull extrapolation guard that raises by default;
   `DesignSurrogate` (GP per objective, per constraint margin, least-squares GP validity
   classifier); held-out accuracy and interval-coverage metrics.
2. `optimization/bayes.py`: ParEGO random-Tchebycheff scalarisation, Monte-Carlo EI ×
   probability of feasibility, batches of 10, predictions logged before evaluation.
3. `optimization/ai_agent.py`: prompt builder (structured JSON only), strict §23 schema
   validator (reject, never clip), Claude Code CLI client run in an empty directory with
   tools and project context off, hard per-seed and study-wide call caps, verbatim
   persistence, `ReplayClient`.
4. `optimization/fidelity.py`: the §26 promotion policy as an interface; Fidelity 1 does not
   exist, so promotions are recorded as requested-not-granted.
5. `optimization/ablation.py`: exact permutation and signed-rank tests, A12, Holm; surrogate
   and agent scoring; per-method gaming audit. `ablation_plots.py`, `ablation_report.py`,
   `scripts/run_ai_ablation.py`, `make ablation | ablation-replay | ablation-report`.
6. Tests use a fake CLI executable and replay; none makes a live call.

Budget/seed choice as first launched: **200 evaluations × 5 seeds (11, 23, 37, 41, 59)
for every method**; `ai_adaptive` on two seeds as plumbing only; LLM `claude-sonnet-5`, at
most 12 calls per seed and 80 for the study.

## Expected

See Hypothesis. No expectation is revised here, because nothing was observed.

## Observed

**No study result exists.** The full run (`M5-ABL-20260920T141724Z`) was killed by the
coordinator part-way through the agent phase because the evaluator's physics was changed
under it by a concurrent work-stream (NR-18). No summary was written and no number from it
was looked at. The smoke-run report and figures that had been written to `reports/` by a
development run were deleted so that nothing on disk can be mistaken for an M5 result.

What *was* observed is about the harness only:

- one live development run on non-study seed 7 (60 evaluations, 2 LLM calls) replayed
  strictly: 0 prompt mismatches, identical candidate log and hypervolume;
- the first response in that run back-computed the constraint limits from the margins and
  stated it was using "ballistic-entry scaling from prior knowledge, checked against the
  rows" — an anecdote from one call on a model that has since changed, recorded because it
  is exactly what the qualitative audit will need to look for, not as a finding;
- one LLM round took about five minutes and ~30k output tokens, most of it reasoning;
- NR-17 (two faults in the first Bayesian optimiser, neither visible in hypervolume).

LLM calls spent: 3 in development (1 CLI isolation check, 2 in the seed-7 smoke run) and
24 prompts issued by the aborted run (16 recorded as complete). None can be replayed as a
result.

## Evidence

`tests/test_ai_agent.py`, `tests/test_surrogate.py`; `results/M5/_dev/` (development runs,
labelled); `results/M5/M5-ABL-20260920T141724Z/README.md` (aborted run, do not analyse).

## Interpretation

None about optimisers. About process: a long run in a repository edited by several agents
needs the evaluator frozen by hash, not by a dirty flag read once at launch; and a report
generator must not carry findings as prose. Both are now enforced in code.

## Next

The coordinator runs `make ablation` once, after M3's drag surface lands and `make doe` /
`make optimize` have been re-run. Study seeds are now 37, 41, 59, 67, 73 (11 and 23 were
seen in development). Then: write `reports/milestones/M5_qualitative_audit.md` against that
run ID, run `make ablation-replay`, and fill in the Observed section above.
