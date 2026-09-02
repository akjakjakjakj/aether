"""Two-dimensional (trajectory x geometry) sweep - the H1 demonstration.

M1 shows that peak heat flux and bondline temperature are anti-correlated over
trajectory shape alone, and that for the fixed baseline geometry NO entry angle
satisfies both the deceleration limit and the bondline limit. That is a squeeze, not a
design: steep entries survive thermally and kill the crew, shallow entries are gentle
and cook the structure.

H1 says the squeeze is an artefact of optimising in one variable. Opening a second axis
- vehicle diameter, which sets the ballistic coefficient beta = m/(C_D A) - should
recover a feasible region, and the design a *peak-heat-only* optimiser picks from that
region should be measurably worse at the bondline than the one a *joint* optimiser picks.

This module runs the grid and extracts exactly that comparison.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..evaluate import DesignEvaluation, evaluate_design


@dataclass
class JointSweep:
    """Grid results over (flight-path angle, diameter)."""

    evaluations: list[DesignEvaluation]
    gamma_deg: np.ndarray
    diameter_m: np.ndarray
    shape: tuple[int, int]

    def field(self, getter) -> np.ndarray:
        """Reshape any per-candidate scalar onto the (gamma, diameter) grid."""
        return np.array([getter(ev) for ev in self.evaluations]).reshape(self.shape)

    @property
    def feasible_mask(self) -> np.ndarray:
        return self.field(lambda e: e.performance.feasible).astype(bool)

    def feasible_evaluations(self) -> list[DesignEvaluation]:
        return [ev for ev in self.evaluations if ev.performance.feasible]


def pareto_front(points: np.ndarray) -> np.ndarray:
    """Indices of the non-dominated rows of `points`. All objectives are MINIMISED.

    Row i is non-dominated iff no other row j is at least as good in every objective and
    strictly better in at least one. Self-comparison is harmless: `points[i] <= points[i]`
    holds everywhere but `points[i] < points[i]` holds nowhere, so a point never dominates
    itself.

    A correct front must be monotone in a 2-objective problem - if a plotted front
    zigzags, this function is wrong, not the data.
    """
    n = points.shape[0]
    keep = np.ones(n, dtype=bool)
    for i in range(n):
        dominates_i = (
            np.all(points <= points[i], axis=1) & np.any(points < points[i], axis=1)
        )
        if np.any(dominates_i):
            keep[i] = False
    return np.flatnonzero(keep)


def run_joint_sweep(
    base_config: dict[str, Any],
    gamma_deg_values: np.ndarray,
    diameter_m_values: np.ndarray,
    *,
    progress: bool = True,
) -> JointSweep:
    """Full-factorial grid over entry angle and vehicle diameter.

    Mass is held fixed, so increasing diameter lowers the ballistic coefficient: the
    vehicle decelerates higher up in thinner air. Nose radius is scaled with diameter to
    keep the capsule's bluntness ratio constant, since an unconstrained nose radius
    would let the optimiser 'win' by changing only the heating correlation's denominator.
    """
    base_d = float(base_config["vehicle"]["geometry"]["diameter_m"])
    base_rn = float(base_config["vehicle"]["geometry"]["nose_radius_m"])
    bluntness = base_rn / base_d

    evaluations: list[DesignEvaluation] = []
    total = len(gamma_deg_values) * len(diameter_m_values)
    for gam in gamma_deg_values:
        for dia in diameter_m_values:
            cfg = copy.deepcopy(base_config)
            cfg["entry"]["flight_path_angle_deg"] = float(gam)
            cfg["vehicle"]["geometry"]["diameter_m"] = float(dia)
            cfg["vehicle"]["geometry"]["nose_radius_m"] = float(bluntness * dia)
            ev = evaluate_design(cfg, design_id=f"J-g{gam:+06.2f}-d{dia:04.2f}")
            evaluations.append(ev)
            if progress and len(evaluations) % 25 == 0:
                print(f"  [{len(evaluations):>4}/{total}] ...", flush=True)

    return JointSweep(
        evaluations=evaluations,
        gamma_deg=np.asarray(gamma_deg_values, dtype=float),
        diameter_m=np.asarray(diameter_m_values, dtype=float),
        shape=(len(gamma_deg_values), len(diameter_m_values)),
    )


@dataclass
class OptimiserComparison:
    """Peak-heat-only design versus joint-objective design, both feasible."""

    peak_only: DesignEvaluation | None
    joint: DesignEvaluation | None
    baseline: DesignEvaluation
    n_feasible: int
    pareto: list[DesignEvaluation]

    @property
    def bondline_saving_k(self) -> float:
        """How much cooler the joint design's bondline is [K]. Positive = joint wins."""
        if self.peak_only is None or self.joint is None:
            return float("nan")
        return (self.peak_only.performance.peak_bondline_temperature_k
                - self.joint.performance.peak_bondline_temperature_k)

    @property
    def peak_flux_cost_pct(self) -> float:
        """What the joint design gives up on the conventional metric [%]."""
        if self.peak_only is None or self.joint is None:
            return float("nan")
        a = self.peak_only.performance.peak_heat_flux_w_m2
        b = self.joint.performance.peak_heat_flux_w_m2
        return 100.0 * (b - a) / a


def compare_optimisers(sweep: JointSweep, baseline: DesignEvaluation) -> OptimiserComparison:
    """Extract the H1 comparison from a completed grid.

    peak_only : the feasible design a conventional peak-heat-flux optimiser selects.
    joint     : from the feasible Pareto front over (q''_max, T_bond_max), the design
                with the lowest bondline temperature - i.e. what O1 would prefer when
                the failure mode is bondline-driven.
    """
    feas = sweep.feasible_evaluations()
    if not feas:
        return OptimiserComparison(None, None, baseline, 0, [])

    peak_only = min(feas, key=lambda e: e.performance.peak_heat_flux_w_m2)
    objectives = np.array([
        [e.performance.peak_heat_flux_w_m2, e.performance.peak_bondline_temperature_k]
        for e in feas
    ])
    front_idx = pareto_front(objectives)
    front = [feas[i] for i in front_idx]
    front.sort(key=lambda e: e.performance.peak_heat_flux_w_m2)
    joint = min(front, key=lambda e: e.performance.peak_bondline_temperature_k)

    return OptimiserComparison(peak_only, joint, baseline, len(feas), front)
