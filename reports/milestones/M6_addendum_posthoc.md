# M6 addendum — what the H2 verdict means, and what the generated report does not say

Companion to `reports/milestones/M6_adaptive_fidelity.md` (generated; `make adaptive-report`
reproduces it byte-for-byte). Written by hand on 2026-09-21. Every number is read from
`results/M6/M6-AF-20260920T211148Z/` (`summary.json`, `curves.csv`, `cfd_calls.csv`,
`cfd_cases.csv`, `reference_front_shapes.csv`, `candidates.csv`); nothing was tuned, and the
pre-declared criterion was applied exactly as `configs/adaptive_fidelity.yaml` states it.

## 0. Scope of this run

* `make adaptive SKIP_LLM=1`. **The `ai_adaptive` arm was not run**: it is exploratory and
  outside the H2 criterion by the config's own declaration, and its live LLM calls were not
  authorised for this run. LLM calls: 0. The generated report's §8 still carries a sentence
  about `ai_adaptive`; read it as "declared, not run here". H2's "AI-guided" clause is therefore
  untested by this study.
* Source hash `c0a44bb0c14acd88`, git `bf4f9a3`, coarse mesh, gate G4 PASS at build and at run.
* Wall time **3 h 43.6 min** (13,414 s) on a 10-core fanless machine shared with M7 (4 workers)
  and M5, load average 6–77. 134 CFD calls charged, 125 cases run (120 promotions + 5
  hold-outs; 134 charged calls map onto 120 distinct cases, i.e. 14 requests were served by a case
  another arm-seed had already paid for — each is still charged), 114 usable, **11 failed and kept on record** (§4). 10.65 core-hours of CFD,
  median case 156 s.

## 1. The verdict, as declared

**H2 @ 95% of the reference hypervolume (target 0.3264): NOT_SUPPORTED** — `adaptive` reached
the target in 0 of 5 seeds (needs 3); no arm reached it. Sensitivity (not the criterion):
90% → NOT_SUPPORTED (reached by `greedy` 1 seed, `upfront` 2 seeds, `adaptive` 0, `f0_only`
0); 98% → NOT_SUPPORTED (nobody).

It is NOT_SUPPORTED and **not** NOT_TESTABLE: the config reserves NOT_TESTABLE for the no-CFD
arm *reaching* the target, and it did not. But the practical meaning is close to it, for a
reason the config did not anticipate (§2).

## 2. Why nobody reached the target: the F0 search budget, not the drag model

* **The target was out of reach of the study's own search budget.** The reference (0.3436) is
  set by the dedicated 2 × 1000-evaluation search on the truth surface. *All 25 arm-seeds
  pooled* — 5000 evaluations — reach 0.3234 = **94.1%** of it, below the 95% target. The best
  single arm-seed (`greedy`, seed 37) reached 0.3217 = 93.6%. No allocation of 8 CFD calls
  could have moved a 200-evaluation search over that line.
* **The searches never got to where the front is.** The 18 reference-front shapes have
  R_n/D = 0.999–1.133 and cone half-angle 65.0–69.6°. The largest bluntness any arm ever found
  feasible in 200 evaluations: `adaptive` 0.931, `greedy` 0.879, `random` 0.846, `f0_only`
  0.896, `upfront` 0.984. So the promoting arms bought CFD where their search *was*:
  `adaptive` at R_n/D 0.478–0.875, `greedy` 0.478–0.875, `random` 0.251–0.767. **Not one of
  their 94 calls was at R_n/D ≥ 1.0.** Only `upfront`'s space-filling design put any there
  (3 of 40).
* **The seed decides the score, not the arm.** Two-way split of the 25 final truth
  hypervolumes: seed 68.7% of the variance, arm 10.6%, residual 20.7%. Seed 73 ends at 0.2165,
  0.2165 and 0.2168 for `adaptive`, `greedy` and `f0_only` — the same stalled search,
  whatever was bought.
* **Extra CFD does not change what the designs are worth.** `f0_only`'s recommended sets score
  0.2753 on the starting 69-point surface and 0.2754 on pooled truth (178 points): 109
  additional CFD points moved it by 0.0001. The largest mean optimism gap of any arm is
  0.0004; **false claims: 0 for every arm and seed**; selection regret 0. The starting surface
  was already accurate where the objectives are decided — consistent with M4's finding that
  C_D at peak heating varies by ~0.1% across the front, and with M7's Sobol' result that the
  GP surrogate term carries ≤ 0.02 of any output's variance.

## 3. What the arms' scores do and do not show

| arm | truth HV mean ± sd | CFD calls (mean) | failed | final-surface RMSE vs truth |
|---|---|---|---|---|
| `upfront` | 0.2972 ± 0.0262 | 8.0 | 0.6 | 0.0061 |
| `adaptive` | 0.2835 ± 0.0389 | 3.6 | 0.4 | 0.0091 |
| `greedy` | 0.2823 ± 0.0395 | 7.2 | 0.8 | 0.0087 |
| `f0_only` | 0.2754 ± 0.0375 | 0.0 | 0.0 | 0.0094 |
| `random` | 0.2652 ± 0.0254 | 8.0 | 0.8 | 0.0084 |

* No paired comparison of `adaptive` with any arm is distinguishable from zero at n = 5:
  vs `random` +0.0183 (p = 0.11), vs `greedy` +0.0012 (0.45), vs `upfront` −0.0137 (0.73),
  vs `f0_only` +0.0081 (0.50; better in 1 of 5 seeds). With 5 seeds this is weak evidence of
  equivalence, not proof of it.
* `adaptive` spent **3.6 of 8** calls (18 in total, all at the Mach-20 node — inside the hull
  the Mach rule buys the node with the largest weight × σ, and that was always Mach 20). Its
  gates judged most candidates "already confident". Given §2 that judgement was *correct* —
  more CFD would not have changed the objectives — so the policy's one measurable merit here
  is that it reached the same score as `greedy` on half the calls. That is not the H2
  criterion and is not claimed as support for H2.
* `upfront` has the best mean and the lowest surface error, and is the only arm that changes
  the surface *before* the search. Its lead is not significant, and because a slightly
  different surface also sends NSGA-II down a different path, its lead cannot be attributed
  to accuracy on this evidence.
* `random` is lowest, below `f0_only`: it pays 20.6 of its 200 F0 evaluations as charged
  re-evaluations after refits (`greedy` 14.2, `adaptive` 6.4), i.e. **promotion costs search
  budget** and, here, buys nothing back.

## 4. Failed CFD promotions (kept, charged, no training point)

11 of 125 cases: 10 REJECTED by M2's force-convergence criterion after the full retry ladder
(4 attempts each, 712–2,952 s), 1 SOLVER_FAILED (`rhoCentralFoam` returned −4, Mach 22.2).
Six of the 11 are at Mach 20, R_n/D 0.27–0.77; one is near the front (R_n/D 1.063, 68.5°,
Mach 11.4). Charged failed calls by arm: `adaptive` 2, `random` 4, `greedy` 4, `upfront` 3.
They are in `cfd_cases.csv` with their reasons.

## 5. How wrong is "truth"?

5 hold-out CFD cases (one per arm, fitted by no surface, charged to nobody), all usable:
errors −0.04%, +0.08%, +0.29%, +0.25%, +0.28% of C_D,fore; |z| ≤ 0.88. Largest 0.29%.
**Limits of that check:** all five are at Mach 27 and at the arms' recommended shapes
(R_n/D 0.72–0.98) — it measures truth where the arms made claims, not at the reference front
(R_n/D 1.0–1.13) and not at other Mach numbers. It is a measurement, not a bound.

## 6. Bottom line for H2

**Negative result, stated plainly: in this design space, at this budget, extra CFD bought
nothing measurable, and adaptive allocation of it therefore had nothing to save.** The model
predicts that the objectives are insensitive to the residual error of the 69-point drag
surface, so which designs get CFD is immaterial to the Pareto front; what limits the front an
optimiser finds in 200 evaluations is the search itself. H2 is **not supported** by this
study. It is also not contradicted in general: a design space in which the cheap model is
materially wrong near the front — which this one is not, after M3 — is where H2 would have
something to show, and the study as sized could not have detected it (target above what 5000
pooled evaluations reach; n = 5; "AI-guided" arm not run).

What would make it a test: an F0 budget at which the no-CFD arm gets within reach of the
target (the reference search used 1000), or a target defined relative to what the pooled arms
reach. Either is a *new* pre-declared study, not a re-scoring of this one — the criterion was
written before the run and is left as written.

## 7. Figures against spec §34

| Figure | Verdict |
|---|---|
| `M6_hv_vs_cfd_calls` | Units, legend, run ID, caption: meets §34. No overall title (panel titles only). Panel (a) is easy to misread — curves rise with CFD calls because search progresses while calls are spent; the caption says so and panel (b) is the honest view. |
| `M6_cfd_spend_map` | Meets §34. Shoulder ratio and Mach not shown (stated). This is the figure that carries §2. |
| `M6_surface_error_vs_truth` | Units, run ID, caption present; **no title**. |
