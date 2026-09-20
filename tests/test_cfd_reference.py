"""Gate G4 - closed-form references used to judge the CFD benchmark."""

import math

import numpy as np
import pytest

from src.aether.cfd.reference import (
    billig_shock_radius_over_radius,
    billig_shock_x_m,
    billig_standoff_over_radius,
    normal_shock_density_ratio,
    normal_shock_pressure_ratio,
    rayleigh_pitot_ratio,
    stagnation_pressure_coefficient,
)


def test_normal_shock_against_naca_1135_table_values():
    """NACA Report 1135 Table II, gamma = 1.4: M=2 -> p2/p1 = 4.500, rho2/rho1 = 2.667;
    M=3 -> p2/p1 = 10.33, rho2/rho1 = 3.857."""
    assert normal_shock_pressure_ratio(2.0) == pytest.approx(4.5, rel=1e-12)
    assert normal_shock_density_ratio(2.0) == pytest.approx(8.0 / 3.0, rel=1e-12)
    assert normal_shock_pressure_ratio(3.0) == pytest.approx(31.0 / 3.0, rel=1e-12)
    assert normal_shock_density_ratio(3.0) == pytest.approx(27.0 / 7.0, rel=1e-12)


def test_density_ratio_tends_to_strong_shock_limit():
    assert normal_shock_density_ratio(1e4) == pytest.approx(6.0, rel=1e-6)


def test_rayleigh_pitot_hand_worked_mach_2():
    """Hand calculation, gamma = 1.4, M = 2:
    p02/p1 = [(2.4^2 * 4) / (4*1.4*4 - 0.8)]^3.5 * (1 - 1.4 + 2.8*4)/2.4
           = (23.04/21.6)^3.5 * 4.5 = 1.066667^3.5 * 4.5 = 5.6404
    which is the value tabulated in NACA 1135 (p02/p1 = 5.640 at M = 2)."""
    assert rayleigh_pitot_ratio(2.0) == pytest.approx(5.6404, rel=1e-4)


def test_rayleigh_pitot_equals_isentropic_times_total_pressure_loss():
    """Independent route: p02/p1 = (p02/p01) * (p01/p1), built from separate relations."""
    g, m = 1.4, 3.0
    p01_p1 = (1 + 0.5 * (g - 1) * m**2) ** (g / (g - 1))
    p02_p01 = (((g + 1) * m**2 / ((g - 1) * m**2 + 2)) ** (g / (g - 1))
               * ((g + 1) / (2 * g * m**2 - (g - 1))) ** (1 / (g - 1)))
    assert rayleigh_pitot_ratio(m, g) == pytest.approx(p01_p1 * p02_p01, rel=1e-12)


def test_rayleigh_pitot_continuous_at_mach_one():
    isentropic = (1 + 0.2) ** 3.5
    assert rayleigh_pitot_ratio(1.0 + 1e-9) == pytest.approx(isentropic, rel=1e-6)


def test_stagnation_cp_hypersonic_limit():
    """Cp,max -> [(g+1)^2/(4g)]^(g/(g-1)) * 4/(g+1) = 1.839 for gamma = 1.4."""
    g = 1.4
    limit = ((g + 1) ** 2 / (4 * g)) ** (g / (g - 1)) * 4 / (g + 1)
    assert stagnation_pressure_coefficient(1e3) == pytest.approx(limit, rel=1e-5)
    assert limit == pytest.approx(1.839, abs=1e-3)


def test_billig_standoff_hand_worked():
    """delta/R = 0.143 exp(3.24/M^2): M=3 -> 0.143*exp(0.36) = 0.20497."""
    assert billig_standoff_over_radius(3.0) == pytest.approx(0.143 * math.exp(0.36), rel=1e-12)
    assert billig_standoff_over_radius(3.0) == pytest.approx(0.20497, abs=5e-6)
    assert billig_standoff_over_radius(1e6) == pytest.approx(0.143, rel=1e-9)


def test_billig_standoff_decreases_with_mach():
    d = [billig_standoff_over_radius(m) for m in (1.5, 2, 3, 4, 6, 10)]
    assert all(a > b for a, b in zip(d, d[1:], strict=False))


def test_billig_shock_shape_vertex_curvature_and_asymptote():
    mach, rn = 4.0, 0.5
    delta = billig_standoff_over_radius(mach) * rn
    rc = billig_shock_radius_over_radius(mach) * rn
    assert billig_shock_x_m(np.array([0.0]), mach, rn)[0] == pytest.approx(-delta, rel=1e-12)
    # near the vertex the hyperbola is the osculating parabola x = -delta + r^2 / (2 Rc)
    r = 1e-4
    assert billig_shock_x_m(np.array([r]), mach, rn)[0] + delta == pytest.approx(
        r**2 / (2 * rc), rel=1e-5)
    # far away dr/dx -> tan(Mach angle)
    r_far = np.array([1e5, 1.1e5])
    x_far = billig_shock_x_m(r_far, mach, rn)
    slope = (r_far[1] - r_far[0]) / (x_far[1] - x_far[0])
    assert slope == pytest.approx(math.tan(math.asin(1 / mach)), rel=1e-6)


@pytest.mark.parametrize("fn", [rayleigh_pitot_ratio, billig_standoff_over_radius,
                                normal_shock_density_ratio])
def test_subsonic_input_is_rejected(fn):
    with pytest.raises(ValueError):
        fn(0.8)
