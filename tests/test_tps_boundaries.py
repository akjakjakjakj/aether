"""Gate G3b - the optional bench-coupon boundary terms on the 1-D conduction solver.

These terms exist for the M8 thermal-coupon experiment: a coupon on a bench loses heat
from both faces into room air and is heated through a real contact interface, none of
which happens to a heat shield in near-vacuum. They all default to zero, so the first
test here is that the entry model is untouched; the rest check each added term against a
closed-form result rather than against itself.
"""

import numpy as np
import pytest

from src.aether.tps import Layer, TPSStack, solve_tps

K, RHO, CP = 0.30, 300.0, 1200.0


def _slab(**kwargs) -> TPSStack:
    """A single 10 mm low-conductivity slab, no radiation unless asked for."""
    kwargs.setdefault("emissivity", 0.0)
    kwargs.setdefault("t_initial_k", 300.0)
    return TPSStack(layers=[Layer("slab", 0.010, K, RHO, CP, 100)], **kwargs)


def test_defaults_reproduce_the_adiabatic_entry_model_exactly():
    """Every added term is off by default: the back face must lose exactly nothing.

    This is the regression guard on every pre-existing M1 result.
    """
    t = np.linspace(0.0, 400.0, 801)
    res = solve_tps(_slab(emissivity=0.85), t, np.full_like(t, 1.0e5))
    assert np.all(res.back_loss_flux_w_m2 == 0.0)
    # and with h_front = 0 the front loss is purely radiative
    eps_sigma = 0.85 * 5.670374419e-8
    expected = eps_sigma * (res.surface_temperature_k[-1] ** 4 - 4.0**4)
    assert res.surface_loss_flux_w_m2[-1] == pytest.approx(expected, rel=1e-6)


def test_back_face_convection_reaches_the_analytical_steady_state():
    """Steady state with a convective back face is exactly solvable.

        T_back    = T_amb + q / h_back
        T_applied = T_back + q * L / k + q * R_contact

    A uniform finite-volume mesh with harmonic interface conductances reproduces a
    linear steady profile exactly, so this is a tight check, not a loose one.
    """
    q, h_back, r_contact, t_amb = 1000.0, 20.0, 1.0e-3, 295.0
    stack = _slab(h_back_w_m2k=h_back, t_ambient_k=t_amb,
                  front_contact_resistance_m2k_w=r_contact)
    t = np.linspace(0.0, 4000.0, 8001)
    res = solve_tps(stack, t, np.full_like(t, q))

    t_back_expected = t_amb + q / h_back
    t_applied_expected = t_back_expected + q * 0.010 / K + q * r_contact

    assert res.temperature_k[-1, -1] == pytest.approx(
        t_back_expected + q * (0.010 / 100) / (2 * K), rel=1e-4)
    assert res.surface_temperature_k[-1] == pytest.approx(t_applied_expected, rel=1e-4)
    assert res.back_loss_flux_w_m2[-1] == pytest.approx(q, rel=1e-4)


def test_contact_resistance_adds_exactly_its_own_temperature_drop():
    """Delta-T across the heater interface must be q * R_c and nothing else."""
    q, h_back, t_amb = 1000.0, 20.0, 295.0
    t = np.linspace(0.0, 4000.0, 8001)
    common = dict(h_back_w_m2k=h_back, t_ambient_k=t_amb)
    perfect = solve_tps(_slab(**common), t, np.full_like(t, q))
    resisted = solve_tps(_slab(front_contact_resistance_m2k_w=2.0e-3, **common),
                         t, np.full_like(t, q))
    rise = resisted.surface_temperature_k[-1] - perfect.surface_temperature_k[-1]
    assert rise == pytest.approx(q * 2.0e-3, rel=1e-3)
    # the solid itself is unaffected: the same flux still crosses it
    assert resisted.temperature_k[-1, -1] == pytest.approx(
        perfect.temperature_k[-1, -1], rel=1e-6)


def test_front_convection_gives_lumped_newton_cooling():
    """A thin, highly conductive slab cooling by convection alone is a first-order lag.

        T(t) = T_amb + (T_0 - T_amb) exp(-t / tau),   tau = rho cp L / h

    Biot number here is h L / k = 25 * 0.005 / 200 = 6e-4, so the lumped solution is
    the right thing to compare against.
    """
    h, l_m, rho_cp = 25.0, 0.005, 2700.0 * 900.0
    stack = TPSStack(
        layers=[Layer("metal", l_m, 200.0, 2700.0, 900.0, 40)],
        emissivity=0.0, h_front_w_m2k=h, t_ambient_k=300.0, t_initial_k=400.0,
    )
    tau = rho_cp * l_m / h
    t = np.linspace(0.0, 2.0 * tau, 4001)
    res = solve_tps(stack, t, np.zeros_like(t))
    for frac in (0.5, 1.0, 2.0):
        i = int(np.argmin(np.abs(t - frac * tau)))
        analytic = 300.0 + 100.0 * np.exp(-frac)
        assert res.temperature_k[i].mean() == pytest.approx(analytic, rel=2e-3), frac


def test_energy_balance_closes_with_every_loss_term_active():
    """In minus out minus stored must still close when all four sinks are on."""
    stack = _slab(emissivity=0.85, back_emissivity=0.85, h_front_w_m2k=12.0,
                  h_back_w_m2k=8.0, t_ambient_k=298.0, t_radiation_sink_k=298.0,
                  front_contact_resistance_m2k_w=1.0e-3)
    t = np.linspace(0.0, 600.0, 3001)
    q = np.where(t < 200.0, 5.0e3, 0.0)
    res = solve_tps(stack, t, q)
    assert res.energy_balance_residual < 1e-4


def test_a_cooling_run_with_no_input_flux_still_reports_a_scaled_residual():
    """Pure cool-down has zero energy IN; the residual must not divide by ~zero.

    The coupon calibration uses exactly this kind of run, so a residual that blew up to
    1e12 here would make every calibration look like a solver failure.
    """
    stack = _slab(h_front_w_m2k=15.0, h_back_w_m2k=15.0, t_ambient_k=300.0,
                  t_initial_k=360.0)
    t = np.linspace(0.0, 1500.0, 3001)
    res = solve_tps(stack, t, np.zeros_like(t))
    assert res.energy_balance_residual < 1e-4
    assert res.temperature_k[-1].mean() == pytest.approx(300.0, abs=1.0)


def test_back_radiation_cools_the_back_face():
    """Switching on back-face emissivity must lower the back temperature, not raise it."""
    t = np.linspace(0.0, 800.0, 1601)
    q = np.full_like(t, 3.0e3)
    cold = solve_tps(_slab(back_emissivity=0.9, t_radiation_sink_k=300.0,
                           t_ambient_k=300.0), t, q)
    hot = solve_tps(_slab(back_emissivity=0.0, t_ambient_k=300.0), t, q)
    assert cold.temperature_k[-1, -1] < hot.temperature_k[-1, -1]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"h_front_w_m2k": -1.0},
        {"h_back_w_m2k": -1.0},
        {"front_contact_resistance_m2k_w": -1.0e-3},
        {"back_emissivity": 1.5},
        {"t_ambient_k": 0.0},
    ],
)
def test_rejects_nonphysical_boundary_parameters(kwargs):
    with pytest.raises(ValueError):
        _slab(**kwargs)
