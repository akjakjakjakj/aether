"""Gate G1B - the 3-DOF integrator against an INDEPENDENT closed-form solution.

Everything in `test_trajectory.py` is verification: tolerance convergence, physical
ordering, no nonphysical states. None of it compares the integrator to a result derived
by anybody else, which is why the validation matrix read "verified, not validated".

This file closes that. It reproduces the published comparison in

    Putnam, Z. R. & Braun, R. D., "Extension and Enhancement of the Allen-Eggers
    Analytical Ballistic Entry Trajectory Solution", J. Guidance, Control, and
    Dynamics 38(3), 2015, pp. 414-430, DOI 10.2514/1.G000846,

whose Table 2 (p. 419) runs three entry cases through BOTH the Allen-Eggers closed form
and a full numerical integration of the planar equations of motion, and prints the
disagreement between them. That disagreement - not zero - is the expected result here.

WHY THE EXPECTED AGREEMENT IS NOT "A FEW PERCENT"
-------------------------------------------------
Allen-Eggers neglects gravity and holds the flight-path angle constant. Those are steep
entry approximations, so a CORRECT numerical integrator must disagree with the closed
form, by more and more as the entry flattens. The paper quantifies it: peak-deceleration
error -5.1% at -30 deg, +34.9% at -8.2 deg, -57.3% at -1.35 deg. An implementation that
matched the closed form to a percent at -1.35 deg would be wrong.

MATCHED ASSUMPTIONS
-------------------
Every assumption is taken from the paper (p. 415-416) rather than chosen here:
exponential atmosphere rho = 1.215 * exp(-h/8500) kg/m^3 (their rho_ref, H and h_ref = 0,
from Fegley 1995); constant gravity g = 9.81 m/s^2; spherical non-rotating Earth,
R = 6378 km; L/D = 0; constant C_D, entering only through the ballistic coefficient
beta = m/(C_D S). The integrator's `gravity_m_s2` and `planet_radius_m` hooks exist for
exactly this and are not used by any production run.

The paper does NOT publish m, S and C_D separately, only their combination, so the
vehicle below is constructed as mass = beta, area = 1, C_D = 1. That reproduces beta
exactly and is the only thing the dynamics depend on.
"""

import numpy as np
import pytest

from src.aether.atmosphere import ExponentialAtmosphere, fit_exponential_to_us76
from src.aether.trajectory import (
    EntryState,
    VehicleAero,
    allen_eggers_peak,
    deceleration_at_altitude,
    integrate_entry,
    velocity_at_altitude,
)
from src.aether.utils.constants import EARTH

# --- the published reference -----------------------------------------------------------
# Putnam & Braun 2015, p. 416 (atmosphere and planet) and Table 1 (cases).
PB_RHO_REF_KG_M3 = 1.215
PB_SCALE_HEIGHT_M = 8_500.0
PB_GRAVITY_M_S2 = 9.81
PB_PLANET_RADIUS_M = 6_378_000.0
PB_ATMOSPHERE = ExponentialAtmosphere(PB_RHO_REF_KG_M3, PB_SCALE_HEIGHT_M)

# Table 1 (p. 416) case definitions + Table 2 (p. 419) published errors.
# Error convention, stated on p. 415-416: (Allen-Eggers - numerical) / numerical * 100.
PB_CASES = [
    # id, V0 [m/s], gamma0 [deg], h0 [m], beta [kg/m^2], err_peak_g, err_V, err_h  [%]
    ("sample_return", 12_800.0, -8.20, 125_000.0, 60.0, +34.9, -2.1, -4.6),
    ("strategic", 7_200.0, -30.00, 125_000.0, 10_000.0, -5.1, -1.8, +3.6),
    ("leo_return", 7_900.0, -1.35, 100_000.0, 450.0, -57.3, +34.9, +27.0),
]

# TOLERANCE - what it is and what it is not.
#
# The EXPECTED VALUE of each error below is the published number; none of it was chosen
# by this project. What had to be chosen is how closely this integrator must reproduce
# somebody else's integrator. That is not a physics tolerance and there is no source for
# it, so it is declared here as a MEASURED RESIDUAL promoted to a regression bound: with
# every published assumption matched, the largest residual observed across all nine
# comparisons is 0.9 percentage points, and the paper publishes nothing further (its
# integrator, step size, and the m/S/C_D split behind beta are all unstated) that could
# shrink it. 1.0 point is that residual rounded up. If a future change to the integrator
# pushes any error past it, the right response is to find out why, not to widen this.
PB_ERROR_ALLOWANCE_POINTS = 1.0


def _numerical_peak(v0_m_s, gamma_deg, h0_m, beta_kg_m2):
    """Integrate one case under the paper's assumptions; return (a_max [m/s^2], V, h).

    The peak is refined by fitting a parabola through the three solver samples around
    the discrete maximum, rather than taking the sample itself. This is not cosmetic:
    the strategic case peaks at ~6 km altitude while travelling at 4.4 km/s, so
    consecutive output samples are hundreds of metres apart and the raw `argmax`
    altitude is quantised at the several-percent level - an artefact of the output grid
    masquerading as a physics disagreement. The refinement reproduces a run at a
    ten-times-finer step to better than 0.01% on all three cases, at a tenth of the cost.
    """
    vehicle = VehicleAero(mass_kg=beta_kg_m2, reference_area_m2=1.0, cd=1.0)
    r = integrate_entry(
        EntryState(h0_m, v0_m_s, np.radians(gamma_deg)),
        vehicle,
        atmosphere=PB_ATMOSPHERE,
        terminal_altitude_m=0.0,
        max_time_s=5_000.0,
        rtol=1e-10,
        atol=1e-10,
        max_step_s=0.1,
        gravity_m_s2=PB_GRAVITY_M_S2,
        planet_radius_m=PB_PLANET_RADIUS_M,
    )
    assert r.success
    # deceleration_g is normalised by the SI standard gravity; go back to m/s^2 so the
    # comparison never depends on which "surface g" either side used.
    a = np.asarray(r.deceleration_g) * EARTH.g0
    i = int(np.argmax(a))
    assert 0 < i < len(a) - 1, "peak deceleration landed on an endpoint"
    window = slice(i - 1, i + 2)
    t = r.time_s[window]
    coeffs = np.polyfit(t, a[window], 2)
    t_peak = -coeffs[1] / (2.0 * coeffs[0])
    at = lambda y: float(np.polyval(np.polyfit(t, y[window], 2), t_peak))  # noqa: E731
    return float(np.polyval(coeffs, t_peak)), at(r.velocity_m_s), at(r.altitude_m)


def _closed_form(v0_m_s, gamma_deg, beta_kg_m2):
    return allen_eggers_peak(
        entry_velocity_m_s=v0_m_s,
        entry_flight_path_angle_rad=np.radians(gamma_deg),
        ballistic_coefficient_kg_m2=beta_kg_m2,
        surface_density_kg_m3=PB_RHO_REF_KG_M3,
        inverse_scale_height_1_m=1.0 / PB_SCALE_HEIGHT_M,
        g0_m_s2=PB_GRAVITY_M_S2,
    )


def _percent_error(approx, numerical):
    return 100.0 * (approx - numerical) / numerical


# --- the closed form on its own --------------------------------------------------------


def test_velocity_at_peak_is_exp_minus_half_of_entry_velocity():
    """NACA 1381 eq. 16. The sharpest prediction the closed form makes: V_1/V_E depends
    on nothing at all - not the vehicle, not the atmosphere, not the entry angle."""
    for beta in (60.0, 450.0, 10_000.0):
        for gamma in (-1.35, -8.2, -30.0):
            sol = _closed_form(7_900.0, gamma, beta)
            assert sol.velocity_at_peak_m_s / 7_900.0 == pytest.approx(
                np.exp(-0.5), rel=1e-12
            )


def test_peak_of_the_deceleration_profile_matches_the_closed_form_peak():
    """Internal consistency: eq. 17's value must be the maximum of the eq. 13 profile,
    at the altitude eq. 15 gives. If these were derived inconsistently this fails."""
    sol = _closed_form(7_900.0, -8.0, 450.0)
    y = np.linspace(0.0, 120_000.0, 400_001)
    a = deceleration_at_altitude(
        y,
        entry_velocity_m_s=7_900.0,
        entry_flight_path_angle_rad=np.radians(-8.0),
        ballistic_coefficient_kg_m2=450.0,
        surface_density_kg_m3=PB_RHO_REF_KG_M3,
        inverse_scale_height_1_m=1.0 / PB_SCALE_HEIGHT_M,
    )
    i = int(np.argmax(a))
    assert float(a[i]) == pytest.approx(sol.peak_deceleration_m_s2, rel=1e-6)
    assert float(y[i]) == pytest.approx(sol.altitude_at_peak_m, abs=1.0)
    # eq. 13 evaluated at eq. 15's altitude must return eq. 16 exactly, not approximately
    assert float(
        velocity_at_altitude(
            sol.altitude_at_peak_m,
            entry_velocity_m_s=7_900.0,
            entry_flight_path_angle_rad=np.radians(-8.0),
            ballistic_coefficient_kg_m2=450.0,
            surface_density_kg_m3=PB_RHO_REF_KG_M3,
            inverse_scale_height_1_m=1.0 / PB_SCALE_HEIGHT_M,
        )
    ) == pytest.approx(sol.velocity_at_peak_m_s, rel=1e-6)


def test_refuses_the_branch_it_does_not_implement():
    """eq. 15 can put the peak below the reference level. NACA 1381 covers that with
    eqs. 20-21, which were not transcribed, so the function must refuse rather than
    evaluate eq. 17 outside its branch."""
    with pytest.raises(ValueError, match="eqs. 20-21"):
        _closed_form(7_900.0, -30.0, 1.0e7)


def test_rejects_horizontal_entry():
    with pytest.raises(ValueError, match="sin"):
        _closed_form(7_900.0, 0.0, 450.0)


# --- the integrator against the closed form, reproducing Table 2 ------------------------


@pytest.mark.parametrize(
    "case_id, v0, gamma_deg, h0, beta, pub_g, pub_v, pub_h", PB_CASES
)
def test_matches_published_allen_eggers_disagreement(
    case_id, v0, gamma_deg, h0, beta, pub_g, pub_v, pub_h
):
    """Putnam & Braun Table 2, p. 419, reproduced under their stated assumptions.

    Each assertion says: the amount by which THIS integrator disagrees with the closed
    form is the amount by which THEIR integrator disagreed with it.
    """
    sol = _closed_form(v0, gamma_deg, beta)
    a_num, v_num, h_num = _numerical_peak(v0, gamma_deg, h0, beta)

    err_g = _percent_error(sol.peak_deceleration_m_s2, a_num)
    err_v = _percent_error(sol.velocity_at_peak_m_s, v_num)
    err_h = _percent_error(sol.altitude_at_peak_m, h_num)

    assert err_g == pytest.approx(pub_g, abs=PB_ERROR_ALLOWANCE_POINTS), (
        f"{case_id}: peak-deceleration disagreement {err_g:+.2f}%, "
        f"published {pub_g:+.1f}%"
    )
    assert err_v == pytest.approx(pub_v, abs=PB_ERROR_ALLOWANCE_POINTS), (
        f"{case_id}: velocity-at-peak disagreement {err_v:+.2f}%, published {pub_v:+.1f}%"
    )
    assert err_h == pytest.approx(pub_h, abs=PB_ERROR_ALLOWANCE_POINTS), (
        f"{case_id}: altitude-at-peak disagreement {err_h:+.2f}%, published {pub_h:+.1f}%"
    )


def test_disagreement_grows_as_the_entry_flattens():
    """The published pattern, and the reason the closed form is a steep-entry solution.

    Note this is an ordering over the three published cases, which differ in entry
    velocity and ballistic coefficient as well as in entry angle - it is the paper's
    own case set, not a controlled sweep in gamma alone.
    """
    errs = {}
    for case_id, v0, gamma_deg, h0, beta, *_ in PB_CASES:
        sol = _closed_form(v0, gamma_deg, beta)
        a_num, _, _ = _numerical_peak(v0, gamma_deg, h0, beta)
        errs[case_id] = abs(_percent_error(sol.peak_deceleration_m_s2, a_num))
    assert errs["strategic"] < errs["sample_return"] < errs["leo_return"]


# --- the exponential-atmosphere hook itself ---------------------------------------------


def test_exponential_atmosphere_is_exactly_exponential():
    atm = ExponentialAtmosphere(1.215, 8_500.0)
    assert atm.state(0.0).density_kg_m3 == pytest.approx(1.215, rel=1e-12)
    assert atm.state(8_500.0).density_kg_m3 == pytest.approx(1.215 / np.e, rel=1e-12)
    assert atm.inverse_scale_height_1_m == pytest.approx(1.0 / 8_500.0, rel=1e-12)


def test_us76_fit_is_a_usable_exponential_but_not_a_good_atmosphere():
    """The fitted exponential is a validation instrument, not a model of the air.

    A single exponential cannot represent USSA-76: the real scale height runs from about
    6.4 km near the surface to about 8.5 km higher up. This pins that the fit is honest
    about it - the worst-case density ratio over 0-100 km is well over 1.3 - so nobody
    mistakes `fit_exponential_to_us76` for an improvement on `USStandardAtmosphere1976`.
    """
    fit = fit_exponential_to_us76(0.0, 100_000.0)
    assert 6_000.0 < fit.atmosphere.scale_height_m < 9_000.0
    assert np.exp(fit.max_abs_log_residual) > 1.3
    assert fit.rms_log_residual > 0.05


def test_production_default_is_unchanged_by_the_validation_hooks():
    """`gravity_m_s2=None` and `planet_radius_m=None` must be bit-identical to the
    integrator as it was before these hooks existed. No config sets either."""
    vehicle = VehicleAero(mass_kg=350.0, reference_area_m2=np.pi * 0.6**2, cd=1.2)
    initial = EntryState(120_000.0, 7_400.0, np.radians(-3.0))
    a = integrate_entry(initial, vehicle)
    b = integrate_entry(initial, vehicle, gravity_m_s2=None, planet_radius_m=None)
    assert a.max_g == b.max_g
    assert a.duration_s == b.duration_s
    np.testing.assert_array_equal(a.velocity_m_s, b.velocity_m_s)


# --- the reconstructed Stardust case: inputs are incomplete ------------------------------


def test_stardust_reconstruction_is_not_attempted_because_inputs_are_missing():
    """Desai & Qualls, "Stardust Entry Reconstruction", AIAA 2008-1198 (NTRS 20080008567)
    gives V = 12.9 km/s, gamma = -8.2 deg, mass 46 kg and a radar-reconstructed peak
    deceleration of 32.89 Earth g (3-sigma dispersion +/-3.64 g).

    That is not enough to run either model. The dynamics depend on the ballistic
    coefficient m/(C_D S), and while the Stardust SRC diameter (0.8128 m, Wilmoth et al.
    AIAA 97-2510) gives S = 0.519 m^2, **no value of C_D for the flown vehicle appears in
    the sourcing pass**, and neither does the atmosphere the reconstruction used. Choosing
    a C_D to make the number come out would be fitting the answer, so the case is skipped
    rather than guessed. See docs/validation/sourcing_report.md section 5.
    """
    pytest.skip(
        "Stardust reconstruction needs C_D (and the reconstruction's atmosphere); "
        "neither is in the sourcing report - see docstring"
    )
