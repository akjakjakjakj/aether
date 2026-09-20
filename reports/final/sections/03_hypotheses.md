# 3. Hypotheses

*Draft. Does not depend on any pending run.*

Three hypotheses were frozen in the project specification before any model was built. They
are reproduced here verbatim, because a hypothesis that is restated after the results exist
is not a hypothesis.

> **H0.** Minimising peak heat flux alone does not necessarily produce the thermally safest
> re-entry solution.
>
> **H1.** Joint optimisation of peak heat flux and in-depth TPS response can identify safer
> feasible designs than peak-heat-only optimisation.
>
> **H2.** Surrogate-assisted and AI-guided adaptive-fidelity search can approach the Pareto
> frontier with fewer expensive CFD evaluations than unguided or brute-force search.

---

## 3.1 H0: what would falsify it

H0 is an existence claim, and it is deliberately weak: it asks for the existence of at least
one pair of designs A and B such that

    q″_max(B) < q″_max(A)   and   T_bond,max(B) > T_bond,max(A),

within a domain where the model is valid. It is falsified by searching that domain and
finding no such pair, which would mean the design minimising peak heat flux also minimises
the in-depth response.

Three things make that a real test rather than a formality.

**The search is automated and its thresholds were declared in advance.** A pair is recorded
only if the peak-flux reduction is at least 1.0% and the bondline penalty at least 1.0 K, so
discretisation noise cannot be reported as physics.

**The falsifying outcome is physically reachable, and was in fact reached once.** With a
40 mm insulator the bondline rose 8.8 K across an entire entry, which makes the two metrics
effectively independent and the effect invisible. That is a genuine falsification of H0 *for
that stack*, and it is recorded as a negative result rather than discarded, because it is
what turns the eventual positive result into a statement about a regime instead of a
statement about every vehicle.

**The result can be too strong, and that is a warning rather than a triumph.** H0 asks for
one counterexample pair; the first sweep returned a domain in which every ordered pair in one
direction is a counterexample. A hypothesis that returns far more than it asked for is
usually a hypothesis that was easy to satisfy, and §7 reports the monotonicity rather than
the rank correlation for exactly that reason.

---

## 3.2 H1: what would falsify it

H1 is a comparison, and it is falsified if a joint optimiser and a peak-flux-only optimiser,
run over the same feasible set with the same evaluation budget, select designs whose in-depth
thermal margins do not differ by more than the model's own resolution.

Two definitional decisions were made before running it, because both could otherwise be
adjusted afterwards to produce a difference.

**"Joint" is defined without weights.** The objective is kept multi-objective and the design
reported against the peak-flux-only optimum is the **knee** of the combined feasible front,
the point furthest from the chord joining the front's extremes in normalised objective space.
That definition contains no weights, so the project's own objective is never collapsed into a
weighted score. Its one dependence is on the normalisation rectangle, which in turn depends
weakly on the bondline allowable, and that is stated.

**"Safer" is reported as an absolute difference, not a ratio.** A margin ratio is measured
against the bondline allowable and swings from 37.5× to 1.6× as that allowable moves from
445 K to 500 K. The absolute difference does not depend on it at all.

---

## 3.3 H2: not tested

**H2 has not been tested.** The harness exists, its success criterion was declared in a
configuration file before any run, and no study has been run.

The criterion is worth stating here rather than in the results section, because its most
important property is that it can return "no answer". Cost is defined as the number of CFD
calls an arm had been charged when its truth hypervolume first reached 95% of a reference
value, censored at budget plus one if it never does. H2 is `SUPPORTED` only if the arm that
buys no CFD fails to reach the target in at least three of five seeds, the adaptive arm does
reach it, its median cost is below the best non-adaptive CFD-buying arm's, and a one-sided
exact permutation rank test gives p < 0.05. `CONTRADICTED` is the mirror image. And if the
no-CFD arm reaches the target, the verdict is **`NOT_TESTABLE`**: "fewer calls" is a
meaningless claim if no calls were needed.

That last branch is not a hedge. The development dry runs never produced an out-of-hull
candidate on the current surface, which is one of the two ways the question could turn out
not to arise on this problem.

With five seeds and small integer costs with ties, the exact test rejects only when the two
samples barely overlap. A null result is therefore weak evidence of equivalence, and is
reported as such.

---

## 3.4 Status against each hypothesis

| Hypothesis | Status | Evidence | Fidelity |
|---|---|---|---|
| H0 | **Supported** in the tested domain | `reports/milestones/M1_burn_vs_bake.md`, `M1_signature_counterexample.md` | 0 |
| H1 | **Supported** on a two-variable grid | `reports/milestones/M1_burn_vs_bake.md` §M1b | 0 |
| H2 | **Not tested** | harness verified; `configs/adaptive_fidelity.yaml` carries the criterion | — |

Both supported results are Fidelity-0 results with a constant drag coefficient, and both are
statements about a small design space. The full-geometry test of H1 under the corrected
heating model and the CFD-derived drag surface is `[PENDING FINAL RUN]`.

---

## 3.5 What the hypotheses do not cover

Worth stating explicitly, because a reader will otherwise assume it.

None of the three says anything about a real vehicle, a qualified TPS material, or a flight
condition. H0 and H1 are statements about a model; H2 is a statement about search efficiency
in that model. The question of whether the physical mechanism behaves as modelled is the
subject of the physical experiment, which has not been run, and even that experiment is a
thermal-transient validation on a coupon rather than a re-entry simulation.

---

## Notes for revision

- Reproduce H0, H1 and H2 exactly as in `CLAUDE.md` §4. Do not tighten the wording.
- The `NOT_TESTABLE` branch of H2 goes in this section rather than only in §12. A reader who
  reaches the adaptive-fidelity section and meets it for the first time will read it as an
  excuse; a reader who met it in the hypotheses will read it as a design decision, which is
  what it is.
- The NR-03 falsification in §3.1 is the strongest single argument that H0 was genuinely
  falsifiable, and it should not be cut for length.
