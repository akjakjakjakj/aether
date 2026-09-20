"""Axisymmetric body outlines, and the checks the mesher needs them to pass.

An *outline* is a pair of arrays (x_m, r_m): x along the symmetry axis measured
downstream from the nose, r the radial coordinate. It starts on the axis at the nose
(0, 0) and ends on the axis at the tail (L, 0). This is exactly what
``aether.geometry.capsule.CapsuleGeometry.profile(n_points)`` returns, so any capsule
design point can be passed straight to :func:`aether.cfd.mesh.build_mesh_plan`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Outline:
    """A validated closed axisymmetric outline, nose to tail."""

    x_m: np.ndarray
    r_m: np.ndarray
    name: str = "body"

    @property
    def length_m(self) -> float:
        return float(self.x_m[-1] - self.x_m[0])

    @property
    def max_radius_m(self) -> float:
        return float(self.r_m.max())

    @property
    def frontal_area_m2(self) -> float:
        return float(np.pi * self.max_radius_m**2)

    @property
    def arc_length_m(self) -> np.ndarray:
        """Cumulative arc length along the outline, starting at 0 at the nose."""
        ds = np.hypot(np.diff(self.x_m), np.diff(self.r_m))
        return np.concatenate(([0.0], np.cumsum(ds)))

    def point_at(self, s_m: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
        """(x, r) at arc length s, by linear interpolation along the polyline."""
        s = self.arc_length_m
        return np.interp(s_m, s, self.x_m), np.interp(s_m, s, self.r_m)


def make_outline(x_m, r_m, name: str = "body", axis_tol_m: float = 1e-9) -> Outline:
    """Validate raw (x, r) arrays and return an :class:`Outline`.

    Raises ValueError on anything the mesher cannot handle, rather than producing a mesh
    that fails later in a less obvious way (spec §36: inspect geometry first).
    """
    x = np.asarray(x_m, dtype=float).copy()
    r = np.asarray(r_m, dtype=float).copy()
    if x.ndim != 1 or x.shape != r.shape or x.size < 5:
        raise ValueError("outline needs matching 1-D x and r arrays of at least 5 points")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(r))):
        raise ValueError("outline contains non-finite coordinates")
    if abs(r[0]) > axis_tol_m or abs(r[-1]) > axis_tol_m:
        raise ValueError("outline must start and end on the axis (r = 0)")
    if np.any(r < -axis_tol_m):
        raise ValueError("outline has negative radius")
    r[0] = r[-1] = 0.0
    r = np.clip(r, 0.0, None)
    if np.any(r[1:-1] <= axis_tol_m):
        raise ValueError("outline touches the axis between nose and tail")
    seg = np.hypot(np.diff(x), np.diff(r))
    if np.any(seg <= 0.0):
        raise ValueError("outline has repeated points")
    if x[-1] <= x[0]:
        raise ValueError("tail must be downstream of the nose")
    x -= x[0]
    return Outline(x, r, name)


def sphere_outline(radius_m: float, n_points: int = 721) -> Outline:
    """Full sphere, nose at x = 0, centre at x = R."""
    if radius_m <= 0:
        raise ValueError("radius must be positive")
    theta = np.linspace(0.0, np.pi, n_points)
    x = radius_m * (1.0 - np.cos(theta))
    r = radius_m * np.sin(theta)
    r[0] = r[-1] = 0.0
    return make_outline(x, r, name=f"sphere_R{radius_m:g}m")


def sphere_cone_capsule_outline(
    nose_radius_m: float,
    diameter_m: float,
    cone_half_angle_deg: float,
    shoulder_radius_m: float,
    aft_cone_angle_deg: float,
    base_radius_m: float,
    n_arc: int = 121,
) -> Outline:
    """A generic blunted-cone forebody + rounded shoulder + conical afterbody + flat base.

    Defined locally for the M2 pipeline demonstration ONLY. The project's parametric
    capsule lives in ``aether.geometry.capsule``; this function exists so that M2 does not
    depend on a module being written concurrently. It is not a model of any flown vehicle.
    """
    rn, rs = nose_radius_m, shoulder_radius_m
    r_max = 0.5 * diameter_m
    tc = np.radians(cone_half_angle_deg)
    ta = np.radians(aft_cone_angle_deg)
    if not (0 < tc < np.pi / 2 and 0 < ta < np.pi / 2):
        raise ValueError("cone angles must be in (0, 90) deg")
    if base_radius_m <= 0 or base_radius_m >= r_max:
        raise ValueError("base radius must be in (0, D/2)")

    # Nose cap: tangent to the cone where the surface angle equals the cone half-angle.
    phi = np.linspace(0.0, np.pi / 2 - tc, n_arc)
    xs, rs_ = [rn * (1 - np.cos(phi))], [rn * np.sin(phi)]
    x_t, r_t = xs[0][-1], rs_[0][-1]

    # Shoulder arc: centre placed so the arc is tangent to the cone and peaks at r_max.
    r_c = r_max - rs
    # surface tangent direction angle (from +x): cone = tc; arc runs tc -> -ta
    x_c = x_t + (r_c + rs * np.cos(tc) - r_t) / np.tan(tc) + rs * np.sin(tc)
    r_s0 = r_c + rs * np.cos(tc)               # radius where the shoulder arc starts
    if r_s0 <= r_t:
        raise ValueError("nose cap already exceeds the shoulder: reduce nose radius/angle")
    ang = np.linspace(tc, -ta, n_arc)  # tangent angle; normal angle = ang + 90 deg
    xs.append(x_c - rs * np.sin(ang))
    rs_.append(r_c + rs * np.cos(ang))
    x_s1, r_s1 = xs[-1][-1], rs_[-1][-1]
    if base_radius_m >= r_s1:
        raise ValueError("base radius must be smaller than the shoulder exit radius")

    # Conical afterbody down to the base radius, then a flat base to the axis.
    x_b = x_s1 + (r_s1 - base_radius_m) / np.tan(ta)
    n_line = max(n_arc // 2, 20)
    xs.append(np.linspace(x_s1, x_b, n_line)[1:])
    rs_.append(np.linspace(r_s1, base_radius_m, n_line)[1:])
    xs.append(np.full(n_line - 1, x_b))
    rs_.append(np.linspace(base_radius_m, 0.0, n_line)[1:])

    x = np.concatenate(xs)
    r = np.concatenate(rs_)
    keep = np.concatenate(([True], np.hypot(np.diff(x), np.diff(r)) > 1e-12))
    # The straight cone flank is the implicit polyline segment from the nose-cap tangent
    # point to the start of the shoulder arc.
    return make_outline(x[keep], r[keep],
                        name=f"spherecone_Rn{rn:g}_D{diameter_m:g}_{cone_half_angle_deg:g}deg")
