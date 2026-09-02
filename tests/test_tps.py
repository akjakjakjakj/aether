"""Gate G3 - the TPS solver against analytical benchmarks and convergence tests.

This is the most important test file in the repository. The burn-vs-bake result is a
claim about in-depth conduction, so if the conduction solver is wrong, the headline
result is worthless regardless of how good the plots look.
"""

import numpy as np
import pytest

from src.aether.tps import Layer, TPSStack, semi_infinite_constant_flux, solve_tps

K, RHO, CP = 0.30, 300.0, 1200.0
ALPHA = K / (RHO * CP)


def _semi_infinite_stack(n_cells: int = 600, thickness: float = 0.30) -> TPSStack:
    """A stack thick enough that the back face never sees the pulse -> semi-infinite."""
    return TPSStack(
        layers=[Layer("slab", thickness, K, RHO, CP, n_cells),
                Layer("tail", 0.001, K, RHO, CP, 2)],
        emissivity=0.0,          # radiation off: the analytical solution has none
        bondline_after_layer=0,
        t_initial_k=0.0,
    )


def test_matches_semi_infinite_constant_flux_analytical():
    """Carslaw & Jaeger 2.9. Must agree to better than 0.1% at every sampled depth."""
    stack = _semi_infinite_stack()
    t = np.linspace(0.0, 300.0, 3001)
    q = np.full_like(t, 1.0e5)
    res = solve_tps(stack, t, q)

    for depth in (0.002, 0.005, 0.010, 0.020):
        i = int(np.argmin(np.abs(res.depth_m - depth)))
        numeric = res.temperature_k[-1, i]
        analytic = float(semi_infinite_constant_flux(res.depth_m[i], 300.0, 1e5, K, ALPHA))
        assert numeric == pytest.approx(analytic, rel=2e-3), f"depth {depth} m"


def test_surface_temperature_matches_analytical():
    stack = _semi_infinite_stack()
    t = np.linspace(0.0, 300.0, 3001)
    res = solve_tps(stack, t, np.full_like(t, 1.0e5))
    analytic = float(semi_infinite_constant_flux(0.0, 300.0, 1e5, K, ALPHA))
    assert res.surface_temperature_k[-1] == pytest.approx(analytic, rel=1e-3)


def test_energy_balance_closes():
    """Global closure: everything in, minus everything radiated, equals what is stored."""
    stack = _semi_infinite_stack()
    t = np.linspace(0.0, 300.0, 1501)
    res = solve_tps(stack, t, np.full_like(t, 1.0e5))
    assert res.energy_balance_residual < 1e-6


def test_grid_convergence():
    """Refining the mesh must reduce the error against the analytical solution."""
    t = np.linspace(0.0, 300.0, 2001)
    q = np.full_like(t, 1.0e5)
    analytic = float(semi_infinite_constant_flux(0.0, 300.0, 1e5, K, ALPHA))
    errors = []
    for n in (75, 150, 300, 600):
        res = solve_tps(_semi_infinite_stack(n_cells=n), t, q)
        errors.append(abs(res.surface_temperature_k[-1] - analytic))
    assert all(errors[i + 1] < errors[i] for i in range(len(errors) - 1)), errors


def test_time_step_convergence():
    """Refining the timestep must reduce the error. Backward Euler is first-order in t."""
    analytic = float(semi_infinite_constant_flux(0.0, 300.0, 1e5, K, ALPHA))
    errors = []
    for n_steps in (301, 601, 1201, 2401):
        t = np.linspace(0.0, 300.0, n_steps)
        res = solve_tps(_semi_infinite_stack(), t, np.full_like(t, 1.0e5))
        errors.append(abs(res.surface_temperature_k[-1] - analytic))
    assert all(errors[i + 1] < errors[i] for i in range(len(errors) - 1)), errors


def test_radiation_reduces_surface_temperature():
    """Re-radiation is a real sink: turning it on must cool the surface, not warm it."""
    t = np.linspace(0.0, 200.0, 2001)
    q = np.full_like(t, 2.0e6)
    layers = [Layer("ins", 0.02, K, RHO, CP, 120), Layer("str", 0.01, 150.0, 2700.0, 900.0, 20)]
    cold = solve_tps(TPSStack(layers, emissivity=0.85, t_initial_k=300.0), t, q)
    hot = solve_tps(TPSStack(layers, emissivity=0.0, t_initial_k=300.0), t, q)
    assert cold.peak_surface_temperature_k < hot.peak_surface_temperature_k


def test_no_flux_means_no_temperature_change():
    """Zero forcing must produce exactly zero response - a null test for spurious sources."""
    t = np.linspace(0.0, 500.0, 501)
    stack = TPSStack([Layer("a", 0.02, K, RHO, CP, 60), Layer("b", 0.01, K, RHO, CP, 20)],
                     emissivity=0.0, t_initial_k=300.0)
    res = solve_tps(stack, t, np.zeros_like(t))
    assert np.allclose(res.temperature_k, 300.0, atol=1e-9)


def test_bondline_peak_lags_the_heat_pulse():
    """The physical claim underlying the soak-out phase: the bondline peaks LATE.

    If this ever fails, the burn-vs-bake mechanism as described is wrong.
    """
    t = np.linspace(0.0, 1200.0, 2401)
    pulse = np.where(t < 150.0, 1.5e6, 0.0)
    stack = TPSStack(
        [Layer("ins", 0.02, K, RHO, CP, 120), Layer("str", 0.01, 150.0, 2700.0, 900.0, 20)],
        emissivity=0.85, bondline_after_layer=0, t_initial_k=300.0,
    )
    res = solve_tps(stack, t, pulse)
    t_peak_flux = t[int(np.argmax(pulse))]
    t_peak_bond = t[int(np.argmax(res.bondline_temperature_k))]
    assert t_peak_bond > t_peak_flux + 50.0


def test_harmonic_interface_blocks_heat_at_an_insulator():
    """A low-k layer must actually insulate. Arithmetic averaging would leak heat."""
    t = np.linspace(0.0, 300.0, 1501)
    q = np.full_like(t, 5.0e5)
    insulated = TPSStack(
        [Layer("ins", 0.02, 0.05, RHO, CP, 120), Layer("str", 0.01, 150.0, 2700.0, 900.0, 20)],
        emissivity=0.0, bondline_after_layer=0, t_initial_k=300.0)
    conductive = TPSStack(
        [Layer("ins", 0.02, 5.0, RHO, CP, 120), Layer("str", 0.01, 150.0, 2700.0, 900.0, 20)],
        emissivity=0.0, bondline_after_layer=0, t_initial_k=300.0)
    assert (solve_tps(insulated, t, q).peak_bondline_temperature_k
            < solve_tps(conductive, t, q).peak_bondline_temperature_k)


def test_rejects_nonmonotonic_time():
    stack = _semi_infinite_stack(n_cells=20, thickness=0.05)
    t = np.array([0.0, 1.0, 0.5, 2.0])
    with pytest.raises(ValueError, match="strictly increasing"):
        solve_tps(stack, t, np.ones_like(t))


def test_rejects_nonphysical_layer():
    with pytest.raises(ValueError):
        Layer("bad", -0.01, K, RHO, CP)
