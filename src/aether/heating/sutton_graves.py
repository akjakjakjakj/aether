"""Stagnation-point convective heating, Sutton-Graves engineering correlation.

Conceptual anchor
-----------------
At the stagnation point the flow is brought to rest across a bow shock, converting the
vehicle's kinetic energy into thermal energy in the shock layer, some fraction of which
is convected into the wall. Sutton and Graves reduced that to a correlation with three
levers:

    q'' = k * sqrt(rho_inf / R_n) * V_inf^3

- V^3 dominates. Halving entry speed cuts stagnation heating by a factor of 8.
- sqrt(rho) means heating peaks *before* the densest air is reached, because V has
  already collapsed by then. Peak heating and peak deceleration do not coincide.
- 1/sqrt(R_n) is why re-entry capsules are blunt. A blunt nose pushes the shock further
  from the wall and spreads the same energy over more area. Sharp is not aerodynamic
  here; sharp is fatal.

Reference
---------
K. Sutton and R. A. Graves Jr., "A General Stagnation-Point Convective-Heating Equation
for Arbitrary Gas Mixtures", NASA TR R-376, 1971.

The Earth-air constant below is the widely used SI reduction of that correlation.
STATUS: reproduced against the standard worked value in tests/test_heating.py, but the
student has NOT yet re-derived it from TR R-376 directly - see VALIDATION_MATRIX.md
row G2 (LIMITED, not PASS).

Limitations that matter for this project
----------------------------------------
- CONVECTIVE ONLY. Radiative heating from the shock layer is neglected. This is
  defensible for Earth entry at ~7.5 km/s with a moderate nose radius, and it is NOT
  defensible for lunar-return or Mars-return speeds. Do not silently reuse.
- Cold-wall correlation: no wall-temperature blowing/hot-wall correction is applied, so
  the flux delivered to a hot surface is over-predicted. That bias is CONSERVATIVE for
  a heat-shield study and is stated rather than hidden.
- Stagnation point only. It says nothing about shoulder or afterbody heating, which is
  frequently where real vehicles are damaged.
"""

from __future__ import annotations

import numpy as np

SUTTON_GRAVES_K_EARTH = 1.7415e-4
"""Sutton-Graves constant for Earth air [kg^0.5 m^-1].

Gives q'' in W m^-2 when rho is kg m^-3, R_n is m and V is m s^-1.
"""


def heat_flux_sutton_graves(
    density_kg_m3,
    velocity_m_s,
    nose_radius_m: float,
    coefficient: float = SUTTON_GRAVES_K_EARTH,
):
    """Stagnation-point convective heat flux [W m^-2].

    Parameters
    ----------
    density_kg_m3:
        Freestream density, scalar or array [kg m^-3].
    velocity_m_s:
        Freestream velocity, scalar or array [m s^-1].
    nose_radius_m:
        EFFECTIVE stagnation-point nose radius [m]. For a spherically blunted capsule
        this is the spherical cap radius, not the vehicle diameter. Confusing the two
        is the single most common way to get this equation wrong.
    coefficient:
        Correlation constant [kg^0.5 m^-1]. Defaults to the Earth-air value. Never pass
        an undocumented value.

    Returns
    -------
    Heat flux in W m^-2, same shape as the inputs.
    """
    if nose_radius_m <= 0.0:
        raise ValueError(f"nose radius must be positive, got {nose_radius_m}")
    rho = np.asarray(density_kg_m3, dtype=float)
    v = np.asarray(velocity_m_s, dtype=float)
    if np.any(rho < 0.0):
        raise ValueError("negative density passed to heating model")
    return coefficient * np.sqrt(rho / nose_radius_m) * v**3


def heat_flux_history(trajectory, nose_radius_m: float, coefficient: float = SUTTON_GRAVES_K_EARTH):
    """Convenience wrapper: q''(t) [W m^-2] along a TrajectoryResult."""
    return heat_flux_sutton_graves(
        trajectory.density_kg_m3, trajectory.velocity_m_s, nose_radius_m, coefficient
    )


def integrated_heat_load(time_s, heat_flux_w_m2) -> float:
    """Total external heat load Q = int q'' dt  [J m^-2].

    NOTE: this is the energy arriving at the OUTER surface. It is a diagnostic, not a
    measure of what reaches the bondline - the TPS decides that. Conflating the two is
    precisely the error this project exists to examine.
    """
    q = np.asarray(heat_flux_w_m2, dtype=float)
    t = np.asarray(time_s, dtype=float)
    return float(np.trapezoid(q, t))
