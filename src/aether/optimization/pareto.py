"""Pareto dominance, hypervolume, spacing and knee-point utilities. Pure numpy.

Conceptual anchor
-----------------
With two objectives there is no single best design, only a set in which improving one
objective must cost the other: the Pareto front. Three numbers describe how good a
front is, and M5 will compare optimisers on exactly these:

  hypervolume   the area between the front and a FIXED reference point - one number that
                rewards both getting closer to the ideal and covering the trade-off
  spacing       how evenly the front is sampled (0 == perfectly even)
  size          how many non-dominated designs were found

ALL OBJECTIVES ARE MINIMISED everywhere in this module. NR-04 recorded an inverted
dominance test in an earlier version of `pareto_front`; the convention is therefore
stated in every docstring and pinned by hand-worked cases in tests/test_pareto.py.
"""

from __future__ import annotations

import numpy as np


def dominates(a: np.ndarray, b: np.ndarray) -> bool:
    """True iff `a` Pareto-dominates `b` (minimisation).

    a dominates b  <=>  a is no worse than b in EVERY objective and strictly better in
    AT LEAST ONE. Equal points do not dominate each other. A point with a NaN objective
    dominates nothing and is dominated by nothing - it is not a measurement.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    if np.any(np.isnan(a)) or np.any(np.isnan(b)):
        return False
    return bool(np.all(a <= b) and np.any(a < b))


def pareto_front(points: np.ndarray) -> np.ndarray:
    """Indices of the non-dominated rows of `points`. All objectives are MINIMISED.

    Row i is non-dominated iff no other row j is at least as good in every objective and
    strictly better in at least one. Self-comparison is harmless: `points[i] <= points[i]`
    holds everywhere but `points[i] < points[i]` holds nowhere, so a point never dominates
    itself. Exact duplicates of a non-dominated point are all kept. Rows containing NaN
    are never returned.

    A correct front must be monotone in a 2-objective problem - if a plotted front
    zigzags, this function is wrong, not the data.
    """
    points = np.asarray(points, dtype=float)
    if points.ndim != 2:
        raise ValueError(f"points must be 2-D (n_points, n_objectives), got {points.shape}")
    n = points.shape[0]
    keep = ~np.any(np.isnan(points), axis=1)
    for i in range(n):
        if not keep[i]:
            continue
        dominates_i = (
            np.all(points <= points[i], axis=1) & np.any(points < points[i], axis=1)
        )
        if np.any(dominates_i):
            keep[i] = False
    return np.flatnonzero(keep)


def hypervolume_2d(points: np.ndarray, reference_point: np.ndarray) -> float:
    """Exact 2-objective hypervolume (minimisation) against `reference_point`.

    The area of the region that is dominated by at least one point AND dominates the
    reference point. Points that do not strictly dominate the reference point in both
    objectives contribute nothing (they are not clipped onto the box - a design worse
    than the reference is worth zero, not a sliver). Units: product of the two objective
    units; pass normalised points for a dimensionless value.

    Algorithm: keep the non-dominated points inside the box, sort by the first objective
    ascending (the second is then strictly descending) and sum the staircase rectangles

        HV = sum_i (f1_{i+1} - f1_i) * (r2 - f2_i),      f1_{n+1} := r1.
    """
    points = np.asarray(points, dtype=float)
    ref = np.asarray(reference_point, dtype=float)
    if ref.shape != (2,):
        raise ValueError("hypervolume_2d needs a 2-component reference point")
    if points.size == 0:
        return 0.0
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError(f"points must have shape (n, 2), got {points.shape}")
    inside = points[np.all(points < ref, axis=1)]
    if inside.shape[0] == 0:
        return 0.0
    front = inside[pareto_front(inside)]
    front = np.unique(front, axis=0)  # sorted by f1, then f2; duplicates removed
    right_edges = np.append(front[1:, 0], ref[0])
    return float(np.sum((right_edges - front[:, 0]) * (ref[1] - front[:, 1])))


def normalise(points: np.ndarray, ideal_point: np.ndarray,
              reference_point: np.ndarray) -> np.ndarray:
    """Affine map sending `ideal_point` to 0 and `reference_point` to 1, per objective."""
    ideal = np.asarray(ideal_point, dtype=float)
    ref = np.asarray(reference_point, dtype=float)
    if np.any(ref <= ideal):
        raise ValueError("reference point must exceed the ideal point in every objective")
    return (np.asarray(points, dtype=float) - ideal) / (ref - ideal)


def normalised_hypervolume(points: np.ndarray, ideal_point: np.ndarray,
                           reference_point: np.ndarray) -> float:
    """Hypervolume as a fraction of the ideal-to-reference rectangle. Lies in [0, 1] as
    long as no point is better than the ideal point."""
    points = np.asarray(points, dtype=float)
    if points.size == 0:
        return 0.0
    return hypervolume_2d(normalise(points, ideal_point, reference_point), np.ones(2))


def spacing_metric(front: np.ndarray) -> float:
    """Schott's spacing: standard deviation of nearest-neighbour L1 distances on a front.

        d_i = min_{j != i} sum_m |f_m^i - f_m^j|,   S = sqrt( sum (d_i - mean d)^2 / (n-1) )

    0 means perfectly even sampling. Pass NORMALISED objectives, otherwise the objective
    with the larger numbers decides the answer. NaN for fewer than 3 points, where the
    statistic is not meaningful.
    """
    front = np.asarray(front, dtype=float)
    n = front.shape[0] if front.ndim == 2 else 0
    if n < 3:
        return float("nan")
    dist = np.sum(np.abs(front[:, None, :] - front[None, :, :]), axis=2)
    np.fill_diagonal(dist, np.inf)
    nearest = np.min(dist, axis=1)
    return float(np.sqrt(np.sum((nearest - nearest.mean()) ** 2) / (n - 1)))


def knee_point(front: np.ndarray) -> int:
    """Index (into `front`) of the knee of a 2-objective front. Pass NORMALISED objectives.

    The knee is the point furthest from the straight line joining the two extreme points
    of the front, on the side towards the ideal - where giving up a little more of one
    objective stops buying much of the other. A definition with no weights in it, which
    is why it is used for the 'joint' design instead of a weighted sum. With fewer than
    three points the lower-first-objective extreme is returned.
    """
    front = np.asarray(front, dtype=float)
    if front.ndim != 2 or front.shape[1] != 2 or front.shape[0] == 0:
        raise ValueError(f"front must have shape (n >= 1, 2), got {front.shape}")
    if front.shape[0] < 3:
        return int(np.argmin(front[:, 0]))
    a = front[int(np.argmin(front[:, 0]))]
    b = front[int(np.argmin(front[:, 1]))]
    chord = b - a
    length = float(np.hypot(*chord))
    if length == 0.0:
        return int(np.argmin(front[:, 0]))
    # signed distance; positive == on the ideal side of the chord
    rel = front - a
    signed = (chord[0] * rel[:, 1] - chord[1] * rel[:, 0]) / length
    return int(np.argmax(-signed))
