"""Isothermal exponential atmosphere.

Conceptual anchor
-----------------
`rho(y) = rho_0 * exp(-y / H)` is the atmosphere you get if you assume constant
temperature and constant gravity and integrate hydrostatic equilibrium once. It is
wrong in detail everywhere - the real scale height runs from about 6.4 km near the
surface to about 8.5 km in the upper stratosphere - and it is the only atmosphere for
which the entry equations have a closed-form solution.

That is the whole reason this module exists. The Allen-Eggers solution
(`aether.trajectory.allen_eggers`) is derived for THIS atmosphere and no other, so
comparing the 3-DOF integrator against it is only a test of the integrator if both are
handed the same exponential. Running the integrator on USSA-76 and the closed form on an
exponential measures the difference between two atmospheres, not the quality of either.

This model is NOT used by any AETHER production result. `configs/baseline.yaml` and
every study run on USSA-76; this is a validation instrument. See ASSUMPTIONS A-ATM-5.

Units: SI throughout. Altitude arguments are altitude above the reference level in metres.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..utils.constants import GAMMA_AIR, R_AIR
from .us76 import AtmosphereState, USStandardAtmosphere1976


@dataclass(frozen=True)
class ExponentialAtmosphere:
    """`rho = rho_0 exp(-y/H)` at a single declared temperature.

    Parameters
    ----------
    surface_density_kg_m3:
        `rho_0`, the density the exponential extrapolates to at y = 0. For a fitted
        exponential this is an extrapolation of the fit, not a measured sea-level
        density, and it is not required to equal 1.225.
    scale_height_m:
        `H`. The Allen-Eggers papers use `beta = 1/H` for this; see the notation warning
        in `allen_eggers.py`.
    temperature_k:
        Isothermal temperature, used only for pressure (ideal gas) and speed of sound.
        Neither enters the ballistic-entry comparison; they exist so this class can be
        dropped into the same `atmosphere` slot as USSA-76 without the caller branching.
    """

    surface_density_kg_m3: float
    scale_height_m: float
    temperature_k: float = 250.0

    def __post_init__(self) -> None:
        if self.surface_density_kg_m3 <= 0.0:
            raise ValueError(f"surface density must be positive, got {self.surface_density_kg_m3}")
        if self.scale_height_m <= 0.0:
            raise ValueError(f"scale height must be positive, got {self.scale_height_m}")
        if self.temperature_k <= 0.0:
            raise ValueError(f"temperature must be positive, got {self.temperature_k}")

    @property
    def inverse_scale_height_1_m(self) -> float:
        """`beta = 1/H` [m^-1] - the symbol NACA 1381 calls beta."""
        return 1.0 / self.scale_height_m

    def state(self, altitude_m: float) -> AtmosphereState:
        """Full state at an altitude [m]. No ceiling and no floor: this model is defined
        everywhere by construction, and refusing to extrapolate would be meaningless for
        an analytic function that was never a measurement."""
        z = float(altitude_m)
        rho = self.surface_density_kg_m3 * np.exp(-z / self.scale_height_m)
        t = self.temperature_k
        return AtmosphereState(
            altitude_m=z,
            temperature_k=t,
            pressure_pa=float(rho * R_AIR * t),
            density_kg_m3=float(rho),
            speed_of_sound_m_s=float(np.sqrt(GAMMA_AIR * R_AIR * t)),
            viscosity_pa_s=float("nan"),
            extrapolated=False,
        )

    def density(self, altitude_m):
        """Density [kg m^-3]. Accepts scalar or array altitude."""
        z = np.asarray(altitude_m, dtype=float)
        rho = self.surface_density_kg_m3 * np.exp(-z / self.scale_height_m)
        return float(rho) if np.ndim(altitude_m) == 0 else rho

    def temperature(self, altitude_m):
        """Temperature [K] - constant."""
        return np.full_like(np.asarray(altitude_m, dtype=float), self.temperature_k)

    def pressure(self, altitude_m):
        """Pressure [Pa], ideal gas at the declared temperature."""
        return self.density(altitude_m) * R_AIR * self.temperature_k

    def speed_of_sound(self, altitude_m):
        """Speed of sound [m s^-1] - constant."""
        a = float(np.sqrt(GAMMA_AIR * R_AIR * self.temperature_k))
        return np.full_like(np.asarray(altitude_m, dtype=float), a)


@dataclass(frozen=True)
class ExponentialFit:
    """An `ExponentialAtmosphere` plus the quality of the fit that produced it."""

    atmosphere: ExponentialAtmosphere
    band_m: tuple[float, float]
    max_abs_log_residual: float
    """Largest |ln(rho_fit) - ln(rho_us76)| over the fitted band. exp() of this is the
    worst-case density ratio, so 0.4 means the fit is off by up to ~50% somewhere."""
    rms_log_residual: float


def fit_exponential_to_us76(
    z_lo_m: float = 0.0,
    z_hi_m: float = 100_000.0,
    n_samples: int = 401,
    temperature_k: float = 250.0,
) -> ExponentialFit:
    """Least-squares fit of `ln rho = ln rho_0 - y/H` to USSA-76 over a band.

    The fit is in LOG density, which is the right space: it weights every decade
    equally, and a linear-space fit would be dominated entirely by the bottom 10 km.

    The returned `rho_0` is the fit's intercept extrapolated to y = 0 and is generally
    NOT 1.225 kg m^-3 - it is whatever sea-level density makes a single exponential
    best represent the chosen band. Which band is chosen therefore decides which
    exponential is tested; it does not decide whether the test is valid, because the
    same exponential is given to both the integrator and the closed form.
    """
    if z_hi_m <= z_lo_m:
        raise ValueError(f"empty band [{z_lo_m}, {z_hi_m}]")
    atm = USStandardAtmosphere1976(warn_above_86km=False)
    z = np.linspace(float(z_lo_m), float(z_hi_m), int(n_samples))
    log_rho = np.log(np.array([atm.state(float(zi)).density_kg_m3 for zi in z]))
    slope, intercept = np.polyfit(z, log_rho, 1)
    if slope >= 0.0:
        raise ValueError("fitted density increases with altitude; check the band")
    residual = log_rho - (slope * z + intercept)
    return ExponentialFit(
        atmosphere=ExponentialAtmosphere(
            surface_density_kg_m3=float(np.exp(intercept)),
            scale_height_m=float(-1.0 / slope),
            temperature_k=temperature_k,
        ),
        band_m=(float(z_lo_m), float(z_hi_m)),
        max_abs_log_residual=float(np.max(np.abs(residual))),
        rms_log_residual=float(np.sqrt(np.mean(residual**2))),
    )
