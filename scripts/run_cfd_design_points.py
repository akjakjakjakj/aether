#!/usr/bin/env python3
"""Milestone M3 driver: run the CFD design points for the drag response surface.

Thin CLI - all logic lives in src/aether/cfd/design_points.py.

    run_cfd_design_points.py                          # production level, new run ID
    run_cfd_design_points.py --run-id M3-DP-...       # resume: finished cases are loaded
    run_cfd_design_points.py --run-id ... --level medium --subset mesh-check
    run_cfd_design_points.py --plan-only              # write the design tables, run nothing

Takes HOURS. Launch it in the background.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.cfd import design_points as dp  # noqa: E402
from src.aether.cfd.runner import openfoam_available, openfoam_version  # noqa: E402
from src.aether.utils.run import (  # noqa: E402
    RunMeta,
    config_hash,
    load_config,
    new_run_id,
    snapshot_config,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(ROOT / "configs" / "cfd_design_points.yaml"))
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--level", choices=sorted(dp.LEVELS), default=None)
    ap.add_argument("--subset", choices=("all", "mesh-check"), default="all")
    ap.add_argument("--only", nargs="*", default=None, help="explicit point IDs")
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    level = args.level or cfg["production_level"]
    run_id = args.run_id or new_run_id("M3-DP")
    run_dir = ROOT / "results" / "M3" / run_id
    generated = ROOT / "cfd" / "generated" / run_id
    if not (run_dir / "config_snapshot.yaml").exists():
        meta = RunMeta(run_id=run_id, config_hash=config_hash(cfg),
                       notes=f"M3 CFD design points; OpenFOAM {openfoam_version()}; "
                             f"gate_G4_status_at_build={dp.GATE_G4_STATUS_AT_BUILD}")
        snapshot_config(cfg, run_dir, meta)
    points, skipped = dp.build_design(cfg)
    print(f"AETHER M3 design points  run={run_id}  level={level}  OpenFOAM={openfoam_version()}"
          f"  planned={len(points)}  skipped_invalid={len(skipped)}", flush=True)
    only = args.only
    if only is None and args.subset == "mesh-check":
        only = dp.mesh_check_ids(cfg, points)
        print("mesh-check subset:", " ".join(only), flush=True)
    if args.plan_only:
        run_dir.mkdir(parents=True, exist_ok=True)
        skipped.to_csv(run_dir / "design_skipped.csv", index=False)
        pd.DataFrame([asdict(p) for p in points]).to_csv(run_dir / "design_planned.csv",
                                                         index=False)
        return 0
    if not openfoam_available():
        print("OpenFOAM launcher not found - cannot run design points.", file=sys.stderr)
        return 2

    t0 = time.perf_counter()
    table = dp.run_design(cfg, run_dir, generated, level, only=only,
                          progress=lambda m: print(m, flush=True))
    wall = time.perf_counter() - t0
    summary = {
        "run_id": run_id, "mesh_level": level, "subset": args.subset,
        "gate_G4_status_at_build": dp.GATE_G4_STATUS_AT_BUILD,
        "openfoam_version": openfoam_version(),
        "n_planned": len(points), "n_skipped_invalid_geometry": int(len(skipped)),
        "n_run": int(len(table)),
        "verdicts": table["verdict"].value_counts().to_dict() if len(table) else {},
        "driver_wall_time_s_this_invocation": wall,
        "sum_case_wall_time_s": float(table["total_wall_time_s"].sum()) if len(table) else 0.0,
        "max_concurrent_cases": int(cfg["execution"]["max_concurrent_cases"]),
        "scale_check": dp.scale_check(table, cfg) if len(table) else {},
    }
    (run_dir / f"summary_{level}.json").write_text(json.dumps(summary, indent=2, default=str))
    # One line per invocation: a resumed run must not erase the wall time of the first one.
    with open(run_dir / f"invocations_{level}.jsonl", "a") as fh:
        fh.write(json.dumps({"subset": args.subset, "only": only, "n_rows": int(len(table)),
                             "driver_wall_time_s": wall}, default=str) + "\n")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
