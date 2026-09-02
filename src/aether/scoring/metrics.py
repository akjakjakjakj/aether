"""Canonical performance metrics. Every candidate design is reduced to one of these.

The metric set exists to keep the burn-vs-bake question honest. M1 (peak flux) is what
a conventional design process minimises; M3/M4/M5 are what actually threaten the
structure. Reporting only one of them is the error under investigation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class PerformanceVector:
    """Y - the machine-readable outcome of one design evaluation. SI units."""

    peak_heat_flux_w_m2: float          # M1
    integrated_external_heat_j_m2: float  # M2
    peak_surface_temperature_k: float
    peak_bondline_temperature_k: float  # M3
    bondline_exposure_metric_k_s: float  # M4
    thermal_penetration_depth_m: float  # M5
    max_g: float
    max_dynamic_pressure_pa: float
    entry_duration_s: float
    time_of_peak_heating_s: float
    energy_balance_residual: float
    feasible: bool
    constraint_margins: dict[str, float]
    """Normalised margin per constraint: (limit - actual)/limit. Negative == violated."""
    termination: str
    status: str
    """'OK', or a short reason the evaluation should not be trusted."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_metrics(
    trajectory,
    heat_flux_w_m2: np.ndarray,
    tps_result,
    *,
    limits: dict[str, float | None],
    t_bondline_reference_k: float,
    t_penetration_threshold_k: float,
) -> PerformanceVector:
    """Reduce one coupled evaluation to the canonical performance vector.

    `limits` may contain None values for constraints that have not yet been sourced.
    A None limit is SKIPPED, never silently treated as satisfied - an unsourced limit is
    an open question, not a pass.
    """
    q = np.asarray(heat_flux_w_m2, dtype=float)
    t = trajectory.time_s

    peak_q = float(np.max(q))
    t_peak = float(t[int(np.argmax(q))])
    q_total = float(np.trapezoid(q, t))

    margins: dict[str, float] = {}
    feasible = True

    def check(name: str, actual: float, limit: float | None) -> None:
        nonlocal feasible
        if limit is None:
            return
        margins[name] = (limit - actual) / limit
        if actual > limit:
            feasible = False

    check("max_g", trajectory.max_g, limits.get("max_g"))
    check("max_dynamic_pressure_pa", trajectory.max_dynamic_pressure_pa,
          limits.get("max_dynamic_pressure_pa"))
    check("peak_bondline_temperature_k", tps_result.peak_bondline_temperature_k,
          limits.get("t_bondline_allowable_k"))
    check("peak_surface_temperature_k", tps_result.peak_surface_temperature_k,
          limits.get("t_surface_allowable_k"))

    status = "OK"
    if trajectory.termination not in ("terminal_altitude",):
        status = f"trajectory terminated as {trajectory.termination}"
        feasible = False
    if tps_result.energy_balance_residual > 1e-3:
        status = f"TPS energy balance residual {tps_result.energy_balance_residual:.2e} > 1e-3"
        feasible = False

    return PerformanceVector(
        peak_heat_flux_w_m2=peak_q,
        integrated_external_heat_j_m2=q_total,
        peak_surface_temperature_k=tps_result.peak_surface_temperature_k,
        peak_bondline_temperature_k=tps_result.peak_bondline_temperature_k,
        bondline_exposure_metric_k_s=tps_result.bondline_exposure(t_bondline_reference_k),
        thermal_penetration_depth_m=tps_result.penetration_depth(t_penetration_threshold_k),
        max_g=trajectory.max_g,
        max_dynamic_pressure_pa=trajectory.max_dynamic_pressure_pa,
        entry_duration_s=trajectory.duration_s,
        time_of_peak_heating_s=t_peak,
        energy_balance_residual=tps_result.energy_balance_residual,
        feasible=feasible,
        constraint_margins=margins,
        termination=trajectory.termination,
        status=status,
    )
