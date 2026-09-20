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

---

# 2026-09-21 addendum — the study, run once on the final physics (Fidelity 1)

The title of this entry says Fidelity 0 because that is what existed when the harness was
built. The study itself ran after gate G4 passed and DOE/M4 were re-run on `cfd_surface_v2`.
The hypotheses above were written before it and are scored below as written.

## Action

`make ablation` once, detached: run `M5-ABL-20260920T211134Z` (git `bf4f9a3`, dirty tree,
source hash `c0a44bb0c14acd88`, DOE `M4-DOE-20260920T204844Z`), concurrently with the M6 and
M7 studies on a shared machine, 6 workers. 1 h 35 min wall. Then
`make ablation-replay RUN_ID=… STRICT=1` (run `M5-REPLAY-20260920T224633Z`), the qualitative
audit, and `make ablation-report`. Nothing under `src/aether` or `configs/` was edited.

## Observed

All numbers from `results/M5/M5-ABL-20260920T211134Z/summary.json`.

| method | HV @ 200, mean ± s.d. (n = 5) | HV @ 50 | HV @ 100 | feasible / 200 | front size |
|---|---|---|---|---|---|
| `lhs_search` | 0.2524 ± 0.0171 | 0.1342 | 0.2131 | 8.2 | 2.2 |
| `nsga2` (pop 40) | 0.2803 ± 0.0253 | 0.2272 | 0.2417 | 60.4 | 3.4 |
| `nsga2_pop20` | 0.2753 ± 0.0381 | 0.1248 | 0.2256 | 106.6 | 3.8 |
| `bo_parego` | 0.3520 ± 0.0011 | 0.3145 | 0.3465 | 103.0 | 7.8 |
| `ai_agent` | 0.3556 ± 0.0000 | 0.3428 | 0.3550 | 163.8 | 72.4 |

- Pre-declared rule, best conventional = `bo_parego` at every checkpoint: **AI helped at 50**
  (+0.0283, A12 0.88, Holm p 0.0278) **and at 100** (+0.0085, A12 1.00, Holm p 0.0119);
  **no measured difference at 200** (+0.0036, A12 1.00, Holm p 0.0119: the test rejects, the
  gain is under the declared 0.005).
- M4's NSGA-II needed 1000 evaluations for 0.3467 ± 0.0055; M5's `nsga2` reproduces M4's
  first 200 evaluations on the shared seeds exactly.
- LLM calls: **67** (47 `ai_agent`, 20 `ai_adaptive`; planned 63, cap 80); 0 failed, 0
  malformed; mean 177 s a round; 1.0 M tokens in, 1.1 M out. Rejections: 37 of 937
  (`ai_agent`), all duplicates or no-change; **none out of bounds**; no LHS fallback.
- Strict replay with no LLM access: 0 prompt mismatches, same source hash, every method's
  per-seed hypervolume identical.
- The agent stated M4's structural finding (a one-parameter front in entry angle at a corner
  fenced by the mass fraction, the CFD hull and the 70° bound) by its third to fifth round in
  every seed, recovered the analytic geometry-validity rule exactly from failure messages in
  three of five seeds in round 1, and had the direction of change right on 93 % of its
  round-1 predictions, which it attributed to Allen–Eggers / Sutton–Graves priors.
- 65 of 900 accepted proposals returned no physics; 20 of them are one round (seed 37, call 2;
  NR-32). 195 of its 1000 paid designs are near-repeats of earlier ones.

## Interpretation

Hypothesis 1 (NSGA-II trails at 50 and 100): held. Hypothesis 2 (agent leads early, on
priors): held, and the audit says so in the agent's own words. Hypothesis 3 (agent and
`bo_parego` within seed noise at 200, test cannot separate them): **wrong as written.** The
gap at 200 is small (0.0036) but it is three times `bo_parego`'s seed s.d. and the exact test
separates the samples completely; what the rule says is that the gap is below the size
declared worth calling a gain. Hypothesis 4 (boundary overshoot, low diversity): half right.
Diversity is the lowest of any method (0.31 against 0.60); the overshoot was never of the
*box* (no out-of-bounds proposal) but of the validity and hull boundaries.

What the result is: on an easy landscape (one real trade-off, monotone free improvements)
an LLM with aerospace priors reaches a mean hypervolume of 0.345 at 60 evaluations and
0.350 at 80, where the GP optimiser (same initial design, 0.1002 for both at 20) needs 100
and 150 and NSGA-II reaches neither in 200. What it is not: evidence that
the agent reasons from data better than a surrogate does (priors and the failure-message
asymmetry are not separable here), evidence about a harder landscape, or a located optimum.
About half of the final lead is precision on two limits M4 calls placeholders. n = 5, one
model, one run of a sampled method.

## Next

1. When no study is running: fix the three generator sentences of NR-31 (CFD-call count,
   `ai_adaptive` wording, conditional power sentence) and re-run `make ablation-report`; the
   numbers will not change.
2. If M5 is ever re-run (it should not be re-run to get a different verdict): carry the
   agent's `observation` forward between rounds, and report a stand-off hypervolume beside
   the raw one (NR-32).
3. M6 fills in the `ai_adaptive` row; its two seeds here are plumbing (0 of 360 promotions
   granted) and are in no comparison.
