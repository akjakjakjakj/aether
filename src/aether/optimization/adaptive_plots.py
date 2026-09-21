"""M6 figures. House standard (spec section 34) via `viz.save_figure`: units on every axis,
caption with the run ID and what the CFD was, PDF + PNG. Arms are told apart by hue AND
marker/line style, never hue alone; one y-axis per panel; colour follows the ARM everywhere.

The five categorical hues were checked with the dataviz palette validator (light surface:
lightness band, CVD separation, normal-vision floor and contrast all pass). The no-CFD arm is
drawn in neutral grey with a dotted line on purpose: it is the floor, not a sixth category.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..aerodynamics.cfd_surface import SHAPE_INPUTS
from ..viz import INK, MUTED, save_figure

ARM_STYLE = {
    "adaptive": dict(color="#c1442a", marker="D", linestyle="-",
                     label="adaptive policy (section 26)"),
    "random": dict(color="#2a6fbd", marker="o", linestyle="--", label="random promotion"),
    "greedy": dict(color="#b07a10", marker="^", linestyle="-.", label="greedy: promote the best"),
    "upfront": dict(color="#0f8f7a", marker="s", linestyle=(0, (5, 2)),
                    label="up-front space-filling CFD"),
    "ai_adaptive": dict(color="#9a48b8", marker="P", linestyle=(0, (1, 1)),
                        label="LLM agent + adaptive policy (exploratory)"),
    "f0_only": dict(color=MUTED, marker="X", linestyle=":", label="no new CFD (floor)"),
}


def _style(arm: str) -> dict[str, Any]:
    return ARM_STYLE.get(arm, dict(color=INK, marker="+", linestyle="-", label=arm))


def plot_adaptive_figures(summary: dict[str, Any], curves: pd.DataFrame, calls: pd.DataFrame,
                          base_table: pd.DataFrame, reference_shapes: pd.DataFrame,
                          out_dir: Path) -> list[Path]:
    banner = summary.get("banner") or ""
    tag = (f"AETHER M6 adaptive fidelity · run {summary['run_id']} · F1 backend: "
           f"{summary['cfd']['backend']} · {banner}").rstrip(" ·")
    arms = list(summary["arms"])
    primary = summary["h2"][next(iter(summary["h2"]))]
    written: list[Path] = []

    # -- 1. truth hypervolume against CFD calls spent, with the seed spread ---------------
    fig, (ax, ax_e) = plt.subplots(1, 2, figsize=(11.0, 4.4), sharey=True)
    budget = int(summary["cfd_budget_calls"])
    for arm in arms:
        style, sub = _style(arm), curves[curves["arm"] == arm]
        seeds = sorted(sub["seed"].unique())
        grid = np.arange(0, budget + 1)
        per_seed = []
        for seed in seeds:
            run = sub[sub["seed"] == seed].sort_values("n_evaluations")
            # best truth HV the arm had reached by the time it had spent <= c calls
            best = [run[run["cfd_calls"] <= c]["hv_truth"].max() for c in grid]
            per_seed.append(best)
            final = run.iloc[-1]
            ax.plot(final["cfd_calls"], final["hv_truth"], marker=style["marker"], ms=6,
                    mfc="none", mec=style["color"], mew=1.2, ls="none")
        by_eval = sub.pivot(index="seed", columns="n_evaluations", values="hv_truth")
        ax_e.fill_between(by_eval.columns, by_eval.min(axis=0), by_eval.max(axis=0),
                          color=style["color"], alpha=0.12, linewidth=0)
        ax_e.plot(by_eval.columns, by_eval.mean(axis=0), color=style["color"],
                  ls=style["linestyle"], lw=1.8, marker=style["marker"], ms=4, markevery=2)
        values = np.array(per_seed, dtype=float)
        ok = np.any(np.isfinite(values), axis=0)
        if not np.any(ok):
            continue
        mean = np.nanmean(values[:, ok], axis=0)
        ax.fill_between(grid[ok], np.nanmin(values[:, ok], axis=0),
                        np.nanmax(values[:, ok], axis=0), color=style["color"], alpha=0.12,
                        linewidth=0)
        ax.plot(grid[ok], mean, color=style["color"], ls=style["linestyle"], lw=1.8,
                marker=style["marker"], ms=4, label=f"{style['label']}  (n = {len(seeds)})")
    ax.axhline(primary["target_hv"], color=INK, lw=0.8, ls=(0, (6, 3)),
               label=f"target: {100 * primary['fraction']:.0f}% of the pooled-truth reference")
    ax.set_xlabel("CFD calls charged to the arm  [OpenFOAM cases]")
    ax.set_ylabel("truth hypervolume of the arm's recommended set  [-]")
    ax.set_xlim(-0.3, budget + 0.3)
    ax.set_title("(a) against CFD calls", fontsize=9, loc="left")
    ax_e.axhline(primary["target_hv"], color=INK, lw=0.8, ls=(0, (6, 3)))
    ax_e.set_xlabel("F0 budget spent  [evaluate_design calls, re-evaluations included]")
    ax_e.set_title("(b) the same runs against F0 evaluations", fontsize=9, loc="left")
    fig.legend(*ax.get_legend_handles_labels(), fontsize=7, loc="lower center", ncol=3,
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.subplots_adjust(bottom=0.27, top=0.86)
    fig.suptitle(f"M6: truth hypervolume of each arm's recommended set - run "
                 f"{summary['run_id']}", fontsize=10, x=0.5, y=0.97)
    written.append(save_figure(
        fig, out_dir, "M6_hv_vs_cfd_calls",
        f"{tag}\n(a) Best truth hypervolume reached within a given number of CFD calls: mean over "
        "seeds (line), min-max over seeds (band); open markers are each seed's end point. READ "
        "WITH (b): calls are spent WHILE the search runs, so the rise of a promoting arm in (a) "
        "is search progress as well as CFD; an arm that buys nothing sits at 0 calls with its "
        "whole search behind it, an up-front arm at its full budget. "
        "Hypervolume is normalised to M4's fixed rectangle and scored under POOLED TRUTH, "
        "never under the arm's own surface."))

    # -- 2. where each arm spent its CFD ------------------------------------------------------
    cfd_arms = [a for a in arms if len(calls) and (calls["arm"] == a).any()]
    n = max(len(cfd_arms), 1)
    fig, axes = plt.subplots(1, n, figsize=(3.1 * n + 0.6, 3.6), sharex=True, sharey=True,
                             squeeze=False)
    for ax, arm in zip(axes[0], cfd_arms or [None], strict=False):
        ax.scatter(base_table["bluntness_ratio"], base_table["cone_half_angle_deg"], s=9,
                   color=MUTED, alpha=0.55, linewidths=0, label="starting CFD points (M3)")
        if len(reference_shapes):
            ax.scatter(reference_shapes["bluntness_ratio"],
                       reference_shapes["cone_half_angle_deg"], s=16, marker="_", color=INK,
                       linewidths=1.0, label="reference-front shapes")
        if arm is not None:
            style, mine = _style(arm), calls[calls["arm"] == arm]
            good = mine["usable"].astype(bool)
            ax.scatter(mine[good]["bluntness_ratio"], mine[good]["cone_half_angle_deg"], s=30,
                       marker=style["marker"], facecolors=style["color"],
                       edgecolors="white", linewidths=0.6, label="usable CFD call")
            ax.scatter(mine[~good]["bluntness_ratio"], mine[~good]["cone_half_angle_deg"],
                       s=30, marker=style["marker"], facecolors="none",
                       edgecolors=style["color"], linewidths=1.0,
                       label="failed CFD call (charged)")
            ax.set_title(f"{style['label']}\n{len(mine)} calls, {int(good.sum())} usable",
                         fontsize=7.5)
        ax.set_xlabel("bluntness ratio $R_n/D$  [-]")
    axes[0][0].set_ylabel("cone half-angle  [deg]")
    handles, labels = (axes[0][0] if cfd_arms else axes[0][0]).get_legend_handles_labels()
    fig.legend(handles, [lab.replace("usable CFD call", "usable CFD call (arm's marker)")
                         for lab in labels], fontsize=7, loc="lower center", ncol=4,
               frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.subplots_adjust(bottom=0.24)
    written.append(save_figure(
        fig, out_dir, "M6_cfd_spend_map",
        f"{tag}\nForebody shapes of every CFD call, all seeds pooled, one panel per arm "
        "(shoulder ratio and Mach not shown). Grey: the CFD points every arm started from."))

    # -- 3. each arm's final surface against pooled truth ---------------------------------------
    errors = pd.DataFrame(summary["surface_error"])
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    for i, arm in enumerate(arms):
        style, mine = _style(arm), errors[errors["arm"] == arm]
        if mine.empty:
            continue
        jitter = np.linspace(-0.12, 0.12, len(mine)) if len(mine) > 1 else np.zeros(1)
        ax.scatter(i + jitter, mine["cd_fore_rmse_vs_truth"], s=28, marker=style["marker"],
                   color=style["color"], edgecolors="white", linewidths=0.6)
        ax.hlines(mine["cd_fore_rmse_vs_truth"].mean(), i - 0.25, i + 0.25, color=style["color"],
                  lw=1.6)
    ax.set_xticks(range(len(arms)))
    ax.set_xticklabels([_style(a)["label"].split(" (")[0].split(":")[0] for a in arms],
                       fontsize=7, rotation=12)
    ax.set_ylabel("RMSE of $C_{D,fore}$ vs pooled truth  [-]")
    ax.set_ylim(bottom=0.0)
    ax.set_title(f"M6: each arm's final drag surface vs pooled truth - run "
                 f"{summary['run_id']}", fontsize=9)
    written.append(save_figure(
        fig, out_dir, "M6_surface_error_vs_truth",
        f"{tag}\nEach arm's FINAL drag surface against the pooled-truth surface on one common "
        f"probe set: {int(errors['n_probe_points'].max()) if len(errors) else 0} points (shapes "
        "of the reference front x the declared Mach nodes). One marker per seed, bar = mean. "
        "Pooled truth is itself a surface; its measured error is in the report's hold-out table."))
    return written


def reference_shape_frame(shapes: list[dict[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(shapes, columns=list(SHAPE_INPUTS))
