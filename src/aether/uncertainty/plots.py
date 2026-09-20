"""M7 figures. House rules (spec §34) come from `aether.viz`: units on both axes, a
caption carrying the run and design IDs, a legible legend, vector PDF plus PNG preview,
and no colour that means anything without a legend.

Every figure here is drawn from the run's own `summary.json` and candidate frame. None of
them is decorative: each one exists because a number in the report is hard to believe
without seeing its shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..viz import ACCENT, DEEP, GRID, HOT, INK, MUTED, save_figure

ALEATORY_STYLE = {"color": DEEP, "hatch": "", "label": "aleatory (variability)"}
EPISTEMIC_STYLE = {"color": HOT, "hatch": "///", "label": "epistemic (model form / ignorance)"}
TIER_MARK = {"T1": "T1", "T2": "T2", "T3": "T3 judgment"}


def _caption(summary: dict[str, Any], extra: str = "") -> str:
    bits = [f"AETHER M7 run {summary.get('run_id', '?')}",
            f"git {summary.get('git_commit', '?')}"
            + (" (dirty)" if summary.get("git_dirty") else ""),
            f"source hash {summary.get('source_hash', '?')}",
            f"aero {summary.get('aero_model', '?')} (fidelity "
            f"{summary.get('fidelity', '?')})"]
    if extra:
        bits.append(extra)
    return " | ".join(bits)


# ---------------------------------------------------------------------------------------

def plot_input_inventory(summary: dict[str, Any], out_dir: Path) -> list[Path]:
    """What is uncertain, by how much, of which kind, and on whose authority."""
    inputs = summary["uncertainty_model"]["inputs"]
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(11.0, 4.6),
                                            gridspec_kw={"width_ratios": [1.25, 1.0]})

    # Discrete inputs are deliberately NOT given a bar: a switch between two source
    # documents has no "spread relative to nominal", and drawing one at the number of
    # states would invite a reader to compare it with a percentage. They are listed
    # instead, which is what they are.
    comparable = [i for i in inputs if np.isfinite(_relative_span(i))]
    other = [i for i in inputs if not np.isfinite(_relative_span(i))]
    continuous = comparable
    names = [i["name"] for i in continuous]
    spans = [_relative_span(i) for i in continuous]
    kinds = [i["kind"] for i in continuous]
    tiers = [i["tier"] for i in continuous]
    order = np.argsort(spans)
    y = np.arange(len(order))
    for pos, idx in zip(y, order, strict=True):
        style = EPISTEMIC_STYLE if kinds[idx] == "epistemic" else ALEATORY_STYLE
        ax_left.barh(pos, spans[idx] * 100.0, color=style["color"], hatch=style["hatch"],
                     edgecolor="white", height=0.66)
        ax_left.text(spans[idx] * 100.0 * 1.02, pos, TIER_MARK[tiers[idx]], va="center",
                     fontsize=6.5, color=MUTED)
    ax_left.set_yticks(y, [names[i] for i in order], fontsize=7.5)
    ax_left.set_xlabel("declared spread [% of nominal]\n"
                       "(2 s.d. for a normal, full width for a band)")
    ax_left.set_title("Declared uncertain inputs (those with a relative spread)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=ALEATORY_STYLE["color"]),
               plt.Rectangle((0, 0), 1, 1, color=EPISTEMIC_STYLE["color"], hatch="///")]
    ax_left.legend(handles, [ALEATORY_STYLE["label"], EPISTEMIC_STYLE["label"]],
                   fontsize=7, loc="lower right")
    if other:
        listing = "; ".join(_describe_incomparable(i) for i in other)
        ax_left.text(0.0, -0.32, "not expressible as a relative spread — " + listing,
                     transform=ax_left.transAxes, fontsize=6.5, color=INK, va="top",
                     wrap=True)

    profile = summary["uncertainty_model"].get("density_profile")
    if profile:
        z = np.asarray(profile["altitude_km"], dtype=float)
        sigma = np.asarray(profile["sigma_relative"], dtype=float)
        tier_rows = profile.get("tier", ["T3"] * len(z))
        ax_right.plot(sigma * 100.0, z, color=DEEP, lw=1.6, marker="o", ms=3.5,
                      label="1 s.d. density dispersion")
        t1 = np.array([t == "T1" for t in tier_rows])
        ax_right.scatter(sigma[t1] * 100.0, z[t1], s=34, facecolor="white",
                         edgecolor=DEEP, zorder=4, label="T1 (GRAM / primary)")
        ax_right.scatter(sigma[~t1] * 100.0, z[~t1], s=34, marker="s", facecolor="white",
                         edgecolor=HOT, zorder=4, label="T3 (engineering judgment)")
        ax_right.axhline(86.0, color=ACCENT, ls="--", lw=1.0)
        ax_right.text(0.02, 0.60, "86 km — above here the atmosphere table is\n"
                      "interpolated (gate G1A′) and every σ is judgment",
                      transform=ax_right.transAxes, fontsize=6.5, color=ACCENT,
                      va="bottom", ha="left")
        ax_right.set_xlabel("1 s.d. density dispersion [% of nominal]")
        ax_right.set_ylabel("geometric altitude [km]")
        ax_right.set_title("Atmospheric density dispersion")
        ax_right.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    return [save_figure(fig, out_dir, "M7_input_inventory",
                        _caption(summary, "declared in configs/uncertainty.yaml"))]


def _relative_span(item: dict[str, Any]) -> float:
    """A single comparable width per input, for the inventory bar chart only."""
    dist = item["distribution"]
    family = dist["family"]
    if item["apply"].get("type") == "density_profile":
        # The distribution here is a z-SCORE; its own width says nothing. What the input
        # actually does is 1 + z * sigma(h), so the comparable width is 2 * max sigma.
        sigmas = item["apply"]["sigma_vs_altitude_km"]["sigma_relative"]
        return float(2.0 * max(float(s) for s in sigmas))
    if item["apply"].get("type") == "offset":
        return float("nan")   # an absolute offset is not a percentage of anything
    if family == "normal":
        mean = abs(dist["mean"])
        if mean == 0.0:
            return float("nan")
        return float(2.0 * dist["std"] / mean)
    if family == "uniform":
        centre = abs(0.5 * (dist["low"] + dist["high"])) or 1.0
        return float((dist["high"] - dist["low"]) / centre)
    if family == "triangular":
        centre = abs(dist["mode"]) or 1.0
        return float((dist["high"] - dist["low"]) / centre)
    if family == "lognormal":
        return float(2.0 * dist["sigma_log"])
    return float("nan")


def _describe_incomparable(item: dict[str, Any]) -> str:
    """One phrase for an input the bar chart cannot honestly draw.

    A switch between two source documents has no "spread relative to nominal", and an
    absolute offset in degrees is not a percentage of anything. Drawing either as a bar
    would invite a comparison that does not exist.
    """
    dist = item["distribution"]
    if dist["family"] == "discrete":
        return (f"{item['name']}: model-form switch, {len(dist['values'])} states "
                f"({TIER_MARK[item['tier']]})")
    if item["apply"].get("type") == "offset":
        width = (2.0 * dist["std"] if dist["family"] == "normal"
                 else dist.get("high", 0.0) - dist.get("low", 0.0))
        return (f"{item['name']}: absolute offset, +/-{width / 2:.3g} "
                f"{item.get('units') or ''} ({TIER_MARK[item['tier']]})")
    return f"{item['name']} ({TIER_MARK[item['tier']]})"


# ---------------------------------------------------------------------------------------

def plot_output_distributions(summary: dict[str, Any], frames: dict[str, pd.DataFrame],
                              out_dir: Path) -> list[Path]:
    """Empirical CDFs of the two objectives, per propagated design, with p95 marked."""
    objectives = tuple(summary["objectives"])
    fig, axes = plt.subplots(1, len(objectives), figsize=(5.4 * len(objectives), 4.2))
    axes = np.atleast_1d(axes)
    colours = [DEEP, HOT, ACCENT, INK, MUTED]
    for ax, name in zip(axes, objectives, strict=True):
        for i, (label, frame) in enumerate(frames.items()):
            values = frame[name].to_numpy(dtype=float)
            values = np.sort(values[np.isfinite(values)])
            if values.size == 0:
                continue
            cdf = np.arange(1, values.size + 1) / values.size
            colour = colours[i % len(colours)]
            ax.plot(values, cdf, color=colour, lw=1.5, label=label)
            p95 = float(np.percentile(values, 95.0))
            ax.plot([p95], [0.95], marker="v", ms=6, color=colour)
        allowable = summary.get("allowables", {}).get(name)
        if allowable is not None:
            ax.axvline(float(allowable), color=HOT, ls="--", lw=1.1)
            ax.text(float(allowable), 0.05, " allowable", color=HOT, fontsize=7,
                    rotation=90, va="bottom")
        ax.axhline(0.95, color=GRID, lw=0.8)
        ax.set_xlabel(f"{name} [{summary['units'].get(name, '')}]")
        ax.set_ylabel("cumulative probability [-]")
        ax.set_title(name)
        ax.legend(fontsize=7)
    fig.suptitle("Propagated output distributions (markers: 95th percentile)", fontsize=10)
    fig.tight_layout()
    return [save_figure(fig, out_dir, "M7_output_distributions",
                        _caption(summary, "pooled aleatory+epistemic mixture; see the "
                                          "p-box figure for the separated view"))]


def plot_pbox(summary: dict[str, Any], frames: dict[str, pd.DataFrame],
              branch_index: dict[str, np.ndarray], out_dir: Path) -> list[Path]:
    """One CDF per epistemic branch: the width of a curve is variability, the gap is
    ignorance. This is the figure that makes the aleatory/epistemic split visible."""
    name = summary.get("pbox_output", summary["objectives"][-1])
    labels = list(frames)
    fig, axes = plt.subplots(1, len(labels), figsize=(4.4 * len(labels), 4.2),
                             sharey=True)
    axes = np.atleast_1d(axes)
    for ax, label in zip(axes, labels, strict=True):
        frame, branches = frames[label], branch_index[label]
        values = frame[name].to_numpy(dtype=float)
        for b in np.unique(branches):
            sub = np.sort(values[(branches == b) & np.isfinite(values)])
            if sub.size < 2:
                continue
            ax.plot(sub, np.arange(1, sub.size + 1) / sub.size, color=MUTED, lw=0.7,
                    alpha=0.8)
        allf = np.sort(values[np.isfinite(values)])
        if allf.size:
            ax.plot(allf, np.arange(1, allf.size + 1) / allf.size, color=DEEP, lw=1.8,
                    label="pooled mixture")
        allowable = summary.get("allowables", {}).get(name)
        if allowable is not None:
            ax.axvline(float(allowable), color=HOT, ls="--", lw=1.1, label="allowable")
        ax.set_title(label, fontsize=9)
        ax.set_xlabel(f"{name} [{summary['units'].get(name, '')}]")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("cumulative probability [-]")
    fig.suptitle("Probability box: one thin curve per epistemic branch "
                 "(spread = variability, separation = ignorance)", fontsize=9.5)
    fig.tight_layout()
    return [save_figure(fig, out_dir, "M7_pbox",
                        _caption(summary, f"output {name}; "
                                 f"{summary['draws']['n_epistemic_branches']} epistemic "
                                 f"branches x {summary['draws']['n_aleatory']} aleatory "
                                 "draws (common random numbers)"))]


# ---------------------------------------------------------------------------------------

def plot_convergence(summary: dict[str, Any], out_dir: Path) -> list[Path]:
    """Statistics vs sample size with bootstrap intervals: the study checking itself."""
    blocks = {label: block for label, block in summary["propagation"].items()
              if block.get("convergence", {}).get("table")}
    if not blocks:
        return []
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
    stats = ("mean", "p95")
    colours = [DEEP, HOT, ACCENT, INK, MUTED]
    for ax, stat in zip(axes, stats, strict=True):
        for i, (label, block) in enumerate(blocks.items()):
            table = pd.DataFrame(block["convergence"]["table"])
            colour = colours[i % len(colours)]
            ax.plot(table["n"], table[stat], color=colour, lw=1.4, marker="o", ms=3,
                    label=label)
            ax.fill_between(table["n"], table[f"{stat}__ci_lo"], table[f"{stat}__ci_hi"],
                            color=colour, alpha=0.15, linewidth=0)
        output = next(iter(blocks.values()))["convergence"]["output"]
        ax.set_xlabel("Monte-Carlo samples used [-]")
        ax.set_ylabel(f"{stat} of {output} [{summary['units'].get(output, '')}]")
        ax.set_title(f"{stat}, with 95% bootstrap interval")
        ax.legend(fontsize=7)
    tol = next(iter(blocks.values()))["convergence"]["tolerance_rel"]
    fig.suptitle("Convergence of the reported statistics "
                 f"(declared tolerance: {tol * 100:g}% relative half-width)", fontsize=9.5)
    fig.tight_layout()
    return [save_figure(fig, out_dir, "M7_convergence",
                        _caption(summary, "shaded band is the percentile bootstrap"))]


def plot_attribution(summary: dict[str, Any], out_dir: Path) -> list[Path]:
    """Sobol' total-order indices: which uncertain input to go and measure next."""
    blocks = summary.get("attribution", {})
    usable = {label: b for label, b in blocks.items() if b.get("outputs")}
    if not usable:
        return []
    label, block = next(iter(usable.items()))
    outputs = list(block["outputs"])
    names = [i["name"] for i in block["inputs"]]
    kinds = [i["kind"] for i in block["inputs"]]
    fig, axes = plt.subplots(1, len(outputs), figsize=(4.6 * len(outputs), 4.4),
                             sharey=True)
    axes = np.atleast_1d(axes)
    for ax, output in zip(axes, outputs, strict=True):
        data = block["outputs"][output]
        total = np.asarray(data["total"], dtype=float)
        ci = np.asarray(data["total_ci"], dtype=float)
        order = np.argsort(total)
        y = np.arange(len(order))
        for pos, idx in zip(y, order, strict=True):
            style = EPISTEMIC_STYLE if kinds[idx] == "epistemic" else ALEATORY_STYLE
            ax.barh(pos, total[idx], color=style["color"], hatch=style["hatch"],
                    edgecolor="white", height=0.66)
            ax.plot([ci[idx, 0], ci[idx, 1]], [pos, pos], color=INK, lw=1.1)
        ax.set_yticks(y, [names[i] for i in order], fontsize=7.5)
        ax.set_xlabel("Sobol' total-order index [-]")
        ax.set_title(output, fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=ALEATORY_STYLE["color"]),
               plt.Rectangle((0, 0), 1, 1, color=EPISTEMIC_STYLE["color"], hatch="///")]
    axes[-1].legend(handles, [ALEATORY_STYLE["label"], EPISTEMIC_STYLE["label"]],
                    fontsize=7, loc="lower right")
    fig.suptitle(f"Variance attribution on design '{label}' "
                 "(bars: total order; lines: 95% bootstrap interval)", fontsize=9.5)
    fig.tight_layout()
    return [save_figure(fig, out_dir, "M7_attribution",
                        _caption(summary, "an index on an EPISTEMIC input is a "
                                          "sensitivity to which model is believed, not a "
                                          "share of real variability"))]


# ---------------------------------------------------------------------------------------

def plot_robust_vs_nominal(summary: dict[str, Any], nominal_front: pd.DataFrame | None,
                           robust_front: pd.DataFrame | None, out_dir: Path) -> list[Path]:
    """What robustness costs: the nominal front, the robust front, and the distance the
    nominal designs move once uncertainty is switched on."""
    if robust_front is None or robust_front.empty:
        return []
    objectives = tuple(summary["objectives"])
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    if nominal_front is not None and not nominal_front.empty:
        ax.plot(nominal_front[objectives[0]], nominal_front[objectives[1]], color=MUTED,
                lw=1.2, marker="o", ms=3, label="nominal front (M4, re-evaluated)")
    percentile = summary["robust"]["settings"]["objective_percentile"]
    ax.plot(robust_front[f"robust__{objectives[0]}"],
            robust_front[f"robust__{objectives[1]}"], color=DEEP, lw=1.6, marker="s",
            ms=4, label=f"robust front ({percentile:g}th percentile)")
    # Only designs that an OPTIMISER selected: the reference capsule is not a
    # "nominal-optimal design" and arrowing it would say it was.
    moved = [e for e in summary.get("nominal_designs_under_uncertainty", [])
             if e.get("is_nominal_optimum")]
    for i, entry in enumerate(moved):
        ax.annotate("", xy=(entry["p95"][objectives[0]], entry["p95"][objectives[1]]),
                    xytext=(entry["nominal"][objectives[0]],
                            entry["nominal"][objectives[1]]),
                    arrowprops={"arrowstyle": "->", "color": HOT, "lw": 1.1})
        ax.scatter([entry["nominal"][objectives[0]]], [entry["nominal"][objectives[1]]],
                   color=HOT, s=26, zorder=5,
                   label="nominal-optimal design, nominal value" if i == 0 else None)
    allowable = summary.get("allowables", {}).get(objectives[1])
    if allowable is not None:
        ax.axhline(float(allowable), color=HOT, ls="--", lw=1.1, label="bondline allowable")
    ax.set_xlabel(f"{objectives[0]} [{summary['units'].get(objectives[0], '')}]")
    ax.set_ylabel(f"{objectives[1]} [{summary['units'].get(objectives[1], '')}]")
    ax.set_title("Nominal vs robust Pareto fronts")
    ax.legend(fontsize=7)
    fig.tight_layout()
    return [save_figure(fig, out_dir, "M7_robust_vs_nominal",
                        _caption(summary, "arrows run from each nominal-optimal design's "
                                          "nominal objective to its 95th percentile"))]


def plot_shortcut_verification(summary: dict[str, Any], out_dir: Path) -> list[Path]:
    """Shortcut robust objective against full independent Monte Carlo, on a subset."""
    block = summary.get("robust", {}).get("verification")
    if not block or not block.get("per_design"):
        return []
    objectives = tuple(summary["objectives"])
    rows = pd.DataFrame(block["per_design"])
    fig, axes = plt.subplots(1, len(objectives), figsize=(4.8 * len(objectives), 4.4))
    axes = np.atleast_1d(axes)
    for ax, name in zip(axes, objectives, strict=True):
        short = rows[f"shortcut__{name}"].to_numpy(dtype=float)
        full = rows[f"full__{name}"].to_numpy(dtype=float)
        lo = float(np.nanmin([short.min(), full.min()]))
        hi = float(np.nanmax([short.max(), full.max()]))
        ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1.0, ls="--", label="exact agreement")
        ax.scatter(full, short, color=DEEP, s=36, zorder=4)
        stats = block["objectives"][name]
        ax.set_xlabel(f"full MC, n = {block['n_full']} [{summary['units'].get(name, '')}]")
        ax.set_ylabel(f"shortcut, n = {block['n_inner']} + CRN "
                      f"[{summary['units'].get(name, '')}]")
        ax.set_title(f"{name}\nbias {stats['mean_relative_bias'] * 100:+.2f}%, "
                     f"Spearman {stats['spearman_rank_correlation']:.3f}", fontsize=8.5)
        ax.legend(fontsize=7)
    verdict = "PASSED" if block["verdict"]["passed"] else "FAILED"
    fig.suptitle(f"Verification of the common-random-number shortcut: {verdict}",
                 fontsize=9.5)
    fig.tight_layout()
    return [save_figure(fig, out_dir, "M7_shortcut_verification",
                        _caption(summary, "declared tolerances: "
                                 + ", ".join(f"{k} {v:g}" for k, v in
                                             block["tolerances"].items())))]


def plot_all(summary: dict[str, Any], frames: dict[str, pd.DataFrame],
             branch_index: dict[str, np.ndarray], nominal_front: pd.DataFrame | None,
             robust_front_frame: pd.DataFrame | None, out_dir: Path) -> list[Path]:
    """Every M7 figure that the available results support. Missing pieces are skipped,
    never faked - a figure with no data behind it is not drawn."""
    figures: list[Path] = []
    figures += plot_input_inventory(summary, out_dir)
    if frames:
        figures += plot_output_distributions(summary, frames, out_dir)
        if branch_index:
            figures += plot_pbox(summary, frames, branch_index, out_dir)
    figures += plot_convergence(summary, out_dir)
    figures += plot_attribution(summary, out_dir)
    figures += plot_robust_vs_nominal(summary, nominal_front, robust_front_frame, out_dir)
    figures += plot_shortcut_verification(summary, out_dir)
    return figures
