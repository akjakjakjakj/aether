"""M4 figures. House standard (spec section 34) via `viz.save_figure`: units on every
axis, caption with run IDs and the fidelity label, PDF + PNG. Series are told apart by
hue AND marker/line style, never hue alone; no dual axes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..viz import ACCENT, DEEP, HOT, INK, MUTED, save_figure

METHOD_STYLE = {
    "lhs_search": dict(color=MUTED, marker="s", linestyle=":", label="LHS search (floor)"),
    "scalarised_de": dict(color=ACCENT, marker="^", linestyle="--",
                          label="scalarised DE (weight sweep)"),
    "nsga2": dict(color=DEEP, marker="o", linestyle="-", label="NSGA-II"),
}
SELECTED_STYLE = {
    "peak_flux_only": dict(marker="v", color=HOT, label="peak-flux-only optimum"),
    "joint_knee": dict(marker="*", color=INK, label="joint knee design"),
    "bondline_only": dict(marker="D", color=DEEP, label="bondline-only optimum"),
}
_OUTPUT_LABEL = {
    "peak_heat_flux_w_m2": "peak heat flux",
    "peak_bondline_temperature_k": "peak bondline T",
    "max_g": "max deceleration",
    "heatshield_mass_fraction": "heat-shield mass fraction",
}


def plot_doe_figures(summary: dict[str, Any], oat: pd.DataFrame, swept: np.ndarray,
                     lhs: pd.DataFrame, names: list[str], out_dir: Path) -> list[Path]:
    tag = (f"AETHER M4 DOE · run {summary['run_id']} · FIDELITY {summary['fidelity']} "
           f"(aero model: {summary['aero_model']})")
    written: list[Path] = []

    # -- Sobol' total-order indices ----------------------------------------------------
    outputs = list(summary["sobol"]["outputs"])
    fig, axes = plt.subplots(1, len(outputs), figsize=(3.0 * len(outputs), 3.9), sharey=True)
    y = np.arange(len(names))
    for ax, out in zip(np.atleast_1d(axes), outputs, strict=True):
        spec = summary["sobol"]["outputs"][out]["variables"]
        total = np.array([spec[n]["total"] for n in names])
        first = np.array([spec[n]["first"] for n in names])
        ci = np.array([spec[n]["total_ci"] for n in names])
        ax.barh(y + 0.18, total, height=0.34, color=DEEP, label="total-order $S_T$")
        ax.errorbar(total, y + 0.18, xerr=[total - ci[:, 0], ci[:, 1] - total], fmt="none",
                    ecolor=INK, elinewidth=0.8, capsize=2)
        ax.barh(y - 0.18, first, height=0.34, color=ACCENT, label="first-order $S_1$")
        ax.axvline(summary["screening"]["thresholds"]["total_index"], color=HOT, lw=0.8,
                   ls="--", label="freeze threshold")
        ax.set_title(_OUTPUT_LABEL.get(out, out))
        ax.set_xlabel("Sobol' index  [-]")
        ax.set_xlim(left=min(0.0, float(first.min()) - 0.02))
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(names)
    axes[0].invert_yaxis()
    axes[-1].legend(loc="lower right", fontsize=7)
    written.append(save_figure(
        fig, out_dir, "M4_doe_sobol",
        f"{tag}. Saltelli/Jansen estimators, n_base = {summary['sobol']['n_base']}, "
        f"{summary['sobol']['n_evaluations']} evaluations on the all-valid sub-box; bars = "
        "95% bootstrap CI on the total-order index."))

    # -- one-at-a-time sweeps ------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    panels = [("peak_heat_flux_w_m2", 1e-4, "peak heat flux  [W cm$^{-2}$]"),
              ("peak_bondline_temperature_k", 1.0, "peak bondline temperature  [K]")]
    markers = ["o", "s", "^", "v", "D", "P", "X", "<", ">", "h"]
    cmap = plt.get_cmap("tab10")
    for ax, (col, scale, label) in zip(axes, panels, strict=True):
        for dim, name in enumerate(names):
            sub = oat[(swept == dim) & (oat["status"] == "OK").to_numpy()]
            if sub.empty:
                continue
            x = sub[f"x__{name}"].to_numpy(dtype=float)
            lo, hi = summary["variables"][name]["lower"], summary["variables"][name]["upper"]
            ax.plot((x - lo) / (hi - lo), sub[col].to_numpy(dtype=float) * scale, lw=1.2,
                    marker=markers[dim % 10], ms=3, color=cmap(dim % 10), label=name)
        ax.set_xlabel("variable position within its range  [0 = min, 1 = max]")
        ax.set_ylabel(label)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.98), ncol=5,
               fontsize=7)
    written.append(save_figure(
        fig, out_dir, "M4_doe_oat",
        f"{tag}. One-at-a-time sweeps about the reference design; geometrically invalid "
        "points are omitted (counts in the report). Overlapping flat lines = inert variables."))

    # -- LHS cloud and the feasible region -------------------------------------------------
    ok = lhs[lhs["status"] == "OK"]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    infeas, feas = ok[~ok["feasible"]], ok[ok["feasible"]]
    ax.scatter(infeas["peak_heat_flux_w_m2"] * 1e-4, infeas["peak_bondline_temperature_k"],
               s=5, color=MUTED, alpha=0.45, marker="x", linewidths=0.6,
               label=f"evaluated, infeasible (n = {len(infeas)})")
    ax.scatter(feas["peak_heat_flux_w_m2"] * 1e-4, feas["peak_bondline_temperature_k"],
               s=12, color=DEEP, marker="o", label=f"feasible (n = {len(feas)})")
    ax.set_xlabel("peak heat flux  [W cm$^{-2}$]")
    ax.set_ylabel("peak bondline temperature  [K]")
    ax.legend(fontsize=7)
    written.append(save_figure(
        fig, out_dir, "M4_doe_lhs",
        f"{tag}. Latin Hypercube over the full 10-variable box, n = {len(lhs)} "
        f"({len(lhs) - len(ok)} not evaluable, of which most are invalid geometry)."))
    return written


def plot_optimisation_figures(summary: dict[str, Any], frame: pd.DataFrame,
                              fronts: dict[str, pd.DataFrame], combined: pd.DataFrame,
                              selected: dict[str, pd.Series], curves: dict[str, np.ndarray],
                              checkpoints: np.ndarray, active: list[str],
                              out_dir: Path) -> list[Path]:
    tag = (f"AETHER M4 · run {summary['run_id']} · DOE {summary['doe_run_id']} · "
           f"FIDELITY {summary['fidelity']} (aero model: {summary['aero_model']})")
    ref = summary["hypervolume"]["reference_point"]
    written: list[Path] = []

    # -- Pareto front ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    ok = frame[(frame["status"] == "OK") & ~frame["cache_hit"]]
    infeas, feas = ok[~ok["feasible"]], ok[ok["feasible"]]
    ax.scatter(infeas["peak_heat_flux_w_m2"] * 1e-4, infeas["peak_bondline_temperature_k"],
               s=3, color=MUTED, alpha=0.25, marker="x", linewidths=0.5,
               label=f"evaluated, infeasible (n = {len(infeas)})")
    ax.scatter(feas["peak_heat_flux_w_m2"] * 1e-4, feas["peak_bondline_temperature_k"],
               s=4, color="#9db7d3", alpha=0.6, label=f"feasible (n = {len(feas)})")
    ax.plot(combined["peak_heat_flux_w_m2"] * 1e-4, combined["peak_bondline_temperature_k"],
            color=INK, lw=1.4, drawstyle="steps-post",
            label=f"combined feasible front (n = {len(combined)})")
    for key, row in selected.items():
        style = SELECTED_STYLE[key]
        ax.scatter([row["peak_heat_flux_w_m2"] * 1e-4], [row["peak_bondline_temperature_k"]],
                   s=90 if key == "joint_knee" else 45, marker=style["marker"],
                   color=style["color"], edgecolors="white", linewidths=0.8, zorder=5,
                   label=f"{style['label']}  ({row['candidate_id']})")
    ax.axhline(ref["peak_bondline_temperature_k"], color=HOT, lw=0.8, ls="--",
               label="bondline allowable = HV reference (placeholder, A-LIM-1)")
    # The front is small on the scale of the cloud: show it again, enlarged, in an inset.
    if len(combined) >= 2:
        fx = combined["peak_heat_flux_w_m2"].to_numpy(dtype=float) * 1e-4
        fy = combined["peak_bondline_temperature_k"].to_numpy(dtype=float)
        pad_x, pad_y = 0.25 * (fx.max() - fx.min()), 0.25 * (fy.max() - fy.min())
        inset = ax.inset_axes([0.50, 0.06, 0.47, 0.36])
        inset.scatter(feas["peak_heat_flux_w_m2"] * 1e-4, feas["peak_bondline_temperature_k"],
                      s=4, color="#9db7d3", alpha=0.6)
        inset.plot(fx, fy, color=INK, lw=1.2, marker=".", ms=3)
        for key, row in selected.items():
            style = SELECTED_STYLE[key]
            inset.scatter([row["peak_heat_flux_w_m2"] * 1e-4],
                          [row["peak_bondline_temperature_k"]], s=70 if key == "joint_knee"
                          else 40, marker=style["marker"], color=style["color"],
                          edgecolors="white", linewidths=0.8, zorder=5)
        inset.set_xlim(fx.min() - pad_x, fx.max() + pad_x)
        inset.set_ylim(fy.min() - pad_y, fy.max() + pad_y)
        inset.set_title("front, enlarged (same units)", fontsize=7)
        inset.tick_params(labelsize=6.5)
        ax.indicate_inset_zoom(inset, edgecolor=MUTED)
    ax.set_xlabel("peak heat flux  [W cm$^{-2}$]")
    ax.set_ylabel("peak bondline temperature  [K]")
    x_hi = float(np.nanpercentile(ok["peak_heat_flux_w_m2"], 99)) * 1e-4
    ax.set_xlim(0.0, x_hi)
    ax.set_ylim(300.0, float(np.nanpercentile(ok["peak_bondline_temperature_k"], 99.5)))
    ax.legend(fontsize=6.5, loc="upper right", ncol=2)
    written.append(save_figure(
        fig, out_dir, "M4_pareto_front",
        f"{tag}. Every candidate from every method and seed. Axes clipped at the 99th "
        "percentile of the evaluated cloud; nothing is removed from the data."))

    # -- hypervolume vs evaluations --------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for method, curve in curves.items():
        style = METHOD_STYLE[method]
        median = np.median(curve, axis=0)
        ax.fill_between(checkpoints, curve.min(axis=0), curve.max(axis=0),
                        color=style["color"], alpha=0.15, linewidth=0)
        ax.plot(checkpoints, median, color=style["color"], ls=style["linestyle"], lw=1.6,
                marker=style["marker"], ms=3.5, markevery=5,
                label=f"{style['label']}: median of {curve.shape[0]} seeds, band = min-max")
    ax.set_xlabel("budget spent  [distinct evaluate_design calls]")
    ax.set_ylabel("normalised hypervolume of the feasible set  [-]")
    ax.set_ylim(bottom=0.0)
    ax.legend(fontsize=7, loc="lower right")
    written.append(save_figure(
        fig, out_dir, "M4_hypervolume",
        f"{tag}. Fixed reference point ({ref['peak_heat_flux_w_m2']:.3g} W/m^2, "
        f"{ref['peak_bondline_temperature_k']:.0f} K); identical budget for every method."))

    # -- where the front sits in the design space ----------------------------------------
    fig, axes = plt.subplots(1, len(active), figsize=(2.6 * len(active), 3.4), sharey=True)
    for ax, name in zip(np.atleast_1d(axes), active, strict=True):
        spec = summary["variables"][name]
        ax.scatter(combined[f"x__{name}"], combined["peak_heat_flux_w_m2"] * 1e-4, s=10,
                   color=DEEP, label="front design")
        for bound, lab in ((spec["lower"], "box bound"), (spec["upper"], None)):
            ax.axvline(bound, color=HOT, lw=0.8, ls="--", label=lab)
        ax.set_xlabel(f"{name}  [{spec['units']}]")
    np.atleast_1d(axes)[0].set_ylabel("peak heat flux  [W cm$^{-2}$]")
    np.atleast_1d(axes)[0].legend(fontsize=6.5)
    written.append(save_figure(
        fig, out_dir, "M4_front_variables",
        f"{tag}. Each combined-front design's value of each active variable. Points "
        "stacked on a dashed line are parked on a box bound (see the exploit audit)."))
    return written
