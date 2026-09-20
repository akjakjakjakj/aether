"""Closed-form reference relations used to judge the CFD benchmark.

Everything here is calorically-perfect-gas theory or a published correlation. Nothing in
this module reads CFD output, so the reference values cannot be tuned towards a result.

Sources
-------
* Normal-shock and Rayleigh-pitot relations: NACA Report 1135, "Equations, Tables and
  Charts for Compressible Flow" (Ames Research Staff, 1953), eqs. 93-100.
* Shock stand-off distance and shock shape: F. S. Billig, "Shock-wave shapes around
  spherical- and cylindrical-nosed bodies", J. Spacecraft and Rockets 4(6), 822-823, 1967.
  The correlation is an empirical fit to experimental data in air; it is NOT exact.
"""

from __future__ import annotations

import math

import numpy as np

from ..utils.constants import GAMMA_AIR


def _require_supersonic(mach: float) -> None:
    if not mach > 1.0:
        raise ValueError(f"relation is defined for supersonic flow only, got M={mach}")


def normal_shock_pressure_ratio(mach: float, gamma: float = GAMMA_AIR) -> float:
    """Static pressure ratio p2/p1 across a normal shock (NACA 1135 eq. 93)."""
    _require_supersonic(mach)
    return 1.0 + 2.0 * gamma / (gamma + 1.0) * (mach**2 - 1.0)


def normal_shock_density_ratio(mach: float, gamma: float = GAMMA_AIR) -> float:
    """Density ratio rho2/rho1 across a normal shock (NACA 1135 eq. 94)."""
    _require_supersonic(mach)
    return (gamma + 1.0) * mach**2 / ((gamma - 1.0) * mach**2 + 2.0)


def rayleigh_pitot_ratio(mach: float, gamma: float = GAMMA_AIR) -> float:
    """Stagnation pressure behind a normal shock over freestream STATIC pressure, p02/p1.

    Rayleigh supersonic pitot formula (NACA 1135 eq. 100). This is the exact inviscid
    perfect-gas value of the pressure at the stagnation point of a blunt body.
    """
    _require_supersonic(mach)
    g = gamma
    a = ((g + 1.0) ** 2 * mach**2 / (4.0 * g * mach**2 - 2.0 * (g - 1.0))) ** (g / (g - 1.0))
    b = (1.0 - g + 2.0 * g * mach**2) / (g + 1.0)
    return a * b


def stagnation_pressure_coefficient(mach: float, gamma: float = GAMMA_AIR) -> float:
    """Cp at the stagnation point, (p02 - p1) / q1, from the Rayleigh-pitot relation."""
    return (rayleigh_pitot_ratio(mach, gamma) - 1.0) / (0.5 * gamma * mach**2)


def billig_standoff_over_radius(mach: float) -> float:
    """Billig (1967) shock stand-off distance over nose radius for a SPHERE in air.

    delta / R = 0.143 exp(3.24 / M^2)
    """
    _require_supersonic(mach)
    return 0.143 * math.exp(3.24 / mach**2)


def billig_shock_radius_over_radius(mach: float) -> float:
    """Billig (1967) shock vertex radius of curvature over nose radius, sphere in air.

    R_c / R = 1.143 exp(0.54 / (M - 1)^1.2)
    """
    _require_supersonic(mach)
    return 1.143 * math.exp(0.54 / (mach - 1.0) ** 1.2)


def billig_shock_x_m(
    r_m: np.ndarray,
    mach: float,
    nose_radius_m: float,
    asymptote_angle_rad: float | None = None,
    standoff_scale: float = 1.0,
) -> np.ndarray:
    """Axial position of Billig's hyperbolic bow shock, in NOSE-ORIGIN coordinates.

    x is measured downstream from the body nose (the convention of every outline in this
    package), so the shock vertex sits at x = -delta. Billig's original form measures x
    upstream from the sphere centre; the two are related by x_here = R - x_billig.

    ``asymptote_angle_rad`` is the far-field wave angle; for a sphere it is the Mach
    angle asin(1/M). ``standoff_scale`` multiplies delta and is used ONLY to size the
    computational domain with margin, never for a validation comparison.
    """
    _require_supersonic(mach)
    beta = math.asin(1.0 / mach) if asymptote_angle_rad is None else asymptote_angle_rad
    delta_m = standoff_scale * billig_standoff_over_radius(mach) * nose_radius_m
    rc_m = billig_shock_radius_over_radius(mach) * nose_radius_m
    r_m = np.asarray(r_m, dtype=float)
    cot2 = 1.0 / math.tan(beta) ** 2
    return -delta_m + rc_m * cot2 * (np.sqrt(1.0 + (r_m * math.tan(beta) / rc_m) ** 2) - 1.0)


def modified_newtonian_sphere_forebody_cd(mach: float, gamma: float = GAMMA_AIR) -> float:
    """Modified-Newtonian pressure drag of a hemisphere forebody, C_D = Cp_max / 2.

    Referenced to frontal area pi R^2 and to p_inf acting on the base. An engineering
    estimate used only as a sanity cross-check, not as a validation reference.
    """
    return 0.5 * stagnation_pressure_coefficient(mach, gamma)
