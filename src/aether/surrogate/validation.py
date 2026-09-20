"""Held-out accuracy and uncertainty calibration of a surrogate (spec section 25).

Conceptual anchor
-----------------
Two different questions, never to be merged into one number:

  accuracy      how far is the predicted mean from what the evaluator then said?
                RMSE, MAE, R^2 on points the model never trained on.
  calibration   when the model says "+/- 1 sigma", is the truth inside that band about
                68% of the time? A model can be accurate and overconfident, or sloppy
                and honest. Coverage of the central 50/68/90/95% predictive intervals is
                reported against the nominal level, plus the standard deviation of the
                z-scores (1 == calibrated, > 1 == overconfident, < 1 == underconfident).

Everything is computed in the surrogate's MODELLED space (log10 for heat flux), because
that is where its Gaussian predictive distribution lives.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import norm

from .gp import GPSurrogate

COVERAGE_LEVELS = (0.50, 0.68, 0.90, 0.95)


def regression_metrics(truth: np.ndarray, mean: np.ndarray, std: np.ndarray) -> dict[str, Any]:
    """Accuracy and calibration of Gaussian predictions (mean, std) against `truth`."""
    truth, mean, std = (np.asarray(a, dtype=float) for a in (truth, mean, std))
    n = int(truth.size)
    if n == 0:
        return {"n": 0}
    err = mean - truth
    ss_tot = float(np.sum((truth - truth.mean()) ** 2))
    z = err / std
    out: dict[str, Any] = {
        "n": n,
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mae": float(np.mean(np.abs(err))),
        "r2": float(1.0 - np.sum(err ** 2) / ss_tot) if ss_tot > 0.0 else float("nan"),
        "z_mean": float(z.mean()),
        "z_std": float(z.std(ddof=1)) if n > 1 else float("nan"),
        "coverage": {},
    }
    for level in COVERAGE_LEVELS:
        half_width = norm.ppf(0.5 + level / 2.0)
        out["coverage"][f"{level:.2f}"] = float(np.mean(np.abs(z) <= half_width))
    return out


def holdout_validation(surrogate: GPSurrogate, x_train: np.ndarray, y_train: np.ndarray,
                       x_test: np.ndarray, y_test: np.ndarray) -> dict[str, Any]:
    """Fit on the training split, score on the held-out split.

    Test points outside the training hull are NOT silently scored with the rest: they
    are counted, and accuracy/calibration are reported separately for the inside-hull
    and outside-hull subsets, so the cost of extrapolating is visible.
    """
    surrogate.fit(x_train, y_train)
    pred = surrogate.predict(x_test, on_extrapolation="flag")
    truth = surrogate.forward(y_test)
    inside = ~pred.extrapolated
    return {
        "output": surrogate.name, "transform": surrogate.transform,
        "n_train": int(len(x_train)), "n_test": int(len(x_test)),
        "n_test_outside_hull": int(np.sum(~inside)),
        "inside_hull": regression_metrics(truth[inside], pred.mean[inside], pred.std[inside]),
        "outside_hull": regression_metrics(truth[~inside], pred.mean[~inside],
                                           pred.std[~inside]),
        "all": regression_metrics(truth, pred.mean, pred.std),
    }
