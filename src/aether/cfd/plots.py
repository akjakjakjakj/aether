"""Milestone-M2 figures. Every curve is read from a results file; see spec §34.

All figures go through :func:`aether.viz._save`, which writes a vector PDF plus a PNG and
attaches the caption (with the run ID) below the axes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..viz import ACCENT, DEEP, HOT, INK, MUTED, _save, plt
from .reference import (
    billig_shock_x_m,
    billig_standoff_over_radius,
    normal_shock_density_ratio,
    stagnation_pressure_coefficient,
)

LEVEL_STYLE = {"coarse": (":", MUTED), "medium": ("--", DEEP), "fine": ("-", INK)}


def _cases(study: pd.DataFrame) -> pd.DataFrame:
    return study[study["status"] == "OK"]


def plot_force_histories(study: pd.DataFrame, run_dir: Path, cfg: dict, run_id: str,
                         out_dir: Path, candidates: pd.DataFrame | None = None) -> Path:
    """C_D history per case, with the declared convergence window and band drawn in.

    ``candidates`` (every solution that exists, incl. lower-Courant restarts and the cases
    that did NOT meet the criterion) are all drawn in the bottom row; a case that missed the
    criterion is drawn in the warning colour and says so in the legend."""
    crit = cfg["convergence_criterion"]
    cand = _cases(study if candidates is None else candidates)
    if "is_restart" not in cand:
        cand = cand.assign(is_restart=False, max_co=float(cfg["solver"]["max_co"]))
    machs = sorted(cand["mach"].unique())
    tail = 2 * int(crit["window_iterations"])
    fig, axes = plt.subplots(2, len(machs), figsize=(4.6 * len(machs), 6.6), squeeze=False)
    for j, mach in enumerate(machs):
        ax, axz = axes[0, j], axes[1, j]
        for _, c in cand[cand["mach"] == mach].iterrows():
            h = pd.read_csv(run_dir / c["case"] / "force_history.csv")
            ls, col = LEVEL_STYLE[c["level"]]
            met = bool(c["cd_fore_converged"])
            if c["is_restart"]:       # of the restarts, the largest Courant number is solid
                first = c["max_co"] == cand[(cand["mach"] == mach) & cand["is_restart"]][
                    "max_co"].max()
                ls, col = ("-" if first else "-."), ((ACCENT if first else INK) if met else HOT)
            elif not met:
                col = HOT
            if not c["is_restart"]:
                frac = h["iteration"] / h["iteration"].iloc[-1]
                ax.plot(frac, h["cd_total"], ls, color=col, lw=1.2,
                        label=f"{c['level']} ({int(c['n_cells']):,} cells, "
                              f"{int(c['n_iterations']):,} it.)"
                              + ("" if met else " - criterion NOT MET"))
            t = h[h["iteration"] >= h["iteration"].iloc[-1] - tail]
            axz.plot(t["iteration"] - h["iteration"].iloc[-1],
                     100.0 * (t["cd_total"] / c["cd_total"] - 1.0), ls, color=col,
                     lw=0.9 if met else 0.6, alpha=1.0 if met else 0.75,
                     label=f"{c['level']}, max Co {c['max_co']:g}: p-p "
                           f"{100 * c['cd_fore_peak_to_peak_rel']:.3f}% - "
                           + ("met" if met else "NOT MET"))
        band = 50.0 * crit["max_peak_to_peak_rel"]
        axz.axhspan(-band, band, color=MUTED, alpha=0.18,
                    label=f"declared band: peak-to-peak ≤ {100 * crit['max_peak_to_peak_rel']:g}%")
        axz.axvline(-crit["window_iterations"], color=MUTED, lw=0.7, ls=":")
        axz.set_ylim(-0.3, 0.3)
        ax.set_ylim(0.0, 1.6)
        ax.set_title(f"sphere, $M_\\infty$ = {mach:g}")
        ax.set_ylabel("forebody drag coefficient  $C_D$  [-]")
        ax.set_xlabel("fraction of the case's iterations  [-]")
        axz.set_ylabel("$C_D$ deviation from final-window mean  [%]")
        axz.set_xlabel("iterations before the end of the case  [-]")
        ax.legend(fontsize=7, loc="lower right")
        axz.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1)
    fig.tight_layout()
    return _save(fig, out_dir, "M2_force_convergence",
                 f"AETHER M2 · run {run_id} · rhoCentralFoam, Euler, local time stepping. "
                 f"Top: full history of the original cases, axis from zero. Bottom: EVERY "
                 f"solution (originals and lower-Courant restarts), last {tail} iterations, "
                 f"±0.3% about the mean of the last {crit['window_iterations']} iterations "
                 f"(right of the dotted line = judged window). Cases that did not meet the "
                 f"declared criterion are drawn in the warning colour and labelled NOT MET.")


def plot_limit_cycle(diagnostics: list[tuple[str, float, dict, pd.DataFrame, pd.DataFrame]],
                     run_id: str, out_dir: Path) -> Path:
    """Where the fine-mesh C_D limit cycle lives. One column per diagnosed case:
    (case name, Mach, summary, per-cell table, every-iteration force history)."""
    n = len(diagnostics)
    fig, axes = plt.subplots(2, n, figsize=(4.8 * n, 7.4), squeeze=False,
                             gridspec_kw={"height_ratios": [2.2, 1.0]})
    for j, (case, mach, summ, cells, hist) in enumerate(diagnostics):
        ax, axh = axes[0, j], axes[1, j]
        rel = np.maximum(cells["p_std_over_p_inf"] / cells["p_mean_over_p_inf"], 1e-7)
        sc = ax.scatter(cells["x_m"], cells["r_m"], c=np.log10(rel), s=0.5, cmap="cividis",
                        vmin=-6.0, vmax=-1.5, rasterized=True)
        fig.colorbar(sc, ax=ax, shrink=0.8,
                     label="log$_{10}$( std of $p$ over the cycle / mean $p$ )  [-]")
        ax.set_aspect("equal")
        ax.set_xlabel("axial position  $x$  [m]")
        ax.set_ylabel("radius  $r$  [m]")
        ax.set_title(f"{case}, $M_\\infty$ = {mach:g}", fontsize=9)
        fc = summ["force_cycle_every_iteration"]
        axh.plot(hist["iteration"] - hist["iteration"].iloc[0],
                 100.0 * (hist["cd_fore"] / fc["mean"] - 1.0), color=INK, lw=0.9)
        axh.axhline(0.0, color=MUTED, lw=0.6)
        axh.set_xlabel(f"iterations after iteration {summ['source_iteration']:,}  [-]")
        axh.set_ylabel("$C_D$ deviation from mean  [%]")
        axh.set_title(f"period ≈ {fc['dominant_period_iterations']:.0f} iterations "
                      f"= {fc['dominant_period_cell_transit_times']:.1f} cell-transit times; "
                      f"peak-to-peak {100 * fc['peak_to_peak_rel']:.2f}%", fontsize=8)
    fig.tight_layout()
    return _save(fig, out_dir, "M2_limit_cycle",
                 f"AETHER M2 · run {run_id} · the original fine cases (max Courant 0.2), "
                 f"continued for a few periods with the pressure field written every 2 "
                 f"iterations and the force every iteration. Top: relative pressure "
                 f"fluctuation per cell (log colour scale, legend on the bar). Bottom: "
                 f"forebody C_D sampled every iteration.")


def plot_residuals(study: pd.DataFrame, run_dir: Path, run_id: str, out_dir: Path) -> Path:
    machs = sorted(_cases(study)["mach"].unique())
    fig, axes = plt.subplots(1, len(machs), figsize=(3.9 * len(machs), 3.4), squeeze=False,
                             sharey=True)
    for j, mach in enumerate(machs):
        ax = axes[0, j]
        for _, c in _cases(study)[study["mach"] == mach].iterrows():
            h = pd.read_csv(run_dir / c["case"] / "force_history.csv")
            ls, col = LEVEL_STYLE[c["level"]]
            r = h["mean_abs_drho_dtau_kg_m3_s"]
            met = bool(c.get("cd_fore_converged", True))
            ax.semilogy(h["iteration"] / h["iteration"].iloc[-1], r / r.iloc[0], ls,
                        color=col if met else HOT, lw=1.0,
                        label=c["level"] + ("" if met else " (force criterion NOT met)"))
        ax.set_title(f"sphere, $M_\\infty$ = {mach:g}")
        ax.set_xlabel("fraction of the run's iterations  [-]")
        ax.legend(fontsize=7)
    axes[0, 0].set_ylabel("volume-mean $|\\partial\\rho/\\partial\\tau|$ / initial value  [-]")
    fig.tight_layout()
    return _save(fig, out_dir, "M2_residuals",
                 f"AETHER M2 · run {run_id}. ORIGINAL cases (max Courant 0.2; the lower-Courant "
                 f"restarts are in the report's table). Steady-state density residual in local "
                 f"pseudo-time τ, normalised by its first recorded value. rhoCentralFoam's "
                 f"explicit (diagonal) solves report no linear-solver residual, so this is the "
                 f"residual of record.")


def plot_mesh_convergence(study: pd.DataFrame, gci: pd.DataFrame, run_id: str,
                          out_dir: Path) -> Path:
    quantities = [("cd_fore", "forebody $C_D$  [-]"),
                  ("standoff_over_max_radius", "shock stand-off  $\\Delta/R$  [-]"),
                  ("p_stag_over_p_inf", "stagnation pressure  $p_0/p_\\infty$  [-]")]
    machs = sorted(_cases(study)["mach"].unique())
    fig, axes = plt.subplots(len(machs), 3, figsize=(10.0, 3.9 * len(machs)), squeeze=False)
    for i, mach in enumerate(machs):
        g = _cases(study)[study["mach"] == mach].sort_values("h_m")
        h_rel = g["h_m"] / g["h_m"].min()
        for j, (q, label) in enumerate(quantities):
            ax = axes[i, j]
            ax.plot(h_rel, g[q], "-o", color=INK, ms=4, lw=1.0, label="CFD")
            row = gci[(gci["mach"] == mach) & (gci["quantity"] == q)]
            if len(row) and np.isfinite(row["phi_extrapolated"].iloc[0]):
                r = row.iloc[0]
                ax.plot([0.0], [r["phi_extrapolated"]], "D", color=HOT, ms=5,
                        label=f"Richardson, p = {r['observed_order']:.2f} "
                              f"({r['convergence_type']})")
                ax.errorbar([1.0], [r["phi_fine"]], yerr=[r["gci_fine"] * abs(r["phi_fine"])],
                            color=DEEP, capsize=3, lw=1.0, fmt="none",
                            label=f"GCI$_{{fine}}$ = {100 * r['gci_fine']:.2f}%")
            ax.set_xlim(-0.3, 4.4)
            ax.set_xlabel("relative cell size  $h/h_{fine}$  [-]")
            ax.set_ylabel(label)
            ax.set_title(f"$M_\\infty$ = {mach:g}", fontsize=9)
            ax.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.24))
    fig.tight_layout()
    return _save(fig, out_dir, "M2_mesh_convergence",
                 f"AETHER M2 · run {run_id} · fine level = solution of record "
                 f"({', '.join(_cases(study)[study['level'] == 'fine']['case'])}) · "
                 f"sphere, three geometrically similar meshes, "
                 f"refinement ratio 2. Procedure of Celik et al. (2008). The y-axes are "
                 f"deliberately zoomed to the variation between meshes; the absolute values "
                 f"are in the report's tables.")


def plot_benchmark(study: pd.DataFrame, run_dir: Path, cfg: dict, run_id: str,
                   out_dir: Path) -> Path:
    """Stagnation-line density (shock position) and surface Cp, against the references."""
    ref = yaml.safe_load(open(Path(run_dir).parents[2] / cfg["benchmark"]["reference_data"]))
    vdg = {r["mach"]: r["standoff_over_radius"]
           for r in ref["sphere_standoff_over_radius"]["rows"]}
    radius = float(cfg["benchmark"]["radius_m"])
    gamma = float(cfg["gas"]["gamma"])
    machs = sorted(_cases(study)["mach"].unique())
    fig, axes = plt.subplots(2, len(machs), figsize=(4.1 * len(machs), 6.0), squeeze=False)
    for j, mach in enumerate(machs):
        ax, axc = axes[0, j], axes[1, j]
        rho_ratio = normal_shock_density_ratio(mach, gamma)
        for _, c in _cases(study)[study["mach"] == mach].iterrows():
            ls, col = LEVEL_STYLE[c["level"]]
            line = pd.read_csv(run_dir / c["case"] / "stagnation_line.csv")
            ax.plot(-line["x_m"] / radius, line["rho"] / line["rho"].iloc[0], ls, color=col,
                    lw=1.1, label=f"CFD {c['level']}")
            body = pd.read_csv(run_dir / c["case"] / "body_pressure.csv")
            theta = np.degrees(np.arccos(np.clip(1.0 - body["x_m"] / radius, -1, 1)))
            axc.plot(theta, body["cp"], ls, color=col, lw=1.1, label=f"CFD {c['level']}")
        if mach in vdg:
            ax.axvline(vdg[mach], color=HOT, lw=1.0, label="Van Dyke & Gordon (TR R-1)")
        ax.axvline(billig_standoff_over_radius(mach), color=ACCENT, lw=1.0, ls="--",
                   label="Billig correlation")
        ax.axhline(rho_ratio, color=MUTED, lw=0.7, ls=":")
        ax.annotate("Rankine–Hugoniot $\\rho_2/\\rho_\\infty$", (0.0, rho_ratio),
                    xytext=(2, 3), textcoords="offset points", fontsize=6.5, color=MUTED)
        ax.set_xlim(0.0, 1.6 * max(vdg.get(mach, 0), billig_standoff_over_radius(mach)))
        ax.set_ylim(0.0, None)
        ax.set_xlabel("distance upstream of the nose  $-x/R$  [-]")
        ax.set_ylabel("density on the stagnation line  $\\rho/\\rho_\\infty$  [-]")
        ax.set_title(f"sphere, $M_\\infty$ = {mach:g}")
        ax.legend(fontsize=6.5, loc="lower left")

        th = np.linspace(0.0, 90.0, 91)
        cp0 = stagnation_pressure_coefficient(mach, gamma)
        axc.plot(th, cp0 * np.cos(np.radians(th)) ** 2, color=ACCENT, lw=1.0, ls="--",
                 label="modified Newtonian (estimate)")
        axc.plot([0.0], [cp0], "D", color=HOT, ms=5, label="Rayleigh pitot $C_{p,0}$ (exact)")
        axc.axhline(0.0, color=MUTED, lw=0.6)
        axc.set_xlabel("angle from the stagnation point  $\\theta$  [deg]")
        axc.set_ylabel("surface pressure coefficient  $C_p$  [-]")
        axc.legend(fontsize=6.5)
    fig.tight_layout()
    return _save(fig, out_dir, "M2_benchmark",
                 f"AETHER M2 · run {run_id} · sphere, calorically perfect air, Euler. Top: the "
                 f"captured bow shock on the stagnation line against the published stand-off "
                 f"distances. Bottom: forebody surface pressure against angle from the stagnation "
                 f"point.")


def plot_flow_field(fields: pd.DataFrame, outline_xr: tuple[np.ndarray, np.ndarray],
                    mach: float, radius_for_billig_m: float | None, title: str, stem: str,
                    caption: str, out_dir: Path) -> Path:
    """Density field in the meridional plane, optionally with Billig's shock shape."""
    import matplotlib.tri as mtri

    xb, rb = outline_xr
    x_lo = fields["x_m"].min()
    x_hi = min(fields["x_m"].max(), xb.max() + 2.5 * rb.max())
    r_hi = min(fields["r_m"].max(), 3.2 * rb.max())
    # figure width follows the domain's aspect ratio, so an equal-aspect axes fills it
    fig, ax = plt.subplots(figsize=(max(4.6, 4.2 * (x_hi - x_lo) / r_hi + 2.4), 5.0))
    tri = mtri.Triangulation(fields["x_m"], fields["r_m"])
    # mask triangles whose centroid falls inside the body
    cx = fields["x_m"].to_numpy()[tri.triangles].mean(axis=1)
    cr = fields["r_m"].to_numpy()[tri.triangles].mean(axis=1)
    inside = (cx > xb.min()) & (cx < xb.max()) & (cr < np.interp(cx, xb, rb))
    tri.set_mask(inside)
    cs = ax.tricontourf(tri, fields["rho_over_rho_inf"], levels=24, cmap="cividis")
    cb = fig.colorbar(cs, ax=ax)
    cb.set_label("density  $\\rho/\\rho_\\infty$  [-]")
    cb.outline.set_edgecolor(MUTED)
    ax.fill_between(xb, 0.0, rb, color="white", zorder=3)
    ax.plot(xb, rb, color=INK, lw=1.0, zorder=4)
    if radius_for_billig_m:
        r = np.linspace(0.0, fields["r_m"].max(), 300)
        ax.plot(billig_shock_x_m(r, mach, radius_for_billig_m), r, color=HOT, lw=1.1, ls="--",
                zorder=5, label="Billig (1967) shock shape")
        ax.legend(fontsize=7, loc="upper left", frameon=True, facecolor="white",
                  edgecolor="none")
    ax.set_aspect("equal")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(0.0, r_hi)
    ax.set_xlabel("axial position  $x$  [m]")
    ax.set_ylabel("radius  $r$  [m]")
    ax.set_title(title)
    ax.grid(False)
    return _save(fig, out_dir, stem, caption)


def plot_demo_pressure(body: pd.DataFrame, title: str, stem: str, caption: str,
                       out_dir: Path) -> Path:
    fig, (axg, ax) = plt.subplots(2, 1, figsize=(6.0, 5.0), sharex=True,
                                  gridspec_kw={"height_ratios": [1, 1.6]})
    axg.fill_between(body["x_m"], 0.0, body["r_m"], color=MUTED, alpha=0.35)
    axg.plot(body["x_m"], body["r_m"], color=INK, lw=1.0)
    axg.set_ylabel("radius  $r$  [m]")
    axg.set_aspect("equal")
    axg.set_title(title)
    ax.plot(body["x_m"], body["cp"], "-", color=HOT, lw=1.2)
    ax.axhline(0.0, color=MUTED, lw=0.6)
    ax.set_xlabel("axial position  $x$  [m]")
    ax.set_ylabel("surface pressure coefficient  $C_p$  [-]")
    fig.tight_layout()
    return _save(fig, out_dir, stem, caption)
