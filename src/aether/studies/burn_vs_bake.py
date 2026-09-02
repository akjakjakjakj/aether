"""Milestone 1 - the burn-vs-bake study.

What this asks
--------------
Is there a pair of otherwise-valid entries (A, B) such that

    q''_max(B) < q''_max(A)        B looks SAFER by the conventional metric
    T_bond_max(B) > T_bond_max(A)  B is actually HOTTER where it matters

If such a pair exists, H0 survives: peak heat flux is not a sufficient design metric.
If it does not exist anywhere in the tested domain, that is a real result too and must
be reported as such. The search below does NOT tune anything to produce the answer - it
sweeps a declared domain, records every candidate including the bad ones, and reports
what came back.

Mechanism, stated in advance so the result can be judged as a prediction
-----------------------------------------------------------------------
Flight-path angle at entry sets how quickly the vehicle descends into dense air.

  steep entry  -> short, intense pulse. High q''_max. The TPS acts as a low-pass
                  filter; a short pulse is largely absorbed near the surface and
                  re-radiated away before it can diffuse a centimetre inward.
  shallow entry -> lower q''_max, but a much longer pulse and a larger integrated load.
                  Duration is comparable to the stack's diffusion time, so the heat
                  arrives at the bondline.

The prediction is therefore that q''_max and T_bond_max are ANTI-correlated over part
of the domain, and the counterexample should appear between shallow and steep entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..evaluate import DesignEvaluation, evaluate_design


@dataclass(frozen=True)
class CounterexamplePair:
    """One (A, B) pair satisfying the signature condition."""

    design_a: str
    design_b: str
    gamma_a_deg: float
    gamma_b_deg: float
    peak_q_a_w_m2: float
    peak_q_b_w_m2: float
    t_bond_a_k: float
    t_bond_b_k: float
    integrated_q_a_j_m2: float
    integrated_q_b_j_m2: float
    duration_a_s: float
    duration_b_s: float

    @property
    def peak_flux_reduction_pct(self) -> float:
        """How much B improves the conventional metric [%]."""
        return 100.0 * (self.peak_q_a_w_m2 - self.peak_q_b_w_m2) / self.peak_q_a_w_m2

    @property
    def bondline_penalty_k(self) -> float:
        """How much hotter B's bondline actually gets [K]."""
        return self.t_bond_b_k - self.t_bond_a_k

    @property
    def severity(self) -> float:
        """Ranking score: bondline penalty per percent of peak-flux 'improvement'."""
        return self.bondline_penalty_k / max(self.peak_flux_reduction_pct, 1e-9)


@dataclass
class BurnVsBakeStudy:
    """Full results of the sweep."""

    evaluations: list[DesignEvaluation]
    gamma_deg: np.ndarray
    peak_flux_w_m2: np.ndarray
    integrated_q_j_m2: np.ndarray
    peak_bondline_k: np.ndarray
    bondline_exposure_k_s: np.ndarray
    penetration_depth_m: np.ndarray
    max_g: np.ndarray
    duration_s: np.ndarray
    feasible: np.ndarray
    counterexamples: list[CounterexamplePair] = field(default_factory=list)

    @property
    def hypothesis_h0_supported(self) -> bool:
        """True iff at least one signature counterexample was found."""
        return len(self.counterexamples) > 0

    def as_table(self) -> list[dict[str, Any]]:
        """Flat records, one per candidate, for Parquet/CSV persistence."""
        return [
            {
                "design_id": ev.design_id,
                "gamma_deg": ev.design_vector["entry_flight_path_angle_deg"],
                "ballistic_coefficient_kg_m2": ev.design_vector["ballistic_coefficient_kg_m2"],
                "nose_radius_m": ev.design_vector["nose_radius_m"],
                **ev.performance.to_dict(),
            }
            for ev in self.evaluations
        ]


def find_counterexamples(
    ids: list[str],
    gamma: np.ndarray,
    peak_q: np.ndarray,
    t_bond: np.ndarray,
    integrated_q: np.ndarray,
    duration: np.ndarray,
    valid: np.ndarray,
    *,
    min_flux_reduction_pct: float = 1.0,
    min_bondline_penalty_k: float = 1.0,
) -> list[CounterexamplePair]:
    """Exhaustive O(n^2) scan for pairs satisfying the signature condition.

    Thresholds exist so that numerical noise cannot be reported as a physical result;
    they are declared, not tuned. Only pairs where BOTH candidates satisfy the hard
    constraints are considered - an infeasible design is not a design.
    """
    pairs: list[CounterexamplePair] = []
    idx = np.flatnonzero(valid)
    for i in idx:
        for j in idx:
            if i == j:
                continue
            reduction = 100.0 * (peak_q[i] - peak_q[j]) / peak_q[i]
            penalty = t_bond[j] - t_bond[i]
            if reduction >= min_flux_reduction_pct and penalty >= min_bondline_penalty_k:
                pairs.append(
                    CounterexamplePair(
                        design_a=ids[i], design_b=ids[j],
                        gamma_a_deg=float(gamma[i]), gamma_b_deg=float(gamma[j]),
                        peak_q_a_w_m2=float(peak_q[i]), peak_q_b_w_m2=float(peak_q[j]),
                        t_bond_a_k=float(t_bond[i]), t_bond_b_k=float(t_bond[j]),
                        integrated_q_a_j_m2=float(integrated_q[i]),
                        integrated_q_b_j_m2=float(integrated_q[j]),
                        duration_a_s=float(duration[i]), duration_b_s=float(duration[j]),
                    )
                )
    pairs.sort(key=lambda p: p.bondline_penalty_k, reverse=True)
    return pairs


def run_burn_vs_bake(
    base_config: dict[str, Any],
    gamma_deg_values: np.ndarray,
    *,
    require_feasible: bool = False,
    progress: bool = True,
) -> BurnVsBakeStudy:
    """Sweep entry flight-path angle and search for the signature counterexample.

    Parameters
    ----------
    require_feasible:
        If True only constraint-satisfying candidates may form a counterexample pair.
        The default is False for M1 because the point of M1 is the PHYSICS of the
        anti-correlation; feasibility filtering is applied in the optimisation phase.
        Both settings are reported.
    """
    import copy

    evaluations: list[DesignEvaluation] = []
    for n, gam in enumerate(gamma_deg_values):
        cfg = copy.deepcopy(base_config)
        cfg["entry"]["flight_path_angle_deg"] = float(gam)
        ev = evaluate_design(cfg, design_id=f"M1-g{gam:+06.2f}")
        evaluations.append(ev)
        if progress:
            p = ev.performance
            print(
                f"  [{n+1:>3}/{len(gamma_deg_values)}] gamma={gam:+6.2f} deg  "
                f"q_pk={p.peak_heat_flux_w_m2/1e4:7.2f} W/cm2  "
                f"T_bond={p.peak_bondline_temperature_k:7.1f} K  "
                f"t={p.entry_duration_s:6.1f} s  "
                f"{'feasible' if p.feasible else 'INFEASIBLE'}",
                flush=True,
            )

    get = lambda f: np.array([f(ev) for ev in evaluations])  # noqa: E731
    peak_q = get(lambda e: e.performance.peak_heat_flux_w_m2)
    t_bond = get(lambda e: e.performance.peak_bondline_temperature_k)
    integrated = get(lambda e: e.performance.integrated_external_heat_j_m2)
    duration = get(lambda e: e.performance.entry_duration_s)
    feasible = get(lambda e: e.performance.feasible).astype(bool)
    ok = get(lambda e: e.performance.status == "OK").astype(bool)

    valid = (feasible & ok) if require_feasible else ok
    pairs = find_counterexamples(
        [ev.design_id for ev in evaluations],
        np.asarray(gamma_deg_values, dtype=float),
        peak_q, t_bond, integrated, duration, valid,
    )

    return BurnVsBakeStudy(
        evaluations=evaluations,
        gamma_deg=np.asarray(gamma_deg_values, dtype=float),
        peak_flux_w_m2=peak_q,
        integrated_q_j_m2=integrated,
        peak_bondline_k=t_bond,
        bondline_exposure_k_s=get(lambda e: e.performance.bondline_exposure_metric_k_s),
        penetration_depth_m=get(lambda e: e.performance.thermal_penetration_depth_m),
        max_g=get(lambda e: e.performance.max_g),
        duration_s=duration,
        feasible=feasible,
        counterexamples=pairs,
    )
