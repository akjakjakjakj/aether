"""Gaussian-process surrogates with an explicit extrapolation guard (spec section 25).

Conceptual anchor
-----------------
A surrogate is a cheap guess at what the evaluator would say. It is only worth anything
if it also says how sure it is, and if it knows where it has never looked. A GP gives a
predictive mean AND a predictive standard deviation; this module adds the second half:

  * every prediction carries an `extrapolated` flag - True when the query point lies
    outside the CONVEX HULL of the training inputs. Inside the hull the GP interpolates
    between things it has seen; outside it, the mean reverts to the prior and the number
    is a guess about a region nobody evaluated.
  * `predict(..., on_extrapolation="raise")` is the default, so a caller that wants a
    number of record outside the hull gets an error, not a silent extrapolation. An
    optimiser's ACQUISITION passes "flag": it is allowed to look outside the hull
    because it is about to BUY an evaluation there, not to trust the prediction.

Inputs are always on the unit hypercube of the active design variables. Outputs can be
modelled through a log10 transform (heat flux spans more than a decade); predictive
intervals and calibration are then stated in the transformed space, where the GP's
Gaussian assumption is made.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy.spatial import Delaunay, QhullError
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

TRANSFORMS = ("identity", "log10")


class ExtrapolationError(ValueError):
    """Raised when a prediction of record is requested outside the training hull."""


class TrainingHull:
    """Convex hull of the training inputs, by Delaunay triangulation.

    With fewer than d + 2 points, or with degenerate (co-planar) points, no hull exists;
    then EVERY query is reported as extrapolated, which is the conservative answer.
    """

    def __init__(self, x_unit: np.ndarray):
        x_unit = np.atleast_2d(np.asarray(x_unit, dtype=float))
        self.n_points, self.n_dims = x_unit.shape
        self._tri: Delaunay | None = None
        if self.n_points >= self.n_dims + 2:
            try:
                self._tri = Delaunay(x_unit)
            except QhullError:
                self._tri = None

    @property
    def defined(self) -> bool:
        return self._tri is not None

    def contains(self, x_unit: np.ndarray) -> np.ndarray:
        x_unit = np.atleast_2d(np.asarray(x_unit, dtype=float))
        if self._tri is None:
            return np.zeros(len(x_unit), dtype=bool)
        return self._tri.find_simplex(x_unit) >= 0


@dataclass(frozen=True)
class Prediction:
    """Predictive distribution in the MODELLED (possibly log10) space, plus the flag.

    `mean`, `std` describe a Gaussian in the transformed space. `central` is the mean
    mapped back to natural units (the median of the implied distribution for log10).
    """

    mean: np.ndarray
    std: np.ndarray
    central: np.ndarray
    extrapolated: np.ndarray


class GPSurrogate:
    """One scalar output as a GP over the unit hypercube. Matern-5/2 with one length
    scale per input (so an input the model cannot see gets a long length scale instead
    of polluting the fit) plus a white-noise term for numerical jitter."""

    def __init__(self, name: str, *, transform: str = "identity", seed: int = 0,
                 n_restarts: int = 2):
        if transform not in TRANSFORMS:
            raise ValueError(f"unknown transform '{transform}', expected {TRANSFORMS}")
        self.name, self.transform = name, transform
        self.seed, self.n_restarts = int(seed), int(n_restarts)
        self._gp: GaussianProcessRegressor | None = None
        self.hull: TrainingHull | None = None
        self.n_train = 0

    # -- transform ---------------------------------------------------------------------
    def forward(self, y: np.ndarray) -> np.ndarray:
        y = np.asarray(y, dtype=float)
        if self.transform == "log10":
            if np.any(y <= 0.0):
                raise ValueError(f"surrogate '{self.name}': log10 transform needs y > 0")
            return np.log10(y)
        return y

    def inverse(self, z: np.ndarray) -> np.ndarray:
        z = np.asarray(z, dtype=float)
        return np.power(10.0, z) if self.transform == "log10" else z

    # -- fit / predict -----------------------------------------------------------------
    def fit(self, x_unit: np.ndarray, y: np.ndarray) -> GPSurrogate:
        x_unit = np.atleast_2d(np.asarray(x_unit, dtype=float))
        z = self.forward(y)
        if x_unit.shape[0] != z.shape[0] or x_unit.shape[0] < 2:
            raise ValueError(f"surrogate '{self.name}': need >= 2 consistent training rows")
        if not (np.all(np.isfinite(x_unit)) and np.all(np.isfinite(z))):
            raise ValueError(f"surrogate '{self.name}': non-finite training data; a design "
                             "with no physics result is not a training point")
        k = x_unit.shape[1]
        kernel = (ConstantKernel(1.0, (1e-3, 1e3))
                  * Matern(length_scale=np.full(k, 0.5), length_scale_bounds=(1e-2, 1e2),
                           nu=2.5)
                  + WhiteKernel(1e-6, (1e-10, 1e-1)))
        self._gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                            n_restarts_optimizer=self.n_restarts,
                                            random_state=self.seed)
        with warnings.catch_warnings():
            # A length scale running into its bound is expected for an inert input.
            warnings.simplefilter("ignore", ConvergenceWarning)
            self._gp.fit(x_unit, z)
        self.hull = TrainingHull(x_unit)
        self.n_train = int(x_unit.shape[0])
        return self

    def predict(self, x_unit: np.ndarray, *, on_extrapolation: str = "raise") -> Prediction:
        """Predict at `x_unit`. `on_extrapolation`: "raise" (default) or "flag"."""
        if self._gp is None or self.hull is None:
            raise RuntimeError(f"surrogate '{self.name}' has not been fitted")
        if on_extrapolation not in ("raise", "flag"):
            raise ValueError("on_extrapolation must be 'raise' or 'flag'")
        x_unit = np.atleast_2d(np.asarray(x_unit, dtype=float))
        outside = ~self.hull.contains(x_unit)
        if on_extrapolation == "raise" and np.any(outside):
            raise ExtrapolationError(
                f"surrogate '{self.name}': {int(outside.sum())} of {len(x_unit)} query "
                f"points lie outside the convex hull of its {self.n_train} training "
                "points; refusing to extrapolate (pass on_extrapolation='flag' to get a "
                "flagged guess)")
        mean, std = self._gp.predict(x_unit, return_std=True)
        return Prediction(mean=mean, std=np.maximum(std, 1e-12), central=self.inverse(mean),
                          extrapolated=outside)

    def sample(self, prediction: Prediction, n_samples: int,
               rng: np.random.Generator) -> np.ndarray:
        """(n_samples, n_points) independent draws in NATURAL units (marginal posterior)."""
        z = prediction.mean + prediction.std * rng.standard_normal(
            (n_samples, prediction.mean.size))
        return self.inverse(z)
