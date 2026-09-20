#!/usr/bin/env python3
"""Spec section 47 step 3: predict the unseen case from FROZEN parameters, and archive it.

    python experiments/thermal_coupon/blind_validation/make_prediction.py \\
        --frozen frozen_parameters.yaml \\
        --case ../data/blind_ramp_case.csv \\
        --out predictions/

Writes, into `--out`:
    prediction_<case>.csv        predicted T(x,t) at every declared sensor depth, with a
                                 parameter-uncertainty band
    manifest_<case>.json         SHA-256 of every input AND of the prediction itself, a
                                 UTC timestamp, the git commit, and hashes of the source
                                 files that computed it

Why a manifest
--------------
A prediction is only blind if it demonstrably existed before the measurement did. The
manifest makes that checkable by anyone: the hashes pin the exact frozen parameters, the
exact declared heating history and the exact code, and the timestamp plus the git commit
pin when. Section 47 step 4 is "archive/timestamp prediction before measurement
analysis", and a hash in a committed file is the cheapest honest way to do it.

The manifest is evidence of ORDER, not of integrity against a determined faker - anyone
with the repository could re-run this and overwrite. What makes it hard to fake is
committing it and pushing before the experiment, which is what README.md in this
directory insists on.

Guards this script enforces, refusing to run rather than warning
----------------------------------------------------------------
1. the parameter file must actually say `frozen: true`;
2. the declared case file must contain NO temperature columns - if the measurement is
   already in the file you are not predicting, you are fitting;
3. a measurement file for this case must not already exist next to the case, unless
   `--allow-existing-measurement` is passed and a reason is recorded.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent / "analysis"
REPO_ROOT = HERE.parents[2]
for path in (str(ANALYSIS), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from coupon_model import (  # noqa: E402
    KELVIN_OFFSET,
    CouponGeometry,
    CouponParameters,
    predict_sensors,
    sha256_file,
    sidecar_path,
)


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "UNTRACKED"
    except Exception:
        return "UNKNOWN"


def _git_dirty() -> bool:
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=5)
        return bool(out.stdout.strip())
    except Exception:
        return True


def load_declared_case(csv_path: str | Path) -> dict[str, Any]:
    """Read a DECLARED heating history: time and heater flux only, plus its sidecar.

    Refuses a file containing temperature columns. That refusal is the point: a "blind"
    prediction made from a file that already holds the answer is not blind, and the
    easiest way to do that by accident is to point this script at the measurement file.
    """
    csv_path = Path(csv_path)
    meta_path = sidecar_path(csv_path)
    if not meta_path.exists():
        raise FileNotFoundError(f"declared case needs a sidecar at {meta_path.name}")
    meta = yaml.safe_load(meta_path.read_text()) or {}

    with open(csv_path, newline="") as fh:
        rows = [r for r in csv.reader(fh) if r and not r[0].lstrip().startswith("#")]
    header = [c.strip() for c in rows[0]]
    leaked = [c for c in header if c.startswith("t_ch")]
    if leaked:
        raise ValueError(
            f"{csv_path.name} contains measurement columns {leaked}. A declared case must "
            f"contain the heating history ONLY. Strip the temperature columns, or you are "
            f"not making a blind prediction."
        )
    for required in ("time_s", "heater_flux_w_m2"):
        if required not in header:
            raise ValueError(f"{csv_path.name}: required column {required!r} is missing")
    col = {name: i for i, name in enumerate(header)}
    body = np.array([[float(v) for v in r] for r in rows[1:]])

    sensors = meta.get("sensors")
    if not sensors:
        raise ValueError(f"{meta_path.name} declares no sensors; nothing to predict at")

    geom = CouponGeometry(
        thickness_m=float(meta["coupon"]["thickness_m"]),
        density_kg_m3=float(meta["coupon"]["density_kg_m3"]),
        heated_area_m2=float(meta["heater"]["heated_area_m2"]),
    )
    return {
        "case_id": str(meta.get("run_id", csv_path.stem)),
        "time_s": body[:, col["time_s"]],
        "flux_w_m2": body[:, col["heater_flux_w_m2"]],
        "geometry": geom,
        "sensor_channels": [s["channel"] for s in sensors],
        "sensor_depths_m": np.array([float(s["depth_m"]) for s in sensors]),
        "t_ambient_k": float(meta.get("ambient", {}).get("t_ambient_k", 295.15)),
        "t_initial_k": float(meta.get("initial", {}).get("t_initial_k",
                             meta.get("ambient", {}).get("t_ambient_k", 295.15))),
        "metadata": meta,
        "csv_path": csv_path,
        "meta_path": meta_path,
        "synthetic": bool(meta.get("synthetic", False)),
    }


def load_frozen(path: str | Path) -> dict[str, Any]:
    """Read a frozen parameter file, refusing anything not marked frozen."""
    path = Path(path)
    data = yaml.safe_load(path.read_text()) or {}
    if not data.get("frozen"):
        raise ValueError(
            f"{path} is not marked `frozen: true`. Run "
            f"`calibrate.py freeze` first - section 47 requires parameters to be frozen "
            f"before the unseen case is predicted."
        )
    return data


def predict_with_uncertainty(
    case: dict[str, Any],
    frozen: dict[str, Any],
    *,
    n_samples: int = 200,
    n_cells: int = 120,
    seed: int = 20260920,
) -> dict[str, Any]:
    """Nominal prediction plus a parameter-uncertainty band by Monte Carlo.

    The band comes from sampling the calibration's linearised parameter covariance. It
    therefore covers PARAMETER uncertainty only. It does not cover model-form error
    (1-D, constant properties, zero-heat-capacity heater), sensor-depth uncertainty, or
    heater-flux calibration error. Section 47's coverage metric is judged against this
    band knowing that, and `compare_model.py` says so in its own output rather than
    letting a coverage number imply more than it measures.
    """
    params = CouponParameters.from_dict(frozen["parameters"])
    nominal = predict_sensors(case["geometry"], params, case["time_s"], case["flux_w_m2"],
                              case["sensor_depths_m"], t_initial_k=case["t_initial_k"],
                              t_ambient_k=case["t_ambient_k"])

    names = frozen.get("parameter_names_fitted") or []
    sigma = frozen.get("parameter_sigma") or {}
    corr = np.array(frozen.get("correlation_matrix") or [], dtype=float)
    samples: list[np.ndarray] = []

    if names and sigma and corr.size == len(names) ** 2:
        sd = np.array([float(sigma.get(n, 0.0)) for n in names])
        cov = corr * np.outer(sd, sd)
        mean = np.array([getattr(params, n) for n in names])
        rng = np.random.default_rng(seed)
        try:
            draws = rng.multivariate_normal(mean, cov, size=n_samples, method="eigh")
        except np.linalg.LinAlgError:
            draws = np.empty((0, len(names)))
        for draw in draws:
            values = params.to_dict()
            values.update(dict(zip(names, map(float, draw), strict=True)))
            values["conductivity_w_mk"] = max(values["conductivity_w_mk"], 1e-4)
            values["specific_heat_j_kgk"] = max(values["specific_heat_j_kgk"], 1.0)
            for key in ("contact_resistance_m2k_w", "h_front_w_m2k", "h_back_w_m2k"):
                values[key] = max(values[key], 0.0)
            try:
                samples.append(predict_sensors(
                    case["geometry"], CouponParameters(**values), case["time_s"],
                    case["flux_w_m2"], case["sensor_depths_m"],
                    t_initial_k=case["t_initial_k"], t_ambient_k=case["t_ambient_k"]))
            except (ValueError, np.linalg.LinAlgError):
                continue

    if samples:
        stack = np.stack(samples)
        lower = np.percentile(stack, 2.5, axis=0)
        upper = np.percentile(stack, 97.5, axis=0)
        sd_field = np.std(stack, axis=0, ddof=1)
    else:
        lower = upper = nominal
        sd_field = np.zeros_like(nominal)

    return {"nominal_k": nominal, "lower_k": lower, "upper_k": upper,
            "sd_k": sd_field, "n_samples": len(samples), "n_cells": n_cells}


def write_prediction(case, frozen, prediction, out_dir: str | Path) -> tuple[Path, Path]:
    """Write the prediction CSV and its SHA-256 manifest."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = case["case_id"].lower().replace("-", "_")
    if case["synthetic"] and "synthetic" not in stem:
        stem += "_synthetic"
    csv_path = out_dir / f"prediction_{stem}.csv"
    manifest_path = out_dir / f"manifest_{stem}.json"

    channels = case["sensor_channels"]
    header = ["time_s", "heater_flux_w_m2"]
    for ch in channels:
        base = ch.replace("_degc", "")
        header += [f"{base}_pred_k", f"{base}_lo95_k", f"{base}_hi95_k", f"{base}_sd_k"]

    lines = []
    if case["synthetic"]:
        lines.append("# SYNTHETIC CASE - prediction for computer-generated data. "
                     "Software check only, NOT experimental evidence.")
    lines.append("# AETHER M8 blind prediction. Frozen parameters; see the manifest.")
    lines.append(",".join(header))
    for j, t in enumerate(case["time_s"]):
        cells = [f"{t:.4f}", f"{case['flux_w_m2'][j]:.6g}"]
        for i in range(len(channels)):
            cells += [f"{prediction['nominal_k'][j, i]:.4f}",
                      f"{prediction['lower_k'][j, i]:.4f}",
                      f"{prediction['upper_k'][j, i]:.4f}",
                      f"{prediction['sd_k'][j, i]:.4f}"]
        lines.append(",".join(cells))
    csv_path.write_text("\n".join(lines) + "\n")

    manifest = {
        "schema_version": 1,
        "kind": "aether_m8_blind_prediction",
        "case_id": case["case_id"],
        "synthetic": case["synthetic"],
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "n_monte_carlo_samples": prediction["n_samples"],
        "n_cells": prediction["n_cells"],
        "parameters_used": frozen["parameters"],
        "inputs": {
            "frozen_parameters": {"path": str(case["frozen_path"]),
                                  "sha256": sha256_file(case["frozen_path"])},
            "declared_case_csv": {"path": str(case["csv_path"]),
                                  "sha256": sha256_file(case["csv_path"])},
            "declared_case_meta": {"path": str(case["meta_path"]),
                                   "sha256": sha256_file(case["meta_path"])},
        },
        "code": {
            name: sha256_file(path) for name, path in (
                ("coupon_model.py", ANALYSIS / "coupon_model.py"),
                ("make_prediction.py", HERE / "make_prediction.py"),
                ("conduction1d.py", REPO_ROOT / "src/aether/tps/conduction1d.py"),
            ) if Path(path).exists()
        },
        "outputs": {"prediction_csv": {"path": str(csv_path), "sha256": None}},
        "uncertainty_band": (
            "95% interval from the calibration's linearised PARAMETER covariance only. "
            "Excludes model-form error, sensor-depth error and heater-flux calibration "
            "error."
        ),
    }
    manifest["outputs"]["prediction_csv"]["sha256"] = sha256_file(csv_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return csv_path, manifest_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frozen", required=True, help="frozen_parameters.yaml")
    ap.add_argument("--case", required=True, help="declared heating history CSV")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--measurement", default=None,
                    help="path the measurement WILL occupy; refuses to run if it exists")
    ap.add_argument("--allow-existing-measurement", action="store_true",
                    help="override the measurement-exists guard; record why you did")
    ap.add_argument("--n-samples", type=int, default=200)
    ap.add_argument("--n-cells", type=int, default=120)
    ap.add_argument("--seed", type=int, default=20260920)
    args = ap.parse_args(argv)

    frozen = load_frozen(args.frozen)
    case = load_declared_case(args.case)
    case["frozen_path"] = Path(args.frozen)

    if args.measurement and Path(args.measurement).exists() \
            and not args.allow_existing_measurement:
        raise SystemExit(
            f"REFUSING: {args.measurement} already exists. The measurement for this case "
            f"has been taken, so a prediction made now is not blind. Pass "
            f"--allow-existing-measurement only if you know why that is acceptable, and "
            f"write the reason into the run's engineering-notebook entry."
        )

    if frozen.get("synthetic_inputs") or case["synthetic"]:
        print("*** SYNTHETIC - software check only, NOT experimental evidence ***")

    prediction = predict_with_uncertainty(case, frozen, n_samples=args.n_samples,
                                          n_cells=args.n_cells, seed=args.seed)
    csv_path, manifest_path = write_prediction(case, frozen, prediction, args.out)

    print(f"case              {case['case_id']}")
    print(f"sensors           {', '.join(case['sensor_channels'])}")
    print(f"depths [mm]       {', '.join(f'{d * 1e3:.1f}' for d in case['sensor_depths_m'])}")
    print(f"MC samples        {prediction['n_samples']}")
    peak = prediction["nominal_k"].max()
    print(f"predicted peak    {peak:.2f} K ({peak - KELVIN_OFFSET:.2f} degC)")
    print(f"\nprediction -> {csv_path}")
    print(f"manifest   -> {manifest_path}")
    print("\nCOMMIT BOTH FILES NOW, before you run the experiment. See "
          "blind_validation/README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
