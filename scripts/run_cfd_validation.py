#!/usr/bin/env python3
"""Milestone M2 driver: sphere benchmark, mesh independence, pipeline demo, gate G4.

Thin CLI only - all logic lives in src/aether/cfd/.

    run_cfd_validation.py                     # everything, new run ID
    run_cfd_validation.py --run-id M2-...     # resume: finished cases are loaded, not re-run
    run_cfd_validation.py --stage report      # rebuild tables, figures and report only

Solver runs take minutes to hours; launch this in the background.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.cfd import validation as val  # noqa: E402
from src.aether.cfd.report import build_report  # noqa: E402
from src.aether.cfd.runner import openfoam_available, openfoam_version  # noqa: E402
from src.aether.utils.run import (  # noqa: E402
    RunMeta,
    config_hash,
    load_config,
    new_run_id,
    snapshot_config,
)

STAGES = ("benchmark", "negative", "demo", "report")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(ROOT / "configs" / "cfd_validation.yaml"))
    ap.add_argument("--run-id", default=None, help="resume an existing run")
    ap.add_argument("--stage", choices=STAGES + ("all",), default="all")
    args = ap.parse_args()

    cfg = load_config(args.config)
    run_id = args.run_id or new_run_id("M2")
    run_dir = ROOT / "results" / "M2" / run_id
    generated = ROOT / "cfd" / "generated"
    stages = STAGES if args.stage == "all" else (args.stage,)

    if not (run_dir / "config_snapshot.yaml").exists():
        meta = RunMeta(run_id=run_id, config_hash=config_hash(cfg),
                       notes=f"M2 CFD validation; OpenFOAM {openfoam_version()}")
        snapshot_config(cfg, run_dir, meta)
    print(f"AETHER M2 CFD validation   run={run_id}   OpenFOAM={openfoam_version()}", flush=True)

    needs_solver = set(stages) & {"benchmark", "negative", "demo"}
    if needs_solver and not openfoam_available():
        print("OpenFOAM launcher not found - cannot run solver stages.", file=sys.stderr)
        return 2

    if "benchmark" in stages:
        study = val.run_mesh_study(cfg, run_id, run_dir, generated)
        print(study[["case", "status", "n_cells", "solver_wall_time_s", "cd_total",
                     "standoff_over_max_radius", "p_stag_over_p_inf"]].to_string(), flush=True)
    if "negative" in stages:
        neg = val.run_negative_cases(cfg, run_id, run_dir, generated)
        print(neg[["case", "status", "cd_total_converged"]].to_string(), flush=True)
    if "demo" in stages:
        demo = val.run_pipeline_demo(cfg, run_id, run_dir, generated)
        print(demo[["case", "status", "cd_total", "outlet_min_mach"]].to_string(), flush=True)

    if "report" in stages:
        gate = build_report(cfg, run_id, run_dir, generated / run_id, ROOT)
        print(f"\nG4 status: {gate['status']}")
        for name, c in gate["conditions"].items():
            print(f"  {'MET    ' if c['met'] else 'NOT MET'}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
