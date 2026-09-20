"""Post-processing of a candidate log: fronts, hypervolume histories, design selection
and the metric-gaming audit. Works on the persisted DataFrame only - it never evaluates
anything, so re-running it on an old run reproduces that run's report exactly.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .design_space import DesignSpace
from .pareto import knee_point, normalise, normalised_hypervolume, pareto_front


def _points(hv_cfg: dict[str, Any], objectives: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
    ideal = np.array([hv_cfg["ideal_point"][name] for name in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][name] for name in objectives], dtype=float)
    return ideal, ref


def feasible_front(frame: pd.DataFrame, objectives: tuple[str, ...]) -> pd.DataFrame:
    """Non-dominated FEASIBLE candidates, one row per distinct OBJECTIVE vector, sorted by
    the first objective. Cache-hit rows are duplicates of an earlier row and are dropped.

    Designs that differ only in a variable the model cannot see (at Fidelity 0: cone
    half-angle) have bit-identical objectives. `pareto_front` rightly keeps all of them,
    but counting them would inflate the front size and distort the spacing metric, so the
    first-evaluated representative of each objective vector is kept."""
    feas = (frame[frame["feasible"]].drop_duplicates("candidate_id")
            .drop_duplicates(list(objectives)))
    if feas.empty:
        return feas
    idx = pareto_front(feas[list(objectives)].to_numpy(dtype=float))
    return feas.iloc[idx].sort_values(objectives[0]).reset_index(drop=True)


def hypervolume_curve(frame: pd.DataFrame, objectives: tuple[str, ...],
                      hv_cfg: dict[str, Any], checkpoints: np.ndarray) -> np.ndarray:
    """Normalised hypervolume of the feasible set after each checkpoint's worth of budget.

    `budget_index` is the number of budget units spent when the row was produced, so the
    curve is a function of what was PAID, and cache hits cannot move it.
    """
    ideal, ref = _points(hv_cfg, objectives)
    feas = frame[frame["feasible"] & ~frame["cache_hit"]]
    spent = feas["budget_index"].to_numpy()
    values = feas[list(objectives)].to_numpy(dtype=float)
    return np.array([normalised_hypervolume(values[spent <= n], ideal, ref)
                     for n in checkpoints])


def select_designs(front: pd.DataFrame, objectives: tuple[str, ...],
                   hv_cfg: dict[str, Any]) -> dict[str, pd.Series]:
    """The three designs the report compares, all taken FROM THE FEASIBLE FRONT.

    peak_flux_only   what a conventional single-objective process would pick
    bondline_only    the opposite extreme of the front
    joint_knee       the knee of the normalised front (no weights involved)
    """
    if front.empty:
        return {}
    ideal, ref = _points(hv_cfg, objectives)
    norm = normalise(front[list(objectives)].to_numpy(dtype=float), ideal, ref)
    return {
        "peak_flux_only": front.iloc[int(np.argmin(norm[:, 0]))],
        "joint_knee": front.iloc[knee_point(norm)],
        "bondline_only": front.iloc[int(np.argmin(norm[:, 1]))],
    }


def audit_exploits(frame: pd.DataFrame, front: pd.DataFrame, space: DesignSpace,
                   objectives: tuple[str, ...], audit_cfg: dict[str, Any]) -> dict[str, Any]:
    """Look for an optimiser winning on a model artefact instead of on physics.

    Checks, each on the final feasible front:
      * variables parked within `bound_tolerance_fraction` of a box bound
      * constraints that are active (normalised margin < 1%)
      * share of the external heat load accumulated above 86 km, where the atmosphere
        is a flagged log-interpolated table (A-ATM-2)
      * bondline still warming when the soak-out window closed (NR-02 revisited)
      * counterfactual: for each constraint, how many front designs of the problem
        WITHOUT that constraint would violate it - i.e. what the optimiser does when the
        constraint is not there to stop it.
    """
    tol = float(audit_cfg["bound_tolerance_fraction"])
    report: dict[str, Any] = {"n_front": int(len(front))}
    if front.empty:
        return report

    parked: dict[str, dict[str, Any]] = {}
    for var in space.active_variables:
        col = front[f"x__{var.name}"].to_numpy(dtype=float)
        at_lo = int(np.sum(col <= var.lower + tol * var.span))
        at_hi = int(np.sum(col >= var.upper - tol * var.span))
        parked[var.name] = {
            "at_lower": at_lo, "at_upper": at_hi, "lower": var.lower, "upper": var.upper,
            "front_min": float(col.min()), "front_max": float(col.max()),
        }
    report["parked_on_bounds"] = parked

    margin_cols = [c for c in front.columns if c.startswith("margin__")]
    report["active_constraints"] = {
        c.removeprefix("margin__"): {
            "n_active": int(np.sum(front[c].to_numpy(dtype=float) < 0.01)),
            "min_margin": float(np.nanmin(front[c].to_numpy(dtype=float))),
        }
        for c in margin_cols if front[c].notna().any()
    }

    high = front["diag__heat_load_fraction_above_86km"].to_numpy(dtype=float)
    limit = float(audit_cfg["max_heat_load_fraction_above_86km"])
    report["heat_load_above_86km"] = {
        "max_fraction": float(np.nanmax(high)), "limit": limit,
        "n_over": int(np.sum(high > limit)),
    }
    rate = front["diag__bondline_end_rate_k_s"].to_numpy(dtype=float)
    rate_limit = float(audit_cfg["max_bondline_end_rate_k_s"])
    report["soak_truncation"] = {
        "max_end_rate_k_s": float(np.nanmax(rate)), "limit_k_s": rate_limit,
        "n_still_warming": int(np.sum(rate > rate_limit)),
    }

    evaluated = frame[(frame["status"] == "OK")].drop_duplicates("candidate_id")
    counterfactual: dict[str, Any] = {}
    for col in margin_cols:
        name = col.removeprefix("margin__")
        if not evaluated[col].notna().any():
            continue
        others = [c for c in margin_cols if c != col]
        ok_without = np.ones(len(evaluated), dtype=bool)
        for other in others:
            vals = evaluated[other].to_numpy(dtype=float)
            ok_without &= np.isnan(vals) | (vals >= 0.0)
        relaxed = evaluated[ok_without]
        if relaxed.empty:
            continue
        idx = pareto_front(relaxed[list(objectives)].to_numpy(dtype=float))
        relaxed_front = relaxed.iloc[idx]
        violating = relaxed_front[relaxed_front[col] < 0.0]
        counterfactual[name] = {
            "n_front_without_constraint": int(len(relaxed_front)),
            "n_of_those_violating_it": int(len(violating)),
            "worst_margin": float(relaxed_front[col].min()),
        }
    report["counterfactual_without_constraint"] = counterfactual
    return report
