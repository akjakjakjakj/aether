"""Spec section 44 - does the Thermal Penetration Index tell us anything new?

The question, stated so it can fail
-----------------------------------
TPI is a candidate cumulative in-depth thermal-exposure metric (`scoring/tpi.py`). The
project already reports peak bondline temperature and integrated external heat load. A
third number earns its place only if it ORDERS DESIGNS DIFFERENTLY from what we already
have - if a designer using TPI would pick a different capsule than a designer using peak
bondline temperature and heat load. If TPI's ranking is reconstructible from those two,
it is a restatement, and the honest thing to do is discard it.

So the test is a redundancy test, declared before the numbers are looked at:

    R^2 of TPI's RANKS regressed on the ranks of (peak bondline T, integrated heat)

If that R^2 is above the threshold in `configs/tpi_study.yaml`, TPI adds no interpretable
information and the verdict is DISCARD. Rank space, not value space, because we care
about which design gets chosen, not about a linear fit to a number in K m s.

The trap this study is built to avoid
-------------------------------------
M1 swept ONE parameter (flight-path angle) and got Spearman rho = -1.000 between peak
flux and bondline temperature. That correlation was nearly content-free: two strictly
monotone functions of a single variable can only ever give rho = +-1, whatever the
physics. The same trap is waiting here - every metric in this project is monotone in
gamma over a fixed-geometry line, so a one-parameter TPI sweep would "prove" whatever
was wanted.

This study therefore runs on the 2-D (flight-path angle x diameter) grid from M1b, where
the metrics are NOT forced into a common ordering, and it computes the one-parameter
correlations too - explicitly labelled as tautological - so the difference is visible
rather than assumed. `one_parameter_tautology_check` exists to make that point with
numbers instead of a footnote.

Every design is evaluated through `evaluate_design` via `run_joint_sweep`. Nothing here
integrates a trajectory or a TPS stack itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.stats import kendalltau, spearmanr

from ..evaluate import DesignEvaluation
from ..scoring import TPIConfig, thermal_penetration_index
from .joint_sweep import JointSweep, run_joint_sweep

COMPARISON_METRICS = (
    ("peak_heat_flux_w_m2", "peak heat flux"),
    ("integrated_external_heat_j_m2", "integrated external heat"),
    ("peak_bondline_temperature_k", "peak bondline temperature"),
    ("bondline_exposure_metric_k_s", "bondline exposure (M4)"),
)


def _ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks, ties shared. scipy's rankdata without the import churn."""
    from scipy.stats import rankdata

    return rankdata(values)


def _safe_spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rho, or NaN when either input is constant (rho is undefined, not 0)."""
    if np.ptp(a) == 0.0 or np.ptp(b) == 0.0:
        return float("nan")
    return float(spearmanr(a, b).statistic)


def rank_regression_r2(target: np.ndarray, predictors: list[np.ndarray]) -> float:
    """R^2 of `target`'s ranks explained by the ranks of `predictors` (OLS, intercept).

    This is the redundancy measure. R^2 = 1 means the target's ordering is a linear
    function of the predictors' orderings, i.e. it carries no ordering information they
    do not already carry.
    """
    y = _ranks(np.asarray(target, dtype=float))
    if np.ptp(y) == 0.0:
        return float("nan")
    cols = [_ranks(np.asarray(p, dtype=float)) for p in predictors]
    design = np.column_stack([np.ones_like(y)] + cols)
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ coef
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot


@dataclass
class TPIVariant:
    """TPI evaluated over the whole grid under one declared configuration."""

    config: TPIConfig
    values_k_m_s: np.ndarray
    peak_exceedance_depth_m: np.ndarray
    exceedance_profiles_k_s: np.ndarray | None = None
    """Shape (n_designs, n_cells). Kept only for the reference variant, because the
    SHAPE of these profiles is what explains the verdict - see
    `exceedance_shape_statistics`."""
    depth_m: np.ndarray | None = None

    @property
    def label(self) -> str:
        return self.config.label


@dataclass
class TPIStudy:
    """Everything the section-44 verdict is read from."""

    sweep: JointSweep
    reference: TPIVariant
    variants: list[TPIVariant]
    metrics: dict[str, np.ndarray]
    feasible: np.ndarray
    thresholds: dict[str, float]
    notes: list[str] = field(default_factory=list)

    # ---- views ----------------------------------------------------------------------

    @property
    def n_designs(self) -> int:
        return len(self.sweep.evaluations)

    def subset(self, feasible_only: bool) -> np.ndarray:
        """Boolean mask selecting the designs a given analysis runs over."""
        if not feasible_only:
            return np.ones(self.n_designs, dtype=bool)
        return self.feasible.copy()

    def correlations(self, variant: TPIVariant, *, feasible_only: bool = False
                     ) -> dict[str, float]:
        """Spearman rho between one TPI variant and each canonical metric."""
        mask = self.subset(feasible_only)
        return {
            key: _safe_spearman(variant.values_k_m_s[mask], self.metrics[key][mask])
            for key, _ in COMPARISON_METRICS
        }

    def redundancy_r2(self, variant: TPIVariant, *, feasible_only: bool = False) -> float:
        """How much of TPI's ordering is already in bondline T plus integrated heat."""
        mask = self.subset(feasible_only)
        return rank_regression_r2(
            variant.values_k_m_s[mask],
            [self.metrics["peak_bondline_temperature_k"][mask],
             self.metrics["integrated_external_heat_j_m2"][mask]],
        )

    def disagreement(self, variant: TPIVariant, *, feasible_only: bool = False
                     ) -> dict[str, Any]:
        """Where TPI and peak bondline temperature order designs differently."""
        mask = self.subset(feasible_only)
        tpi = variant.values_k_m_s[mask]
        bond = self.metrics["peak_bondline_temperature_k"][mask]
        n = len(tpi)
        if n < 2 or np.ptp(tpi) == 0.0 or np.ptp(bond) == 0.0:
            return {"n": n, "kendall_tau": float("nan"), "discordant_pairs": 0,
                    "total_pairs": n * (n - 1) // 2, "discordant_fraction": float("nan")}
        tau = float(kendalltau(tpi, bond).statistic)
        total = n * (n - 1) // 2
        # Kendall tau-b with no ties: tau = (concordant - discordant) / total
        discordant = int(round(total * (1.0 - tau) / 2.0))
        return {
            "n": n,
            "kendall_tau": tau,
            "discordant_pairs": discordant,
            "total_pairs": total,
            "discordant_fraction": discordant / total if total else float("nan"),
        }

    def best_by(self, key: str, *, feasible_only: bool = True) -> DesignEvaluation | None:
        """The design a single-objective minimiser of `key` would select."""
        mask = self.subset(feasible_only)
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return None
        values = self.metrics[key][mask]
        return self.sweep.evaluations[int(idx[int(np.argmin(values))])]

    def best_by_tpi(self, variant: TPIVariant, *, feasible_only: bool = True
                    ) -> DesignEvaluation | None:
        mask = self.subset(feasible_only)
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return None
        values = variant.values_k_m_s[mask]
        return self.sweep.evaluations[int(idx[int(np.argmin(values))])]

    def exceedance_shape_statistics(self, *, outer_fraction: float = 0.2) -> dict[str, Any]:
        """Is TPI redundant because the surface dominates, or because the SHAPE is fixed?

        Those are different explanations and they have different consequences, so the
        question is settled with numbers rather than with an argument.

        - If the depth integral were dominated by the outer millimetre, TPI would be a
          surface metric wearing a depth integral as a disguise, and a depth weighting
          could in principle rescue it.
        - If instead every design produces the SAME normalised exceedance profile scaled
          by a different factor, then TPI is that scalar, no weighting can separate the
          designs any differently, and the metric is redundant by construction.

        Reported: the fraction of the depth integral lying in the outermost
        `outer_fraction` of the domain (uniform would give exactly `outer_fraction`), and
        the minimum pairwise cosine similarity between the designs' normalised profiles
        (1.0 means every design has an identical profile shape).
        """
        profiles = self.reference.exceedance_profiles_k_s
        if profiles is None:
            return {"available": False}
        totals = profiles.sum(axis=1)
        live = totals > 0.0
        p = profiles[live]
        n_outer = max(1, int(round(outer_fraction * p.shape[1])))
        outer = p[:, :n_outer].sum(axis=1) / p.sum(axis=1)
        unit = p / np.linalg.norm(p, axis=1, keepdims=True)
        similarity = unit @ unit.T
        return {
            "available": True,
            "n_designs_with_any_exceedance": int(live.sum()),
            "outer_fraction_of_domain": outer_fraction,
            "outer_share_min": float(outer.min()),
            "outer_share_max": float(outer.max()),
            "outer_share_if_uniform": outer_fraction,
            "min_pairwise_cosine_similarity": float(similarity.min()),
            "mean_pairwise_cosine_similarity": float(similarity.mean()),
        }

    def one_parameter_tautology_check(self) -> dict[str, Any]:
        """Spearman rho along each fixed-diameter LINE of the grid.

        Along a line only flight-path angle varies. If both metrics are monotone in it,
        rho must be exactly +-1 regardless of whether the metrics are related - the
        result M1 already flagged. Reporting the distribution of |rho| over the lines
        next to the 2-D value is the cheapest available demonstration that the 2-D
        number is the one carrying information.
        """
        n_gamma, n_dia = self.sweep.shape
        tpi_grid = self.reference.values_k_m_s.reshape(self.sweep.shape)
        bond_grid = self.metrics["peak_bondline_temperature_k"].reshape(self.sweep.shape)
        per_line = [
            _safe_spearman(tpi_grid[:, j], bond_grid[:, j]) for j in range(n_dia)
        ]
        per_line = [r for r in per_line if not np.isnan(r)]
        return {
            "n_lines": len(per_line),
            "line_length": n_gamma,
            "min_abs_rho": float(np.min(np.abs(per_line))) if per_line else float("nan"),
            "n_saturated": int(np.sum(np.abs(per_line) >= 0.999)) if per_line else 0,
            "grid_rho": _safe_spearman(
                self.reference.values_k_m_s,
                self.metrics["peak_bondline_temperature_k"]),
        }


@dataclass
class TPIVerdict:
    """The section-44 decision, with the evidence that produced it."""

    decision: str
    """'DISCARD' or 'KEEP'."""
    reasons: list[str]
    reference_r2: float
    reference_rho_bondline: float
    variant_r2: dict[str, float]
    unanimous: bool
    """True if every sensitivity variant reached the same decision as the reference."""
    selects_a_different_design: bool
    """Whether a TPI-minimising optimiser picks a different design than a bondline-
    minimising one. If it never does, the metric cannot change an engineering decision."""


def decide(study: TPIStudy) -> TPIVerdict:
    """Apply the pre-declared redundancy thresholds. No threshold is chosen here."""
    r2_thr = study.thresholds["redundancy_r2_threshold"]
    rho_thr = study.thresholds["redundancy_rho_threshold"]

    ref_r2 = study.redundancy_r2(study.reference)
    ref_rho = study.correlations(study.reference)["peak_bondline_temperature_k"]

    variant_r2 = {v.label: study.redundancy_r2(v) for v in study.variants}
    redundant = [r >= r2_thr for r in variant_r2.values() if not np.isnan(r)]

    best_tpi = study.best_by_tpi(study.reference)
    best_bond = study.best_by("peak_bondline_temperature_k")
    differs = (best_tpi is not None and best_bond is not None
               and best_tpi.design_id != best_bond.design_id)

    reasons: list[str] = []
    decision = "KEEP"
    if not np.isnan(ref_r2) and ref_r2 >= r2_thr:
        decision = "DISCARD"
        reasons.append(
            f"TPI's ranking is {100 * ref_r2:.2f}% reconstructible from peak bondline "
            f"temperature and integrated heat load (rank R^2 = {ref_r2:.4f} >= "
            f"{r2_thr:.2f}), so it restates information the project already reports."
        )
    if not np.isnan(ref_rho) and abs(ref_rho) >= rho_thr:
        decision = "DISCARD"
        reasons.append(
            f"TPI and peak bondline temperature are ordered almost identically over the "
            f"2-D grid (Spearman rho = {ref_rho:+.4f}, |rho| >= {rho_thr:.2f})."
        )
    if not differs:
        reasons.append(
            "A TPI-minimising optimiser selects the same design as a bondline-minimising "
            "one, so adopting TPI would not have changed any design decision in this study."
        )
    elif decision == "DISCARD":
        reasons.append(
            "Note: despite the redundancy, the TPI-optimal and bondline-optimal designs "
            "differ - see the report before treating the discard as absolute."
        )
    if decision == "KEEP":
        reasons.append(
            f"TPI's ordering is only {100 * ref_r2:.2f}% explained by the existing metrics "
            f"(threshold {100 * r2_thr:.0f}%), so it carries ordering information they do "
            f"not."
        )

    return TPIVerdict(
        decision=decision,
        reasons=reasons,
        reference_r2=ref_r2,
        reference_rho_bondline=ref_rho,
        variant_r2=variant_r2,
        unanimous=bool(redundant) and (all(redundant) or not any(redundant)),
        selects_a_different_design=differs,
    )


def evaluate_tpi_over_sweep(sweep: JointSweep, config: TPIConfig, *,
                            keep_profiles: bool = False) -> TPIVariant:
    """Apply one TPI configuration to every already-evaluated design in a sweep."""
    values = np.empty(len(sweep.evaluations))
    depths = np.empty(len(sweep.evaluations))
    profiles: list[np.ndarray] = []
    cell_depths = None
    for i, ev in enumerate(sweep.evaluations):
        out = thermal_penetration_index(ev.tps, config)
        values[i] = out.tpi_k_m_s
        depths[i] = out.peak_exceedance_depth_m
        if keep_profiles:
            profiles.append(out.exceedance_profile_k_s)
            cell_depths = out.depth_m
    return TPIVariant(
        config=config, values_k_m_s=values, peak_exceedance_depth_m=depths,
        exceedance_profiles_k_s=(np.array(profiles) if keep_profiles else None),
        depth_m=cell_depths,
    )


def run_tpi_study(
    base_config: dict[str, Any],
    gamma_deg_values: np.ndarray,
    diameter_m_values: np.ndarray,
    reference_config: TPIConfig,
    variant_configs: list[TPIConfig],
    thresholds: dict[str, float],
    *,
    progress: bool = True,
) -> TPIStudy:
    """Run the M1b design grid through `evaluate_design` and score every design's TPI.

    The grid is deliberately the SAME one M1b used, so TPI is being compared against the
    existing metrics on the existing design space rather than on a space chosen to suit
    it.
    """
    sweep = run_joint_sweep(base_config, gamma_deg_values, diameter_m_values,
                            progress=progress)

    metrics = {
        key: np.array([getattr(ev.performance, key) for ev in sweep.evaluations])
        for key, _ in COMPARISON_METRICS
    }
    feasible = np.array([ev.performance.feasible for ev in sweep.evaluations], dtype=bool)

    reference = evaluate_tpi_over_sweep(sweep, reference_config, keep_profiles=True)
    variants = [evaluate_tpi_over_sweep(sweep, cfg) for cfg in variant_configs]

    return TPIStudy(
        sweep=sweep,
        reference=reference,
        variants=variants,
        metrics=metrics,
        feasible=feasible,
        thresholds=dict(thresholds),
    )


def study_table(study: TPIStudy) -> list[dict[str, Any]]:
    """Flat per-design records for CSV persistence. Every reported number comes from here."""
    rows: list[dict[str, Any]] = []
    for i, ev in enumerate(study.sweep.evaluations):
        row = {
            "design_id": ev.design_id,
            "gamma_deg": ev.design_vector["entry_flight_path_angle_deg"],
            "diameter_m": ev.design_vector["diameter_m"],
            "ballistic_coefficient_kg_m2": ev.design_vector["ballistic_coefficient_kg_m2"],
            "feasible": ev.performance.feasible,
            "tpi_reference_k_m_s": study.reference.values_k_m_s[i],
            "tpi_peak_exceedance_depth_m": study.reference.peak_exceedance_depth_m[i],
        }
        for key, _ in COMPARISON_METRICS:
            row[key] = study.metrics[key][i]
        for v in study.variants:
            row[f"tpi[{v.label}]_k_m_s"] = v.values_k_m_s[i]
        rows.append(row)
    return rows
