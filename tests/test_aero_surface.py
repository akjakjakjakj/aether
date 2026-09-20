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
            for p in points if p.role != "scale_check" and "@M" not in p.label]
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


def test_design_space_default_is_the_current_cfd_surface_and_never_opts_into_provisional():
    space = load_config(REPO_ROOT / "configs" / "design_space.yaml")
    aero = space["base_overrides"]["vehicle"]["aero"]
    assert aero["model"] == cs.MODEL_NAME == "cfd_surface_v2"
    assert "allow_provisional" not in aero


# -- surface v2: the gate is READ, the Mach extension truncates per shape ---------------------

def _copy_surface(src, dst, **meta_changes):
    meta = json.loads((src / "surface.json").read_text())
    meta.update(meta_changes)
    (dst / "surface.json").write_text(json.dumps(meta))
    (dst / "training_data.csv").write_text((src / "training_data.csv").read_text())
    return dst


def test_a_surface_built_under_pass_is_served_without_any_opt_in(surface_dir, tmp_path,
                                                                 monkeypatch):
    passed = _copy_surface(surface_dir, tmp_path, gate_G4_status_at_build="PASS")
    capsule = CapsuleGeometry(**BASELINE_CAPSULE)
    monkeypatch.setattr(cs, "gate_g4_status", lambda *a, **k: {"status": "PASS", "source": "x"})
    model, fidelity = build_cd_model({"model": cs.MODEL_NAME, "surface_dir": str(passed)},
                                     capsule)
    assert fidelity == 1 and model.provenance["provisional"] is False
    gate = m3_coupled.gate_g5({**_config(passed), "vehicle": {**_config(passed)["vehicle"],
                               "aero": {"model": cs.MODEL_NAME, "surface_dir": str(passed)}}},
                              repeats=2)
    assert gate["status"] == "PASS" and gate["surface_provisional"] is False
    # ... and the SAME surface is refused again the moment the gate file stops saying PASS
    monkeypatch.setattr(cs, "gate_g4_status", lambda *a, **k: {"status": "LIMITED",
                                                               "source": "x"})
    with pytest.raises(cs.GateNotPassedError):
        build_cd_model({"model": cs.MODEL_NAME, "surface_dir": str(passed)}, capsule)


def test_no_gate_status_is_typed_in_source():
    """The three labels v1 carried as typed strings (design_points, surface_build,
    m3_coupled) and the fourth in the figure captions are gone; the status is read."""
    import re
    for rel in ("cfd/design_points.py", "aerodynamics/surface_build.py",
                "studies/m3_coupled.py", "aerodynamics/plots.py"):
        text = (REPO_ROOT / "src" / "aether" / rel).read_text()
        assert not re.search(r'^[A-Z_0-9]+\s*=\s*"[^"]*(IN_PROGRESS|PASS)', text, re.M), rel


def test_build_meta_records_the_gate_file_not_a_constant(monkeypatch):
    from src.aether.aerodynamics import surface_build as sb
    cfg = load_config(REPO_ROOT / "configs" / "cfd_design_points.yaml")
    for status in ("PASS", "LIMITED"):
        monkeypatch.setattr(sb, "gate_g4_status", lambda s=status: {"status": s, "source": "f"})
        meta = sb._meta(cfg, "RUN", "coarse", {"model_form_rel_halfband": 0.05})
        assert meta["gate_G4_status_at_build"] == status
        assert meta["provisional"] is (status != "PASS")
    assert meta["mach_core_max"] == 20.0 and meta["input_ranges"]["mach"][1] == 27.0


def test_v1_stays_registered_and_both_names_resolve():
    from src.aether.aerodynamics import _REGISTRY
    assert {"constant", "cfd_surface_v1", "cfd_surface_v2"} <= set(_REGISTRY)
    assert cs.surface_dir("cfd_surface_v1").name == "cfd_surface_v1"
    with pytest.raises(KeyError):
        cs.surface_dir("cfd_surface_v9")


@pytest.fixture(scope="module")
def surface_v2_dir(tmp_path_factory):
    """Synthetic v2: the Mach-extension node exists for every anchor shape EXCEPT the slender
    20-degree ones - the situation NR-28 records."""
    cfg = load_config(REPO_ROOT / "configs" / "cfd_design_points.yaml")
    points, _ = dp.build_design(cfg)
    rows = [{"point_id": p.point_id, "role": p.role, "split": p.split, "mach": p.mach,
             **p.shape(), "cd_fore": _fake_cd(p.mach, *p.shape().values())}
            for p in points if p.role != "scale_check"
            and not ("@M" in p.label and p.cone_half_angle_deg < 30.0)]
    inp = cfg["inputs"]
    meta = {"model": cs.MODEL_NAME, "gate_G4_status_at_build": "IN_PROGRESS",
            "source_run": "SYNTHETIC-TEST", "mesh_level": "coarse", "seed": 1,
            "model_form_rel_halfband": 0.05, "base_drag": {}, "mach_core_max": 20.0,
            "input_ranges": {"mach": [inp["mach"]["min"], 27.0],
                             **{k: [inp[k]["min"], inp[k]["max"]] for k in cs.SHAPE_INPUTS}}}
    out = tmp_path_factory.mktemp("surface_v2")
    cs.CfdDragSurface(pd.DataFrame(rows), meta).save(out)
    return out


def test_mach_extension_truncates_per_shape_instead_of_rejecting(surface_v2_dir):
    surface = cs.CfdDragSurface.load(surface_v2_dir)
    assert surface.mach_max == 27.0
    blunt = surface.cd_model({"bluntness_ratio": 1.18, "cone_half_angle_deg": 69.5,
                              "shoulder_ratio": 0.10})
    slender = surface.cd_model(cs.shape_of(CapsuleGeometry(**BASELINE_CAPSULE)))
    assert blunt.mach_nodes[-1] == pytest.approx(27.0)
    assert blunt.provenance["mach_top_truncated_by_hull"] is False
    assert 20.0 - 1e-9 <= slender.mach_nodes[-1] < 27.0          # core range always kept
    assert slender.provenance["mach_top_truncated_by_hull"] is True
    assert slender.provenance["mach_range"][1] == pytest.approx(slender.mach_nodes[-1])
    assert slender.provenance["shape_extrapolated"] is False
    assert slender(27.0, 0.0) == slender(float(slender.mach_nodes[-1]), 0.0)   # held above
    # a shape outside the CORE hull is still refused, exactly as in v1
    from src.aether.surrogate.gp import ExtrapolationError
    with pytest.raises(ExtrapolationError, match="outside the convex hull"):
        surface.cd_model({"bluntness_ratio": 0.5, "cone_half_angle_deg": 15.0,
                          "shoulder_ratio": 0.10})


def test_mach_extension_never_renumbers_or_redraws_the_v1_design():
    cfg = load_config(REPO_ROOT / "configs" / "cfd_design_points.yaml")
    with_ext, _ = dp.build_design(cfg)
    off = copy.deepcopy(cfg)
    off["design"]["mach_extension"]["enabled"] = False
    without, _ = dp.build_design(off)
    old = {p.point_id: p for p in without}
    new = {p.point_id: p for p in with_ext}
    assert all(new[k] == v for k, v in old.items())
    added = [p for k, p in new.items() if k not in old]
    assert added and all("@M" in p.label and p.mach == 27.0 and p.split == "train"
                         for p in added)
    assert dp.mesh_check_ids(cfg, with_ext) == dp.mesh_check_ids(off, without)


def test_courant_pass_only_takes_cases_rejected_for_the_force_criterion_alone():
    f = dp._only_force_criterion_missed
    assert f({"verdict": "REJECTED", "reasons": "force criterion not met (p2p 0.002, ...)"})
    assert not f({"verdict": "REJECTED",
                  "reasons": "force criterion not met (...) | outflow plane not supersonic"})
    assert not f({"verdict": "SOLVER_FAILED", "reasons": "rhoCentralFoam returned -4"})
    assert not f({"verdict": "USABLE", "reasons": ""})
    assert dp.courant_case_name("dp001", "coarse", 0.05) == "dp001_coarse_Co0p05"


def test_gci_hook_passes_the_labelled_iterative_columns_through(tmp_path):
    run = tmp_path / "M2-X"
    run.mkdir()
    pd.DataFrame([{"mach": 3.0, "quantity": "cd_fore", "phi_coarse": 0.84,
                   "phi_extrapolated": 0.85, "band_coarse_rel": 0.0047,
                   "limit_cycle_half_p2p_rel_coarse": 0.0002,
                   "band_coarse_at_cycle_extremes_max": 0.0055,
                   "discretisation_plus_cycle_rel_coarse": 0.0049},
                  {"mach": 6.0, "quantity": "cd_fore", "phi_coarse": 0.86,
                   "phi_extrapolated": 0.87, "band_coarse_rel": 0.0063,
                   "limit_cycle_half_p2p_rel_coarse": 0.0001,
                   "band_coarse_at_cycle_extremes_max": 0.0099,
                   "discretisation_plus_cycle_rel_coarse": 0.0064}]).to_csv(
        run / "gci.csv", index=False)
    band = cs.discretisation_band("coarse", root=tmp_path)
    assert band["rel_band"] == pytest.approx(0.0063)            # the file's own column
    assert band["iterative_half_p2p_rel"] == pytest.approx(0.0002)
    assert band["rel_band_at_cycle_extremes_max"] == pytest.approx(0.0099)
    assert band["rel_band_sampled"] == pytest.approx(0.0064)    # discretisation + iterative


def test_a_courant_restart_must_pass_in_consecutive_blocks(tmp_path):
    """NR-25's rule made explicit (NR-27): meeting the criterion in the last window only, after
    a window that missed it, is not a pass."""
    def write(flags):
        (tmp_path / "restart_blocks.json").write_text(json.dumps(
            [{"end_iteration": 5000 * (i + 1), "converged": f} for i, f in enumerate(flags)]))
    assert dp._passed_in_a_row(tmp_path / "missing", 2) is False
    write([True])
    assert dp._passed_in_a_row(tmp_path, 2) is False
    write([False, True])
    assert dp._passed_in_a_row(tmp_path, 2) is False
    write([True, False, True, True])
    assert dp._passed_in_a_row(tmp_path, 2) is True
    cfg = load_config(REPO_ROOT / "configs" / "cfd_design_points.yaml")
    assert cfg["acceptance"]["courant_retry"]["consecutive_passes"] == 2


def test_hull_coverage_and_saltelli_preflight(surface_dir):
    """Fidelity-1 pre-flight: a sub-box inside the hull passes, one that leaves it (or contains
    impossible forebodies) REFUSES before anything is spent; coverage fractions are consistent."""
    from src.aether.optimization import hull_coverage as hc
    surface = cs.CfdDragSurface.load(surface_dir)
    inside = {"bluntness_ratio": (0.3, 0.8), "cone_half_angle_deg": (60.0, 69.0),
              "shoulder_ratio": (0.03, 0.09)}
    assert hc.check_box_inside_hull(surface, inside, n_interior=256)["all_valid_and_inside_hull"]
    with pytest.raises(ValueError, match="not evaluable everywhere"):
        hc.check_box_inside_hull(surface, {**inside, "cone_half_angle_deg": (10.0, 69.0)},
                                 n_interior=256)
    cov = hc.coverage(surface, {"bluntness_ratio": (0.25, 1.35),
                                "cone_half_angle_deg": (20.0, 70.0),
                                "shoulder_ratio": (0.02, 0.10)}, n_samples=1500, seed=3)
    assert 0.0 < cov["fraction_of_box_valid_and_inside_hull"] <= min(
        cov["fraction_of_box_valid_forebody"], cov["fraction_of_box_inside_hull"])
    front = pd.DataFrame({"x__bluntness_ratio": [0.5, 1.2], "x__cone_half_angle_deg": [45.0, 70.0],
                          "x__shoulder_ratio": [0.06, 0.10]})
    audit = hc.front_hull_audit(front, {k: tuple(v) for k, v in cov["bounds"].items()}, surface)
    outcomes = {(r["input"], r["direction"], r["outcome"]) for r in audit["all_outcomes"]}
    assert ("cone_half_angle_deg", "+", "box_bound") in outcomes
    assert ("shoulder_ratio", "+", "box_bound") in outcomes
    assert audit["n_front"] == 2
