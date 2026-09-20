# 2026-09-20 — M7: uncertainty propagation and robust design (harness built, study not run)

## Question

Every AETHER result so far is a point prediction from a model whose own documentation says
it is uncertain: a Sutton–Graves constant carrying the primary's 3.3% average fit error, an
effective nose radius two NASA reports disagree about by ~20%, an atmosphere table that is
interpolated above 86 km where NR-14 measured 5–20% of the bondline's heat load accrues, and
TPS properties that A-TPS-7 calls engineering placeholders. **How wide are the answers, which
piece of not-knowing is responsible, and does the design change once the constraints become
probabilities?**

## Hypothesis

Stated before building, so it can be wrong in public:

1. **The spread will be dominated by EPISTEMIC terms, not aleatory ones.** The aleatory
   inputs are a few percent (mass, density, delivered flight-path angle); the epistemic ones
   are a ±15% band on a placeholder conductivity and a ~20% disagreement about R_eff. If
   true, the actionable output of M7 is a *list of measurements to buy*, not a margin.
2. **The M4 front designs will prove fragile.** An optimiser with no reason to leave margin
   parks on its binding constraint; A-LIM-1b already records the baseline sitting at +0.9%
   on the g limit. Under a chance constraint at α = 0.05 they should stop being feasible.
3. **The effective-nose-radius model form will be the single largest heating term** —
   ±10% on flux against the Sutton–Graves constant's ±4%.

## Action

Built `src/aether/uncertainty/` and the two runners, plus three identity-by-default hooks in
the evaluator. Design decisions worth recording:

**Uncertainty is a coordinate of the design space, not a layer beside it.** The obvious
implementation — loop over draws outside the optimiser — would have bypassed
`BudgetedEvaluator`, which spec §19 and M4's accounting both forbid. Instead
`make_uncertain_space` appends ONE synthetic `_uq_draw` variable to the `DesignSpace`, so
`(design…, draw index)` is an ordinary design vector whose `config_for` applies that draw's
perturbations. Nothing in `budget.py`, `persistence.py` or `evaluate.py` needed to change;
each (design, draw) pair gets a candidate ID, is charged one evaluation and is logged, and
common random numbers become free, *visible* cache hits rather than an untracked saving.

**Aleatory and epistemic are separated by the SAMPLE SHAPE, not by a post-hoc split.**
Nested sampling — E epistemic branches × A aleatory draws sharing common random numbers —
gives E complete output distributions. The p-box figure then makes the distinction visual:
the width of one curve is variability, the gap between curves is ignorance. The pooled mean
and s.d. are still printed, and the code says in as many words that pooling them is the law
of total variance, i.e. **in quadrature**, and that the identity is only *meaningful* if an
epistemic band is read as a probability distribution.

**Three physics hooks, all identity by default.** `atmosphere:` (an altitude-dependent
density multiplier, applied isothermally so `p = ρRT` and the speed of sound are preserved)
and `heating:` (a Sutton–Graves coefficient scale; a >86 km flux multiplier). A regression
test asserts the baseline's peak flux, bondline and max-g are bit-identical with the blocks
absent, empty, or set to identity.

**The nose-radius alternative went where K lives.** `geometry/stagnation_gradient.py` gained
`velocity_gradient_zoby`: Ellison's table displaced by *Ellison's own published disagreement*
with Zoby & Sullivan (TN D-5121 p. 5, verbatim). It is not a second dataset — this project
never transcribed Zoby & Sullivan's curves — and A-UQ-NOSE-1 lists the three ways it is
wider than the source strictly licenses. Its sign is evidenced, not assumed: at the flat
face Ellison tabulates R_eff = 3.155 R_b against the other's digitised 3.40–3.50 R_b.

**The GCI term refuses rather than skipping.** `cd_discretisation` declares
`when_unavailable: {aero_model: skip, discretisation_band: refuse}`. At Fidelity 0 it
quietly skips — there is no surface for it to be about. Select `cfd_surface_v1` and it
**stops the run**, naming the input, the requirement and `gci.csv`, because A-CFD-9 says the
band "raises rather than silently becoming zero" and dropping it would understate the C_D
uncertainty with nothing in the output to show it.

**The shortcut is measured, not asserted.** Robust optimisation uses S = 32 inner draws under
common random numbers. `verify_shortcut` then re-scores a subset of the finished front under
full independent Monte Carlo (1000 draws, different seed, no CRN) and reports bias, rank
correlation and violation-probability error against tolerances declared beforehand. The
check has tests proving it FAILS on an injected bias, a reversed ranking and a wrong
probability — a verification that cannot fail is a rubber stamp.

## Expected

- The harness runs end to end at small N.
- Fidelity 1 refuses on the missing GCI.
- The evaluator is bit-identical with every hook at its default.
- The study itself does not run, because the DOE screening is stale.

## Observed

**All four, plus two things worth writing down.**

1. **The runner refused to start, correctly.** `screening_is_current` reports that DOE run
   `M4-DOE-20260920T131334Z`'s active-variable list is void for today's design space
   (`base_overrides` and the base evaluator config both differ). This is the intended
   behaviour and it is the state A-OPT-5 describes: the current M4 front was computed under
   the legacy `cap_radius` model behind a bluntness cap that has since been removed. M7 is
   therefore **blocked on `make doe && make optimize`**, which is the coordinator's call.
   `--smoke` downgrades the refusal to a recorded warning and labels everything it writes.

2. **Re-evaluating the M4 designs under today's source moves them by ~20% in peak flux** —
   e.g. the stored peak-flux-only design's 201.9 kW/m² becomes 243.4 kW/m², +20.5%, exactly
   the shift `results/M4/nose-model-recheck/` measured for the nose-model change. This is why
   the §39 generator re-evaluates every row under one source hash and prints the stored value
   beside it with the delta, rather than quoting stale numbers next to a freshly-run robust
   design. Nothing is overwritten; the history is on the page.

3. **The smoke runs worked.** `results/M7/M7-SMOKE-ROBUST-*`: 15 generations, 960 inner
   evaluations, 4 chance-feasible front designs, shortcut verification PASSED on 3 designs
   (bias −1.51% and −0.69%, Spearman 1.000 on both objectives — at S = 8, so it means the
   plumbing works, nothing more). `results/M7/M7-SMOKE-*`: 4 designs propagated, Sobol'
   attribution, all seven figures, the §39 table with its robust row. Both publish nothing to
   `reports/` and carry a `SMOKE.md`.

4. **A property of the chance constraint I had not thought about until the code printed it.**
   With S inner draws the estimated probability can only be a multiple of 1/S. So α = 0.05
   at S = 32 really means *"at most 1 of 32 draws may violate"*, and at S = 8 — the smoke
   setting — it means **zero violations**, which is far harsher than 5% sounds. The first
   smoke run returned an empty front for exactly that reason and I initially read it as a
   bug. `RobustSettings.effective_chance_rule` now computes and prints the translation, and
   it is tested.

5. **A zero sensitivity index that is geometry, not a bug.** Sobol' on the reference capsule
   gave `effective_nose_radius_model` a total-order index of exactly 0.000 — surprising for
   the term I expected to dominate. The reason is that the reference capsule has nose radius
   = body radius, i.e. K = 1, where the forebody *is* a hemisphere and the two primaries agree
   identically by Zoby & Sullivan's own eq. (5). The M4 front sits at K ≈ 0.42, where they
   disagree by ~20%. The report now computes K and says this rather than leaving a reader to
   wonder; hypothesis 3 is untested until the front is regenerated.

## Evidence

- `src/aether/uncertainty/` (12 modules), `configs/uncertainty.yaml`,
  `scripts/run_uncertainty.py`, `scripts/run_robust_optimize.py`
- `tests/test_uncertainty.py` (45 tests) + `tests/test_robust.py` (16). Full suite and ruff
  clean.
- `results/M7/M7-SMOKE-*`, `results/M7/M7-SMOKE-ROBUST-*` — labelled, unpublished
- `docs/theory/uncertainty.md`, `ASSUMPTIONS.md` A-UQ-*, `VALIDATION_MATRIX.md` M7 row

## Interpretation

The harness is built and every piece of it that can be checked against a closed form has
been: the Wilson interval against its own algebra, Clopper–Pearson at k = 0 against
1 − α^(1/n) (the rule of three), percentiles against the order statistic that defines them,
and the whole propagation chain against a toy linear model whose mean, variance and
percentiles are analytic.

**Hypothesis 1 looks right and is not yet a result.** The smoke runs put the epistemic share
of the bondline variance at 98–99%, but on 12 draws with a stale active-variable list, so it
is an indication of where the answer will land, not the answer. If it holds at full sample
size, M7's headline recommendation is a *shopping list* — settle the Ellison/Zoby–Sullivan
question, find real TPS property data — rather than a margin.

**Hypothesis 2 is untestable until the front is regenerated**, because the designs being
tested are from a superseded run.

The honest summary of this milestone as it stands: **the machinery is verified; nothing has
been measured.** Every output distribution it will produce is also a lower bound on the real
uncertainty, because gate G2′ — catalycity, hot wall, radiation, where catalycity alone is
worth about a factor of two — has no distribution attached and is not in the inventory, and
seven of the nine active inputs are engineering judgment.

## Next

1. **`make doe && make optimize`** — a current screening and a front computed under today's
   heating model. Everything M7 does is blocked on this and it is the coordinator's call.
2. `make robust` then `make uncertainty` (`make m7` does both in order).
3. Read the shortcut verification FIRST. If it fails its declared tolerances, the front is
   the output of an unverified approximation and the report must be read that way.
4. If the epistemic share is as high as the smoke runs suggest, the Sobol' ranking is the
   deliverable: it names which piece of evidence buys the most. The single highest-value
   follow-up already has a name — Rodrigues, JTHT 2026, DOI 10.2514/1.T7458, the published
   closed-form reconstruction of Zoby–Sullivan scaling that would replace this project's own
   interpolation and collapse the dominant epistemic term (sourcing report item 8, paywalled).
5. Once `cfd_surface_v1` is in use, the four sourced C_D terms replace the single ±10%
   judgment band — and the run will refuse until M2 produces a GCI, which is the point.
