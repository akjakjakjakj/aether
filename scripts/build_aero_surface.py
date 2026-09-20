#!/usr/bin/env python3
"""Milestone M3: fit, cross-validate and persist the CFD drag surface `cfd_surface_v1`.

    build_aero_surface.py --run-id M3-DP-...            # production mesh level of the config
    build_aero_surface.py --run-id M3-DP-... --level medium

Reads results/M3/<run>/design_points_<level>.csv. Writes the surface to
data/aero/cfd_surface_v1/ (what `vehicle.aero.model: cfd_surface_v1` loads) and the
validation tables + figures next to the run. Seconds, no OpenFOAM needed.
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from aether.aerodynamics import plots
from aether.aerodynamics.cfd_surface import SHAPE_INPUTS, CfdDragSurface
from aether.aerodynamics.surface_build import build
from aether.utils.run import REPO_ROOT, load_config


def latest_run() -> str:
    runs = sorted(p.name for p in (REPO_ROOT / "results" / "M3").glob("M3-DP-*") if p.is_dir())
    if not runs:
        raise SystemExit("no results/M3/M3-DP-* run found; run `make cfd-design-points` first")
    return runs[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(REPO_ROOT / "configs" / "aero_surface.yaml"))
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--level", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    dp_cfg = load_config(REPO_ROOT / cfg["design_points_config"])
    run_id = args.run_id or latest_run()
    level = args.level or dp_cfg["production_level"]
    run_dir = REPO_ROOT / "results" / "M3" / run_id

    summary = build(run_dir, dp_cfg, cfg["surface"], level)
    surface = CfdDragSurface.load(run_dir / f"surface_{level}")
    table = pd.read_csv(run_dir / f"design_points_{level}.csv")
    skipped = pd.read_csv(run_dir / "design_skipped.csv")
    shapes = {str(s["name"]): {k: float(s[k]) for k in SHAPE_INPUTS}
              for s in cfg["surface"]["report_shapes"]}
    figs = REPO_ROOT / "reports" / "figures"
    plots.plot_design_coverage(table, skipped, run_id, level, figs)
    plots.plot_cd_vs_mach(surface, shapes, table, run_id, figs)
    plots.plot_cv_parity(pd.read_csv(run_dir / f"surface_cv_predictions_{level}.csv"),
                         run_id, figs)
    plots.plot_base_fraction(pd.read_csv(run_dir / f"base_drag_fraction_{level}.csv"),
                             run_id, figs)
    print(json.dumps({k: summary[k] for k in ("run_id", "mesh_level", "n_usable", "verdicts",
                                              "training_hash", "holdout", "k_fold",
                                              "mesh_check", "discretisation_band_hook")},
                     indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
