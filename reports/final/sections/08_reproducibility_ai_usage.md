# 19. Reproducibility, part 2: AI usage

*Draft. Does not depend on any pending run. The environment, commands, runtimes and
determinism half of §19 is sourced from `REPRODUCIBILITY.md` and
`docs/submission_package/reproducibility_links.md` and is assembled at the end, because its
run IDs and commit hash must be the final ones.*

This subsection exists because the honest answer to "who wrote this" affects what the reader
should check, and because a project in which an AI wrote most of the code is only reproducible
in a useful sense if that fact is stated with enough precision to be acted on.

---

## 19.1 What was AI-generated

Most of the software in this repository was written by Claude, through Claude Code, working
from a project specification. That includes the atmosphere, trajectory, heating and conduction
models; the parametric geometry generator and its STL exporter; the CFD case pipeline; the
optimisation, surrogate, adaptive-fidelity and uncertainty machinery; the test suite; and the
figure and report generators.

Several modelling decisions that change results were also proposed by the model and accepted
by the author. Four are recorded with the reason they were accepted:

- **Newton linearisation of the radiating boundary condition**, proposed in response to an
  actual divergence rather than as a refinement.
- **The post-entry soak-out phase**, proposed after observing that truncating the thermal
  solve at the trajectory's end understated the bondline peak by about 50 K.
- **Sizing the TPS stack to 15 mm**, because at the original 40 mm the bondline never
  responded within the entry, which would have hidden the effect under a design margin nobody
  would fly.
- **The effective-nose-radius correction**, made on the one ground the frozen scope permits
  new physics, a demonstrated validation failure in the objective.

The full item-by-item record is `AI_USAGE.md`, which classifies every component into four
categories: AI-generated and student-reviewed, AI-proposed and student-approved,
student-authored, and external.

---

## 19.2 What review status actually means here

`AI_USAGE.md` marks some rows **review pending**. That means precisely what it says: the
author has not yet read that code line by line and understood it. Those rows change only when
that has happened, not when a milestone is declared complete.

This is stated at this length because the alternative phrasings available are all misleading.
"Reviewed by the author" would be false for the pending rows. "AI-assisted" would be true and
uninformative. The count of reviewed against unreviewed components, current at submission
date, belongs in the final text and is `[PENDING — read from AI_USAGE.md at submission]`.

A proposed update listing the components added most recently, every one of them unreviewed,
together with a prioritised reading order and an honest time estimate, is
`docs/ai_usage_proposed_update.md`.

---

## 19.3 What AI-generated code got wrong, and how it was caught

Five defects introduced by generated code are documented rather than quietly fixed, because
they are the honest measure of what unreviewed generated code is worth, and because the
mechanism that caught each one is more informative than the defect.

| Defect | Caught by |
|---|---|
| A radiating boundary condition solved by fixed-point iteration, which diverges because the local gain of an iteration on a T⁴ law exceeds 1 at entry temperatures | The solver failing outright, with infinities |
| A thermal solve truncated at the end of the trajectory, understating the bondline peak by about 50 K, in the direction that would have weakened the project's own result | Physical reasoning about why the bondline peak lags, prompted by a number that looked low |
| An inverted control flow in the Pareto dominance test, returning every feasible design as non-dominated | **A figure.** A two-objective front must be monotone, so a zigzag is geometrically impossible. No test asserted monotonicity |
| A variance estimator whose confidence intervals fell outside the range a variance share can occupy | The interval itself, [−0.41, 1.15], being impossible |
| A surrogate classifier returning NaN, after which the optimiser silently stopped optimising and fell through to space-filling samples | **Where the budget went.** The hypervolume did not show it: on this problem a broken and a working optimiser score alike at the study budget |

Two of the five were caught by looking at output rather than by a test, and one was invisible
in the metric the study reports. That is the practical argument for the plotting standard and
for the budget-accounting figures, and it is why neither is treated as presentation.

---

## 19.4 What AI did not contribute

The research question, the choice of hypotheses, the frozen scope, and the decision that the
bondline rather than the surface is the interesting failure mode. Those came from the project
specification, and §1 says so for the same reason.

Also not contributed: the judgement about what this work is allowed to claim. Several of the
decisions that most shape the paper are refusals rather than additions. Not changing the
heating constant after deriving a different one. Not relaxing a convergence criterion the
first time it bit. Not adopting a metric the project had built. Not resolving a disagreement
between two primary sources by preferring one. Not deciding a deceleration limit that decides
the feasible region. Each of those is recorded with its reasoning, and each is the kind of
decision that a system optimising for a finished-looking result would make the other way.

---

## 19.5 Reproducing a study that calls a language model

One part of this project measures an AI agent against conventional optimisation algorithms
under matched evaluation budgets, which raises a reproducibility problem that is worth stating
precisely rather than hedging.

**The model cannot be reproduced. The run can.** Every prompt and every raw response is
persisted verbatim, and a replay mode re-runs every evaluation from them, using the recorded
run's configuration snapshot, and checks that the hypervolumes match. A strict replay of a
live development run produced zero prompt mismatches and an identical candidate log and
hypervolume. A stranger with no model access can therefore reproduce the recorded result,
which is what the specification's stranger-reproducibility requirement asks for. Issuing new
calls will give different numbers, and that is a property of the object being studied rather
than a defect in the harness.

Three further properties of that harness are part of the reproducibility claim:

- **Model output is untrusted data.** It is parsed as JSON only, validated field by field
  against a declared schema, and unknown fields, unknown parent designs, non-finite values and
  out-of-bounds values are rejected and logged, never clipped or repaired. The rejection count
  is itself a reported metric, because a model that is careless about bounds loses
  evaluations, which is the correct price.
- **The agent is isolated from the answer.** It runs in an empty temporary directory with
  tools, external servers, hooks, skills and project-file discovery switched off, specifically
  so that it cannot read the report that states the result. It receives structured data only.
  What it can still use is that variable and metric names carry aerospace meaning, so prior
  knowledge cannot be separated from reasoning over the supplied data, and that is stated as
  part of what is measured rather than claimed away.
- **The success criterion was declared before any run.** No claim of AI superiority or
  inferiority is made anywhere in this paper, because the study has not been run.
  `[PENDING FINAL RUN]`

---

## 19.6 Why the disclosure is this specific

A disclosure that reads as a legal hedge invites the reader to skip it, and the obvious
follow-up question deserves an answer rather than a formula. If an AI wrote it, what did the
author do?

The answer available here is that the author is accountable for every claim; that the boundary
between what was generated and what has been understood is tracked rather than asserted; and
that the parts not yet understood are named rather than averaged into a reassuring sentence.
That answer is stronger than a vaguer one, and it is only available because the tracking
exists.

It is also incomplete, and the incompleteness has a name. The final quality gate's twelfth
item is clear student intellectual ownership, and it is the one item nobody else can discharge
on the author's behalf. Its current status is in `docs/final_quality_gate.md`.
