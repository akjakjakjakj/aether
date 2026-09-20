#!/usr/bin/env python3
"""Milestone M4, part 2: multi-objective optimisation under matched budgets.

    python scripts/run_optimize.py [--config configs/design_space.yaml]
                                   [--doe-run M4-DOE-...] [--workers N]
                                   [--report-only M4-OPT-...]

Frees exactly the variables the DOE's `screening.json` left active (latest DOE run unless
`--doe-run` is given), then runs every enabled method for every seed through the same
`BudgetedEvaluator`.

Writes:
    results/M4/<run_id>/candidates.csv|.parquet  every candidate of every method and seed
    results/M4/<run_id>/summary.json             every number the report quotes
    results/M4/<run_id>/config_snapshot.yaml
    reports/figures/M4_pareto_front|M4_hypervolume|M4_front_variables .png / .pdf
    reports/milestones/M4_pareto_optimisation.md

Runs for several minutes - use the background.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# One BLAS thread per worker process. The banded solves are tiny; letting every worker
# spawn its own thread pool oversubscribes the machine (observed: load average > 30 with
# six workers) and slows everything else running on it, the M2 CFD job included.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.optimization import (  # noqa: E402
    METHODS,
    BudgetedEvaluator,
    CandidateStore,
    audit_exploits,
    feasible_front,
    hypervolume_curve,
    load_candidates,
    load_design_space,
    normalise,
    normalised_hypervolume,
    select_designs,
    spacing_metric,
)
from src.aether.optimization.budget import evaluate_candidate  # noqa: E402
from src.aether.optimization.plots import plot_optimisation_figures  # noqa: E402
from src.aether.optimization.report import write_m4_report  # noqa: E402
from src.aether.utils.run import RunMeta, config_hash, new_run_id, snapshot_config  # noqa: E402


def _latest_doe(results: Path) -> Path:
    runs = sorted(p for p in results.glob("M4-DOE-*") if (p / "screening.json").exists())
    if not runs:
        raise SystemExit("no DOE run with a screening.json found - run `make doe` first")
    return runs[-1]


def _row_dict(row) -> dict:
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in row.to_dict().items()}


def _what_stops_it(row, space, audit_cfg) -> dict:
    """Box bounds a selected design is parked on, and constraints within 1% of active."""
    tol = float(audit_cfg["bound_tolerance_fraction"])
    bounds = []
    for var in space.active_variables:
        value = float(row[f"x__{var.name}"])
        if value <= var.lower + tol * var.span:
            bounds.append(f"{var.name} at its lower box bound {var.lower:g}")
        elif value >= var.upper - tol * var.span:
            bounds.append(f"{var.name} at its upper box bound {var.upper:g}")
    active = [c.removeprefix("margin__") for c in row.index
              if c.startswith("margin__") and row[c] == row[c] and row[c] < 0.01]
    return {"box_bounds": bounds, "active_constraints": active}


def summarise(frame, space, cfg, run_meta: dict, doe_summary: dict, wall: dict) -> tuple:
    opt = cfg["optimize"]
    objectives = tuple(cfg["objectives"])
    hv_cfg = {key: {name: float(value) for name, value in opt["hypervolume"][key].items()}
              for key in ("reference_point", "ideal_point")}
    ideal = np.array([hv_cfg["ideal_point"][n] for n in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][n] for n in objectives], dtype=float)
    budget = int(opt["budget_evaluations"])
    checkpoints = np.unique(np.linspace(budget / int(opt["curve_checkpoints"]), budget,
                                        int(opt["curve_checkpoints"])).astype(int))

    methods: dict = {}
    curves: dict = {}
    fronts: dict = {}
    for method in [m for m in METHODS if m in set(frame["method"])]:
        sub = frame[frame["method"] == method]
        per_seed, stats = [], {k: [] for k in ("n_feasible", "front_size", "spacing",
                                               "cache_hits", "budget_used", "not_evaluable",
                                               "evals_to_95pct")}
        for seed in sorted(sub["seed"].unique()):
            run = sub[sub["seed"] == seed]
            curve = hypervolume_curve(run, objectives, hv_cfg, checkpoints)
            per_seed.append(curve)
            front = feasible_front(run, objectives)
            paid = run[~run["cache_hit"]]
            stats["n_feasible"].append(int(paid["feasible"].sum()))
            stats["front_size"].append(int(len(front)))
            stats["spacing"].append(spacing_metric(
                normalise(front[list(objectives)].to_numpy(dtype=float), ideal, ref))
                if len(front) else float("nan"))
            stats["cache_hits"].append(int(run["cache_hit"].sum()))
            stats["budget_used"].append(int(paid["budget_index"].max()))
            stats["not_evaluable"].append(int((paid["status"] != "OK").sum()))
            reached = np.flatnonzero(curve >= 0.95 * curve[-1]) if curve[-1] > 0 else []
            stats["evals_to_95pct"].append(
                float(checkpoints[reached[0]]) if len(reached) else float("nan"))
        curve_arr = np.array(per_seed)
        curves[method] = curve_arr
        fronts[method] = feasible_front(sub, objectives)
        final = curve_arr[:, -1]
        methods[method] = {
            "hv_final_per_seed": final.tolist(),
            "hv_mean": float(final.mean()), "hv_std": float(final.std(ddof=1)),
            "hv_min": float(final.min()), "hv_max": float(final.max()),
            "n_feasible_mean": float(np.mean(stats["n_feasible"])),
            "front_size_mean": float(np.mean(stats["front_size"])),
            "spacing_mean": float(np.nanmean(stats["spacing"])),
            "cache_hits_mean": float(np.mean(stats["cache_hits"])),
            "evals_to_95pct_median": float(np.nanmedian(stats["evals_to_95pct"])),
            "wall_s_mean": float(np.mean(wall.get(method, [float("nan")]))),
            "per_seed": stats,
            "hv_curve_median": np.median(curve_arr, axis=0).tolist(),
        }

    combined = feasible_front(frame, objectives)
    selected = select_designs(combined, objectives, hv_cfg)
    feas = frame[frame["feasible"]].drop_duplicates("candidate_id")
    outside = int(np.sum(~np.all(feas[list(objectives)].to_numpy(dtype=float) < ref, axis=1)))
    combined_norm = normalise(combined[list(objectives)].to_numpy(dtype=float), ideal, ref)

    summary = {
        **run_meta,
        "objectives": list(objectives), "active": list(space.active),
        "frozen": {v.name: v.reference for v in space.variables if v.name not in space.active},
        "variables": doe_summary["variables"],
        "budget": budget, "seeds": [int(s) for s in opt["seeds"]],
        "checkpoints": checkpoints.tolist(),
        "hypervolume": hv_cfg, "methods": methods,
        "combined": {
            "n_front": int(len(combined)),
            "hv": normalised_hypervolume(feas[list(objectives)].to_numpy(dtype=float),
                                         ideal, ref),
            "spacing": spacing_metric(combined_norm) if len(combined) else float("nan"),
            "n_feasible_distinct": int(len(feas)),
            "n_feasible_outside_reference": outside,
        },
        "selected": {k: _row_dict(v) for k, v in selected.items()},
        "selected_limits": {k: _what_stops_it(v, space, opt["exploit_audit"])
                            for k, v in selected.items()},
        "method_settings": {m: opt["methods"][m] for m in methods},
        "audit": audit_exploits(frame, combined, space, objectives, opt["exploit_audit"]),
    }
    if {"peak_flux_only", "joint_knee"} <= set(selected):
        a, b = selected["peak_flux_only"], selected["joint_knee"]
        summary["comparison"] = {
            "bondline_delta_k": float(b["peak_bondline_temperature_k"]
                                      - a["peak_bondline_temperature_k"]),
            "peak_flux_delta_w_m2": float(b["peak_heat_flux_w_m2"] - a["peak_heat_flux_w_m2"]),
            "heat_load_delta_j_m2": float(b["integrated_external_heat_j_m2"]
                                          - a["integrated_external_heat_j_m2"]),
            "front_bondline_span_k": float(combined["peak_bondline_temperature_k"].max()
                                           - combined["peak_bondline_temperature_k"].min()),
            "front_flux_span_w_m2": float(combined["peak_heat_flux_w_m2"].max()
                                          - combined["peak_heat_flux_w_m2"].min()),
        }
    return summary, fronts, combined, selected, curves, checkpoints


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/design_space.yaml")
    ap.add_argument("--doe-run", default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--report-only", default=None, metavar="RUN_ID",
                    help="rebuild summary, figures and report from an existing run's log")
    args = ap.parse_args()

    results = ROOT / "results" / "M4"
    full_space, cfg = load_design_space(ROOT / args.config)
    opt = cfg["optimize"]
    objectives = tuple(cfg["objectives"])

    if args.report_only:
        out_dir = results / args.report_only
        saved = json.loads((out_dir / "summary.json").read_text())
        doe_dir, run_meta, wall = results / saved["doe_run_id"], None, saved["wall_s"]
        run_id = args.report_only
    else:
        doe_dir = results / args.doe_run if args.doe_run else _latest_doe(results)
        run_id = new_run_id("M4-OPT")
        out_dir = results / run_id
    doe_summary = json.loads((doe_dir / "summary.json").read_text())
    screening = json.loads((doe_dir / "screening.json").read_text())
    space = full_space.with_active(screening["active"])

    if args.report_only:
        run_meta = {k: saved[k] for k in ("run_id", "doe_run_id", "git_commit", "git_dirty",
                                          "config_hash", "fidelity", "aero_model",
                                          "reference_design", "wall_s", "workers")}
    else:
        snapshot = {"study": cfg, "base": space.base_config, "screening": screening}
        meta = RunMeta(run_id=run_id, config_hash=config_hash(snapshot),
                       notes=f"M4 optimisation against DOE {doe_summary['run_id']}")
        snapshot_config(snapshot, out_dir, meta)
        store = CandidateStore(out_dir / "candidates.csv")
        workers = int(args.workers or opt["workers"])
        print(f"AETHER M4 optimise  run={run_id}  doe={doe_summary['run_id']}  "
              f"git={meta.git_commit}{' (dirty)' if meta.git_dirty else ''}  workers={workers}")
        print(f"active variables: {list(space.active)}")

        reference_values = {v.name: v.reference for v in space.variables}
        reference_design = {
            "candidate_id": "reference",
            **evaluate_candidate((space.config_for(reference_values), "reference")),
        }
        wall: dict[str, list[float]] = {}
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for method, runner in METHODS.items():
                settings = opt["methods"].get(method, {})
                if not settings.get("enabled", False):
                    continue
                for seed in opt["seeds"]:
                    evaluator = BudgetedEvaluator(
                        space, int(opt["budget_evaluations"]), store, run_id=run_id,
                        method=method, seed=int(seed), executor=pool)
                    start = time.perf_counter()
                    runner(evaluator, settings, objectives, opt["hypervolume"])
                    wall.setdefault(method, []).append(time.perf_counter() - start)
                    print(f"  {method:<14} seed {seed:>3}: spent {evaluator.used} of "
                          f"{evaluator.budget}, {evaluator.n_cache_hits} cache hits, "
                          f"{wall[method][-1]:.0f} s", flush=True)
        store.export_parquet()
        run_meta = {
            "run_id": run_id, "doe_run_id": doe_summary["run_id"],
            "git_commit": meta.git_commit, "git_dirty": meta.git_dirty,
            "config_hash": meta.config_hash, "workers": workers, "wall_s": wall,
            "aero_model": space.base_config["vehicle"]["aero"]["model"],
            "reference_design": reference_design,
        }

    frame = load_candidates(out_dir / "candidates.csv")
    run_meta["fidelity"] = int(frame["fidelity"].max())
    summary, fronts, combined, selected, curves, checkpoints = summarise(
        frame, space, cfg, run_meta, doe_summary, wall)
    with open(out_dir / "summary.json", "w") as fh:
        json.dump(summary, fh, indent=2, default=float)

    figures = plot_optimisation_figures(summary, frame, fronts, combined, selected, curves,
                                        checkpoints, list(space.active),
                                        ROOT / "reports" / "figures")
    report = write_m4_report(ROOT, doe_summary, summary)

    print()
    for method, m in summary["methods"].items():
        print(f"  {method:<14} HV = {m['hv_mean']:.4f} +/- {m['hv_std']:.4f} "
              f"[{m['hv_min']:.4f}, {m['hv_max']:.4f}]")
    print(f"combined front: {summary['combined']['n_front']} designs")
    print(f"figures: {[p.name for p in figures]}")
    print(f"report -> {report}\nresults -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
