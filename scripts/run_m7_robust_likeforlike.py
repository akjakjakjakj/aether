#!/usr/bin/env python3
"""M7 follow-up (NR-34 item 8): propagate the ROBUST KNEE through the parent run's draws.

    python scripts/run_m7_robust_likeforlike.py M7-UQ-<parent run id> [--workers N]

The §39 table of a `make uncertainty` run gives three rows a 3000-draw NESTED propagation
and the robust row a 500-draw MIXED one on another seed, because the robust design is not
in the propagation list. The rows are then not like-for-like and the robust design cannot
be paired with the others draw for draw. This script closes that gap and nothing else.

WHAT IT IS: a propagation of ONE design (the robust knee the parent's §39 table already
reports), through the SAME draw set - same mode, branch count, draw count and seed - as the
parent's other designs. About 3000 coupled evaluations.
WHAT IT IS NOT: a re-run of the study. No optimiser runs, no other design is evaluated
beyond the equivalence check below, and the parent run's files are not written to.

It REFUSES unless all of these hold, and records each in `likeforlike.json`:
  1. today's configs hash to the parent's recorded `config_hash` (same study, design space,
     base physics config, screening and robust run);
  2. the robust-knee design vector it resolves equals the one in the parent's §39 row;
  3. the draw set it regenerates equals the parent's `draws.csv`, value for value;
  4. EVALUATOR EQUIVALENCE: `src/aether` has been edited since the parent ran (report and
     plotting code), so the source hash differs. A declared subset of the parent's own
     evaluations of `joint_knee` is therefore re-run here and must reproduce the parent's
     logged outputs. If it does not, today's evaluator is not the parent's and the new
     column would not be comparable: the run stops and says so.

Writes results/M7/M7-LFL-<stamp>/: candidates.csv, config_snapshot.yaml, likeforlike.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.optimization import BudgetedEvaluator, load_candidates  # noqa: E402
from src.aether.uncertainty import comparison as cmp_mod  # noqa: E402
from src.aether.uncertainty.driver import (  # noqa: E402
    achieved_throughput,
    active_vector,
    load_context,
    resolve_designs,
    run_propagation,
)
from src.aether.uncertainty.guards import GuardedStore  # noqa: E402
from src.aether.uncertainty.propagate import evaluate_under_uncertainty  # noqa: E402
from src.aether.uncertainty.sampling import make_draws  # noqa: E402
from src.aether.uncertainty.space import make_uncertain_space  # noqa: E402
from src.aether.utils.run import RunMeta, config_hash, new_run_id, snapshot_config  # noqa: E402

LABEL = "robust_knee"
CHECK_DESIGN = "joint_knee"
CHECK_EVERY = 25            # every 25th draw of the parent's joint_knee: 120 evaluations
CHECK_COLUMNS = ("peak_heat_flux_w_m2", "peak_bondline_temperature_k", "max_g",
                 "margin__heatshield_mass_fraction")
CHECK_RTOL = 1e-12


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("parent", metavar="M7-UQ-RUN_ID")
    ap.add_argument("--config", default="configs/uncertainty.yaml")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    results = ROOT / "results" / "M7"
    parent_dir = results / args.parent
    parent = json.loads((parent_dir / "summary.json").read_text())
    if parent.get("smoke"):
        raise SystemExit("the parent is a smoke run; nothing about it is a result")
    robust_id = parent["robust"]["run_id"]
    robust_front = pd.read_csv(results / robust_id / "robust_front.csv")

    ctx = load_context(ROOT, args.config, doe_run=parent["doe_run_id"])
    # 1. same configuration as the parent, by the parent's own hash recipe
    parent_recipe = {"study": ctx.study, "design_space": ctx.design_space_config,
                     "base": ctx.space.base_config, "screening": ctx.screening,
                     "smoke": False, "robust_run": robust_id}
    if config_hash(parent_recipe) != parent["config_hash"]:
        raise SystemExit(f"REFUSING: today's configuration hashes to "
                         f"{config_hash(parent_recipe)}, the parent recorded "
                         f"{parent['config_hash']}. The draws and the physics config would "
                         "not be the parent's.")
    if ctx.m4_run_id != parent["m4_run_id"]:
        raise SystemExit(f"REFUSING: latest M4 run is {ctx.m4_run_id}, the parent used "
                         f"{parent['m4_run_id']}")

    # 2. the design the parent's §39 table reports, resolved the way the parent did
    spec = next(r for r in ctx.study["comparison"]["rows"] if r["source"] == "m7_robust")
    designs = resolve_designs(ctx, [{**spec, "label": LABEL}], robust_front=robust_front,
                              robust_run_id=robust_id)
    values = designs[LABEL]["values"]
    parent_row = next(r for r in parent["comparison"]["rows"] if r["source"] == "m7_robust")
    mismatch = {k: (values[k], v) for k, v in parent_row["design_values"].items()
                if values.get(k) != v}
    if mismatch or set(values) != set(parent_row["design_values"]):
        raise SystemExit(f"REFUSING: resolved robust knee differs from the parent's §39 row: "
                         f"{mismatch}")

    # 3. the parent's draw set, regenerated and compared value for value
    prop = ctx.study["propagation"]
    draws = make_draws(ctx.model.n_inputs, ctx.model.indices_of_kind("aleatory"),
                       ctx.model.indices_of_kind("epistemic"), mode=str(prop["mode"]),
                       seed=int(prop["seed"]), n_aleatory=int(prop["aleatory_samples"]),
                       n_epistemic_branches=int(prop["epistemic_branches"]))
    parent_draws = pd.read_csv(parent_dir / "draws.csv")
    parent_unit = parent_draws[[f"u__{n}" for n in ctx.model.names]].to_numpy(dtype=float)
    max_draw_diff = float(np.max(np.abs(parent_unit - draws.unit)))
    same_branches = bool(np.array_equal(parent_draws["epistemic_branch"].to_numpy(),
                                        draws.epistemic_index))
    if max_draw_diff > 1e-15 or not same_branches:
        raise SystemExit(f"REFUSING: regenerated draws differ from the parent's draws.csv "
                         f"(max |du| {max_draw_diff:.3g}, branches equal: {same_branches})")

    run_id = new_run_id("M7-LFL")
    out_dir = results / run_id
    snapshot = {**parent_recipe, "likeforlike_parent": args.parent, "design_label": LABEL}
    meta = RunMeta(run_id=run_id, config_hash=config_hash(snapshot),
                   notes=f"M7 like-for-like propagation of the robust knee on the draws of "
                         f"{args.parent} (NR-34 item 8). One design; not a study re-run.")
    snapshot_config(snapshot, out_dir, meta)
    store = GuardedStore(out_dir / "candidates.csv", ROOT / "src" / "aether", out_dir)
    print(f"AETHER M7 like-for-like  run={run_id}  parent={args.parent}  robust={robust_id}")
    print(f"source hash now {store.launch_hash}, parent {parent['source_hash']}", flush=True)

    parent_frame = load_candidates(parent_dir / "candidates.csv")
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        # 4. evaluator equivalence on the parent's own evaluations
        subset = np.arange(0, len(draws), CHECK_EVERY)
        uspace = make_uncertain_space(ctx.space, ctx.model, draws.unit)
        check_values = resolve_designs(
            ctx, [d for d in prop["designs"] if d["label"] == CHECK_DESIGN],
            robust_front=robust_front, robust_run_id=robust_id)[CHECK_DESIGN]["values"]
        evaluator = BudgetedEvaluator(uspace, len(subset), store, run_id=run_id,
                                      method=f"equivalence:{CHECK_DESIGN}",
                                      seed=int(prop["seed"]), executor=pool)
        redo = evaluate_under_uncertainty(evaluator, uspace, active_vector(ctx, check_values),
                                          subset, generation=0)
        ref = parent_frame[parent_frame["method"] == f"propagate:{CHECK_DESIGN}"]
        ref = ref.set_index(ref["x___uq_draw"].astype(int)).loc[subset]
        redo = redo.set_index(redo["x___uq_draw"].astype(int)).loc[subset]
        worst = {}
        for col in CHECK_COLUMNS:
            a, b = redo[col].to_numpy(dtype=float), ref[col].to_numpy(dtype=float)
            worst[col] = float(np.nanmax(np.abs(a - b) / np.maximum(np.abs(b), 1e-300)))
        feasible_same = bool(np.array_equal(redo["feasible"].to_numpy(dtype=bool),
                                            ref["feasible"].to_numpy(dtype=bool)))
        equivalence = {"design": CHECK_DESIGN, "draw_indices": f"0::{CHECK_EVERY}",
                       "n_evaluations": int(len(subset)), "rtol_required": CHECK_RTOL,
                       "max_relative_difference": worst,
                       "feasibility_identical": feasible_same,
                       "passed": bool(feasible_same and max(worst.values()) <= CHECK_RTOL)}
        print(f"equivalence check: {equivalence}", flush=True)
        if not equivalence["passed"]:
            (out_dir / "ABORTED.md").write_text(
                "# ABORTED - DO NOT ANALYSE\n\nToday's evaluator did not reproduce the "
                f"parent run's logged evaluations: {json.dumps(equivalence)}\n")
            raise SystemExit("REFUSING: evaluator equivalence check failed; see ABORTED.md")

        store.check("before the robust-knee propagation")
        propagations, used = run_propagation(
            ctx, {LABEL: designs[LABEL]}, store=store, run_id=run_id, executor=pool,
            n_aleatory=int(prop["aleatory_samples"]),
            n_epistemic=int(prop["epistemic_branches"]), mode=str(prop["mode"]),
            seed=int(prop["seed"]), outputs=tuple(prop["outputs"]),
            percentiles=tuple(float(p) for p in prop["percentiles"]),
            confidence=float(prop["confidence"]), convergence=prop["convergence"])
    wall = time.perf_counter() - start
    store.check("after the propagation")
    store.export_parquet()
    assert np.array_equal(used.unit, draws.unit)

    block = propagations[LABEL]
    result = block["result"]
    payload = result.to_dict()
    payload["nominal_feasible"] = bool(block["nominal_row"]["feasible"])
    payload["nominal_status"] = str(block["nominal_row"]["status"])
    frame = store.load()
    n_paid = int((~frame["cache_hit"]).sum())
    out = {
        "run_id": run_id, "parent_run": args.parent, "robust_run": robust_id,
        "label": LABEL, "comparison_row": parent_row["label"],
        "what_this_is": "propagation of ONE design through the parent's nested draw set; "
                        "not a study re-run; the parent's files are untouched",
        "git_commit": meta.git_commit, "git_dirty": meta.git_dirty,
        "config_hash": meta.config_hash, "source_hash": store.launch_hash,
        "parent_source_hash": parent["source_hash"],
        "parent_config_hash_reproduced": True,
        "design_values": {k: float(v) for k, v in values.items()},
        "draws": {**used.to_dict(), "max_abs_difference_vs_parent_draws_csv": max_draw_diff,
                  "epistemic_branches_identical": same_branches},
        "evaluator_equivalence": equivalence,
        "workers": args.workers, "wall_s": wall, "n_evaluations": n_paid,
        "achieved_throughput": achieved_throughput(
            n_evaluations=n_paid, wall_s=wall, workers=args.workers,
            seconds_per_evaluation=None),
        "propagation": payload,
        "uncertainty_cell": cmp_mod.uncertainty_cell(result, ctx.objectives),
    }
    (out_dir / "likeforlike.json").write_text(json.dumps(out, indent=2, default=float))
    anyv = out["uncertainty_cell"]["violation_probability"]["any"]
    print(f"\n{LABEL}: n = {payload['n_samples']}, P(any violation) {anyv['phrase']}")
    for name in ctx.objectives:
        c = payload["combined"][name]
        print(f"  {name:<30} mean {c['mean']:.6g}  p95 {c['percentiles']['p95']:.6g}")
    print(f"{n_paid} evaluations in {wall:.0f} s\nresults -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
