"""M4 design of experiments: sweeps, Latin Hypercube, global sensitivity, screening.

Spec section 21: before optimising, find out which variables actually move O1, and do not
hand the optimiser the ones that do not. Three complementary experiments, because each
answers a question the others cannot:

  one-at-a-time   what does each variable do ALONE about the reference design? Cheap,
                  exact, readable - and blind to interactions.
  Latin Hypercube what does the whole box look like: how much of it is geometrically
                  valid, how much feasible, which variables decide validity? Works on a
                  box with holes in it.
  Sobol'          first- AND total-order variance-based indices with bootstrap
                  confidence intervals, on an all-valid rectangular sub-box. Total order
                  is what licenses freezing a variable.

Sobol' rather than Morris: one coupled evaluation costs ~0.15 s, so the ~6000 evaluations
a Saltelli design needs for ten variables are a few minutes on six cores. Morris screening
is what one falls back to when that is unaffordable; it is not, so the quantitative
method with confidence intervals is used. Revisit when Fidelity 1 makes evaluations dear.

Every evaluation goes through `BudgetedEvaluator`, hence through `evaluate_design`, and
is persisted - invalid geometries included, with the reason.
"""

from __future__ import annotations

from concurrent.futures import Executor
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from ..optimization.budget import METRIC_NAMES, BudgetedEvaluator
from ..optimization.design_space import DesignSpace
from ..optimization.persistence import CandidateStore
from ..optimization.sampling import (
    given_data_first_order,
    latin_hypercube,
    one_at_a_time,
    saltelli_sample,
    sobol_indices,
)


def output_column(name: str) -> str:
    """Candidate-log column for a sensitivity output: a canonical metric or a diagnostic."""
    return name if name in METRIC_NAMES else f"diag__{name}"


def _evaluate_all(space: DesignSpace, unit: np.ndarray, store: CandidateStore, *,
                  run_id: str, method: str, seed: int, executor: Executor | None,
                  chunk: int = 240) -> pd.DataFrame:
    evaluator = BudgetedEvaluator(space, len(unit), store, run_id=run_id, method=method,
                                  seed=seed, executor=executor)
    rows: list[dict[str, Any]] = []
    for gen, start in enumerate(range(0, len(unit), chunk)):
        rows.extend(evaluator.evaluate(space.from_unit(unit[start:start + chunk]),
                                       generation=gen))
    return pd.DataFrame(rows)


# -- one at a time ----------------------------------------------------------------------
def run_oat(space: DesignSpace, store: CandidateStore, *, n_points: int, run_id: str,
            seed: int, executor: Executor | None) -> tuple[pd.DataFrame, np.ndarray]:
    reference = space.to_unit(np.array([v.reference for v in space.active_variables]))
    unit, swept = one_at_a_time(space.n_active, n_points, reference)
    return _evaluate_all(space, unit, store, run_id=run_id, method="doe_oat", seed=seed,
                         executor=executor), swept


def oat_effects(frame: pd.DataFrame, swept: np.ndarray, space: DesignSpace,
                outputs: list[str]) -> dict[str, Any]:
    """Range of each output over each single-variable sweep (valid points only)."""
    table: dict[str, Any] = {}
    for dim, var in enumerate(space.active_variables):
        sub = frame[swept == dim]
        ok = sub[sub["status"] == "OK"]
        entry: dict[str, Any] = {
            "n_points": int(len(sub)),
            "n_invalid_geometry": int(sub["status"].str.startswith("invalid geometry").sum()),
            "n_not_ok": int((sub["status"] != "OK").sum()),
            "n_feasible": int(sub["feasible"].sum()),
        }
        for out in outputs:
            col = ok[output_column(out)].to_numpy(dtype=float)
            if col.size == 0:
                entry[out] = {"range": float("nan"), "min": float("nan"), "max": float("nan")}
                continue
            entry[out] = {"range": float(col.max() - col.min()), "min": float(col.min()),
                          "max": float(col.max())}
        table[var.name] = entry
    return table


# -- Latin Hypercube --------------------------------------------------------------------
def run_lhs(space: DesignSpace, store: CandidateStore, *, n_samples: int, run_id: str,
            seed: int, executor: Executor | None) -> pd.DataFrame:
    unit = latin_hypercube(n_samples, space.n_active, seed)
    return _evaluate_all(space, unit, store, run_id=run_id, method="doe_lhs", seed=seed,
                         executor=executor)


def lhs_sensitivity(frame: pd.DataFrame, space: DesignSpace, outputs: list[str], *,
                    n_bins: int, seed: int) -> dict[str, Any]:
    """Box statistics, given-data first-order indices and Spearman rank correlations.

    The geometry-validity indicator (1 == `CapsuleGeometry.validate()` accepted it) is
    analysed over ALL samples; the physics outputs over the evaluated samples only.
    """
    names = [v.name for v in space.active_variables]
    x_all = frame[[f"x__{n}" for n in names]].to_numpy(dtype=float)
    valid = ~frame["status"].str.startswith("invalid geometry").to_numpy()
    evaluated = (frame["status"] == "OK").to_numpy()

    reasons = (frame.loc[~frame["feasible"], "failure_reason"]
               .str.replace(r"[-+]?\d+\.?\d*(e[-+]?\d+)?", "#", regex=True).str.slice(0, 90)
               .value_counts().head(8))
    result: dict[str, Any] = {
        "n_samples": int(len(frame)),
        "n_valid_geometry": int(valid.sum()),
        "n_evaluated_ok": int(evaluated.sum()),
        "n_feasible": int(frame["feasible"].sum()),
        "failure_reasons": {str(k): int(v) for k, v in reasons.items()},
        "violation_counts": {
            c.removeprefix("margin__"): int((frame[c] < 0.0).sum())
            for c in frame.columns if c.startswith("margin__") and frame[c].notna().any()
        },
    }

    idx, ci = given_data_first_order(x_all, valid.astype(float), n_bins=n_bins, seed=seed)
    result["validity"] = {n: {"first": float(idx[i]), "ci": [float(ci[i, 0]), float(ci[i, 1])]}
                          for i, n in enumerate(names)}

    x_ok = x_all[evaluated]
    result["outputs"] = {}
    for out in outputs:
        y = frame.loc[evaluated, output_column(out)].to_numpy(dtype=float)
        idx, ci = given_data_first_order(x_ok, y, n_bins=n_bins, seed=seed)
        rho = [float(spearmanr(x_ok[:, i], y).statistic) for i in range(len(names))]
        result["outputs"][out] = {
            n: {"first": float(idx[i]), "ci": [float(ci[i, 0]), float(ci[i, 1])],
                "spearman": rho[i]}
            for i, n in enumerate(names)
        }
    feas = frame[frame["feasible"]]
    result["feasible_objective_max"] = {
        out: (float(feas[output_column(out)].max()) if len(feas) else float("nan"))
        for out in outputs
    }
    return result


# -- Sobol' -----------------------------------------------------------------------------
def run_sobol(space: DesignSpace, store: CandidateStore, *, n_base: int, run_id: str,
              seed: int, executor: Executor | None) -> pd.DataFrame:
    unit = saltelli_sample(n_base, space.n_active, seed)
    return _evaluate_all(space, unit, store, run_id=run_id, method="doe_sobol", seed=seed,
                         executor=executor)


def sobol_table(frame: pd.DataFrame, space: DesignSpace, outputs: list[str], *,
                n_bootstrap: int, confidence: float, seed: int) -> dict[str, Any]:
    names = [v.name for v in space.active_variables]
    not_ok = frame[frame["status"] != "OK"]
    if len(not_ok):
        raise RuntimeError(
            f"{len(not_ok)} of {len(frame)} Saltelli samples did not evaluate cleanly "
            f"(first: '{not_ok['status'].iloc[0]}'). The Sobol' sub-box must be all-valid; "
            "narrow `doe.sobol.sub_box` rather than estimating indices from a biased subset.")
    table: dict[str, Any] = {"n_evaluations": int(len(frame)), "outputs": {}}
    for out in outputs:
        res = sobol_indices(frame[output_column(out)].to_numpy(dtype=float), len(names),
                            n_bootstrap=n_bootstrap, confidence=confidence, seed=seed)
        table["n_base"] = res.n_base
        table["outputs"][out] = {
            "variance": res.variance,
            "variables": {
                n: {"first": float(res.first[i]),
                    "first_ci": [float(res.first_ci[i, 0]), float(res.first_ci[i, 1])],
                    "total": float(res.total[i]),
                    "total_ci": [float(res.total_ci[i, 0]), float(res.total_ci[i, 1])]}
                for i, n in enumerate(names)
            },
        }
    return table


# -- screening --------------------------------------------------------------------------
def screen_variables(space: DesignSpace, sobol: dict[str, Any], lhs: dict[str, Any],
                     screening_cfg: dict[str, Any]) -> dict[str, Any]:
    """Apply the PRE-DECLARED freeze rule (configs/design_space.yaml `doe.screening`).

    A `design` variable is frozen iff its total-order index upper confidence bound is
    below the threshold for every screened output AND its validity index upper bound is
    below its threshold. `given` and `deferred` variables are never optimised, whatever
    their sensitivity; their indices are reported because M7 needs them.
    """
    t_total = float(screening_cfg["total_index_threshold"])
    t_valid = float(screening_cfg["validity_index_threshold"])
    decisions: dict[str, Any] = {}
    for var in space.variables:
        uppers = {out: spec["variables"][var.name]["total_ci"][1]
                  for out, spec in sobol["outputs"].items()}
        worst_out = max(uppers, key=uppers.get)
        valid_upper = lhs["validity"][var.name]["ci"][1]
        entry = {
            "role": var.role, "reference": var.reference,
            "max_total_index_upper": float(uppers[worst_out]),
            "max_total_index_output": worst_out,
            "validity_index_upper": float(valid_upper),
        }
        if var.role == "given":
            entry.update(decision="frozen", reason="mission given, not a design choice")
        elif var.role == "deferred":
            entry.update(decision="frozen", reason="deferred design variable (A-OPT-2)")
        elif uppers[worst_out] < t_total and valid_upper < t_valid:
            entry.update(decision="frozen",
                         reason=f"total-order upper bound < {t_total} on every output and "
                                f"validity index upper bound < {t_valid}")
        elif uppers[worst_out] < t_total:
            entry.update(decision="active",
                         reason="moves no objective or constraint, but decides which "
                                "geometries are valid")
        else:
            entry.update(decision="active",
                         reason=f"total-order index on {worst_out} is not below {t_total}")
        decisions[var.name] = entry
    return {
        "thresholds": {"total_index": t_total, "validity_index": t_valid},
        "variables": decisions,
        "active": [n for n, d in decisions.items() if d["decision"] == "active"],
        "frozen": [n for n, d in decisions.items() if d["decision"] == "frozen"],
    }
