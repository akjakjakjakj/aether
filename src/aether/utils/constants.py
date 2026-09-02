"""Physical constants. SI only.

Every constant carries its source. An undocumented constant is a defect.
"""

from dataclasses import dataclass

SIGMA_SB = 5.670374419e-8
"""Stefan-Boltzmann constant [W m^-2 K^-4]. CODATA 2018 (exact by SI definition)."""

R_UNIVERSAL_USSA76 = 8.31432
"""Universal gas constant [J mol^-1 K^-1] as used by US Standard Atmosphere 1976.

NOTE: this differs from the modern CODATA value 8.314462618. USSA-76 is *defined*
with 8.31432, so reproducing the published USSA-76 tables requires this value. Do not
"correct" it.
"""

M_AIR_USSA76 = 28.9644e-3
"""Mean molar mass of dry air below 86 km [kg mol^-1]. USSA-76 defined value."""

R_AIR = R_UNIVERSAL_USSA76 / M_AIR_USSA76
"""Specific gas constant for air [J kg^-1 K^-1] ~= 287.053."""

GAMMA_AIR = 1.4
"""Ratio of specific heats for air, calorically perfect assumption.

Valid for the atmosphere model's speed-of-sound output in the homosphere. At the
temperatures behind a re-entry bow shock this is NOT valid; Mach here is a freestream
bookkeeping quantity, not a shock-layer property.
"""


@dataclass(frozen=True)
class Planet:
    """Gravitational and geometric parameters for the entry body."""

    name: str
    mu: float
    """Standard gravitational parameter [m^3 s^-2]."""
    radius: float
    """Mean equatorial radius used for the spherical-Earth trajectory [m]."""
    r_geopotential: float
    """Effective radius for geopotential altitude conversion [m]."""
    g0: float
    """Standard surface gravity [m s^-2]."""


EARTH = Planet(
    name="Earth",
    mu=3.986004418e14,      # IERS / EGM96 GM
    radius=6371.0e3,        # mean volumetric radius
    r_geopotential=6356.766e3,  # USSA-76 defined effective earth radius
    g0=9.80665,             # standard gravity, SI defined
)
