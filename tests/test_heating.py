"""Gate G2 - Sutton-Graves scaling laws, a reference calculation, and the constant
re-derived from the primary document."""

import math

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


# --- Gate G2 - the constant, against the PRIMARY document -----------------------------
# NASA TR R-376 (Sutton & Graves, 1971), NTRS 19720003329, read from 300 dpi page renders.
# Full derivation with every step and unit: docs/theory/sutton_graves_constant.md
#
# The report does NOT contain q = k sqrt(rho/Rn) V^3 or the number 1.7415e-4. It gives
#     q_dot [MW/m^2] = K sqrt(p_s[atm] / R[m]) * (h_s - h_w)[MJ/kg]      (eq. 33, p. 13)
# with K(air) = 0.1113 kg/s-m^3/2-atm^1/2 from Table II, p. 39.

TR_R376_K_AIR = 0.1113
"""Table II, p. 39, row `0.2320 O2 - 0.7680 N2 (air)`. Units kg s^-1 m^-3/2 atm^-1/2."""

TR_R376_AIR_AVERAGE_ERROR = 0.033
"""Average correlation error for air quoted in Table II (3.3%); maximum is 9.8%.

This is the TOLERANCE for every comparison below, and it is not a number this project
chose. Demanding that a re-derivation reproduce the constant more tightly than the
primary's own fit reproduces the computations it was fitted to would be asserting
precision the source does not have.
"""

STANDARD_ATMOSPHERE_PA = 101325.0
"""Quoted inside the report itself: "1 atmosphere equals 101.325 kN/m^2" (SYMBOLS, p. 3)."""


def test_constant_matches_rederivation_from_tr_r376():
    """k = K_air / (2 sqrt(101325)), from eq. (33) plus the three standard substitutions
    (p_s = rho V^2, h_s = V^2/2, cold wall). See the theory document for the units."""
    k_derived = TR_R376_K_AIR / (2.0 * math.sqrt(STANDARD_ATMOSPHERE_PA))
    assert k_derived == pytest.approx(1.74826e-4, rel=1e-4)
    assert SUTTON_GRAVES_K_EARTH == pytest.approx(k_derived, rel=TR_R376_AIR_AVERAGE_ERROR)
    # and record how close it actually is: 0.39%, an order of magnitude inside the bound
    assert abs(SUTTON_GRAVES_K_EARTH / k_derived - 1.0) < 0.005


def test_primary_equation_in_its_own_units_reproduces_the_code():
    """End-to-end: evaluate TR R-376 eq. (33) entirely in MW/m^2, atm, m and MJ/kg, then
    convert only the answer. If someone ever "fixes" the constant, this fails."""
    rho, r_n, v = 1.0e-4, 1.0, 7_000.0
    p_s_atm = rho * v**2 / STANDARD_ATMOSPHERE_PA        # (S1) Newtonian stagnation pressure
    h_s_mj_kg = 0.5 * v**2 / 1e6                         # (S2)+(S3) cold wall, h = V^2/2
    q_mw_m2 = TR_R376_K_AIR * math.sqrt(p_s_atm / r_n) * h_s_mj_kg
    assert float(heat_flux_sutton_graves(rho, v, r_n)) == pytest.approx(
        q_mw_m2 * 1e6, rel=TR_R376_AIR_AVERAGE_ERROR
    )


def test_constant_is_exactly_the_value_every_result_was_computed_with():
    """Regression pin. This constant multiplies every heat flux in the repository, so a
    change to it invalidates every stored result. The re-derivation above deliberately
    did NOT change it - see docs/negative_results.md NR-12."""
    assert SUTTON_GRAVES_K_EARTH == 1.7415e-4
