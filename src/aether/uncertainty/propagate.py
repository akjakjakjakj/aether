"""Propagation of the declared uncertainty through the canonical evaluator (spec §27).

Conceptual anchor
-----------------
One design in, one output DISTRIBUTION out. Every sample is a full coupled evaluation -
geometry, aerodynamics, trajectory, heating, conduction - because the quantities that
matter are not linear in the inputs and cannot be propagated by a sensitivity matrix. A
10% denser atmosphere does not give 5% more peak flux (sqrt(rho)); it decelerates the
vehicle earlier, so V is lower when the dense air arrives, and the measured answer on the
baseline is +0.2%. That coupling is the reason this is Monte Carlo and not algebra.

What comes out, and in what form
--------------------------------
    combined    statistics of the pooled sample - the MIXTURE of variability and
                ignorance. Reportable, and always labelled as a mixture.
    per_branch  the same statistics inside each epistemic branch. The spread of ONE curve
                is variability; the gap BETWEEN curves is ignorance.
    band        for each percentile, the interval it spans across the epistemic branches.
                This is the p-box view and it is the primary result for a design decision,
                because it does not require pretending that a band between two NASA
                reports is a probability distribution.
    violations  P(constraint violated), with a confidence interval, never as a bare zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..optimization.budget import MARGIN_NAMES, BudgetedEvaluator, BudgetExhausted
from .sampling import DrawSet
from .space import UncertainDesignSpace
from .statistics import (
    DEFAULT_PERCENTILES,
    ViolationProbability,
    converged,
    convergence_table,
    quantile,
    summarise,
    violation_probability,
)

DEFAULT_OUTPUTS = (
    "peak_heat_flux_w_m2",
    "integrated_external_heat_j_m2",
    "peak_surface_temperature_k",
    "peak_bondline_temperature_k",
    "bondline_exposure_metric_k_s",
    "thermal_penetration_depth_m",
    "max_g",
    "max_dynamic_pressure_pa",
    "entry_duration_s",
)


@dataclass
class DesignPropagation:
    """The full uncertainty picture for ONE design."""

    label: str
    design_values: dict[str, float]
    rows: pd.DataFrame
    outputs: tuple[str, ...]
    combined: dict[str, Any] = field(default_factory=dict)
    per_branch: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    band: dict[str, dict[str, Any]] = field(default_factory=dict)
    decomposition: dict[str, Any] = field(default_factory=dict)
    violations: dict[str, ViolationProbability] = field(default_factory=dict)
    convergence: dict[str, Any] = field(default_factory=dict)
    n_not_evaluable: int = 0
    nominal: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "design_values": self.design_values,
            "n_samples": int(len(self.rows)),
            "n_not_evaluable": self.n_not_evaluable,
            "outputs": list(self.outputs),
            "nominal": self.nominal,
            "combined": self.combined,
            "per_branch": self.per_branch,
            "band": self.band,
            "decomposition": self.decomposition,
            "violations": {k: v.to_dict() for k, v in self.violations.items()},
            "convergence": self.convergence,
        }


# ---------------------------------------------------------------------------------------
# running the samples
# ---------------------------------------------------------------------------------------

def evaluate_under_uncertainty(evaluator: BudgetedEvaluator, space: UncertainDesignSpace,
                               x_design: np.ndarray, draw_indices,
                               *, generation: int = 0, chunk: int = 256) -> pd.DataFrame:
    """Run one design over `draw_indices`, through the budget wrapper. Returns its rows.

    Submitted in chunks so that a long study leaves partial results on disk and so that
    the process pool is fed steadily rather than in one enormous map. A `BudgetExhausted`
    stops the loop and returns what was paid for - it is never swallowed silently; the
    caller sees a short frame and reports it.
    """
    vectors = space.design_vectors(np.atleast_2d(x_design), draw_indices)
    rows: list[dict[str, Any]] = []
    try:
        for start in range(0, len(vectors), chunk):
            rows.extend(evaluator.evaluate(vectors[start:start + chunk],
                                           generation=generation))
    except BudgetExhausted:
        pass
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------
# reducing them
# ---------------------------------------------------------------------------------------

def _series(frame: pd.DataFrame, name: str) -> np.ndarray:
    return frame[name].to_numpy(dtype=float)


def analyse(label: str, frame: pd.DataFrame, draws: DrawSet, *,
            design_values: dict[str, float],
            outputs: tuple[str, ...] = DEFAULT_OUTPUTS,
            percentiles: tuple[float, ...] = DEFAULT_PERCENTILES,
            confidence: float = 0.95,
            convergence_checkpoints: tuple[int, ...] = (),
            convergence_output: str = "peak_bondline_temperature_k",
            convergence_tolerance_rel: float = 0.02,
            nominal: dict[str, float] | None = None,
            seed: int = 0) -> DesignPropagation:
    """Reduce one design's sample frame to the reported statistics.

    `frame` must carry one row per draw, in draw order, so that `draws.epistemic_index`
    lines up with it. The caller guarantees that by submitting `space.design_vectors`,
    which emits draw-fastest.
    """
    if len(frame) != len(draws):
        raise ValueError(f"{label}: {len(frame)} rows for {len(draws)} draws - the sample "
                         "and the draw set have gone out of step; statistics would be "
                         "attributed to the wrong epistemic branch")

    not_evaluable = (frame["status"].to_numpy() != "OK")
    result = DesignPropagation(label=label, design_values=dict(design_values),
                               rows=frame, outputs=tuple(outputs),
                               n_not_evaluable=int(not_evaluable.sum()),
                               nominal=dict(nominal or {}))

    # -- combined (mixture) -------------------------------------------------------------
    for name in outputs:
        result.combined[name] = summarise(_series(frame, name), percentiles).to_dict()

    # -- per epistemic branch, and the band across branches -----------------------------
    n_branches = draws.n_epistemic_branches
    for name in outputs:
        branch_rows: list[dict[str, Any]] = []
        for b in range(n_branches):
            idx = draws.branch(b)
            summary = summarise(_series(frame.iloc[idx], name), percentiles).to_dict()
            branch_rows.append({"branch": b, **summary})
        result.per_branch[name] = branch_rows
        keys = [f"p{p:g}" for p in percentiles]
        band: dict[str, Any] = {}
        for key in [*keys, "mean"]:
            vals = np.array([r["percentiles"][key] if key in r["percentiles"] else r[key]
                             for r in branch_rows], dtype=float)
            finite = vals[np.isfinite(vals)]
            band[key] = {"min": float(finite.min()) if finite.size else float("nan"),
                         "max": float(finite.max()) if finite.size else float("nan"),
                         "n_branches": int(finite.size)}
        result.band[name] = band

    # -- variance decomposition ---------------------------------------------------------
    result.decomposition = {name: _decompose(_series(frame, name), draws)
                            for name in outputs}

    # -- constraint violation probabilities ---------------------------------------------
    for name in MARGIN_NAMES:
        column = f"margin__{name}"
        if column not in frame.columns:
            continue
        margins = _series(frame, column)
        if not np.any(np.isfinite(margins)):
            continue     # constraint not declared (a null limit is skipped, A-LIM-2)
        result.violations[name] = violation_probability(
            name, np.isfinite(margins) & (margins < 0.0),
            not_evaluable=not_evaluable, confidence=confidence)
    result.violations["any"] = violation_probability(
        "any", ~frame["feasible"].to_numpy(dtype=bool) & ~not_evaluable,
        not_evaluable=not_evaluable, confidence=confidence)

    # -- convergence ---------------------------------------------------------------------
    if convergence_checkpoints:
        stats = {"mean": lambda a: float(np.mean(a)),
                 "p95": lambda a: float(np.percentile(a, 95.0))}
        table = convergence_table(_series(frame, convergence_output),
                                  convergence_checkpoints, stats, seed=seed,
                                  confidence=confidence)
        result.convergence = {
            "output": convergence_output,
            "table": table,
            "verdict": {label_: converged(table, label_, convergence_tolerance_rel)
                        for label_ in stats},
            "tolerance_rel": convergence_tolerance_rel,
        }
    return result


def _decompose(values: np.ndarray, draws: DrawSet) -> dict[str, Any]:
    """Split the variance by the law of total variance, and say what that assumes.

        Var(Y) = E_e[ Var_a(Y | e) ]  +  Var_e[ E_a(Y | e) ]
                 \\_____aleatory_____/    \\_____epistemic____/

    The identity is exact for the sampled mixture. What is NOT free is the step before it:
    treating an epistemic BAND - "one of these two NASA reports is right, we do not know
    which" - as a probability distribution at all. Doing so is a subjective-probability
    reading, it is the only way to get a single variance out, and the `band` view exists
    beside this one precisely because it does not require it.

    In `mixed` sampling mode there is one branch, so the epistemic term is zero BY
    CONSTRUCTION and not by measurement. The returned dict says which case it is.
    """
    finite = np.isfinite(values)
    out: dict[str, Any] = {
        "mode": draws.mode,
        "n_branches": int(draws.n_epistemic_branches),
        "separable": bool(draws.mode == "nested" and draws.n_epistemic_branches > 1),
    }
    if not np.any(finite):
        return {**out, "std_total": float("nan"), "std_aleatory": float("nan"),
                "std_epistemic": float("nan"), "epistemic_share_of_variance": float("nan")}
    total = float(np.var(values[finite], ddof=1)) if finite.sum() > 1 else 0.0
    out["std_total"] = float(np.sqrt(total))
    if not out["separable"]:
        return {**out, "std_aleatory": float("nan"), "std_epistemic": float("nan"),
                "epistemic_share_of_variance": float("nan"),
                "note": "mixed sampling: the two sources are pooled by construction"}
    within, means = [], []
    for b in range(draws.n_epistemic_branches):
        idx = draws.branch(b)
        vals = values[idx]
        vals = vals[np.isfinite(vals)]
        if vals.size < 2:
            continue
        within.append(float(np.var(vals, ddof=1)))
        means.append(float(np.mean(vals)))
    if len(means) < 2:
        return {**out, "std_aleatory": float("nan"), "std_epistemic": float("nan"),
                "epistemic_share_of_variance": float("nan"),
                "note": "too few usable branches to separate"}
    var_a = float(np.mean(within))
    var_e = float(np.var(means, ddof=1))
    out.update({
        "std_aleatory": float(np.sqrt(var_a)),
        "std_epistemic": float(np.sqrt(var_e)),
        "std_combined_in_quadrature": float(np.sqrt(var_a + var_e)),
        "epistemic_share_of_variance": float(var_e / (var_a + var_e))
        if (var_a + var_e) > 0 else float("nan"),
        "note": ("aleatory and epistemic are combined by the law of total variance, i.e. "
                 "IN QUADRATURE. That is exact for the sampled mixture and is stated "
                 "explicitly because it is only meaningful if the epistemic band is read "
                 "as a probability distribution - see `band` for the view that is not"),
    })
    return out


def robust_objective_values(frame: pd.DataFrame, objectives: tuple[str, ...],
                            percentile: float) -> dict[str, float]:
    """The robust objective of a sample: the declared percentile of each objective."""
    return {name: quantile(_series(frame, name), percentile) for name in objectives}
