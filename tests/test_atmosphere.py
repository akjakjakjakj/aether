"""Gate G1A - the atmosphere must agree with published USSA-76 values."""

import numpy as np
import pytest

from src.aether.atmosphere import USStandardAtmosphere1976, us76

ATM = USStandardAtmosphere1976(warn_above_86km=False)


def test_sea_level_matches_definition():
    """USSA-76 sea level is a DEFINED point; anything but an exact match is a bug."""
    s = ATM.state(0.0)
    assert s.temperature_k == pytest.approx(288.15, abs=1e-6)
    assert s.pressure_pa == pytest.approx(101325.0, abs=1e-6)
    assert s.density_kg_m3 == pytest.approx(1.225, rel=1e-4)
    assert s.speed_of_sound_m_s == pytest.approx(340.294, rel=1e-4)


@pytest.mark.parametrize(
    "h_geopot_m, t_ref, p_ref",
    [
        (11_000.0, 216.65, 22_632.06),
        (20_000.0, 216.65, 5_474.889),
        (32_000.0, 228.65, 868.0187),
        (47_000.0, 270.65, 110.9063),
        (51_000.0, 270.65, 66.93887),
        (71_000.0, 214.65, 3.956420),
    ],
)
def test_layer_boundaries_against_published_table(h_geopot_m, t_ref, p_ref):
    """Published USSA-76 layer-base values, reproduced to 0.1%.

    These are quoted in GEOPOTENTIAL altitude, so the geometric altitude must be
    back-converted before querying. Getting this wrong is the classic USSA-76 error.
    """
    r = us76.EARTH.r_geopotential
    z_geometric = r * h_geopot_m / (r - h_geopot_m)
    s = ATM.state(z_geometric)
    assert s.temperature_k == pytest.approx(t_ref, rel=1e-4)
    assert s.pressure_pa == pytest.approx(p_ref, rel=1e-3)


def test_density_decreases_monotonically():
    z = np.linspace(0.0, 140_000.0, 400)
    rho = np.array([ATM.state(float(zi)).density_kg_m3 for zi in z])
    assert np.all(np.diff(rho) < 0.0)


def test_ideal_gas_closure_in_homosphere():
    for z in (0.0, 5_000.0, 25_000.0, 60_000.0, 80_000.0):
        s = ATM.state(z)
        assert s.pressure_pa == pytest.approx(s.density_kg_m3 * us76.R_AIR * s.temperature_k,
                                              rel=1e-9)


def test_refuses_to_extrapolate_above_ceiling():
    with pytest.raises(ValueError, match="Refusing to extrapolate"):
        ATM.state(200_000.0)


def test_flags_extrapolation_above_86km():
    assert ATM.state(80_000.0).extrapolated is False
    assert ATM.state(100_000.0).extrapolated is True


def test_warns_once_above_86km():
    noisy = USStandardAtmosphere1976(warn_above_86km=True)
    with pytest.warns(RuntimeWarning, match="above 86 km"):
        noisy.state(100_000.0)


# --- Gate G1A' - the >86 km table against a PRIMARY copy of USSA-76 -------------------
# Source: U.S. Standard Atmosphere, 1976 (NOAA-S/T 76-1562 / NASA-TM-X-74335), Table I,
# "Geometric Altitude, Metric Units", pp. 68-69. The five rows below were read directly
# off 300 dpi page renders of the primary document, not from OCR text and not from a
# secondary tabulation - see docs/validation/sourcing_report.md section 6.
#
# TOLERANCE, and why it is this and not tighter or looser: the primary prints T to two
# decimal places and rho to four significant figures, so the tightest claim the document
# itself can support is half of its own last printed digit. That is 0.005 K on T, and
# 2.5e-4 relative on rho (half-ULP of a four-significant-figure value is at worst 1/(2*4000)
# ~ 1.25e-4 relative; 2.5e-4 carries a factor of two). Anything finer would be asserting
# precision the source does not print.
_USSA76_PRIMARY_TABLE_I = [
    # (geometric altitude [m], T [K], rho [kg m^-3])
    (90_000.0, 186.87, 3.416e-06),
    (100_000.0, 195.08, 5.604e-07),
    (110_000.0, 240.00, 9.708e-08),
    (120_000.0, 360.00, 2.222e-08),
    (150_000.0, 634.39, 2.076e-09),
]
_T_TOL_K = 0.005
_RHO_REL_TOL = 2.5e-4


@pytest.mark.parametrize("z_m, t_ref, rho_ref", _USSA76_PRIMARY_TABLE_I)
def test_upper_table_against_primary_ussa76(z_m, t_ref, rho_ref):
    """The transcribed 86-150 km table must reproduce the primary document.

    This is the check that was outstanding as A-ATM-2 / G1A'. It pins the MODEL OUTPUT
    (not the raw array) at each altitude, so a future change to the interpolation scheme
    has to keep agreeing with the source.
    """
    s = ATM.state(z_m)
    assert s.temperature_k == pytest.approx(t_ref, abs=_T_TOL_K)
    assert s.density_kg_m3 == pytest.approx(rho_ref, rel=_RHO_REL_TOL)


def test_upper_table_rows_that_are_NOT_primary_checked_are_declared():
    """Honesty guard: three of the eight table rows have no primary value behind them.

    86, 95 and 130 km were not among the altitudes read off the primary document, so
    nothing above validates them. If someone adds a row, this test fails until they
    either source it or declare it unsourced here and in ASSUMPTIONS A-ATM-2.
    """
    checked = {z for z, _, _ in _USSA76_PRIMARY_TABLE_I}
    unchecked = {float(z) for z in us76._UPPER_TABLE[:, 0]} - checked
    assert unchecked == {86_000.0, 95_000.0, 130_000.0}


def test_86km_seam_discontinuity_stays_small():
    """The exact homosphere and the transcribed table do not meet exactly at 86 km.

    They are two different constructions of the same standard (exact integration of the
    defined layer profile below, a transcribed diffusive-equilibrium tabulation above),
    so a small step is expected. This records its measured size - 0.04% in T, 0.03% in
    rho - so that it cannot grow unnoticed. It is an INTERNAL consistency check, not a
    validation against the source.
    """
    below = ATM.state(85_999.0)
    above = ATM.state(86_001.0)
    assert abs(above.temperature_k - below.temperature_k) / below.temperature_k < 1e-3
    assert abs(above.density_kg_m3 - below.density_kg_m3) / below.density_kg_m3 < 1e-3
