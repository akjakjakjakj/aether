"""Re-evaluate the M4 combined feasible front under the corrected nose-radius model.

WHAT THIS IS NOT. It is not a re-run of M4. The optimisers are not invoked, no new
designs are generated, and the front is not recomputed. It takes the 64 designs that the
M4 run already found, re-evaluates each one twice through `evaluate_design` - once under
the legacy `cap_radius` model and once under `velocity_gradient` - and reports what moved.
Re-running the optimisation is the coordinator's job, after the CFD surrogate lands.

WHY BOTH ARMS ARE RECOMPUTED rather than comparing against the numbers in the candidate
log: the log was written by a working tree that has since been committed and extended, and
a handful of its rows differ from a present-day re-evaluation in the seventh significant
figure (the run's own `git_dirty: true`). Recomputing both arms in one process makes the
reported delta exactly attributable to the model switch and nothing else. The offset
against the logged values is measured and reported too, so it is visible rather than
assumed away.

    .venv/bin/python scripts/reevaluate_m4_front.py
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from aether.evaluate import evaluate_design
from aether.geometry import CAP_RADIUS, VELOCITY_GRADIENT
from aether.optimization.analysis import feasible_front
from aether.optimization.design_space import DesignSpace, DesignVariable
from aether.utils.run import REPO_ROOT, load_config

DEFAULT_RUN = REPO_ROOT / "results" / "M4" / "M4-OPT-20260920T132037Z"
OUT_DIR = REPO_ROOT / "results" / "M4" / "nose-model-recheck"


def _space_from_snapshot(snapshot: dict) -> DesignSpace:
    """Rebuild the design space from the run's OWN config snapshot, not from configs/.

    The snapshot is the authoritative record of what ran (spec section 9). Reading
    configs/design_space.yaml here would silently pick up any later edit.
    """
    variables = tuple(
        DesignVariable(
            name, str(spec["kind"]), str(spec["path"]), str(spec.get("units", "")),
            str(spec["role"]), float(spec["min"]), float(spec["max"]), float(spec["reference"]),
        )
        for name, spec in snapshot["study"]["variables"].items()
    )
    return DesignSpace(variables, tuple(v.name for v in variables), snapshot["base"])


def _evaluate(space: DesignSpace, values: dict[str, float], model: str, design_id: str):
    cfg = copy.deepcopy(space.config_for(values))
    cfg["vehicle"]["geometry"]["effective_nose_radius_model"] = model
    return evaluate_design(cfg, design_id=design_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    frame = pd.read_parquet(args.run / "candidates.parquet")
    summary = json.loads((args.run / "summary.json").read_text())
    snapshot = load_config(args.run / "config_snapshot.yaml")["config"]
    objectives = tuple(summary["objectives"])

    front = feasible_front(frame, objectives)
    if len(front) != summary["combined"]["n_front"]:
        raise SystemExit(
            f"rebuilt front has {len(front)} designs, summary says "
            f"{summary['combined']['n_front']} - refusing to report on a different set"
        )

    space = _space_from_snapshot(snapshot)
    x_columns = [c for c in front.columns if c.startswith("x__")]
    bluntness_cap = snapshot["base"]["limits"]["max_bluntness_ratio"]

    records = []
    for _, row in front.iterrows():
        values = {c[3:]: float(row[c]) for c in x_columns}
        design_id = str(row["candidate_id"])
        legacy = _evaluate(space, values, CAP_RADIUS, design_id)
        corrected = _evaluate(space, values, VELOCITY_GRADIENT, design_id)
        lp, cp = legacy.performance, corrected.performance
        records.append({
            "candidate_id": design_id,
            "bluntness_ratio": values["bluntness_ratio"],
            "diameter_m": values["diameter_m"],
            "cone_half_angle_deg": values["cone_half_angle_deg"],
            "flight_path_angle_deg": values["flight_path_angle_deg"],
            "k_body_over_nose": 1.0 / (2.0 * values["bluntness_ratio"]),
            "corner_ratio": 2.0 * values["shoulder_ratio"],
            "logged_peak_flux_w_m2": float(row["peak_heat_flux_w_m2"]),
            "logged_bondline_k": float(row["peak_bondline_temperature_k"]),
            "legacy_peak_flux_w_m2": lp.peak_heat_flux_w_m2,
            "legacy_bondline_k": lp.peak_bondline_temperature_k,
            "legacy_feasible": lp.feasible,
            "corrected_peak_flux_w_m2": cp.peak_heat_flux_w_m2,
            "corrected_bondline_k": cp.peak_bondline_temperature_k,
            "corrected_surface_k": cp.peak_surface_temperature_k,
            "corrected_heat_load_j_m2": cp.integrated_external_heat_j_m2,
            "corrected_feasible": cp.feasible,
            "corrected_failure": cp.status if not cp.feasible else "",
            "corrected_violations": ",".join(
                n for n, m in cp.constraint_margins.items()
                if m is not None and not np.isnan(m) and m < 0.0
            ),
            "effective_nose_radius_m": corrected.diagnostics["effective_nose_radius_m"],
            "r_eff_over_r_n": corrected.diagnostics["effective_nose_radius_ratio"],
            "extrapolated": bool(corrected.diagnostics["nose_model_extrapolated"]),
            "margin_bondline": cp.constraint_margins.get("peak_bondline_temperature_k"),
            "margin_max_g": cp.constraint_margins.get("max_g"),
            "margin_bluntness": cp.constraint_margins.get("bluntness_ratio"),
            "margin_shield_mass": cp.constraint_margins.get("heatshield_mass_fraction"),
        })

    out = pd.DataFrame(records)
    args.out.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out / "front_under_both_models.csv", index=False)

    flux_gain = out.corrected_peak_flux_w_m2 / out.legacy_peak_flux_w_m2
    bond_delta = out.corrected_bondline_k - out.legacy_bondline_k
    repro_flux = np.abs(out.legacy_peak_flux_w_m2 - out.logged_peak_flux_w_m2) / \
        out.logged_peak_flux_w_m2
    repro_bond = np.abs(out.legacy_bondline_k - out.logged_bondline_k)

    def span(series) -> dict[str, float]:
        return {"min": float(series.min()), "max": float(series.max()),
                "mean": float(series.mean())}

    stats = {
        "run": args.run.name,
        "n_front": int(len(out)),
        "bluntness_cap": bluntness_cap,
        "reproduction_of_logged_values_under_legacy": {
            "max_relative_flux_difference": float(repro_flux.max()),
            "max_absolute_bondline_difference_k": float(repro_bond.max()),
        },
        "k_body_over_nose": span(out.k_body_over_nose),
        "corner_ratio": span(out.corner_ratio),
        "r_eff_over_r_n": span(out.r_eff_over_r_n),
        "n_extrapolated": int(out.extrapolated.sum()),
        "peak_flux_ratio_corrected_over_legacy": span(flux_gain),
        "peak_flux_w_m2": {"legacy": span(out.legacy_peak_flux_w_m2),
                           "corrected": span(out.corrected_peak_flux_w_m2)},
        "bondline_k": {"legacy": span(out.legacy_bondline_k),
                       "corrected": span(out.corrected_bondline_k)},
        "bondline_rise_k": span(bond_delta),
        "feasibility": {
            "legacy_feasible": int(out.legacy_feasible.sum()),
            "corrected_feasible": int(out.corrected_feasible.sum()),
        },
        "corrected_violation_counts": {
            name: int(out.corrected_violations.str.contains(name).sum())
            for name in ("peak_bondline_temperature_k", "max_g", "bluntness_ratio",
                         "heatshield_mass_fraction")
        },
    }
    (args.out / "summary.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
