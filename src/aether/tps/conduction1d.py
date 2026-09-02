"""Transient 1-D multilayer heat conduction through a thermal protection system.

Conceptual anchor
-----------------
This module is the reason the project exists. The heating correlation tells you what
lands on the outside; conduction tells you what arrives at the *bondline*, which is the
glue plane where the heat shield meets the structure and where the vehicle actually
fails. The two are separated by a diffusion process with its own clock:

    tau_diffusion ~ L^2 / alpha,    alpha = k / (rho * cp)

For a 50 mm low-conductivity shield (alpha ~ 2e-7 m^2/s) that timescale is on the order
of 10^4 s - far longer than a 400 s entry. The shield is therefore never in equilibrium
during entry. It is a low-pass filter on the heat pulse: it flattens spikes and passes
the integral. That is exactly why a *lower* peak flux, sustained longer, can deliver a
*higher* bondline temperature. Burn versus bake.

Governing equation
------------------
    rho * cp * dT/dt = d/dx ( k dT/dx )

discretised with a cell-centred finite-volume scheme (conservative by construction) and
integrated with backward Euler (unconditionally stable, so the timestep is chosen for
accuracy rather than survival).

Boundary conditions
-------------------
Outer surface : q_net(t) = q_conv(t) - eps * sigma * (T_s^4 - T_inf^4)
                Re-radiation is the dominant cooling mechanism at these temperatures and
                is strongly nonlinear; it is resolved by fixed-point iteration each step.
Inner surface : adiabatic (zero flux). This is the CONSERVATIVE choice - it lets no heat
                escape at the back and therefore over-predicts bondline temperature.
                Stated, not hidden. See ASSUMPTIONS.md A-TPS-3.

Explicitly not modelled: ablation/pyrolysis, in-depth radiation, contact resistance
between layers, orthotropic conductivity, mass loss, shape change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.linalg import solve_banded
from scipy.special import erfc

from ..utils.constants import SIGMA_SB


@dataclass(frozen=True)
class Layer:
    """One homogeneous material layer of the stack.

    Properties are constant with temperature at Fidelity 0. Temperature-dependent
    properties are a documented later refinement, not an omission.
    """

    name: str
    thickness_m: float
    conductivity_w_mk: float
    density_kg_m3: float
    specific_heat_j_kgk: float
    n_cells: int = 40

    def __post_init__(self) -> None:
        positive = ("thickness_m", "conductivity_w_mk", "density_kg_m3",
                    "specific_heat_j_kgk")
        for fieldname in positive:
            if getattr(self, fieldname) <= 0.0:
                raise ValueError(f"Layer {self.name}: {fieldname} must be positive")
        if self.n_cells < 2:
            raise ValueError(f"Layer {self.name}: need at least 2 cells")

    @property
    def thermal_diffusivity_m2_s(self) -> float:
        """alpha = k / (rho cp) [m^2 s^-1]. Sets how fast a thermal front travels."""
        return self.conductivity_w_mk / (self.density_kg_m3 * self.specific_heat_j_kgk)


@dataclass
class TPSStack:
    """An ordered stack of layers, outer surface first.

    Parameters
    ----------
    bondline_after_layer:
        Index of the last layer counted as thermal protection. The bondline is the
        interface immediately behind it. Defaults to the second-to-last layer, i.e. the
        stack is [...TPS..., structure].
    emissivity:
        Surface emissivity for re-radiation [-].
    """

    layers: list[Layer]
    emissivity: float = 0.85
    bondline_after_layer: int | None = None
    t_initial_k: float = 300.0
    t_radiation_sink_k: float = 4.0
    """Effective radiation sink temperature [K]. Near-vacuum/deep-space background."""

    _x_faces: np.ndarray = field(init=False, repr=False)
    _x_centres: np.ndarray = field(init=False, repr=False)
    _dx: np.ndarray = field(init=False, repr=False)
    _k: np.ndarray = field(init=False, repr=False)
    _rhocp: np.ndarray = field(init=False, repr=False)
    _bond_index: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.layers:
            raise ValueError("stack must contain at least one layer")
        if not 0.0 <= self.emissivity <= 1.0:
            raise ValueError("emissivity must be in [0, 1]")

        dx_list, k_list, rhocp_list, faces = [], [], [], [0.0]
        x = 0.0
        for layer in self.layers:
            dx = layer.thickness_m / layer.n_cells
            for _ in range(layer.n_cells):
                dx_list.append(dx)
                k_list.append(layer.conductivity_w_mk)
                rhocp_list.append(layer.density_kg_m3 * layer.specific_heat_j_kgk)
                x += dx
                faces.append(x)
        self._dx = np.array(dx_list)
        self._k = np.array(k_list)
        self._rhocp = np.array(rhocp_list)
        self._x_faces = np.array(faces)
        self._x_centres = 0.5 * (self._x_faces[:-1] + self._x_faces[1:])

        idx = self.bondline_after_layer
        if idx is None:
            idx = max(0, len(self.layers) - 2)
        if not 0 <= idx < len(self.layers):
            raise ValueError("bondline_after_layer out of range")
        # first cell of the layer behind the bondline
        self._bond_index = sum(layer.n_cells for layer in self.layers[: idx + 1])
        self._bond_index = min(self._bond_index, len(self._dx) - 1)

    @property
    def total_thickness_m(self) -> float:
        return float(self._x_faces[-1])

    @property
    def bondline_depth_m(self) -> float:
        return float(self._x_centres[self._bond_index])

    @property
    def cell_centres_m(self) -> np.ndarray:
        return self._x_centres.copy()

    def _conductances(self) -> np.ndarray:
        """Interface conductances C_{i+1/2} [W m^-2 K^-1], harmonic (series) mean.

        Harmonic averaging is required, not cosmetic: an arithmetic mean across a
        low-k / high-k interface leaks heat that physically cannot cross.
        """
        dx, k = self._dx, self._k
        return 1.0 / (dx[:-1] / (2.0 * k[:-1]) + dx[1:] / (2.0 * k[1:]))


@dataclass
class TPSResult:
    """Time histories from a TPS solve."""

    time_s: np.ndarray
    depth_m: np.ndarray
    temperature_k: np.ndarray
    """Shape (n_time, n_cells). T[j, i] is cell i at time j."""
    surface_temperature_k: np.ndarray
    bondline_temperature_k: np.ndarray
    absorbed_flux_w_m2: np.ndarray
    """Net flux actually entering the surface after re-radiation."""
    reradiated_flux_w_m2: np.ndarray
    energy_balance_residual: float
    """Relative closure error of the global energy balance [-]. Should be << 1e-3."""
    bond_index: int

    @property
    def peak_surface_temperature_k(self) -> float:
        return float(np.max(self.surface_temperature_k))

    @property
    def peak_bondline_temperature_k(self) -> float:
        return float(np.max(self.bondline_temperature_k))

    def bondline_exposure(self, t_ref_k: float) -> float:
        """M4 = int max(0, T_bond - T_ref) dt  [K s].

        A dose, not a peak. Two designs can share a peak bondline temperature and differ
        by an order of magnitude in how long they sat near it.
        """
        excess = np.maximum(0.0, self.bondline_temperature_k - t_ref_k)
        return float(np.trapezoid(excess, self.time_s))

    def penetration_depth(self, t_threshold_k: float) -> float:
        """M5 = deepest point that ever exceeded `t_threshold_k` [m].

        Returns 0.0 if the threshold was never exceeded anywhere.
        """
        ever_hot = np.max(self.temperature_k, axis=0) > t_threshold_k
        if not np.any(ever_hot):
            return 0.0
        return float(self.depth_m[np.max(np.flatnonzero(ever_hot))])


def solve_tps(
    stack: TPSStack,
    time_s: np.ndarray,
    heat_flux_w_m2: np.ndarray,
    *,
    max_surface_iterations: int = 30,
    surface_tolerance_k: float = 1e-6,
) -> TPSResult:
    """Integrate the 1-D stack under a prescribed external convective flux history.

    Parameters
    ----------
    time_s, heat_flux_w_m2:
        The incident convective flux history, e.g. from `heating.heat_flux_history`.
        Must be the same length and monotonically increasing in time.

    Returns
    -------
    TPSResult, including a global energy-balance residual that the caller should check.
    """
    t = np.asarray(time_s, dtype=float)
    q_in = np.asarray(heat_flux_w_m2, dtype=float)
    if t.shape != q_in.shape:
        raise ValueError("time and heat-flux arrays must have the same shape")
    if np.any(np.diff(t) <= 0.0):
        raise ValueError("time array must be strictly increasing")

    n = len(stack._dx)
    dx, k, rhocp = stack._dx, stack._k, stack._rhocp
    cond = stack._conductances()
    eps_sigma = stack.emissivity * SIGMA_SB
    t_sink4 = stack.t_radiation_sink_k**4

    temp = np.full(n, stack.t_initial_k)
    history = np.empty((len(t), n))
    history[0] = temp
    surf = np.empty(len(t))
    bond = np.empty(len(t))
    absorbed = np.empty(len(t))
    reradiated = np.empty(len(t))

    r_half = dx[0] / (2.0 * k[0])
    """Conductive resistance between the wall and the first cell centre [K m^2 W^-1]."""

    def surface_temperature(cell0: float, q_net: float) -> float:
        """Wall temperature extrapolated from the first cell centre."""
        return cell0 + q_net * r_half

    surf[0] = temp[0]
    bond[0] = temp[stack._bond_index]
    absorbed[0] = 0.0
    reradiated[0] = eps_sigma * (surf[0] ** 4 - t_sink4)

    energy_in = 0.0
    energy_out = 0.0

    for j in range(1, len(t)):
        dt = t[j] - t[j - 1]
        q_conv = float(q_in[j])
        cap = rhocp * dx / dt

        # ---- nonlinear radiating surface --------------------------------------------
        # q_net = q_conv - eps*sigma*(T_s^4 - T_sink^4),   T_s = T_0 + q_net * r_half
        #
        # A raw fixed-point sweep on T^4 diverges at entry heat fluxes. Instead
        # NEWTON-LINEARISE the radiation law about the current surface estimate,
        #
        #     q_rad(T_s) ~ q_rad(T_s*) + h_rad * (T_s - T_s*),   h_rad = 4 eps sigma T_s*^3
        #
        # which makes the surface flux affine in the unknown T_0,
        #
        #     q_net = a - b * T_0
        #
        # so it folds straight into the tridiagonal system and is solved IMPLICITLY.
        # h_rad is a radiative heat-transfer coefficient; the scheme is unconditionally
        # stable because b >= 0 strengthens the diagonal.
        t_surf = surface_temperature(temp[0], max(q_conv, 0.0))
        new = temp
        q_net = q_conv

        for _ in range(max_surface_iterations):
            h_rad = 4.0 * eps_sigma * t_surf**3
            a_num = q_conv - eps_sigma * (t_surf**4 - t_sink4) + h_rad * t_surf
            denom = 1.0 + h_rad * r_half
            a = a_num / denom
            b = h_rad / denom

            lower = np.zeros(n)
            diag = cap.copy()
            upper = np.zeros(n)
            rhs = cap * temp

            diag[:-1] += cond
            diag[1:] += cond
            upper[1:] = -cond
            lower[:-1] = -cond

            diag[0] += b        # implicit radiative sink
            rhs[0] += a         # net absorbed flux; back face stays adiabatic

            ab = np.zeros((3, n))
            ab[0, 1:] = upper[1:]
            ab[1, :] = diag
            ab[2, :-1] = lower[:-1]
            new = solve_banded((1, 1), ab, rhs)

            q_net = a - b * new[0]
            t_surf_new = surface_temperature(new[0], q_net)
            converged = abs(t_surf_new - t_surf) < surface_tolerance_k
            t_surf = t_surf_new
            if converged:
                break

        temp = new
        history[j] = temp
        surf[j] = t_surf
        bond[j] = temp[stack._bond_index]
        absorbed[j] = q_net
        reradiated[j] = q_conv - q_net

        energy_in += q_conv * dt
        energy_out += (q_conv - q_net) * dt

    stored = float(np.sum(rhocp * dx * (temp - stack.t_initial_k)))
    denom = max(energy_in, 1e-12)
    residual = abs(energy_in - energy_out - stored) / denom

    return TPSResult(
        time_s=t, depth_m=stack.cell_centres_m, temperature_k=history,
        surface_temperature_k=surf, bondline_temperature_k=bond,
        absorbed_flux_w_m2=absorbed, reradiated_flux_w_m2=reradiated,
        energy_balance_residual=residual, bond_index=stack._bond_index,
    )


def semi_infinite_constant_flux(
    x_m, time_s, q_w_m2: float, k_w_mk: float, alpha_m2_s: float, t_initial_k: float = 0.0
):
    """Analytical benchmark: semi-infinite solid, constant surface flux from t=0.

        T(x,t) - T0 = (2 q / k) sqrt(alpha t / pi) exp(-x^2 / (4 alpha t))
                      - (q x / k) erfc( x / (2 sqrt(alpha t)) )

    Carslaw & Jaeger, *Conduction of Heat in Solids*, 2nd ed., section 2.9.
    Used by tests/test_tps.py to verify the numerical solver, not by the physics model.
    """
    x = np.asarray(x_m, dtype=float)
    t = np.asarray(time_s, dtype=float)
    at = alpha_m2_s * t
    with np.errstate(divide="ignore", invalid="ignore"):
        term1 = 2.0 * q_w_m2 / k_w_mk * np.sqrt(at / np.pi) * np.exp(-(x**2) / (4.0 * at))
        term2 = q_w_m2 * x / k_w_mk * erfc(x / (2.0 * np.sqrt(at)))
    return t_initial_k + np.where(t > 0.0, term1 - term2, 0.0)
