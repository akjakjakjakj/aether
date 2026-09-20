"""How much of the design box can a Fidelity-1 study actually explore?

Conceptual anchor
-----------------
The CFD drag surface refuses a capsule whose forebody shape lies outside the convex hull of
the CFD cases it was fitted to (spec §25: never extrapolate silently). That is right, and it
has a price: the optimiser can only be told anything about the part of the design box that
lies inside that hull. Where CFD happened to be run - and where it happened to converge -
therefore bounds the search. This module MEASURES that bound instead of leaving it implicit:

  * `shape_inside_hull`   is this forebody shape evaluable at every core Mach node?
  * `coverage`            Monte-Carlo fractions of the shape box that are geometrically valid,
                          inside the hull, and both - the honest size of the Fidelity-1 search
                          space;
  * `check_box_inside_hull`  pre-flight for the Saltelli design, which cannot tolerate a single
                          rejected sample: every vertex of the sub-box and a seeded sample of
                          its interior must be valid AND inside the hull, else it raises BEFORE
                          thousands of evaluations are spent.

Nothing here touches the evaluator; it asks the persisted surface the same question the
evaluator would.
"""

from __future__ import annotations

import itertools
from typing import Any

import numpy as np

from ..aerodynamics.cfd_surface import N_MACH_NODES, SHAPE_INPUTS, CfdDragSurface
from ..cfd.design_points import forebody_capsule


def shape_inside_hull(surface: CfdDragSurface, shapes: np.ndarray) -> np.ndarray:
    """Boolean per row of `shapes` (columns = SHAPE_INPUTS): inside the hull at EVERY core
    Mach node, i.e. `cd_model` would not refuse it."""
    shapes = np.atleast_2d(np.asarray(shapes, dtype=float))
    core_max = float(surface.meta.get("mach_core_max") or surface.mach_max)
    nodes = np.exp(np.linspace(np.log(surface.mach_min), np.log(core_max), N_MACH_NODES))
    inside = np.ones(len(shapes), dtype=bool)
    for mach in nodes:
        idx = np.flatnonzero(inside)
        if idx.size == 0:
            break
        inside[idx] = surface.gp.hull.contains(surface.unit(np.full(idx.size, mach),
                                                            shapes[idx]))
    return inside


def forebody_valid(shapes: np.ndarray, diameter_m: float = 1.2) -> np.ndarray:
    """Can this FOREBODY exist at all (neutral afterbody, as in the CFD design)?"""
    out = np.zeros(len(shapes), dtype=bool)
    for i, row in enumerate(np.atleast_2d(shapes)):
        try:
            forebody_capsule(*map(float, row), diameter_m=diameter_m)
            out[i] = True
        except ValueError:
            pass
    return out


def coverage(surface: CfdDragSurface, bounds: dict[str, tuple[float, float]],
             n_samples: int = 20000, seed: int = 0) -> dict[str, Any]:
    """Monte-Carlo coverage of the shape box `bounds` (keys = SHAPE_INPUTS)."""
    lo = np.array([bounds[k][0] for k in SHAPE_INPUTS], dtype=float)
    hi = np.array([bounds[k][1] for k in SHAPE_INPUTS], dtype=float)
    shapes = lo + np.random.default_rng(seed).random((n_samples, 3)) * (hi - lo)
    valid = forebody_valid(shapes)
    inside = shape_inside_hull(surface, shapes)
    both = valid & inside
    se = lambda p: float(np.sqrt(max(p * (1 - p), 0.0) / n_samples))  # noqa: E731
    return {
        "n_samples": int(n_samples), "seed": int(seed),
        "bounds": {k: [float(a), float(b)] for k, a, b in zip(SHAPE_INPUTS, lo, hi,
                                                              strict=True)},
        "fraction_of_box_valid_forebody": float(valid.mean()),
        "fraction_of_box_inside_hull": float(inside.mean()),
        "fraction_of_box_valid_and_inside_hull": float(both.mean()),
        "fraction_of_valid_shapes_inside_hull": float(both.sum() / max(valid.sum(), 1)),
        "standard_error_of_box_fractions": se(float(both.mean())),
        "note": "shape box only (bluntness, cone half-angle, shoulder ratio); diameter, "
                "afterbody and entry variables do not enter the drag surface. 'valid "
                "forebody' uses the CFD design's neutral afterbody, so a full capsule can "
                "still be invalid for afterbody reasons.",
    }


def check_box_inside_hull(surface: CfdDragSurface, bounds: dict[str, tuple[float, float]],
                          n_interior: int = 4096, seed: int = 0) -> dict[str, Any]:
    """Raise ValueError unless every vertex and every sampled interior point of the shape
    box `bounds` is a valid forebody inside the hull. Returns the counts when it passes."""
    lo = np.array([bounds[k][0] for k in SHAPE_INPUTS], dtype=float)
    hi = np.array([bounds[k][1] for k in SHAPE_INPUTS], dtype=float)
    vertices = np.array(list(itertools.product(*zip(lo, hi, strict=True))))
    interior = lo + np.random.default_rng(seed).random((n_interior, 3)) * (hi - lo)
    pts = np.vstack([vertices, interior])
    bad_valid = ~forebody_valid(pts)
    bad_hull = ~shape_inside_hull(surface, pts)
    if bad_valid.any() or bad_hull.any():
        worst = pts[bad_valid | bad_hull][:5]
        raise ValueError(
            f"Saltelli sub-box is not evaluable everywhere at Fidelity 1: {int(bad_valid.sum())}"
            f" of {len(pts)} probe shapes are invalid forebodies and {int(bad_hull.sum())} lie "
            f"outside the CFD hull (first offenders, {SHAPE_INPUTS}: {worst.round(4).tolist()})."
            " Shrink doe.sobol.sub_box until it sits inside the hull; do NOT estimate indices "
            "from the surviving subset.")
    return {"n_vertices": int(len(vertices)), "n_interior": int(n_interior),
            "all_valid_and_inside_hull": True}


def front_hull_audit(front, box: dict[str, tuple[float, float]], surface: CfdDragSurface,
                     step_fraction: float = 0.01) -> dict[str, Any]:
    """Metric-gaming audit, Fidelity 1: is a front design stopped by WHERE CFD WAS RUN?

    For every design on the front, each shape input is stepped by +-`step_fraction` of its
    box range, one at a time. A step can leave the box (a box bound stops the design), make
    the forebody impossible (geometry stops it), or leave the CFD hull while staying a valid
    forebody inside the box - and only that last outcome means the design sits on the edge of
    the region where CFD happened to be run and converge. `front` needs `x__<shape input>`
    columns. Nothing is evaluated."""
    import pandas as pd  # local: keeps module import light

    lo = np.array([box[k][0] for k in SHAPE_INPUTS], dtype=float)
    hi = np.array([box[k][1] for k in SHAPE_INPUTS], dtype=float)
    shapes = front[[f"x__{k}" for k in SHAPE_INPUTS]].to_numpy(dtype=float)
    # `times_diameter` variables are stored as ratios in the x__ columns already
    rows = []
    for i, shape in enumerate(shapes):
        for j, name in enumerate(SHAPE_INPUTS):
            for sign in (-1.0, 1.0):
                probe = shape.copy()
                probe[j] += sign * step_fraction * (hi[j] - lo[j])
                if probe[j] < lo[j] - 1e-12 or probe[j] > hi[j] + 1e-12:
                    outcome = "box_bound"
                elif not forebody_valid(probe[None, :])[0]:
                    outcome = "invalid_forebody"
                elif not shape_inside_hull(surface, probe[None, :])[0]:
                    outcome = "cfd_hull"
                else:
                    outcome = "free"
                rows.append({"design": i, "input": name, "direction": "+" if sign > 0 else "-",
                             "outcome": outcome})
    table = pd.DataFrame(rows)
    on_hull = table[table["outcome"] == "cfd_hull"]
    by_dir = (on_hull.groupby(["input", "direction"]).size().rename("n").reset_index()
              .to_dict(orient="records"))
    stopped = table.groupby(["input", "direction", "outcome"]).size().rename("n").reset_index()
    return {"step_fraction_of_box_range": step_fraction, "n_front": int(len(front)),
            "n_front_on_cfd_hull_boundary": int(on_hull["design"].nunique()),
            "cfd_hull_by_input_and_direction": by_dir,
            "all_outcomes": stopped.to_dict(orient="records")}
