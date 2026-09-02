"""Point-mass 3-DOF planar atmospheric entry.

Conceptual anchor
-----------------
Entry is an energy-disposal problem. A vehicle arrives with kinetic energy of order
0.5 * V^2 ~ 27 MJ/kg at 7.4 km/s, and essentially all of it has to leave as heat into
the air. The trajectory does not decide *how much* energy is dumped - orbital mechanics
already did - it decides *how fast*. Steep entry dumps it in a short, violent window;
shallow entry spreads it over minutes. That single choice is what makes peak heating and
soak heating pull in opposite directions, which is the whole subject of this project.

Model
-----
Planar (non-lifting-turn) motion of a point mass over a spherical, non-rotating Earth:

    r     = R_E + h
    g(r)  = mu / r^2
    D     = 0.5 rho V^2 C_D A
    L     = 0.5 rho V^2 C_L A

    dh/dt     = V sin(gamma)
    dV/dt     = -D/m - g sin(gamma)
    dgamma/dt = (1/V) [ L cos(sigma)/m - g cos(gamma) + V^2 cos(gamma)/r ]
    ds/dt     = V cos(gamma) R_E / r

gamma is the flight-path angle measured POSITIVE UPWARD, so an entry has gamma < 0.
sigma is bank angle (0 for the ballistic baseline).

Deliberately excluded: Earth rotation, winds, 6-DOF attitude dynamics, aeroelasticity,
mass loss from ablation. See ASSUMPTIONS.md A-TRAJ-1..4.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from ..atmosphere import USStandardAtmosphere1976
from ..utils.constants import EARTH


@dataclass(frozen=True)
class EntryState:
    """Initial condition at the entry interface."""

    altitude_m: float
    velocity_m_s: float
    flight_path_angle_rad: float
    """Positive upward. An entry trajectory has a NEGATIVE value."""
    downrange_m: float = 0.0


@dataclass(frozen=True)
class VehicleAero:
    """Aerodynamic and mass properties held constant over the entry.

    Fidelity 0 uses constant coefficients. Fidelity 1 replaces `cd` with a response
    surface Cd(M, alpha, geometry); the interface below is deliberately shaped so that
    substitution does not change any caller.
    """

    mass_kg: float
    reference_area_m2: float
    cd: float
    cl: float = 0.0
    bank_angle_rad: float = 0.0

    @property
    def ballistic_coefficient(self) -> float:
        """beta = m / (C_D A)  [kg m^-2].

        The single number that most controls how deep in the atmosphere a vehicle
        decelerates. High beta -> penetrates deeper, decelerates lower and harder.
        """
        return self.mass_kg / (self.cd * self.reference_area_m2)


@dataclass
class TrajectoryResult:
    """Time histories from one entry integration. All arrays share `time_s`."""

    time_s: np.ndarray
    altitude_m: np.ndarray
    velocity_m_s: np.ndarray
    flight_path_angle_rad: np.ndarray
    downrange_m: np.ndarray
    density_kg_m3: np.ndarray
    mach: np.ndarray
    dynamic_pressure_pa: np.ndarray
    deceleration_g: np.ndarray
    termination: str
    """Why integration stopped: 'terminal_altitude', 'ground', 'skip_out', 'time_limit'."""
    success: bool
    message: str = ""

    @property
    def max_g(self) -> float:
        return float(np.max(self.deceleration_g))

    @property
    def max_dynamic_pressure_pa(self) -> float:
        return float(np.max(self.dynamic_pressure_pa))

    @property
    def duration_s(self) -> float:
        return float(self.time_s[-1] - self.time_s[0])


def integrate_entry(
    initial: EntryState,
    vehicle: VehicleAero,
    *,
    terminal_altitude_m: float = 20_000.0,
    max_time_s: float = 3_000.0,
    rtol: float = 1e-9,
    atol: float = 1e-9,
    max_step_s: float = 1.0,
    atmosphere: USStandardAtmosphere1976 | None = None,
    cd_model: Callable[[float, float], float] | None = None,
) -> TrajectoryResult:
    """Integrate the entry from `initial` down to `terminal_altitude_m`.

    Parameters
    ----------
    terminal_altitude_m:
        Integration stops here. The default 20 km is where the aerothermal problem is
        effectively over for a blunt entry body and where parachute/descent phases -
        explicitly out of scope - would take over.
    cd_model:
        Optional callable (mach, altitude_m) -> Cd, used in place of the constant
        `vehicle.cd`. This is the hook for the Fidelity-1 aerodynamic response surface.

    Returns
    -------
    TrajectoryResult with dense-sampled histories.
    """
    atm = atmosphere or USStandardAtmosphere1976(warn_above_86km=False)
    mu, r_e = EARTH.mu, EARTH.radius

    def cd_of(mach: float, altitude: float) -> float:
        return vehicle.cd if cd_model is None else float(cd_model(mach, altitude))

    def rhs(t: float, y: np.ndarray) -> list[float]:
        h, v, gam, _s = y
        h = max(h, -4_999.0)
        st = atm.state(h)
        rho = st.density_kg_m3
        r = r_e + h
        g = mu / (r * r)
        q_dyn = 0.5 * rho * v * v
        mach = v / st.speed_of_sound_m_s
        drag = q_dyn * cd_of(mach, h) * vehicle.reference_area_m2
        lift = q_dyn * vehicle.cl * vehicle.reference_area_m2

        dh = v * np.sin(gam)
        dv = -drag / vehicle.mass_kg - g * np.sin(gam)
        dgam = (
            lift * np.cos(vehicle.bank_angle_rad) / (vehicle.mass_kg * v)
            - (g / v) * np.cos(gam)
            + (v / r) * np.cos(gam)
        )
        ds = v * np.cos(gam) * r_e / r
        return [dh, dv, dgam, ds]

    def ev_terminal(t, y):
        return y[0] - terminal_altitude_m
    ev_terminal.terminal = True
    ev_terminal.direction = -1

    def ev_ground(t, y):
        return y[0]
    ev_ground.terminal = True
    ev_ground.direction = -1

    def ev_skipout(t, y):
        # velocity still above local circular speed while climbing -> skipping out
        return y[0] - 200_000.0
    ev_skipout.terminal = True
    ev_skipout.direction = +1

    y0 = [
        initial.altitude_m,
        initial.velocity_m_s,
        initial.flight_path_angle_rad,
        initial.downrange_m,
    ]

    sol = solve_ivp(
        rhs, (0.0, max_time_s), y0,
        method="LSODA", rtol=rtol, atol=atol, max_step=max_step_s,
        events=[ev_terminal, ev_ground, ev_skipout], dense_output=True,
    )

    if sol.t_events[0].size:
        termination = "terminal_altitude"
    elif sol.t_events[1].size:
        termination = "ground"
    elif sol.t_events[2].size:
        termination = "skip_out"
    else:
        termination = "time_limit"

    t = sol.t
    h, v, gam, s = sol.y

    rho = np.array([atm.state(float(z)).density_kg_m3 for z in h])
    a_snd = np.array([atm.state(float(z)).speed_of_sound_m_s for z in h])
    q_dyn = 0.5 * rho * v**2
    cds = np.array([
        cd_of(float(vi / ai), float(zi))
        for vi, ai, zi in zip(v, a_snd, h, strict=True)
    ])
    drag = q_dyn * cds * vehicle.reference_area_m2
    decel_g = drag / (vehicle.mass_kg * EARTH.g0)

    return TrajectoryResult(
        time_s=t, altitude_m=h, velocity_m_s=v, flight_path_angle_rad=gam,
        downrange_m=s, density_kg_m3=rho, mach=v / a_snd,
        dynamic_pressure_pa=q_dyn, deceleration_g=decel_g,
        termination=termination, success=bool(sol.success), message=str(sol.message),
    )
