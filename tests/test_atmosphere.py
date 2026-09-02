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
