"""Milestone-M3 figures (spec §34). Every mark is read from a results file.

House palette and `_save` (PDF + PNG + caption with run ID) come from `aether.viz`. Series
identity is never colour alone: each series also has its own marker or line style, and
every multi-series panel has a legend.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..viz import ACCENT, DEEP, GRID, HOT, INK, MUTED, _save, plt
from .cfd_surface import MODEL_NAME, SHAPE_INPUTS, CfdDragSurface, gate_g4_status, load_surface


def gate_label() -> str:
    """Caption suffix stating the gate status. READ from the current surface's `surface.json`
    and from M2's `gate_assessment.json`; v1's figures carried a typed string here."""
    try:
        at_build = str(load_surface().meta.get("gate_G4_status_at_build", "UNKNOWN"))
    except FileNotFoundError:
        at_build = "UNKNOWN"
    now = gate_g4_status()["status"]
    if at_build == "PASS" and now == "PASS":
        return "Gate G4 PASS at build and now (read from M2's gate file)"
    return f"PROVISIONAL: gate G4 {at_build} at build, {now} now"
SERIES = [(INK, "-", "o"), (DEEP, "--", "s"), (HOT, "-.", "^"), (ACCENT, ":", "D"),
          (MUTED, "-", "v")]
VERDICT_STYLE = {"USABLE": (DEEP, "o"), "REJECTED": (ACCENT, "X"),
                 "SOLVER_FAILED": (HOT, "P"), "MESH_FAILED": (MUTED, "s"),
                 "POSTPROCESS_FAILED": (MUTED, "D")}


def _mach_axis(ax) -> None:
    from matplotlib.ticker import NullFormatter

    ax.set_xscale("log")
    ax.set_xticks([3, 5, 10, 20, 27], labels=["3", "5", "10", "20", "27"])
    ax.xaxis.set_minor_formatter(NullFormatter())


def _grid(ax) -> None:
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def plot_design_coverage(table: pd.DataFrame, skipped: pd.DataFrame, run_id: str,
                         level: str, out_dir: Path) -> Path:
    pts = table[table["role"] != "scale_check"]
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.8))
    pairs = [("bluntness_ratio", "cone_half_angle_deg"), ("mach", "cone_half_angle_deg"),
             ("bluntness_ratio", "shoulder_ratio")]
    names = {"bluntness_ratio": "bluntness ratio  $R_n/D$  [-]",
             "cone_half_angle_deg": "cone half-angle  [deg]",
             "shoulder_ratio": "shoulder ratio  $R_c/D$  [-]", "mach": "Mach number  [-]"}
    for ax, (xk, yk) in zip(axes, pairs, strict=True):
        if len(skipped) and xk in skipped and yk in skipped:
            ax.scatter(skipped[xk], skipped[yk], s=14, marker="x", color=GRID, lw=1.0,
                       label=f"skipped: invalid geometry ({len(skipped)})")
        for verdict, grp in pts.groupby("verdict"):
            col, mk = VERDICT_STYLE.get(verdict, (MUTED, "h"))
            ax.scatter(grp[xk], grp[yk], s=30, marker=mk, color=col, edgecolor="white",
                       lw=0.6, label=f"{verdict} ({len(grp)})", zorder=3)
        if xk == "mach":
            _mach_axis(ax)
        ax.set_xlabel(names[xk])
        ax.set_ylabel(names[yk])
        _grid(ax)
    axes[0].legend(fontsize=6.5, loc="lower right")
    axes[1].set_title(f"CFD design points, {level} mesh")
    fig.tight_layout()
    return _save(fig, out_dir, "M3_design_coverage",
                 f"Planned CFD design (anchors on the hull + scrambled-Sobol fill) and the "
                 f"verdict of each case. Run {run_id}. {gate_label()}.")


def plot_cd_vs_mach(surface: CfdDragSurface, shapes: dict[str, dict[str, float]],
                    table: pd.DataFrame, run_id: str, out_dir: Path) -> Path:
    mach = np.exp(np.linspace(np.log(surface.mach_min), np.log(surface.mach_max), 80))
    fig, (ax, axb) = plt.subplots(1, 2, figsize=(10.4, 4.2), sharey=True)
    usable = table[(table["verdict"] == "USABLE") & (table["role"] != "scale_check")]
    for (col, ls, mk), (name, shape) in zip(SERIES, shapes.items(), strict=False):
        p = surface.predict_fore(mach, shape, on_extrapolation="flag")
        tag = " (outside hull)" if np.any(p.extrapolated) else ""
        ax.plot(mach, p.central, ls, color=col, lw=1.6, label=f"{name}{tag}")
        ax.fill_between(mach, p.central - 2 * p.std, p.central + 2 * p.std, color=col,
                        alpha=0.13, lw=0)
        same = usable[np.all([np.isclose(usable[k], shape[k], atol=1e-6)
                              for k in SHAPE_INPUTS], axis=0)]
        ax.scatter(same["mach"], same["cd_fore"], marker=mk, s=34, color=col,
                   edgecolor="white", lw=0.7, zorder=4)
        lo, nom, hi = surface.base.band(mach)
        axb.plot(mach, p.central + nom, ls, color=col, lw=1.6, label=name)
        axb.fill_between(mach, p.central + lo, p.central + hi, color=col, alpha=0.13, lw=0)
    for a, title in ((ax, "forebody: GP mean, band = ±2σ (GP only); markers = CFD cases"),
                     (axb, "total = forebody + base assumption; band = base-pressure band")):
        _mach_axis(a)
        a.set_xlabel("freestream Mach number  [-]")
        a.set_title(title, fontsize=8.5)
        a.set_ylim(bottom=0.0)
        _grid(a)
    ax.set_ylabel("drag coefficient  $C_D$  [-]  (ref. area πD²/4)")
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    return _save(fig, out_dir, "M3_cd_vs_mach",
                 f"{MODEL_NAME} along Mach for named shapes; inviscid perfect gas, α = 0. "
                 f"Surface hash {surface.meta['training_hash']}, run {run_id}. {gate_label()}.")


def plot_cv_parity(folds: pd.DataFrame, run_id: str, out_dir: Path) -> Path:
    fig, (ax, axr) = plt.subplots(1, 2, figsize=(9.6, 4.2))
    for flag, col, mk, lab in ((False, DEEP, "o", "inside the fold's hull"),
                               (True, ACCENT, "X", "outside the fold's hull (extrapolated)")):
        g = folds[folds["outside_fold_hull"] == flag]
        if g.empty:
            continue
        ax.errorbar(g["cd_fore_cfd"], g["cd_fore_pred"], yerr=2 * g["cd_fore_std"], fmt=mk,
                    ms=5, color=col, ecolor=col, elinewidth=0.7, alpha=0.9, mec="white",
                    mew=0.5, label=f"{lab} (n={len(g)})")
        axr.scatter(g["mach"], 100 * (g["cd_fore_pred"] / g["cd_fore_cfd"] - 1), marker=mk,
                    s=30, color=col, edgecolor="white", lw=0.5, label=lab)
    lim = [0.0, float(max(folds["cd_fore_cfd"].max(), folds["cd_fore_pred"].max()) * 1.05)]
    ax.plot(lim, lim, color=MUTED, lw=0.8)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("CFD  $C_{D,fore}$  [-]")
    ax.set_ylabel("out-of-fold GP prediction ± 2σ  [-]")
    ax.set_title("k-fold cross-validation parity")
    ax.legend(fontsize=7, loc="upper left")
    axr.axhline(0.0, color=MUTED, lw=0.8)
    _mach_axis(axr)
    axr.set_xlabel("freestream Mach number  [-]")
    axr.set_ylabel("prediction error  [% of CFD value]")
    axr.set_title("out-of-fold error against Mach")
    for a in (ax, axr):
        _grid(a)
    fig.tight_layout()
    return _save(fig, out_dir, "M3_surface_cv",
                 f"Every usable CFD point predicted by a GP that did not see it. Run {run_id}. "
                 f"{gate_label()}.")


def plot_base_fraction(base: pd.DataFrame, run_id: str, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for (col, ls, mk), (name, g) in zip(SERIES, base.groupby("shape", sort=False), strict=False):
        ax.plot(g["mach"], 100 * g["base_fraction_nominal"], ls, marker=mk, ms=4.5, color=col,
                lw=1.5, label=f"{name}: nominal")
        ax.fill_between(g["mach"], 100 * g["base_fraction_low"], 100 * g["base_fraction_high"],
                        color=col, alpha=0.12, lw=0)
    ax.axhline(0.0, color=MUTED, lw=0.8)
    _mach_axis(ax)
    ax.set_xlabel("freestream Mach number  [-]")
    ax.set_ylabel("base drag / total drag  [%]")
    ax.set_title("Assumed base drag as a share of total $C_D$ (band = base-pressure band)")
    ax.legend(fontsize=7)
    _grid(ax)
    fig.tight_layout()
    return _save(fig, out_dir, "M3_base_drag_fraction",
                 "C_D,base = (1 - p_b/p_inf)·2/(γM²): an assumption, not CFD. Band: p_b/p_inf "
                 "from 0 (exact vacuum limit) up to 1 (M ≤ 6) … 3 (M ≥ 10, NASA TN D-4800 fig. "
                 f"11b, read by eye). Negative = base pressure above freestream. Run {run_id}. "
                 f"{gate_label()}.")


def plot_constant_vs_surface(summary: dict, run_id: str, out_dir: Path) -> Path:
    moves = pd.DataFrame(summary["constant_vs_surface"])
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.9), sharey=True)
    y = np.arange(len(moves))
    spec = [("peak_heat_flux_rel_change", 100.0, "peak heat flux change  [%]", HOT),
            ("peak_bondline_change_k", 1.0, "peak bondline change  [K]", DEEP),
            ("max_g_rel_change", 100.0, "peak deceleration change  [%]", INK)]
    for ax, (key, scale, label, col) in zip(axes, spec, strict=True):
        vals = scale * moves[key]
        ax.hlines(y, 0.0, vals, color=col, lw=1.4)
        ax.scatter(vals, y, s=36, color=col, edgecolor="white", lw=0.7, zorder=3)
        for yi, v in zip(y, vals, strict=True):
            ax.annotate(f"{v:+.2f}", (v, yi), textcoords="offset points", xytext=(0, 7),
                        ha="center", fontsize=7, color=INK)
        ax.axvline(0.0, color=MUTED, lw=0.8)
        ax.set_xlabel(label)
        _grid(ax)
    labels = [f"{d}\n$C_D$ {c:.2f} → {s:.3f}" + ("  [outside hull]" if e else "")
              for d, c, s, e in zip(moves["design"], moves["cd_constant"],
                                    moves["cd_surface_at_peak_heating"],
                                    moves["shape_extrapolated"], strict=True)]
    axes[0].set_yticks(y, labels=labels, fontsize=6.5)
    axes[0].invert_yaxis()
    axes[1].set_title("CFD drag surface relative to constant $C_D$, same design")
    fig.tight_layout()
    return _save(fig, out_dir, "M3_constant_vs_surface",
                 "Each design evaluated twice through evaluate_design: constant C_D (Fidelity 0) "
                 f"and {MODEL_NAME} (Fidelity 1). C_D shown: constant → surface value at peak "
                 f"heating. Run {run_id}. {gate_label()}.")


def plot_shape_sweep(shape: pd.DataFrame, run_id: str, out_dir: Path) -> Path:
    piv = shape.pivot_table(index=["bluntness_ratio", "cone_half_angle_deg"], columns="arm",
                            values=["peak_heat_flux_w_m2", "aero_cd_at_peak_heating",
                                    "aero_shape_extrapolated"], aggfunc="first").dropna(
        subset=[("peak_heat_flux_w_m2", "surface"), ("peak_heat_flux_w_m2", "constant")])
    fig, (ax, axc) = plt.subplots(1, 2, figsize=(9.8, 4.1))
    for (col, ls, mk), (b, g) in zip(SERIES, piv.groupby(level=0), strict=False):
        theta = g.index.get_level_values(1)
        inside = g[("aero_shape_extrapolated", "surface")] == 0.0
        rel = 100 * (g[("peak_heat_flux_w_m2", "surface")]
                     / g[("peak_heat_flux_w_m2", "constant")] - 1.0)
        ax.plot(theta[inside], rel[inside], ls, marker=mk, ms=5, color=col, lw=1.5,
                label=f"$R_n/D$ = {b:g}")
        axc.plot(theta[inside], g[("aero_cd_at_peak_heating", "surface")][inside], ls,
                 marker=mk, ms=5, color=col, lw=1.5, label=f"$R_n/D$ = {b:g}")
    ax.axhline(0.0, color=MUTED, lw=0.8)
    ax.set_xlabel("cone half-angle  [deg]")
    ax.set_ylabel("peak heat flux: surface vs constant $C_D$  [%]")
    ax.set_title("Shape acting THROUGH DRAG (zero by construction at constant $C_D$)",
                 fontsize=8.5)
    axc.set_xlabel("cone half-angle  [deg]")
    axc.set_ylabel("surface $C_D$ at peak heating  [-]")
    axc.set_ylim(bottom=0.0)
    axc.set_title("the drag coefficient behind it", fontsize=8.5)
    ax.legend(fontsize=7)
    for a in (ax, axc):
        _grid(a)
    fig.tight_layout()
    return _save(fig, out_dir, "M3_shape_sweep",
                 "Reference capsule, mass, entry state; only the forebody shape varies. Shapes "
                 f"outside the CFD hull or geometrically invalid are not drawn. Run {run_id}. "
                 f"{gate_label()}.")
