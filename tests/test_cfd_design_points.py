"""M3 design-point planning and acceptance rules. No OpenFOAM needed."""

import copy

import numpy as np
import pytest

from src.aether.cfd import design_points as dp
from src.aether.cfd.case import FlowCondition
from src.aether.cfd.mesh import build_mesh_plan
from src.aether.cfd.pipeline import CaseResult
from src.aether.geometry.capsule import CapsuleGeometry
from src.aether.utils.run import REPO_ROOT, load_config


@pytest.fixture(scope="module")
def cfg():
    return load_config(REPO_ROOT / "configs" / "cfd_design_points.yaml")


def test_design_is_deterministic_and_every_point_is_a_valid_capsule(cfg):
    a, skipped_a = dp.build_design(cfg)
    b, _ = dp.build_design(cfg)
    assert a == b
    assert len({p.point_id for p in a}) == len(a)
    for p in a:
        capsule = dp.forebody_capsule(diameter_m=p.diameter_m, **p.shape())
        capsule.validate()
        top = max([cfg["inputs"]["mach"]["max"], *cfg["design"]["mach_extension"]["mach"]])
        assert cfg["inputs"]["mach"]["min"] <= p.mach <= top
        if p.role == "fill":      # the Sobol fill never leaves the core Mach range
            assert p.mach <= cfg["inputs"]["mach"]["max"]
    # invalid draws are logged with a reason, never silently dropped
    assert len(skipped_a) > 0 and skipped_a["reason"].str.len().min() > 0


def test_holdout_is_drawn_from_fill_points_only(cfg):
    points, _ = dp.build_design(cfg)
    test = [p for p in points if p.split == "test"]
    assert len(test) == cfg["design"]["holdout"]["n_test"]
    assert all(p.role == "fill" for p in test)


def test_anchors_span_both_ends_of_the_mach_range(cfg):
    points, _ = dp.build_design(cfg)
    anchors = [p for p in points if p.role == "anchor" and "@M" not in p.label]
    machs = {p.mach for p in anchors}
    assert machs == {cfg["inputs"]["mach"]["min"], cfg["inputs"]["mach"]["max"]}
    labels = {p.label for p in anchors}
    assert all(sum(p.label == lb for p in anchors) == 2 for lb in labels)


def test_a_different_seed_gives_a_different_fill(cfg):
    other = copy.deepcopy(cfg)
    other["design"]["seed"] += 1
    a = [p for p in dp.build_design(cfg)[0] if p.role == "fill"]
    b = [p for p in dp.build_design(other)[0] if p.role == "fill"]
    assert [p.mach for p in a] != [p.mach for p in b]


def test_critical_cone_angle_is_the_validity_boundary():
    b, s, d = 0.8, 0.10, 1.2
    theta = dp.critical_cone_angle_deg(b, s)
    dp.forebody_capsule(b, theta + 0.2, s, d)
    with pytest.raises(ValueError):
        dp.forebody_capsule(b, theta - 0.2, s, d)


def test_scale_check_capsule_is_valid_at_the_larger_diameter(cfg):
    sc = cfg["scale_check"]
    dp.forebody_capsule(diameter_m=sc["diameter_m"], **sc["shape"])


def test_forebody_outline_is_independent_of_the_afterbody():
    """The reason aft angle and length are not surface inputs: same forebody mesh plan."""
    kw = dict(nose_radius_m=0.6, diameter_m=1.2, shoulder_radius_m=0.12,
              cone_half_angle_deg=25.0)
    plans = []
    for aft, length in ((0.0, 0.9), (20.0, 1.05)):
        capsule = CapsuleGeometry(aft_cone_angle_deg=aft, length_m=length, **kw)
        plans.append(build_mesh_plan(dp.capsule_outline(capsule, "x"), 6.0))
    a, b = (np.vstack([blk.body_xy for blk in p.blocks]) for p in plans)
    # Same nose, same shoulder station. Tolerance 1 mm, not 1e-9: with a non-zero aft angle
    # the maximum-radius station lies INSIDE the shoulder arc and is located to the nearest
    # profile sample. `forebody_capsule` uses a 0 deg aft angle, which makes it a breakpoint.
    assert np.allclose(a[[0, -1]], b[[0, -1]], atol=1e-3)
    assert plans[0].outflow_x_m == pytest.approx(plans[1].outflow_x_m, abs=1e-3)


def test_slender_cone_at_high_mach_opens_the_inflow_boundary_beyond_the_cone_shock(cfg):
    capsule = dp.forebody_capsule(0.25, 20.0, 0.02, 1.2)
    margin = dp.asymptote_margin_deg(capsule, 20.0, 1.4, cfg["domain_sizing"], 6.0)
    mach_angle = np.degrees(np.arcsin(1.0 / 20.0))
    assert mach_angle + margin > 20.0 * 1.09      # hypersonic cone shock ~1.095 * theta
    blunt = dp.forebody_capsule(1.2, 69.5, 0.10, 1.2)
    assert dp.asymptote_margin_deg(blunt, 20.0, 1.4, cfg["domain_sizing"], 6.0) == 6.0


def _ok_case(**metrics) -> CaseResult:
    base = {"outlet_min_mach": 2.0, "upstream_clearance_fraction": 0.5,
            "p_stag_over_p_inf": 1.0, "n_extensions": 0}
    return CaseResult("c", "/nonexistent", "OK", metrics={**base, **metrics},
                      convergence={"cd_fore": {"converged": True, "peak_to_peak_rel": 1e-4,
                                               "drift_rel": 1e-5}})


def test_acceptance_rejects_subsonic_outflow_and_a_crowded_shock(cfg):
    flow = FlowCondition(6.0, 1000.0, 220.0)
    acc = cfg["acceptance"]
    sub = dp.assess_case(_ok_case(outlet_min_mach=0.9), flow, acc)
    assert sub["verdict"] == "REJECTED" and any("supersonic" in r for r in sub["reasons"])
    near = dp.assess_case(_ok_case(upstream_clearance_fraction=0.05), flow, acc)
    assert near["shock_clearance_ok"] is False
    failed = dp.assess_case(CaseResult("c", "/x", "SOLVER_FAILED", "boom"), flow, acc)
    assert failed["verdict"] == "SOLVER_FAILED"


def test_unconverged_force_is_never_usable(cfg):
    case = _ok_case()
    case.convergence["cd_fore"]["converged"] = False
    out = dp.assess_case(case, FlowCondition(6.0, 1000.0, 220.0), cfg["acceptance"])
    assert out["verdict"] == "REJECTED"
    assert any("force criterion" in r for r in out["reasons"])
