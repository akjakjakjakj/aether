"""Gate G4 bookkeeping added on 2026-09-21 (NR-25, NR-26), tested without OpenFOAM:
which solution is 'of record', that a miss can never be hidden by a restart, how a leftover
case directory is handled, and the limit-cycle measures."""

import json

import numpy as np
import pandas as pd
import pytest

from src.aether.cfd import validation as val
from src.aether.cfd.limit_cycle import force_cycle
from src.aether.cfd.pipeline import CaseResult
from src.aether.utils.run import REPO_ROOT, load_config

CFG = load_config(REPO_ROOT / "configs" / "cfd_validation.yaml")


def _write(run_dir, name, cd, p2p, converged, status="OK"):
    d = run_dir / name
    d.mkdir(parents=True)
    res = CaseResult(name, str(d), status, n_cells=100, representative_cell_size_m=0.01,
                     metrics={"cd_fore": cd, "cd_total": cd, "n_iterations": 1000},
                     convergence={"cd_fore": {"converged": converged, "peak_to_peak_rel": p2p,
                                              "drift_rel": 1e-5}})
    (d / "case_result.json").write_text(json.dumps(res.to_dict()))


def _study(tmp_path, restarts):
    """Mach-3 fine level: original misses; ``restarts`` = {max_co: converged}."""
    _write(tmp_path, "sphere_M3_fine", 0.8472, 2.8e-3, False)
    for co, ok in restarts.items():
        _write(tmp_path, val.restart_case_name(3.0, "fine", co), 0.8469, 4e-4 if ok else 2e-3, ok)
    cand = val.collect_level_candidates(CFG, tmp_path)
    return cand, val.collect_mesh_study(CFG, tmp_path)


def test_solution_of_record_is_the_largest_courant_number_that_met_the_criterion(tmp_path):
    cand, study = _study(tmp_path, {0.1: True, 0.05: True})
    assert list(cand["case"]) == ["sphere_M3_fine", "sphere_M3_fine_Co0p1",
                                  "sphere_M3_fine_Co0p05"]
    assert study["case"].tolist() == ["sphere_M3_fine_Co0p1"]


def test_a_smaller_courant_number_is_used_only_if_the_larger_one_failed(tmp_path):
    _, study = _study(tmp_path, {0.1: False, 0.05: True})
    assert study["case"].tolist() == ["sphere_M3_fine_Co0p05"]


def test_if_nothing_converged_the_original_stays_of_record_and_stays_unconverged(tmp_path):
    _, study = _study(tmp_path, {0.1: False, 0.05: False})
    assert study["case"].tolist() == ["sphere_M3_fine"]
    assert not bool(study["cd_fore_converged"].iloc[0])


def test_gate_detail_lists_the_original_miss_even_when_a_restart_is_of_record(tmp_path):
    cand, study = _study(tmp_path, {0.1: True})
    gate = val.assess_gate(CFG, study, pd.DataFrame(), pd.DataFrame(), None, cand)
    listed = {c["case"]: c["cd_fore_converged"]
              for c in gate["conditions"]["2_force_convergence"]["detail"][
                  "all_candidate_solutions"]}
    assert listed == {"sphere_M3_fine": False, "sphere_M3_fine_Co0p1": True}
    assert gate["status"] != "PASS"            # one level of one Mach is not a study


def test_leftover_case_directory_is_set_aside_not_deleted_and_not_resumed(tmp_path, monkeypatch):
    gen, run_dir = tmp_path / "gen", tmp_path / "run"
    (gen / "caseA" / "system").mkdir(parents=True)
    (gen / "caseA" / "system" / "controlDict").write_text("half written")
    run_dir.mkdir()
    called = {}

    def fake_run_case(name, results_dir, **kwargs):
        called["fresh_dir_is_free"] = not (kwargs["generated_root"] / name).exists()
        return CaseResult(name, "x", "OK")

    monkeypatch.setattr(val, "run_case", fake_run_case)
    val._run_or_load("caseA", run_dir, generated_root=gen)
    assert called["fresh_dir_is_free"]
    aside = [p for p in gen.iterdir() if p.name.startswith("caseA__aborted_")]
    assert len(aside) == 1 and (aside[0] / "system" / "controlDict").read_text() == "half written"
    log = json.loads((run_dir / "aborted_attempts.json").read_text())
    assert log[0]["case"] == "caseA" and log[0]["contents"] == ["system"]


def test_finished_case_is_loaded_even_if_it_failed(tmp_path, monkeypatch):
    _write(tmp_path, "caseB", float("nan"), float("nan"), False, status="SOLVER_FAILED")
    monkeypatch.setattr(val, "run_case", lambda *a, **k: pytest.fail("must not re-run"))
    assert val._run_or_load("caseB", tmp_path, generated_root=tmp_path).status == "SOLVER_FAILED"


def test_force_cycle_recovers_amplitude_and_period():
    it = np.arange(5, 20005, 5)
    y = 0.85 * (1.0 + 1.4e-3 * np.sin(2 * np.pi * it / 40.0))
    c = force_cycle(pd.DataFrame({"iteration": it, "cd_fore": y}), "cd_fore", 2000, 0.2)
    assert c["peak_to_peak_rel"] == pytest.approx(2.8e-3, rel=0.02)
    assert c["dominant_period_iterations"] == pytest.approx(40.0, rel=0.03)
    assert c["dominant_period_cell_transit_times"] == pytest.approx(8.0, rel=0.03)
    assert c["period_resolved"]


def test_limit_cycle_columns_are_separate_from_and_never_shrink_the_gci():
    g = pd.DataFrame({
        "level": ["coarse", "medium", "fine"], "case": ["c", "m", "f"],
        "cd_fore": [0.8444, 0.8461, 0.8472], "h_m": [0.04, 0.02, 0.01],
        "cd_fore_peak_to_peak_rel": [5e-4, 8e-4, 2.8e-3],
        "cd_fore_converged": [True, True, False]}).set_index("level")
    out = val._limit_cycle_columns("cd_fore", g)
    assert out["limit_cycle_half_p2p_rel_fine"] == pytest.approx(1.4e-3)
    assert out["criterion_met_fine"] is False
    assert out["gci_fine_at_cycle_extremes_max"] >= 0
    assert out["band_coarse_at_cycle_extremes_max"] >= out["band_coarse_rel"]
    assert out["discretisation_plus_cycle_rel_coarse"] == pytest.approx(
        out["band_coarse_rel"] + 2.5e-4)
