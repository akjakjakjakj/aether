"""Gate G4 - metric extraction, tested on synthetic solver output (no OpenFOAM)."""

import numpy as np
import pandas as pd
import pytest

from src.aether.cfd.case import FlowCondition
from src.aether.cfd.postprocess import (
    ConvergenceCriterion,
    assess_convergence,
    force_coefficient_history,
    outlet_min_mach,
    read_internal_field,
    shock_metrics,
    stagnation_pressure_pa,
)
from src.aether.cfd.reference import normal_shock_density_ratio

FLOW = FlowCondition(mach=3.0, pressure_pa=1000.0, temperature_k=220.0)


def _line(x_shock, width, n=400):
    """Smooth density ramp centred on x_shock, plus mild post-shock compression."""
    x = np.linspace(-0.3, -1e-4, n)
    rho1 = FLOW.density_kg_m3
    rho2 = rho1 * normal_shock_density_ratio(3.0)
    s = 0.5 * (1 + np.tanh((x - x_shock) / width))
    rho = rho1 + (rho2 - rho1) * s * (1 + 0.05 * (x - x_shock) / 0.1 * (x > x_shock))
    return pd.DataFrame({"x_m": x, "rho": rho, "p": 1000.0 + 11000.0 * s})


def test_shock_position_recovered_to_subcell_accuracy():
    m = shock_metrics(_line(-0.1065, 0.002), FLOW)
    assert m.standoff_m == pytest.approx(0.1065, abs=2e-4)     # cell size is 7.5e-4
    assert m.shock_thickness_m > 0 and m.shock_thickness_cells > 1


def test_missing_shock_raises():
    flat = pd.DataFrame({"x_m": np.linspace(-0.3, 0, 50), "rho": FLOW.density_kg_m3,
                         "p": 1000.0})
    with pytest.raises(ValueError):
        shock_metrics(flat, FLOW)


def test_stagnation_pressure_extrapolates_to_the_wall():
    line = pd.DataFrame({"x_m": [-0.03, -0.02, -0.01], "p": [100.0, 110.0, 120.0]})
    body = pd.DataFrame({"x_m": [0.0, 0.1], "r_m": [0.01, 0.3], "p_pa": [129.0, 80.0]})
    p0 = stagnation_pressure_pa(body, line)
    assert p0["line_extrapolated"] == pytest.approx(130.0)
    assert p0["wall_face"] == 129.0 and p0["max_on_body"] == 129.0


def _history(y):
    return pd.DataFrame({"iteration": np.arange(5, 5 * len(y) + 1, 5), "cd_total": y})


def test_convergence_criterion_accepts_a_settled_history():
    it = np.arange(2000)
    y = 0.9 + 0.3 * np.exp(-it / 100.0) + 1e-5 * np.sin(it)
    r = assess_convergence(_history(y), "cd_total", ConvergenceCriterion())
    assert r.converged and r.mean == pytest.approx(0.9, abs=1e-4)


def test_convergence_criterion_rejects_drift_and_oscillation_and_short_runs():
    it = np.arange(2000)
    crit = ConvergenceCriterion()
    drifting = 0.9 + 1e-6 * it
    assert not assess_convergence(_history(drifting), "cd_total", crit).converged
    buzzing = 0.9 * (1 + 1e-3 * np.sin(it / 5.0))
    res = assess_convergence(_history(buzzing), "cd_total", crit)
    assert not res.converged and res.peak_to_peak_rel == pytest.approx(2e-3, rel=0.05)
    assert not assess_convergence(_history(np.full(100, 0.9)), "cd_total", crit).converged


def _write_force(path, fx):
    path.parent.mkdir(parents=True)
    rows = ["# Force", "# Time total_x total_y total_z pressure_x ... viscous_z"]
    rows += [f"{5 * (i + 1)} {v} 0 0 {v} 0 0 0 0 0" for i, v in enumerate(fx)]
    path.write_text("\n".join(rows) + "\n")


def test_force_coefficient_scaling_from_wedge_to_full_body(tmp_path):
    """A 5-degree wedge carries 1/72 of the body. Fx_wedge chosen so that C_D = 1 exactly."""
    area = np.pi * 0.25
    fx = FLOW.dynamic_pressure_pa * area / 72.0
    _write_force(tmp_path / "postProcessing/forcesFore/0/force.dat", [fx, fx])
    h = force_coefficient_history(tmp_path, FLOW, area, 5.0)
    assert h["cd_fore"].iloc[-1] == pytest.approx(1.0, rel=1e-12)
    assert h["cd_total"].iloc[-1] == pytest.approx(1.0, rel=1e-12)
    assert np.isnan(h["cd_aft"]).all()          # absent, NOT zero

    _write_force(tmp_path / "postProcessing/forcesAft/0/force.dat", [0.1 * fx, 0.1 * fx])
    h = force_coefficient_history(tmp_path, FLOW, area, 5.0)
    assert h["cd_total"].iloc[-1] == pytest.approx(1.1, rel=1e-12)


def test_restarts_are_stitched_with_the_later_run_winning(tmp_path):
    _write_force(tmp_path / "postProcessing/forcesFore/0/force.dat", [1.0, 2.0, 3.0])
    p = tmp_path / "postProcessing/forcesFore/10/force.dat"
    p.parent.mkdir()
    p.write_text("# restart\n15 30 0 0 30 0 0 0 0 0\n20 40 0 0 40 0 0 0 0 0\n")
    h = force_coefficient_history(tmp_path, FLOW, 1.0, 360.0)
    q = FLOW.dynamic_pressure_pa
    assert list(h["iteration"]) == [5, 10, 15, 20]
    assert h["cd_fore"].to_numpy() * q == pytest.approx([1.0, 2.0, 30.0, 40.0])


def test_outlet_min_mach(tmp_path):
    d = tmp_path / "postProcessing/sampleOutlet/100"
    d.mkdir(parents=True)
    a = FLOW.speed_of_sound_m_s
    (d / "T_outlet.raw").write_text("# x y z T\n0 1 0 220\n0 2 0 220\n")
    (d / "U_outlet.raw").write_text(f"# x y z Ux Uy Uz\n0 1 0 {2 * a} 0 0\n0 2 0 0 {1.5 * a} 0\n")
    assert outlet_min_mach(tmp_path, FLOW) == pytest.approx(1.5)


def test_read_internal_field_scalar_and_vector(tmp_path):
    (tmp_path / "p").write_text("internalField   nonuniform List<scalar> \n3\n(\n1.5\n2.5\n"
                                "3.5\n)\n;\n"
                                "boundaryField { a { value nonuniform List<scalar> 1(9); } }")
    (tmp_path / "U").write_text("internalField   nonuniform List<vector> \n2\n(\n(1 2 3)\n"
                                "(4 5 6)\n)\n;\n")
    assert read_internal_field(tmp_path / "p") == pytest.approx([1.5, 2.5, 3.5])
    assert read_internal_field(tmp_path / "U").tolist() == [[1, 2, 3], [4, 5, 6]]
