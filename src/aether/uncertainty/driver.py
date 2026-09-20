"""The M7 study driver: everything the two scripts share.

`scripts/run_uncertainty.py` and `scripts/run_robust_optimize.py` are thin wrappers over
this module, so the propagation a robust run uses to verify its shortcut is literally the
same code as the propagation the standalone study reports, and the §39 table is assembled
once.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from ..optimization import BudgetedEvaluator, CandidateStore, load_design_space
from ..optimization.budget import evaluate_candidate
from ..optimization.design_space import DesignSpace
from ..scoring.tpi import TPIConfig
from ..utils.run import load_config
from . import comparison as cmp_mod
from .attribution import attribute, saltelli_unit_points
from .guards import m4_front_is_current, screening_is_current, stale_banner
from .inputs import UncertaintyModel
from .propagate import analyse, evaluate_under_uncertainty
from .sampling import make_draws
from .space import make_uncertain_space

UNITS = dict(cmp_mod.COLUMN_UNITS)


# ---------------------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------------------

@dataclass
class Context:
    """Everything a study needs, loaded and checked once."""

    root: Path
    study: dict[str, Any]
    space: DesignSpace
    model: UncertaintyModel
    screening: dict[str, Any]
    doe_run_id: str
    m4_summary: dict[str, Any] | None
    m4_run_id: str
    m4_snapshot: dict[str, Any]
    stale_warnings: list[str] = field(default_factory=list)

    @property
    def objectives(self) -> tuple[str, ...]:
        return tuple(self.design_space_config["objectives"])

    design_space_config: dict[str, Any] = field(default_factory=dict)


def load_context(root: Path, config_path: str | Path, *, doe_run: str | None = None,
                 strict_screening: bool = True,
                 aero_model: str | None = None) -> Context:
    """Load the design space, the DOE screening and the uncertainty inventory.

    Refuses, exactly as `scripts/run_ai_ablation.py` does, if the DOE screening that
    supplies the active-variable list is void for today's design space: the active list is
    a property of the model it was screened on. `strict_screening=False` downgrades that
    refusal to a recorded warning and is reserved for SMOKE runs, whose output is labelled
    as not being a result.

    `aero_model` overrides `vehicle.aero.model` with `allow_provisional: true`. It exists
    to exercise the Fidelity-1 branch of the uncertainty inventory - where it will
    correctly REFUSE, because the C_D discretisation term needs an M2 GCI that does not
    exist yet - and must not be used to produce a reported number.
    """
    root = Path(root)
    study = load_config(root / config_path if not Path(config_path).is_absolute()
                        else config_path)
    full_space, ds_cfg = load_design_space(root / study["meta"]["design_space"], root)
    if aero_model is not None:
        full_space.base_config.setdefault("vehicle", {})["aero"] = {
            "model": str(aero_model), "allow_provisional": True}

    doe_dir = _latest(root / "results" / "M4", "M4-DOE-*", "screening.json",
                      pinned=doe_run)
    if doe_dir is None:
        raise SystemExit("no DOE run with a screening.json under results/M4 - run "
                         "`make doe` first")
    screening = json.loads((doe_dir / "screening.json").read_text())
    doe_snapshot = yaml.safe_load((doe_dir / "config_snapshot.yaml").read_text())["config"]
    stale = screening_is_current(doe_snapshot, ds_cfg, full_space.base_config)
    warnings: list[str] = []
    if stale and strict_screening:
        raise SystemExit(
            f"REFUSING TO RUN: the screening of DOE run {doe_dir.name} is void for the "
            "current design space:\n  - " + "\n  - ".join(stale) + "\nThe active-variable "
            "list is a property of the model it was screened on. Re-run `make doe` (and "
            "`make optimize`) first, or pin a current DOE run with DOE_RUN=...")
    if stale:
        warnings.append(
            f"STALE SCREENING, ACCEPTED FOR A SMOKE RUN ONLY: DOE run {doe_dir.name}'s "
            "active-variable list is void for the current design space:\n  - "
            + "\n  - ".join(stale)
            + "\nThe run continued because strict screening was switched off. Nothing "
              "produced under this flag is a result.")
    space = full_space.with_active(screening["active"])

    model = UncertaintyModel.from_config(study, space.base_config)

    m4_summary, m4_run_id, m4_snapshot = cmp_mod.load_m4_summary(root / "results")
    if m4_snapshot:
        reasons = m4_front_is_current(m4_snapshot, ds_cfg, space.base_config)
        banner = stale_banner(reasons, m4_run_id)
        if banner:
            warnings.append(banner)
    return Context(root=root, study=study, space=space, model=model, screening=screening,
                   doe_run_id=doe_dir.name, m4_summary=m4_summary, m4_run_id=m4_run_id,
                   m4_snapshot=m4_snapshot, stale_warnings=warnings,
                   design_space_config=ds_cfg)


def _latest(results: Path, pattern: str, marker: str, pinned: str | None = None
            ) -> Path | None:
    if pinned:
        candidate = results / pinned
        return candidate if (candidate / marker).exists() else None
    runs = sorted(p for p in results.glob(pattern) if (p / marker).exists())
    return runs[-1] if runs else None


def latest_robust_run(root: Path, pinned: str | None = None) -> Path | None:
    return _latest(Path(root) / "results" / "M7", "M7-ROBUST-*", "robust.json",
                   pinned=pinned)


# ---------------------------------------------------------------------------------------
# design resolution
# ---------------------------------------------------------------------------------------

def resolve_designs(ctx: Context, specs: list[dict[str, Any]], *,
                    robust_front: pd.DataFrame | None = None,
                    robust_run_id: str = "") -> dict[str, dict[str, Any]]:
    """{label: {values, source, source_run, reason}} for a list of design specs."""
    out: dict[str, dict[str, Any]] = {}
    for spec in specs:
        values, source_run, reason = cmp_mod.resolve_design(
            spec, ctx.space, m4_summary=ctx.m4_summary, m4_run_id=ctx.m4_run_id,
            robust_front=robust_front, robust_run_id=robust_run_id)
        out[str(spec["label"])] = {"values": values, "source": str(spec["source"]),
                                   "source_run": source_run, "reason": reason,
                                   "spec": spec}
    return out


def active_vector(ctx: Context, values: dict[str, float]) -> np.ndarray:
    return np.array([[float(values[name]) for name in ctx.space.active]])


# ---------------------------------------------------------------------------------------
# sizing
# ---------------------------------------------------------------------------------------

def measure_evaluation_cost(ctx: Context, n: int = 5) -> float:
    """Wall time of one coupled evaluation on the design-space reference design.

    Measured, not assumed: `configs/uncertainty.yaml` carries a value from the last
    measurement and the study prints what it measures now beside it.
    """
    reference = {v.name: v.reference for v in ctx.space.variables}
    config = ctx.space.config_for(reference)
    evaluate_candidate((config, "warmup"))
    start = time.perf_counter()
    for _ in range(n):
        evaluate_candidate((config, "timing"))
    return (time.perf_counter() - start) / n


def size_study(ctx: Context, *, seconds_per_evaluation: float, workers: int,
               efficiency: float, counts: dict[str, int]) -> dict[str, Any]:
    """Project the wall time of each stage from the measured per-evaluation cost."""
    sizing = dict(ctx.study.get("sizing", {}))
    rate = workers * efficiency / seconds_per_evaluation if seconds_per_evaluation else 0.0
    out: dict[str, Any] = {
        "declared_seconds_per_evaluation": sizing.get("measured_seconds_per_evaluation"),
        "measured_seconds_per_evaluation": seconds_per_evaluation,
        "workers": workers,
        "declared_parallel_efficiency": sizing.get("parallel_efficiency"),
        "measured_parallel_efficiency": efficiency,
        "measured_evaluations_per_second": rate,
        "budget_seconds": float(sizing.get("budget_seconds", 7200.0)),
    }
    total = 0
    for stage, n in counts.items():
        out[f"{stage}_evaluations"] = int(n)
        out[f"{stage}_seconds"] = float(n / rate) if rate else float("nan")
        total += int(n)
    out["total_evaluations"] = total
    out["total_seconds"] = float(total / rate) if rate else float("nan")
    out["fits_budget"] = bool(out["total_seconds"] <= out["budget_seconds"])
    return out


# ---------------------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------------------

def run_propagation(ctx: Context, designs: dict[str, dict[str, Any]], *,
                    store: CandidateStore, run_id: str, executor,
                    n_aleatory: int, n_epistemic: int, mode: str, seed: int,
                    outputs: tuple[str, ...], percentiles: tuple[float, ...],
                    confidence: float, convergence: dict[str, Any],
                    method: str = "propagate") -> tuple[dict[str, Any], dict[str, Any]]:
    """Propagate every available design. Returns ({label: DesignPropagation}, draws)."""
    model = ctx.model
    draws = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                       model.indices_of_kind("epistemic"), mode=mode, seed=seed,
                       n_aleatory=n_aleatory, n_epistemic_branches=n_epistemic)
    uspace = make_uncertain_space(ctx.space, model, draws.unit)
    indices = np.arange(len(draws))

    results: dict[str, Any] = {}
    for i, (label, entry) in enumerate(designs.items()):
        if entry["values"] is None:
            continue
        evaluator = BudgetedEvaluator(uspace, len(draws), store, run_id=run_id,
                                      method=f"{method}:{label}", seed=seed,
                                      executor=executor)
        frame = evaluate_under_uncertainty(evaluator, uspace,
                                           active_vector(ctx, entry["values"]), indices,
                                           generation=i)
        nominal = evaluate_candidate((ctx.space.config_for(entry["values"]),
                                      f"M7-nominal-{label}"))
        result = analyse(label, frame, draws,
                         design_values={k: float(v) for k, v in entry["values"].items()},
                         outputs=outputs, percentiles=percentiles, confidence=confidence,
                         convergence_checkpoints=tuple(convergence.get("checkpoints", ())),
                         convergence_output=str(convergence.get(
                             "output", "peak_bondline_temperature_k")),
                         convergence_tolerance_rel=float(convergence.get(
                             "tolerance_relative", 0.02)),
                         nominal={k: float(nominal[k]) for k in outputs if k in nominal},
                         seed=seed)
        result.nominal_feasible = bool(nominal["feasible"])  # type: ignore[attr-defined]
        results[label] = {"result": result, "nominal_row": nominal, "entry": entry}
    return results, draws


def run_attribution(ctx: Context, designs: dict[str, dict[str, Any]], labels: list[str], *,
                    store: CandidateStore, run_id: str, executor, n_base: int,
                    outputs: tuple[str, ...], n_bootstrap: int, confidence: float,
                    seed: int) -> dict[str, Any]:
    """Sobol' attribution over the uncertain inputs, per requested design."""
    model = ctx.model
    unit = saltelli_unit_points(model.n_inputs, n_base, seed)
    uspace = make_uncertain_space(ctx.space, model, unit)
    indices = np.arange(len(unit))
    out: dict[str, Any] = {}
    for i, label in enumerate(labels):
        entry = designs.get(label)
        if entry is None or entry["values"] is None:
            continue
        evaluator = BudgetedEvaluator(uspace, len(unit), store, run_id=run_id,
                                      method=f"attribute:{label}", seed=seed,
                                      executor=executor)
        frame = evaluate_under_uncertainty(evaluator, uspace,
                                           active_vector(ctx, entry["values"]), indices,
                                           generation=i)
        if len(frame) != len(unit):
            out[label] = {"n_base": n_base, "n_evaluations": len(unit), "inputs": [],
                          "outputs": {},
                          "not_computed": {o: "the Saltelli design did not complete "
                                              "within the budget" for o in outputs}}
            continue
        block = attribute(label, frame, model, n_base=n_base, outputs=outputs,
                          n_bootstrap=n_bootstrap, confidence=confidence,
                          seed=seed).to_dict()
        # K = R_b/R_n decides whether the nose-radius model form can move anything at
        # all: at K = 1 the body IS a hemisphere and the two sources agree identically by
        # Zoby & Sullivan's own eq. (5), so a zero index there is a property of the
        # geometry and not a broken input. The report says so rather than leaving a
        # reader to wonder.
        bluntness = entry["values"].get("bluntness_ratio")
        block["k_body_over_nose"] = (0.5 / float(bluntness)
                                     if bluntness else float("nan"))
        out[label] = block
    return out


def build_comparison(ctx: Context, *, propagations: dict[str, Any],
                     robust_front: pd.DataFrame | None, robust_run_id: str,
                     store: CandidateStore, run_id: str, executor
                     ) -> cmp_mod.ComparisonTable:
    """The §39 table: design vectors from result files, metrics re-evaluated here."""
    spec = ctx.study["comparison"]
    tpi_cfg = TPIConfig(**{k: v for k, v in spec["tpi"].items()})
    columns = tuple(spec["columns"])
    n_samples = int(spec.get("uncertainty_samples", 500))
    seed = int(spec.get("uncertainty_seed", 0))

    designs = resolve_designs(ctx, spec["rows"], robust_front=robust_front,
                              robust_run_id=robust_run_id)
    model = ctx.model
    draws = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                       model.indices_of_kind("epistemic"), mode="mixed", seed=seed,
                       n_aleatory=n_samples)
    uspace = make_uncertain_space(ctx.space, model, draws.unit)
    indices = np.arange(len(draws))

    rows: list[cmp_mod.ComparisonRow] = []
    for i, (label, entry) in enumerate(designs.items()):
        if entry["values"] is None:
            rows.append(cmp_mod.ComparisonRow(label=label, source=entry["source"],
                                              available=False, reason=entry["reason"],
                                              source_run=entry["source_run"]))
            continue
        stored = cmp_mod.stored_metrics_for(entry["spec"], ctx.m4_summary)
        row = cmp_mod.evaluate_row(label, entry["source"], entry["values"], ctx.space,
                                   tpi_cfg, entry["source_run"], stored)
        # reuse an existing propagation if this design already has one
        existing = _matching_propagation(propagations, entry["values"])
        if existing is not None:
            row.uncertainty = cmp_mod.uncertainty_cell(existing, ctx.objectives)
        else:
            evaluator = BudgetedEvaluator(uspace, len(draws), store, run_id=run_id,
                                          method=f"compare:{label}", seed=seed,
                                          executor=executor)
            frame = evaluate_under_uncertainty(
                evaluator, uspace, active_vector(ctx, entry["values"]), indices,
                generation=100 + i)
            result = analyse(label, frame, draws,
                             design_values={k: float(v) for k, v in
                                            entry["values"].items()},
                             outputs=ctx.objectives, seed=seed)
            row.uncertainty = cmp_mod.uncertainty_cell(result, ctx.objectives)
        rows.append(row)

    table = cmp_mod.ComparisonTable(
        rows=rows, columns=columns, units=dict(cmp_mod.COLUMN_UNITS),
        tpi_footnote=cmp_mod.TPI_FOOTNOTE, stale_warnings=list(ctx.stale_warnings),
        provenance={"m4_run_id": ctx.m4_run_id, "robust_run_id": robust_run_id,
                    "doe_run_id": ctx.doe_run_id,
                    "uncertainty_samples": n_samples, "uncertainty_seed": seed,
                    "tpi_config": dict(spec["tpi"])})
    table.uncertainty_samples = n_samples  # type: ignore[attr-defined]
    return table


def _matching_propagation(propagations: dict[str, Any], values: dict[str, float]):
    for block in propagations.values():
        result = block["result"]
        if all(abs(float(result.design_values.get(k, np.nan)) - float(v)) <= 1e-9
               for k, v in values.items() if k in result.design_values) \
                and result.design_values:
            return result
    return None


# ---------------------------------------------------------------------------------------
# summary assembly
# ---------------------------------------------------------------------------------------

def density_profile_block(ctx: Context) -> dict[str, Any] | None:
    for item in ctx.model.inputs:
        if item.apply.get("type") == "density_profile":
            block = dict(item.apply["sigma_vs_altitude_km"])
            return {"altitude_km": list(block["altitude_km"]),
                    "sigma_relative": list(block["sigma_relative"]),
                    "tier": list(block.get("tier", []))}
    return None


def assemble_summary(ctx: Context, *, run_id: str, meta: Any, workers: int,
                     wall_s: float, n_evaluations: int, source_hash: str,
                     propagations: dict[str, Any], draws: Any,
                     attribution: dict[str, Any] | None = None,
                     robust: dict[str, Any] | None = None,
                     comparison: cmp_mod.ComparisonTable | None = None,
                     sizing: dict[str, Any] | None = None,
                     figures: list[Path] | None = None) -> dict[str, Any]:
    base = ctx.space.base_config
    limits = base.get("limits", {}) or {}
    summary: dict[str, Any] = {
        "run_id": run_id,
        "git_commit": meta.git_commit,
        "git_dirty": meta.git_dirty,
        "config_hash": meta.config_hash,
        "source_hash": source_hash,
        "doe_run_id": ctx.doe_run_id,
        "m4_run_id": ctx.m4_run_id,
        "workers": workers,
        "wall_s": wall_s,
        "n_evaluations": n_evaluations,
        "aero_model": str((base.get("vehicle", {}).get("aero") or {}).get("model",
                                                                         "constant")),
        "fidelity": 1 if str((base.get("vehicle", {}).get("aero") or {})
                             .get("model", "constant")) != "constant" else 0,
        "objectives": list(ctx.objectives),
        "active": list(ctx.space.active),
        "frozen": {v.name: v.reference for v in ctx.space.variables
                   if v.name not in ctx.space.active},
        "units": dict(UNITS),
        "allowables": {"peak_bondline_temperature_k": limits.get("t_bondline_allowable_k"),
                       "max_g": limits.get("max_g")},
        "uncertainty_model": {**ctx.model.to_dict(),
                              "density_profile": density_profile_block(ctx)},
        "draws": draws.to_dict() if draws is not None else {},
        "pbox_output": ctx.objectives[-1],
        "stale_warnings": list(ctx.stale_warnings),
        "sizing": sizing or {},
        "propagation": {},
        "figures": [str(p) for p in (figures or [])],
    }
    for label, block in propagations.items():
        result = block["result"]
        payload = result.to_dict()
        payload["nominal_feasible"] = bool(block["nominal_row"]["feasible"])
        payload["nominal_status"] = str(block["nominal_row"]["status"])
        payload["source"] = block["entry"]["source"]
        payload["source_run"] = block["entry"]["source_run"]
        summary["propagation"][label] = payload
    if attribution:
        summary["attribution"] = attribution
    if robust:
        summary["robust"] = robust
    if comparison is not None:
        summary["comparison"] = {**comparison.to_dict(),
                                 "uncertainty_samples": getattr(
                                     comparison, "uncertainty_samples", None)}
    summary["nominal_designs_under_uncertainty"] = _fragility(ctx, propagations)
    summary["cost_of_robustness"] = _cost_of_robustness(ctx, summary)
    return summary


def _fragility(ctx: Context, propagations: dict[str, Any]) -> list[dict[str, Any]]:
    """Where each nominal-optimal design sits relative to its own constraints once
    uncertainty is on. This is the §28 'do not pick a fragile design' evidence."""
    out: list[dict[str, Any]] = []
    for label, block in propagations.items():
        result = block["result"]
        nominal_row = block["nominal_row"]
        margins = {k.removeprefix("margin__"): float(v) for k, v in nominal_row.items()
                   if k.startswith("margin__") and np.isfinite(float(v))}
        worst = min(margins.items(), key=lambda kv: kv[1]) if margins else (None, np.nan)
        anyv = result.violations.get("any")
        out.append({
            "label": label,
            "source": block["entry"]["source"],
            "is_nominal_optimum": block["entry"]["source"] == "m4_selected",
            "nominal": {name: float(nominal_row[name]) for name in ctx.objectives},
            "p95": {name: result.combined.get(name, {}).get("percentiles", {}).get("p95")
                    for name in ctx.objectives},
            "binding_constraint": worst[0],
            "nominal_margin_pct": float(worst[1] * 100.0) if np.isfinite(worst[1])
            else float("nan"),
            "violation_point": anyv.point if anyv else float("nan"),
            "violation_phrase": anyv.phrase if anyv else "",
            "nominal_feasible": bool(nominal_row["feasible"]),
        })
    return out


def _cost_of_robustness(ctx: Context, summary: dict[str, Any]) -> dict[str, Any]:
    """What robustness cost in nominal performance, if both fronts exist."""
    robust = summary.get("robust") or {}
    front = robust.get("front")
    comparison = summary.get("comparison")
    if not front or not comparison:
        return {}
    rows = {r["label"]: r for r in comparison["rows"] if r["available"]}
    joint = rows.get("Joint O1 optimised")
    robust_row = rows.get("Robust O1 optimised")
    if joint is None or robust_row is None:
        return {}
    out: dict[str, Any] = {}
    for name in ctx.objectives:
        a = float(joint["metrics"].get(name, np.nan))
        b = float(robust_row["metrics"].get(name, np.nan))
        out[f"nominal_{name}_joint"] = a
        out[f"nominal_{name}_robust"] = b
        out[f"nominal_{name}_penalty"] = b - a
        out[f"nominal_{name}_penalty_fraction"] = (b - a) / a if a else float("nan")
    return out
