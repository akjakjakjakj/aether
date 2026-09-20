"""Space-filling samples and variance-based sensitivity estimators. Seeded throughout.

Conceptual anchor
-----------------
A sensitivity index answers "if I could pin this one input down, how much of the
output's variance would disappear?".

  first-order  S_i  = Var( E[Y | X_i] ) / Var(Y)     the input's effect on its own
  total-order  ST_i = E( Var[Y | X_~i] ) / Var(Y)    its own effect PLUS every interaction

ST_i ~ 0 is the only safe licence to freeze a variable: S_i ~ 0 alone can hide a variable
that matters only in combination with another. Two estimators are provided because they
need different samples:

  * `sobol_indices`  Saltelli/Jansen estimators on a Saltelli design. Gives S_i AND ST_i
                     but needs a rectangular box where every point can be evaluated.
  * `given_data_first_order`  a binned conditional-mean estimator on ANY sample (here an
                     LHS with invalid designs removed). First-order only, biased upward
                     by roughly (bins - 1)/n, but indifferent to holes in the box.

All samples are returned on the unit hypercube; `DesignSpace.from_unit` scales them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import qmc


def latin_hypercube(n_samples: int, n_dims: int, seed: int) -> np.ndarray:
    """Seeded Latin Hypercube on [0, 1)^k, shape (n_samples, n_dims).

    Defining property (tested): in every dimension, each of the `n_samples` equal-width
    strata [j/n, (j+1)/n) contains EXACTLY one point.
    """
    sampler = qmc.LatinHypercube(d=n_dims, seed=np.random.default_rng(seed))
    return sampler.random(n_samples)


def one_at_a_time(n_dims: int, n_points: int, reference_unit: np.ndarray
                  ) -> tuple[np.ndarray, np.ndarray]:
    """One-at-a-time sweeps about a reference point, on the unit hypercube.

    Returns (samples, swept_dimension): `n_dims * n_points` rows; row r varies only
    dimension `swept_dimension[r]`, over `n_points` evenly spaced values across [0, 1].
    """
    reference_unit = np.asarray(reference_unit, dtype=float)
    grid = np.linspace(0.0, 1.0, n_points)
    samples = np.tile(reference_unit, (n_dims * n_points, 1))
    swept = np.repeat(np.arange(n_dims), n_points)
    for dim in range(n_dims):
        samples[dim * n_points:(dim + 1) * n_points, dim] = grid
    return samples, swept


def saltelli_sample(n_base: int, n_dims: int, seed: int) -> np.ndarray:
    """Saltelli design from a scrambled Sobol' sequence: shape (n_base * (k + 2), k).

    Row layout: A (n_base rows), B (n_base rows), then AB_0 ... AB_{k-1}, where AB_i is A
    with column i taken from B. `n_base` should be a power of two (Sobol' balance).
    """
    sampler = qmc.Sobol(d=2 * n_dims, scramble=True, seed=np.random.default_rng(seed))
    base = sampler.random(n_base)
    a, b = base[:, :n_dims], base[:, n_dims:]
    blocks = [a, b]
    for i in range(n_dims):
        ab = a.copy()
        ab[:, i] = b[:, i]
        blocks.append(ab)
    return np.vstack(blocks)


@dataclass(frozen=True)
class SobolResult:
    """Indices with percentile-bootstrap confidence intervals. Arrays have length k."""

    first: np.ndarray
    first_ci: np.ndarray   # shape (k, 2): lower, upper
    total: np.ndarray
    total_ci: np.ndarray
    variance: float
    n_base: int


def _sobol_point(f_a, f_b, f_ab):
    # Centre first. Sobol' indices are invariant to a constant shift of the output, but
    # the first-order estimator's VARIANCE is not: for an output with a large mean and a
    # small spread (a bondline near 400 K varying by tens of K) the product f(B) * (...)
    # is dominated by mean * noise. Uncentred, the first-order CIs on the bondline came
    # out as wide as [-0.4, 1.1] in the first M4 DOE run; centred they are usable.
    centre = np.mean(np.concatenate([f_a, f_b]))
    f_a, f_b, f_ab = f_a - centre, f_b - centre, f_ab - centre
    variance = np.var(np.concatenate([f_a, f_b]), ddof=1)
    if variance <= 0.0:
        k = f_ab.shape[0]
        return np.zeros(k), np.zeros(k), 0.0
    first = np.mean(f_b[None, :] * (f_ab - f_a[None, :]), axis=1) / variance
    total = 0.5 * np.mean((f_a[None, :] - f_ab) ** 2, axis=1) / variance
    return first, total, float(variance)


def sobol_indices(y: np.ndarray, n_dims: int, *, n_bootstrap: int = 500,
                  confidence: float = 0.95, seed: int = 0) -> SobolResult:
    """First- and total-order Sobol' indices from outputs on a `saltelli_sample` design.

    Estimators: Saltelli et al. (2010) for S_i, Jansen (1999) for ST_i:

        S_i  = mean( f(B) * (f(AB_i) - f(A)) ) / Var(Y)
        ST_i = mean( (f(A) - f(AB_i))^2 ) / (2 Var(Y))

    evaluated on the mean-centred output (see `_sobol_point`).

    Confidence intervals resample the BASE rows with replacement (whole A/B/AB_i tuples
    move together). Any NaN in `y` raises: dropping rows from a Saltelli design silently
    biases every index.
    """
    y = np.asarray(y, dtype=float)
    if y.ndim != 1 or y.size % (n_dims + 2) != 0:
        raise ValueError(f"len(y) = {y.size} is not a multiple of k + 2 = {n_dims + 2}")
    if np.any(~np.isfinite(y)):
        raise ValueError("non-finite outputs in a Saltelli design; indices would be biased")
    n_base = y.size // (n_dims + 2)
    f_a, f_b = y[:n_base], y[n_base:2 * n_base]
    f_ab = y[2 * n_base:].reshape(n_dims, n_base)

    first, total, variance = _sobol_point(f_a, f_b, f_ab)
    rng = np.random.default_rng(seed)
    boot_first = np.empty((n_bootstrap, n_dims))
    boot_total = np.empty((n_bootstrap, n_dims))
    for r in range(n_bootstrap):
        idx = rng.integers(0, n_base, n_base)
        boot_first[r], boot_total[r], _ = _sobol_point(f_a[idx], f_b[idx], f_ab[:, idx])
    alpha = 100.0 * (1.0 - confidence) / 2.0
    return SobolResult(
        first=first, first_ci=np.percentile(boot_first, [alpha, 100.0 - alpha], axis=0).T,
        total=total, total_ci=np.percentile(boot_total, [alpha, 100.0 - alpha], axis=0).T,
        variance=variance, n_base=n_base,
    )


def _binned_index(x: np.ndarray, y: np.ndarray, n_bins: int) -> float:
    variance = np.var(y)
    if variance <= 0.0:
        return 0.0
    order = np.argsort(x, kind="stable")
    groups = np.array_split(y[order], n_bins)
    means = np.array([g.mean() for g in groups])
    weights = np.array([g.size for g in groups], dtype=float) / y.size
    return float(np.sum(weights * (means - y.mean()) ** 2) / variance)


def given_data_first_order(x: np.ndarray, y: np.ndarray, *, n_bins: int = 20,
                           n_bootstrap: int = 300, confidence: float = 0.95,
                           seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """First-order indices from an arbitrary (x, y) sample by equal-count binning.

    S_i ~ Var_bins( mean(y | x_i in bin) ) / Var(y). Returns (index, ci) with shapes (k,)
    and (k, 2). Biased upward by ~ (n_bins - 1)/n even for an inert input, so compare the
    CI against a threshold above that floor, not against zero. If the sample is not a
    rectangular box (invalid designs removed) the inputs are no longer independent and
    the indices are descriptive, not a variance decomposition.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = x.shape
    index = np.array([_binned_index(x[:, i], y, n_bins) for i in range(k)])
    rng = np.random.default_rng(seed)
    boot = np.empty((n_bootstrap, k))
    for r in range(n_bootstrap):
        idx = rng.integers(0, n, n)
        boot[r] = [_binned_index(x[idx, i], y[idx], n_bins) for i in range(k)]
    alpha = 100.0 * (1.0 - confidence) / 2.0
    return index, np.percentile(boot, [alpha, 100.0 - alpha], axis=0).T
