"""The specification's section 39 final comparison table, generated from result files.

Conceptual anchor
-----------------
Section 39 asks for four designs side by side - Baseline, peak-heat-only optimised,
joint-O1 optimised, robust-O1 optimised - across nine metrics plus feasibility plus
uncertainty. It is the table the whole project is answerable for, so the one thing it may
never contain is a hand-typed number.

Every row here is built the same way:

  1. its DESIGN VECTOR is read from a result file on disk (the design-space reference,
     an M4 run's `summary.json`, a robust run's front), never typed;
  2. it is RE-EVALUATED through the canonical `evaluate_design` under today's source, in
     one run, so that the four rows are comparable with each other;
  3. the value STORED in its source run is quoted beside it, with the difference, because
     a design optimised under a different heating model is a fact about the project's
     history and silently replacing it would erase that;
  4. its uncertainty column comes from an actual propagation of the declared inputs, not
     from a repeated assertion that the model is approximate.

Step 2 is not optional. The M4 front on disk was computed under the legacy `cap_radius`
heating model, behind a bluntness cap that has since been removed (A-OPT-5, NR-15), so
its stored peak-flux numbers are about 20% low relative to today's model. Quoting them in
the same table as a freshly-run robust design would be comparing two different physics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..evaluate import evaluate_design
from ..optimization.design_space import DesignSpace
from ..scoring.tpi import TPIConfig, thermal_penetration_index

SOURCE_KINDS = ("design_space_reference", "m4_selected", "m7_robust")

COLUMN_UNITS = {
    "peak_heat_flux_w_m2": "W m^-2",
    "integrated_external_heat_j_m2": "J m^-2",
    "peak_surface_temperature_k": "K",
    "peak_bondline_temperature_k": "K",
    "bondline_exposure_metric_k_s": "K s",
    "thermal_penetration_depth_m": "m",
    "tpi_k_m_s": "K m s",
    "max_g": "g",
    "max_dynamic_pressure_pa": "Pa",
    "entry_duration_s": "s",
}

TPI_FOOTNOTE = (
    "The Thermal Penetration Index column is reported FOR COMPLETENESS ONLY. Spec §44 "
    "asked for it; the §44 study (`reports/milestones/TPI_study.md`, "
    "`docs/negative_results.md` NR-10) returned the verdict **DISCARD**: over the M1b "
    "design grid, TPI's ranking of designs is 99.94% reconstructible by rank regression "
    "on (peak bondline temperature, integrated heat load), its Spearman correlation with "
    "peak bondline temperature alone is +0.9992, and a TPI-minimising optimiser selects "
    "the same design as a bondline-minimising one. All 16 declared combinations of "
    "reference temperature and weighting family failed the pre-declared redundancy "
    "criterion, so it is not an artefact of one setting. The mechanism is shape "
    "invariance: every design produces very nearly the same normalised depth profile, so "
    "any weighted depth integral of it recovers the scale factor and nothing more. It is "
    "printed here so a reader can check that claim on these four designs rather than "
    "take it on trust, and it is NOT used to rank anything."
)


@dataclass
class ComparisonRow:
    """One row of the §39 table."""

    label: str
    source: str
    available: bool
    reason: str = ""
    design_values: dict[str, float] = field(default_factory=dict)
    source_run: str = ""
    metrics: dict[str, float] = field(default_factory=dict)
    stored_metrics: dict[str, float] = field(default_factory=dict)
    deltas: dict[str, float] = field(default_factory=dict)
    feasible: bool | None = None
    status: str = ""
    constraint_margins: dict[str, float] = field(default_factory=dict)
    uncertainty: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in
                ("label", "source", "available", "reason", "design_values", "source_run",
                 "metrics", "stored_metrics", "deltas", "feasible", "status",
                 "constraint_margins", "uncertainty", "diagnostics")}


# ---------------------------------------------------------------------------------------
# resolving design vectors from result files
# ---------------------------------------------------------------------------------------

def latest_run(results: Path, pattern: str, marker: str) -> Path | None:
    runs = sorted(p for p in results.glob(pattern) if (p / marker).exists())
    return runs[-1] if runs else None


def resolve_design(spec: dict[str, Any], space: DesignSpace, *,
                   m4_summary: dict[str, Any] | None,
                   m4_run_id: str,
                   robust_front: pd.DataFrame | None,
                   robust_run_id: str) -> tuple[dict[str, float] | None, str, str]:
    """(design values, source run id, reason it is unavailable).

    Never invents a design. A row whose source is not on disk comes back as None with the
    reason written out, and the table prints NOT AVAILABLE for it.
    """
    kind = str(spec["source"])
    if kind not in SOURCE_KINDS:
        raise ValueError(f"unknown comparison source {kind!r}, expected {SOURCE_KINDS}")

    if kind == "design_space_reference":
        return {v.name: v.reference for v in space.variables}, "configs/design_space.yaml", ""

    if kind == "m4_selected":
        if m4_summary is None:
            return None, "", ("no M4 optimisation run with a summary.json was found under "
                              "results/M4 - run `make doe && make optimize` first")
        key = str(spec["key"])
        selected = m4_summary.get("selected", {})
        if key not in selected:
            return None, m4_run_id, (f"M4 run {m4_run_id} has no selected design {key!r} "
                                     f"(it has {sorted(selected)})")
        row = selected[key]
        values = {v.name: float(row[f"x__{v.name}"]) for v in space.variables
                  if f"x__{v.name}" in row}
        missing = [v.name for v in space.variables if f"x__{v.name}" not in row]
        if missing:
            return None, m4_run_id, (f"M4 run {m4_run_id}'s {key!r} design does not carry "
                                     f"{missing}; the design space has changed since")
        return values, m4_run_id, ""

    # m7_robust
    if robust_front is None or robust_front.empty:
        return None, robust_run_id, ("no robust optimisation front is available - run "
                                     "`make robust` first")
    key = str(spec.get("key", "knee"))
    row = _pick_robust(robust_front, key)
    values = {v.name: float(row[f"x__{v.name}"]) for v in space.variables
              if f"x__{v.name}" in row}
    frozen = {v.name: v.reference for v in space.variables if f"x__{v.name}" not in row}
    return {**frozen, **values}, robust_run_id, ""


def _pick_robust(front: pd.DataFrame, key: str) -> pd.Series:
    """Which point of the robust front the table reports."""
    from ..optimization.pareto import knee_point, normalise

    cols = [c for c in front.columns if c.startswith("robust__")]
    if key == "knee" and len(front) >= 3:
        points = front[cols].to_numpy(dtype=float)
        ideal = points.min(axis=0)
        ref = points.max(axis=0)
        ref = np.where(ref > ideal, ref, ideal + 1.0)
        return front.iloc[knee_point(normalise(points, ideal, ref))]
    if key.startswith("min_"):
        return front.iloc[int(front[f"robust__{key[4:]}"].astype(float).argmin())]
    return front.iloc[0]


# ---------------------------------------------------------------------------------------
# building the table
# ---------------------------------------------------------------------------------------

def evaluate_row(label: str, source: str, values: dict[str, float], space: DesignSpace,
                 tpi_cfg: TPIConfig, source_run: str,
                 stored: dict[str, float] | None = None) -> ComparisonRow:
    """One nominal evaluation of one row, through the canonical evaluator.

    TPI is computed here and not in the budget wrapper because it needs the whole T(x, t)
    field, which the wrapper deliberately does not ship back from a worker process
    (`budget.evaluate_candidate` returns scalars only). One call per table row is four
    calls in total, so there is nothing to parallelise.
    """
    config = space.config_for(values)
    ev = evaluate_design(config, design_id=f"M7-{label}")
    perf = ev.performance
    metrics: dict[str, float] = {
        name: float(getattr(perf, name)) for name in COLUMN_UNITS if name != "tpi_k_m_s"
    }
    metrics["tpi_k_m_s"] = (float(thermal_penetration_index(ev.tps, tpi_cfg).tpi_k_m_s)
                            if ev.tps is not None else float("nan"))
    stored = stored or {}
    deltas = {k: float(metrics[k] - stored[k]) for k in metrics
              if k in stored and np.isfinite(stored[k]) and np.isfinite(metrics[k])}
    return ComparisonRow(
        label=label, source=source, available=True, design_values=dict(values),
        source_run=source_run, metrics=metrics, stored_metrics=dict(stored),
        deltas=deltas, feasible=bool(perf.feasible), status=perf.status,
        constraint_margins={k: float(v) for k, v in perf.constraint_margins.items()},
        diagnostics={k: float(v) for k, v in ev.diagnostics.items()},
    )


def stored_metrics_for(spec: dict[str, Any], m4_summary: dict[str, Any] | None
                       ) -> dict[str, float]:
    """The metrics the source run recorded for this design, for the traceability column."""
    if str(spec["source"]) != "m4_selected" or m4_summary is None:
        return {}
    row = m4_summary.get("selected", {}).get(str(spec["key"]), {})
    return {k: float(v) for k, v in row.items()
            if k in COLUMN_UNITS and isinstance(v, int | float)}


def uncertainty_cell(propagation: Any, objectives: tuple[str, ...]) -> dict[str, Any]:
    """The §39 'uncertainty' column: what the propagation says about this row.

    Deliberately not one number. A single "+-x%" would have to pick between variability
    and ignorance, and the whole point of M7 is that they are different.
    """
    if propagation is None:
        return {"available": False,
                "reason": "no propagation was run for this design"}
    cell: dict[str, Any] = {"available": True,
                            "n_samples": int(len(propagation.rows)),
                            "n_not_evaluable": propagation.n_not_evaluable}
    for name in objectives:
        combined = propagation.combined.get(name, {})
        decomposition = propagation.decomposition.get(name, {})
        band = propagation.band.get(name, {}).get("p95", {})
        cell[name] = {
            "mean": combined.get("mean"),
            "std": combined.get("std"),
            "p5": combined.get("percentiles", {}).get("p5"),
            "p95": combined.get("percentiles", {}).get("p95"),
            "p99": combined.get("percentiles", {}).get("p99"),
            "std_aleatory": decomposition.get("std_aleatory"),
            "std_epistemic": decomposition.get("std_epistemic"),
            "epistemic_share_of_variance": decomposition.get(
                "epistemic_share_of_variance"),
            "p95_band_across_epistemic_branches": [band.get("min"), band.get("max")],
        }
    cell["violation_probability"] = {
        name: {"point": v.point, "wilson": list(v.wilson), "phrase": v.phrase}
        for name, v in propagation.violations.items()
    }
    return cell


@dataclass
class ComparisonTable:
    """The whole §39 table plus every caveat it has to carry."""

    rows: list[ComparisonRow]
    columns: tuple[str, ...]
    units: dict[str, str]
    tpi_footnote: str
    stale_warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"columns": list(self.columns), "units": dict(self.units),
                "tpi_footnote": self.tpi_footnote,
                "stale_warnings": list(self.stale_warnings),
                "provenance": dict(self.provenance),
                "rows": [r.to_dict() for r in self.rows]}

    def to_frame(self) -> pd.DataFrame:
        """Long-form table, one row per (design, column). The CSV a reader can re-plot."""
        records: list[dict[str, Any]] = []
        for row in self.rows:
            for name in self.columns:
                records.append({
                    "design": row.label, "source": row.source,
                    "source_run": row.source_run, "available": row.available,
                    "metric": name, "units": self.units.get(name, ""),
                    "value": row.metrics.get(name, float("nan")),
                    "stored_value": row.stored_metrics.get(name, float("nan")),
                    "delta_vs_stored": row.deltas.get(name, float("nan")),
                    "feasible": row.feasible,
                })
        return pd.DataFrame(records)


def load_m4_summary(results: Path) -> tuple[dict[str, Any] | None, str, dict[str, Any]]:
    """(summary, run id, config snapshot) of the newest M4 optimisation run, or Nones."""
    import yaml

    run = latest_run(results / "M4", "M4-OPT-*", "summary.json")
    if run is None:
        return None, "", {}
    summary = json.loads((run / "summary.json").read_text())
    snapshot_path = run / "config_snapshot.yaml"
    snapshot = (yaml.safe_load(snapshot_path.read_text())["config"]
                if snapshot_path.exists() else {})
    return summary, run.name, snapshot
