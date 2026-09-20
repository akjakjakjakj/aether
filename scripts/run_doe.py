#!/usr/bin/env python3
"""Milestone M4, part 1: design of experiments, global sensitivity, variable screening.

    python scripts/run_doe.py [--config configs/design_space.yaml] [--workers N]

Writes:
    results/M4/<run_id>/candidates.csv|.parquet  every evaluated design, invalid included
    results/M4/<run_id>/summary.json             every number the report quotes
    results/M4/<run_id>/screening.json           which variables `make optimize` will free
    results/M4/<run_id>/config_snapshot.yaml     immutable provenance
    reports/figures/M4_doe_*.png / .pdf
    reports/milestones/M4_pareto_optimisation.md (DOE sections; `make optimize` completes it)

Takes a few minutes on six cores - run it in the background.
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

from src.aether.optimization import CandidateStore, load_design_space  # noqa: E402
from src.aether.optimization.plots import plot_doe_figures  # noqa: E402
from src.aether.optimization.report import write_m4_report  # noqa: E402
from src.aether.studies.doe import (  # noqa: E402
    lhs_sensitivity,
    oat_effects,
    run_lhs,
    run_oat,
    run_sobol,
    screen_variables,
    sobol_table,
)
from src.aether.utils.run import RunMeta, config_hash, new_run_id, snapshot_config  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/design_space.yaml")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--report-only", default=None, metavar="RUN_ID",
                    help="re-analyse an existing run's candidate log: no evaluations, "
                         "analysis settings and design space read from its config snapshot")
    args = ap.parse_args()
    if args.report_only:
        return reanalyse(args.report_only)

    space, cfg = load_design_space(ROOT / args.config)
    doe = cfg["doe"]
    workers = int(args.workers or doe["workers"])
    seed = int(doe["seed"])

    run_id = new_run_id("M4-DOE")
    out_dir = ROOT / "results" / "M4" / run_id
    snapshot = {"study": cfg, "base": space.base_config}
    meta = RunMeta(run_id=run_id, config_hash=config_hash(snapshot),
                   notes="M4 DOE / sensitivity / screening")
    snapshot_config(snapshot, out_dir, meta)
    store = CandidateStore(out_dir / "candidates.csv")
    sub_space = space.with_bounds(doe["sobol"].get("sub_box") or {})
    hull = f1_hull_preflight(space, sub_space, seed)     # raises BEFORE anything is spent
    if hull is not None:
        (out_dir / "f1_hull_coverage.json").write_text(json.dumps(hull, indent=2))
        full = hull["full_box"]
        print(f"  Fidelity-1 hull: {100 * full['fraction_of_box_valid_and_inside_hull']:.1f}% "
              f"of the shape box is a valid forebody inside the CFD hull "
              f"({100 * full['fraction_of_valid_shapes_inside_hull']:.1f}% of valid "
              "shapes); Saltelli sub-box verified inside it", flush=True)

    print(f"AETHER M4 DOE  run={run_id}  git={meta.git_commit}"
          f"{' (dirty)' if meta.git_dirty else ''}  workers={workers}")
    t_start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        oat, swept = run_oat(space, store, n_points=int(doe["oat"]["points_per_variable"]),
                             run_id=run_id, seed=seed, executor=pool)
        print(f"  one-at-a-time: {len(oat)} evaluations", flush=True)
        lhs = run_lhs(space, store, n_samples=int(doe["lhs"]["n_samples"]), run_id=run_id,
                      seed=seed, executor=pool)
        print(f"  Latin Hypercube: {len(lhs)} evaluations", flush=True)
        sob = run_sobol(sub_space, store, n_base=int(doe["sobol"]["n_base"]), run_id=run_id,
                        seed=seed, executor=pool)
        print(f"  Saltelli design: {len(sob)} evaluations", flush=True)
    wall_s = time.perf_counter() - t_start
    store.export_parquet()
    return analyse(space, sub_space, cfg, store.load(), swept, run_id, meta.git_commit,
                   meta.git_dirty, meta.config_hash, args.config, workers, wall_s, out_dir)


def f1_hull_preflight(space, sub_space, seed: int) -> dict | None:
    """At Fidelity 1 only: measure how much of the shape box the CFD hull leaves, and REFUSE
    to start if the Saltelli sub-box is not inside it (a Saltelli design cannot tolerate one
    rejected sample). None at Fidelity 0."""
    aero = space.base_config["vehicle"].get("aero", {}) or {}
    model = str(aero.get("model", "constant"))
    if not model.startswith("cfd_surface"):
        return None
    from src.aether.aerodynamics.cfd_surface import SHAPE_INPUTS, load_surface, surface_dir
    from src.aether.optimization.hull_coverage import check_box_inside_hull, coverage

    directory = ROOT / aero["surface_dir"] if aero.get("surface_dir") else surface_dir(model)
    surface = load_surface(directory)

    def bounds(sp):
        by_name = {v.name: v for v in sp.variables}
        return {k: (by_name[k].lower, by_name[k].upper) for k in SHAPE_INPUTS}

    full_b, sub_b = bounds(space), bounds(sub_space)
    full = coverage(surface, full_b, seed=seed)
    vol = float(np.prod([(sub_b[k][1] - sub_b[k][0]) / (full_b[k][1] - full_b[k][0])
                         for k in SHAPE_INPUTS]))
    return {"aero_model": model, "surface_training_hash": surface.meta["training_hash"],
            "sub_box_volume_fraction_of_shape_box": vol,
            "sub_box_volume_fraction_of_evaluable_region":
                vol / full["fraction_of_box_valid_and_inside_hull"],
            "full_box": full,
            "sobol_sub_box": {**coverage(surface, bounds(sub_space), n_samples=4096, seed=seed),
                              "preflight": check_box_inside_hull(surface, bounds(sub_space),
                                                                 seed=seed)}}


def reanalyse(run_id: str) -> int:
    """Rebuild summary, screening, figures and report from a finished run's log."""
    import yaml

    from src.aether.optimization import load_candidates
    from src.aether.optimization.design_space import DesignSpace
    from src.aether.optimization.sampling import one_at_a_time

    out_dir = ROOT / "results" / "M4" / run_id
    snap = yaml.safe_load((out_dir / "config_snapshot.yaml").read_text())
    old = json.loads((out_dir / "summary.json").read_text())
    cfg = snap["config"]["study"]
    space = DesignSpace.from_config(cfg, ROOT)
    sub_space = space.with_bounds(cfg["doe"]["sobol"].get("sub_box") or {})
    _, swept = one_at_a_time(space.n_active, int(cfg["doe"]["oat"]["points_per_variable"]),
                             np.zeros(space.n_active))
    return analyse(space, sub_space, cfg, load_candidates(out_dir / "candidates.csv"), swept,
                   run_id, snap["_meta"]["git_commit"], snap["_meta"]["git_dirty"],
                   snap["_meta"]["config_hash"], old["config_path"], old["workers"],
                   old["cost"]["total_wall_s"], out_dir)


def analyse(space, sub_space, cfg, everything, swept, run_id, git_commit, git_dirty,
            cfg_hash, config_path, workers, wall_s, out_dir) -> int:
    doe = cfg["doe"]
    seed = int(doe["seed"])
    outputs = list(doe["screening"]["outputs"])
    oat = everything[everything["method"] == "doe_oat"].reset_index(drop=True)
    lhs = everything[everything["method"] == "doe_lhs"].reset_index(drop=True)
    sob = everything[everything["method"] == "doe_sobol"].reset_index(drop=True)

    lhs_table = lhs_sensitivity(lhs, space, outputs, seed=seed,
                                n_bins=int(doe["lhs"]["given_data_bins"]))
    sobol = sobol_table(sob, sub_space, outputs, seed=seed,
                        n_bootstrap=int(doe["sobol"]["n_bootstrap"]),
                        confidence=float(doe["sobol"]["confidence"]))
    screening = screen_variables(space, sobol, lhs_table, doe["screening"])

    paid = everything[~everything["cache_hit"]]
    evaluated = paid[paid["status"] == "OK"]["wall_time_s"].to_numpy(dtype=float)
    summary = {
        "run_id": run_id, "git_commit": git_commit, "git_dirty": git_dirty,
        "config_hash": cfg_hash, "config_path": config_path,
        "fidelity": int(everything["fidelity"].max()),
        "aero_model": space.base_config["vehicle"]["aero"]["model"],
        "seed": seed, "workers": workers,
        "variables": {
            v.name: {"role": v.role, "units": v.units, "lower": v.lower, "upper": v.upper,
                     "reference": v.reference, "kind": v.kind}
            for v in space.variables
        },
        "sobol_sub_box": {v.name: [v.lower, v.upper] for v in sub_space.variables},
        "cost": {
            "n_evaluations_paid": int(len(paid)),
            "n_physics_evaluations": int(evaluated.size),
            "per_evaluation_wall_s": {
                "mean": float(evaluated.mean()), "median": float(np.median(evaluated)),
                "p95": float(np.percentile(evaluated, 95)), "max": float(evaluated.max()),
            },
            "total_wall_s": wall_s,
            "throughput_evaluations_per_s": float(len(paid) / wall_s),
        },
        "oat": oat_effects(oat, swept, space, outputs),
        "lhs": lhs_table,
        "sobol": sobol,
        "screening": screening,
        "limits": space.base_config["limits"],
        "f1_hull": (json.loads((out_dir / "f1_hull_coverage.json").read_text())
                    if (out_dir / "f1_hull_coverage.json").exists() else None),
    }
    with open(out_dir / "summary.json", "w") as fh:
        json.dump(summary, fh, indent=2, default=float)
    with open(out_dir / "screening.json", "w") as fh:
        json.dump({"doe_run_id": run_id, **screening}, fh, indent=2, default=float)

    names = [v.name for v in space.variables]
    figures = plot_doe_figures(summary, oat, swept, lhs, names, ROOT / "reports" / "figures")
    report = write_m4_report(ROOT, summary, None)

    print(f"\nper-evaluation wall time: median "
          f"{summary['cost']['per_evaluation_wall_s']['median']:.3f} s, "
          f"{summary['cost']['throughput_evaluations_per_s']:.1f} evaluations/s overall")
    print(f"active after screening: {screening['active']}")
    print(f"frozen:                 {screening['frozen']}")
    print(f"figures: {[p.name for p in figures]}")
    print(f"report -> {report}\nresults -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
