"""M3: base-drag model, the CFD drag surface, its guards, and gate G5 on a SYNTHETIC surface.

The synthetic table is a smooth made-up function, never CFD: these tests check the
machinery (persistence, guards, provenance, determinism), not any aerodynamic number.
"""

import copy
import json

import numpy as np
import pandas as pd
import pytest

from src.aether.aerodynamics import build_cd_model
from src.aether.aerodynamics import cfd_surface as cs
from src.aether.aerodynamics.base_drag import BaseDragModel
from src.aether.cfd import design_points as dp
from src.aether.evaluate import evaluate_design
from src.aether.geometry.capsule import CapsuleGeometry
from src.aether.studies import m3_coupled
from src.aether.utils.run import REPO_ROOT, load_config


def _fake_cd(mach, b, theta, s):
    return 0.4 + 1.1 * np.sin(np.radians(theta)) ** 2 + 0.15 * b - 0.3 * s + 0.6 / mach**2


@pytest.fixture(scope="module")
def surface_dir(tmp_path_factory):
    cfg = load_config(REPO_ROOT / "configs" / "cfd_design_points.yaml")
    points, _ = dp.build_design(cfg)
    rows = [{"point_id": p.point_id, "role": p.role, "split": p.split, "mach": p.mach,
             **p.shape(), "cd_fore": _fake_cd(p.mach, **{k: v for k, v in zip(
                 ("b", "theta", "s"), p.shape().values(), strict=True)})}
            for p in points if p.role != "scale_check"]
    inp = cfg["inputs"]
    meta = {"model": cs.MODEL_NAME, "gate_G4_status_at_build": "IN_PROGRESS",
            "source_run": "SYNTHETIC-TEST", "mesh_level": "coarse", "seed": 1,
            "model_form_rel_halfband": 0.05, "base_drag": {},
            "input_ranges": {"mach": [inp["mach"]["min"], inp["mach"]["max"]],
                             **{k: [inp[k]["min"], inp[k]["max"]] for k in cs.SHAPE_INPUTS}}}
    out = tmp_path_factory.mktemp("surface")
    cs.CfdDragSurface(pd.DataFrame(rows), meta).save(out)
    return out


BASELINE_CAPSULE = dict(nose_radius_m=0.6, diameter_m=1.2, shoulder_radius_m=0.12,
                        cone_half_angle_deg=25.0, aft_cone_angle_deg=20.0, length_m=1.05)


def _config(surface_dir, **aero):
    cfg = copy.deepcopy(load_config(REPO_ROOT / "configs" / "baseline.yaml"))
    cfg["vehicle"]["geometry"] = dict(BASELINE_CAPSULE)
    cfg["vehicle"]["aero"] = {"model": cs.MODEL_NAME, "surface_dir": str(surface_dir),
                              "allow_provisional": True, **aero}
    return cfg


# -- base drag ------------------------------------------------------------------------------

def test_base_drag_is_bounded_by_the_vacuum_limit_and_fades_as_one_over_mach_squared():
    model = BaseDragModel()
    mach = np.array([3.0, 6.0, 10.0, 20.0])
    lo, nom, hi = model.band(mach)
    assert np.all(hi <= model.vacuum_limit(mach) + 1e-15)
    assert np.all(lo <= nom) and np.all(nom <= hi)
    assert np.allclose(hi, 2.0 / (1.4 * mach**2))            # beta = 0: algebra, not data
    assert hi[-1] / hi[0] == pytest.approx((3.0 / 20.0) ** 2)
    with pytest.raises(ValueError):
        model.cd_base(5.0, position=1.5)


# -- persistence and guards -----------------------------------------------------------------

def test_surface_reloads_bit_for_bit(surface_dir):
    a, b = cs.CfdDragSurface.load(surface_dir), cs.CfdDragSurface.load(surface_dir)
    shape = cs.shape_of(CapsuleGeometry(**BASELINE_CAPSULE))
    mach = np.array([3.5, 7.0, 15.0])
    pa, pb = a.predict_fore(mach, shape), b.predict_fore(mach, shape)
    assert np.array_equal(pa.mean, pb.mean) and np.array_equal(pa.std, pb.std)
    assert np.allclose(pa.central, _fake_cd(mach, 0.5, 25.0, 0.10), atol=0.02)


def test_a_hand_edited_training_table_is_refused(surface_dir, tmp_path):
    for name in ("surface.json", "training_data.csv"):
        (tmp_path / name).write_text((surface_dir / name).read_text())
    table = pd.read_csv(tmp_path / "training_data.csv")
    table.loc[0, "cd_fore"] += 0.01
    table.to_csv(tmp_path / "training_data.csv", index=False)
    with pytest.raises(ValueError, match="hash"):
        cs.CfdDragSurface.load(tmp_path)


def test_provisional_surface_is_refused_without_the_explicit_opt_in(surface_dir):
    capsule = CapsuleGeometry(**BASELINE_CAPSULE)
    with pytest.raises(cs.GateNotPassedError):
        build_cd_model({"model": cs.MODEL_NAME, "surface_dir": str(surface_dir)}, capsule)
    model, fidelity = build_cd_model({"model": cs.MODEL_NAME, "surface_dir": str(surface_dir),
                                      "allow_provisional": True}, capsule)
    assert fidelity == 1 and model.provenance["provisional"] is True


def test_the_surface_needs_a_full_capsule(surface_dir):
    with pytest.raises(ValueError, match="full capsule"):
        build_cd_model({"model": cs.MODEL_NAME, "surface_dir": str(surface_dir),
                        "allow_provisional": True}, None)


def test_shape_outside_the_cfd_hull_is_a_rejected_candidate_not_a_silent_guess(surface_dir):
    cfg = _config(surface_dir)
    cfg["vehicle"]["geometry"].update(cone_half_angle_deg=15.0, length_m=1.4)  # below 20 deg
    ev = evaluate_design(cfg)
    assert ev.performance.status.startswith("aero surface extrapolation")
    assert not ev.performance.feasible and np.isnan(ev.performance.peak_heat_flux_w_m2)
    flagged = evaluate_design({**cfg, "vehicle": {**cfg["vehicle"], "aero": {
        **cfg["vehicle"]["aero"], "on_extrapolation": "flag"}}})
    assert flagged.diagnostics["aero_shape_extrapolated"] == 1.0
    assert flagged.aero_provenance["shape_extrapolated"] is True


def test_mach_outside_the_cfd_range_holds_the_boundary_value(surface_dir):
    model, _ = build_cd_model({"model": cs.MODEL_NAME, "surface_dir": str(surface_dir),
                               "allow_provisional": True}, CapsuleGeometry(**BASELINE_CAPSULE))
    lo, hi = model.mach_nodes[0], model.mach_nodes[-1]
    assert model(0.5, 0.0) == model(lo, 0.0)
    assert model(27.0, 0.0) == model(hi, 0.0)
    assert model(lo * 1.0001, 0.0) == pytest.approx(model(lo, 0.0), rel=1e-3)   # continuous


def test_discretisation_draw_is_an_error_until_m2_has_a_gci(surface_dir, monkeypatch):
    monkeypatch.setattr(cs, "discretisation_band", lambda *a, **k: {
        "available": False, "rel_band": None, "source": None})
    surface = cs.CfdDragSurface.load(surface_dir)
    shape = cs.shape_of(CapsuleGeometry(**BASELINE_CAPSULE))
    with pytest.raises(cs.GateNotPassedError):
        surface.cd_model(shape, z_discretisation=1.0)
    surface.cd_model(shape)                                        # nominal is fine


def test_gci_hook_reads_the_file_and_never_a_typed_number(tmp_path):
    assert cs.discretisation_band("medium", root=tmp_path)["available"] is False
    run = tmp_path / "M2-X"
    run.mkdir()
    pd.DataFrame([{"mach": 3.0, "quantity": "cd_fore", "gci_medium": 0.004, "gci_fine": 0.001,
                   "phi_coarse": 0.84, "phi_extrapolated": 0.85},
                  {"mach": 6.0, "quantity": "cd_fore", "gci_medium": 0.006, "gci_fine": 0.002,
                   "phi_coarse": 0.86, "phi_extrapolated": 0.87}]).to_csv(run / "gci.csv",
                                                                         index=False)
    assert cs.discretisation_band("medium", root=tmp_path)["rel_band"] == pytest.approx(0.006)
    assert cs.discretisation_band("coarse", root=tmp_path)["rel_band"] == pytest.approx(
        1.25 * 0.01 / 0.85)
    (run / "gate_assessment.json").write_text(json.dumps({"status": "PASS"}))
    assert cs.gate_g4_status(root=tmp_path)["status"] == "PASS"


def test_uncertainty_draws_move_cd_in_the_documented_direction(surface_dir):
    surface = cs.CfdDragSurface.load(surface_dir)
    shape = cs.shape_of(CapsuleGeometry(**BASELINE_CAPSULE))
    nominal = surface.cd_model(shape)
    assert np.all(surface.cd_model(shape, u_base=1.0).cd_total > nominal.cd_total)
    assert np.all(surface.cd_model(shape, z_gp=2.0).cd_total > nominal.cd_total)
    assert np.allclose(surface.cd_model(shape, u_model_form=1.0).cd_total - nominal.cd_total,
                       0.05 * nominal.cd_fore)


# -- gate G5 --------------------------------------------------------------------------------

def test_gate_g5_determinism_and_provenance(surface_dir):
    gate = m3_coupled.gate_g5(_config(surface_dir), repeats=2)
    assert gate["checks"]["deterministic"], gate["fingerprints"]
    assert gate["all_checks_met"], gate
    assert gate["status"] == "LIMITED"            # never PASS on a provisional surface
    prov = gate["provenance_example"]
    assert prov["gate_G4_status_at_build"] == "IN_PROGRESS"
    assert prov["surface_source_run"] == "SYNTHETIC-TEST"


def test_constant_cd_path_is_untouched_by_m3():
    cfg = copy.deepcopy(load_config(REPO_ROOT / "configs" / "baseline.yaml"))
    cfg["vehicle"]["geometry"] = dict(BASELINE_CAPSULE)
    ev = evaluate_design(cfg)
    assert ev.fidelity == 0 and ev.aero_provenance == {}
    assert not any(k.startswith("aero_") for k in ev.diagnostics)


def test_design_space_default_is_still_constant_cd():
    space = load_config(REPO_ROOT / "configs" / "design_space.yaml")
    assert space["base_overrides"]["vehicle"]["aero"]["model"] == "constant"
