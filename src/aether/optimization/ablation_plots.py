"""M5 figures. House standard (spec section 34) via `viz.save_figure`: units on every axis,
caption with the run ID and the fidelity label, PDF + PNG. Methods are told apart by hue
AND marker/line style, never hue alone; no dual axes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..viz import ACCENT, DEEP, HOT, INK, MUTED, save_figure
from .analysis import feasible_front

METHOD_STYLE = {
    "lhs_search": dict(color=MUTED, marker="s", linestyle=":", label="LHS search (floor)"),
    "nsga2": dict(color=DEEP, marker="o", linestyle="-", label="NSGA-II, pop 40 (M4 settings)"),
    "nsga2_pop20": dict(color="#6f9bc8", marker="h", linestyle="-.", label="NSGA-II, pop 20"),
    "bo_parego": dict(color=ACCENT, marker="^", linestyle="--", label="GP surrogate / ParEGO"),
    "ai_agent": dict(color=HOT, marker="D", linestyle="-", label="AI engineering agent (LLM)"),
    "ai_adaptive": dict(color="#8a5a9e", marker="P", linestyle=(0, (1, 1)),
                        label="AI + adaptive fidelity [F0 only: NOT YET MEANINGFUL]"),
}


def _style(method: str) -> dict[str, Any]:
    return METHOD_STYLE.get(method, dict(color=INK, marker="x", linestyle="-", label=method))


def plot_ablation_figures(summary: dict[str, Any], frame: pd.DataFrame,
                          curves: dict[str, np.ndarray], checkpoints: np.ndarray,
                          out_dir: Path) -> list[Path]:
    tag = (f"AETHER M5 ablation · run {summary['run_id']} · FIDELITY {summary['fidelity']} "
           f"(aero model: {summary['aero_model']})")
    ref = summary["hypervolume"]["reference_point"]
    objectives = tuple(summary["objectives"])
    budget = summary["budget"]
    n_cfd = sum(sum(m["per_seed"]["cfd_calls"]) for m in summary["methods"].values())
    written: list[Path] = []

    # -- hypervolume vs evaluations ------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.0, 4.3))
    for method, curve in curves.items():
        style = _style(method)
        ax.fill_between(checkpoints, curve.min(axis=0), curve.max(axis=0),
                        color=style["color"], alpha=0.13, linewidth=0)
        ax.plot(checkpoints, curve.mean(axis=0), color=style["color"], ls=style["linestyle"],
                lw=1.6, marker=style["marker"], ms=3.5, markevery=2,
                label=f"{style['label']}  (n = {curve.shape[0]})")
    for n_eval in summary["criteria"].get("checkpoints", {}):
        ax.axvline(int(n_eval), color=MUTED, lw=0.6, ls=":")
    m4 = summary.get("m4_reference") or {}
    if m4.get("nsga2_hv_mean_at_full_budget") is not None:
        ax.axhline(m4["nsga2_hv_mean_at_full_budget"], color=DEEP, lw=0.8, ls=(0, (5, 3)),
                   label=f"M4 NSGA-II after {m4['budget']} evaluations (mean of "
                         f"{m4['n_seeds']} seeds)")
    ax.set_xlabel("budget spent  [distinct evaluate_design calls]")
    ax.set_ylabel("normalised hypervolume of the feasible set  [-]")
    ax.set_xlim(0, budget)
    ax.set_ylim(bottom=0.0)
    ax.legend(fontsize=6.5, loc="lower right")
    written.append(save_figure(
        fig, out_dir, "M5_hypervolume",
        f"{tag}. Line = mean over seeds, band = min-max over seeds. Fixed reference point "
        f"({ref['peak_heat_flux_w_m2']:.3g} W/m^2, {ref['peak_bondline_temperature_k']:.0f} K); "
        f"identical budget of {budget} evaluations for every method. Dotted verticals: the "
        f"pre-declared comparison checkpoints. Evaluations above fidelity 0: {n_cfd}."))

    # -- per-seed hypervolume at the declared checkpoints ---------------------------------
    marks = [int(c) for c in summary["criteria"].get("checkpoints", {})] or [budget]
    fig, axes = plt.subplots(1, len(marks), figsize=(3.1 * len(marks), 3.8), sharey=True)
    for ax, n_eval in zip(np.atleast_1d(axes), marks, strict=True):
        idx = int(np.flatnonzero(checkpoints == n_eval)[0])
        for pos, (method, curve) in enumerate(curves.items()):
            style = _style(method)
            values = curve[:, idx]
            jitter = np.linspace(-0.12, 0.12, len(values)) if len(values) > 1 else [0.0]
            ax.scatter(pos + np.array(jitter), values, s=22, color=style["color"],
                       marker=style["marker"], edgecolors="white", linewidths=0.5,
                       label=style["label"] if ax is np.atleast_1d(axes)[0] else None)
            ax.hlines(values.mean(), pos - 0.28, pos + 0.28, color=INK, lw=1.0)
        ax.set_xticks(range(len(curves)))
        ax.set_xticklabels(list(curves), rotation=60, ha="right", fontsize=6.5)
        ax.set_title(f"after {n_eval} evaluations")
        ax.set_ylim(bottom=0.0)
    np.atleast_1d(axes)[0].set_ylabel("normalised hypervolume  [-]")
    np.atleast_1d(axes)[0].legend(fontsize=5.5, loc="lower left")
    written.append(save_figure(
        fig, out_dir, "M5_hypervolume_per_seed",
        f"{tag}. One marker per seed, black bar = mean. These are the samples the exact "
        "permutation tests compare."))

    # -- fronts ----------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    for method in curves:
        style = _style(method)
        front = feasible_front(frame[frame["method"] == method], objectives)
        if front.empty:
            continue
        ax.plot(front[objectives[0]] * 1e-4, front[objectives[1]], color=style["color"],
                ls=style["linestyle"], lw=1.2, marker=style["marker"], ms=3.5,
                drawstyle="steps-post",
                label=f"{style['label']}  ({len(front)} designs, all seeds pooled)")
    ax.set_xlabel("peak heat flux  [W cm$^{-2}$]")
    ax.set_ylabel("peak bondline temperature  [K]")
    ax.legend(fontsize=6.5, loc="upper right")
    written.append(save_figure(
        fig, out_dir, "M5_fronts",
        f"{tag}. Feasible non-dominated designs per method, seeds pooled. Axes span the "
        "fronts only, not the evaluated cloud - read the axis values before reading the gaps."))

    # -- where the budget went --------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    names = list(curves)
    paid = frame[~frame["cache_hit"]]
    shares = []
    for method in names:
        sub = paid[paid["method"] == method]
        n = max(len(sub), 1)
        shares.append([float(sub["feasible"].sum()) / n,
                       float(((sub["status"] == "OK") & ~sub["feasible"]).sum()) / n,
                       float((sub["status"] != "OK").sum()) / n])
    shares_arr = np.array(shares)
    left = np.zeros(len(names))
    for col, (label, color, hatch) in enumerate((
            ("feasible", DEEP, ""), ("evaluated, constraint violated", ACCENT, "//"),
            ("no physics result (invalid geometry)", MUTED, ".."))):
        ax.barh(names, shares_arr[:, col], left=left, color=color, hatch=hatch,
                edgecolor="white", linewidth=0.5, label=label)
        left += shares_arr[:, col]
    ax.set_xlabel("share of the evaluation budget  [-]")
    ax.set_xlim(0.0, 1.0)
    ax.invert_yaxis()
    ax.legend(fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    written.append(save_figure(
        fig, out_dir, "M5_budget_use",
        f"{tag}. How each method's paid evaluations turned out, all seeds pooled. Every "
        "distinct design costs 1, including geometrically invalid ones (A-OPT-3)."))

    # -- surrogate calibration ---------------------------------------------------------------
    static = (summary.get("surrogate") or {}).get("static", {}).get("pooled", {})
    online = (summary.get("surrogate") or {}).get("prospective", {}).get("outputs", {})
    if static or online:
        fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.7), sharey=True)
        panels = ((axes[0], static, "inside_hull", "held-out LHS designs, inside the hull"),
                  (axes[1], online, "all", "BO's own picks, scored before evaluation"))
        markers = ("o", "s", "^", "D", "v", "P")
        for ax, source, region, title in panels:
            ax.plot([0, 1], [0, 1], color=MUTED, lw=0.8, ls="--", label="perfect calibration")
            for k, (name, cell) in enumerate(source.items()):
                cov = (cell.get(region) or {}).get("coverage")
                if not cov:
                    continue
                levels = sorted(float(level) for level in cov)
                ax.plot(levels, [cov[f"{level:.2f}"] for level in levels], lw=1.1,
                        marker=markers[k % len(markers)], ms=4,
                        label=f"{name} (n = {cell[region]['n']})")
            ax.set_xlabel("nominal coverage of the predictive interval  [-]")
            ax.set_title(title, fontsize=8)
            ax.set_xlim(0.4, 1.0)
            ax.set_ylim(0.0, 1.02)
            ax.legend(fontsize=5.5, loc="lower right")
        axes[0].set_ylabel("observed coverage  [-]")
        written.append(save_figure(
            fig, out_dir, "M5_surrogate_calibration",
            f"{tag}. Share of held-out truths falling inside the GP's central predictive "
            "interval. Below the diagonal = overconfident. Intervals are in the modelled "
            "space (log10 for heat flux)."))
    return written
