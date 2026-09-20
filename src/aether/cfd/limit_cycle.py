"""Diagnosis of a bounded limit cycle in a nominally steady case (spec §36, NR-25).

Conceptual anchor
-----------------
A local-time-stepping Euler solution with a TVD limiter can end in a small, stationary
oscillation instead of a fixed point. Before anyone argues about what to do with it, three
questions have measurable answers: how big is it, how long is its period, and WHERE in the
field does it live. This module answers them from solver output only.

Under local time stepping every cell advances by ``max_co`` of ITS OWN acoustic transit time
per iteration, so there is no global physical time and "flow-through times" are not defined.
The natural unit of a period is therefore *cell-transit times*: period_iterations * max_co.

:func:`force_cycle` works on a stored force history. :func:`field_cycle` copies a finished
case (the source is never modified), advances it a few periods while writing the pressure
field every few iterations, and maps the per-cell fluctuation.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from .case import FlowCondition, set_end_iteration
from .pipeline import _latest_time_dir
from .postprocess import force_coefficient_history, read_internal_field
from .reference import normal_shock_density_ratio
from .runner import run_foam


def force_cycle(history: pd.DataFrame, quantity: str, window_iterations: int,
                max_co: float) -> dict:
    """Amplitude and dominant period of ``quantity`` over the final window."""
    it = history["iteration"].to_numpy()
    y = history[quantity].to_numpy()
    m = it >= it[-1] - window_iterations
    w, step = y[m], float(np.median(np.diff(it[m])))
    mean = float(w.mean())
    dev = (w - mean) * np.hanning(len(w))
    power = np.abs(np.fft.rfft(dev)) ** 2
    freq = np.fft.rfftfreq(len(w), step)
    k = int(np.argmax(power[1:]) + 1)
    period = float(1.0 / freq[k])
    return {
        "quantity": quantity, "window_iterations": int(window_iterations),
        "sample_interval_iterations": step, "mean": mean,
        "peak_to_peak_rel": float(np.ptp(w) / abs(mean)),
        "half_peak_to_peak_rel": float(0.5 * np.ptp(w) / abs(mean)),
        "rms_rel": float(w.std() / abs(mean)),
        "dominant_period_iterations": period,
        "dominant_period_power_fraction": float(power[k] / power[1:].sum()),
        "dominant_period_cell_transit_times": period * max_co,
        "period_resolved": bool(period >= 4.0 * step),
    }


def _set_control(case_dir: Path, key: str, value: str) -> None:
    path = Path(case_dir) / "system" / "controlDict"
    text, n = re.subn(rf"(?m)^{key}\s+\S+;", f"{key} {value};", path.read_text())
    if n != 1:
        raise RuntimeError(f"could not set {key} in {path}")
    path.write_text(text)


def field_cycle(source_case_dir: Path, diag_case_dir: Path, flow: FlowCondition,
                reference_area_m2: float, wedge_angle_deg: float, max_co: float,
                n_iterations: int = 200, write_every: int = 2,
                ) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Map where the oscillation lives. Returns (summary, per-cell table, force history).

    The per-cell table has x_m, r_m, the mean p/p_inf and the peak-to-peak and standard
    deviation of p/p_inf over the written snapshots.
    """
    source_case_dir, diag_case_dir = Path(source_case_dir), Path(diag_case_dir)
    latest = _latest_time_dir(source_case_dir)
    if not (diag_case_dir / "log.rhoCentralFoam_diag").exists():
        if diag_case_dir.exists():
            shutil.rmtree(diag_case_dir)
        diag_case_dir.mkdir(parents=True)
        for sub in ("constant", "system"):
            shutil.copytree(source_case_dir / sub, diag_case_dir / sub)
        shutil.copytree(latest, diag_case_dir / latest.name)
        set_end_iteration(diag_case_dir, int(float(latest.name)) + n_iterations)
        _set_control(diag_case_dir, "writeInterval", str(write_every))
        _set_control(diag_case_dir, "purgeWrite", "0")
        ctl = diag_case_dir / "system" / "controlDict"
        ctl.write_text(re.sub(r"(writeInterval|executeInterval)(\s+)5;", r"\g<1>\g<2>1;",
                              ctl.read_text()))
        step = run_foam(diag_case_dir, "rhoCentralFoam_diag", "rhoCentralFoam", 1800.0)
        if not step.ok:
            raise RuntimeError(f"diagnostic solver run failed in {diag_case_dir}")
    if not (latest / "C").exists():
        raise FileNotFoundError(f"{latest}/C missing: run writeCellCentres on the source")
    c = read_internal_field(latest / "C")
    snaps = sorted((d for d in diag_case_dir.iterdir()
                    if d.is_dir() and d.name.isdigit() and d.name != latest.name),
                   key=lambda d: int(d.name))
    p = np.vstack([read_internal_field(d / "p") for d in snaps]) / flow.pressure_pa
    cells = pd.DataFrame({
        "x_m": c[:, 0], "r_m": np.hypot(c[:, 1], c[:, 2]), "p_mean_over_p_inf": p.mean(0),
        "p_peak_to_peak_over_p_inf": np.ptp(p, axis=0), "p_std_over_p_inf": p.std(0)})
    # Model-free localisation: rank cells by pressure variance and ask how few of them hold
    # half / 90% of it, and where those cells are.
    var = cells["p_std_over_p_inf"].to_numpy() ** 2
    order = np.argsort(var)[::-1]
    cum = np.cumsum(var[order]) / var.sum()
    n_half, n_90 = int(np.searchsorted(cum, 0.5) + 1), int(np.searchsorted(cum, 0.9) + 1)
    top = cells.iloc[order[:n_90]]
    k = int(order[0])
    angle = np.degrees(np.arctan2(top["r_m"], -top["x_m"] + 0.0))
    history = force_coefficient_history(diag_case_dir, flow, reference_area_m2,
                                        wedge_angle_deg)
    rho2_over_rho1 = normal_shock_density_ratio(flow.mach, flow.gamma)
    summary = {
        "source_case": source_case_dir.name, "source_iteration": int(float(latest.name)),
        "n_snapshots": len(snaps), "snapshot_interval_iterations": write_every,
        "n_cells": int(len(cells)),
        "max_cell_p_peak_to_peak_over_p_inf": float(cells["p_peak_to_peak_over_p_inf"].max()),
        "max_cell_location_x_m": float(cells["x_m"].iloc[k]),
        "max_cell_location_r_m": float(cells["r_m"].iloc[k]),
        "max_cell_mean_p_over_p_inf": float(cells["p_mean_over_p_inf"].iloc[k]),
        "cells_holding_50pct_of_variance": n_half,
        "cells_holding_90pct_of_variance": n_90,
        "fraction_of_cells_holding_90pct_of_variance": n_90 / len(cells),
        "top90_x_range_m": [float(top["x_m"].min()), float(top["x_m"].max())],
        "top90_r_range_m": [float(top["r_m"].min()), float(top["r_m"].max())],
        "top90_polar_angle_from_axis_deg_range": [float(angle.min()), float(angle.max())],
        "top90_mean_p_over_p_inf_range": [float(top["p_mean_over_p_inf"].min()),
                                          float(top["p_mean_over_p_inf"].max())],
        "normal_shock_density_ratio": rho2_over_rho1,
        "force_cycle_every_iteration": force_cycle(history, "cd_fore", n_iterations, max_co),
    }
    return summary, cells, history


def write_field_cycle(out_dir: Path, summary: dict, cells: pd.DataFrame,
                      history: pd.DataFrame | None = None) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if history is not None:
        history.to_csv(out_dir / "force_history_every_iteration.csv", index=False)
    cells.to_parquet(out_dir / "limit_cycle_cells.parquet", index=False)
    with open(out_dir / "limit_cycle_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
