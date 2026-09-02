"""US Standard Atmosphere 1976.

Conceptual anchor
-----------------
The whole re-entry problem is driven by one number: how much air the vehicle meets per
second. Everything downstream - drag, heating, dynamic pressure - is a function of
density, and density falls off roughly exponentially with altitude. So the atmosphere
model is not a detail; a 10% density error is a ~10% drag error and a ~5% heat-flux
error (q'' ~ sqrt(rho)) at every point of the trajectory.

Implementation
--------------
0 - 86 km : the defined USSA-76 piecewise-linear temperature profile in *geopotential*
            altitude, integrated exactly (hydrostatic + ideal gas). This region is
            computed from first principles, not interpolated, so it is exact to the
            standard's own definition.

86 - 150 km : USSA-76 above 86 km is defined by a species-diffusion model with varying
            mean molar mass, which is out of scope here. This module instead
            log-interpolates a transcribed table of published USSA-76 values and sets
            `extrapolated=True`. Treat results above 86 km as LIMITED, not validated.
            See ASSUMPTIONS.md A-ATM-2.

> 150 km  : refused. The caller gets an explicit error rather than a silent number.

Units: SI throughout. Altitude arguments are GEOMETRIC altitude in metres.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

from ..utils.constants import EARTH, GAMMA_AIR, R_AIR

# --- USSA-76 defined layers, 0-86 km, in geopotential altitude -----------------------
# (base geopotential altitude [m], base temperature [K], lapse rate [K/m])
_LAYERS = (
    (0.0, 288.15, -6.5e-3),
    (11_000.0, 216.65, 0.0),
    (20_000.0, 216.65, +1.0e-3),
    (32_000.0, 228.65, +2.8e-3),
    (47_000.0, 270.65, 0.0),
    (51_000.0, 270.65, -2.8e-3),
    (71_000.0, 214.65, -2.0e-3),
    (84_852.0, 186.946, 0.0),  # 84.852 km geopotential == 86 km geometric
)
_P0 = 101_325.0
_H_MAX_GEOPOT = 84_852.0

# Base pressures at each layer boundary, integrated once at import (exact, not tabulated).
def _layer_base_pressures() -> tuple[float, ...]:
    pressures = [_P0]
    for i in range(len(_LAYERS) - 1):
        h_b, t_b, lam = _LAYERS[i]
        h_top = _LAYERS[i + 1][0]
        p_b = pressures[-1]
        if lam == 0.0:
            p = p_b * np.exp(-EARTH.g0 * (h_top - h_b) / (R_AIR * t_b))
        else:
            t_top = t_b + lam * (h_top - h_b)
            p = p_b * (t_top / t_b) ** (-EARTH.g0 / (R_AIR * lam))
        pressures.append(float(p))
    return tuple(pressures)


_P_BASE = _layer_base_pressures()

# --- Transcribed USSA-76 values above 86 km (geometric altitude) ---------------------
# SOURCE STATUS: transcribed from published USSA-76 tables; NOT yet checked against a
# primary copy of NOAA/NASA/USAF (1976). VALIDATION_MATRIX marks this LIMITED.
# columns: Z [m], T [K], rho [kg m^-3], p [Pa]
_UPPER_TABLE = np.array([
    [86_000.0, 186.87, 6.958e-06, 3.7338e-01],
    [90_000.0, 186.87, 3.416e-06, 1.8359e-01],
    [95_000.0, 188.42, 1.393e-06, 7.5966e-02],
    [100_000.0, 195.08, 5.604e-07, 3.2011e-02],
    [110_000.0, 240.00, 9.708e-08, 7.1042e-03],
    [120_000.0, 360.00, 2.222e-08, 2.5382e-03],
    [130_000.0, 469.27, 8.152e-09, 1.2505e-03],
    [150_000.0, 634.39, 2.076e-09, 4.5422e-04],
])
_Z_TABLE_MAX = 150_000.0


@dataclass(frozen=True)
class AtmosphereState:
    """Freestream state at one altitude."""

    altitude_m: float
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    speed_of_sound_m_s: float
    viscosity_pa_s: float
    extrapolated: bool
    """True if the value came from the >86 km interpolated table rather than the
    exactly-integrated USSA-76 homosphere."""


def geometric_to_geopotential(z_m: float | np.ndarray) -> float | np.ndarray:
    """Convert geometric altitude to geopotential altitude [m].

    Geopotential altitude absorbs the variation of g with height so the hydrostatic
    equation can be integrated with a constant g0.
    """
    r = EARTH.r_geopotential
    return r * z_m / (r + z_m)


def _sutherland_viscosity(t_k: float | np.ndarray) -> float | np.ndarray:
    """Dynamic viscosity of air [Pa s]. Sutherland's law, USSA-76 coefficients."""
    beta = 1.458e-6  # kg m^-1 s^-1 K^-0.5
    s = 110.4        # K
    return beta * t_k**1.5 / (t_k + s)


class USStandardAtmosphere1976:
    """Callable atmosphere model.

    Parameters
    ----------
    warn_above_86km:
        Emit a RuntimeWarning the first time the caller asks for an altitude in the
        interpolated region. Silent extrapolation is the failure mode this guards.
    """

    def __init__(self, warn_above_86km: bool = True) -> None:
        self.warn_above_86km = warn_above_86km
        self._warned = False

    # -- scalar core ------------------------------------------------------------------
    def _homosphere(self, h_geopot: float) -> tuple[float, float, float]:
        """Exact USSA-76 T, p, rho for geopotential altitude <= 84.852 km."""
        idx = 0
        for i, (h_b, _, _) in enumerate(_LAYERS):
            if h_geopot >= h_b:
                idx = i
        h_b, t_b, lam = _LAYERS[idx]
        p_b = _P_BASE[idx]
        dh = h_geopot - h_b
        if lam == 0.0:
            t = t_b
            p = p_b * np.exp(-EARTH.g0 * dh / (R_AIR * t_b))
        else:
            t = t_b + lam * dh
            p = p_b * (t / t_b) ** (-EARTH.g0 / (R_AIR * lam))
        rho = p / (R_AIR * t)
        return float(t), float(p), float(rho)

    def _upper(self, z_m: float) -> tuple[float, float, float]:
        """Log-interpolated table values for 86 km < z <= 150 km."""
        z = _UPPER_TABLE[:, 0]
        t = np.interp(z_m, z, _UPPER_TABLE[:, 1])
        # density and pressure vary over orders of magnitude -> interpolate in log space
        rho = np.exp(np.interp(z_m, z, np.log(_UPPER_TABLE[:, 2])))
        p = np.exp(np.interp(z_m, z, np.log(_UPPER_TABLE[:, 3])))
        return float(t), float(p), float(rho)

    def state(self, altitude_m: float) -> AtmosphereState:
        """Full atmospheric state at a geometric altitude [m]."""
        z = float(altitude_m)
        if z > _Z_TABLE_MAX:
            raise ValueError(
                f"altitude {z/1e3:.1f} km is above this model's declared ceiling "
                f"({_Z_TABLE_MAX/1e3:.0f} km). Refusing to extrapolate."
            )
        if z < -5_000.0:
            raise ValueError(f"altitude {z/1e3:.3f} km is below the model floor (-5 km).")

        h = geometric_to_geopotential(z)
        if h <= _H_MAX_GEOPOT:
            t, p, rho = self._homosphere(h)
            extrapolated = False
        else:
            if self.warn_above_86km and not self._warned:
                warnings.warn(
                    "atmosphere queried above 86 km: values are log-interpolated from a "
                    "transcribed USSA-76 table, status LIMITED (see ASSUMPTIONS.md A-ATM-2)",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self._warned = True
            t, p, rho = self._upper(z)
            extrapolated = True

        return AtmosphereState(
            altitude_m=z,
            temperature_k=t,
            pressure_pa=p,
            density_kg_m3=rho,
            speed_of_sound_m_s=float(np.sqrt(GAMMA_AIR * R_AIR * t)),
            viscosity_pa_s=float(_sutherland_viscosity(t)),
            extrapolated=extrapolated,
        )

    # -- vectorised convenience accessors ---------------------------------------------
    def density(self, altitude_m):
        """Density [kg m^-3]. Accepts scalar or array altitude."""
        return self._map(altitude_m, lambda s: s.density_kg_m3)

    def temperature(self, altitude_m):
        """Temperature [K]."""
        return self._map(altitude_m, lambda s: s.temperature_k)

    def pressure(self, altitude_m):
        """Pressure [Pa]."""
        return self._map(altitude_m, lambda s: s.pressure_pa)

    def speed_of_sound(self, altitude_m):
        """Speed of sound [m s^-1]."""
        return self._map(altitude_m, lambda s: s.speed_of_sound_m_s)

    def _map(self, altitude_m, getter):
        arr = np.atleast_1d(np.asarray(altitude_m, dtype=float))
        out = np.array([getter(self.state(float(z))) for z in arr])
        return float(out[0]) if np.isscalar(altitude_m) or np.ndim(altitude_m) == 0 else out
