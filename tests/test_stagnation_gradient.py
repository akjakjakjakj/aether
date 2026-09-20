"""Effective nose radius from the stagnation-point velocity gradient (NR-15 fix).

What is being tested, and against what:

* the interpolant reproduces NASA TN D-5121 table I EXACTLY at every tabulated point -
  those nine numbers are the model, so anything else is a transcription or indexing bug;
* the two analytic limits, hemisphere (R_eff -> R_n) and flat face (R_eff -> a finite
  multiple of the body radius), which is the whole point of the change;
* monotonicity and continuity, including across the K = 1 seam where the model hands
  back to the legacy cap radius;
* agreement with the OTHER primary, Zoby & Sullivan TM X-1067 figure 4, within the
  disagreement Ellison himself documents - the test asserts the documented discrepancy is
  REPRODUCED, not smoothed away;
* that the module constant still matches data/reference/stagnation_velocity_gradient.yaml;
* and that the legacy default leaves the persisted M1 results bit-for-bit unchanged.
"""

from __future__ import annotations

import copy
import csv

import numpy as np
import pytest
import yaml

from src.aether.evaluate import evaluate_design
from src.aether.geometry import CapsuleGeometry
from src.aether.geometry.stagnation_gradient import (
    _K_NODES,
    _R_NODES,
    _RB_OVER_REFF,
    CAP_RADIUS,
    VELOCITY_GRADIENT,
    effective_nose_radius_report,
    rb_over_reff,
)
from src.aether.utils.run import REPO_ROOT, load_config

REFERENCE_PATH = REPO_ROOT / "data" / "reference" / "stagnation_velocity_gradient.yaml"

# A capsule whose forebody really is a shallow spherical segment blended into the body by
# the shoulder, i.e. the shape Zoby & Sullivan and Ellison measured. These are the M4
# front's own proportions: R_n/D = 1.19, shoulder/D = 0.10, 70 deg cone.
FRONT_LIKE = dict(
    diameter_m=3.376,
    nose_radius_m=1.19 * 3.376,
    shoulder_radius_m=0.10 * 3.376,
    cone_half_angle_deg=69.0,
    aft_cone_angle_deg=20.0,
    length_m=0.875 * 3.376,
)


def _capsule(model: str = VELOCITY_GRADIENT, **overrides) -> CapsuleGeometry:
    return CapsuleGeometry(**{**FRONT_LIKE, **overrides}, effective_nose_radius_model=model)


# -- the table itself ---------------------------------------------------------------------


def test_module_table_matches_the_reference_data_file():
    """The physics constant and its provenance record must not drift apart."""
    with open(REFERENCE_PATH) as fh:
        ref = yaml.safe_load(fh)
    rows = ref["ellison_1969_table_i_alpha0"]["rows"]
    assert len(rows) == 9, "Ellison table I alpha=0 has exactly nine rows"
    for row in rows:
        i = _K_NODES.index(row["k_body_over_nose"])
        j = _R_NODES.index(row["r_corner_over_body"])
        assert _RB_OVER_REFF[i][j] == row["rb_over_reff"]
    anchor = ref["hemisphere_anchor"]
    assert anchor["k_body_over_nose"] == 1.0 and anchor["rb_over_reff"] == 1.0
    assert all(v == 1.0 for v in _RB_OVER_REFF[_K_NODES.index(1.0)])


@pytest.mark.parametrize("i,k", list(enumerate(_K_NODES)))
@pytest.mark.parametrize("j,r", list(enumerate(_R_NODES)))
def test_interpolant_is_exact_at_every_tabulated_point(i, k, j, r):
    assert rb_over_reff(k, r) == pytest.approx(_RB_OVER_REFF[i][j], abs=1e-12)


def test_k_outside_the_tabulated_range_is_refused_at_the_low_level():
    with pytest.raises(ValueError, match=r"must be in \[0, 1\]"):
        rb_over_reff(1.4, 0.2)


# -- the two limits -----------------------------------------------------------------------


def test_hemisphere_limit_returns_the_cap_radius_exactly():
    """K = 1: the segment IS a hemisphere, so R_eff must be R_n to machine precision."""
    r_b = 1.5
    report = effective_nose_radius_report(
        nose_radius_m=r_b, body_radius_m=r_b, corner_radius_m=0.0, model=VELOCITY_GRADIENT
    )
    assert report.k_body_over_nose == pytest.approx(1.0)
    assert report.effective_nose_radius_m == pytest.approx(r_b, rel=1e-12)
    assert report.ratio_to_cap_radius == pytest.approx(1.0, rel=1e-12)
    assert not report.extrapolated


def test_hemisphere_limit_is_independent_of_corner_radius():
    """A hemisphere on a cylinder is already tangent; the corner has nothing to blend."""
    r_b = 1.5
    values = [
        effective_nose_radius_report(r_b, r_b, r_c, VELOCITY_GRADIENT).effective_nose_radius_m
        for r_c in (0.0, 0.1 * r_b, 0.3 * r_b, 0.4 * r_b)
    ]
    assert values == pytest.approx([r_b] * 4, rel=1e-12)


def test_flat_face_saturates_at_a_finite_multiple_of_the_body_radius():
    """R_n -> infinity must NOT send heating to zero. Ellison: R_b/R_eff -> 0.317 sharp."""
    r_b = 1.0
    ratios = [
        effective_nose_radius_report(r_n, r_b, 0.0, VELOCITY_GRADIENT).effective_nose_radius_m
        for r_n in (1e2, 1e4, 1e6, 1e8)
    ]
    assert ratios[-1] == pytest.approx(r_b / 0.317, rel=1e-6)
    # genuinely converged, not still climbing: the last decade moves it by nothing,
    # and even a nose 100x the body radius is already within 3% of the asymptote
    assert ratios[-1] - ratios[-2] < 1e-5 * ratios[-1]
    assert ratios[-1] - ratios[0] < 0.03 * ratios[-1]
    # the widely-quoted "about 3.3-3.4 x body radius" for a sharp-cornered flat face
    assert 3.0 < ratios[-1] / r_b < 3.3


def test_flat_face_value_matches_the_two_primaries_side_by_side():
    """Ellison (M=8, tabulated) 3.155 R_b; Zoby & Sullivan (figure) about 3.40 R_b."""
    ellison = 1.0 / 0.317
    zoby_sullivan = 1.0 / 0.286
    assert ellison == pytest.approx(3.155, abs=0.005)
    assert zoby_sullivan == pytest.approx(3.497, abs=0.005)
    # Ellison is the conservative one: smaller R_eff, therefore more heating.
    assert ellison < zoby_sullivan


# -- shape of the correction --------------------------------------------------------------


def test_effective_radius_increases_with_nose_radius_but_with_shrinking_returns():
    """Still monotone - so a flatter nose is never punished - but it saturates."""
    r_b = 1.0
    r_n = np.linspace(1.0, 40.0, 60)
    r_eff = np.array([
        effective_nose_radius_report(x, r_b, 0.2 * r_b, VELOCITY_GRADIENT).effective_nose_radius_m
        for x in r_n
    ])
    assert np.all(np.diff(r_eff) > 0.0), "monotone increasing in nose radius"
    gains = np.diff(r_eff) / np.diff(r_n)
    assert np.all(np.diff(gains) < 1e-9), "marginal gain per metre of nose radius never rises"
    # the legacy model would have kept pace with R_n forever; this one does not
    assert r_eff[-1] < 0.35 * r_n[-1]


def test_rounding_the_corner_raises_heating():
    """Zoby & Sullivan p.6: increasing corner radius increases the velocity gradient."""
    r_b = 1.0
    values = [
        effective_nose_radius_report(2.4 * r_b, r_b, r * r_b, VELOCITY_GRADIENT
                                     ).effective_nose_radius_m
        for r in (0.0, 0.1, 0.2, 0.3, 0.4)
    ]
    assert values == sorted(values, reverse=True), "R_eff falls as the corner is rounded"


def test_model_is_continuous_across_the_sphere_cone_seam():
    """At K = 1 the correction hands back to R_eff = R_n; no step is allowed there."""
    r_b = 1.0
    below = effective_nose_radius_report(r_b / 0.9999, r_b, 0.2, VELOCITY_GRADIENT)
    above = effective_nose_radius_report(r_b / 1.0001, r_b, 0.2, VELOCITY_GRADIENT)
    assert above.extrapolated and not below.extrapolated
    assert below.effective_nose_radius_m == pytest.approx(
        above.effective_nose_radius_m, rel=1e-3
    )


def test_model_is_continuous_in_k_everywhere_inside_the_range():
    r_c = 0.2
    k = np.linspace(1e-4, 1.0, 4000)
    vals = np.array([rb_over_reff(x, r_c) for x in k])
    assert np.all(np.diff(vals) > 0.0), "monotone in K"
    steps = np.abs(np.diff(vals))
    assert steps.max() < 20.0 * steps.mean(), "no kink: no step is an outlier"


def test_sphere_cone_falls_back_to_the_cap_radius_and_says_so():
    """Viking-like: R_n < R_b. Outside both sources, so no correction is invented."""
    report = effective_nose_radius_report(0.25, 1.0, 0.1, VELOCITY_GRADIENT)
    assert report.effective_nose_radius_m == 0.25
    assert report.extrapolated
    assert "sphere-cone" in report.notes[0]


def test_corner_ratio_beyond_the_measured_range_is_clamped_and_flagged():
    report = effective_nose_radius_report(2.4, 1.0, 0.55, VELOCITY_GRADIENT)
    assert report.extrapolated
    assert any("exceeds the measured maximum" in n for n in report.notes)
    assert report.effective_nose_radius_m == pytest.approx(
        effective_nose_radius_report(2.4, 1.0, 0.40, VELOCITY_GRADIENT).effective_nose_radius_m
    )


def test_a_long_fore_cone_is_flagged_without_changing_the_number():
    plain = effective_nose_radius_report(2.4, 1.0, 0.2, VELOCITY_GRADIENT, cone_span_fraction=0.0)
    flagged = effective_nose_radius_report(2.4, 1.0, 0.2, VELOCITY_GRADIENT,
                                           cone_span_fraction=0.7)
    assert flagged.effective_nose_radius_m == plain.effective_nose_radius_m
    assert any("fore-cone" in n for n in flagged.notes)
    assert plain.notes == ()


def test_repeated_calls_are_deterministic():
    a = [effective_nose_radius_report(2.4, 1.0, 0.2, VELOCITY_GRADIENT) for _ in range(5)]
    assert len({x.effective_nose_radius_m for x in a}) == 1


# -- cross-check against the second primary ------------------------------------------------

# Zoby & Sullivan TM X-1067 figure 4, digitised (+-0.010). Ellison's own p.5 statement is
# the yardstick: "agree ... within 10 percent for K = 0 and K = 0.707; however, for
# K = 0.417 and R = 0, the disagreement is about 20 percent." Tolerances below are that
# statement widened by the figure read-off error.
_ZOBY_SULLIVAN_SHARP = {0.00: 0.286}
_ZOBY_SULLIVAN_BUNDLE = {0.70: 0.732, 0.75: 0.776, 0.80: 0.820, 0.85: 0.868,
                         0.90: 0.916, 1.00: 1.000}


@pytest.mark.parametrize("k,expected", sorted(_ZOBY_SULLIVAN_BUNDLE.items()))
def test_agrees_with_zoby_sullivan_where_both_primaries_say_they_agree(k, expected):
    """K >= 0.7: Ellison says within 10 percent, and the curves have merged there."""
    assert rb_over_reff(k, 0.2) == pytest.approx(expected, rel=0.05)


def test_flat_face_disagreement_matches_ellisons_stated_ten_percent():
    disagreement = abs(rb_over_reff(0.0, 0.0) - _ZOBY_SULLIVAN_SHARP[0.00]) / \
        _ZOBY_SULLIVAN_SHARP[0.00]
    assert disagreement < 0.15, "Ellison states 10 percent at K = 0; +-0.010 read widens it"


def test_the_documented_twenty_percent_disagreement_is_reproduced_not_smoothed_away():
    """The worst inter-source disagreement sits at K ~ 0.42 - exactly where M4's front is.

    Zoby & Sullivan's r_C/r_B = 0.30 curve reads 0.502 at K = 0.40 and the merged bundle
    reads 0.530 at K = 0.45, so about 0.512 at K = 0.417. Ellison's measured value at the
    same K and the closest tabulated corner ratio is 0.640. If a future edit quietly
    replaced this table with something that split the difference, this test would catch
    it - the disagreement is a real, documented feature of the literature, not noise.
    """
    zoby_sullivan_at_k417 = 0.512
    ratio = rb_over_reff(0.417, 0.4) / zoby_sullivan_at_k417
    assert 1.10 < ratio < 1.35, "Ellison p.5 says the disagreement here is about 20 percent"


def test_zoby_sullivan_own_eleven_percent_checksum():
    """TM X-1067 p.6: the fig-3 ordinate rises ~11% as r_C/r_B goes 0 -> 0.3 at K = 0.

    Fig 3's ordinate is the square root of fig 4's, and it is also q_BB/q_Hemi. Applying
    the paper's own statement to Ellison's numbers is an independent check that the two
    data sets describe the same physical effect with the same sign and rough size.
    """
    ellison_ratio = np.sqrt(rb_over_reff(0.0, 0.3) / rb_over_reff(0.0, 0.0))
    zoby_sullivan_ratio = np.sqrt(0.365 / 0.286)
    assert ellison_ratio == pytest.approx(1.11, abs=0.04)
    assert zoby_sullivan_ratio == pytest.approx(1.13, abs=0.04)


# -- integration with CapsuleGeometry and the evaluator ------------------------------------


def test_capsule_default_model_is_the_legacy_identity():
    geom = CapsuleGeometry(**FRONT_LIKE)
    assert geom.effective_nose_radius_model == CAP_RADIUS
    assert geom.effective_nose_radius_m == geom.nose_radius_m


def test_capsule_velocity_gradient_model_shrinks_this_front_like_nose():
    geom = _capsule()
    report = geom.effective_nose_radius_report()
    assert report.k_body_over_nose == pytest.approx(1.0 / (2 * 1.19), rel=1e-9)
    assert report.corner_ratio == pytest.approx(0.2, rel=1e-9)
    assert not report.extrapolated
    assert report.notes == ()
    assert geom.effective_nose_radius_m < geom.nose_radius_m
    assert report.ratio_to_cap_radius == pytest.approx(0.685, abs=0.01)


def test_front_like_capsule_has_a_short_fore_cone_like_the_reference_bodies():
    """The sources' bodies have none at all; this one must at least be close."""
    assert _capsule()._fore_cone_span_fraction < 0.10


def test_the_model_changes_no_geometry():
    """It is a heating-model switch, not a shape parameter."""
    cap, vel = _capsule(CAP_RADIUS), _capsule(VELOCITY_GRADIENT)
    assert cap.reference_area_m2 == vel.reference_area_m2
    assert cap.wetted_forebody_area_m2 == vel.wetted_forebody_area_m2
    assert cap.enclosed_volume_m3 == vel.enclosed_volume_m3
    assert np.array_equal(np.asarray(cap.profile()), np.asarray(vel.profile()))


def test_unknown_model_is_rejected_by_validate():
    with pytest.raises(ValueError, match="effective_nose_radius_model must be one of"):
        CapsuleGeometry(**FRONT_LIKE, effective_nose_radius_model="newtonian").validate()


def test_legacy_two_parameter_config_refuses_the_correction():
    """No body radius, no corner radius - so silently ignoring the key is not an option."""
    cfg = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    cfg["vehicle"]["geometry"]["effective_nose_radius_model"] = VELOCITY_GRADIENT
    with pytest.raises(ValueError, match="needs a full capsule"):
        evaluate_design(cfg)


def test_evaluator_uses_the_geometric_radius_for_bluntness_and_the_effective_one_for_heat():
    """The bluntness constraint is a statement about GEOMETRY and must stay one."""
    cfg = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    cfg["vehicle"]["geometry"] = {**FRONT_LIKE,
                                  "effective_nose_radius_model": VELOCITY_GRADIENT}
    cfg["limits"] = {**cfg.get("limits", {}), "max_bluntness_ratio": 1.2}
    ev = evaluate_design(cfg)
    assert ev.design_vector["nose_radius_m"] == pytest.approx(FRONT_LIKE["nose_radius_m"])
    assert ev.diagnostics["bluntness_ratio"] == pytest.approx(1.19, rel=1e-9)
    assert ev.diagnostics["effective_nose_radius_m"] < FRONT_LIKE["nose_radius_m"]
    assert ev.diagnostics["nose_model_extrapolated"] == 0.0


def test_switching_the_model_raises_peak_flux_for_a_shallow_segment():
    base = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    cfg_cap = copy.deepcopy(base)
    cfg_cap["vehicle"]["geometry"] = {**FRONT_LIKE, "effective_nose_radius_model": CAP_RADIUS}
    cfg_vel = copy.deepcopy(base)
    cfg_vel["vehicle"]["geometry"] = {**FRONT_LIKE,
                                      "effective_nose_radius_model": VELOCITY_GRADIENT}
    cap, vel = evaluate_design(cfg_cap), evaluate_design(cfg_vel)
    assert vel.performance.peak_heat_flux_w_m2 > cap.performance.peak_heat_flux_w_m2
    assert vel.performance.peak_bondline_temperature_k > \
        cap.performance.peak_bondline_temperature_k
    # q'' scales as 1/sqrt(R_eff) and nothing else in the chain changed
    ratio = vel.performance.peak_heat_flux_w_m2 / cap.performance.peak_heat_flux_w_m2
    expected = np.sqrt(FRONT_LIKE["nose_radius_m"] /
                       _capsule().effective_nose_radius_m)
    assert ratio == pytest.approx(expected, rel=1e-9)


# -- the reproducibility guarantee ---------------------------------------------------------

M1_RUN = REPO_ROOT / "results" / "M1" / "M1-20260902T130424Z" / "candidates.csv"


def test_persisted_m1_results_are_reproduced_bit_for_bit_under_the_default():
    """The default model must leave every pre-existing result untouched, exactly.

    Not 'within a tolerance' - the same float64. M1 predates this change entirely, so any
    difference at all would mean the default is no longer the legacy model.
    """
    base = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    with open(M1_RUN) as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "the persisted M1 run must still be on disk for this test to mean anything"
    for row in rows:
        cfg = copy.deepcopy(base)
        cfg["entry"]["flight_path_angle_deg"] = float(row["gamma_deg"])
        ev = evaluate_design(cfg, design_id=row["design_id"])
        for name in ("peak_heat_flux_w_m2", "integrated_external_heat_j_m2",
                     "peak_surface_temperature_k", "peak_bondline_temperature_k",
                     "max_g", "max_dynamic_pressure_pa", "entry_duration_s"):
            assert getattr(ev.performance, name) == float(row[name]), (
                f"{row['design_id']}: {name} moved under the default model"
            )
        assert ev.design_vector["nose_radius_m"] == float(row["nose_radius_m"])


def test_explicit_cap_radius_is_identical_to_omitting_the_key():
    base = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    without = copy.deepcopy(base)
    without["vehicle"]["geometry"] = dict(FRONT_LIKE)
    with_key = copy.deepcopy(base)
    with_key["vehicle"]["geometry"] = {**FRONT_LIKE, "effective_nose_radius_model": CAP_RADIUS}
    a, b = evaluate_design(without), evaluate_design(with_key)
    assert a.performance.peak_heat_flux_w_m2 == b.performance.peak_heat_flux_w_m2
    assert a.performance.peak_bondline_temperature_k == b.performance.peak_bondline_temperature_k
    assert a.design_id == b.design_id, "the design hash must not depend on the model key"


# -- the configuration decisions taken on 2026-09-20 ---------------------------------------


def _design_space_cfg() -> dict:
    return load_config(REPO_ROOT / "configs" / "design_space.yaml")


def test_m4_design_space_now_defaults_to_the_corrected_model():
    overrides = _design_space_cfg()["base_overrides"]
    assert overrides["vehicle"]["geometry"]["effective_nose_radius_model"] == VELOCITY_GRADIENT


def test_the_bluntness_fence_has_been_relaxed_to_a_geometry_bound():
    """NR-15's fence was a model-validity limit; the model no longer needs one.

    `null` means SKIPPED (A-LIM-2), leaving `CapsuleGeometry.validate()` - i.e. whether
    the nose cap actually fits inside the body - as the only thing stopping the nose
    flattening. A number here again would be a fence again.
    """
    assert _design_space_cfg()["base_overrides"]["limits"]["max_bluntness_ratio"] is None


def test_the_reference_design_is_a_hemisphere_so_the_default_change_does_not_move_it():
    """Not a coincidence worth leaving unpinned: diameter 1.2 m with bluntness 0.5 puts
    R_n exactly on D/2, so K = 1 and the correction is identically inert. That is why
    the baseline, M1 and M1b results are untouched by switching the default, and why
    `test_full_geometry_path_reproduces_the_legacy_two_parameter_result` still passes.
    """
    variables = _design_space_cfg()["variables"]
    diameter = variables["diameter_m"]["reference"]
    bluntness = variables["bluntness_ratio"]["reference"]
    assert bluntness * diameter == pytest.approx(diameter / 2.0)
    geom = CapsuleGeometry(
        nose_radius_m=bluntness * diameter, diameter_m=diameter,
        shoulder_radius_m=variables["shoulder_ratio"]["reference"] * diameter,
        cone_half_angle_deg=variables["cone_half_angle_deg"]["reference"],
        aft_cone_angle_deg=variables["aft_cone_angle_deg"]["reference"],
        length_m=variables["fineness_ratio"]["reference"] * diameter,
        effective_nose_radius_model=VELOCITY_GRADIENT,
    )
    assert geom.effective_nose_radius_m == pytest.approx(geom.nose_radius_m, rel=1e-12)


def test_the_corner_radius_is_no_longer_inert_for_the_optimiser():
    """M4 froze shoulder_ratio on a Sobol total-order index of exactly 0. Not any more."""
    variables = _design_space_cfg()["variables"]
    diameter = 3.376
    def flux_scale(shoulder_ratio: float) -> float:
        geom = CapsuleGeometry(
            nose_radius_m=1.19 * diameter, diameter_m=diameter,
            shoulder_radius_m=shoulder_ratio * diameter, cone_half_angle_deg=69.0,
            aft_cone_angle_deg=20.0, length_m=0.875 * diameter,
            effective_nose_radius_model=VELOCITY_GRADIENT,
        )
        return 1.0 / np.sqrt(geom.effective_nose_radius_m)
    lo = flux_scale(variables["shoulder_ratio"]["min"])
    hi = flux_scale(variables["shoulder_ratio"]["max"])
    assert hi > lo, "a rounder shoulder must raise stagnation heating"
    assert 0.005 < hi / lo - 1.0 < 0.03, "about 1.5% of peak flux across the box"
