"""A density dispersion applied on top of a nominal atmosphere, for M7.

Conceptual anchor
-----------------
USSA-76 is a *standard*, not a forecast. The air a vehicle actually meets on a given day
differs from it, and the difference grows with altitude: a few percent in the troposphere,
tens of percent in the thermosphere where solar activity drives the density directly. The
entry problem is driven almost entirely by that one number (drag ~ rho, q'' ~ sqrt(rho)),
so the dispersion has to be propagated rather than assumed away.

This class is the mechanism, not the numbers. It multiplies the density of ANY
`AtmosphereModel` by an altitude-dependent factor supplied by the caller; the factor
itself is drawn by `aether.uncertainty` from a distribution declared, with its source and
its tier, in `configs/uncertainty.yaml`.

Isothermal perturbation (A-UQ-ATM-1)
------------------------------------
Density and pressure are multiplied by the SAME factor and temperature is left alone, so

    p = rho R T

still holds exactly, and the speed of sound - hence the Mach number at a given altitude
and velocity - is unchanged. That is a modelling choice with a consequence worth stating:
real upper-atmosphere density variability is substantially thermal, and a thermal anomaly
would also move the speed of sound by roughly sqrt(dT/T). Every quantity this project
reports (drag, dynamic pressure, deceleration, Sutton-Graves heat flux) depends on density
and velocity and NOT on the speed of sound, so the omission is second-order here and would
not be at Fidelity 1, where C_D is a function of Mach.

One draw per trajectory, not per time step
-------------------------------------------
The multiplier is a fixed profile for the whole entry. A density anomaly is a weather-like
field correlated over hundreds of kilometres and hours; an entry lasts a few minutes and
crosses one such field. Sampling independently at every integration step would model it as
white noise, which would average out and UNDER-state its effect on integrated quantities.
This is the same argument A-AERO-2 makes for the GP draw.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from .us76 import AtmosphereState, USStandardAtmosphere1976


@dataclass(frozen=True)
class DensityMultiplierProfile:
    """Piecewise-linear multiplier on density vs geometric altitude.

    `altitude_m` must be strictly increasing. Outside the tabulated range the end values
    are HELD - never extrapolated - because a dispersion profile is a fit to observations
    over a stated band and has no meaning above or below it.
    """

    altitude_m: tuple[float, ...]
    multiplier: tuple[float, ...]

    def __post_init__(self) -> None:
        z = np.asarray(self.altitude_m, dtype=float)
        m = np.asarray(self.multiplier, dtype=float)
        if z.ndim != 1 or z.size < 2:
            raise ValueError("a density multiplier profile needs at least two altitudes")
        if m.shape != z.shape:
            raise ValueError(f"altitude_m {z.shape} and multiplier {m.shape} differ in length")
        if np.any(np.diff(z) <= 0.0):
            raise ValueError("altitude_m must be strictly increasing")
        if np.any(~np.isfinite(m)) or np.any(m <= 0.0):
            raise ValueError("every density multiplier must be finite and strictly positive")

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> DensityMultiplierProfile:
        """Build from the `atmosphere.density_multiplier_profile` config block.

        Altitudes are given in km in YAML because that is how a dispersion table is
        published; they are converted to metres here so nothing downstream sees km
        (spec section 8).
        """
        return cls(
            altitude_m=tuple(float(z) * 1e3 for z in cfg["altitude_km"]),
            multiplier=tuple(float(m) for m in cfg["multiplier"]),
        )

    @property
    def is_identity(self) -> bool:
        return all(m == 1.0 for m in self.multiplier)

    def at(self, altitude_m: float) -> float:
        """Multiplier at one geometric altitude [m]; held outside the tabulated range."""
        return float(np.interp(float(altitude_m), np.asarray(self.altitude_m, dtype=float),
                               np.asarray(self.multiplier, dtype=float)))

    def to_dict(self) -> dict[str, list[float]]:
        return {"altitude_km": [z / 1e3 for z in self.altitude_m],
                "multiplier": list(self.multiplier)}


class PerturbedAtmosphere:
    """`AtmosphereModel` wrapper: `base` with an altitude-dependent density multiplier.

    Every other field of the state - temperature, speed of sound, viscosity and the
    `extrapolated` flag - is passed through untouched, so a perturbed run keeps the same
    >86 km provenance flag as the nominal one.
    """

    def __init__(self, base: Any, profile: DensityMultiplierProfile):
        self.base = base
        self.profile = profile

    def state(self, altitude_m: float) -> AtmosphereState:
        st = self.base.state(altitude_m)
        factor = self.profile.at(st.altitude_m)
        if factor == 1.0:
            return st
        return replace(st, density_kg_m3=st.density_kg_m3 * factor,
                       pressure_pa=st.pressure_pa * factor)

    def density(self, altitude_m):
        arr = np.atleast_1d(np.asarray(altitude_m, dtype=float))
        out = np.array([self.state(float(z)).density_kg_m3 for z in arr])
        return float(out[0]) if np.ndim(altitude_m) == 0 else out


def build_atmosphere(cfg: dict[str, Any] | None) -> Any:
    """The evaluator's atmosphere, from an optional `atmosphere:` config block.

    `None`, an empty block, or an identity profile all return a bare
    `USStandardAtmosphere1976(warn_above_86km=False)` - the exact object the evaluator
    built before M7 existed - so every pre-M7 config evaluates bit-identically.
    """
    base = USStandardAtmosphere1976(warn_above_86km=False)
    block = (cfg or {}).get("density_multiplier_profile")
    if not block:
        return base
    profile = DensityMultiplierProfile.from_config(block)
    return base if profile.is_identity else PerturbedAtmosphere(base, profile)
