"""The surrogate of one optimisation run: a GP per objective, a GP per constraint margin,
and a classifier for "does this design produce a physics result at all".

Trained ONLY on candidates the run has already paid for (rows of the candidate log).
Nothing here calls the evaluator, and nothing here is told the analytic geometry rule:
the valid region is learnt from the designs that came back `invalid geometry`, exactly as
every other optimiser has to learn it (ASSUMPTIONS A-AI-2).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import norm

from ..optimization.budget import MARGIN_NAMES
from ..optimization.design_space import DesignSpace
from .gp import GPSurrogate, Prediction

MIN_TRAINING_ROWS = 6
"""Fewer evaluated designs than this and no GP is fitted; the caller falls back to
space-filling samples. With 4 active inputs a GP on fewer points is decoration."""


def unit_inputs(rows: list[dict[str, Any]], space: DesignSpace) -> np.ndarray:
    x = np.array([[row[f"x__{name}"] for name in space.active] for row in rows], dtype=float)
    return space.to_unit(x) if len(rows) else np.empty((0, space.n_active))


def has_physics(row: dict[str, Any]) -> bool:
    return row["status"] == "OK"


class DesignSurrogate:
    def __init__(self, space: DesignSpace, objectives: tuple[str, ...], *, seed: int,
                 transforms: dict[str, str] | None = None, n_restarts: int = 2):
        self.space, self.objectives = space, tuple(objectives)
        self.seed, self.n_restarts = int(seed), int(n_restarts)
        self.transforms = dict(transforms or {})
        self.objective_models: dict[str, GPSurrogate] = {}
        self.margin_models: dict[str, GPSurrogate] = {}
        self._validity: GPSurrogate | None = None
        self._validity_constant: float | None = None
        self.n_physics = 0

    @property
    def fitted(self) -> bool:
        return bool(self.objective_models)

    def fit(self, rows: list[dict[str, Any]]) -> DesignSurrogate:
        """Fit on a run's evaluated rows. Rows without physics train only the classifier."""
        rows = [row for row in rows if not row.get("cache_hit", False)]
        physics = [row for row in rows if has_physics(row)]
        self.n_physics = len(physics)
        if self.n_physics < MIN_TRAINING_ROWS:
            raise ValueError(f"only {self.n_physics} evaluated designs with a physics "
                             f"result; need {MIN_TRAINING_ROWS} to fit a surrogate")
        x_phys = unit_inputs(physics, self.space)
        self.objective_models = {
            name: GPSurrogate(name, transform=self.transforms.get(name, "identity"),
                              seed=self.seed, n_restarts=self.n_restarts
                              ).fit(x_phys, np.array([row[name] for row in physics]))
            for name in self.objectives
        }
        self.margin_models = {}
        for name in MARGIN_NAMES:
            values = np.array([row[f"margin__{name}"] for row in physics], dtype=float)
            if np.any(~np.isfinite(values)) or np.ptp(values) == 0.0:
                continue  # a null limit (A-LIM-2) has no margin to model
            self.margin_models[name] = GPSurrogate(
                f"margin__{name}", seed=self.seed, n_restarts=self.n_restarts
            ).fit(x_phys, values)

        labels = np.array([has_physics(row) for row in rows], dtype=int)
        self._validity, self._validity_constant = None, None
        if labels.min() == labels.max():
            self._validity_constant = float(labels[0])
        else:
            # Least-squares GP classification: regress the labels -1 / +1 and squash the
            # predictive distribution through a probit. Cruder than a Laplace-approximated
            # GP classifier, but sklearn's one returned NaN probabilities (negative latent
            # variance) as soon as the batch clustered near the front, which silently
            # switched the acquisition off; this one cannot. Its probabilities are scored
            # on held-out designs like every other prediction here.
            self._validity = GPSurrogate("validity", seed=self.seed,
                                         n_restarts=self.n_restarts
                                         ).fit(unit_inputs(rows, self.space),
                                               2.0 * labels - 1.0)
        return self

    # -- predictions -------------------------------------------------------------------
    def predict_objectives(self, x_unit: np.ndarray, *, on_extrapolation: str = "raise"
                           ) -> dict[str, Prediction]:
        return {name: model.predict(x_unit, on_extrapolation=on_extrapolation)
                for name, model in self.objective_models.items()}

    def predict_margins(self, x_unit: np.ndarray, *, on_extrapolation: str = "raise"
                        ) -> dict[str, Prediction]:
        return {name: model.predict(x_unit, on_extrapolation=on_extrapolation)
                for name, model in self.margin_models.items()}

    def probability_valid(self, x_unit: np.ndarray) -> np.ndarray:
        x_unit = np.atleast_2d(np.asarray(x_unit, dtype=float))
        if self._validity is None:
            if self._validity_constant is None:
                raise RuntimeError("DesignSurrogate has not been fitted")
            return np.full(len(x_unit), self._validity_constant)
        pred = self._validity.predict(x_unit, on_extrapolation="flag")
        return norm.cdf(pred.mean / pred.std)

    def probability_feasible(self, x_unit: np.ndarray) -> np.ndarray:
        """P(physics result) x prod_j P(margin_j >= 0), margins treated as independent.

        A classifier/GP probability, not a measurement; outside the training hull it is
        a flagged guess like any other prediction here.
        """
        prob = self.probability_valid(x_unit)
        for pred in self.predict_margins(x_unit, on_extrapolation="flag").values():
            prob = prob * norm.cdf(pred.mean / pred.std)
        return prob
