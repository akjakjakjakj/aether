"""Robust multi-objective optimisation and the verification of its shortcut (spec §28).

Conceptual anchor
-----------------
The nominal Pareto front answers "which design is best if the world behaves exactly as
modelled". Nothing flies that world. Robust optimisation asks instead:

    minimise   the 95th percentile of peak heat flux
               the 95th percentile of peak bondline temperature
    subject to P(constraint violated) <= alpha

so a design is judged on a bad day rather than an average one, and a constraint it clears
by 0.9% nominally is not counted as satisfied if a third of its draws cross it.

Why this needs a shortcut, and what the shortcut is
----------------------------------------------------
Full nested Monte Carlo - a thousand samples inside every candidate of every generation -
is four orders of magnitude beyond this project's compute budget. Two things make it
affordable:

  * **A modest inner sample.** S draws per candidate, declared in config, not the
    thousands a standalone estimate of a 95th percentile would want.
  * **Common random numbers.** Every candidate in every generation is evaluated on the
    SAME S draws. The comparison between two designs is then not confounded by sampling
    noise - the estimator of the DIFFERENCE is far better than the estimator of either
    value - and, because a repeated design hits the evaluator's cache, re-testing costs
    nothing.

Both are approximations, and the second is what makes the first tolerable. Neither is
taken on faith: `verify_shortcut` re-runs a subset of the finished front under full,
independent Monte Carlo with a different seed and reports the measured bias in each
robust objective, the measured error in each violation probability, and whether the
RANKING of the subset survived - against tolerances declared before the run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.evaluator import Evaluator
from pymoo.core.problem import Problem
from pymoo.core.termination import NoTermination
from pymoo.operators.mutation.pm import PM
from pymoo.problems.static import StaticProblem
from scipy.stats import spearmanr

from ..optimization.budget import BudgetedEvaluator, BudgetExhausted
from ..optimization.optimizers import _INFEASIBLE_OBJECTIVE, _TrackedSBX
from .space import UncertainDesignSpace
from .statistics import quantile, violation_probability

QUANTILE_ESTIMATORS = ("empirical",)


@dataclass(frozen=True)
class RobustSettings:
    """Everything about the robust problem, declared in config BEFORE any run.

    None of these may be chosen after looking at a result; they are snapshotted with the
    run and the report quotes them from the snapshot.
    """

    objective_percentile: float
    quantile_estimator: str
    chance_alpha: dict[str, float]
    inner_samples: int
    inner_seed: int
    population_size: int
    budget_evaluations: int
    seeds: tuple[int, ...]

    def __post_init__(self) -> None:
        if not 0.0 < self.objective_percentile < 100.0:
            raise ValueError("robust.objective_percentile must lie strictly in (0, 100)")
        if self.quantile_estimator not in QUANTILE_ESTIMATORS:
            raise ValueError(f"robust.quantile_estimator must be one of "
                             f"{QUANTILE_ESTIMATORS}, got {self.quantile_estimator!r}")
        if self.inner_samples < 2:
            raise ValueError("robust.inner_samples must be at least 2")
        for name, alpha in self.chance_alpha.items():
            if not 0.0 <= alpha <= 1.0:
                raise ValueError(f"robust.chance_constraints['{name}'] must be a "
                                 f"probability, got {alpha}")

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> RobustSettings:
        return cls(
            objective_percentile=float(cfg["objective_percentile"]),
            quantile_estimator=str(cfg.get("quantile_estimator", "empirical")),
            chance_alpha={str(k): float(v)
                          for k, v in (cfg["chance_constraints"] or {}).items()},
            inner_samples=int(cfg["inner_samples"]),
            inner_seed=int(cfg["inner_seed"]),
            population_size=int(cfg["population_size"]),
            budget_evaluations=int(cfg["budget_evaluations"]),
            seeds=tuple(int(s) for s in cfg["seeds"]),
        )

    @property
    def constraint_names(self) -> tuple[str, ...]:
        return tuple(self.chance_alpha)

    @property
    def probability_resolution(self) -> float:
        """The smallest non-zero violation probability the inner sample can express.

        An inner sample of S draws can only ever report p_hat in {0, 1/S, 2/S, ...}, so a
        chance constraint at alpha means "at most floor(alpha * S) violations out of S" -
        and if alpha < 1/S it means "ZERO violations", which is a far stricter
        requirement than the number suggests. This is a property of the shortcut and the
        report prints it rather than letting a reader assume alpha is met continuously.
        """
        return 1.0 / self.inner_samples

    @property
    def effective_chance_rule(self) -> dict[str, str]:
        rules = {}
        for name, alpha in self.chance_alpha.items():
            allowed = int(np.floor(alpha * self.inner_samples + 1e-12))
            rules[name] = (f"at most {allowed} of {self.inner_samples} inner draws may "
                           f"violate (alpha {alpha:g}"
                           + (", i.e. ZERO violations - alpha is below the inner "
                              f"sample's resolution of {self.probability_resolution:g}"
                              if allowed == 0 else "") + ")")
        return rules

    def to_dict(self) -> dict[str, Any]:
        return {"objective_percentile": self.objective_percentile,
                "quantile_estimator": self.quantile_estimator,
                "chance_constraints": dict(self.chance_alpha),
                "inner_samples": self.inner_samples, "inner_seed": self.inner_seed,
                "population_size": self.population_size,
                "budget_evaluations": self.budget_evaluations,
                "seeds": list(self.seeds),
                "probability_resolution": self.probability_resolution,
                "effective_chance_rule": self.effective_chance_rule}


# ---------------------------------------------------------------------------------------
# reducing one design's inner sample
# ---------------------------------------------------------------------------------------

@dataclass
class RobustScore:
    """What one candidate design scored on its inner sample."""

    objectives: dict[str, float]
    violation_probability: dict[str, float]
    chance_violation: dict[str, float]
    """p_hat - alpha per chance constraint. <= 0 means the chance constraint is met."""
    n_samples: int
    n_not_evaluable: int
    nominal_available: bool = True

    @property
    def worst_chance_violation(self) -> float:
        return max(self.chance_violation.values()) if self.chance_violation else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"objectives": dict(self.objectives),
                "violation_probability": dict(self.violation_probability),
                "chance_violation": dict(self.chance_violation),
                "n_samples": self.n_samples, "n_not_evaluable": self.n_not_evaluable}


def score_sample(block: pd.DataFrame, objectives: tuple[str, ...],
                 settings: RobustSettings) -> RobustScore:
    """Robust objectives and chance-constraint probabilities for ONE design's draws.

    A draw that produced no physics (`status != OK`) counts as a violation of EVERY chance
    constraint - a vehicle that does not complete an entry has not satisfied anything -
    and is excluded from the objective percentiles, where it has no value to contribute.
    """
    not_evaluable = (block["status"].to_numpy() != "OK")
    values = {name: quantile(block[name].to_numpy(dtype=float),
                             settings.objective_percentile)
              for name in objectives}
    probs: dict[str, float] = {}
    chance: dict[str, float] = {}
    for name, alpha in settings.chance_alpha.items():
        if name == "any":
            violated = ~block["feasible"].to_numpy(dtype=bool) & ~not_evaluable
        else:
            column = f"margin__{name}"
            margins = (block[column].to_numpy(dtype=float) if column in block.columns
                       else np.full(len(block), np.nan))
            violated = np.isfinite(margins) & (margins < 0.0)
        p = float(np.mean(violated | not_evaluable))
        probs[name] = p
        chance[name] = p - alpha
    return RobustScore(objectives=values, violation_probability=probs,
                       chance_violation=chance, n_samples=int(len(block)),
                       n_not_evaluable=int(not_evaluable.sum()))


def _blocks(rows: pd.DataFrame, inner: int) -> list[pd.DataFrame]:
    """Split a design-major, draw-fastest frame into one block per design."""
    n = len(rows) // inner
    return [rows.iloc[i * inner:(i + 1) * inner] for i in range(n)]


# ---------------------------------------------------------------------------------------
# the optimiser
# ---------------------------------------------------------------------------------------

def run_robust_nsga2(evaluator: BudgetedEvaluator, space: UncertainDesignSpace,
                     objectives: tuple[str, ...], settings: RobustSettings,
                     *, inner_indices: np.ndarray,
                     record: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """NSGA-II on the robust problem, every evaluation through `evaluator`.

    This deliberately mirrors `optimization.optimizers.run_nsga2` rather than calling it:
    that function evaluates ONE vector per individual, and here each individual costs an
    inner sample of `settings.inner_samples` evaluations that then has to be reduced
    before pymoo sees an objective. The ask/tell structure, the constraint-domination
    handling and the parent-ID tracking are otherwise identical, and the two are pinned
    against each other by a test that a degenerate one-draw uncertainty model reproduces
    the nominal optimiser's accounting.
    """
    n_design = space.n_active - 1
    constraint_names = settings.constraint_names
    problem = Problem(n_var=n_design, n_obj=len(objectives),
                      n_ieq_constr=max(1, len(constraint_names)), xl=0.0, xu=1.0)
    algorithm = NSGA2(pop_size=settings.population_size,
                      crossover=_TrackedSBX(prob=0.9, eta=15),
                      mutation=PM(eta=20), eliminate_duplicates=True)
    algorithm.setup(problem, termination=NoTermination(), seed=evaluator.seed,
                    verbose=False)

    inner = int(settings.inner_samples)
    lower = np.array([v.lower for v in space.active_variables[:n_design]])
    upper = np.array([v.upper for v in space.active_variables[:n_design]])
    generation, stopped = 0, "budget spent"
    while evaluator.remaining >= inner:
        pop = algorithm.ask()
        unit = np.clip(pop.get("X"), 0.0, 1.0)
        x_design = lower + unit * (upper - lower)
        parents = [list(ind.get("parent_ids") or []) for ind in pop]
        vectors = space.design_vectors(x_design, inner_indices)
        expanded = [p for p in parents for _ in range(inner)]
        try:
            rows = pd.DataFrame(evaluator.evaluate(vectors, generation=generation,
                                                   parent_ids=expanded))
        except BudgetExhausted:
            stopped = "budget exhausted mid-generation; that generation is logged but " \
                      "was not told to the optimiser"
            break
        if len(rows) != len(vectors):
            stopped = "an incomplete generation came back; it is logged but unused"
            break

        blocks = _blocks(rows, inner)
        scores = [score_sample(b, objectives, settings) for b in blocks]
        f = np.array([[s.objectives[name] for name in objectives] for s in scores])
        f = np.where(np.isfinite(f), f, _INFEASIBLE_OBJECTIVE)
        if constraint_names:
            g = np.array([[s.chance_violation[c] for c in constraint_names]
                          for s in scores])
        else:
            g = np.zeros((len(scores), 1))
        Evaluator().eval(StaticProblem(problem, F=f, G=g), pop)
        pop.set("cid", np.array([b["candidate_id"].iloc[0] for b in blocks], dtype=object))
        algorithm.tell(infills=pop)
        if record is not None:
            for block, score, xd in zip(blocks, scores, x_design, strict=True):
                record.append({
                    "run_id": evaluator.run_id, "method": evaluator.method,
                    "seed": evaluator.seed, "generation": generation,
                    "candidate_id": block["candidate_id"].iloc[0],
                    **{f"x__{v.name}": float(val) for v, val in
                       zip(space.active_variables[:n_design], xd, strict=True)},
                    **{f"robust__{k}": v for k, v in score.objectives.items()},
                    **{f"pviol__{k}": v for k, v in score.violation_probability.items()},
                    "worst_chance_violation": score.worst_chance_violation,
                    "n_not_evaluable": score.n_not_evaluable,
                })
        generation += 1
    return {"generations": generation, "stopped_because": stopped,
            "budget_used": evaluator.used, "cache_hits": evaluator.n_cache_hits,
            "inner_samples": inner}


def robust_front(record: list[dict[str, Any]], objectives: tuple[str, ...]
                 ) -> pd.DataFrame:
    """The non-dominated, chance-feasible designs of a robust run's record."""
    from ..optimization.pareto import pareto_front

    frame = pd.DataFrame(record)
    if frame.empty:
        return frame
    frame = frame.drop_duplicates("candidate_id")
    feasible = frame[frame["worst_chance_violation"] <= 0.0]
    if feasible.empty:
        return feasible
    cols = [f"robust__{name}" for name in objectives]
    idx = pareto_front(feasible[cols].to_numpy(dtype=float))
    return feasible.iloc[idx].sort_values(cols[0]).reset_index(drop=True)


# ---------------------------------------------------------------------------------------
# verifying the shortcut
# ---------------------------------------------------------------------------------------

@dataclass
class ShortcutVerification:
    """Shortcut robust statistics against full independent Monte Carlo, on a subset."""

    n_designs: int
    n_inner: int
    n_full: int
    full_seed: int
    objectives: dict[str, Any] = field(default_factory=dict)
    probabilities: dict[str, Any] = field(default_factory=dict)
    tolerances: dict[str, float] = field(default_factory=dict)
    verdict: dict[str, Any] = field(default_factory=dict)
    per_design: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"n_designs": self.n_designs, "n_inner": self.n_inner,
                "n_full": self.n_full, "full_seed": self.full_seed,
                "objectives": self.objectives, "probabilities": self.probabilities,
                "tolerances": self.tolerances, "verdict": self.verdict,
                "per_design": self.per_design}


def verify_shortcut(shortcut_scores: list[RobustScore], full_scores: list[RobustScore],
                    objectives: tuple[str, ...], settings: RobustSettings,
                    *, labels: list[str], n_full: int, full_seed: int,
                    tolerances: dict[str, float]) -> ShortcutVerification:
    """Measure the shortcut's error against full MC. Tolerances are declared beforehand.

    Three questions, because they can fail independently:

    1. **Is the robust objective biased?** Mean signed relative difference between the
       S-draw CRN percentile and the `n_full`-draw independent one. A quantile estimated
       from a small sample is biased inward, so a non-zero answer is expected; what
       matters is whether it is small compared with the spread the front covers.
    2. **Is the RANKING preserved?** Spearman rank correlation over the subset. An
       optimiser only ever needs to know which design is better, so a biased estimator
       that ranks correctly is still a usable one - and this is the question the shortcut
       actually has to pass.
    3. **Are the violation probabilities right?** Absolute difference per chance
       constraint. A chance constraint decides feasibility, so an error here changes
       which designs exist, not just where they sit.
    """
    n = len(shortcut_scores)
    if n != len(full_scores) or n != len(labels):
        raise ValueError("shortcut, full and label lists must be the same length")
    result = ShortcutVerification(n_designs=n, n_inner=settings.inner_samples,
                                 n_full=n_full, full_seed=full_seed,
                                 tolerances=dict(tolerances))

    for name in objectives:
        short = np.array([s.objectives[name] for s in shortcut_scores], dtype=float)
        full = np.array([s.objectives[name] for s in full_scores], dtype=float)
        ok = np.isfinite(short) & np.isfinite(full) & (full != 0.0)
        rel = (short[ok] - full[ok]) / full[ok]
        rho = (float(spearmanr(short[ok], full[ok]).statistic)
               if ok.sum() >= 3 and np.ptp(full[ok]) > 0 else float("nan"))
        result.objectives[name] = {
            "n_compared": int(ok.sum()),
            "mean_relative_bias": float(np.mean(rel)) if rel.size else float("nan"),
            "max_abs_relative_error": float(np.max(np.abs(rel))) if rel.size
            else float("nan"),
            "spearman_rank_correlation": rho,
            "full_span": float(np.ptp(full[ok])) if ok.sum() else float("nan"),
            "mean_abs_error_over_full_span": (
                float(np.mean(np.abs(short[ok] - full[ok])) / np.ptp(full[ok]))
                if ok.sum() and np.ptp(full[ok]) > 0 else float("nan")),
        }

    for name in settings.constraint_names:
        short = np.array([s.violation_probability[name] for s in shortcut_scores])
        full = np.array([s.violation_probability[name] for s in full_scores])
        alpha = settings.chance_alpha[name]
        result.probabilities[name] = {
            "alpha": alpha,
            "max_abs_difference": float(np.max(np.abs(short - full))),
            "mean_abs_difference": float(np.mean(np.abs(short - full))),
            "n_verdict_disagreements": int(np.sum((short <= alpha) != (full <= alpha))),
            "full_wilson_of_worst": violation_probability(
                name, np.zeros(n_full, dtype=bool)).to_dict()["wilson_hi"],
        }

    for label, s, f in zip(labels, shortcut_scores, full_scores, strict=True):
        result.per_design.append({
            "label": label,
            **{f"shortcut__{k}": v for k, v in s.objectives.items()},
            **{f"full__{k}": v for k, v in f.objectives.items()},
            **{f"shortcut_p__{k}": v for k, v in s.violation_probability.items()},
            **{f"full_p__{k}": v for k, v in f.violation_probability.items()},
        })

    bias_tol = float(tolerances.get("max_abs_relative_bias", 0.05))
    rank_tol = float(tolerances.get("min_rank_correlation", 0.8))
    prob_tol = float(tolerances.get("max_abs_probability_difference", 0.05))
    failures: list[str] = []
    for name, block in result.objectives.items():
        if not np.isfinite(block["mean_relative_bias"]) or \
                abs(block["mean_relative_bias"]) > bias_tol:
            failures.append(f"{name}: mean relative bias "
                            f"{block['mean_relative_bias']:+.4f} exceeds {bias_tol:g}")
        rho = block["spearman_rank_correlation"]
        if not np.isfinite(rho) or rho < rank_tol:
            failures.append(f"{name}: rank correlation {rho:.3f} below {rank_tol:g}")
    for name, block in result.probabilities.items():
        if block["max_abs_difference"] > prob_tol:
            failures.append(f"P({name}): max absolute difference "
                            f"{block['max_abs_difference']:.4f} exceeds {prob_tol:g}")
    result.verdict = {
        "passed": not failures,
        "failures": failures,
        "statement": ("the common-random-number shortcut reproduced full Monte Carlo "
                      "within every declared tolerance on this subset"
                      if not failures else
                      "the shortcut did NOT reproduce full Monte Carlo within the "
                      "declared tolerances; the robust front must be read as the output "
                      "of the shortcut, not as a converged robust optimum"),
    }
    return result
