"""Allen-Eggers closed-form ballistic entry solution - an INDEPENDENT reference.

Purpose
-------
`entry3dof.py` is a numerical integration. Nothing in this repository has so far checked
it against anything derived by a different method, which is why VALIDATION_MATRIX row
G1B read "verified, not validated". This module is the different method: the 1958
closed-form solution, implemented from the primary document's own equations, with no
shared code and no shared assumptions beyond the physics both are modelling.

Source
------
Allen, H. J. & Eggers, A. J. Jr., "A Study of the Motion and Aerodynamic Heating of
Ballistic Missiles Entering the Earth's Atmosphere at High Supersonic Speeds",
**NACA Report 1381** (1958), NTRS 19930091020. (Supersedes the classified NACA TN 4047.)
Equation numbers below are that report's. Verified against the primary document in
`docs/validation/sourcing_report.md` section 5.

Assumptions - all of them stated in the primary source
------------------------------------------------------
1. Isothermal exponential atmosphere, `rho = rho_0 exp(-beta*y)`.
2. **Gravity is neglected relative to drag** during the decelerating phase.
3. **Straight-line flight path**: the flight-path angle `theta_E` does not change.
4. Constant `C_D` (the report notes this is good "as long as the total drag is largely
   pressure drag" - i.e. a blunt body).
5. Flat, non-rotating Earth over the altitude band that matters.
6. Constant mass.

Assumptions 2 and 3 are a **steep-entry** approximation. They are why the closed form is
expected to disagree with a gravity-inclusive integration by a double-digit percentage
at shallow entry angles - see `docs/validation/sourcing_report.md` section 5 for the
published quantification of exactly that (Putnam & Braun, JGCD 2015).

NOTATION WARNING
----------------
NACA 1381 uses `beta` for the **inverse atmospheric scale height** `1/H` [m^-1].
Modern restatements (and `VehicleAero.ballistic_coefficient` in this package) use
`beta` for the **ballistic coefficient** `m/(C_D A)` [kg m^-2]. They are different
physical quantities with different units. Every name in this module is spelled out in
full for that reason: `inverse_scale_height_1_m` and `ballistic_coefficient_kg_m2`.

Units: SI throughout.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..utils.constants import EARTH


@dataclass(frozen=True)
class AllenEggersSolution:
    """Closed-form peak-deceleration conditions for one ballistic entry."""

    peak_deceleration_m_s2: float
    """Magnitude of the aerodynamic deceleration at its maximum. This is DRAG ONLY -
    the gravity component along the flight path is neglected in the derivation, so this
    is the quantity to compare against `TrajectoryResult.max_g`, which is also drag
    only."""
    peak_deceleration_g: float
    """Same, in multiples of standard gravity 9.80665 m s^-2."""
    velocity_at_peak_m_s: float
    """Eq. 16: `V_1 = V_E * exp(-1/2)`. Note this is INDEPENDENT of everything except
    the entry velocity - not of the vehicle, the atmosphere or the entry angle. It is
    the sharpest single falsifiable prediction the closed form makes."""
    altitude_at_peak_m: float
    """Eq. 15."""
    entry_velocity_m_s: float
    inverse_scale_height_1_m: float
    ballistic_coefficient_kg_m2: float
    entry_flight_path_angle_rad: float
    """Magnitude, measured from the local horizontal (the report's `theta_E`)."""


def _check_inputs(
    entry_velocity_m_s: float,
    entry_flight_path_angle_rad: float,
    ballistic_coefficient_kg_m2: float,
    surface_density_kg_m3: float,
    inverse_scale_height_1_m: float,
) -> float:
    if entry_velocity_m_s <= 0.0:
        raise ValueError(f"entry velocity must be positive, got {entry_velocity_m_s}")
    if ballistic_coefficient_kg_m2 <= 0.0:
        raise ValueError(
            f"ballistic coefficient must be positive, got {ballistic_coefficient_kg_m2}"
        )
    if surface_density_kg_m3 <= 0.0 or inverse_scale_height_1_m <= 0.0:
        raise ValueError("atmosphere parameters must be positive")
    sin_theta = math.sin(abs(entry_flight_path_angle_rad))
    if sin_theta <= 0.0:
        raise ValueError(
            "entry flight-path angle must be non-zero: the solution divides by "
            "sin(theta_E), and a horizontal entry is outside its derivation."
        )
    return sin_theta


def velocity_at_altitude(
    altitude_m,
    *,
    entry_velocity_m_s: float,
    entry_flight_path_angle_rad: float,
    ballistic_coefficient_kg_m2: float,
    surface_density_kg_m3: float,
    inverse_scale_height_1_m: float,
):
    """Eq. 13 - velocity as a function of altitude [m s^-1].

        V = V_E * exp[ -rho_0 / (2 * beta * B * sin(theta_E)) * exp(-beta*y) ]

    where `B = m/(C_D A)` is the ballistic coefficient and `beta = 1/H`. The report
    writes the prefactor as `C_D rho_0 A / (2 beta m sin theta_E)`, which is the same
    quantity with `B` expanded.
    """
    sin_theta = _check_inputs(
        entry_velocity_m_s,
        entry_flight_path_angle_rad,
        ballistic_coefficient_kg_m2,
        surface_density_kg_m3,
        inverse_scale_height_1_m,
    )
    y = np.asarray(altitude_m, dtype=float)
    k = surface_density_kg_m3 / (
        2.0 * inverse_scale_height_1_m * ballistic_coefficient_kg_m2 * sin_theta
    )
    return entry_velocity_m_s * np.exp(-k * np.exp(-inverse_scale_height_1_m * y))


def deceleration_at_altitude(
    altitude_m,
    *,
    entry_velocity_m_s: float,
    entry_flight_path_angle_rad: float,
    ballistic_coefficient_kg_m2: float,
    surface_density_kg_m3: float,
    inverse_scale_height_1_m: float,
):
    """Aerodynamic deceleration magnitude [m s^-2] along the closed-form solution.

        |dV/dt| = rho(y) V(y)^2 / (2 B)

    with `V(y)` from eq. 13. Its maximum is eq. 17; this function exists so the whole
    profile can be plotted or differenced against an integration, not only its peak.
    """
    v = velocity_at_altitude(
        altitude_m,
        entry_velocity_m_s=entry_velocity_m_s,
        entry_flight_path_angle_rad=entry_flight_path_angle_rad,
        ballistic_coefficient_kg_m2=ballistic_coefficient_kg_m2,
        surface_density_kg_m3=surface_density_kg_m3,
        inverse_scale_height_1_m=inverse_scale_height_1_m,
    )
    rho = surface_density_kg_m3 * np.exp(
        -inverse_scale_height_1_m * np.asarray(altitude_m, dtype=float)
    )
    return rho * v**2 / (2.0 * ballistic_coefficient_kg_m2)


def allen_eggers_peak(
    *,
    entry_velocity_m_s: float,
    entry_flight_path_angle_rad: float,
    ballistic_coefficient_kg_m2: float,
    surface_density_kg_m3: float,
    inverse_scale_height_1_m: float,
    g0_m_s2: float = EARTH.g0,
) -> AllenEggersSolution:
    """Peak-deceleration conditions, NACA 1381 eqs. 15-17.

        y_1 = (1/beta) * ln[ rho_0 / (beta * B * sin theta_E) ]          (eq. 15)
        V_1 = V_E * exp(-1/2)                                            (eq. 16)
        |dV/dt|_max = beta * V_E^2 * sin(theta_E) / (2e)                 (eq. 17)

    `entry_flight_path_angle_rad` may be given with either sign; only its magnitude
    enters, matching the report's `theta_E` (measured from the horizontal).

    Raises
    ------
    ValueError
        If eq. 15 puts the peak below the reference level (`y_1 < 0`). The report covers
        that case with separate closed forms (eqs. 20-21) for a body that is still
        accelerating into the ground when it arrives. Those equations were **not**
        transcribed from the primary document for this project, so rather than
        extrapolating eq. 17 outside its branch, this function refuses. A vehicle in
        that regime is also outside anything AETHER models, which stops at 20 km.
    """
    sin_theta = _check_inputs(
        entry_velocity_m_s,
        entry_flight_path_angle_rad,
        ballistic_coefficient_kg_m2,
        surface_density_kg_m3,
        inverse_scale_height_1_m,
    )
    ratio = surface_density_kg_m3 / (
        inverse_scale_height_1_m * ballistic_coefficient_kg_m2 * sin_theta
    )
    y1 = math.log(ratio) / inverse_scale_height_1_m
    if y1 < 0.0:
        raise ValueError(
            f"eq. 15 gives y_1 = {y1/1e3:.2f} km, below the reference level: peak "
            "deceleration would occur at the surface and NACA 1381 eqs. 20-21 apply "
            "instead. Those are not implemented here - see the docstring."
        )
    a_max = (
        inverse_scale_height_1_m * entry_velocity_m_s**2 * sin_theta / (2.0 * math.e)
    )
    return AllenEggersSolution(
        peak_deceleration_m_s2=a_max,
        peak_deceleration_g=a_max / g0_m_s2,
        velocity_at_peak_m_s=entry_velocity_m_s * math.exp(-0.5),
        altitude_at_peak_m=y1,
        entry_velocity_m_s=entry_velocity_m_s,
        inverse_scale_height_1_m=inverse_scale_height_1_m,
        ballistic_coefficient_kg_m2=ballistic_coefficient_kg_m2,
        entry_flight_path_angle_rad=abs(entry_flight_path_angle_rad),
    )
