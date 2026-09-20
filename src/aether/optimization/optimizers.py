"""The three M4 optimisers. All of them see the design space as the unit hypercube and
reach the physics ONLY through a `BudgetedEvaluator`, so their budgets are identical by
construction and M5 can add a fourth method without touching the accounting.

  lhs_search      the floor: one seeded Latin Hypercube of `budget` points, no learning.
                  Anything that cannot beat this is not optimising.
  nsga2           pymoo's NSGA-II, constraint-domination for feasibility, driven through
                  ask/tell so that every individual passes through the budget wrapper and
                  carries its parents' candidate IDs.
  scalarised_de   the simple baseline: differential evolution (rand/1/bin) on a weighted
                  sum of the two NORMALISED objectives, repeated over a sweep of weights
                  with the budget split equally. The weights generate a front; they are
                  never used to pick a single 'best' design (spec section 3).

Feasibility is handled the same way everywhere (Deb's rules): a feasible design beats an
infeasible one; two infeasible designs are compared by total constraint violation.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.evaluator import Evaluator
from pymoo.core.problem import Problem
from pymoo.core.termination import NoTermination
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.problems.static import StaticProblem

from .budget import BudgetedEvaluator, BudgetExhausted, constraint_violation, objective_matrix
from .pareto import normalise
from .sampling import latin_hypercube

_INFEASIBLE_OBJECTIVE = 1.0e30
"""Stand-in handed to pymoo for the objectives of a design with no physics result. It is
never persisted and never ranked on: constraint-domination compares infeasible designs by
violation alone. It exists only because NaN breaks pymoo's sorting."""

_INFEASIBLE_SCALAR_OFFSET = 10.0


def _unit_evaluate(evaluator: BudgetedEvaluator, unit_x: np.ndarray, **kwargs):
    return evaluator.evaluate(evaluator.space.from_unit(np.clip(unit_x, 0.0, 1.0)), **kwargs)


# ---------------------------------------------------------------------------------------
def run_lhs_search(evaluator: BudgetedEvaluator, settings: dict[str, Any],
                   objectives: tuple[str, ...], hv_cfg: dict[str, Any]) -> None:
    """Space-filling floor. `generation` is the chunk index; it carries no meaning."""
    k = evaluator.space.n_active
    unit = latin_hypercube(evaluator.budget, k, evaluator.seed)
    chunk = int(settings.get("chunk_size", 50))
    try:
        for gen, start in enumerate(range(0, len(unit), chunk)):
            _unit_evaluate(evaluator, unit[start:start + chunk], generation=gen)
    except BudgetExhausted:
        pass


# ---------------------------------------------------------------------------------------
class _TrackedSBX(SBX):
    """SBX that stamps each offspring with its parents' candidate IDs (spec section 22)."""

    def do(self, problem, pop, parents=None, **kwargs):
        matings = [pop[m] for m in parents] if parents is not None else pop
        off = super().do(problem, pop, parents=parents, **kwargs)
        n_matings = len(matings)
        for j, individual in enumerate(off):
            ids = [p.get("cid") for p in matings[j % n_matings]]
            individual.set("parent_ids", [i for i in ids if i is not None])
        return off


def run_nsga2(evaluator: BudgetedEvaluator, settings: dict[str, Any],
              objectives: tuple[str, ...], hv_cfg: dict[str, Any]) -> None:
    k = evaluator.space.n_active
    problem = Problem(n_var=k, n_obj=len(objectives), n_ieq_constr=1, xl=0.0, xu=1.0)
    algorithm = NSGA2(
        pop_size=int(settings["population_size"]),
        crossover=_TrackedSBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True,
    )
    algorithm.setup(problem, termination=NoTermination(), seed=evaluator.seed, verbose=False)

    generation = 0
    try:
        while evaluator.remaining > 0:
            pop = algorithm.ask()
            parents = [list(ind.get("parent_ids") or []) for ind in pop]
            rows = _unit_evaluate(evaluator, pop.get("X"), generation=generation,
                                  parent_ids=parents)
            f = objective_matrix(rows, objectives)
            f = np.where(np.isfinite(f), f, _INFEASIBLE_OBJECTIVE)
            g = constraint_violation(rows)[:, None]
            Evaluator().eval(StaticProblem(problem, F=f, G=g), pop)
            pop.set("cid", np.array([row["candidate_id"] for row in rows], dtype=object))
            algorithm.tell(infills=pop)
            generation += 1
    except BudgetExhausted:
        pass


# ---------------------------------------------------------------------------------------
def _scalar_fitness(rows, objectives, weight: float, hv_cfg) -> np.ndarray:
    ideal = np.array([hv_cfg["ideal_point"][name] for name in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][name] for name in objectives], dtype=float)
    f_norm = normalise(objective_matrix(rows, objectives), ideal, ref)
    scalar = weight * f_norm[:, 0] + (1.0 - weight) * f_norm[:, 1]
    violation = constraint_violation(rows)
    return np.where(violation > 0.0, _INFEASIBLE_SCALAR_OFFSET + violation, scalar)


def run_scalarised_de(evaluator: BudgetedEvaluator, settings: dict[str, Any],
                      objectives: tuple[str, ...], hv_cfg: dict[str, Any]) -> None:
    """DE/rand/1/bin with dithered mutation, once per weight, budget split equally.

    `generation` restarts at 0 for each weight and the weight index is encoded as
    1000 * weight_index + generation, so the log stays sortable.
    """
    if len(objectives) != 2:
        raise ValueError("scalarised_de is written for exactly two objectives")
    k = evaluator.space.n_active
    n_weights = int(settings["n_weights"])
    n_pop = int(settings["population_size"])
    f_lo, f_hi = (float(v) for v in settings["mutation"])
    cr = float(settings["recombination"])
    weights = np.linspace(0.0, 1.0, n_weights)
    shares = np.full(n_weights, evaluator.budget // n_weights)
    shares[: evaluator.budget % n_weights] += 1
    targets = np.cumsum(shares)
    rng = np.random.default_rng(evaluator.seed)

    try:
        for w_index, (weight, target) in enumerate(zip(weights, targets, strict=True)):
            gen_base = 1000 * w_index
            room = int(target - evaluator.used)
            if room <= 0:
                continue
            pop = latin_hypercube(min(n_pop, room), k, int(rng.integers(0, 2**31 - 1)))
            rows = _unit_evaluate(evaluator, pop, generation=gen_base)
            fitness = _scalar_fitness(rows, objectives, weight, hv_cfg)
            ids = [row["candidate_id"] for row in rows]
            generation, stalled = 1, 0
            while evaluator.used < target and len(pop) >= 4 and stalled < 25:
                n_trial = min(len(pop), int(target - evaluator.used))
                targets_idx = rng.permutation(len(pop))[:n_trial]
                trials, parents = [], []
                for i in targets_idx:
                    a, b, c = rng.choice([j for j in range(len(pop)) if j != i], 3,
                                         replace=False)
                    mutant = pop[a] + rng.uniform(f_lo, f_hi) * (pop[b] - pop[c])
                    cross = rng.random(k) < cr
                    cross[rng.integers(0, k)] = True
                    trials.append(np.clip(np.where(cross, mutant, pop[i]), 0.0, 1.0))
                    parents.append([ids[i], ids[a], ids[b], ids[c]])
                used_before = evaluator.used
                rows = _unit_evaluate(evaluator, np.array(trials),
                                      generation=gen_base + generation, parent_ids=parents)
                stalled = stalled + 1 if evaluator.used == used_before else 0
                trial_fitness = _scalar_fitness(rows, objectives, weight, hv_cfg)
                for i, trial, row, fit in zip(targets_idx, trials, rows, trial_fitness,
                                              strict=True):
                    if fit <= fitness[i]:
                        pop[i], fitness[i], ids[i] = trial, fit, row["candidate_id"]
                generation += 1
    except BudgetExhausted:
        pass


METHODS = {
    "lhs_search": run_lhs_search,
    "nsga2": run_nsga2,
    "scalarised_de": run_scalarised_de,
}
