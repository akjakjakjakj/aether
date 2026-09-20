#!/usr/bin/env python3
"""Spec section 47 step 6: compare an archived blind prediction with the measurement.

    python experiments/thermal_coupon/analysis/compare_model.py \\
        --prediction ../blind_validation/predictions/prediction_blind_ramp.csv \\
        --manifest   ../blind_validation/predictions/manifest_blind_ramp.json \\
        --measurement ../data/blind_ramp.csv \\
        --out ../results/

Metrics, per sensor and pooled (section 47): RMSE, bias, peak error, time-to-peak error,
maximum absolute residual, and the fraction of measured samples falling inside the
prediction's 95% parameter-uncertainty band.

Two things this script does that a plotting script would not
------------------------------------------------------------
1. It re-hashes the prediction file and checks it against the manifest. If the
   prediction was edited after it was archived, the comparison is void and the script
   says so instead of quietly reporting a good fit.
2. It refuses to call anything PASS. It computes numbers and states what they are; the
   validation matrix decision is a human one, made against a tolerance that must be
   written down before the experiment (see protocol.md, step 9).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for path in (str(HERE), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from coupon_model import load_run, sha256_file  # noqa: E402


def load_prediction(csv_path: str | Path) -> dict[str, Any]:
    """Read a prediction file written by `blind_validation/make_prediction.py`."""
    csv_path = Path(csv_path)
    with open(csv_path, newline="") as fh:
        rows = [r for r in csv.reader(fh) if r and not r[0].lstrip().startswith("#")]
    header = [c.strip() for c in rows[0]]
    body = np.array([[float(v) for v in r] for r in rows[1:]])
    col = {name: i for i, name in enumerate(header)}
    channels = [h[: -len("_pred_k")] for h in header if h.endswith("_pred_k")]
    return {
        "path": csv_path,
        "time_s": body[:, col["time_s"]],
        "channels": channels,
        "nominal_k": np.column_stack([body[:, col[f"{c}_pred_k"]] for c in channels]),
        "lower_k": np.column_stack([body[:, col[f"{c}_lo95_k"]] for c in channels]),
        "upper_k": np.column_stack([body[:, col[f"{c}_hi95_k"]] for c in channels]),
        "synthetic": any("SYNTHETIC" in line for line in
                         csv_path.read_text().splitlines()[:3]),
    }


def check_manifest(manifest_path: str | Path, prediction_path: str | Path) -> dict[str, Any]:
    """Verify the archived prediction is byte-identical to the one the manifest names."""
    manifest = json.loads(Path(manifest_path).read_text())
    recorded = manifest.get("outputs", {}).get("prediction_csv", {}).get("sha256")
    actual = sha256_file(prediction_path)
    return {
        "manifest_path": str(manifest_path),
        "recorded_sha256": recorded,
        "actual_sha256": actual,
        "intact": bool(recorded) and recorded == actual,
        "created_utc": manifest.get("created_utc"),
        "git_commit": manifest.get("git_commit"),
        "git_dirty": manifest.get("git_dirty"),
        "case_id": manifest.get("case_id"),
        "synthetic": bool(manifest.get("synthetic")),
    }


def _time_of_peak(time_s: np.ndarray, series: np.ndarray) -> float:
    """Raw argmax time. Reported, but see `_time_of_peak_robust` before quoting it."""
    return float(time_s[int(np.nanargmax(series))])


SMOOTHING_FRACTION = 0.03
"""Robust-estimator smoothing window, as a fraction of the record length.

Declared as a constant rather than buried in a default argument, because it is a
methodological choice: too short leaves the noise in, too long rounds a genuine peak
off. At 3% of a 1500 s record it is a 45 s window, which is short compared with both the
pulse duration and the diffusion time of a 10 mm coupon, and long enough to average ~9
samples at 0.2 Hz. Change it deliberately and re-report, do not tune it per run.
"""


def _smooth(series: np.ndarray, window: int) -> np.ndarray:
    """Centred moving average with edge padding. `window` <= 2 is a no-op."""
    s = np.asarray(series, dtype=float)
    if window < 3 or window >= len(s):
        return s
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.concatenate([np.full(pad, s[0]), s, np.full(pad, s[-1])])
    return np.convolve(padded, np.ones(window) / window, mode="valid")[: len(s)]


def _smoothing_window(n_samples: int) -> int:
    return max(3, int(round(SMOOTHING_FRACTION * n_samples)) | 1)


def _near_peak_mask(series: np.ndarray, tolerance: float) -> np.ndarray:
    """Samples within `tolerance` of the peak, measured as a fraction of the range."""
    s = np.asarray(series, dtype=float)
    span = float(np.nanmax(s) - np.nanmin(s))
    if not np.isfinite(span) or span <= 0.0:
        return s == np.nanmax(s)
    return s >= np.nanmax(s) - tolerance * span


def _peak_robust(series: np.ndarray, *, tolerance: float = 0.02,
                 window: int | None = None) -> float:
    """Peak of the smoothed record, averaged over its near-peak plateau [K].

    Two separate biases are being removed here, and it took a failing test to notice the
    second one.

    1. The maximum of a noisy record is biased HIGH by roughly sigma*sqrt(2 ln N) - over
       a kelvin at 0.4 K noise and a few hundred samples - in the direction that makes a
       correct model look like it under-predicts the peak.
    2. Averaging the plateau does NOT fix that on its own, because the plateau window is
       itself SELECTED by the noisy maximum. Only samples that happened to sit within a
       couple of sigma of the luckiest one get averaged, so the selection bias survives
       the average. Measured on the synthetic case: plateau averaging alone left +1.36 K
       of bias at the surface sensor.

    Smoothing FIRST removes the selection bias, because the window is then chosen from a
    series whose noise has already been averaged down. The same smoothing is applied to
    the prediction, so whatever rounding the filter causes on a genuinely sharp peak
    happens to both series and cancels in the difference. Measured on the same case: the
    residual bias falls from +1.36 K to +0.08 K.
    """
    s = np.asarray(series, dtype=float)
    smoothed = _smooth(s, window if window is not None else _smoothing_window(len(s)))
    return float(np.nanmean(smoothed[_near_peak_mask(smoothed, tolerance)]))


def _time_of_peak_robust(time_s: np.ndarray, series: np.ndarray,
                         *, tolerance: float = 0.02, window: int | None = None) -> float:
    """Midpoint of the smoothed record's near-peak plateau [s].

    Argmax is a bad estimator of time-to-peak whenever the peak is flat, which is exactly
    what a surface sensor under a slowly varying heater flux produces. With 0.4 K of
    noise on a plateau that changes by less than 0.4 K over tens of seconds, argmax lands
    wherever the noise happened to be largest, and a time-to-peak "error" of tens of
    seconds is an artefact of the estimator rather than a statement about the model.

    Smoothed exactly as `_peak_robust` is, then the midpoint of the samples within
    `tolerance` of the peak. On a sharp peak it reduces to argmax; on a plateau it
    returns the plateau's centre, which is stable.
    """
    s = np.asarray(series, dtype=float)
    span = float(np.nanmax(s) - np.nanmin(s))
    if not np.isfinite(span) or span <= 0.0:
        return _time_of_peak(time_s, s)
    smoothed = _smooth(s, window if window is not None else _smoothing_window(len(s)))
    near = np.flatnonzero(_near_peak_mask(smoothed, tolerance))
    return float(0.5 * (time_s[near[0]] + time_s[near[-1]]))


def compare(prediction: dict[str, Any], measurement, *, band_pad_k: float | None = None
            ) -> dict[str, Any]:
    """Per-sensor and pooled comparison metrics.

    The prediction and the measurement are resampled onto the measurement's time base by
    linear interpolation. The measurement's clock is the reference because it is the
    thing that was observed; interpolating the observation instead would smooth the very
    noise the coverage metric is trying to account for.

    Coverage compares like with like
    --------------------------------
    The prediction band is an interval on the TRUE temperature. A thermocouple reading
    is the true temperature plus its own noise, so asking what fraction of readings fall
    inside the parameter band answers the wrong question: with a well-determined
    calibration the band is a fraction of a kelvin wide and the sensor noise is larger
    than it, and coverage would come out near zero while nothing is wrong.

    `band_pad_k = None` (the default) therefore widens the band by 1.96 sigma of each
    sensor's DECLARED measurement uncertainty, from the run's metadata sidecar, turning
    it into an interval on the reading. Pass a number to override, or 0.0 to score the
    raw parameter band. Which was used is recorded in the output.
    """
    t = measurement.time_s
    per_sensor: list[dict[str, Any]] = []
    all_residuals: list[np.ndarray] = []
    declared = {s["channel"]: s for s in measurement.metadata.get("sensors", [])}

    for j, channel in enumerate(measurement.sensor_channels):
        base = channel.replace("_degc", "")
        if base not in prediction["channels"]:
            per_sensor.append({"channel": channel, "status": "no matching prediction column"})
            continue
        k = prediction["channels"].index(base)

        if band_pad_k is None:
            sensor_sigma = float(declared.get(channel, {}).get(
                "temperature_uncertainty_k", 0.0) or 0.0)
            pad = 1.96 * sensor_sigma
        else:
            pad = float(band_pad_k)

        pred = np.interp(t, prediction["time_s"], prediction["nominal_k"][:, k])
        lo = np.interp(t, prediction["time_s"], prediction["lower_k"][:, k]) - pad
        hi = np.interp(t, prediction["time_s"], prediction["upper_k"][:, k]) + pad
        meas = measurement.sensor_temperatures_k[:, j]

        good = np.isfinite(meas) & np.isfinite(pred)
        if measurement.quality_flag is not None:
            good &= measurement.quality_flag == 0
        residual = pred[good] - meas[good]
        all_residuals.append(residual)

        per_sensor.append({
            "channel": channel,
            "depth_m": float(measurement.sensor_depths_m[j]),
            "n_points": int(good.sum()),
            "rmse_k": float(np.sqrt(np.mean(residual**2))),
            "mae_k": float(np.mean(np.abs(residual))),
            "bias_k": float(np.mean(residual)),
            "max_abs_residual_k": float(np.max(np.abs(residual))),
            "peak_measured_k": float(np.nanmax(meas)),
            "peak_predicted_k": float(np.nanmax(pred)),
            "peak_error_k": float(np.nanmax(pred) - np.nanmax(meas)),
            "peak_robust_measured_k": _peak_robust(meas),
            "peak_robust_predicted_k": _peak_robust(pred),
            "peak_robust_error_k": _peak_robust(pred) - _peak_robust(meas),
            "time_to_peak_measured_s": _time_of_peak(t, meas),
            "time_to_peak_predicted_s": _time_of_peak(t, pred),
            "time_to_peak_error_s": _time_of_peak(t, pred) - _time_of_peak(t, meas),
            "time_to_peak_robust_measured_s": _time_of_peak_robust(t, meas),
            "time_to_peak_robust_predicted_s": _time_of_peak_robust(t, pred),
            "time_to_peak_robust_error_s": (_time_of_peak_robust(t, pred)
                                            - _time_of_peak_robust(t, meas)),
            "coverage_fraction": float(np.mean((meas[good] >= lo[good])
                                               & (meas[good] <= hi[good]))),
            "band_pad_k": pad,
            "mean_band_width_k": float(np.mean(hi[good] - lo[good])),
            "band_is_degenerate": bool(np.allclose(hi[good], lo[good])),
        })

    pooled = np.concatenate(all_residuals) if all_residuals else np.array([])
    covered = [s["coverage_fraction"] for s in per_sensor if "coverage_fraction" in s]
    return {
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "per_sensor": per_sensor,
        "pooled": {
            "rmse_k": float(np.sqrt(np.mean(pooled**2))) if pooled.size else float("nan"),
            "bias_k": float(np.mean(pooled)) if pooled.size else float("nan"),
            "max_abs_residual_k": float(np.max(np.abs(pooled))) if pooled.size
            else float("nan"),
            "n_points": int(pooled.size),
            "mean_coverage_fraction": float(np.mean(covered)) if covered else float("nan"),
        },
    }


def plot_comparison(prediction, measurement, result, out_dir: str | Path,
                    *, tag: str) -> list[Path]:
    """Overlay and residual figures, to the house standard in `src/aether/viz.py`."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from src.aether.viz import DEEP, HOT, MUTED, save_figure

    out_dir = Path(out_dir)
    written: list[Path] = []
    t = measurement.time_s
    n = len(measurement.sensor_channels)

    fig, axes = plt.subplots(n, 1, figsize=(6.4, 1.9 * n + 0.8), sharex=True, squeeze=False)
    for j, channel in enumerate(measurement.sensor_channels):
        ax = axes[j, 0]
        base = channel.replace("_degc", "")
        depth_mm = measurement.sensor_depths_m[j] * 1e3
        if base in prediction["channels"]:
            k = prediction["channels"].index(base)
            ax.fill_between(prediction["time_s"], prediction["lower_k"][:, k],
                            prediction["upper_k"][:, k], color=DEEP, alpha=0.18,
                            linewidth=0, label="predicted, 95% parameter band")
            ax.plot(prediction["time_s"], prediction["nominal_k"][:, k], "-", color=DEEP,
                    lw=1.5, label="predicted (frozen parameters)")
        ax.plot(t, measurement.sensor_temperatures_k[:, j], ".", color=HOT, ms=1.8,
                label="measured")
        ax.set_ylabel(f"T at {depth_mm:.1f} mm  [K]")
        if j == 0:
            ax.legend(fontsize=7, loc="upper right")
    axes[-1, 0].set_xlabel("time from run start  [s]")
    axes[0, 0].set_title("Blind prediction against measurement")
    fig.tight_layout()
    written.append(save_figure(fig, out_dir, f"M8_{tag}_overlay",
                               f"AETHER M8 · case {result['manifest']['case_id']} · "
                               f"prediction archived {result['manifest']['created_utc']} "
                               f"(git {result['manifest']['git_commit']}) · pooled RMSE "
                               f"{result['pooled']['rmse_k']:.2f} K."))

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.axhline(0.0, color=MUTED, lw=0.9)
    styles = ["-", "--", "-.", ":"]
    for j, channel in enumerate(measurement.sensor_channels):
        base = channel.replace("_degc", "")
        if base not in prediction["channels"]:
            continue
        k = prediction["channels"].index(base)
        pred = np.interp(t, prediction["time_s"], prediction["nominal_k"][:, k])
        ax.plot(t, pred - measurement.sensor_temperatures_k[:, j], styles[j % len(styles)],
                lw=1.2, label=f"{measurement.sensor_depths_m[j] * 1e3:.1f} mm")
    ax.set_xlabel("time from run start  [s]")
    ax.set_ylabel("residual, predicted − measured  [K]")
    ax.set_title("Residuals: a trend is model error, scatter is sensor noise")
    ax.legend(fontsize=8, title="sensor depth", title_fontsize=7.5)
    written.append(save_figure(fig, out_dir, f"M8_{tag}_residuals",
                               f"AETHER M8 · case {result['manifest']['case_id']} · "
                               f"pooled bias {result['pooled']['bias_k']:+.2f} K."))
    return written


def write_report(result: dict[str, Any], figures: list[Path], out_path: Path) -> None:
    m = result["manifest"]
    p = result["pooled"]
    lines = [
        "# M8 — blind prediction versus measurement\n",
        f"> Case `{m['case_id']}` · prediction archived {m['created_utc']} at git "
        f"`{m['git_commit']}`{' (dirty)' if m.get('git_dirty') else ''} · compared "
        f"{result['generated_utc']}\n",
    ]
    if m.get("synthetic") or result.get("synthetic"):
        lines += [
            "\n> ## ⚠ SYNTHETIC — THIS IS NOT EXPERIMENTAL EVIDENCE\n",
            "> The 'measurement' compared here was generated by the project's own solver, "
            "not by an instrument. This document demonstrates that the calibrate → freeze "
            "→ predict → compare chain runs and recovers what it was given. It says "
            "nothing whatsoever about whether the model describes a real material. The "
            "physical experiment has not been run.\n",
        ]
    lines += [
        "\n## Archive integrity\n",
        f"- manifest: `{m['manifest_path']}`\n",
        f"- recorded prediction SHA-256: `{m['recorded_sha256']}`\n",
        f"- recomputed now:              `{m['actual_sha256']}`\n",
        "- **" + ("MATCH — the prediction compared here is the one that was archived."
                  if m["intact"] else
                  "MISMATCH — the prediction file changed after archiving. "
                  "THIS COMPARISON IS VOID.") + "**\n",
        "\n## Metrics (spec §47)\n",
        "| Sensor depth [mm] | n | RMSE [K] | bias [K] | max\\|res\\| [K] | "
        "ΔT_peak (max) [K] | ΔT_peak (plateau) [K] | "
        "Δt_peak (argmax) [s] | Δt_peak (plateau) [s] | band coverage |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n",
    ]
    for s in result["per_sensor"]:
        if "rmse_k" not in s:
            lines.append(f"| — | | | | | | | | | {s.get('status', 'skipped')} |\n")
            continue
        cover = ("degenerate band" if s["band_is_degenerate"]
                 else f"{100 * s['coverage_fraction']:.1f}%")
        lines.append(
            f"| {s['depth_m'] * 1e3:.1f} | {s['n_points']} | {s['rmse_k']:.3f} | "
            f"{s['bias_k']:+.3f} | {s['max_abs_residual_k']:.3f} | "
            f"{s['peak_error_k']:+.3f} | {s['peak_robust_error_k']:+.3f} | "
            f"{s['time_to_peak_error_s']:+.1f} | "
            f"{s['time_to_peak_robust_error_s']:+.1f} | {cover} |\n")
    lines.append(
        "\n**Both peak metrics are reported twice, because §47's metrics are estimator-"
        "dependent on noisy data and a single column would hide that choice inside a "
        "script.** The maximum of a noisy record is biased high by about σ·√(2 ln N) — "
        "with 0.4 K sensor noise and a few hundred samples that is over a kelvin, which "
        "makes a correct model look like it under-predicts the peak. `argmax` "
        "time-to-peak is worse still: on a flat peak it lands wherever the noise was "
        "largest.\n"
        f"\nThe `plateau` columns first apply a centred moving average over "
        f"{100 * SMOOTHING_FRACTION:.0f}% of the record "
        "(`compare_model.SMOOTHING_FRACTION`), then take the mean — respectively the "
        "midpoint — of the samples within 2% of the smoothed peak. **The smoothing is "
        "not cosmetic.** Averaging the plateau without it leaves the bias almost intact, "
        "because the plateau window is selected by the noisy maximum and so contains only "
        "the luckiest samples; on the synthetic case that left +1.36 K at the surface "
        "sensor against +0.08 K with smoothing. The identical filter is applied to the "
        "prediction, so any rounding of a genuinely sharp peak affects both series and "
        "cancels in the difference. **Quote the plateau columns.**\n")
    lines += [
        f"\n**Pooled:** RMSE {p['rmse_k']:.3f} K, bias {p['bias_k']:+.3f} K, "
        f"largest residual {p['max_abs_residual_k']:.3f} K over {p['n_points']} points; "
        f"mean 95%-band coverage {100 * p['mean_coverage_fraction']:.1f}%.\n",
        "\n### What the coverage number does and does not include\n",
        "The band is the calibration's linearised **parameter** covariance propagated by "
        "Monte Carlo, widened by 1.96σ of each sensor's declared measurement uncertainty "
        "so that it is an interval on the *reading* rather than on the true temperature. "
        "It excludes model-form error (1-D conduction, temperature-independent properties, "
        "zero-heat-capacity heater), sensor-depth uncertainty, and heater-flux calibration "
        "error. Coverage near 95% therefore means the parameter uncertainty plus sensor "
        "noise is consistent with the residuals — not that the model is validated. "
        "Coverage far below 95% with a *structured* residual is the interesting failure: "
        "it says the error is systematic and no parameter value would have fixed it.\n",
        "\n## Figures\n",
        *[f"- `{f}`\n" for f in figures],
        "\n## Verdict\n",
        "This script does not assign one. The pass/fail tolerance must be declared in the "
        "engineering notebook **before** the experiment (protocol.md step 9), and the "
        "`VALIDATION_MATRIX.md` row is updated by a person who has read the residual plot, "
        "not by a threshold on RMSE.\n",
    ]
    out_path.write_text("".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prediction", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--measurement", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default=None, help="figure filename tag")
    ap.add_argument("--band-pad-k", type=float, default=None,
                    help="widen the coverage band by this many K; default 1.96 x the "
                         "sensor uncertainty declared in the measurement's sidecar")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args(argv)

    prediction = load_prediction(args.prediction)
    manifest = check_manifest(args.manifest, args.prediction)
    measurement = load_run(args.measurement)

    result = compare(prediction, measurement, band_pad_k=args.band_pad_k)
    result["manifest"] = manifest
    result["synthetic"] = prediction["synthetic"] or measurement.synthetic

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = args.tag or manifest["case_id"].lower().replace("-", "_")

    if not manifest["intact"]:
        print("*** MANIFEST MISMATCH - the prediction file is not the archived one. "
              "This comparison is VOID. ***")
    if result["synthetic"]:
        print("*** SYNTHETIC - software check only, NOT experimental evidence ***")

    figures = ([] if args.no_figures
               else plot_comparison(prediction, measurement, result,
                                    REPO_ROOT / "reports" / "figures", tag=tag))
    (out_dir / f"comparison_{tag}.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "figures"}, indent=2,
                   default=float) + "\n")
    write_report(result, [str(f) for f in figures], out_dir / f"comparison_{tag}.md")

    p = result["pooled"]
    print(f"pooled RMSE {p['rmse_k']:.3f} K, bias {p['bias_k']:+.3f} K, "
          f"coverage {100 * p['mean_coverage_fraction']:.1f}%")
    for s in result["per_sensor"]:
        if "rmse_k" in s:
            print(f"  {s['depth_m'] * 1e3:5.1f} mm  RMSE {s['rmse_k']:6.3f} K  "
                  f"peak err {s['peak_error_k']:+7.3f} K  "
                  f"t_peak err {s['time_to_peak_error_s']:+7.1f} s")
    print(f"\nwritten -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
