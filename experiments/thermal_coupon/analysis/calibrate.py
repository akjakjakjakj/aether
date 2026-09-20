#!/usr/bin/env python3
"""Fit coupon model parameters from calibration runs, then freeze them.

    python experiments/thermal_coupon/analysis/calibrate.py fit \\
        --runs data/cal_*.csv --out results/

    python experiments/thermal_coupon/analysis/calibrate.py freeze \\
        --calibration results/calibrated_parameters.yaml \\
        --out blind_validation/frozen_parameters.yaml

Why this is two commands, not one
---------------------------------
Spec section 47 requires model parameters to be FROZEN before the validation case is
predicted, and the prediction to be archived before the validation case is measured. A
single script that fits and predicts in one breath makes it impossible to prove which
happened first. Splitting them forces a file, and the file gets committed.

What is fitted and what is not
------------------------------
Fitted: effective through-thickness conductivity, specific heat, heater contact
resistance, and the two face loss coefficients.

Not fitted: density (measured with a scale and calipers), coupon thickness (measured),
sensor depths (measured, with a declared uncertainty), emissivity (fixed - it is
strongly degenerate with the convective coefficients, and fitting both would produce two
precise-looking numbers when the data only constrains their sum).

A fit that is allowed to absorb a measurement error into an 'effective' property will
do exactly that, and the resulting parameter set will predict the calibration runs
beautifully and the blind case badly. That failure is the entire point of section 47's
blind case, so the fit is deliberately given less freedom than it could have.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from coupon_model import (  # noqa: E402
    FREE_PARAMETER_NAMES,
    CouponParameters,
    RunData,
    load_run,
    predict_run,
    sha256_file,
)

DEFAULT_BOUNDS: dict[str, tuple[float, float]] = {
    # Physical brackets for a hobby-grade printed-polymer coupon in room air. They are
    # brackets, not priors: a fit that lands ON a bound is a warning that the model is
    # wrong or the data uninformative, and `fit` reports that explicitly.
    "conductivity_w_mk": (0.01, 5.0),
    "specific_heat_j_kgk": (100.0, 5000.0),
    "contact_resistance_m2k_w": (0.0, 0.05),
    "h_front_w_m2k": (0.0, 200.0),
    "h_back_w_m2k": (0.0, 200.0),
}

DEFAULT_INITIAL: dict[str, float] = {
    # Order-of-magnitude starting guesses for a generic thermoplastic. These are NOT
    # claims about any particular filament; the protocol tells the student to replace
    # them with the datasheet values for whatever they actually print.
    "conductivity_w_mk": 0.2,
    "specific_heat_j_kgk": 1500.0,
    "contact_resistance_m2k_w": 1.0e-3,
    "h_front_w_m2k": 10.0,
    "h_back_w_m2k": 10.0,
}


@dataclass
class CalibrationResult:
    """A fit, its uncertainty, and enough provenance to audit it later."""

    parameters: CouponParameters
    sigma: dict[str, float]
    """1-sigma parameter standard errors [same units as the parameter]."""
    correlation: np.ndarray
    parameter_names: list[str]
    fixed: dict[str, float]
    rmse_k: float
    per_run_rmse_k: dict[str, float]
    n_residuals: int
    n_free: int
    at_bound: list[str]
    inputs: list[dict[str, str]]
    any_synthetic: bool
    converged: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "frozen": False,
            "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "synthetic_inputs": self.any_synthetic,
            "parameters": self.parameters.to_dict(),
            "parameter_sigma": self.sigma,
            "parameter_names_fitted": self.parameter_names,
            "parameters_held_fixed": self.fixed,
            "correlation_matrix": [[float(v) for v in row] for row in self.correlation],
            "fit_quality": {
                "rmse_k": self.rmse_k,
                "per_run_rmse_k": self.per_run_rmse_k,
                "n_residuals": self.n_residuals,
                "n_free_parameters": self.n_free,
                "converged": self.converged,
                "optimiser_message": self.message,
                "parameters_at_bound": self.at_bound,
            },
            "inputs": self.inputs,
        }


def _residuals_for(runs: list[RunData], params: CouponParameters, n_cells: int
                   ) -> list[np.ndarray]:
    """Per-run residual vectors, model minus measurement, in Kelvin.

    Residuals are weighted by each sensor's declared temperature uncertainty when the
    sidecar provides one. A surface thermocouple pressed against a heater and one
    embedded 9 mm deep do not deserve equal say in the fit.
    """
    out: list[np.ndarray] = []
    for run in runs:
        predicted = predict_run(run, params, n_cells=n_cells)
        measured = run.sensor_temperatures_k
        sigma = np.ones(measured.shape[1])
        declared = {s["channel"]: s for s in run.metadata.get("sensors", [])}
        for j, ch in enumerate(run.sensor_channels):
            u = declared.get(ch, {}).get("temperature_uncertainty_k")
            if u:
                sigma[j] = float(u)
        good = np.isfinite(measured)
        if run.quality_flag is not None:
            good &= (run.quality_flag[:, None] == 0)
        weighted = np.where(good, (predicted - measured) / sigma, 0.0)
        out.append(weighted.ravel())
    return out


def calibrate(
    runs: list[RunData],
    *,
    initial: dict[str, float] | None = None,
    bounds: dict[str, tuple[float, float]] | None = None,
    fixed: dict[str, float] | None = None,
    emissivity: float = 0.90,
    n_cells: int = 120,
    verbose: bool = False,
) -> CalibrationResult:
    """Least-squares fit of the free parameters against every supplied run at once.

    Fitting all runs jointly rather than one at a time is deliberate: a single heating
    run cannot separate conductivity from contact resistance (both delay the interior
    response), while a cool-down run with no heater flux constrains the loss
    coefficients almost alone. The protocol asks for both kinds for exactly that reason.
    """
    if not runs:
        raise ValueError("no calibration runs supplied")
    initial = {**DEFAULT_INITIAL, **(initial or {})}
    bounds = {**DEFAULT_BOUNDS, **(bounds or {})}
    fixed = dict(fixed or {})

    free_names = [n for n in FREE_PARAMETER_NAMES if n not in fixed]
    if not free_names:
        raise ValueError("every parameter is fixed; there is nothing to calibrate")

    x0 = np.array([initial[n] for n in free_names], dtype=float)
    lo = np.array([bounds[n][0] for n in free_names], dtype=float)
    hi = np.array([bounds[n][1] for n in free_names], dtype=float)
    x0 = np.clip(x0, lo + 1e-12, hi - 1e-12)

    def build(vector: np.ndarray) -> CouponParameters:
        values = dict(zip(free_names, map(float, vector), strict=True))
        values.update(fixed)
        return CouponParameters(**values, emissivity=emissivity)

    def residual(vector: np.ndarray) -> np.ndarray:
        return np.concatenate(_residuals_for(runs, build(vector), n_cells))

    fit = least_squares(residual, x0, bounds=(lo, hi), x_scale="jac",
                        verbose=2 if verbose else 0)

    params = build(fit.x)
    per_run = {}
    for run, res in zip(runs, _residuals_for(runs, params, n_cells), strict=True):
        per_run[run.run_id] = float(np.sqrt(np.mean(res**2)))
    rmse = float(np.sqrt(np.mean(fit.fun**2)))

    # ---- parameter uncertainty ------------------------------------------------------
    # cov = s^2 (J^T J)^-1 with s^2 = 2*cost/(m-n). This is the linearised, Gaussian,
    # independent-residual estimate. Thermocouple residuals in a transient experiment
    # are NOT independent in time, so this UNDERSTATES the true uncertainty; the number
    # is reported as a lower bound and the blind case is what actually tests it.
    m, n_free = len(fit.fun), len(free_names)
    dof = max(m - n_free, 1)
    s2 = 2.0 * fit.cost / dof
    jtj = fit.jac.T @ fit.jac
    try:
        cov = s2 * np.linalg.inv(jtj)
    except np.linalg.LinAlgError:
        cov = s2 * np.linalg.pinv(jtj)
    sd = np.sqrt(np.clip(np.diag(cov), 0.0, np.inf))
    denom = np.outer(sd, sd)
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.where(denom > 0.0, cov / denom, 0.0)

    at_bound = [
        name for name, value, a, b in zip(free_names, fit.x, lo, hi, strict=True)
        if abs(value - a) <= 1e-9 * max(1.0, abs(a)) or abs(value - b) <= 1e-9 * abs(b)
    ]

    return CalibrationResult(
        parameters=params,
        sigma={n: float(v) for n, v in zip(free_names, sd, strict=True)},
        correlation=corr,
        parameter_names=free_names,
        fixed=fixed,
        rmse_k=rmse,
        per_run_rmse_k=per_run,
        n_residuals=m,
        n_free=n_free,
        at_bound=at_bound,
        inputs=[{"path": str(r.source_path), "run_id": r.run_id, "run_type": r.run_type,
                 "sha256": sha256_file(r.source_path)} for r in runs if r.source_path],
        any_synthetic=any(r.synthetic for r in runs),
        converged=bool(fit.success),
        message=str(fit.message),
    )


def freeze(calibration_path: str | Path, out_path: str | Path) -> dict[str, Any]:
    """Copy a completed calibration into a FROZEN parameter file.

    The frozen file records the SHA-256 of the calibration it came from, so a prediction
    can be traced back to the exact fit, and that fit back to the exact raw data.
    """
    calibration_path, out_path = Path(calibration_path), Path(out_path)
    data = yaml.safe_load(calibration_path.read_text())
    if "parameters" not in data:
        raise ValueError(f"{calibration_path} does not look like a calibration output")

    payload = {
        "schema_version": 1,
        "frozen": True,
        "frozen_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "synthetic_inputs": bool(data.get("synthetic_inputs", False)),
        "parameters": data["parameters"],
        "parameter_sigma": data.get("parameter_sigma", {}),
        "correlation_matrix": data.get("correlation_matrix", []),
        "parameter_names_fitted": data.get("parameter_names_fitted", []),
        "source_calibration": {
            "path": str(calibration_path),
            "sha256": sha256_file(calibration_path),
            "created_utc": data.get("created_utc"),
            "rmse_k": data.get("fit_quality", {}).get("rmse_k"),
        },
        "warning": (
            "These parameters are FROZEN. Editing this file after a blind prediction has "
            "been archived invalidates the validation. Re-fit and re-freeze instead, and "
            "record why in docs/negative_results.md."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return payload


def _cmd_fit(args) -> int:
    runs = [load_run(p) for p in args.runs]
    fixed = {}
    for item in args.fix or []:
        name, _, value = item.partition("=")
        if name not in FREE_PARAMETER_NAMES:
            raise SystemExit(f"--fix: {name!r} is not a fittable parameter")
        fixed[name] = float(value)

    print(f"calibrating against {len(runs)} run(s): "
          f"{', '.join(f'{r.run_id}[{r.run_type}]' for r in runs)}")
    if any(r.synthetic for r in runs):
        print("  *** SYNTHETIC INPUT PRESENT - this is a software check, NOT experimental "
              "evidence ***")

    result = calibrate(runs, fixed=fixed, emissivity=args.emissivity,
                       n_cells=args.n_cells, verbose=args.verbose)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "calibrated_parameters.yaml"
    target.write_text(yaml.safe_dump(result.to_dict(), sort_keys=False))

    print(f"\nRMSE over all sensors and runs: {result.rmse_k:.3f} K "
          f"({result.n_residuals} residuals, {result.n_free} free parameters)")
    for name in result.parameter_names:
        value = getattr(result.parameters, name)
        print(f"  {name:<28} {value:12.6g}  +/- {result.sigma[name]:.3g}")
    for name, value in result.fixed.items():
        print(f"  {name:<28} {value:12.6g}  (held fixed)")
    if result.at_bound:
        print(f"\n  WARNING: parameters at a bound: {', '.join(result.at_bound)}. "
              f"The data does not constrain them; do not report them as measurements.")
    if not result.converged:
        print(f"\n  WARNING: optimiser did not converge: {result.message}")
    print(f"\nwritten -> {target}")
    return 0


def _cmd_freeze(args) -> int:
    payload = freeze(args.calibration, args.out)
    print(f"frozen -> {args.out}")
    print(f"  source calibration sha256 {payload['source_calibration']['sha256']}")
    if payload["synthetic_inputs"]:
        print("  *** these parameters were fitted to SYNTHETIC data - software check "
              "only ***")
    print("  Commit this file BEFORE running the validation experiment (spec section 47).")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    fit = sub.add_parser("fit", help="fit parameters from calibration runs")
    fit.add_argument("--runs", nargs="+", required=True, help="acquisition CSV files")
    fit.add_argument("--out", required=True, help="output directory")
    fit.add_argument("--fix", nargs="*", help="hold a parameter fixed, e.g. h_back_w_m2k=8")
    fit.add_argument("--emissivity", type=float, default=0.90)
    fit.add_argument("--n-cells", type=int, default=120)
    fit.add_argument("--verbose", action="store_true")
    fit.set_defaults(func=_cmd_fit)

    frz = sub.add_parser("freeze", help="lock a calibration into a frozen parameter file")
    frz.add_argument("--calibration", required=True)
    frz.add_argument("--out", required=True)
    frz.set_defaults(func=_cmd_freeze)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
