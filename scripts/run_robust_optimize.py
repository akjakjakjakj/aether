#!/usr/bin/env python3
"""Milestone M7, part 2: robust multi-objective optimisation (spec §28).

    python scripts/run_robust_optimize.py            full study
    python scripts/run_robust_optimize.py --smoke    tiny budget, proves the chain only

Re-optimises the design space against ROBUST objectives - the declared percentile of each
O1 objective - under chance constraints, with NSGA-II driven through the same
`BudgetedEvaluator` M4 and M5 use, so a robust evaluation is charged by the same meter as
any other.

The shortcut, and the check on it
----------------------------------
Full nested Monte Carlo is unaffordable, so each candidate is judged on a modest inner
sample under COMMON RANDOM NUMBERS - the same draws for every candidate, which removes
sampling noise from the comparison between designs and makes a re-proposed design a free
cache hit. That is an approximation, so when the front is finished a subset of it is
re-scored under full, independent Monte Carlo at a different seed and the measured bias,
rank correlation and violation-probability error are reported against tolerances declared
in `configs/uncertainty.yaml` before the run.

Writes:
    results/M7/<run_id>/candidates.csv|.parquet   every inner evaluation
    results/M7/<run_id>/robust_record.csv         every candidate's robust score
    results/M7/<run_id>/robust_front.csv          the chance-feasible non-dominated set
    results/M7/<run_id>/robust.json               settings, runs, front, verification
    results/M7/<run_id>/config_snapshot.yaml

Then run `make uncertainty` (or `scripts/run_uncertainty.py`) to fold this run into the
M7 report and the §39 comparison table.

Hours on six workers - run it in the background.
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

from src.aether.optimization import BudgetedEvaluator  # noqa: E402
from src.aether.uncertainty.driver import (  # noqa: E402
    active_vector,
    load_context,
    measure_evaluation_cost,
    size_study,
)
from src.aether.uncertainty.guards import GuardedStore  # noqa: E402
from src.aether.uncertainty.propagate import evaluate_under_uncertainty  # noqa: E402
from src.aether.uncertainty.robust import (  # noqa: E402
    RobustSettings,
    robust_front,
    run_robust_nsga2,
    score_sample,
    verify_shortcut,
)
from src.aether.uncertainty.sampling import common_random_numbers, make_draws  # noqa: E402
from src.aether.uncertainty.space import make_uncertain_space  # noqa: E402
from src.aether.utils.run import (  # noqa: E402
    RunMeta,
    config_hash,
    new_run_id,
    snapshot_config,
)

SMOKE_NOTE = (
    "# SMOKE RUN - NOT A RESULT\n\n"
    "Produced by `scripts/run_robust_optimize.py --smoke`, whose only purpose is to "
    "prove the robust chain executes end to end. The budget, population and inner "
    "sample are far too small for the front or the verification in it to mean anything. "
    "No number from this directory may be quoted. Delete it, or leave it labelled.\n"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/uncertainty.yaml")
    ap.add_argument("--doe-run", default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    ctx = load_context(ROOT, args.config, doe_run=args.doe_run,
                       strict_screening=not args.smoke,
                       aero_model=getattr(args, "aero_model", None))
    cfg = dict(ctx.study["robust"])
    if args.smoke:
        cfg.update(inner_samples=8, population_size=8, budget_evaluations=960,
                   seeds=[37])
        cfg["verification"] = {**cfg["verification"], "n_designs": 3,
                               "n_full_samples": 24}
    settings = RobustSettings.from_config(cfg)
    workers = int(args.workers or cfg.get("workers", 6))

    run_id = new_run_id("M7-SMOKE-ROBUST" if args.smoke else "M7-ROBUST")
    out_dir = ROOT / "results" / "M7" / run_id
    snapshot = {"study": ctx.study, "design_space": ctx.design_space_config,
                "base": ctx.space.base_config, "screening": ctx.screening,
                "robust": cfg, "smoke": bool(args.smoke)}
    meta = RunMeta(run_id=run_id, config_hash=config_hash(snapshot),
                   notes=("M7 SMOKE robust - not a result" if args.smoke
                          else "M7 robust optimisation"))
    snapshot_config(snapshot, out_dir, meta)
    if args.smoke:
        (out_dir / "SMOKE.md").write_text(SMOKE_NOTE)

    store = GuardedStore(out_dir / "candidates.csv", ROOT / "src" / "aether", out_dir)
    model = ctx.model
    inner_unit = common_random_numbers(model.n_inputs, settings.inner_samples,
                                       settings.inner_seed)
    uspace = make_uncertain_space(ctx.space, model, inner_unit)
    inner_indices = np.arange(settings.inner_samples)

    print(f"AETHER M7 robust  run={run_id}  git={meta.git_commit}"
          f"{' (dirty)' if meta.git_dirty else ''}  workers={workers}")
    print(f"evaluator source hash at launch: {store.launch_hash}")
    print(f"active variables: {list(ctx.space.active)}")
    print(f"robust objectives: {settings.objective_percentile:g}th percentile of "
          f"{list(ctx.objectives)}  ({settings.quantile_estimator} estimator)")
    print(f"inner sample: {settings.inner_samples} draws, common random numbers, "
          f"seed {settings.inner_seed}")
    print("chance constraints (as the inner sample can actually express them):")
    for name, rule in settings.effective_chance_rule.items():
        print(f"    P({name}) <= {settings.chance_alpha[name]:g}  ->  {rule}")
    sys.stdout.flush()

    measured = measure_evaluation_cost(ctx)
    n_robust = settings.budget_evaluations * len(settings.seeds)
    n_verify = int(cfg["verification"]["n_designs"]) * \
        int(cfg["verification"]["n_full_samples"])
    sizing = size_study(ctx, seconds_per_evaluation=measured, workers=workers,
                        efficiency=float(ctx.study["sizing"].get("parallel_efficiency",
                                                                0.8)),
                        counts={"robust": n_robust, "verification": n_verify,
                                "propagation": 0, "attribution": 0, "comparison": 0})
    print(f"projected: {sizing['total_evaluations']:,} evaluations, "
          f"~{sizing['total_seconds'] / 60:.1f} min at "
          f"{sizing['projected_evaluations_per_second']:.1f} eval/s (a projection from "
          "the declared parallel efficiency, not a measurement)", flush=True)

    record: list[dict] = []
    runs: list[dict] = []
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for seed in settings.seeds:
            store.check(f"before robust seed {seed}")
            evaluator = BudgetedEvaluator(uspace, settings.budget_evaluations, store,
                                          run_id=run_id, method="robust_nsga2",
                                          seed=int(seed), executor=pool)
            seed_record: list[dict] = []
            info = run_robust_nsga2(evaluator, uspace, ctx.objectives, settings,
                                    inner_indices=inner_indices, record=seed_record)
            record.extend(seed_record)
            front = robust_front(seed_record, ctx.objectives)
            info.update(seed=int(seed), front_size=int(len(front)))
            runs.append(info)
            print(f"  seed {seed:>3}: {info['generations']} generations, "
                  f"{info['budget_used']:,} paid, {info['cache_hits']:,} cache hits, "
                  f"front {len(front)} ({time.perf_counter() - start:.0f} s)", flush=True)

        combined = robust_front(record, ctx.objectives)
        print(f"  combined chance-feasible front: {len(combined)} designs", flush=True)

        store.check("before shortcut verification")
        verification = _verify(ctx, cfg, settings, combined, store, run_id, pool,
                              inner_indices, uspace)
    wall = time.perf_counter() - start
    store.check("after the robust study")

    store.export_parquet()
    pd.DataFrame(record).to_csv(out_dir / "robust_record.csv", index=False)
    combined.to_csv(out_dir / "robust_front.csv", index=False)

    block = {
        "run_id": run_id, "git_commit": meta.git_commit, "git_dirty": meta.git_dirty,
        "source_hash": store.launch_hash, "workers": workers, "wall_s": wall,
        "smoke": bool(args.smoke),
        "settings": settings.to_dict(),
        "runs": runs,
        "n_candidates": int(len(record)),
        "front_size": int(len(combined)),
        "verification": verification,
    }
    (out_dir / "robust.json").write_text(json.dumps(block, indent=2, default=float))

    print()
    if verification:
        for name, stats in verification["objectives"].items():
            print(f"  shortcut vs full MC  {name:<30} bias "
                  f"{stats['mean_relative_bias'] * 100:+.2f}%  Spearman "
                  f"{stats['spearman_rank_correlation']:.3f}")
        print(f"  verification verdict: "
              f"{'PASSED' if verification['verdict']['passed'] else 'FAILED'}")
        for failure in verification["verdict"]["failures"]:
            print(f"    - {failure}")
    print(f"\nresults -> {out_dir}")
    print("next: `make uncertainty` folds this run into the M7 report and the §39 table")
    if args.smoke:
        print(f"\nSMOKE RUN: no number above is a result. See "
              f"{out_dir.relative_to(ROOT)}/SMOKE.md")
    return 0


def _verify(ctx, cfg, settings, front, store, run_id, pool, inner_indices, uspace):
    """Re-score a subset of the finished front under full, independent Monte Carlo."""
    vcfg = cfg["verification"]
    n_designs = int(vcfg["n_designs"])
    n_full = int(vcfg["n_full_samples"])
    if front.empty:
        return {}
    picks = np.unique(np.linspace(0, len(front) - 1, min(n_designs, len(front)))
                      .astype(int))
    model = ctx.model
    full_draws = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                            model.indices_of_kind("epistemic"), mode="mixed",
                            seed=int(vcfg["full_seed"]), n_aleatory=n_full)
    full_space = make_uncertain_space(ctx.space, model, full_draws.unit)
    full_indices = np.arange(n_full)

    shortcut_scores, full_scores, labels = [], [], []
    for i, index in enumerate(picks):
        row = front.iloc[int(index)]
        values = {v.name: float(row[f"x__{v.name}"]) if f"x__{v.name}" in row
                  else v.reference for v in ctx.space.variables}
        x = active_vector(ctx, values)
        short_eval = BudgetedEvaluator(uspace, settings.inner_samples, store,
                                       run_id=run_id, method=f"verify_shortcut:{i}",
                                       seed=settings.inner_seed, executor=pool)
        short_frame = evaluate_under_uncertainty(short_eval, uspace, x, inner_indices,
                                                 generation=200 + i)
        full_eval = BudgetedEvaluator(full_space, n_full, store, run_id=run_id,
                                      method=f"verify_full:{i}",
                                      seed=int(vcfg["full_seed"]), executor=pool)
        full_frame = evaluate_under_uncertainty(full_eval, full_space, x, full_indices,
                                                generation=300 + i)
        if len(short_frame) < settings.inner_samples or len(full_frame) < n_full:
            continue
        shortcut_scores.append(score_sample(short_frame, ctx.objectives, settings))
        full_scores.append(score_sample(full_frame, ctx.objectives, settings))
        labels.append(str(row["candidate_id"]))
    if not labels:
        return {}
    return verify_shortcut(shortcut_scores, full_scores, ctx.objectives, settings,
                           labels=labels, n_full=n_full,
                           full_seed=int(vcfg["full_seed"]),
                           tolerances={k: float(v) for k, v in
                                       vcfg["tolerances"].items()}).to_dict()


if __name__ == "__main__":
    raise SystemExit(main())
