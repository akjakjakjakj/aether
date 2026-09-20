"""M5: constrained bi-objective Bayesian optimisation through the same budget meter.

Conceptual anchor
-----------------
Bayesian optimisation spends an expensive evaluation where a cheap statistical model
says it is most likely to pay off. Three choices define this implementation:

  scalarisation  ParEGO-style (Knowles 2006): each point of a batch gets its own random
                 weight vector and the two NORMALISED objectives are collapsed by the
                 augmented Tchebycheff function  max_i(w_i f_i) + rho * sum_i(w_i f_i).
                 Random weights are what spread the batch along the front; no weight is
                 ever used to pick a "best" design (spec section 3).
  improvement    expected improvement of that scalar over the best FEASIBLE evaluated
                 design, by Monte-Carlo over the per-objective GP posteriors. The GPs
                 model the objectives themselves, not the scalar, so the same models are
                 the ones whose accuracy and calibration are validated (section 25).
  feasibility    EI is multiplied by the probability of feasibility: P(the design yields
                 a physics result) x prod_j P(constraint margin_j >= 0). While no
                 feasible design is known, the acquisition is that probability alone.

Why this and not expected hypervolume improvement: with a batch of 10 and a constrained,
half-invalid box, EHVI needs either a greedy fantasy loop or a joint batch integral; the
random-weight scheme gives batch diversity for free and its cost is one GP fit per
iteration. The choice was made before the ablation ran (configs/ai_ablation.yaml).

The acquisition is allowed to pick points OUTSIDE the training hull - it is buying an
evaluation there, not trusting the prediction - but every such pick is flagged in the
prediction log and counted in the report.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import qmc

from ..surrogate.model import MIN_TRAINING_ROWS, DesignSurrogate, has_physics, unit_inputs
from .budget import BudgetedEvaluator, BudgetExhausted
from .pareto import normalise, pareto_front
from .sampling import latin_hypercube

_RHO = 0.05              # augmented-Tchebycheff coefficient, Knowles (2006)
_MIN_SEPARATION = 1e-3   # unit-cube distance below which a pool point counts as a repeat


def initial_design_size(settings: dict[str, Any], n_active: int) -> int:
    """Size of the seeded initial Latin Hypercube: `n_initial_per_variable` x the number of
    ACTIVE variables, so it follows the DOE screening instead of assuming four of them. An
    explicit `n_initial` overrides it (tests, development runs)."""
    if "n_initial" in settings:
        return int(settings["n_initial"])
    return int(settings["n_initial_per_variable"]) * int(n_active)


def _tchebycheff(f_norm: np.ndarray, weights: np.ndarray) -> np.ndarray:
    weighted = f_norm * weights
    return np.max(weighted, axis=-1) + _RHO * np.sum(weighted, axis=-1)


def _candidate_pool(rows: list[dict[str, Any]], evaluator: BudgetedEvaluator,
                    objectives: tuple[str, ...], n_pool: int, local_sigma: float,
                    rng: np.random.Generator) -> np.ndarray:
    """Half a scrambled-Sobol' cover of the box, half Gaussian perturbations of the
    current feasible front (or of the least-violating designs while there is none)."""
    k = evaluator.space.n_active
    n_global = n_pool // 2
    sobol = qmc.Sobol(d=k, scramble=True, seed=rng).random(n_global)
    feasible = [row for row in rows if row["feasible"]]
    if feasible:
        front = pareto_front(np.array([[row[name] for name in objectives]
                                       for row in feasible], dtype=float))
        anchors = unit_inputs([feasible[i] for i in front], evaluator.space)
    else:
        physics = [row for row in rows if has_physics(row)]
        anchors = unit_inputs(physics or rows, evaluator.space)
    picks = anchors[rng.integers(0, len(anchors), n_pool - n_global)]
    local = np.clip(picks + local_sigma * rng.standard_normal(picks.shape), 0.0, 1.0)
    return np.vstack([sobol, local])


def run_bo_parego(evaluator: BudgetedEvaluator, settings: dict[str, Any],
                  objectives: tuple[str, ...], hv_cfg: dict[str, Any], *,
                  prediction_log: list[dict[str, Any]] | None = None) -> None:
    """GP surrogate + ParEGO/EI x probability-of-feasibility acquisition, batched.

    `prediction_log`, if given, receives one record per proposed design with the
    surrogate's prediction made BEFORE the design was evaluated - the prospective
    held-out test of section 25 (scored later against the candidate log).
    """
    if len(objectives) != 2:
        raise ValueError("bo_parego is written for exactly two objectives")
    space, k = evaluator.space, evaluator.space.n_active
    rng = np.random.default_rng(evaluator.seed)
    ideal = np.array([hv_cfg["ideal_point"][name] for name in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][name] for name in objectives], dtype=float)
    batch, n_pool = int(settings["batch_size"]), int(settings["pool_size"])
    n_mc = int(settings["mc_samples"])
    rows: list[dict[str, Any]] = []

    def record(new_rows: list[dict[str, Any]]) -> None:
        rows.extend(row for row in new_rows if not row["cache_hit"])

    try:
        init = latin_hypercube(min(initial_design_size(settings, k), evaluator.budget), k,
                               evaluator.seed)
        record(evaluator.evaluate(space.from_unit(init), generation=0))
        generation = 1
        while evaluator.remaining > 0:
            q = min(batch, evaluator.remaining)
            if sum(has_physics(row) for row in rows) < MIN_TRAINING_ROWS:
                # not enough physics to fit anything: keep filling space, and say so
                fill = latin_hypercube(q, k, int(rng.integers(0, 2**31 - 1)))
                record(evaluator.evaluate(space.from_unit(fill), generation=generation))
                generation += 1
                continue
            model = DesignSurrogate(space, objectives, seed=evaluator.seed,
                                    transforms=settings.get("transforms"),
                                    n_restarts=int(settings.get("gp_restarts", 2))).fit(rows)
            pool = _candidate_pool(rows, evaluator, objectives, n_pool,
                                   float(settings["local_sigma"]), rng)
            seen = unit_inputs(rows, space)
            pred = model.predict_objectives(pool, on_extrapolation="flag")
            margins = model.predict_margins(pool, on_extrapolation="flag")
            p_valid = model.probability_valid(pool)
            p_feasible = model.probability_feasible(pool)
            draws = np.stack([model.objective_models[name].sample(pred[name], n_mc, rng)
                              for name in objectives], axis=-1)       # (n_mc, n_pool, 2)
            draws_norm = normalise(draws, ideal, ref)
            feasible = [row for row in rows if row["feasible"]]
            f_feasible = (normalise(np.array([[row[name] for name in objectives]
                                              for row in feasible], dtype=float), ideal, ref)
                          if feasible else None)

            available = np.ones(len(pool), dtype=bool)
            near_seen = np.min(np.linalg.norm(pool[:, None, :] - seen[None, :, :], axis=2),
                               axis=1)
            available &= near_seen > _MIN_SEPARATION
            # Guard against EI x PoF chasing optimistic extrapolations: once the front has
            # converged, EI inside the feasible region is ~0 and the product is won by
            # points with a huge prior-mean EI and a ~1% chance of existing at all. Points
            # the model itself gives under `min_probability_feasible` are excluded unless
            # nothing else is left. Added after a one-seed smoke test, before the study ran.
            likely = p_feasible >= float(settings["min_probability_feasible"])
            if np.any(available & likely):
                available &= likely
            chosen: list[int] = []
            weights_used: list[float] = []
            for _ in range(q):
                w1 = float(rng.uniform(0.0, 1.0))
                weights = np.array([w1, 1.0 - w1])
                if f_feasible is None:
                    acquisition = p_feasible.copy()
                else:
                    best = float(np.min(_tchebycheff(f_feasible, weights)))
                    gain = np.maximum(best - _tchebycheff(draws_norm, weights), 0.0)
                    acquisition = gain.mean(axis=0) * p_feasible
                acquisition[~available] = -np.inf
                pick = int(np.argmax(acquisition))
                if not np.isfinite(acquisition[pick]):
                    break
                chosen.append(pick)
                weights_used.append(w1)
                available &= np.linalg.norm(pool - pool[pick], axis=1) > _MIN_SEPARATION
            if not chosen:  # pool exhausted (never seen in practice): keep spending honestly
                fill = latin_hypercube(q, k, int(rng.integers(0, 2**31 - 1)))
                record(evaluator.evaluate(space.from_unit(fill), generation=generation))
                generation += 1
                continue
            x_batch = space.from_unit(pool[chosen])
            if prediction_log is not None:
                for j, pick in enumerate(chosen):
                    outputs = {name: {"mean": float(p.mean[pick]), "std": float(p.std[pick]),
                                      "transform": model.objective_models[name].transform}
                               for name, p in pred.items()}
                    outputs.update({f"margin__{name}": {"mean": float(p.mean[pick]),
                                                        "std": float(p.std[pick]),
                                                        "transform": "identity"}
                                    for name, p in margins.items()})
                    prediction_log.append({
                        "method": evaluator.method, "seed": evaluator.seed,
                        "generation": generation,
                        "candidate_id": evaluator.candidate_id(space.values(x_batch[j])),
                        "weight_first_objective": weights_used[j],
                        "n_train_physics": model.n_physics,
                        "extrapolated": bool(pred[objectives[0]].extrapolated[pick]),
                        "p_valid": float(p_valid[pick]),
                        "p_feasible": float(p_feasible[pick]),
                        "outputs": outputs,
                    })
            record(evaluator.evaluate(x_batch, generation=generation))
            generation += 1
    except BudgetExhausted:
        pass
