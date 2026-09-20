#!/usr/bin/env python3
"""Milestone M3: coupled-model gate G5, constant-C_D vs CFD-surface comparison, and report.

    run_m3_coupled.py --dp-run M3-DP-...          # study + figures + report
    run_m3_coupled.py --dp-run M3-DP-... --report-only

Needs data/aero/cfd_surface_v1/ (`make aero-surface`). About a minute; no OpenFOAM.
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from aether.aerodynamics import plots
from aether.studies import m3_coupled, m3_report
from aether.utils.run import REPO_ROOT, RunMeta, config_hash, load_config, snapshot_config


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(REPO_ROOT / "configs" / "aero_surface.yaml"))
    ap.add_argument("--dp-run", required=True, help="the M3-DP-* design-point run")
    ap.add_argument("--level", default=None)
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    dp_cfg = load_config(REPO_ROOT / cfg["design_points_config"])
    level = args.level or dp_cfg["production_level"]
    dp_dir = REPO_ROOT / "results" / "M3" / args.dp_run
    run_dir = dp_dir / "coupled"
    if not args.report_only:
        meta = RunMeta(run_id=f"{args.dp_run}/coupled", config_hash=config_hash(cfg),
                       notes="M3 coupled gate G5; gate_G4_status_at_build=IN_PROGRESS")
        snapshot_config(cfg, run_dir, meta)
        inclusive = dp_dir / f"surface_{level}_inclusive"
        m3_coupled.run_study(cfg, run_dir, progress=lambda m: print(m, flush=True),
                             inclusive_surface_dir=inclusive if inclusive.exists() else None)
    summary = json.loads((run_dir / "summary.json").read_text())
    figs = REPO_ROOT / "reports" / "figures"
    plots.plot_constant_vs_surface(summary, args.dp_run, figs)
    plots.plot_shape_sweep(pd.read_csv(run_dir / "shape_sweep.csv"), args.dp_run, figs)
    out = m3_report.write_report(dp_dir, level, cfg, dp_cfg)
    print(f"report: {out.relative_to(REPO_ROOT)}")
    print(json.dumps(summary["gate_G5"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
