"""Parametric axisymmetric blunt-capsule geometry: sphere - cone - torus - cone - flat base.

Conceptual anchor
------------------
A re-entry capsule forebody is blunt because Sutton-Graves heating scales as
1/sqrt(R_n) - a big nose radius spreads the same stagnation energy over more area
and pushes the shock further from the wall. This module gives that blunt forebody a
single reproducible geometric description that every other subsystem in the project
can share:

  - `heating` needs `effective_nose_radius_m`.
  - the CFD mesher (another module) needs `.profile()`, the meridian outline.
  - the AI/optimiser candidate schema (spec S23) needs `.validate()` to reject
    free-form geometry outside bounds before anything downstream ever sees it.

Governing construction
-----------------------
Five analytic segments, nose to base, chosen so the whole meridian has an EXACT
arc-length parametrization and closed-form (or adaptively-quadratured) surface and
volume contributions - no segment needs its own numerical root-find:

  1. spherical nose cap     radius R_n, from the tip (x=0, r=0) to the point where
                             the local slope matches the fore-cone half-angle.
  2. straight fore cone      half-angle theta_c. MAY be zero length: that is how a
                             pure spherical-segment forebody (Apollo-like) is
                             represented here - see A-GEO-1.
  3. toroidal shoulder       tube radius R_c, sweeping through the station of
                             maximum diameter (where the local slope is exactly
                             horizontal) and blending into the aft cone.
  4. straight aft cone       half-angle theta_a. Zero is a valid, cylindrical
                             afterbody.
  5. flat base                a radial segment at x = length_m, closing the body from
                             the aft-cone's edge radius down to the axis. This join
                             is a genuine geometric corner, not tangent-continuous
                             (A-GEO-4) - real capsule aft rims are corners too.

Derivation of the two tangency conditions (fore-cone/sphere and shoulder/cones) is in
`ASSUMPTIONS.md` under A-GEO-1..A-GEO-9. All of it reduces to elementary trigonometry;
the only place this module reaches for `scipy.integrate.quad` is the toroidal
shoulder's contribution to the enclosed volume, which needs a cos^3 term with no
short closed form (A-GEO-6) - everything else here is closed-form.

Explicitly not modelled: variable/morphing geometry (out of scope, spec S2), internal
structure, ablation-driven shape change, off-axis asymmetry.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path

import numpy as np
import yaml
from scipy import integrate

from ..utils.run import REPO_ROOT
from .stagnation_gradient import (
    CAP_RADIUS,
    MODELS,
    VELOCITY_GRADIENT,
    EffectiveNoseRadiusReport,
    effective_nose_radius_report,
)

DEFAULT_BOUNDS_PATH = REPO_ROOT / "configs" / "geometry_bounds.yaml"

__all__ = ["CapsuleGeometry", "read_stl_triangles", "CAP_RADIUS", "VELOCITY_GRADIENT"]


@lru_cache(maxsize=1)
def _default_bounds() -> dict:
    """Engineering-choice geometry bounds, loaded once from configs/geometry_bounds.yaml.

    These are judgment calls about the design space (spec S9: physical limits never
    hard-coded). Pure geometric feasibility - tangency, positive lengths - is NOT in
    this file; it is hard-coded in `CapsuleGeometry.validate()` because it is math,
    not a design choice.
    """
    with open(DEFAULT_BOUNDS_PATH) as fh:
        return yaml.safe_load(fh) or {}


# --------------------------------------------------------------------------------
# Closed-form building blocks. Each is a standalone textbook result, unit-tested
# directly in tests/test_geometry.py - this is the "tested against sphere and cone
# closed forms" verification the volume/area properties are built from.
# --------------------------------------------------------------------------------


def _spherical_cap_volume(radius_m: float, height_m: float) -> float:
    """Volume of a spherical cap of given height cut from a sphere. V = pi h^2 (3R-h)/3.

    height_m == radius_m gives exactly a hemisphere, (2/3) pi R^3.
    """
    return float(np.pi * height_m**2 * (3.0 * radius_m - height_m) / 3.0)


def _spherical_cap_area(radius_m: float, height_m: float) -> float:
    """Lateral (curved) surface area of a spherical cap. A = 2 pi R h."""
    return float(2.0 * np.pi * radius_m * height_m)


def _cone_frustum_volume(r1_m: float, r2_m: float, height_m: float) -> float:
    """Volume of a right-circular conical frustum. V = pi h (r1^2 + r1 r2 + r2^2) / 3."""
    return float(np.pi * height_m * (r1_m**2 + r1_m * r2_m + r2_m**2) / 3.0)


def _cone_frustum_area(r1_m: float, r2_m: float, slant_m: float) -> float:
    """Lateral surface area of a conical frustum. A = pi (r1 + r2) * slant."""
    return float(np.pi * (r1_m + r2_m) * slant_m)


@dataclass(frozen=True)
class _Joins:
    """Internal breakpoints of the five-segment meridian.

    Not part of the public API. All lengths in metres, all angles in radians.
    Segment order: [nose sphere | fore cone | shoulder torus | aft cone | flat base].
    """

    theta_c_rad: float
    theta_a_rad: float
    x1: float
    r1: float  # nose-sphere / fore-cone tangent point
    x2: float
    r2: float  # fore-cone / shoulder-torus tangent point (fore side)
    x_s: float  # shoulder-torus tube-centre axial position (station of max diameter)
    x3: float
    r3: float  # shoulder-torus / aft-cone tangent point (aft side)
    r_base: float  # radius at x = length_m, i.e. the outer edge of the flat base
    s1: float  # arc length of each segment
    s2: float
    s3: float
    s4: float
    s5: float


@dataclass(frozen=True)
class CapsuleGeometry:
    """Axisymmetric blunt sphere-cone-torus-cone capsule with a flat base.

    Parameters
    ----------
    nose_radius_m:
        Spherical nose-cap radius R_n [m]. Also `effective_nose_radius_m` - the
        quantity `heating.heat_flux_sutton_graves` expects.
    diameter_m:
        Maximum vehicle diameter [m], reached at the shoulder (the station where the
        toroidal blend is exactly horizontal). `reference_area_m2` is computed from
        this, never from nose_radius_m.
    shoulder_radius_m:
        Toroidal shoulder tube radius R_c [m], blending the fore cone into the aft
        cone.
    cone_half_angle_deg:
        Forebody cone half-angle [deg], from the axis of symmetry. Must be strictly
        positive - a value of exactly zero divides by zero in the fore-cone
        construction (A-GEO-2). The straight fore-cone segment's length is a
        DERIVED quantity (depends on nose_radius_m, diameter_m and
        shoulder_radius_m too) and degenerates toward zero for a pure
        spherical-segment forebody like Apollo (A-GEO-1) - that limiting case is
        reached by choosing this angle near the critical value for the other three
        parameters, not by setting it to zero.
    aft_cone_angle_deg:
        Aft-body cone half-angle [deg]. Zero is a valid, cylindrical afterbody.
    length_m:
        Total capsule length, nose tip to the base plane [m].
    effective_nose_radius_model:
        Which rule `effective_nose_radius_m` follows (A-GEO-3). `'cap_radius'` is the
        legacy identity R_eff = R_n and is the DEFAULT, so every pre-existing config,
        result and test is untouched. `'velocity_gradient'` applies the measured
        stagnation-velocity-gradient correction of `.stagnation_gradient` - see
        `docs/theory/effective_nose_radius.md` and `docs/negative_results.md` NR-15.
        Not a shape parameter: it changes no geometry, no area, no volume and no STL.
    """

    nose_radius_m: float
    diameter_m: float
    shoulder_radius_m: float
    cone_half_angle_deg: float
    aft_cone_angle_deg: float
    length_m: float
    effective_nose_radius_model: str = CAP_RADIUS

    # -- internal geometry ---------------------------------------------------------

    @cached_property
    def _joins(self) -> _Joins:
        """Compute every breakpoint of the meridian from the raw parameters.

        Pure trigonometry - always finite as long as 0 < cone_half_angle_deg < 90,
        which `validate()` checks BEFORE any caller reaches this property (every
        public method calls `validate()` first), so the tan(0) division here is
        never actually hit with an invalid angle.
        """
        r_n = self.nose_radius_m
        r_b = self.diameter_m / 2.0
        r_c = self.shoulder_radius_m
        theta_c = np.radians(self.cone_half_angle_deg)
        theta_a = np.radians(self.aft_cone_angle_deg)

        # nose sphere -> fore-cone tangent point. Derivation: on the sphere
        # (x - Rn)^2 + r^2 = Rn^2, dr/dx = (Rn - x) / r must equal tan(theta_c).
        x1 = r_n * (1.0 - np.sin(theta_c))
        r1 = r_n * np.cos(theta_c)
        beta_max = 0.5 * np.pi - theta_c  # angle swept along the sphere from the tip
        s1 = r_n * beta_max

        # fore-cone -> shoulder-torus tangent point (fore side). The torus is
        # r(psi) = (Rb - Rc) + Rc cos(psi), tangent to slope tan(psi); psi = theta_c
        # is exactly where its slope matches the cone.
        r2 = r_b - r_c * (1.0 - np.cos(theta_c))
        cone_fore_len = (r2 - r1) / np.tan(theta_c)
        x2 = x1 + cone_fore_len
        s2 = cone_fore_len / np.cos(theta_c)

        # shoulder torus, through the station of maximum diameter (psi = 0).
        x_s = x2 + r_c * np.sin(theta_c)
        s3 = r_c * (theta_c + theta_a)

        # shoulder torus -> aft-cone tangent point (aft side, psi = -theta_a).
        x3 = x_s + r_c * np.sin(theta_a)
        r3 = r_b - r_c * (1.0 - np.cos(theta_a))

        # aft cone -> flat base.
        aft_len = self.length_m - x3
        r_base = r3 - aft_len * np.tan(theta_a)
        s4 = aft_len / np.cos(theta_a)
        s5 = max(r_base, 0.0)

        return _Joins(theta_c, theta_a, x1, r1, x2, r2, x_s, x3, r3, r_base, s1, s2, s3, s4, s5)

    def _segment_breaks(self) -> np.ndarray:
        """Cumulative arc length at each of the 6 segment boundaries."""
        j = self._joins
        return np.cumsum([0.0, j.s1, j.s2, j.s3, j.s4, j.s5])

    # -- validation -------------------------------------------------------------

    def validate(self, bounds: dict | None = None) -> None:
        """Raise ValueError with a specific message if this geometry is invalid.

        Two independent layers:

        1. PURE GEOMETRIC feasibility - hard-coded, because it is math, not a
           design choice: all lengths finite and positive, the shoulder must fit
           inside the vehicle radius, the fore-cone and aft-cone tangency
           constructions must have non-negative length, and length_m must be long
           enough to contain the nose/cone/shoulder.
        2. ENGINEERING bounds - judgment calls about the design space, loaded from
           `configs/geometry_bounds.yaml` unless `bounds` is passed explicitly. A
           bound that is `null`/missing is SKIPPED, never treated as satisfied -
           the same convention as `limits:` in configs/baseline.yaml (A-LIM-2).
           Pass `bounds={}` to check pure geometric feasibility only.
        """
        name = type(self).__name__

        if self.effective_nose_radius_model not in MODELS:
            raise ValueError(
                f"{name}.effective_nose_radius_model must be one of {MODELS}, got "
                f"{self.effective_nose_radius_model!r}"
            )

        # Primitive scalars first, before anything trig-based (self._joins) is
        # touched - cone_half_angle_deg == 0 divides by zero in _joins.
        for field_name in ("nose_radius_m", "diameter_m", "shoulder_radius_m", "length_m"):
            value = getattr(self, field_name)
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name}.{field_name} must be finite and positive, got {value}")

        if not (0.0 < self.cone_half_angle_deg < 90.0):
            raise ValueError(
                "cone_half_angle_deg must be strictly between 0 and 90 deg (0 divides "
                "by zero in the fore-cone construction; a pure spherical-segment "
                "forebody is reached by choosing the angle near its critical value "
                f"for the given nose/diameter/shoulder, not by setting it to 0), got "
                f"{self.cone_half_angle_deg}"
            )
        if not (0.0 <= self.aft_cone_angle_deg < 90.0):
            raise ValueError(
                f"aft_cone_angle_deg must be in [0, 90) deg, got {self.aft_cone_angle_deg}"
            )

        r_b = self.diameter_m / 2.0
        if self.shoulder_radius_m > r_b:
            raise ValueError(
                f"shoulder_radius_m ({self.shoulder_radius_m:.4f} m) cannot exceed "
                f"diameter_m/2 ({r_b:.4f} m) - the shoulder does not fit inside the "
                "vehicle radius."
            )

        j = self._joins
        tol = 1e-9 * max(self.nose_radius_m, self.diameter_m, self.length_m, 1e-9)

        cone_fore_len = j.x2 - j.x1
        if cone_fore_len < -tol:
            raise ValueError(
                f"cone_half_angle_deg ({self.cone_half_angle_deg:.3f} deg) is too "
                "small for this nose_radius_m / diameter_m / shoulder_radius_m "
                f"combination: the fore cone would need a negative length "
                f"({cone_fore_len * 1e3:.3f} mm) - the nose sphere and the shoulder "
                "torus overlap. Increase cone_half_angle_deg, decrease "
                "nose_radius_m, or increase diameter_m."
            )

        if j.x3 > self.length_m + tol:
            raise ValueError(
                f"length_m ({self.length_m:.4f} m) is too short to contain the "
                f"nose, fore cone and shoulder, which end at x={j.x3:.4f} m. "
                "Increase length_m."
            )

        if j.r_base < -tol:
            raise ValueError(
                f"aft_cone_angle_deg ({self.aft_cone_angle_deg:.3f} deg) closes the "
                f"aft body to a point before reaching length_m ({self.length_m:.4f} "
                "m). Decrease aft_cone_angle_deg or decrease length_m."
            )

        bounds = _default_bounds() if bounds is None else bounds
        self._check_bounds(bounds)

    def _check_bounds(self, bounds: dict) -> None:
        """Engineering-choice range checks against a bounds dict (A-GEO-7)."""
        name = type(self).__name__
        for field_name in (
            "nose_radius_m",
            "diameter_m",
            "shoulder_radius_m",
            "cone_half_angle_deg",
            "aft_cone_angle_deg",
            "length_m",
        ):
            spec = bounds.get(field_name)
            if not spec:
                continue
            value = getattr(self, field_name)
            lo, hi = spec.get("min"), spec.get("max")
            if lo is not None and value < lo:
                raise ValueError(
                    f"{name}.{field_name} = {value} is below bound min={lo} "
                    "(configs/geometry_bounds.yaml)"
                )
            if hi is not None and value > hi:
                raise ValueError(
                    f"{name}.{field_name} = {value} is above bound max={hi} "
                    "(configs/geometry_bounds.yaml)"
                )

        fineness = bounds.get("fineness_ratio")
        if fineness:
            ratio = self.length_m / self.diameter_m
            lo, hi = fineness.get("min"), fineness.get("max")
            if lo is not None and ratio < lo:
                raise ValueError(
                    f"{name}: length_m/diameter_m = {ratio:.3f} is below "
                    f"fineness_ratio min={lo} (configs/geometry_bounds.yaml)"
                )
            if hi is not None and ratio > hi:
                raise ValueError(
                    f"{name}: length_m/diameter_m = {ratio:.3f} is above "
                    f"fineness_ratio max={hi} (configs/geometry_bounds.yaml)"
                )

    # -- derived quantities -------------------------------------------------------

    @property
    def _fore_cone_span_fraction(self) -> float:
        """Radial span of the straight fore cone, as a fraction of the body radius.

        Zero when the spherical cap runs straight into the shoulder torus, which is the
        shape Zoby & Sullivan and Ellison actually measured. Large when a long conical
        flank separates the two, which they did not. Only ever raises a flag.
        """
        j = self._joins
        return float((j.r2 - j.r1) / (self.diameter_m / 2.0))

    def effective_nose_radius_report(self) -> EffectiveNoseRadiusReport:
        """`effective_nose_radius_m` plus every reason to distrust it (A-GEO-3).

        Same number as the property, with the dimensionless groups, the validity flags
        and any extrapolation note attached. `evaluate_design` puts these on every
        candidate as diagnostics, so "the correction was extrapolated here" shows up in
        the candidate log instead of being invisible.
        """
        self.validate(bounds={})
        return effective_nose_radius_report(
            nose_radius_m=self.nose_radius_m,
            body_radius_m=self.diameter_m / 2.0,
            corner_radius_m=self.shoulder_radius_m,
            model=self.effective_nose_radius_model,
            cone_span_fraction=self._fore_cone_span_fraction,
        )

    @property
    def effective_nose_radius_m(self) -> float:
        """Stagnation-point radius for Sutton-Graves heating [m] (A-GEO-3).

        NOT necessarily the nose radius. Sutton-Graves' 1/sqrt(R_n) is really a
        statement about the stagnation-point VELOCITY GRADIENT, and for a shallow
        spherical segment that gradient is governed by the body radius and the corner
        rather than by the cap's own curvature - so flattening the nose buys less and
        less, and in the flat-faced limit buys nothing at all. Which rule applies here is
        set by `effective_nose_radius_model`:

        `'cap_radius'` (default)
            R_eff = R_n. Exact only at the hemisphere. This is what every M1/M1b result
            was computed with and it is kept as the default so those reproduce
            bit-for-bit.
        `'velocity_gradient'`
            R_eff from NASA TN D-5121 table I via `.stagnation_gradient`, continuous with
            the hemisphere limit and saturating at the flat face.
        `'velocity_gradient_zoby'`
            The same, displaced by Ellison's own published disagreement with the other
            primary (NASA TM X-1067). It exists ONLY as the alternative state of the M7
            model-form switch on this quantity - see `stagnation_gradient` and
            ASSUMPTIONS A-UQ-NOSE-1 - and nothing selects it by default.

        Derivation and worked numbers: `docs/theory/effective_nose_radius.md`.
        """
        if self.effective_nose_radius_model == CAP_RADIUS:
            return self.nose_radius_m
        return self.effective_nose_radius_report().effective_nose_radius_m

    @property
    def reference_area_m2(self) -> float:
        """Aerodynamic reference area: the frontal disk at maximum diameter, pi (D/2)^2."""
        return float(np.pi * (self.diameter_m / 2.0) ** 2)

    @property
    def wetted_forebody_area_m2(self) -> float:
        """Wetted area of the forward-facing heat shield [m^2] (A-GEO-5).

        Nose tip to the station of maximum diameter (the top of the shoulder
        torus) - the conventional forward-facing/heat-shield wetted area, not the
        full vehicle. Closed-form sum of the nose spherical cap, the fore-cone
        frustum, and the fore half of the shoulder torus (all via Pappus's
        theorem).
        """
        self.validate(bounds={})
        j = self._joins
        r_n = self.nose_radius_m
        r_b = self.diameter_m / 2.0
        r_c = self.shoulder_radius_m

        cap = _spherical_cap_area(r_n, j.x1)
        frustum = _cone_frustum_area(j.r1, j.r2, j.s2)
        # Fore half of the torus, psi in [0, theta_c]: for the arc r(psi) =
        # (Rb-Rc) + Rc cos(psi), ds = Rc dpsi, so A = 2 pi int r ds
        #   = 2 pi Rc [ (Rb-Rc) theta_c + Rc sin(theta_c) ]
        torus = 2.0 * np.pi * r_c * ((r_b - r_c) * j.theta_c_rad + r_c * np.sin(j.theta_c_rad))
        return float(cap + frustum + torus)

    @property
    def enclosed_volume_m3(self) -> float:
        """Enclosed volume, nose tip to the flat base [m^3] (A-GEO-6).

        The nose spherical cap and both conical frusta use exact closed forms
        (`_spherical_cap_volume`, `_cone_frustum_volume`), each unit-tested
        directly against known values in tests/test_geometry.py. The toroidal
        shoulder's contribution to pi * int r(x)^2 dx needs a cos^3(psi) term with
        no short closed form and is instead obtained by adaptive quadrature
        (`scipy.integrate.quad`), cross-checked in tests against an independent
        numerical washer integration of the full `.profile()` output.
        """
        self.validate(bounds={})
        j = self._joins
        r_b = self.diameter_m / 2.0
        r_c = self.shoulder_radius_m

        cap = _spherical_cap_volume(self.nose_radius_m, j.x1)
        fore_frustum = _cone_frustum_volume(j.r1, j.r2, j.x2 - j.x1)
        aft_frustum = _cone_frustum_volume(j.r3, j.r_base, max(self.length_m - j.x3, 0.0))

        def integrand(psi: float) -> float:
            r = (r_b - r_c) + r_c * np.cos(psi)
            return r**2 * np.cos(psi)

        torus_integral, _ = integrate.quad(integrand, -j.theta_a_rad, j.theta_c_rad)
        torus = np.pi * r_c * torus_integral

        return float(cap + fore_frustum + torus + aft_frustum)

    # -- meridian outline ---------------------------------------------------------

    def _point_at_arclength(self, s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Vectorised (x, r) at each global arc-length value s (m), s in [0, S_total]."""
        j = self._joins
        r_n = self.nose_radius_m
        r_b = self.diameter_m / 2.0
        r_c = self.shoulder_radius_m
        breaks = self._segment_breaks()
        x = np.empty_like(s, dtype=float)
        r = np.empty_like(s, dtype=float)

        m = (s >= breaks[0]) & (s <= breaks[1])  # nose sphere
        beta = s[m] / r_n
        x[m] = r_n * (1.0 - np.cos(beta))
        r[m] = r_n * np.sin(beta)

        m = (s > breaks[1]) & (s <= breaks[2])  # fore cone
        t = s[m] - breaks[1]
        x[m] = j.x1 + t * np.cos(j.theta_c_rad)
        r[m] = j.r1 + t * np.sin(j.theta_c_rad)

        m = (s > breaks[2]) & (s <= breaks[3])  # shoulder torus
        t = s[m] - breaks[2]
        psi = j.theta_c_rad - t / r_c
        x[m] = j.x_s - r_c * np.sin(psi)
        r[m] = (r_b - r_c) + r_c * np.cos(psi)

        m = (s > breaks[3]) & (s <= breaks[4])  # aft cone
        t = s[m] - breaks[3]
        x[m] = j.x3 + t * np.cos(j.theta_a_rad)
        r[m] = j.r3 - t * np.sin(j.theta_a_rad)

        m = s > breaks[4]  # flat base
        t = s[m] - breaks[4]
        x[m] = self.length_m
        r[m] = np.maximum(j.r_base - t, 0.0)

        return x, r

    def profile(self, n_points: int = 200) -> tuple[np.ndarray, np.ndarray]:
        """Meridian outline (x_m, r_m), nose tip to base centre.

        Exact arc-length parametrisation: `s` is monotone non-decreasing along the
        returned arrays, built from the five analytic segments, so the outline is
        tangent-continuous at the three internal joins by construction
        (nose-sphere/fore-cone, fore-cone/shoulder, shoulder/aft-cone). The final
        join - aft cone to flat base - is a genuine geometric corner (A-GEO-4), not
        tangent-continuous, matching a real capsule's aft rim.

        The 6 segment breakpoints are always included exactly; approximately
        `n_points` total points are returned, weighted by each segment's arc
        length (a segment whose length is negligible relative to the whole - the
        near-zero-length limiting cases in A-GEO-1 - contributes no extra interior
        points beyond its own breakpoint).

        This exact signature (name, `n_points` argument, `(x_m, r_m)` return) is
        consumed by the CFD mesher - do not change it.
        """
        if n_points < 6:
            raise ValueError(
                f"n_points must be >= 6 to represent all five segments, got {n_points}"
            )
        self.validate(bounds={})

        breaks = self._segment_breaks()
        seg_lengths = np.diff(breaks)
        s_total = breaks[-1]
        eps = 1e-9 * max(s_total, 1e-9)

        interior_budget = max(n_points - breaks.size, 0)
        weights = np.where(seg_lengths > eps, seg_lengths, 0.0)
        if weights.sum() > 0.0:
            interior_counts = np.floor(interior_budget * weights / weights.sum()).astype(int)
        else:
            interior_counts = np.zeros(5, dtype=int)

        samples = [breaks]
        for i in range(5):
            if interior_counts[i] > 0:
                interior = np.linspace(breaks[i], breaks[i + 1], interior_counts[i] + 2)[1:-1]
                samples.append(interior)
        s = np.unique(np.concatenate(samples))

        return self._point_at_arclength(s)

    # -- STL export -----------------------------------------------------------

    def to_stl(
        self, path: str | Path, n_circumferential: int = 64, n_profile_points: int = 200
    ) -> Path:
        """Write a deterministic, watertight binary STL by revolving `.profile()`.

        Determinism: no timestamps, no host-dependent float formatting, no set/dict
        iteration - triangles are generated in a single fixed traversal order
        (nose fan, then ring-by-ring quad strips, then base fan) and written as
        little-endian IEEE-754 binary, so the same geometry and resolution always
        produce a byte-identical file.

        Watertightness (every edge shared by exactly two triangles) is a property
        of this construction, not merely hoped for - it is checked directly in
        tests/test_geometry.py by reading the file back and counting edges.
        """
        self.validate(bounds={})
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        x, r = self.profile(n_profile_points)
        n = len(x)
        if n < 4:
            raise ValueError(f"profile returned only {n} points; need at least 4 to revolve")
        if n_circumferential < 3:
            raise ValueError(f"n_circumferential must be >= 3, got {n_circumferential}")

        phi = np.linspace(0.0, 2.0 * np.pi, n_circumferential, endpoint=False)
        cos_phi, sin_phi = np.cos(phi), np.sin(phi)

        def ring(i: int) -> np.ndarray:
            return np.column_stack(
                [np.full(n_circumferential, x[i]), r[i] * cos_phi, r[i] * sin_phi]
            )

        # Winding: r increases outward as x increases along the body (nose to
        # shoulder), so for OUTWARD-pointing normals under the right-hand rule with
        # phi increasing counter-clockwise about +x, each triangle is listed
        # (near-ring point, far-ring point, near-ring point at phi+dphi) - verified
        # against the enclosed-volume closed form via the divergence theorem in
        # tests/test_geometry.py::test_stl_mesh_volume_matches_enclosed_volume.
        tris: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []

        apex = np.array([x[0], 0.0, 0.0])
        r1v = ring(1)
        for k in range(n_circumferential):
            kk = (k + 1) % n_circumferential
            tris.append((apex, r1v[kk], r1v[k]))

        for i in range(1, n - 2):
            a, b = ring(i), ring(i + 1)
            for k in range(n_circumferential):
                kk = (k + 1) % n_circumferential
                tris.append((a[k], b[kk], b[k]))
                tris.append((a[k], a[kk], b[kk]))

        base_pole = np.array([x[-1], 0.0, 0.0])
        r_last = ring(n - 2)
        for k in range(n_circumferential):
            kk = (k + 1) % n_circumferential
            tris.append((base_pole, r_last[k], r_last[kk]))

        v1 = np.array([t[0] for t in tris], dtype=np.float64)
        v2 = np.array([t[1] for t in tris], dtype=np.float64)
        v3 = np.array([t[2] for t in tris], dtype=np.float64)
        normal = np.cross(v2 - v1, v3 - v1)
        norm_len = np.linalg.norm(normal, axis=1, keepdims=True)
        normal = np.divide(normal, norm_len, out=np.zeros_like(normal), where=norm_len > 1e-15)

        record_dtype = np.dtype(
            [
                ("normal", "<f4", (3,)),
                ("v1", "<f4", (3,)),
                ("v2", "<f4", (3,)),
                ("v3", "<f4", (3,)),
                ("attr", "<u2"),
            ]
        )
        records = np.zeros(len(tris), dtype=record_dtype)
        records["normal"] = normal
        records["v1"] = v1
        records["v2"] = v2
        records["v3"] = v3
        records["attr"] = 0

        header = b"AETHER parametric capsule STL - deterministic, generated by " \
                 b"aether.geometry.capsule.CapsuleGeometry.to_stl"
        header = header[:80].ljust(80, b"\x00")

        with open(path, "wb") as fh:
            fh.write(header)
            fh.write(np.uint32(len(tris)).tobytes())
            fh.write(records.tobytes())

        return path


def read_stl_triangles(path: str | Path) -> np.ndarray:
    """Read a binary STL back as an (n_triangles, 3, 3) float32 vertex array.

    Verification-only helper (watertightness checks, mesh-volume cross-checks in
    tests/test_geometry.py) - not needed by production code, since `to_stl` writes
    directly rather than round-tripping through this.
    """
    record_dtype = np.dtype(
        [
            ("normal", "<f4", (3,)),
            ("v1", "<f4", (3,)),
            ("v2", "<f4", (3,)),
            ("v3", "<f4", (3,)),
            ("attr", "<u2"),
        ]
    )
    with open(path, "rb") as fh:
        fh.read(80)
        n_tri = int(np.frombuffer(fh.read(4), dtype="<u4")[0])
        records = np.frombuffer(fh.read(n_tri * record_dtype.itemsize), dtype=record_dtype)
    return np.stack([records["v1"], records["v2"], records["v3"]], axis=1)
