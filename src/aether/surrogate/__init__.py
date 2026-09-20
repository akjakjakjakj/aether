"""M5: Gaussian-process surrogates, their held-out validation, and the run-level bundle
(`DesignSurrogate`) used by the Bayesian optimiser and the fidelity-promotion policy.

A surrogate here never evaluates physics and never extrapolates silently: see `gp.py`.
"""

from .gp import ExtrapolationError, GPSurrogate, Prediction, TrainingHull
from .model import MIN_TRAINING_ROWS, DesignSurrogate, has_physics, unit_inputs
from .validation import COVERAGE_LEVELS, holdout_validation, regression_metrics

__all__ = [
    "COVERAGE_LEVELS",
    "MIN_TRAINING_ROWS",
    "DesignSurrogate",
    "ExtrapolationError",
    "GPSurrogate",
    "Prediction",
    "TrainingHull",
    "has_physics",
    "holdout_validation",
    "regression_metrics",
    "unit_inputs",
]
