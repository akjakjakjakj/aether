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
Outer surface : q_net(t) = q_applied(t)
                           - eps * sigma * (T_s^4 - T_sink^4)      re-radiation
                           - h_front * (T_s - T_ambient)           optional convection
                Re-radiation is strongly nonlinear; it is Newton-linearised and solved
                implicitly each step (see NR-01 in docs/negative_results.md).
Inner surface : adiabatic by DEFAULT (zero flux). This is the CONSERVATIVE choice for
                the entry problem - it lets no heat escape at the back and therefore
                over-predicts bondline temperature. Stated, not hidden: ASSUMPTIONS.md
                A-TPS-3. Optionally a convective + radiative loss face (see below).

Optional boundary extensions (added 2026-09-20 for the M8 thermal-coupon experiment)
------------------------------------------------------------------------------------
The entry problem happens in near-vacuum with a structure behind the TPS, so an
adiabatic back face and a purely radiating front face are the right defaults. A bench
coupon sits in room air, loses heat from BOTH faces, and is heated through a physical
contact interface whose resistance is not negligible. Calibrating the model against such
a coupon is impossible without those terms - the fit would absorb the unmodelled losses
into an apparent conductivity and report a wrong number. The following are therefore
available and all DEFAULT TO ZERO, so every pre-existing result is bit-identical:

    h_front_w_m2k                  front-face convective loss coefficient
    h_back_w_m2k                   back-face convective loss coefficient
    back_emissivity                back-face emissivity for re-radiation
    t_ambient_k                    ambient air temperature for the convective terms
    front_contact_resistance_m2k_w series resistance between the plane where the flux is
                                   applied (a thin film heater, taken as having
                                   negligible thermal mass) and the first cell centre

With a non-zero contact resistance, `surface_temperature_k` is the temperature of the
FLUX-APPLICATION PLANE - i.e. the heater film - not the coupon's own front face. Surface
losses are evaluated there. That is exact for a thin bonded film heater and an
approximation for anything with appreciable heat capacity of its own; the coupon
protocol says so and tells the student which heater types make it true.

Explicitly not modelled: ablation/pyrolysis, in-depth radiation, contact resistance
*between* layers, orthotropic conductivity, mass loss, shape change, heater heat
capacity.
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

    # ---- optional bench-coupon boundary terms; all zero => original entry model -------
    h_front_w_m2k: float = 0.0
    """Convective loss coefficient at the heated face [W m^-2 K^-1]. 0 = vacuum."""
    h_back_w_m2k: float = 0.0
    """Convective loss coefficient at the back face [W m^-2 K^-1]. 0 = adiabatic."""
    back_emissivity: float = 0.0
    """Back-face emissivity for re-radiation [-]. 0 = no back-face radiation."""
    t_ambient_k: float = 300.0
    """Ambient temperature the convective terms exchange with [K]."""
    front_contact_resistance_m2k_w: float = 0.0
    """Series thermal resistance between the flux-application plane and the solid
    [K m^2 W^-1]. Models a heater-to-coupon interface. 0 = perfect contact."""

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
        if not 0.0 <= self.back_emissivity <= 1.0:
            raise ValueError("back_emissivity must be in [0, 1]")
        for name in ("h_front_w_m2k", "h_back_w_m2k", "front_contact_resistance_m2k_w"):
            if getattr(self, name) < 0.0:
                raise ValueError(f"{name} must be non-negative")
        if self.t_ambient_k <= 0.0:
            raise ValueError("t_ambient_k must be positive (it is an absolute temperature)")

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
    """Cell-centre depths from the heated surface [m]."""
    cell_width_m: np.ndarray
    """Finite-volume cell widths [m]. Carried so that a depth integral can be taken as
    sum(f_i * dx_i) - the cell-averaged quantity's exact quadrature - rather than by
    trapezoid over cell centres, which silently drops half a cell at each end."""
    temperature_k: np.ndarray
    """Shape (n_time, n_cells). T[j, i] is cell i at time j."""
    surface_temperature_k: np.ndarray
    bondline_temperature_k: np.ndarray
    absorbed_flux_w_m2: np.ndarray
    """Net flux actually entering the solid at the front face, after surface losses."""
    surface_loss_flux_w_m2: np.ndarray
    """Front-face loss: re-radiation plus any convective loss. Equals the re-radiated
    flux alone when `h_front_w_m2k` is zero, which is the entry configuration."""
    back_loss_flux_w_m2: np.ndarray
    """Back-face loss flux. Identically zero for an adiabatic back face."""
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
    eps_sigma_back = stack.back_emissivity * SIGMA_SB
    h_front = stack.h_front_w_m2k
    h_back = stack.h_back_w_m2k
    t_amb = stack.t_ambient_k
    back_active = (h_back > 0.0) or (eps_sigma_back > 0.0)

    temp = np.full(n, stack.t_initial_k)
    history = np.empty((len(t), n))
    history[0] = temp
    surf = np.empty(len(t))
    bond = np.empty(len(t))
    absorbed = np.empty(len(t))
    surface_loss = np.empty(len(t))
    back_loss = np.zeros(len(t))

    r_half = dx[0] / (2.0 * k[0]) + stack.front_contact_resistance_m2k_w
    """Resistance between the flux-application plane and the first cell centre
    [K m^2 W^-1]: half a cell of conduction, plus any heater contact resistance."""
    r_half_back = dx[-1] / (2.0 * k[-1])
    """Resistance between the last cell centre and the back face [K m^2 W^-1]."""

    def surface_temperature(cell0: float, q_net: float) -> float:
        """Flux-application-plane temperature extrapolated from the first cell centre."""
        return cell0 + q_net * r_half

    def back_temperature(cell_last: float, q_out: float) -> float:
        """Back-face temperature extrapolated from the last cell centre."""
        return cell_last - q_out * r_half_back

    surf[0] = temp[0]
    bond[0] = temp[stack._bond_index]
    absorbed[0] = 0.0
    surface_loss[0] = (eps_sigma * (surf[0] ** 4 - t_sink4)
                       + h_front * (surf[0] - t_amb))

    energy_in = 0.0
    energy_out = 0.0
    t_back = temp[-1]

    for j in range(1, len(t)):
        dt = t[j] - t[j - 1]
        q_conv = float(q_in[j])
        cap = rhocp * dx / dt

        # ---- nonlinear radiating surface --------------------------------------------
        # q_net = q_conv - eps*sigma*(T_s^4 - T_sink^4) - h_front*(T_s - T_amb),
        #     with T_s = T_0 + q_net * r_half
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
        # stable because b >= 0 strengthens the diagonal. The convective term is already
        # linear in T_s and joins h_rad without further approximation.
        t_surf = surface_temperature(temp[0], max(q_conv, 0.0))
        new = temp
        q_net = q_conv
        q_back = 0.0

        for _ in range(max_surface_iterations):
            h_rad = 4.0 * eps_sigma * t_surf**3
            h_tot = h_rad + h_front
            a_num = (q_conv - eps_sigma * (t_surf**4 - t_sink4) + h_rad * t_surf
                     + h_front * t_amb)
            denom = 1.0 + h_tot * r_half
            a = a_num / denom
            b = h_tot / denom

            # ---- back face -----------------------------------------------------------
            # Adiabatic unless a loss coefficient or a back emissivity was supplied.
            # Same Newton linearisation, about the current back-face estimate:
            #     q_out = g * T_{n-1} - c
            if back_active:
                h_rad_b = 4.0 * eps_sigma_back * t_back**3
                h_tot_b = h_rad_b + h_back
                c_num = (h_back * t_amb + h_rad_b * t_back
                         - eps_sigma_back * (t_back**4 - t_sink4))
                denom_b = 1.0 + h_tot_b * r_half_back
                g = h_tot_b / denom_b
                c = c_num / denom_b
            else:
                g = c = 0.0

            lower = np.zeros(n)
            diag = cap.copy()
            upper = np.zeros(n)
            rhs = cap * temp

            diag[:-1] += cond
            diag[1:] += cond
            upper[1:] = -cond
            lower[:-1] = -cond

            diag[0] += b        # implicit front-face radiative + convective sink
            rhs[0] += a         # net absorbed flux
            diag[-1] += g       # implicit back-face sink; g = 0 => adiabatic
            rhs[-1] += c

            ab = np.zeros((3, n))
            ab[0, 1:] = upper[1:]
            ab[1, :] = diag
            ab[2, :-1] = lower[:-1]
            new = solve_banded((1, 1), ab, rhs)

            q_net = a - b * new[0]
            q_back = g * new[-1] - c
            t_surf_new = surface_temperature(new[0], q_net)
            t_back_new = back_temperature(new[-1], q_back)
            converged = (abs(t_surf_new - t_surf) < surface_tolerance_k
                         and abs(t_back_new - t_back) < surface_tolerance_k)
            t_surf = t_surf_new
            t_back = t_back_new
            if converged:
                break

        temp = new
        history[j] = temp
        surf[j] = t_surf
        bond[j] = temp[stack._bond_index]
        absorbed[j] = q_net
        surface_loss[j] = q_conv - q_net
        back_loss[j] = q_back

        energy_in += q_conv * dt
        energy_out += (q_conv - q_net + q_back) * dt

    stored = float(np.sum(rhocp * dx * (temp - stack.t_initial_k)))
    denom = max(energy_in, abs(energy_out), 1e-12)
    residual = abs(energy_in - energy_out - stored) / denom

    return TPSResult(
        time_s=t, depth_m=stack.cell_centres_m, cell_width_m=dx.copy(),
        temperature_k=history,
        surface_temperature_k=surf, bondline_temperature_k=bond,
        absorbed_flux_w_m2=absorbed, surface_loss_flux_w_m2=surface_loss,
        back_loss_flux_w_m2=back_loss,
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
