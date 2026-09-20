"""Phase F - parametric capsule geometry (sphere-cone-torus-cone-flat-base).

Every derived quantity here is checked at least two independent ways: the closed-form
building blocks (spherical cap, conical frustum) against textbook values; the total
enclosed volume against an independent numerical washer integration of `.profile()`;
the exported STL's mesh volume (divergence theorem) against the same closed form; and
watertightness by reading the file back and counting edges, not by construction alone.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from src.aether.geometry.capsule import (
    CapsuleGeometry,
    _cone_frustum_volume,
    _spherical_cap_volume,
    read_stl_triangles,
)

# A general, comfortably non-degenerate sphere-cone-torus capsule: every one of the
# five segments has a real, non-negligible length, so tangent-continuity and
# per-segment checks below all have something to bite on.
GENERAL = dict(
    nose_radius_m=0.60,
    diameter_m=1.20,
    shoulder_radius_m=0.15,
    cone_half_angle_deg=20.0,
    aft_cone_angle_deg=15.0,
    length_m=1.10,
)


def _slope_deg(geom: CapsuleGeometry, s0: float, eps: float = 1e-6) -> float:
    """Local slope angle [deg] of the meridian at arc length s0, by central difference."""
    xa, ra = geom._point_at_arclength(np.array([s0 - eps]))
    xb, rb = geom._point_at_arclength(np.array([s0 + eps]))
    return float(np.degrees(np.arctan2(rb[0] - ra[0], xb[0] - xa[0])))


# --------------------------------------------------------------------------------
# Closed-form building blocks - the "sphere and cone closed forms" the derived
# quantities are built from and cross-checked against.
# --------------------------------------------------------------------------------


def test_spherical_cap_volume_hemisphere():
    """height == radius must give exactly the textbook hemisphere volume (2/3) pi R^3."""
    r = 2.0
    assert _spherical_cap_volume(r, r) == pytest.approx((2.0 / 3.0) * np.pi * r**3, rel=1e-12)


def test_spherical_cap_volume_full_sphere():
    """height == 2R (the whole sphere) must give the full sphere volume (4/3) pi R^3."""
    r = 1.3
    assert _spherical_cap_volume(r, 2 * r) == pytest.approx((4.0 / 3.0) * np.pi * r**3, rel=1e-12)


def test_cone_frustum_volume_reduces_to_cone():
    """r1 == 0 (a point) must reduce the frustum formula to the plain cone volume."""
    r2, h = 2.0, 5.0
    assert _cone_frustum_volume(0.0, r2, h) == pytest.approx(np.pi * r2**2 * h / 3.0, rel=1e-12)


def test_cone_frustum_volume_reduces_to_cylinder():
    """r1 == r2 must reduce the frustum formula to the plain cylinder volume."""
    r, h = 1.5, 4.0
    assert _cone_frustum_volume(r, r, h) == pytest.approx(np.pi * r**2 * h, rel=1e-12)


# --------------------------------------------------------------------------------
# validate() - geometric feasibility and engineering bounds
# --------------------------------------------------------------------------------


def test_general_geometry_is_valid():
    CapsuleGeometry(**GENERAL).validate()


@pytest.mark.parametrize(
    "field,value",
    [
        ("nose_radius_m", 0.0),
        ("nose_radius_m", -0.1),
        ("diameter_m", 0.0),
        ("shoulder_radius_m", -0.01),
        ("length_m", 0.0),
    ],
)
def test_rejects_nonpositive_scalars(field, value):
    params = dict(GENERAL, **{field: value})
    with pytest.raises(ValueError, match=field):
        CapsuleGeometry(**params).validate(bounds={})


def test_rejects_cone_half_angle_zero():
    """Exactly 0 divides by zero in the fore-cone construction - must be rejected,
    not silently produce inf/nan."""
    params = dict(GENERAL, cone_half_angle_deg=0.0)
    with pytest.raises(ValueError, match="cone_half_angle_deg"):
        CapsuleGeometry(**params).validate(bounds={})


def test_rejects_cone_half_angle_at_or_above_90():
    for angle in (90.0, 95.0):
        params = dict(GENERAL, cone_half_angle_deg=angle)
        with pytest.raises(ValueError, match="cone_half_angle_deg"):
            CapsuleGeometry(**params).validate(bounds={})


def test_aft_cone_angle_zero_is_valid_cylindrical_afterbody():
    params = dict(GENERAL, aft_cone_angle_deg=0.0)
    CapsuleGeometry(**params).validate(bounds={})


def test_rejects_shoulder_radius_larger_than_vehicle_radius():
    params = dict(GENERAL, shoulder_radius_m=GENERAL["diameter_m"])  # >> R_b
    with pytest.raises(ValueError, match="shoulder_radius_m"):
        CapsuleGeometry(**params).validate(bounds={})


def test_rejects_cone_angle_too_small_for_nose_radius():
    """A nose radius this large relative to diameter/shoulder needs a bigger
    cone_half_angle_deg than 2 deg gives - the sphere and shoulder torus overlap."""
    params = dict(GENERAL, nose_radius_m=1.5, cone_half_angle_deg=2.0)
    with pytest.raises(ValueError, match="overlap"):
        CapsuleGeometry(**params).validate(bounds={})


def test_rejects_length_too_short_to_contain_shoulder():
    params = dict(GENERAL, length_m=0.3)
    with pytest.raises(ValueError, match="length_m"):
        CapsuleGeometry(**params).validate(bounds={})


def test_rejects_aft_cone_closing_before_base():
    """A steep aft cone over a long body closes to a point before x = length_m."""
    params = dict(GENERAL, aft_cone_angle_deg=60.0, length_m=3.0)
    with pytest.raises(ValueError, match="aft_cone_angle_deg"):
        CapsuleGeometry(**params).validate(bounds={})


# GENERAL scaled 10x (angles unchanged) - geometrically self-consistent (tangency is
# scale-invariant given proportional lengths), but comfortably outside
# configs/geometry_bounds.yaml's engineering-taste ranges (max diameter 6 m, max
# length 8 m). Used to test that the DEFAULT bounds are actually consulted, distinct
# from pure geometric feasibility.
OVERSIZE = {
    k: (v * 10.0 if k not in ("cone_half_angle_deg", "aft_cone_angle_deg") else v)
    for k, v in GENERAL.items()
}


def test_default_bounds_reject_oversize_diameter():
    """configs/geometry_bounds.yaml is actually consulted when bounds=None (default)."""
    CapsuleGeometry(**OVERSIZE).validate(bounds={})  # geometrically feasible on its own
    with pytest.raises(ValueError, match="geometry_bounds.yaml"):
        CapsuleGeometry(**OVERSIZE).validate()


def test_empty_bounds_skips_engineering_checks():
    """bounds={} must still enforce pure geometric feasibility, but no design-taste bound."""
    CapsuleGeometry(**OVERSIZE).validate(bounds={})  # must not raise


def test_null_bound_is_skipped_not_treated_as_satisfied():
    params = dict(GENERAL, shoulder_radius_m=0.001)
    bounds = {"shoulder_radius_m": {"min": None, "max": None}}
    CapsuleGeometry(**params).validate(bounds=bounds)  # must not raise: null == skip


# --------------------------------------------------------------------------------
# profile() - endpoints, monotone arc length, tangent continuity
# --------------------------------------------------------------------------------


def test_profile_starts_at_nose_tip_and_ends_at_base_centre():
    x, r = CapsuleGeometry(**GENERAL).profile(200)
    assert x[0] == pytest.approx(0.0, abs=1e-12)
    assert r[0] == pytest.approx(0.0, abs=1e-12)
    assert x[-1] == pytest.approx(GENERAL["length_m"], rel=1e-9)
    assert r[-1] == pytest.approx(0.0, abs=1e-9)


def test_profile_rejects_too_few_points():
    with pytest.raises(ValueError, match="n_points"):
        CapsuleGeometry(**GENERAL).profile(5)


def test_profile_arc_length_is_monotone_nondecreasing():
    geom = CapsuleGeometry(**GENERAL)
    x, r = geom.profile(400)
    ds = np.sqrt(np.diff(x) ** 2 + np.diff(r) ** 2)
    assert np.all(ds >= -1e-12)


def test_profile_radius_never_negative():
    x, r = CapsuleGeometry(**GENERAL).profile(400)
    assert np.all(r >= -1e-12)


def test_profile_reaches_max_diameter():
    geom = CapsuleGeometry(**GENERAL)
    x, r = geom.profile(2000)
    assert r.max() == pytest.approx(geom.diameter_m / 2.0, rel=1e-3)


@pytest.mark.parametrize(
    "join_name,break_index,expected_slope_deg",
    [
        ("nose-sphere / fore-cone", 1, GENERAL["cone_half_angle_deg"]),
        ("fore-cone / shoulder-torus", 2, GENERAL["cone_half_angle_deg"]),
        ("shoulder-torus / aft-cone", 3, -GENERAL["aft_cone_angle_deg"]),
    ],
)
def test_tangent_continuity_at_internal_joins(join_name, break_index, expected_slope_deg):
    geom = CapsuleGeometry(**GENERAL)
    s0 = geom._segment_breaks()[break_index]
    measured = _slope_deg(geom, s0)
    assert measured == pytest.approx(expected_slope_deg, abs=0.05), join_name


def test_base_rim_is_a_genuine_corner_not_tangent_continuous():
    """A-GEO-4: the aft-cone/flat-base join is NOT tangent-continuous by design."""
    geom = CapsuleGeometry(**GENERAL)
    s0 = geom._segment_breaks()[4]
    before = _slope_deg(geom, s0 - 1e-4)
    after = _slope_deg(geom, s0 + 1e-4)
    assert abs(before - after) > 10.0  # a real corner, not a smooth transition


def test_pure_spherical_segment_forebody_limiting_case():
    """A-GEO-1: choosing cone_half_angle_deg at its critical value for a given
    nose/diameter/shoulder combination collapses the fore-cone segment to (numerically)
    zero length - an Apollo-like pure spherical-segment forebody, not a dedicated flag.

    Critical angle solved from r2(theta) == r1(theta):
        Rb - Rc(1 - cos(theta)) == Rn cos(theta)  =>  cos(theta) = (Rb-Rc)/(Rn-Rc)
    which requires Rn > Rb (nose radius exceeds base radius) - true of Apollo
    (Rn ~ 4.69 m, base radius ~ 1.96 m).
    """
    r_n, r_c, r_b = 0.90, 0.08, 0.60
    theta_c = float(np.degrees(np.arccos((r_b - r_c) / (r_n - r_c))))
    geom = CapsuleGeometry(
        nose_radius_m=r_n, diameter_m=2 * r_b, shoulder_radius_m=r_c,
        cone_half_angle_deg=theta_c, aft_cone_angle_deg=10.0, length_m=1.0,
    )
    geom.validate(bounds={})
    j = geom._joins
    assert (j.x2 - j.x1) == pytest.approx(0.0, abs=1e-9)
    # still produces a clean, monotone profile with no crash or NaN
    x, r = geom.profile(200)
    assert np.all(np.isfinite(x)) and np.all(np.isfinite(r))


def test_sphere_cone_overlap_just_past_critical_angle_is_rejected():
    """One degree below the critical angle from the previous test must be infeasible."""
    r_n, r_c, r_b = 0.90, 0.08, 0.60
    theta_c = float(np.degrees(np.arccos((r_b - r_c) / (r_n - r_c))))
    geom = CapsuleGeometry(
        nose_radius_m=r_n, diameter_m=2 * r_b, shoulder_radius_m=r_c,
        cone_half_angle_deg=theta_c - 1.0, aft_cone_angle_deg=10.0, length_m=1.0,
    )
    with pytest.raises(ValueError, match="overlap"):
        geom.validate(bounds={})


# --------------------------------------------------------------------------------
# Derived quantities
# --------------------------------------------------------------------------------


def test_reference_area_is_frontal_disk_at_max_diameter():
    geom = CapsuleGeometry(**GENERAL)
    assert geom.reference_area_m2 == pytest.approx(np.pi * (geom.diameter_m / 2.0) ** 2, rel=1e-12)


def test_effective_nose_radius_is_the_sphere_radius():
    geom = CapsuleGeometry(**GENERAL)
    assert geom.effective_nose_radius_m == geom.nose_radius_m


def test_enclosed_volume_matches_independent_numerical_washer_integration():
    """The production volume (closed-form cap/frusta + quadratured torus) must agree
    with a fully independent pi * int r(x)^2 dx over a fine `.profile()` sample."""
    geom = CapsuleGeometry(**GENERAL)
    x, r = geom.profile(5000)
    v_numeric = float(np.pi * np.trapezoid(r**2, x))
    assert v_numeric == pytest.approx(geom.enclosed_volume_m3, rel=1e-5)


def test_enclosed_volume_hemisphere_limit():
    """Rn == Rb, shoulder/aft-cone collapsed to negligible size, length == Rn: the
    body is a hemisphere to within the O(Rc) size of the (deliberately tiny) shoulder."""
    r_n = 1.0
    r_c = 1e-4 * r_n  # negligible relative to Rn: shoulder contributes ~0 volume
    geom = CapsuleGeometry(
        nose_radius_m=r_n, diameter_m=2 * r_n, shoulder_radius_m=r_c,
        cone_half_angle_deg=0.05, aft_cone_angle_deg=0.05, length_m=r_n,
    )
    geom.validate(bounds={})
    hemisphere = (2.0 / 3.0) * np.pi * r_n**3
    assert geom.enclosed_volume_m3 == pytest.approx(hemisphere, rel=2e-3)


def test_wetted_forebody_area_matches_independent_pappus_integration():
    """Independent check of the closed-form wetted-area formula: integrate 2 pi r ds
    directly over a fine sample of just the forebody portion of the profile (nose tip
    to the station of maximum diameter) and compare."""
    geom = CapsuleGeometry(**GENERAL)
    j = geom._joins
    s_top = j.s1 + j.s2 + geom.shoulder_radius_m * j.theta_c_rad
    s = np.linspace(0.0, s_top, 4000)
    x, r = geom._point_at_arclength(s)
    ds = np.sqrt(np.diff(x) ** 2 + np.diff(r) ** 2)
    r_mid = 0.5 * (r[1:] + r[:-1])
    area_numeric = float(2.0 * np.pi * np.sum(r_mid * ds))
    assert area_numeric == pytest.approx(geom.wetted_forebody_area_m2, rel=1e-3)


# --------------------------------------------------------------------------------
# STL export: determinism, watertightness, mesh-volume cross-check
# --------------------------------------------------------------------------------


def _edge_counts(triangles: np.ndarray) -> Counter:
    counts: Counter = Counter()
    for tri in triangles:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((tuple(tri[a]), tuple(tri[b]))))
            counts[edge] += 1
    return counts


def test_stl_is_watertight(tmp_path):
    """Every edge in the exported mesh must be shared by EXACTLY two triangles."""
    geom = CapsuleGeometry(**GENERAL)
    path = geom.to_stl(tmp_path / "capsule.stl", n_circumferential=48, n_profile_points=150)
    triangles = read_stl_triangles(path)
    counts = _edge_counts(triangles)
    bad = {edge: n for edge, n in counts.items() if n != 2}
    assert not bad, f"{len(bad)} of {len(counts)} edges are not shared by exactly 2 triangles"


def test_stl_is_deterministic_same_input_same_bytes(tmp_path):
    geom = CapsuleGeometry(**GENERAL)
    p1 = geom.to_stl(tmp_path / "a.stl", n_circumferential=32, n_profile_points=80)
    p2 = geom.to_stl(tmp_path / "b.stl", n_circumferential=32, n_profile_points=80)
    assert p1.read_bytes() == p2.read_bytes()


def test_stl_mesh_volume_matches_enclosed_volume(tmp_path):
    """Independent third computation of volume: the divergence theorem applied to the
    actual exported triangle mesh, read back from disk - not the same code path as
    `enclosed_volume_m3` at all."""
    geom = CapsuleGeometry(**GENERAL)
    path = geom.to_stl(tmp_path / "capsule.stl", n_circumferential=96, n_profile_points=400)
    triangles = read_stl_triangles(path).astype(np.float64)
    v1, v2, v3 = triangles[:, 0, :], triangles[:, 1, :], triangles[:, 2, :]
    mesh_volume = float(np.sum(np.einsum("ij,ij->i", v1, np.cross(v2, v3))) / 6.0)
    assert mesh_volume == pytest.approx(geom.enclosed_volume_m3, rel=5e-3)
    assert mesh_volume > 0.0  # outward-normal winding, not merely watertight


def test_stl_rejects_too_few_circumferential_divisions(tmp_path):
    geom = CapsuleGeometry(**GENERAL)
    with pytest.raises(ValueError, match="n_circumferential"):
        geom.to_stl(tmp_path / "capsule.stl", n_circumferential=2)
