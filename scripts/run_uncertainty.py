#!/usr/bin/env python3
"""Milestone M7, part 1: uncertainty propagation, attribution and the §39 table.

    python scripts/run_uncertainty.py                      full study
    python scripts/run_uncertainty.py --smoke               tiny N, proves the chain only
    python scripts/run_uncertainty.py --time-only           measure per-evaluation cost
    python scripts/run_uncertainty.py --robust-run M7-...   pin a robust run to fold in
    python scripts/run_uncertainty.py --report-only M7-...  rebuild figures and report

Propagates the inputs declared in `configs/uncertainty.yaml` through the canonical
`evaluate_design`, for every design the config lists, keeping aleatory variability and
epistemic ignorance separate to the outputs. Then runs Sobol' attribution over the
uncertain inputs and assembles the specification's §39 comparison table.

The active design variables come from the latest M4 DOE's `screening.json`, and the run
REFUSES if that screening is void for today's design space - the active list is a
property of the model it was screened on.

Writes:
    results/M7/<run_id>/candidates.csv|.parquet   every evaluation, as M4 logs them
    results/M7/<run_id>/draws.csv                 every uncertainty draw, physical values
    results/M7/<run_id>/comparison.csv            the §39 table, long form
    results/M7/<run_id>/summary.json              every number the report quotes
    results/M7/<run_id>/config_snapshot.yaml
    reports/figures/M7_*.png|.pdf
    reports/milestones/M7_uncertainty_robust.md

Sized to about two hours on six workers - run it in the background.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# One BLAS thread per worker process: see scripts/run_optimize.py for why.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.uncertainty import plots  # noqa: E402
from src.aether.uncertainty.driver import (  # noqa: E402
    assemble_summary,
    build_comparison,
    latest_robust_run,
    load_context,
    measure_evaluation_cost,
    resolve_designs,
    run_attribution,
    run_propagation,
    size_study,
)
from src.aether.uncertainty.guards import GuardedStore  # noqa: E402
from src.aether.uncertainty.report import write_m7_report, write_summary  # noqa: E402
from src.aether.utils.run import (  # noqa: E402
    RunMeta,
    config_hash,
    new_run_id,
    snapshot_config,
)

SMOKE_NOTE = (
    "# SMOKE RUN - NOT A RESULT\n\n"
    "This directory was produced by `scripts/run_uncertainty.py --smoke`, whose only "
    "purpose is to prove that the propagation chain executes end to end. The sample "
    "sizes are far too small for any statistic in it to mean anything, and no number "
    "from it may be quoted anywhere. Delete it, or leave it labelled.\n"
)


def _draws_frame(model, draws) -> pd.DataFrame:
    rows = []
    for i, point in enumerate(draws.unit):
        values = model.draw(np.asarray(point))
        rows.append({"draw_index": i,
                     "epistemic_branch": int(draws.epistemic_index[i]),
                     "aleatory_index": int(draws.aleatory_index[i]),
                     **{f"u__{name}": float(u) for name, u in
                        zip(model.names, point, strict=True)},
                     **{f"value__{k}": v for k, v in values.items()}})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/uncertainty.yaml")
    ap.add_argument("--doe-run", default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--robust-run", default=None,
                    help="pin a robust run to fold in (default: the latest, if any)")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny sample sizes; proves the chain, produces no result")
    ap.add_argument("--time-only", action="store_true",
                    help="measure and print the per-evaluation cost, then stop")
    ap.add_argument("--report-only", default=None, metavar="RUN_ID",
                    help="rebuild figures and the report from an existing summary.json")
    ap.add_argument("--aero-model", default=None,
                    help="override vehicle.aero.model with allow_provisional: true. Only "
                         "for exercising the Fidelity-1 branch of the inventory, where it "
                         "will correctly REFUSE until M2 produces a GCI. Never for a "
                         "reported number")
    args = ap.parse_args()

    results = ROOT / "results" / "M7"

    if args.report_only:
        out_dir = results / args.report_only
        summary = json.loads((out_dir / "summary.json").read_text())
        if summary.get("smoke"):
            raise SystemExit("a smoke run publishes nothing; --report-only is for a study")
        frames, branches = _load_frames(out_dir, summary)
        # NR-34 item 6: this path used to pass None for BOTH fronts and silently dropped
        # two figures. Every input of every figure is now re-read from the run's records.
        import yaml
        snap = yaml.safe_load((out_dir / "config_snapshot.yaml").read_text())["config"]
        nominal_front, robust_front = _report_inputs(
            summary, frames, branches, float(snap["study"]["propagation"]["confidence"]))
        figures = plots.plot_all(summary, frames, branches, nominal_front, robust_front,
                                 ROOT / "reports" / "figures")
        summary["figures"] = [str(p) for p in figures]
        write_summary(out_dir, summary)
        report = write_m7_report(ROOT, summary)
        print(f"figures: {[p.name for p in figures]}\nreport -> {report}")
        return 0

    ctx = load_context(ROOT, args.config, doe_run=args.doe_run,
                       strict_screening=not args.smoke,
                       aero_model=getattr(args, "aero_model", None))
    prop_cfg = dict(ctx.study["propagation"])
    attr_cfg = dict(ctx.study["attribution"])
    workers = int(args.workers or prop_cfg.get("workers", 6))

    measured = measure_evaluation_cost(ctx)
    if args.time_only:
        print(f"measured wall time per coupled evaluation: {measured:.4f} s "
              "(single process, one BLAS thread)")
        print("configs/uncertainty.yaml declares "
              f"{ctx.study['sizing']['measured_seconds_per_evaluation']} s")
        return 0

    if args.smoke:
        prop_cfg.update(epistemic_branches=3, aleatory_samples=4)
        prop_cfg["convergence"] = {**prop_cfg["convergence"], "checkpoints": [4, 8, 12]}
        attr_cfg.update(n_base=8, n_bootstrap=20, designs=attr_cfg["designs"][:1])

    run_id = new_run_id("M7-SMOKE" if args.smoke else "M7-UQ")
    out_dir = results / run_id
    robust_dir = latest_robust_run(ROOT, args.robust_run)
    snapshot = {"study": ctx.study, "design_space": ctx.design_space_config,
                "base": ctx.space.base_config, "screening": ctx.screening,
                "smoke": bool(args.smoke), "robust_run": robust_dir.name if robust_dir
                else None}
    meta = RunMeta(run_id=run_id, config_hash=config_hash(snapshot),
                   notes=("M7 SMOKE - not a result" if args.smoke
                          else "M7 uncertainty propagation and attribution"))
    snapshot_config(snapshot, out_dir, meta)
    if args.smoke:
        (out_dir / "SMOKE.md").write_text(SMOKE_NOTE)

    store = GuardedStore(out_dir / "candidates.csv", ROOT / "src" / "aether", out_dir)
    print(f"AETHER M7 uncertainty  run={run_id}  git={meta.git_commit}"
          f"{' (dirty)' if meta.git_dirty else ''}  workers={workers}")
    print(f"evaluator source hash at launch: {store.launch_hash}")
    print(f"active variables: {list(ctx.space.active)}")
    print(f"uncertain inputs: {list(ctx.model.names)}")
    print(f"  aleatory : {[i.name for i in ctx.model.of_kind('aleatory')]}")
    print(f"  epistemic: {[i.name for i in ctx.model.of_kind('epistemic')]}")
    for name, reason in ctx.model.skipped:
        print(f"  SKIPPED {name}: {reason}")
    for warning in ctx.stale_warnings:
        print("\n" + warning + "\n")
    print(f"measured {measured:.4f} s per evaluation (single process)", flush=True)

    robust_block, robust_front = _load_robust(robust_dir)
    designs = resolve_designs(ctx, prop_cfg["designs"], robust_front=robust_front,
                              robust_run_id=robust_dir.name if robust_dir else "")
    for label, entry in designs.items():
        if entry["values"] is None:
            print(f"  design '{label}' UNAVAILABLE: {entry['reason']}")

    n_designs = sum(1 for e in designs.values() if e["values"] is not None)
    n_prop = (int(prop_cfg["epistemic_branches"]) * int(prop_cfg["aleatory_samples"])
              * n_designs)
    n_attr = int(attr_cfg["n_base"]) * (ctx.model.n_inputs + 2) * len(attr_cfg["designs"])
    n_cmp = int(ctx.study["comparison"].get("uncertainty_samples", 500)) * \
        len(ctx.study["comparison"]["rows"])
    sizing = size_study(ctx, seconds_per_evaluation=measured, workers=workers,
                        efficiency=float(ctx.study["sizing"].get("parallel_efficiency",
                                                                0.8)),
                        counts={"propagation": n_prop, "attribution": n_attr,
                                "comparison": n_cmp, "robust": 0, "verification": 0})
    print(f"projected: {sizing['total_evaluations']:,} evaluations, "
          f"~{sizing['total_seconds'] / 60:.1f} min at "
          f"{sizing['projected_evaluations_per_second']:.1f} eval/s (a projection from "
          "the declared parallel efficiency, not a measurement)", flush=True)

    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        store.check("before propagation")
        propagations, draws = run_propagation(
            ctx, designs, store=store, run_id=run_id, executor=pool,
            n_aleatory=int(prop_cfg["aleatory_samples"]),
            n_epistemic=int(prop_cfg["epistemic_branches"]),
            mode=str(prop_cfg["mode"]), seed=int(prop_cfg["seed"]),
            outputs=tuple(prop_cfg["outputs"]),
            percentiles=tuple(float(p) for p in prop_cfg["percentiles"]),
            confidence=float(prop_cfg["confidence"]),
            convergence=prop_cfg["convergence"])
        print(f"  propagation: {len(propagations)} designs x {len(draws)} draws "
              f"({time.perf_counter() - start:.0f} s)", flush=True)

        store.check("before attribution")
        attribution = run_attribution(
            ctx, designs, list(attr_cfg["designs"]), store=store, run_id=run_id,
            executor=pool, n_base=int(attr_cfg["n_base"]),
            outputs=tuple(attr_cfg["outputs"]),
            n_bootstrap=int(attr_cfg["n_bootstrap"]),
            confidence=float(attr_cfg["confidence"]), seed=int(attr_cfg["seed"]))
        print(f"  attribution: {list(attribution)} "
              f"({time.perf_counter() - start:.0f} s)", flush=True)

        store.check("before the comparison table")
        comparison = build_comparison(
            ctx, propagations=propagations, robust_front=robust_front,
            robust_run_id=robust_dir.name if robust_dir else "", store=store,
            run_id=run_id, executor=pool)
    wall = time.perf_counter() - start
    store.check("after the study")

    store.export_parquet()
    _draws_frame(ctx.model, draws).to_csv(out_dir / "draws.csv", index=False)
    comparison.to_frame().to_csv(out_dir / "comparison.csv", index=False)

    frame = store.load()
    summary = assemble_summary(
        ctx, run_id=run_id, meta=meta, workers=workers, wall_s=wall,
        n_evaluations=int((~frame["cache_hit"]).sum()), source_hash=store.launch_hash,
        propagations=propagations, draws=draws, attribution=attribution,
        robust=robust_block, comparison=comparison, sizing=sizing)
    summary["smoke"] = bool(args.smoke)

    # A SMOKE run documents itself inside its own directory and NEVER publishes to
    # reports/ - the same rule `scripts/run_ai_ablation.py` applies to a replay. A report
    # in reports/milestones/ is a claim; a smoke run has nothing to claim.
    fig_dir = (ROOT / "reports" / "figures") if not args.smoke else (out_dir / "figures")
    report_path = (None if not args.smoke
                   else out_dir / "M7_uncertainty_robust.SMOKE.md")
    frames = {label: block["result"].rows for label, block in propagations.items()}
    branches = {label: draws.epistemic_index for label in frames}
    nominal_front, robust_front = _report_inputs(summary, frames, branches,
                                                 float(prop_cfg["confidence"]))
    figures = plots.plot_all(summary, frames, branches, nominal_front, robust_front, fig_dir)
    summary["figures"] = [str(p) for p in figures]
    write_summary(out_dir, summary)
    report = write_m7_report(ROOT, summary, report_path)

    print()
    for label, block in summary["propagation"].items():
        for name in summary["objectives"]:
            c = block["combined"][name]
            d = block["decomposition"][name]
            print(f"  {label:<18} {name:<30} mean {c['mean']:.4g}  "
                  f"p95 {c['percentiles']['p95']:.4g}  "
                  f"sd_a {d.get('std_aleatory', float('nan')):.4g} / "
                  f"sd_e {d.get('std_epistemic', float('nan')):.4g}")
        print(f"  {label:<18} P(any constraint violated): "
              f"{block['violations']['any']['phrase']}")
    print(f"\nfigures: {[p.name for p in figures]}")
    print(f"report -> {report}\nresults -> {out_dir}")
    if args.smoke:
        print("\nSMOKE RUN: no number above is a result. See "
              f"{out_dir.relative_to(ROOT)}/SMOKE.md")
    return 0


def _load_robust(robust_dir: Path | None):
    if robust_dir is None:
        return None, None
    block = json.loads((robust_dir / "robust.json").read_text())
    front_path = robust_dir / "robust_front.csv"
    front = pd.read_csv(front_path) if front_path.exists() else None
    block["front"] = [] if front is None else front.to_dict("records")
    return block, front


def _report_inputs(summary: dict, frames: dict, branches: dict, confidence: float):
    """Everything the figures and the report need beyond `summary`, re-read from the runs
    the summary NAMES (never from "the latest"), plus the derived blocks a summary written
    before 2026-09-21 does not carry. Evaluates nothing. Existing summary fields are never
    modified: blocks are only ADDED, and only when absent.

    Returns (nominal_front, robust_front), either of which may be None.
    """
    from src.aether.optimization import feasible_front, load_candidates
    from src.aether.uncertainty.driver import achieved_throughput
    from src.aether.uncertainty.propagate import cluster_convergence

    objectives = tuple(summary["objectives"])
    results = ROOT / "results"

    robust_front = None
    robust_id = (summary.get("robust") or {}).get("run_id")
    if robust_id and (results / "M7" / robust_id / "robust_front.csv").exists():
        robust_front = pd.read_csv(results / "M7" / robust_id / "robust_front.csv")

    # the ACTUAL nominal front: the feasible non-dominated set of the M4 run this study
    # took its designs from, with the objective values M4 logged
    nominal_front = None
    m4_dir = results / "M4" / str(summary.get("m4_run_id") or "")
    if summary.get("m4_run_id") and (m4_dir / "candidates.csv").exists():
        nominal_front = feasible_front(load_candidates(m4_dir / "candidates.csv"),
                                       objectives).reset_index(drop=True)
        # is "as M4 logged them" the same physics as this run? measured, not assumed:
        # the §39 rows carry both M4's stored value and this run's re-evaluation
        diffs = [abs(row["metrics"][n] - row["stored_metrics"][n]) / abs(row["stored_metrics"][n])
                 for row in (summary.get("comparison") or {}).get("rows", [])
                 if row.get("available") and row.get("source") == "m4_selected"
                 for n in objectives if row.get("stored_metrics", {}).get(n)]
        summary.setdefault("nominal_front_consistency", {
            "m4_run_id": summary["m4_run_id"], "n_front_designs": int(len(nominal_front)),
            "n_values_compared": len(diffs),
            "max_abs_relative_difference": float(max(diffs)) if diffs else None,
            "basis": "objectives of the m4_selected §39 rows: this run's re-evaluation vs "
                     "the value M4 stored"})

    for label, block in summary.get("propagation", {}).items():
        conv = block.get("convergence") or {}
        if conv.get("table") and "cluster_bootstrap" not in conv \
                and label in frames and label in branches:
            conv["cluster_bootstrap"] = cluster_convergence(
                frames[label][conv["output"]].to_numpy(dtype=float), branches[label],
                float(conv["tolerance_rel"]), confidence=confidence)

    if "achieved_throughput" not in summary and summary.get("wall_s"):
        summary["achieved_throughput"] = achieved_throughput(
            n_evaluations=int(summary["n_evaluations"]), wall_s=float(summary["wall_s"]),
            workers=int(summary["workers"]),
            seconds_per_evaluation=(summary.get("sizing") or {}).get(
                "measured_seconds_per_evaluation"))

    # a like-for-like propagation of the robust knee on THIS run's draws, if one exists
    # (scripts/run_m7_robust_likeforlike.py). The newest one that names this run is used.
    for lfl_path in sorted((results / "M7").glob("M7-LFL-*/likeforlike.json"), reverse=True):
        lfl = json.loads(lfl_path.read_text())
        if lfl.get("parent_run") != summary["run_id"] \
                or not lfl["evaluator_equivalence"]["passed"]:
            continue
        block = {k: v for k, v in lfl.items() if k != "propagation"}
        block["violations"] = lfl["propagation"]["violations"]
        block["convergence"] = lfl["propagation"].get("convergence", {})
        paired = lfl_path.parent / "paired_difference.json"
        if paired.exists():
            block["paired"] = json.loads(paired.read_text())["pairs"]
        summary["robust_likeforlike"] = block
        break
    return nominal_front, robust_front


def _load_frames(out_dir: Path, summary: dict):
    """Re-read a finished run's per-design sample frames for --report-only."""
    from src.aether.optimization import load_candidates

    frame = load_candidates(out_dir / "candidates.csv")
    frames, branches = {}, {}
    draws_path = out_dir / "draws.csv"
    draw_table = pd.read_csv(draws_path) if draws_path.exists() else None
    for label in summary.get("propagation", {}):
        sub = frame[frame["method"] == f"propagate:{label}"]
        if sub.empty:
            continue
        frames[label] = sub.reset_index(drop=True)
        if draw_table is not None and len(draw_table) == len(sub):
            branches[label] = draw_table["epistemic_branch"].to_numpy()
    return frames, branches


if __name__ == "__main__":
    raise SystemExit(main())
