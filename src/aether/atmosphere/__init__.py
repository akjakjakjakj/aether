from typing import Protocol, runtime_checkable

from .exponential import (
    ExponentialAtmosphere,
    ExponentialFit,
    fit_exponential_to_us76,
)
from .perturbed import (
    DensityMultiplierProfile,
    PerturbedAtmosphere,
    build_atmosphere,
)
from .us76 import AtmosphereState, USStandardAtmosphere1976


@runtime_checkable
class AtmosphereModel(Protocol):
    """What the trajectory integrator actually needs from an atmosphere.

    Deliberately one method. `USStandardAtmosphere1976` is the production model;
    `ExponentialAtmosphere` is the validation instrument that makes the Allen-Eggers
    closed form applicable. Anything else satisfying this can be substituted without
    touching `integrate_entry`.
    """

    def state(self, altitude_m: float) -> AtmosphereState:  # pragma: no cover - protocol
        ...


__all__ = [
    "AtmosphereModel",
    "AtmosphereState",
    "DensityMultiplierProfile",
    "ExponentialAtmosphere",
    "ExponentialFit",
    "PerturbedAtmosphere",
    "USStandardAtmosphere1976",
    "build_atmosphere",
    "fit_exponential_to_us76",
]
