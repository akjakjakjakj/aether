"""Thermal Penetration Index (TPI) - a candidate cumulative in-depth exposure metric.

Conceptual anchor
-----------------
Peak bondline temperature answers "how hot did the worst plane get, at its worst
moment". It is a single number pulled from a single point in a two-dimensional field
T(x, t). It says nothing about how much of the stack got hot, or for how long. Two
designs can share a bondline peak and differ by an order of magnitude in how long the
inner half of the shield sat above the adhesive's service temperature.

TPI is the obvious thing to try instead: integrate the temperature *exceedance* above a
reference temperature over both depth and time, with a depth weighting that can be
pointed at whatever plane actually fails.

    TPI = INT_0^t_end INT_0^L  w(x) * max( T(x,t) - T_ref , 0 )  dx dt

Units
-----
    [w] = 1 (dimensionless)      [x] = m      [t] = s      [T - T_ref] = K
    => [TPI] = K * m * s

A Kelvin-metre-second. It is not a standard engineering unit and this project does not
pretend otherwise; it is the unit that falls out of the definition. Reporting it without
its weighting family, its T_ref and its depth limit is meaningless, because all three
change the number.

What this module deliberately does NOT do
-----------------------------------------
It does not claim TPI is new, and it does not claim it is useful. Prior art for
cumulative thermal-exposure metrics is reviewed in `docs/theory/tpi.md`, and whether TPI
carries information beyond peak bondline temperature and integrated heat load is an
empirical question answered in `reports/milestones/TPI_study.md`. The answer there may
be, and is allowed to be, "no".

Configuration
-------------
`t_reference_k`, the weighting family and its parameters, and the depth limit all come
from YAML (`configs/tpi_study.yaml`). None of them is hard-coded anywhere in this file
except as the dataclass defaults that make a bare `TPIConfig(t_reference_k=...)` legal,
and every study writes all of them explicitly into its config snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

WEIGHTING_FAMILIES = ("uniform", "linear_depth", "exponential_depth", "bondline_gaussian")


@dataclass(frozen=True)
class TPIConfig:
    """Everything that has to be declared before a TPI number means anything."""

    t_reference_k: float
    """Exceedance datum [K]. Below this, a temperature contributes nothing."""

    weighting: str = "uniform"
    """One of WEIGHTING_FAMILIES. See `weight_profile` for the definitions."""

    weight_params: dict[str, float] = field(default_factory=dict)
    """Family-specific parameters, e.g. {'decay': 3.0} or {'sigma_m': 0.003}."""

    normalise_weights: bool = True
    """Rescale w so its depth-average over the integration domain is exactly 1.

    With this on, every family produces the same TPI for a spatially uniform temperature
    field, so a change in TPI between families is attributable to the *shape* of the
    field and not to the arbitrary scale of the weight function. Comparing families
    without it compares apples to a different number of apples.
    """

    depth_limit_m: float | None = None
    """Integrate only over 0 <= x <= depth_limit_m [m]. None means the whole stack.

    Spec section 44 defines TPI over TPS depth. A stack that ends in an aluminium
    structure is not all TPS, and including the structure would let a metal layer's
    thermal mass dominate a metric that is supposed to describe the insulator.
    """

    def __post_init__(self) -> None:
        if self.weighting not in WEIGHTING_FAMILIES:
            raise ValueError(
                f"unknown weighting family {self.weighting!r}; "
                f"expected one of {WEIGHTING_FAMILIES}"
            )
        if self.t_reference_k <= 0.0:
            raise ValueError("t_reference_k is an absolute temperature and must be positive")
        if self.depth_limit_m is not None and self.depth_limit_m <= 0.0:
            raise ValueError("depth_limit_m must be positive when given")
        if self.weighting == "bondline_gaussian":
            sigma = self.weight_params.get("sigma_m")
            if sigma is None or sigma <= 0.0:
                raise ValueError("bondline_gaussian requires weight_params['sigma_m'] > 0")
        if self.weighting == "exponential_depth":
            if float(self.weight_params.get("decay", 3.0)) < 0.0:
                raise ValueError("exponential_depth requires a non-negative 'decay'")

    @property
    def label(self) -> str:
        """Short human label that carries every choice that changes the number."""
        bits = [self.weighting, f"Tref={self.t_reference_k:.0f}K"]
        for key in sorted(self.weight_params):
            bits.append(f"{key}={self.weight_params[key]:g}")
        if self.depth_limit_m is not None:
            bits.append(f"x<={self.depth_limit_m * 1e3:.0f}mm")
        return " · ".join(bits)

    def to_dict(self) -> dict[str, Any]:
        return {
            "t_reference_k": self.t_reference_k,
            "weighting": self.weighting,
            "weight_params": dict(self.weight_params),
            "normalise_weights": self.normalise_weights,
            "depth_limit_m": self.depth_limit_m,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TPIConfig:
        return cls(
            t_reference_k=float(data["t_reference_k"]),
            weighting=str(data.get("weighting", "uniform")),
            weight_params={k: float(v) for k, v in (data.get("weight_params") or {}).items()},
            normalise_weights=bool(data.get("normalise_weights", True)),
            depth_limit_m=(None if data.get("depth_limit_m") is None
                           else float(data["depth_limit_m"])),
        )


def weight_profile(depth_m: np.ndarray, domain_length_m: float, config: TPIConfig) -> np.ndarray:
    """The depth weighting w(x) [-], evaluated at `depth_m`, before normalisation.

    Families, with x measured from the heated surface and L the integration domain:

    ``uniform``
        w = 1. Every millimetre of TPS counts the same. The null hypothesis of the
        weighting question.
    ``linear_depth``
        w = x / L. Zero at the surface, one at the far edge of the domain. Surface
        heating is not what TPI is trying to measure, so it is discounted smoothly.
    ``exponential_depth``
        w = exp(decay * (x/L - 1)). One at the far edge, exp(-decay) at the surface.
        ``decay`` sets how aggressively the interior is favoured; decay -> 0 recovers
        the uniform family, which makes it a genuine one-parameter generalisation.
    ``bondline_gaussian``
        w = exp(-0.5 * ((x - x_centre)/sigma)^2), centred by default on the far edge of
        the domain, i.e. the bondline plane. Requires ``sigma_m``. This is the family to
        use when the failure mode is a specific adhesive at a specific depth.
    """
    x = np.asarray(depth_m, dtype=float)
    if config.weighting == "uniform":
        return np.ones_like(x)
    if config.weighting == "linear_depth":
        return x / domain_length_m
    if config.weighting == "exponential_depth":
        decay = float(config.weight_params.get("decay", 3.0))
        return np.exp(decay * (x / domain_length_m - 1.0))
    # bondline_gaussian
    sigma = float(config.weight_params["sigma_m"])
    centre = float(config.weight_params.get("centre_m", domain_length_m))
    return np.exp(-0.5 * ((x - centre) / sigma) ** 2)


@dataclass(frozen=True)
class TPIResult:
    """One TPI evaluation and the intermediate quantities needed to argue about it."""

    tpi_k_m_s: float
    """The index itself [K m s]."""
    config: TPIConfig
    domain_length_m: float
    """Depth actually integrated over [m]."""
    n_cells_in_domain: int
    exceedance_profile_k_s: np.ndarray
    """Per-cell time-integrated exceedance INT max(T - T_ref, 0) dt [K s], UNweighted.

    This is what a residual plot needs: it shows *where* in the stack the index came
    from, which is the only way to tell an index that is measuring in-depth soak from
    one that is measuring the surface with extra steps.
    """
    depth_m: np.ndarray
    weight: np.ndarray
    """Normalised weights actually used [-], aligned with `depth_m`."""
    peak_exceedance_depth_m: float
    """Depth at which the unweighted time-integrated exceedance is largest [m]."""

    @property
    def deepest_exceeded_m(self) -> float:
        """Deepest cell in the domain that ever exceeded T_ref [m]. 0.0 if none did."""
        hot = np.flatnonzero(self.exceedance_profile_k_s > 0.0)
        return float(self.depth_m[hot[-1]]) if hot.size else 0.0


def thermal_penetration_index(tps_result, config: TPIConfig) -> TPIResult:
    """Evaluate TPI for one solved TPS response.

    Quadrature
    ----------
    In depth, ``sum_i f_i * dx_i``. The finite-volume solution stores a cell AVERAGE, so
    the midpoint rule is the matching quadrature and it covers the full domain. A
    trapezoid over cell centres would drop half a cell at each end - at the surface,
    where the field is steepest, which is exactly the wrong place to lose a term.

    In time, the trapezoid rule over the solver's own time base, which includes the
    post-entry soak-out. The soak-out matters more for TPI than for any other metric,
    because interior temperature keeps rising after the heat pulse is over.
    """
    depth = np.asarray(tps_result.depth_m, dtype=float)
    widths = np.asarray(tps_result.cell_width_m, dtype=float)
    temps = np.asarray(tps_result.temperature_k, dtype=float)
    time = np.asarray(tps_result.time_s, dtype=float)

    limit = config.depth_limit_m
    if limit is None:
        mask = np.ones_like(depth, dtype=bool)
    else:
        mask = depth <= limit
        if not np.any(mask):
            raise ValueError(
                f"depth_limit_m={limit} m excludes every cell; the shallowest cell centre "
                f"is at {depth[0]:.4g} m"
            )

    depth_in = depth[mask]
    widths_in = widths[mask]
    domain_length = float(np.sum(widths_in))

    excess = np.maximum(0.0, temps[:, mask] - config.t_reference_k)
    exceedance = np.trapezoid(excess, time, axis=0)          # [K s] per cell

    weight = weight_profile(depth_in, domain_length, config)
    if config.normalise_weights:
        mean_weight = float(np.sum(weight * widths_in) / domain_length)
        if mean_weight <= 0.0:
            raise ValueError("weight profile integrates to zero; cannot normalise")
        weight = weight / mean_weight

    tpi = float(np.sum(weight * exceedance * widths_in))

    return TPIResult(
        tpi_k_m_s=tpi,
        config=config,
        domain_length_m=domain_length,
        n_cells_in_domain=int(np.count_nonzero(mask)),
        exceedance_profile_k_s=exceedance,
        depth_m=depth_in,
        weight=weight,
        peak_exceedance_depth_m=float(depth_in[int(np.argmax(exceedance))]),
    )
