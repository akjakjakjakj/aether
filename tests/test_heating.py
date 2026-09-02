"""Gate G2 - Sutton-Graves scaling laws and a reference calculation."""

import numpy as np
import pytest

from src.aether.heating import (
    SUTTON_GRAVES_K_EARTH,
    heat_flux_sutton_graves,
    integrated_heat_load,
)


def test_cubic_velocity_scaling():
    """q'' ~ V^3. Doubling velocity must multiply flux by exactly 8."""
    a = heat_flux_sutton_graves(1e-4, 3_000.0, 0.5)
    b = heat_flux_sutton_graves(1e-4, 6_000.0, 0.5)
    assert b / a == pytest.approx(8.0, rel=1e-12)


def test_sqrt_density_scaling():
    a = heat_flux_sutton_graves(1e-4, 5_000.0, 0.5)
    b = heat_flux_sutton_graves(4e-4, 5_000.0, 0.5)
    assert b / a == pytest.approx(2.0, rel=1e-12)


def test_inverse_sqrt_nose_radius_scaling():
    """Bluntness is protective: 4x the nose radius halves the stagnation flux."""
    a = heat_flux_sutton_graves(1e-4, 5_000.0, 0.5)
    b = heat_flux_sutton_graves(1e-4, 5_000.0, 2.0)
    assert b / a == pytest.approx(0.5, rel=1e-12)


def test_reference_calculation():
    """Direct evaluation of q'' = k sqrt(rho/Rn) V^3 for a documented case.

    rho = 1.0e-4 kg/m3, Rn = 1.0 m, V = 7000 m/s.
    """
    q = heat_flux_sutton_graves(1.0e-4, 7_000.0, 1.0)
    expected = SUTTON_GRAVES_K_EARTH * np.sqrt(1.0e-4 / 1.0) * 7_000.0**3
    assert q == pytest.approx(expected, rel=1e-12)
    assert 5e5 < float(q) < 1e6  # order-of-magnitude sanity: ~60 W/cm^2


def test_rejects_invalid_nose_radius():
    with pytest.raises(ValueError):
        heat_flux_sutton_graves(1e-4, 5_000.0, 0.0)


def test_rejects_negative_density():
    with pytest.raises(ValueError):
        heat_flux_sutton_graves(-1.0, 5_000.0, 0.5)


def test_integrated_load_of_constant_flux():
    t = np.linspace(0.0, 100.0, 1001)
    q = np.full_like(t, 1e5)
    assert integrated_heat_load(t, q) == pytest.approx(1e7, rel=1e-12)
