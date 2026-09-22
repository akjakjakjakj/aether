"""The figures of the CFD flow-field gallery (reports/figures/cfd/).

Each ``fig_*`` function reads case directories and result tables, draws one figure through
:mod:`aether.cfd.gallery`, and registers it (or the reason it could not be drawn) with the
:class:`~aether.cfd.gallery.Gallery`. No number is typed here: coefficients come from
``case_result.json`` / the design tables, fields from the saved time directories.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..utils.run import REPO_ROOT
from ..viz import ACCENT, DEEP, HOT, INK, MUTED, plt
from . import validation as val
from .design_points import capsule_outline, forebody_capsule
from .gallery import (
    CAT_COLOURS,
    CAT_STYLES,
    LABEL,
    CaseView,
    Gallery,
    annotate_standoff,
    colorbar,
    draw_body,
    draw_cells,
    draw_contour,
    field_panel,
    frame,
    last_logged_iteration,
    load_case,
    load_flow,
    read_internal_field,
    read_wedge_mesh,
    result_json,
    saved_times,
    sonic_handle,
    tag,
)
from .outline import sphere_outline
from .plots import LEVEL_STYLE
from .reference import (
    billig_shock_x_m,
    billig_standoff_over_radius,
    stagnation_pressure_coefficient,
)

GEN = REPO_ROOT / "cfd" / "generated"
RES = REPO_ROOT / "results"
GAS = ("rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, "
       "T∞ = 220 K")


# ---------------------------------------------------------------------------------------
# M2 sphere benchmark
# ---------------------------------------------------------------------------------------

def _m2_cfg(m2: str) -> dict:
    snap = yaml.safe_load((RES / "M2" / m2 / "config_snapshot.yaml").read_text())
    return snap.get("config", snap)


def _sphere_xr(m2: str) -> tuple[np.ndarray, np.ndarray, float]:
    radius = float(_m2_cfg(m2)["benchmark"]["radius_m"])
    o = sphere_outline(radius)
    return o.x_m, o.r_m, radius


def _m2_case(m2: str, case: str, xr, time=None, flow=None) -> tuple[CaseView, dict]:
    view = load_case(GEN / m2 / case, xr, time=time, flow=flow)
    return view, result_json(RES / "M2" / m2 / case / "case_result.json").get("metrics", {})


def fig_sphere_four_panel(g: Gallery, m2: str, mach: float) -> None:
    case = f"sphere_M{mach:g}_fine_Co0p1"
    xb, rb, radius = _sphere_xr(m2)
    try:
        view, met = _m2_case(m2, case, (xb, rb))
    except (FileNotFoundError, ValueError) as e:
        g.cannot(f"sphere four-panel, Mach {mach:g}: {e}")
        return
    w = 4.3
    h = w * view.mesh.r_max / np.ptp(view.mesh.x_range) + 0.9
    fig, axes = plt.subplots(2, 2, figsize=(2 * w + 1.6, 2 * h))
    lims = {"mach": (0.0, mach), "p": (1.0, float(np.nanmax(view.fields["p"]))),
            "T": (1.0, float(np.nanmax(view.fields["T"]))),
            "rho": (1.0, float(np.nanmax(view.fields["rho"])))}
    for ax, f in zip(axes.ravel(), ("mach", "p", "T", "rho"), strict=False):
        field_panel(fig, ax, view, f, *lims[f], LABEL[f].split("  ")[0])
    ax = axes[0, 0]
    r = np.linspace(0.0, view.mesh.r_max, 400)
    ax.plot(billig_shock_x_m(r, mach, radius), r, color=HOT, lw=1.1, ls="--", zorder=6,
            label="Billig (1967) shock-shape correlation")
    ax.legend(handles=[*ax.get_legend_handles_labels()[0], sonic_handle()], fontsize=6.5,
              loc="upper left", frameon=True, facecolor="white", edgecolor="none")
    sd = met.get("standoff_m")
    if sd:
        annotate_standoff(axes[0, 1], sd, view.mesh.r_max,
                          f"Δ = {sd:.4f} m  (Δ/R = {sd / radius:.3f})")
    fig.suptitle(f"sphere forebody, $M_\\infty$ = {mach:g}, fine mesh, max Co 0.1 — "
                 f"{case}, iteration {view.time:,}", fontsize=10)
    fig.tight_layout()
    g.save(fig, f"M2_sphere_M{mach:g}_fine_fourpanel",
           f"AETHER M2 · run {m2} · case {case} · sphere R = {radius:g} m · M∞ = {mach:g} · "
           f"fine mesh (refinement factor 4, {view.mesh.n_cells:,} cells) · max Courant 0.1, "
           f"the solution of record after NR-25 · saved iteration {view.time:,}. {GAS}. One "
           f"flat polygon per cell. White line: sonic line M = 1 from the cell-centre "
           f"triangulation - it bounds the subsonic nose region and ALSO runs along the "
           f"captured shock, where M passes through 1 inside the 1-2 cells of numerical shock "
           f"thickness. Dashed: Billig's correlation for the shock SHAPE (independent "
           f"empirical curve, not a fit). Δ: shock stand-off from case_result.json (50% "
           f"density-rise point on the stagnation line). Colour bars: Mach viridis, p/p∞ "
           f"magma, T/T∞ cividis, ρ/ρ∞ viridis.",
           run_id=m2, cases=case, mach=f"{mach:g}", mesh_level="fine (x4)",
           time_step=f"{view.time}", field="Mach, p/p∞, T/T∞, ρ/ρ∞")


def fig_sphere_mesh_levels(g: Gallery, m2: str, mach: float = 6.0) -> None:
    xb, rb, radius = _sphere_xr(m2)
    specs = [("coarse", f"sphere_M{mach:g}_coarse", True),
             ("medium", f"sphere_M{mach:g}_medium", True),
             ("fine", f"sphere_M{mach:g}_fine_Co0p1", False)]
    views = []
    for level, case, edges in specs:
        try:
            v, met = _m2_case(m2, case, (xb, rb))
        except (FileNotFoundError, ValueError) as e:
            g.cannot(f"sphere mesh comparison, {case}: {e}")
            return
        views.append((level, v, met, edges))
    w = 3.9
    aspect = views[0][1].mesh.r_max / np.ptp(views[0][1].mesh.x_range)
    h = 0.8 * w * aspect + 1.0     # 0.8: the shared colour bar takes the rest of the width
    fig, axes = plt.subplots(1, 3, figsize=(3 * w + 1.2, h))
    pc = None
    for ax, (level, v, met, edges) in zip(axes, views, strict=False):
        pc = field_panel(fig, ax, v, "mach", 0.0, mach,
                         f"{level}: {v.mesh.n_cells:,} cells, max Co "
                         f"{met.get('max_co', 0.2):g}, it {v.time:,}", cbar=False, edges=edges)
        sd = met.get("standoff_m")
        if sd:
            tag(ax, f"$C_{{D,fore}}$ = {met['cd_fore']:.4f}\nΔ/R = {sd / radius:.4f}",
                loc="lower right")
    colorbar(fig, axes.tolist(), pc, LABEL["mach"], shrink=0.9, pad=0.02)
    axes[0].legend(handles=[sonic_handle()], fontsize=6.5, loc="upper left", frameon=True,
                   facecolor="white", edgecolor="none")
    fig.suptitle(f"sphere forebody, $M_\\infty$ = {mach:g}: Mach number on the three meshes "
                 f"(refinement ratio 2)", fontsize=10)
    g.save(fig, f"M2_sphere_M{mach:g}_mesh_levels",
           f"AETHER M2 · run {m2} · cases {', '.join(s[1] for s in specs)} · sphere R = "
           f"{radius:g} m · M∞ = {mach:g} · coarse / medium / fine = refinement factors 1 / 2 / "
           f"4 · saved iterations {', '.join(f'{v.time:,}' for _, v, _, _ in views)}. {GAS}. "
           f"Common colour scale (viridis, 0 to M∞). Cell edges are drawn on the coarse and "
           f"medium meshes so the refinement is visible; on the fine mesh "
           f"({views[2][1].mesh.n_cells:,} "
           f"cells) they would blacken the panel and are omitted. The fine panel is the max "
           f"Courant 0.1 restart of record (NR-25); coarse and medium ran at max Courant 0.2. "
           f"C_D,fore and Δ/R from each case_result.json.",
           run_id=m2, cases=", ".join(s[1] for s in specs), mach=f"{mach:g}",
           mesh_level="coarse, medium, fine",
           time_step=", ".join(str(v.time) for _, v, _, _ in views),
           field="Mach")


def fig_stagnation_lines(g: Gallery, m2: str) -> None:
    cfg = _m2_cfg(m2)
    radius = float(cfg["benchmark"]["radius_m"])
    machs = [float(m) for m in cfg["benchmark"]["mach_numbers"]]
    levels = [("coarse", "{c}_coarse"), ("medium", "{c}_medium"), ("fine", "{c}_fine_Co0p1")]
    fig, axes = plt.subplots(4, len(machs), figsize=(4.4 * len(machs), 9.2), squeeze=False,
                             sharex="col")
    used, times = [], []
    for j, mach in enumerate(machs):
        stem = f"sphere_M{mach:g}"
        flow = val._flow(cfg, mach)
        for level, pat in levels:
            case = pat.format(c=stem)
            f = RES / "M2" / m2 / case / "stagnation_line.csv"
            if not f.exists():
                g.cannot(f"stagnation-line profile {case}: {f} missing")
                continue
            line = pd.read_csv(f)
            met = result_json(RES / "M2" / m2 / case / "case_result.json").get("metrics", {})
            x = line["x_m"] / radius
            speed = np.sqrt(line["Ux"] ** 2 + line["Uy"] ** 2 + line["Uz"] ** 2)
            rows = [line["p"] / flow.pressure_pa, line["T"] / flow.temperature_k,
                    line["rho"] / flow.density_kg_m3,
                    speed / np.sqrt(flow.gamma * flow.gas_constant_j_kgk * line["T"])]
            ls, col = LEVEL_STYLE[level]
            for i, y in enumerate(rows):
                axes[i, j].plot(x, y, ls, color=col, lw=1.1, label=f"{level} ({case})")
                if met.get("standoff_m"):
                    axes[i, j].axvline(-met["standoff_m"] / radius, color=col, lw=0.6, ls=ls,
                                       alpha=0.7)
            if met.get("standoff_m"):
                axes[0, j].annotate(f"Δ/R {level} = {met['standoff_m'] / radius:.4f}",
                                    (-met["standoff_m"] / radius, 1.0),
                                    xytext=(-10, 6 + 9 * levels.index((level, pat))),
                                    textcoords="offset points", fontsize=6, color=col, ha="right")
            used.append(case)
            times.append(str(met.get("n_iterations", "?")))
        b = billig_standoff_over_radius(mach)
        for i in range(4):
            axes[i, j].axvline(-b, color=ACCENT, lw=0.9, ls="--",
                               label="Billig stand-off" if i == 0 else None)
        labels = ("$p/p_\\infty$  [-]", "$T/T_\\infty$  [-]", "$\\rho/\\rho_\\infty$  [-]",
                  "Mach number  [-]")
        for i, lab in enumerate(labels):
            axes[i, j].set_ylabel(lab)
        axes[0, j].set_title(f"sphere, $M_\\infty$ = {mach:g}: stagnation line (axis, r = 0)")
        axes[3, j].set_xlabel("axial position  $x/R$  [-]  (nose at 0, flow from the left)")
        axes[3, j].axhline(1.0, color=MUTED, lw=0.6, ls=":")
        axes[0, j].legend(fontsize=6.5, loc="upper left")
    fig.tight_layout()
    g.save(fig, "M2_sphere_stagnation_line_profiles",
           f"AETHER M2 · run {m2} · cases {', '.join(used)} · sphere R = {radius:g} m · "
           f"three meshes (coarse x1, medium x2, fine x4; the fine curve is the max Courant 0.1 "
           f"restart of record) · each sampled at its final iteration ({', '.join(times)}). "
           f"{GAS}. Sampled cell values along the symmetry axis (postProcess sampleLine). "
           f"Thin vertical lines: the shock stand-off Δ of each mesh (50% density-rise point, "
           f"case_result.json); dashed: Billig (1967) stand-off correlation. Line style AND "
           f"colour distinguish the meshes.",
           run_id=m2, cases=", ".join(used), mach=", ".join(f"{m:g}" for m in machs),
           mesh_level="coarse, medium, fine", time_step=", ".join(times),
           field="p/p∞, T/T∞, ρ/ρ∞, Mach on the axis")


# ---------------------------------------------------------------------------------------
# M2 limit cycle
# ---------------------------------------------------------------------------------------

def _log_rel(num: np.ndarray, den: np.ndarray, floor: float = 1e-9) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log10(np.maximum(np.abs(num) / np.abs(den), floor))


def _layer_mask(case_dir: Path, time: int, flow) -> np.ndarray:
    """Cells behind the captured shock: rho/rho_inf > 1.5 at the given saved iteration."""
    return read_internal_field(Path(case_dir) / str(time) / "rho") / flow.density_kg_m3 > 1.5


def fig_limit_cycle(g: Gallery, m2: str, mach: float) -> None:
    xb, rb, radius = _sphere_xr(m2)
    src, diag, rec = (GEN / m2 / f"sphere_M{mach:g}_fine{s}" for s in ("", "_cyclediag", "_Co0p1"))
    if not src.exists():
        g.cannot(f"limit cycle Mach {mach:g}: {src} missing")
        return
    flow = load_flow(src)
    src_t = saved_times(src)
    diag_t = [t for t in saved_times(diag) if t not in src_t] if diag.exists() else []
    rec_t = saved_times(rec) if rec.exists() else []
    vmin, vmax = -4.5, -1.0
    panels, stats = [], {}   # (title, mesh, values, kind)

    def stat(tag_, r, layer):
        stats[tag_] = (float(r.max()), float(np.median(r[layer])), float((r[layer] > 1e-3).mean()))
        return f"max {r.max():.1e} · median in the shock layer {np.median(r[layer]):.1e}"

    if len(diag_t) >= 2:
        mesh = read_wedge_mesh(diag)
        P = np.vstack([read_internal_field(diag / str(t) / "p") for t in diag_t])
        rms = P.std(0) / P.mean(0)
        layer = _layer_mask(diag, diag_t[-1], flow)
        panels.append((f"(a) {diag.name}, max Co 0.2\nrms of p over {len(diag_t)} snapshots, "
                       f"it {diag_t[0]:,}–{diag_t[-1]:,} every {diag_t[1] - diag_t[0]}\n"
                       + stat("a", rms, layer), mesh, np.log10(np.maximum(rms, 1e-9)), "log"))
    else:
        g.cannot(f"limit cycle Mach {mach:g}: {diag.name} has {len(diag_t)} snapshots; the rms "
                 f"field needs at least two")
    if len(src_t) >= 2:
        mesh = read_wedge_mesh(src)
        p1, p0 = (read_internal_field(src / str(t) / "p") for t in (src_t[-1], src_t[-2]))
        r = np.abs(p1 - p0) / p1
        title = (f"(b) {src.name}, max Co 0.2\n|p(it {src_t[-1]:,}) − p(it {src_t[-2]:,})| / p, "
                 f"saved fields {src_t[-1] - src_t[-2]:,} it apart\n"
                 + stat("b", r, _layer_mask(src, src_t[-1], flow)))
        panels.append((title, mesh, _log_rel(p1 - p0, p1), "log"))
    else:
        g.cannot(f"limit cycle Mach {mach:g}: {src.name} has only {src_t} saved; the two-time "
                 f"difference needs two saved iterations")
    if len(rec_t) >= 2:
        mesh = read_wedge_mesh(rec)
        p1, p0 = (read_internal_field(rec / str(t) / "p") for t in (rec_t[-1], rec_t[-2]))
        r = np.abs(p1 - p0) / p1
        title = (f"(c) {rec.name}, max Co 0.1 (of record)\n|p(it {rec_t[-1]:,}) − "
                 f"p(it {rec_t[-2]:,})| / p, saved fields {rec_t[-1] - rec_t[-2]:,} it apart\n"
                 + stat("c", r, _layer_mask(rec, rec_t[-1], flow)))
        panels.append((title, mesh, _log_rel(p1 - p0, p1), "log"))
        panels.append((f"(d) {rec.name}\np/p∞ at it {rec_t[-1]:,} (the field of record)\n ",
                       mesh, p1 / flow.pressure_pa, "p"))
    else:
        g.cannot(f"limit cycle Mach {mach:g}: {rec.name} has {rec_t} saved iterations")
    if not panels:
        return
    xbf, rbf = xb[: int(np.argmax(rb)) + 1], rb[: int(np.argmax(rb)) + 1]
    w = 4.4
    m0 = panels[0][1]
    h = w * m0.r_max / np.ptp(m0.x_range) + 1.25
    n = len(panels)
    ncol = 2 if n > 1 else 1
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(ncol * w + 1.8, nrow * h), squeeze=False)
    for ax in axes.ravel()[n:]:
        ax.set_visible(False)
    for ax, (title, mesh, vals, kind) in zip(axes.ravel(), panels, strict=False):
        if kind == "log":
            pc = draw_cells(ax, mesh, vals, "T", vmin, vmax, cmap="cividis")
            draw_body(ax, xbf, rbf)
            frame(ax, mesh, xbf, rbf)
            colorbar(fig, ax, pc, "log$_{10}$( relative pressure fluctuation )  [-]", shrink=0.85,
                     pad=0.02)
        else:
            pc = draw_cells(ax, mesh, vals, "p", 1.0, float(np.nanmax(vals)))
            draw_body(ax, xbf, rbf)
            frame(ax, mesh, xbf, rbf)
            colorbar(fig, ax, pc, LABEL["p"], shrink=0.85, pad=0.02)
        ax.set_title(title, fontsize=7, loc="left")
    fig.suptitle(f"sphere forebody, $M_\\infty$ = {mach:g}, fine mesh: where the max-Courant-0.2 "
                 f"limit cycle lives (NR-25)", fontsize=10)
    fig.tight_layout()
    cases = ", ".join(d.name for d in (src, diag, rec) if d.exists())
    b, c = stats.get("b"), stats.get("c")
    compare = ""
    if b and c:
        compare = (f"The two-time difference does NOT separate the two Courant numbers by its "
                   f"maximum ({b[0]:.1e} vs {c[0]:.1e}, both in the cells the captured shock "
                   f"straddles near the outflow corner); it does by its level inside the shock "
                   f"layer: median {b[1]:.1e} vs {c[1]:.1e}, and {100 * b[2]:.0f}% vs "
                   f"{100 * c[2]:.0f}% of the layer's cells above 1e-3. ")
    g.save(fig, f"M2_sphere_M{mach:g}_limit_cycle_field",
           f"AETHER M2 · run {m2} · sphere R = {radius:g} m · M∞ = {mach:g} · fine mesh "
           f"({m0.n_cells:,} cells) · cases {cases}. {GAS}. (a) Per-cell standard deviation of "
           f"p over the {len(diag_t)} snapshots of the cycle-diagnosis continuation of the max "
           f"Courant 0.2 case (written every {diag_t[1] - diag_t[0] if len(diag_t) > 1 else '?'} "
           f"iterations), divided by the per-cell mean: the fluctuation is smallest around the "
           f"stagnation point and grows along the body in ray-like bands from the captured shock "
           f"toward the supersonic outflow (NR-25). (b) The same case's difference between its two "
           f"last SAVED fields, a two-phase sample of the oscillation. (c) The max Courant 0.1 "
           f"restart of record, difference between ITS two last saved fields, on the same colour "
           f"scale; the intervals differ ({src_t[-1] - src_t[-2] if len(src_t) > 1 else '?'} vs "
           f"{rec_t[-1] - rec_t[-2] if len(rec_t) > 1 else '?'} iterations), so read the level, "
           f"not "
           f"a ratio. {compare}'Shock layer' = cells with ρ/ρ∞ > 1.5 at the later saved iteration. "
           f"(d) p/p∞ of record. Colour: cividis, log10 clipped to [{vmin:g}, {vmax:g}]; magma "
           f"for p/p∞.",
           run_id=m2, cases=cases, mach=f"{mach:g}", mesh_level="fine (x4)",
           time_step=f"cyclediag {diag_t[0] if diag_t else '?'}–{diag_t[-1] if diag_t else '?'}; "
                     f"Co0.2 {src_t[-2] if len(src_t) > 1 else '?'},{src_t[-1] if src_t else '?'}; "
                     f"Co0.1 {rec_t[-2] if len(rec_t) > 1 else '?'},{rec_t[-1] if rec_t else '?'}",
           field="pressure fluctuation (rms, two-time difference), p/p∞")


# ---------------------------------------------------------------------------------------
# M2 demonstration capsule
# ---------------------------------------------------------------------------------------

def fig_demo_capsule(g: Gallery, m2: str) -> None:
    cfg = _m2_cfg(m2)
    demo = pd.read_csv(RES / "M2" / m2 / "pipeline_demo.csv")
    ok = demo[demo["status"] == "OK"]
    if ok.empty:
        g.cannot("demo capsule: no OK case in pipeline_demo.csv")
        return
    row = ok.iloc[-1]
    case = row["case"]
    o = val.demo_outline(cfg)
    try:
        view, met = _m2_case(m2, case, (o.x_m, o.r_m))
    except (FileNotFoundError, ValueError) as e:
        g.cannot(f"demo capsule {case}: {e}")
        return
    mach = float(row["mach"])
    x_up = float(view.meta["mesh"]["upstream_axis_x_m"])
    sd = float(met["standoff_m"])
    clear = -x_up - sd
    w = 4.2
    h = 0.85 * w * view.mesh.r_max / np.ptp(view.mesh.x_range) + 1.0
    fig, axes = plt.subplots(1, 3, figsize=(3 * w + 1.6, h))
    lims = {"mach": (0.0, mach), "p": (1.0, float(np.nanmax(view.fields["p"]))),
            "T": (1.0, float(np.nanmax(view.fields["T"])))}
    for ax, f in zip(axes, ("mach", "p", "T"), strict=False):
        field_panel(fig, ax, view, f, *lims[f], LABEL[f].split("  ")[0])
    ax = axes[0]
    rt = view.mesh.r_max
    annotate_standoff(ax, sd, rt, f"Δ = {sd:.4f} m", y=0.05 * rt)
    ax.annotate("", xy=(x_up, 0.16 * rt), xytext=(-sd, 0.16 * rt),
                arrowprops=dict(arrowstyle="<->", color=DEEP, lw=0.9, shrinkA=0, shrinkB=0),
                zorder=7)
    ax.text(0.5 * (x_up - sd), 0.18 * rt, f"shock → inflow boundary: {clear:.3f} m\n"
            f"clearance fraction 1 − Δ/|x_inflow| = {met['upstream_clearance_fraction']:.3f}",
            ha="center", va="bottom", fontsize=6.3, color=DEEP, zorder=8,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    ax.axvline(x_up, color=DEEP, lw=0.8, ls=":", zorder=6)
    ax.legend(handles=[sonic_handle()], fontsize=6.5, loc="upper left", frameon=True,
              facecolor="white", edgecolor="none")
    failed = demo[demo["status"] != "OK"]
    fig.suptitle(f"pipeline demonstration body ({view.meta['body']['name']}), "
                 f"$M_\\infty$ = {mach:g}, medium mesh — {case}, iteration {view.time:,}",
                 fontsize=10)
    fig.tight_layout()
    fl = "; ".join(f"{r['case']} (sizing radius {r['sizing_radius_m']:g} m): {r['status']}, "
                   f"no field "
                   f"written" for _, r in failed.iterrows())
    g.save(fig, "M2_demo_capsule_M6_fields",
           f"AETHER M2 · run {m2} · case {case} · generic blunted 60° cone (nose R 0.6 m, "
           f"D 1.2 m; NOT a flown vehicle, NOT a validated result) · M∞ = {mach:g} · medium mesh "
           f"(refinement factor 2, {view.mesh.n_cells:,} cells, sizing radius "
           f"{row['sizing_radius_m']:g} m) · "
           f"saved iteration {view.time:,}. {GAS}. White: sonic line. Red: shock stand-off Δ from "
           f"case_result.json; blue: distance from the captured shock to the fixed-value inflow "
           f"boundary on the axis (x_inflow = {x_up:.3f} m), the clearance NR-26 is about — the "
           f"first attempt in the sphere-sized domain crashed and wrote no field: {fl}. "
           f"C_D,fore = {met['cd_fore']:.4f}. Colour: viridis / magma / cividis.",
           run_id=m2, cases=case, mach=f"{mach:g}", mesh_level="medium (x2)",
           time_step=f"{view.time}", field="Mach, p/p∞, T/T∞")


# ---------------------------------------------------------------------------------------
# M3 design points
# ---------------------------------------------------------------------------------------

# (row key, bold row header, ratios line, {Mach: point_id}) - the six shapes of the grid, chosen
# from the design's named anchors: baseline, the M4-front shape, the slender and the wide-shoulder
# box corners, and the two shapes that stayed REJECTED under NR-27.
GRID_ROWS = [
    ("baseline", "baseline", "$R_n/D$ 0.50 · 25° · $R_c/D$ 0.10",
     {3: "dp016", 6: "sc1p2", 20: "dp017", 27: "dp070"}),
    ("m4_front_hi", "M4-front shape\n(m4_front_hi)", "$R_n/D$ 1.20 · 70° · $R_c/D$ 0.10",
     {3: "dp056", 20: "dp057", 27: "dp073"}),
    ("vertex0", "slender sphere-cone\n(vertex0)", "$R_n/D$ 0.25 · 20° · $R_c/D$ 0.02",
     {3: "dp000", 20: "dp001", 27: "dp062"}),
    ("vertex3", "wide-shoulder blunt cone\n(vertex3)", "$R_n/D$ 0.25 · 70° · $R_c/D$ 0.10",
     {3: "dp006", 20: "dp007", 27: "dp065"}),
    ("boundary0", "REJECTED under NR-27\n(boundary0)", "$R_n/D$ 0.80 · 52.5° · $R_c/D$ 0.02",
     {3: "dp010", 20: "dp011", 27: "dp067"}),
    ("m4_front_lo_b_crit", "REJECTED under NR-27\n(m4_front_lo_b_crit)",
     "$R_n/D$ 1.15 · 68.1° · $R_c/D$ 0.10", {3: "dp060", 20: "dp061", 27: "dp075"}),
]
# Mach 12 is deliberately absent: the design sampled it only at fill-point shapes, so every
# cell of a Mach-12 column would be blank (the caption says so).
GRID_MACHS = [3, 6, 20, 27]


def _design_table(m3: str) -> pd.DataFrame:
    return pd.read_csv(RES / "M3" / m3 / "design_points_coarse.csv").set_index("point_id")


def _dp_outline(row: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    cap = forebody_capsule(float(row["bluntness_ratio"]), float(row["cone_half_angle_deg"]),
                           float(row["shoulder_ratio"]), float(row["diameter_m"]))
    o = capsule_outline(cap, str(row.name))
    return o.x_m, o.r_m


def _dp_view(m3: str, table: pd.DataFrame, point_id: str) -> tuple[CaseView | None, dict, str]:
    """(view, metrics, verdict). view is None when no field can be shown."""
    row = table.loc[point_id]
    case = row["case"]
    verdict = str(row["verdict"])
    met = result_json(RES / "M3" / m3 / "cases" / case / "case_result.json").get("metrics", {})
    cdir = GEN / m3 / case
    if not cdir.exists() or not saved_times(cdir):
        return None, met, verdict
    return load_case(cdir, _dp_outline(row)), met, verdict


def fig_design_grid(g: Gallery, m3: str) -> None:
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    from matplotlib.gridspec import GridSpec

    table = _design_table(m3)
    nrow, ncol = len(GRID_ROWS), len(GRID_MACHS)
    slot_w, slot_h, label_w, cbar_h = 3.3, 4.4, 1.9, 0.28
    fig = plt.figure(figsize=(label_w + slot_w * ncol + 0.4, slot_h * nrow + cbar_h + 1.3))
    gs = GridSpec(nrow + 1, ncol + 1, figure=fig,
                  width_ratios=[label_w] + [slot_w] * ncol,
                  height_ratios=[slot_h] * nrow + [cbar_h],
                  left=0.01, right=0.99, top=0.95, bottom=0.05, wspace=0.08, hspace=0.32)
    shown, blank = [], []

    def blank_cell(ax, text, color=MUTED):
        ax.set_axis_off()
        ax.text(0.5, 0.5, text, transform=ax.transAxes, ha="center", va="center", fontsize=8,
                color=color, wrap=True)

    for i, (key, header, ratios, cells) in enumerate(GRID_ROWS):
        lab = fig.add_subplot(gs[i, 0])
        lab.set_axis_off()
        lab.text(0.0, 0.56, header, transform=lab.transAxes, ha="left", va="bottom",
                 fontsize=10, fontweight="bold", color=HOT if "REJECTED" in header else INK)
        lab.text(0.0, 0.5, ratios, transform=lab.transAxes, ha="left", va="top", fontsize=9)
        for j, mach in enumerate(GRID_MACHS):
            ax = fig.add_subplot(gs[i, j + 1])
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
            head = f"$M_\\infty$ = {mach}\n" if i == 0 else ""
            pid = cells.get(mach)
            if pid is None:
                blank_cell(ax, f"no usable case\n(not in the design at Mach {mach})")
                ax.set_title(head, fontsize=11)
                blank.append(f"{key} @ M{mach}: not in the design")
                continue
            row = table.loc[pid]
            case, verdict = row["case"], str(row["verdict"])
            if verdict not in ("USABLE", "REJECTED"):
                reason = str(row["reasons"])
                blank_cell(ax, f"no usable case\n{pid} ({case}): {verdict}\n{reason}\n"
                           f"no field survives the van Leer hand-over (NR-28)", color=HOT)
                ax.set_title(head, fontsize=11)
                blank.append(f"{pid} ({case}) @ M{mach}: {verdict} - {reason}")
                continue
            view, met, verdict = _dp_view(m3, table, pid)
            if view is None:
                blank_cell(ax, f"no usable case\n{pid} ({case}): no saved field on disk", color=HOT)
                ax.set_title(head, fontsize=11)
                blank.append(f"{pid} ({case}) @ M{mach}: no saved field on disk")
                continue
            draw_cells(ax, view.mesh, view.fields["mach"], "mach", 0.0, float(mach))
            draw_body(ax, view.xb, view.rb)
            draw_contour(ax, view.mesh, view.fields["mach"], 1.0, view.xb, view.rb, lw=0.9)
            x0, x1 = view.mesh.x_range
            ax.set_xlim(x0, x1)
            ax.set_ylim(0, view.mesh.r_max)
            ax.set_aspect("equal")
            cd = met.get("cd_fore", float("nan"))
            if verdict == "USABLE":
                ax.set_title(f"{head}{case} · it {view.time:,}\n$C_{{D,fore}}$ = {cd:.3f}",
                             fontsize=8.5)
            else:
                nr = "27" if mach < 27 else "28"
                ax.set_title(f"{head}{case} · it {view.time:,}\nREJECTED (NR-{nr}: force "
                             f"criterion)\n$C_{{D,fore}}$ = {cd:.3f}, not on the surface",
                             fontsize=8.5, color=HOT)
                for sp in ax.spines.values():
                    sp.set_visible(True)
                    sp.set_edgecolor(HOT)
                    sp.set_linewidth(1.8)
            shown.append(f"{pid}={case}@{view.time}")
    for j, mach in enumerate(GRID_MACHS):
        cax = fig.add_subplot(gs[nrow, j + 1])
        sm = ScalarMappable(norm=Normalize(0.0, float(mach)), cmap="viridis")
        cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
        cb.set_label(f"Mach number  [-]  (viridis, 0 to {mach})")
        cb.outline.set_edgecolor(MUTED)
    fig.suptitle("M3 design points: Mach-number field by forebody shape (rows) and Mach number "
                 "(columns), coarse mesh, forebody domain; every cell's own domain, axis equal",
                 fontsize=12)
    g.save(fig, "M3_design_point_grid_mach",
           f"AETHER M3 · run {m3} · coarse mesh (refinement factor 1, 3,072 cells) · forebody "
           f"domain (nose to the maximum-radius station, closed by a supersonic outflow) · D = "
           f"1.2 m "
           f"· each panel at its case's final saved iteration (in its title). {GAS}. Colour: "
           f"viridis, "
           f"one scale per column (0 to M∞). Thin white line: sonic line. C_D,fore from each "
           f"case_result.json. Rows 5-6 are the two shapes that stayed REJECTED under NR-27 at "
           f"Mach "
           f"20 (force criterion never met in two consecutive blocks at Co 0.2 / 0.1 / 0.05) and, "
           f"as "
           f"NR-28 records, at Mach 27 too; their fields are the final saved solution of the last "
           f"Courant restart, shown for what they are - not on the drag surface. There is NO "
           f"Mach-12 "
           f"column: the design sampled Mach 12 (and Mach 6, except the baseline scale-check case "
           f"sc1p2) only at fill-point shapes, so no usable case exists for any of these six "
           f"shapes "
           f"there. dp062 (vertex0 at Mach 27) crashed in all three domain attempts without "
           f"writing "
           f"a second-order field (NR-28; its first-order start-up field is in the Mach-27 "
           f"figure). "
           f"Outlines are drawn to the maximum-radius station only, where the domain ends.",
           run_id=m3, cases="; ".join(shown), mach="3, 6, 20, 27", mesh_level="coarse (x1)",
           time_step="final saved iteration per case (in panel titles)", field="Mach")
    for b in blank:
        g.cannot(f"design grid cell: {b}")
    g.cannot("design grid column Mach 12: no usable case for any of the six shapes (the design "
             "sampled Mach 12 only at fill-point shapes), so the column is omitted")


# ---------------------------------------------------------------------------------------
# M3 Mach-27 start-up failure
# ---------------------------------------------------------------------------------------

def fig_mach27_failure(g: Gallery, m3: str, exp_run: str) -> None:
    table = _design_table(m3)
    pid = "dp062"
    if pid not in table.index:
        g.cannot(f"Mach-27 failure: {pid} not in {m3}")
        return
    row = table.loc[pid]
    xr = _dp_outline(row)
    cands = [GEN / m3 / row["case"], GEN / exp_run / "dp062_A_fo6000"]
    views = []
    for cdir in cands:
        if not cdir.exists() or not saved_times(cdir):
            g.cannot(f"Mach-27 failure: {cdir} has no saved field")
            continue
        v = load_case(cdir, xr)
        died = last_logged_iteration(cdir / "log.rhoCentralFoam")
        handover = last_logged_iteration(cdir / "log.rhoCentralFoam_startup")
        views.append((v, died, handover))
    if not views:
        return
    w = 4.0
    h = w * views[0][0].mesh.r_max / np.ptp(views[0][0].mesh.x_range) + 1.4
    fig, axes = plt.subplots(len(views), 3, figsize=(3 * w + 2.2, len(views) * h), squeeze=False)
    for (v, died, handover), (axT, axM, axK) in zip(views, axes, strict=False):
        tmin = float(np.nanmin(v.fields["T_K"]))
        field_panel(fig, axT, v, "T", 1.0, float(np.nanmax(v.fields["T"])),
                    f"{v.name}: $T/T_\\infty$ at it {v.time:,}\nlast saved field = end of the "
                    f"first-order start\nmin T = {tmin:.0f} K = $T_\\infty$", sonic=False)
        field_panel(fig, axM, v, "mach", 0.0, v.flow.mach,
                    f"Mach at it {v.time:,}\nvan Leer hand-over at it {handover:,}\nsolver died at "
                    f"it {died:,}, no field written")
        axM.legend(handles=[sonic_handle()], fontsize=6.5, loc="upper left", frameon=True,
                   facecolor="white", edgecolor="none")
        kf = v.fields["ke_fraction"]
        pc = draw_cells(axK, v.mesh, kf, "T", 0.0, 1.0, cmap="cividis")
        draw_body(axK, v.xb, v.rb)
        frame(axK, v.mesh, v.xb, v.rb)
        colorbar(fig, axK, pc,
                 "kinetic / total energy  $\\frac{1}{2}u^2 / (\\frac{1}{2}u^2 + c_v T)$  [-]",
                 shrink=0.85, pad=0.02)
        axK.set_title(f"kinetic / total energy at it {v.time:,}\nfreestream value {kf.max():.4f}\n"
                      f"(internal energy = the small remainder)", fontsize=8.5)
    fig.suptitle("Mach 27, slender sphere-cone dp062 ($R_n/D$ 0.25, 20°, $R_c/D$ 0.02): the "
                 "last fields that survive the start-up failure (NR-28)", fontsize=10)
    fig.tight_layout()
    a2 = views[0]
    others = []
    for nm in ("dp062_coarse_a0", "dp062_coarse_a1", "dp063_coarse_a2"):
        d = GEN / m3 / nm
        if d.exists():
            others.append(f"{nm}: died at it {last_logged_iteration(d / 'log.rhoCentralFoam')}")
    for nm in ("dp062_B_fo1500_co01", "dp062_C_fo6000_co01"):
        d = GEN / exp_run / nm
        if d.exists():
            others.append(f"{nm}: died at it {last_logged_iteration(d / 'log.rhoCentralFoam')}")
    g.save(fig, "M3_mach27_dp062_startup_failure",
           f"AETHER M3 · runs {m3} (top row: {a2[0].name}, the design-point attempt of record) and "
           f"{exp_run} (bottom row: {views[-1][0].name}, the NR-28 isolation run with a "
           f"6000-iteration "
           f"first-order start) · point dp062 · M∞ = 27 · coarse mesh ({a2[0].mesh.n_cells:,} "
           f"cells). "
           f"{GAS}. WHAT SURVIVES: only the field written at the end of the first-order (upwind) "
           f"start-up - iteration {a2[0].time:,} resp. {views[-1][0].time:,}. The van Leer "
           f"hand-over "
           f"then diverged with a floating-point exception in sqrt (a negative temperature) at "
           f"iteration {a2[1]} resp. {views[-1][1]}, and a crashed run writes NO field: the cell "
           f"where the temperature went negative is not recorded anywhere on disk and cannot be "
           f"shown. The saved first-order fields contain no cell below T∞ (min T = "
           f"{np.nanmin(a2[0].fields['T_K']):.0f} K), so they hold no precursor either. The third "
           f"column shows the mechanism NR-28 names: the kinetic energy is >99% of the total "
           f"energy "
           f"in the freestream and stays dominant through the thin attached shock layer along the "
           f"20° cone, so a small error in total energy is a large relative error in c_v T. Other "
           f"attempts, all without a post-hand-over field: {'; '.join(others)}. Colour: cividis "
           f"(T/T∞, energy fraction), viridis (Mach).",
           run_id=f"{m3}; {exp_run}", cases=", ".join(v[0].name for v in views), mach="27",
           mesh_level="coarse (x1)", time_step=", ".join(str(v[0].time) for v in views),
           field="T/T∞, Mach, kinetic-energy fraction (first-order start-up solution)")


# ---------------------------------------------------------------------------------------
# M6 promotions
# ---------------------------------------------------------------------------------------

M6_PICK = ["af2a27042848", "af5e13e211ab", "af01fbe28a96", "af1376216f0b"]


def fig_m6_promotions(g: Gallery, m6: str) -> None:
    root = RES / "M6" / m6
    calls = pd.read_csv(root / "cfd_calls.csv")
    calls = calls[calls["arm"] == "adaptive"]
    attempts = [json.loads(line)
                for line in (root / "cfd" / "attempts.jsonl").read_text().splitlines()
                if line.strip()]
    counters = json.loads((root / "counters.json").read_text())
    views = []
    for pid in M6_PICK:
        c = calls[calls["point_id"] == pid]
        if c.empty:
            g.cannot(f"M6 promotion {pid}: not an adaptive-arm CFD call in {m6}")
            continue
        c = c.iloc[0]
        att = [a for a in attempts if a["point_id"] == pid]
        if not att:
            g.cannot(f"M6 promotion {pid}: no attempt in cfd/attempts.jsonl")
            continue
        case = att[-1]["case"]
        cdir = GEN / m6 / case
        if not cdir.exists() or not saved_times(cdir):
            g.cannot(f"M6 promotion {pid}: {cdir} has no saved field")
            continue
        meta_body = yaml.safe_load((cdir / "aether_case.yaml").read_text())["body"]
        d = 2.0 * float(meta_body["max_radius_m"])
        cap = forebody_capsule(float(c["bluntness_ratio"]), float(c["cone_half_angle_deg"]),
                               float(c["shoulder_ratio"]), d)
        o = capsule_outline(cap, pid)
        v = load_case(cdir, (o.x_m, o.r_m))
        met = result_json(root / "cfd" / "cases" / case / "case_result.json").get("metrics", {})
        n_calls = int((calls["seed"] == c["seed"]).sum())
        hist = counters.get(f"adaptive|{int(c['seed'])}", {}).get("surface_history", [])
        ntrain = " → ".join(str(hh["n_train"]) for hh in hist)
        views.append((v, c, met, n_calls, ntrain))
    if not views:
        return
    w = 4.3
    r_max = max(v.mesh.r_max / np.ptp(v.mesh.x_range) for v, *_ in views)
    h = min(w * r_max + 1.5, 6.4)
    ncol = 2 if len(views) > 1 else 1
    nrow = int(np.ceil(len(views) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(ncol * w + 1.8, nrow * h), squeeze=False)
    for ax in axes.ravel()[len(views):]:
        ax.set_visible(False)
    for ax, (v, c, met, n_calls, _ntrain) in zip(axes.ravel(), views, strict=False):
        mach = float(c["mach"])
        pc = draw_cells(ax, v.mesh, v.fields["mach"], "mach", 0.0, mach)
        draw_body(ax, v.xb, v.rb)
        draw_contour(ax, v.mesh, v.fields["mach"], 1.0, v.xb, v.rb)
        frame(ax, v.mesh, v.xb, v.rb)
        colorbar(fig, ax, pc, LABEL["mach"] + f"  (0 to {mach:g})", shrink=0.85, pad=0.02)
        usable = str(c["verdict"]) == "USABLE"
        ax.set_title(f"{v.name}, it {v.time:,} - adaptive arm, seed {int(c['seed'])}, call "
                     f"{int(c['call_index'])} of {n_calls}\n$R_n/D$ {c['bluntness_ratio']:.3f}, "
                     f"{c['cone_half_angle_deg']:.1f}°, $R_c/D$ {c['shoulder_ratio']:.2f}",
                     fontsize=7.5)
        if usable:
            tag(ax, f"USABLE · $C_{{D,fore}}$ = {met.get('cd_fore', float('nan')):.4f}",
                loc="lower right")
        else:
            tag(ax, f"{c['verdict']} · $C_{{D,fore}}$ = {met.get('cd_fore', float('nan')):.4f}\n"
                f"(not accepted: force criterion)", loc="lower right", color=HOT)
            for sp in ax.spines.values():
                sp.set_visible(True)
                sp.set_edgecolor(HOT)
                sp.set_linewidth(1.6)
    axes[0, 0].legend(handles=[sonic_handle()], fontsize=6.5, loc="upper left", frameon=True,
                      facecolor="white", edgecolor="none")
    fig.suptitle("M6: shapes the adaptive arm bought CFD for (promotions), Mach-number field, "
                 "coarse mesh, $M_\\infty$ = 20", fontsize=10)
    fig.tight_layout()
    ctx = "; ".join(f"{v.name}: seed {int(c['seed'])}, {c['verdict']}, surface training set "
                    f"{nt} points over the run" for v, c, met, n, nt in views)
    g.save(fig, "M6_adaptive_promotions_mach",
           f"AETHER M6 · run {m6} · adaptive arm · coarse mesh (3,072 cells) · D = 1.2 m · "
           f"forebody "
           f"domain · each panel at its case's final saved iteration (title). {GAS}. A promotion "
           f"is "
           f"a candidate the adaptive policy sent to CFD instead of trusting the Fidelity-1 "
           f"surface "
           f"(promotion_log.json reason for every adaptive promotion: 'promising, and the cheap "
           f"model "
           f"is untrusted here'; none was outside the arm's hull). Every usable case is appended "
           f"to "
           f"that arm-and-seed's own surface, which is re-fitted (counters.json surface_history): "
           f"{ctx}. The REJECTED case never met the force criterion in two consecutive blocks at "
           f"Co 0.2 / 0.1 / 0.05 (same rule as NR-27); its field is the last Courant restart's "
           f"final "
           f"save, shown but not used. White: sonic line. Colour: viridis.",
           run_id=m6, cases=", ".join(v.name for v, *_ in views), mach="20",
           mesh_level="coarse (x1)", time_step=", ".join(str(v.time) for v, *_ in views),
           field="Mach")


# ---------------------------------------------------------------------------------------
# Surface pressure coefficient
# ---------------------------------------------------------------------------------------

def fig_cp_sphere(g: Gallery, m2: str) -> None:
    cfg = _m2_cfg(m2)
    radius = float(cfg["benchmark"]["radius_m"])
    gamma = float(cfg["gas"]["gamma"])
    machs = [float(m) for m in cfg["benchmark"]["mach_numbers"]]
    levels = [("coarse", "{c}_coarse"), ("medium", "{c}_medium"), ("fine", "{c}_fine_Co0p1")]
    fig, axes = plt.subplots(1, len(machs), figsize=(4.6 * len(machs), 3.9), squeeze=False)
    used, times = [], []
    for ax, mach in zip(axes[0], machs, strict=False):
        for level, pat in levels:
            case = pat.format(c=f"sphere_M{mach:g}")
            f = RES / "M2" / m2 / case / "body_pressure.csv"
            if not f.exists():
                g.cannot(f"sphere Cp {case}: {f} missing")
                continue
            body = pd.read_csv(f)
            met = result_json(RES / "M2" / m2 / case / "case_result.json").get("metrics", {})
            theta = np.degrees(np.arccos(np.clip(1.0 - body["x_m"] / radius, -1, 1)))
            ls, col = LEVEL_STYLE[level]
            ax.plot(theta, body["cp"], ls, color=col, lw=1.2,
                    label=f"CFD {level} ({case}, it {met.get('n_iterations', '?')})")
            used.append(case)
            times.append(str(met.get("n_iterations", "?")))
        th = np.linspace(0.0, 90.0, 181)
        cp0 = stagnation_pressure_coefficient(mach, gamma)
        ax.plot(th, cp0 * np.cos(np.radians(th)) ** 2, color=ACCENT, lw=1.1, ls="--",
                label="modified Newtonian, $C_{p,max}\\cos^2\\theta$ (analytical estimate)")
        ax.plot([0.0], [cp0], "D", color=HOT, ms=5, label="Rayleigh-pitot $C_{p,max}$ (exact)")
        ax.axhline(0.0, color=MUTED, lw=0.6)
        ax.set_xlim(0.0, 90.0)
        ax.set_xlabel("angle from the stagnation point  $\\theta$  [deg]")
        ax.set_ylabel("surface pressure coefficient  $C_p$  [-]")
        ax.set_title(f"sphere, $M_\\infty$ = {mach:g}")
        ax.legend(fontsize=6.3, loc="upper right")
    fig.tight_layout()
    g.save(fig, "M2_sphere_cp_meshes",
           f"AETHER M2 · run {m2} · cases {', '.join(used)} · sphere R = {radius:g} m · three "
           f"meshes "
           f"(coarse x1, medium x2, fine x4 = the max Courant 0.1 restart of record) · surface "
           f"pressure sampled at each case's final iteration ({', '.join(times)}). {GAS}. C_p = "
           f"(p − p∞)/q∞. Dashed: modified Newtonian theory C_p = C_p,max cos²θ with C_p,max from "
           f"the "
           f"exact Rayleigh-pitot relation — an analytical estimate for comparison, not a "
           f"validation "
           f"reference. Line style AND colour distinguish the meshes.",
           run_id=m2, cases=", ".join(used), mach=", ".join(f"{m:g}" for m in machs),
           mesh_level="coarse, medium, fine", time_step=", ".join(times), field="surface C_p")


def fig_cp_design_points(g: Gallery, m3: str) -> None:
    table = _design_table(m3)
    machs = [6, 20]
    fig, axes = plt.subplots(len(machs), 2, figsize=(10.4, 3.9 * len(machs)), squeeze=False,
                             gridspec_kw={"width_ratios": [1.0, 1.5]})
    used, times = [], []
    for (axo, axc), mach in zip(axes, machs, strict=False):
        n_series = 0
        for k, (_key, header, _ratios, cells) in enumerate(GRID_ROWS):
            pid = cells.get(mach)
            if pid is None:
                continue
            row = table.loc[pid]
            case = row["case"]
            f = RES / "M3" / m3 / "cases" / case / "body_pressure.csv"
            if not f.exists():
                g.cannot(f"design-point Cp {case}: {f} missing")
                continue
            body = pd.read_csv(f)
            met = result_json(RES / "M3" / m3 / "cases" / case / "case_result.json"
                              ).get("metrics", {})
            d = float(row["diameter_m"])
            ds = np.hypot(np.diff(body["x_m"]), np.diff(body["r_m"]))
            s = np.concatenate(([0.0], np.cumsum(ds)))
            verdict = str(row["verdict"])
            col, ls = CAT_COLOURS[k], CAT_STYLES[k]
            name = header.replace("\n", " ").replace("REJECTED under NR-27 ", "")
            lab = f"{name} — {case}" + ("" if verdict == "USABLE" else f" [{verdict}]")
            axc.plot(s / d, body["cp"], ls, color=col, lw=1.2, label=lab)
            xb, rb = _dp_outline(row)
            i = int(np.argmax(rb))
            axo.plot(xb[:i + 1] / d, rb[:i + 1] / d, ls, color=col, lw=1.2, label=name)
            used.append(case)
            times.append(str(met.get("n_iterations", "?")))
            n_series += 1
        axo.set_aspect("equal")
        axo.set_xlabel("$x/D$  [-]")
        axo.set_ylabel("$r/D$  [-]")
        axo.set_title(f"forebody outlines, $M_\\infty$ = {mach}", fontsize=9)
        axc.axhline(0.0, color=MUTED, lw=0.6)
        axc.set_xlabel("arc length from the nose along the meridian  $s/D$  [-]")
        axc.set_ylabel("surface pressure coefficient  $C_p$  [-]")
        axc.set_title(f"$C_p$ along the forebody, $M_\\infty$ = {mach}, coarse mesh", fontsize=9)
        if n_series:
            axc.legend(fontsize=6.3, loc="upper right")
        if n_series == 1:
            axc.text(0.02, 0.06, f"only one of the six grid shapes was run at Mach {mach} "
                     f"(the design sampled Mach {mach} elsewhere only at fill-point shapes)",
                     transform=axc.transAxes, fontsize=6.5, color=MUTED)
    fig.tight_layout()
    g.save(fig, "M3_design_point_cp",
           f"AETHER M3 · run {m3} · cases {', '.join(used)} · coarse mesh (3,072 cells) · D = 1.2 "
           f"m · "
           f"surface pressure sampled at each case's final iteration ({', '.join(times)}). {GAS}. "
           f"C_p = (p − p∞)/q∞ against arc length from the nose over the diameter; the left panels "
           f"show the same outlines in the same colour and line style. Series tagged [REJECTED] "
           f"are "
           f"the two NR-27 shapes: their C_p is the last Courant restart's final save and is not "
           f"on "
           f"the drag surface. At Mach 6 only the baseline shape (scale-check case sc1p2) exists.",
           run_id=m3, cases=", ".join(used), mach="6, 20", mesh_level="coarse (x1)",
           time_step=", ".join(times), field="surface C_p")
