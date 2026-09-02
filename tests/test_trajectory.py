"""Gate G1B - trajectory integration stability, convergence and physical plausibility."""

import numpy as np
import pytest

from src.aether.trajectory import EntryState, VehicleAero, integrate_entry

VEHICLE = VehicleAero(mass_kg=350.0, reference_area_m2=np.pi * 0.6**2, cd=1.2)
INITIAL = EntryState(altitude_m=120_000.0, velocity_m_s=7_400.0,
                     flight_path_angle_rad=np.radians(-3.0))


def test_nominal_entry_reaches_terminal_altitude():
    r = integrate_entry(INITIAL, VEHICLE)
    assert r.success
    assert r.termination == "terminal_altitude"
    assert r.altitude_m[-1] == pytest.approx(20_000.0, abs=50.0)


def test_no_nonphysical_states():
    r = integrate_entry(INITIAL, VEHICLE)
    assert np.all(r.velocity_m_s > 0.0)
    assert np.all(r.altitude_m > 0.0)
    assert np.all(np.isfinite(r.density_kg_m3))
    assert np.all(r.dynamic_pressure_pa >= 0.0)


def test_vehicle_decelerates():
    r = integrate_entry(INITIAL, VEHICLE)
    assert r.velocity_m_s[-1] < 0.2 * r.velocity_m_s[0]


def test_tolerance_convergence():
    """Tightening the integrator tolerance must stop changing the answer."""
    peaks = []
    for rtol in (1e-6, 1e-8, 1e-10):
        r = integrate_entry(INITIAL, VEHICLE, rtol=rtol, atol=rtol, max_step_s=0.5)
        peaks.append(r.max_g)
    assert abs(peaks[2] - peaks[1]) < abs(peaks[1] - peaks[0]) + 1e-9
    assert peaks[2] == pytest.approx(peaks[1], rel=1e-4)


def test_steeper_entry_is_shorter_and_harder():
    """Physical ordering: steeper -> less time, more g. If this inverts, signs are wrong."""
    shallow = integrate_entry(
        EntryState(120_000.0, 7_400.0, np.radians(-2.0)), VEHICLE)
    steep = integrate_entry(
        EntryState(120_000.0, 7_400.0, np.radians(-7.0)), VEHICLE)
    assert steep.duration_s < shallow.duration_s
    assert steep.max_g > shallow.max_g


def test_peak_deceleration_precedes_terminal_altitude():
    r = integrate_entry(INITIAL, VEHICLE)
    assert r.time_s[int(np.argmax(r.deceleration_g))] < r.time_s[-1]


def test_ballistic_coefficient_definition():
    v = VehicleAero(mass_kg=1000.0, reference_area_m2=2.0, cd=1.0)
    assert v.ballistic_coefficient == pytest.approx(500.0)


def test_lower_ballistic_coefficient_decelerates_higher():
    """beta = m/(Cd A). A lighter, draggier vehicle must slow down at higher altitude."""
    heavy = VehicleAero(mass_kg=1500.0, reference_area_m2=np.pi * 0.6**2, cd=1.2)
    light = VehicleAero(mass_kg=200.0, reference_area_m2=np.pi * 0.6**2, cd=1.2)
    h_peak = {}
    for name, veh in (("heavy", heavy), ("light", light)):
        r = integrate_entry(INITIAL, veh)
        h_peak[name] = r.altitude_m[int(np.argmax(r.deceleration_g))]
    assert h_peak["light"] > h_peak["heavy"]
