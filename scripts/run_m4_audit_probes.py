#!/usr/bin/env python3
"""M4 metric-gaming audit, part 2: PROBES around the selected front designs.

The audit in `run_optimize.py` reads the candidate log. This script asks two counterfactual
questions the log cannot answer, by evaluating a handful of LABELLED probe designs through the
canonical evaluator. Probes are never candidates: they enter no front, no hypervolume and no
optimiser; they exist to say what a fence is worth.

  shoulder   the screening froze `shoulder_ratio` at its reference. What would a sharper
             shoulder have been worth to each selected design? (A stagnation-point-only
             heating model rewards a sharp corner and cannot see corner heating.)
  bluntness  front designs sit on the CFD hull in +bluntness. What does the model say just
             beyond it? Evaluated with `on_extrapolation: flag`, i.e. as LABELLED GP
             extrapolations - the numbers are what the optimiser is being denied, not results.

    run_m4_audit_probes.py M4-OPT-...      writes results/M4/<run>/audit_probes.csv|.json
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.evaluate import evaluate_design  # noqa: E402
from src.aether.optimization import load_design_space  # noqa: E402

SHOULDER = (0.02, 0.04, 0.06, 0.08, 0.10)
BLUNTNESS_STEP = (0.0, 0.01, 0.02, 0.04, 0.06)


def main() -> int:
    run = ROOT / "results" / "M4" / sys.argv[1]
    summary = json.loads((run / "summary.json").read_text())
    space, _ = load_design_space(ROOT / "configs" / "design_space.yaml")
    rows = []
    for label, d in summary["selected"].items():
        base = {v.name: float(d[f"x__{v.name}"]) for v in space.variables}

        def probe(kind: str, values: dict, flag: bool = False, label: str = label) -> None:
            cfg = space.config_for(values)
            if flag:
                cfg = copy.deepcopy(cfg)
                cfg["vehicle"]["aero"]["on_extrapolation"] = "flag"
            ev = evaluate_design(cfg)
            p = ev.performance
            rows.append({
                "design": label, "probe": kind, "shoulder_ratio": values["shoulder_ratio"],
                "bluntness_ratio": values["bluntness_ratio"], "status": p.status,
                "feasible": bool(p.feasible),
                "peak_heat_flux_w_m2": p.peak_heat_flux_w_m2,
                "peak_bondline_temperature_k": p.peak_bondline_temperature_k,
                "max_g": p.max_g,
                "shape_extrapolated": bool(ev.aero_provenance.get("shape_extrapolated", False)),
                "cd_at_peak_heating": ev.diagnostics.get("aero_cd_at_peak_heating"),
                "heatshield_mass_fraction": ev.diagnostics.get("heatshield_mass_fraction")})

        for s in SHOULDER:
            probe("shoulder", {**base, "shoulder_ratio": s})
        for db in BLUNTNESS_STEP:
            probe("bluntness_beyond_hull",
                  {**base, "bluntness_ratio": base["bluntness_ratio"] + db}, flag=True)
    table = pd.DataFrame(rows)
    table.to_csv(run / "audit_probes.csv", index=False)
    out: dict = {"run_id": sys.argv[1], "note": "PROBES, not candidates; see the script docstring",
                 "designs": {}}
    for label, g in table.groupby("design"):
        ref = g[(g["probe"] == "shoulder") & (g["shoulder_ratio"] == 0.10)].iloc[0]
        sh = g[(g["probe"] == "shoulder") & (g["status"] == "OK")]
        sharp = sh.sort_values("shoulder_ratio").iloc[0]
        bl = g[(g["probe"] == "bluntness_beyond_hull") & (g["status"] == "OK")]
        far = bl.sort_values("bluntness_ratio").iloc[-1]
        out["designs"][label] = {
            "sharpest_valid_shoulder_ratio": float(sharp["shoulder_ratio"]),
            "sharp_shoulder_peak_flux_delta_w_m2": float(sharp["peak_heat_flux_w_m2"]
                                                         - ref["peak_heat_flux_w_m2"]),
            "sharp_shoulder_bondline_delta_k": float(sharp["peak_bondline_temperature_k"]
                                                     - ref["peak_bondline_temperature_k"]),
            "sharp_shoulder_feasible": bool(sharp["feasible"]),
            "bluntest_evaluable_bluntness_ratio": float(far["bluntness_ratio"]),
            "bluntest_is_gp_extrapolation": bool(far["shape_extrapolated"]),
            "bluntest_peak_flux_delta_w_m2": float(far["peak_heat_flux_w_m2"]
                                                   - ref["peak_heat_flux_w_m2"]),
            "bluntest_bondline_delta_k": float(far["peak_bondline_temperature_k"]
                                               - ref["peak_bondline_temperature_k"]),
            "n_bluntness_probes_invalid_geometry": int(
                (g[g["probe"] == "bluntness_beyond_hull"]["status"] != "OK").sum())}
    (run / "audit_probes.json").write_text(json.dumps(out, indent=2))
    print(table.to_string())
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
