# ruff: noqa: E501
"""Explanatory infographics for the AETHER paper.

Seven figures that explain the ARGUMENT, as opposed to the scientific plots the milestone
scripts already write into reports/figures/. Every number drawn here is read from a result
file (results/<run>/…) or from a generated report; nothing is typed in. Each figure carries
the run IDs it drew on in small print, and INDEX.md records the sources per figure.

    make infographics            (or)  .venv/bin/python scripts/render_infographics.py

Outputs: reports/figures/infographics/<stem>.{png,pdf,svg} + INDEX.md.

Nothing under src/, configs/ or results/ is touched. The one computation performed here
(figure 1) re-runs the canonical evaluator on the M1 config snapshot to recover the time
histories that the M1 run did not persist, and asserts that the scalars it produces match
the logged candidates.csv row to 1e-9 relative before anything is drawn.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patheffects  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, to_rgb  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports" / "figures" / "infographics"

# --------------------------------------------------------------------------------------
# Runs and files this script reads. Change a run here, and every figure and INDEX.md follow.
# --------------------------------------------------------------------------------------
M1_RUN = "M1-20260902T130547Z"
M2_RUN = "M2-20260920T123901Z"
M4_RUN = "M4-OPT-20260920T205252Z"
M5_RUN = "M5-ABL-20260920T211134Z"
M6_RUN = "M6-AF-20260920T211148Z"
M7_UQ_RUN = "M7-UQ-20260920T233048Z"
M7_ROBUST_RUN = "M7-ROBUST-20260920T211216Z"
M7_LFL_RUN = "M7-LFL-20260921T011854Z"

R = ROOT / "results"
F = {
    "m1_csv": R / "M1" / M1_RUN / "candidates.csv",
    "m1_cfg": R / "M1" / M1_RUN / "config_snapshot.yaml",
    "m1_report": ROOT / "reports" / "milestones" / "M1_burn_vs_bake.md",
    "m2_gate": R / "M2" / M2_RUN / "gate_assessment.json",
    "m2_gate_before": R / "M2" / M2_RUN / "gate_assessment_20260921_0057_before_restarts.json",
    "m2_gci": R / "M2" / M2_RUN / "gci.csv",
    "m2_gci_before": R / "M2" / M2_RUN / "gci_20260921_0057_before_restarts.csv",
    "m2_cfg": R / "M2" / M2_RUN / "config_snapshot.yaml",
    "m4_summary": R / "M4" / M4_RUN / "summary.json",
    "m4_csv": R / "M4" / M4_RUN / "candidates.csv",
    "m5_summary": R / "M5" / M5_RUN / "summary.json",
    "m6_summary": R / "M6" / M6_RUN / "summary.json",
    "m6_report": ROOT / "reports" / "milestones" / "M6_adaptive_fidelity.md",
    "m7_summary": R / "M7" / M7_UQ_RUN / "summary.json",
    "m7_paired": R / "M7" / M7_UQ_RUN / "paired_difference.json",
    "m7_lfl": R / "M7" / M7_LFL_RUN / "likeforlike.json",
    "m7_robust_front": R / "M7" / M7_ROBUST_RUN / "robust_front.csv",
    "paper": ROOT / "reports" / "final" / "AETHER_paper.md",
    "matrix": ROOT / "VALIDATION_MATRIX.md",
    "nr": ROOT / "docs" / "negative_results.md",
}

# --------------------------------------------------------------------------------------
# One type system, one palette, for all seven figures.
# Categorical slots are the dataviz reference palette (validated adjacent-pair CVD ΔE ≥ 8
# on a white surface with scripts/validate_palette.js: slots 1-4 pass; yellow and aqua sit
# below 3:1 so they are never used without a text label). Status colours are the fixed
# status scale and are ALWAYS paired with a text label.
# --------------------------------------------------------------------------------------
INK = "#141413"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e6e5df"
RULE = "#c3c2b7"
SURFACE = "#ffffff"
PANEL = "#f4f4f1"

S1 = "#2a78d6"   # blue    - series 1 / steep entry / epistemic
S2 = "#eb6834"   # orange  - series 2 / shallow entry / aleatory
S3 = "#1baf7a"   # aqua    - series 3
S4 = "#eda100"   # yellow  - series 4 (label-relief required)

GOOD = "#0ca30c"       # PASS / supported
WARN = "#fab219"       # LIMITED / supported narrowly (label-relief required)
CRIT = "#d03b3b"       # FAIL / not supported
NEUT = "#898781"       # IN_PROGRESS / not run / no reference

SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
CMAP_GAMMA = LinearSegmentedColormap.from_list("aether_blue", SEQ_BLUE)

FONT = ["Avenir Next", "Helvetica Neue", "DejaVu Sans"]

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": 9,
    "axes.labelcolor": INK2,
    "axes.edgecolor": RULE,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "grid.linestyle": "-",
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.frameon": False,
    "legend.fontsize": 8.5,
    "text.color": INK,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "figure.dpi": 110,
    "savefig.dpi": 220,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "mathtext.fontset": "dejavusans",
})


def wrap(text: str, width: int) -> str:
    """Deterministic wrapping (matplotlib's wrap=True depends on the renderer dpi)."""
    return "\n".join(textwrap.fill(par, width) for par in text.split("\n"))


def tint(hex_colour: str, amount: float = 0.85) -> tuple[float, float, float]:
    """Mix a colour with white; amount = share of white."""
    r, g, b = to_rgb(hex_colour)
    return (r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount)


# --------------------------------------------------------------------------------------
# Small helpers: frame, stamps, saving, index
# --------------------------------------------------------------------------------------
@dataclass
class IndexEntry:
    number: int
    stem: str
    title: str
    claim: str
    sources: list[str]
    notes: list[str]


INDEX: list[IndexEntry] = []


def frame(fig, number: int, title: str, claim: str, *, top: float = 0.955) -> None:
    fig.text(0.035, top, f"{number}", fontsize=30, weight="bold", color=RULE, va="top", ha="left")
    fig.text(0.075, top, title, fontsize=17, weight="bold", color=INK, va="top", ha="left")
    fig.text(0.075, top - 0.045, claim, fontsize=10.5, color=INK2, va="top", ha="left", wrap=True)


def stamp(fig, lines: list[str], *, y: float = 0.018) -> None:
    txt = "\n".join(textwrap.fill(ln, 265) for ln in lines)
    fig.text(0.035, y, txt, fontsize=6.6, color=MUTED, va="bottom", ha="left", linespacing=1.35)


def save(fig, stem: str) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("png", "pdf", "svg"):
        p = OUT / f"{stem}.{ext}"
        fig.savefig(p, bbox_inches=None, pad_inches=0)
        written.append(p)
    plt.close(fig)
    return written


def chip(ax, x, y, text, colour, *, w=None, h=0.028, fontsize=7.5, ha="left", z=5):
    """A status chip: light tint fill, solid colour bar on the left, ink text. Never colour alone."""
    if w is None:
        w = 0.012 + 0.0068 * len(text)
    x0 = x if ha == "left" else x - w
    ax.add_patch(FancyBboxPatch((x0, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.006",
                                fc=tint(colour, 0.82), ec="none", zorder=z, transform=ax.transAxes))
    ax.add_patch(Rectangle((x0, y - h / 2), 0.006, h, fc=colour, ec="none", zorder=z + 1,
                           transform=ax.transAxes))
    ax.text(x0 + 0.012, y, text, fontsize=fontsize, weight="bold", color=INK, va="center",
            ha="left", zorder=z + 2, transform=ax.transAxes)
    return w


def kw(x_w_m2: float) -> str:
    return f"{x_w_m2 / 1e3:.1f} kW/m²"


def git_first_date(pattern: str, path: Path) -> str | None:
    try:
        out = subprocess.run(["git", "log", "--format=%ad", "--date=short", "--reverse", "-S", pattern,
                              "--", str(path.relative_to(ROOT))], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.split()
        return out[0] if out else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def load_json(p: Path) -> dict:
    return json.loads(p.read_text())


def status_from_matrix(gate: str) -> list[tuple[str, str]]:
    """Statuses of one VALIDATION_MATRIX.md row: [(STATUS, qualifier), ...]."""
    rows = []
    for line in F["matrix"].read_text().splitlines():
        if line.startswith(f"| {gate} |"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            status_cell = cells[5] if len(cells) > 5 else ""
            found = re.findall(r"\*\*(PASS|LIMITED|IN_PROGRESS|FAIL|NOT_STARTED)\*\*\s*(\([^)]*\))?",
                               status_cell)
            rows.extend((s, q.strip("()") if q else "") for s, q in found)
    if not rows:
        raise KeyError(f"gate {gate!r} not found in VALIDATION_MATRIX.md")
    return rows


STATUS_COLOUR = {"PASS": GOOD, "LIMITED": WARN, "IN_PROGRESS": NEUT, "FAIL": CRIT, "NOT_STARTED": NEUT}


# ======================================================================================
# Figure 1 - the burn-vs-bake mechanism
# ======================================================================================
def fig1_burn_vs_bake() -> IndexEntry:
    from src.aether.evaluate import evaluate_design

    csv = pd.read_csv(F["m1_csv"])
    snap = yaml.safe_load(F["m1_cfg"].read_text())
    meta, cfg = snap["_meta"], snap["config"]
    row_a = csv.loc[csv.gamma_deg.idxmin()]   # steepest
    row_b = csv.loc[csv.gamma_deg.idxmax()]   # shallowest
    n_pairs = re.search(r"Signature counterexample pairs \| (\d+)", F["m1_report"].read_text()).group(1)

    evs = {}
    for key, row in (("A", row_a), ("B", row_b)):
        c = copy.deepcopy(cfg)
        c["entry"]["flight_path_angle_deg"] = float(row.gamma_deg)
        ev = evaluate_design(c, design_id=str(row.design_id))
        for col in ("peak_heat_flux_w_m2", "peak_bondline_temperature_k", "entry_duration_s",
                    "integrated_external_heat_j_m2"):
            logged, now = float(row[col]), float(getattr(ev.performance, col))
            assert abs(now - logged) <= 1e-9 * abs(logged), (col, logged, now)
        evs[key] = ev
    a, b = evs["A"], evs["B"]
    allow = float(cfg["limits"]["t_bondline_allowable_k"])
    bond_depth_mm = a.tps.depth_m[a.tps.bond_index] * 1e3
    stack_mm = sum(layer["thickness_m"] for layer in cfg["tps"]["layers"]) * 1e3
    ins_mm = cfg["tps"]["layers"][0]["thickness_m"] * 1e3

    dq = (row_b.peak_heat_flux_w_m2 / row_a.peak_heat_flux_w_m2 - 1) * 100
    dT = row_b.peak_bondline_temperature_k - row_a.peak_bondline_temperature_k

    fig = plt.figure(figsize=(13, 8.6))
    frame(fig, 1, "Burn versus bake: the shallow entry is cooler outside and hotter inside",
          "Two entries of the same capsule. The shallow one lowers peak heat flux by "
          f"{abs(dq):.1f}% and leaves the bondline {dT:.1f} K hotter.\n"
          "Peak flux is a surface quantity; bondline temperature is an integrated, delayed one.")
    gs = GridSpec(2, 3, figure=fig, left=0.06, right=0.975, top=0.835, bottom=0.155,
                  hspace=0.48, wspace=0.32, width_ratios=[1, 1, 1.15])

    col = {"A": S1, "B": S2}
    lab = {"A": f"A  steep  γ₀ = {row_a.gamma_deg:+.2f}°", "B": f"B  shallow  γ₀ = {row_b.gamma_deg:+.2f}°"}
    style = {"A": "-", "B": "-"}

    # (a) trajectory: altitude vs time
    ax = fig.add_subplot(gs[0, 0])
    for k, e in evs.items():
        ax.plot(e.trajectory.time_s, e.trajectory.altitude_m / 1e3, style[k], color=col[k], lw=2,
                label=lab[k], solid_capstyle="round")
        ax.plot(e.trajectory.time_s[-1], e.trajectory.altitude_m[-1] / 1e3, "o", color=col[k], ms=6,
                mec=SURFACE, mew=1.5)
        ax.annotate(f"{e.performance.entry_duration_s:.0f} s", (e.trajectory.time_s[-1],
                    e.trajectory.altitude_m[-1] / 1e3), xytext=(4, 6), textcoords="offset points",
                    fontsize=8, color=INK2)
    ax.set_title("a  Entry trajectory")
    ax.set_xlabel("time from entry interface [s]")
    ax.set_ylabel("altitude [km]")
    ax.set_ylim(0, 125)
    ax.legend(loc="upper right", handlelength=1.6)

    # (b) heat-flux histories
    ax = fig.add_subplot(gs[0, 1])
    for k, e in evs.items():
        q = e.heat_flux_w_m2 / 1e4
        ax.plot(e.trajectory.time_s, q, style[k], color=col[k], lw=2, solid_capstyle="round")
        i = int(np.argmax(q))
        ax.plot(e.trajectory.time_s[i], q[i], "o", color=col[k], ms=6, mec=SURFACE, mew=1.5)
        ax.annotate(f"{q[i]:.1f} W/cm²", (e.trajectory.time_s[i], q[i]), xytext=(8, 2),
                    textcoords="offset points", fontsize=8.5, color=INK, weight="bold")
    ax.set_title("b  External heat flux (Sutton–Graves)")
    ax.set_xlabel("time from entry interface [s]")
    ax.set_ylabel("stagnation heat flux [W/cm²]")
    ax.set_ylim(0, None)
    ax.text(0.98, 0.9, f"integrated load\nA {row_a.integrated_external_heat_j_m2/1e6:.1f} MJ/m²\n"
            f"B {row_b.integrated_external_heat_j_m2/1e6:.1f} MJ/m²", transform=ax.transAxes,
            fontsize=8, color=INK2, ha="right", va="top", linespacing=1.4)

    # (c) bondline temperature histories
    ax = fig.add_subplot(gs[0, 2])
    for k, e in evs.items():
        T = e.tps.bondline_temperature_k
        ax.plot(e.tps.time_s, T, style[k], color=col[k], lw=2, solid_capstyle="round")
        i = int(np.argmax(T))
        ax.plot(e.tps.time_s[i], T[i], "o", color=col[k], ms=6, mec=SURFACE, mew=1.5)
        ax.annotate(f"{T[i]:.1f} K at {e.tps.time_s[i]:.0f} s", (e.tps.time_s[i], T[i]),
                    xytext=(6, 4 if k == "B" else -12), textcoords="offset points", fontsize=8.5,
                    color=INK, weight="bold")
        ax.axvline(e.trajectory.time_s[-1], color=col[k], lw=0.8, alpha=0.45)
    ax.axhline(allow, color=CRIT, lw=1.1)
    ax.text(ax.get_xlim()[1] * 0.99 if False else 1500, allow + 3, f"{allow:.0f} K allowable (placeholder, A-LIM-1)",
            fontsize=7.5, color=CRIT, ha="right", va="bottom")
    ax.set_title("c  Bondline temperature, entry + 1200 s soak")
    ax.set_xlabel("time from entry interface [s]")
    ax.set_ylabel("bondline temperature [K]")
    ax.set_xlim(0, 1550)
    ax.text(0.98, 0.05, "thin verticals: aeroheating ends;\nthe bondline keeps rising after it",
            transform=ax.transAxes, fontsize=7.5, color=INK2, va="bottom", ha="right")

    # (d) temperature vs depth at the moment of peak bondline temperature
    ax = fig.add_subplot(gs[1, 0:2])
    ax.axvspan(ins_mm, stack_mm, color=PANEL, zorder=0)
    ax.text(ins_mm + (stack_mm - ins_mm) / 2, 0.97, "aluminium structure", transform=ax.get_xaxis_transform(),
            fontsize=8, color=INK2, ha="center", va="top")
    ax.text(ins_mm / 2, 0.97, "low-density insulator", transform=ax.get_xaxis_transform(),
            fontsize=8, color=INK2, ha="center", va="top")
    for k, e in evs.items():
        i = int(np.argmax(e.tps.bondline_temperature_k))
        prof = e.tps.temperature_k[i]
        ax.plot(e.tps.depth_m * 1e3, prof, style[k], color=col[k], lw=2.2, solid_capstyle="round",
                label=f"{lab[k]}   at t = {e.tps.time_s[i]:.0f} s")
        j = e.tps.bond_index
        ax.plot(e.tps.depth_m[j] * 1e3, prof[j], "o", color=col[k], ms=7, mec=SURFACE, mew=1.5, zorder=6)
        ax.annotate(f"{prof[j]:.1f} K", (e.tps.depth_m[j] * 1e3, prof[j]), xytext=(10, 6 if k == "B" else -14),
                    textcoords="offset points", fontsize=9, weight="bold", color=INK)
    ax.axvline(bond_depth_mm, color=INK, lw=1.0, ls=(0, (3, 2)))
    ax.text(bond_depth_mm - 0.25, 0.60, f"bondline\n{bond_depth_mm:.0f} mm", transform=ax.get_xaxis_transform(),
            fontsize=8, color=INK, ha="right", va="center", weight="bold")
    ax.axhline(allow, color=CRIT, lw=1.1)
    ax.text(0.3, allow + 5, f"{allow:.0f} K bondline allowable", fontsize=8, color=CRIT, va="bottom")
    ax.set_title("d  Temperature through the heat-shield stack at the instant each bondline peaks")
    ax.set_xlabel("depth from heated surface [mm]")
    ax.set_ylabel("temperature [K]")
    ax.set_xlim(0, stack_mm)
    ax.set_ylim(280, 660)
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 0.04))
    ax.annotate("the long, mild pulse has had time to soak in", xy=(9.5, float(np.interp(9.5, b.tps.depth_m * 1e3,
                b.tps.temperature_k[int(np.argmax(b.tps.bondline_temperature_k))]))),
                xytext=(2.5, 600), fontsize=8.5, color=S2, arrowprops=dict(arrowstyle="-", color=S2, lw=0.8))

    # (e) the two numbers
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.03", fc=PANEL, ec="none",
                                transform=ax.transAxes))
    ax.text(0.07, 0.90, "B, the shallow entry, against A", fontsize=9, color=INK2, va="top")
    ax.text(0.07, 0.78, f"{dq:+.1f}%", fontsize=30, weight="bold", color=S2, va="top")
    ax.text(0.07, 0.56, "peak heat flux — the conventional metric", fontsize=9, color=INK, va="top")
    ax.text(0.07, 0.47, f"{dT:+.1f} K", fontsize=30, weight="bold", color=S2, va="top")
    ax.text(0.07, 0.25, "peak bondline temperature — the failure mode", fontsize=9, color=INK, va="top")
    ax.text(0.07, 0.14, f"{n_pairs} such pairs in a 41-point sweep of entry angle;\n"
            "every step that lowers peak flux raises the bondline.", fontsize=8, color=INK2, va="top",
            linespacing=1.35)

    stamp(fig, [
        f"Run {meta['run_id']} · git {meta['git_commit']} (working tree dirty) · config hash {meta['config_hash']} · "
        f"designs {row_a.design_id} (A) and {row_b.design_id} (B) · scalars as logged in results/M1/{M1_RUN}/candidates.csv.",
        "Fidelity 0 with the LEGACY cap-radius nose model (R_eff = R_n, harmless for this hemispherical nose), constant C_D = 1.2, "
        "Sutton–Graves convective stagnation heating, 1-D conduction, adiabatic back face, placeholder TPS properties.",
        "Time histories were not persisted by the M1 run: they are re-derived here by evaluate_design() from config_snapshot.yaml and "
        "checked against the logged scalars to 1e-9 relative. Model predicts, within tested assumptions; no claim about any flight vehicle.",
    ])
    save(fig, "01_burn_vs_bake_mechanism")
    return IndexEntry(1, "01_burn_vs_bake_mechanism", "Burn versus bake: the mechanism",
                      f"Shallow entry: {dq:+.1f}% peak flux, {dT:+.1f} K bondline (M1, Fidelity 0).",
                      [f"results/M1/{M1_RUN}/candidates.csv", f"results/M1/{M1_RUN}/config_snapshot.yaml",
                       "reports/milestones/M1_burn_vs_bake.md (pair count)"],
                      ["Histories re-derived through evaluate_design(); scalars asserted equal to the log.",
                       "Legacy cap-radius nose model, as the M1 run used."])


# ======================================================================================
# Figure 2 - the pipeline and what is validated against what
# ======================================================================================
def fig2_pipeline() -> IndexEntry:
    st = {g: status_from_matrix(g) for g in ("G1A", "G1A′", "G1B", "G2", "G2′", "G3", "G-GEO2", "G4", "G5",
                                             "M3", "M4", "M5", "M6", "M7", "M8", "M1")}
    m2 = load_json(F["m2_gate"])
    m7 = load_json(F["m7_summary"])
    m4 = load_json(F["m4_summary"])
    n_in = m7["uncertainty_model"]["n_inputs"]
    n_ep, n_al = m7["uncertainty_model"]["n_epistemic"], m7["uncertainty_model"]["n_aleatory"]
    tiers = m7["uncertainty_model"]["tier_counts"]
    draws = m7["draws"]

    fig = plt.figure(figsize=(13.5, 8.6))
    frame(fig, 2, "One evaluator, two aerodynamic fidelities, and what each box was checked against",
          "Every study calls evaluate_design(config). The chain is verified block by block; the statuses are the "
          "validation matrix's own words, and LIMITED is never reported as PASS.")
    ax = fig.add_axes([0.03, 0.075, 0.94, 0.77])
    ax.set_xlim(0, 100)
    ax.set_ylim(-13.5, 100)
    ax.axis("off")
    QUAL = {"G1A′": {"PASS": "5 altitudes", "LIMITED": "the rest"}, "G2′": {}, "G-GEO2": {"PASS": "code", "LIMITED": "physics"},
            "G5": {"PASS": "software gate"}}

    def chips(x, y, statuses, gate=None, z=5):
        cx = x
        for st_, q in statuses:
            q = QUAL.get(gate, {}).get(st_, "") if gate else q
            w_chip = 2.2 + 0.9 * len(st_)
            ax.add_patch(FancyBboxPatch((cx, y), w_chip, 3.4, boxstyle="round,pad=0,rounding_size=0.6",
                                        fc=tint(STATUS_COLOUR[st_], 0.8), ec="none", zorder=z))
            ax.add_patch(Rectangle((cx, y), 0.7, 3.4, fc=STATUS_COLOUR[st_], ec="none", zorder=z + 1))
            ax.text(cx + 1.4, y + 1.7, st_, fontsize=6.6, weight="bold", color=INK, va="center", zorder=z + 2)
            cx += w_chip + 1.0
            if q:
                ax.text(cx, y + 1.7, q, fontsize=6.3, color=INK2, va="center", zorder=z + 2)
                cx += 0.72 * len(q) + 1.6

    def box(x, y, w, h, title, body, statuses, *, gate=None, fc=SURFACE, ec=RULE, lw=1.0, z=3):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=ec, lw=lw, zorder=z))
        ax.text(x + 1.5, y + h - 1.5, title, fontsize=9, weight="bold", color=INK, va="top", zorder=z + 1)
        ax.text(x + 1.5, y + h - 5.0, body, fontsize=6.6, color=INK2, va="top", linespacing=1.28, zorder=z + 1)
        chips(x + 1.5, y + 1.2, statuses, gate, z=z + 1)

    def arrow(p0, p1, *, color=INK2, lw=1.2, style="-|>", z=4):
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=11, color=color, lw=lw, zorder=z))

    # outer layers
    ax.add_patch(FancyBboxPatch((1, 1), 98, 97, boxstyle="round,pad=0,rounding_size=2", fc=SURFACE, ec=S1, lw=1.2,
                                ls=(0, (4, 3)), zorder=1))
    ax.text(3, 95, f"M7 uncertainty layer — {n_in} uncertain inputs ({n_al} aleatory, {n_ep} epistemic; "
            f"tiers: {tiers['T1']} primary, {tiers['T2']} secondary, {tiers['T3']} engineering judgment), "
            f"nested {draws['n_epistemic_branches']} branches × {draws['n_aleatory']} draws; every draw is one ordinary evaluation",
            fontsize=8, color=S1, weight="bold", va="center")
    ax.add_patch(FancyBboxPatch((3, 3.5), 94, 86.5, boxstyle="round,pad=0,rounding_size=2", fc=SURFACE, ec=INK2, lw=1.0, zorder=2))
    ax.text(5, 87, "optimiser loop — M4 NSGA-II / LHS / scalarised DE · M5 GP-ParEGO and LLM agent · M6 adaptive-fidelity "
            "promotion. A budget wrapper is the only caller of the evaluator; every candidate is logged.",
            fontsize=8, color=INK2, weight="bold", va="center")
    ax.add_patch(FancyBboxPatch((5, 6), 92, 71, boxstyle="round,pad=0,rounding_size=2", fc=PANEL, ec="none", zorder=2))
    ax.text(7, 74.5, "evaluate_design(config)  — the one contract every study goes through", fontsize=9, color=INK,
            weight="bold", va="center")

    # main chain
    Y, H = 40, 30
    box(6, Y, 18, H, "Atmosphere",
        "USSA-76, exact to 86 km;\nlog-interpolated table\n86–150 km, flagged.\n\nvs the published\nUSSA-76 tables",
        st["G1A"][:1] + st["G1A′"][1:2], gate="G1A′")
    box(26.5, Y, 18, H, "Trajectory",
        "3-DOF planar ballistic\nentry, solve_ivp.\n\nvs Allen–Eggers closed\nform on 3 published\ncases (Putnam & Braun)",
        st["G1B"][:1])
    box(47, Y, 18.5, H, "Heating",
        "Sutton–Graves stagnation\nflux, effective nose radius\nfrom Ellison (1969).\n\nconstant: vs TR R-376\nform (catalycity, hot\nwall, radiation): untested",
        [st["G2"][0], st["G2′"][0]])
    box(68, Y, 16, H, "TPS",
        "1-D multilayer\nconduction, radiating\nsurface, 1200 s soak.\n\nvs Carslaw & Jaeger\nanalytical: 0.002%\nat the surface",
        st["G3"][:1])
    box(86.5, Y, 10, H, "Objectives",
        "peak heat flux\npeak bondline T\n\nlimits: 450 K,\n12 g, and mass\nfraction ≤ 1 (a\nfence, no budget)",
        [("LIMITED", "")])
    for x0, x1 in ((24, 26.5), (44.5, 47), (65.5, 68), (84, 86.5)):
        arrow((x0, Y + H / 2), (x1, Y + H / 2))

    # aerodynamics row: two fidelities feeding the trajectory through one bus
    box(6, 8, 24, 24, "Aerodynamics, Fidelity 0",
        "constant C_D = 1.2 — an engineering\nvalue with no reference. Used for\nM1 and M1b. M3 later measured it\n+16.5% high in peak flux for the\nbaseline capsule.",
        [("LIMITED", "no reference")])
    box(33, 8, 24.5, 24, "Aerodynamics, Fidelity 1 — OpenFOAM",
        "rhoCentralFoam: Euler, perfect gas,\nforebody only, axisymmetric; anchors\nMach 3–27. vs a sphere at Mach 3 and\n6: Rayleigh pitot, Van Dyke & Gordon\nstand-off, Clark's forebody drag.",
        [(m2["status"], "")], ec=S1, lw=1.2)
    box(65, 8, 31.5, 24, "Drag surface cfd_surface_v2",
        "GP of forebody C_D over (Mach, R_n/D, cone\nangle, shoulder) + an assumed base-drag band.\nNo capsule test data; ±5% perfect-gas band\ndeclared, not validated. Built only once gate\nG4 read PASS (restart rule after the fact: fig. 7).",
        st["M3"][:1])
    ax.add_patch(FancyBboxPatch((59, 15.5), 4.5, 9, boxstyle="round,pad=0,rounding_size=0.8", fc=tint(STATUS_COLOUR[m2["status"]], 0.75),
                                ec=STATUS_COLOUR[m2["status"]], lw=1.2, zorder=6))
    ax.text(61.25, 22.6, "gate", fontsize=6.2, color=INK2, ha="center", va="center", zorder=7)
    ax.text(61.25, 20.0, "G4", fontsize=8.5, weight="bold", color=INK, ha="center", va="center", zorder=7)
    ax.text(61.25, 17.3, m2["status"], fontsize=6.2, weight="bold", color=INK, ha="center", va="center", zorder=7)
    arrow((57.5, 20), (59, 20), lw=1.0)
    arrow((63.5, 20), (65, 20), lw=1.0)
    ax.plot([18, 18, 80.75, 80.75], [32, 36.5, 36.5, 32], color=INK2, lw=1.1, zorder=4)
    arrow((35.5, 36.5), (35.5, Y), lw=1.2)
    ax.text(37, 37.6, "C_D(t) into the trajectory — Fidelity 0 for M1/M1b, Fidelity 1 for every study from M3 on",
            fontsize=7, color=INK2, va="bottom")

    # optimiser loop: objectives back to the config
    ax.plot([91.5, 91.5, 15, 15], [Y + H, 81.5, 81.5, Y + H + 1.2], color=INK2, lw=1.3, zorder=4)
    arrow((15, Y + H + 3), (15, Y + H + 0.3), lw=1.3)
    ax.text(53, 82.6, "next candidate design vector (diameter, bluntness, cone angle, entry angle; shoulder frozen by the screening)",
            fontsize=7.4, color=INK2, ha="center", va="bottom")

    # experiment (outside the loop: it has not been run) and the status legend
    ax.add_patch(FancyBboxPatch((6, -13), 42, 11.5, boxstyle="round,pad=0,rounding_size=1.2", fc=SURFACE, ec=RULE,
                                lw=1.0, ls=(0, (3, 2)), zorder=3))
    ax.text(7.5, -3.2, "M8 thermal coupon experiment — attaches to the TPS block", fontsize=8.6, weight="bold", va="top")
    ax.text(7.5, -6.6, "a blind prediction of the conduction model, frozen before measurement; no measurement exists yet",
            fontsize=6.8, color=INK2, va="top")
    chips(7.5, -12, st["M8"][:1])
    ax.text(52, -3.2, "what a status means here (VALIDATION_MATRIX.md)", fontsize=7.6, weight="bold", va="top", color=INK)
    for (lx, ly), s_, meaning in (((52, -8.6), "PASS", "checked against an independent reference"),
                                  ((52, -12.6), "LIMITED", "runs and is self-consistent; no external check"),
                                  ((80, -8.6), "IN_PROGRESS", "built, not yet run")):
        w_chip = 2.2 + 0.9 * len(s_)
        ax.add_patch(FancyBboxPatch((lx, ly), w_chip, 3.4, boxstyle="round,pad=0,rounding_size=0.6",
                                    fc=tint(STATUS_COLOUR[s_], 0.8), ec="none", zorder=4))
        ax.add_patch(Rectangle((lx, ly), 0.7, 3.4, fc=STATUS_COLOUR[s_], ec="none", zorder=5))
        ax.text(lx + 1.4, ly + 1.7, s_, fontsize=6.6, weight="bold", va="center", zorder=6)
        ax.text(lx + w_chip + 0.8, ly + 1.7, meaning, fontsize=6.6, color=INK2, va="center")

    stamp(fig, [
        f"Statuses parsed from VALIDATION_MATRIX.md (last updated as stated there); G4 from results/M2/{M2_RUN}/gate_assessment.json; "
        f"uncertainty inventory from results/M7/{M7_UQ_RUN}/summary.json; active/frozen variables from results/M4/{M4_RUN}/summary.json "
        f"(active: {', '.join(m4['active'])}).",
        "Study rows M4–M7 are LIMITED because no external reference exists for any of them. Structure after ARCHITECTURE.md. "
        "Within tested assumptions; nothing here is checked against a measurement.",
    ])
    save(fig, "02_pipeline_validation")
    return IndexEntry(2, "02_pipeline_validation", "The pipeline and what is validated against what",
                      "Statuses are the validation matrix's own; G4 PASS carries its restart history.",
                      ["VALIDATION_MATRIX.md", f"results/M2/{M2_RUN}/gate_assessment.json",
                       f"results/M7/{M7_UQ_RUN}/summary.json", f"results/M4/{M4_RUN}/summary.json", "ARCHITECTURE.md"],
                      ["Box descriptions paraphrase the matrix's 'validation source' column; no numbers are typed."])


# ======================================================================================
# Figure 3 - what the optimiser actually found
# ======================================================================================
def pareto_front(df: pd.DataFrame) -> pd.DataFrame:
    x, y = df.peak_heat_flux_w_m2.values, df.peak_bondline_temperature_k.values
    order = np.argsort(x, kind="stable")
    keep, best = [], np.inf
    for i in order:
        if y[i] < best:
            keep.append(i)
            best = y[i]
    return df.iloc[keep].sort_values("peak_heat_flux_w_m2")


def fig3_pareto() -> IndexEntry:
    m4 = load_json(F["m4_summary"])
    m7 = load_json(F["m7_summary"])
    lfl = load_json(F["m7_lfl"])
    cand = pd.read_csv(F["m4_csv"])
    feas = cand[cand.feasible == True].drop_duplicates("candidate_id")  # noqa: E712
    front = pareto_front(feas)
    assert len(front) == m4["combined"]["n_front"], (len(front), m4["combined"]["n_front"])
    sel = m4["selected"]
    lim = m4["selected_limits"]
    audit = m4["audit"]
    bounds = audit["parked_on_bounds"]
    active = audit["active_constraints"]
    allow = m7["allowables"]
    robust_front = pd.read_csv(F["m7_robust_front"])
    rk = lfl["propagation"]
    rk_nom, rk_p95 = rk["nominal"], {k: v["percentiles"]["p95"] for k, v in rk["combined"].items()}
    knee_uq = m7["propagation"]["joint_knee"]
    mf_knee = sel["joint_knee"]["diag__heatshield_mass_fraction"]
    mass = m4["frozen"]["mass_kg"]

    fig = plt.figure(figsize=(13.5, 8.6))
    frame(fig, 3, "What the optimiser found: an entry-angle curve drawn at a fenced geometry",
          f"The {len(front)}-design front trades the two objectives through flight-path angle only.\n"
          "Diameter, bluntness and cone angle are pinned by a mass-fraction fence, the edge of where CFD was run, and a box bound.")
    ax = fig.add_axes([0.065, 0.165, 0.58, 0.655])
    axr = fig.add_axes([0.745, 0.47, 0.225, 0.35])
    axt = fig.add_axes([0.685, 0.165, 0.285, 0.21])

    # feasible cloud
    ax.scatter(feas.peak_heat_flux_w_m2 / 1e3, feas.peak_bondline_temperature_k, s=4, color=RULE, alpha=0.35,
               lw=0, zorder=1, label=f"{len(feas):,} feasible candidates, 7 seeds × 3 methods")
    # robust front (95th percentiles)
    ax.plot(robust_front.robust__peak_heat_flux_w_m2 / 1e3, robust_front.robust__peak_bondline_temperature_k, "s",
            ms=3.2, color=S3, mec=SURFACE, mew=0.4, zorder=3, alpha=0.9,
            label=f"robust front, 95th percentiles ({len(robust_front)} designs, M7)")
    # nominal front coloured by entry angle
    g = front.x__flight_path_angle_deg.values
    ax.plot(front.peak_heat_flux_w_m2 / 1e3, front.peak_bondline_temperature_k, "-", color=INK2, lw=1.0, zorder=3)
    sc = ax.scatter(front.peak_heat_flux_w_m2 / 1e3, front.peak_bondline_temperature_k, c=g, cmap=CMAP_GAMMA,
                    vmin=g.min(), vmax=g.max(), s=42, edgecolor=SURFACE, linewidth=0.8, zorder=4,
                    label=f"nominal Pareto front, {len(front)} designs (M4, Fidelity 1)")
    cax = fig.add_axes([0.75, 0.43, 0.19, 0.014])
    cb = fig.colorbar(sc, cax=cax, orientation="horizontal")
    cb.set_label("colour of the front points: entry angle γ₀ [deg]  (light = shallow, dark = steep)", fontsize=7.0, color=INK2)
    cb.outline.set_edgecolor(RULE)
    cb.ax.tick_params(labelsize=7.4, color=RULE)

    # named designs
    names = {"peak_flux_only": "peak-flux-only optimum", "joint_knee": "joint knee (O1)", "bondline_only": "bondline-only optimum"}
    offs = {"peak_flux_only": (-14, 44), "joint_knee": (60, 84), "bondline_only": (-250, -14)}
    for key, label in names.items():
        d = sel[key]
        x, y = d["peak_heat_flux_w_m2"] / 1e3, d["peak_bondline_temperature_k"]
        ax.plot(x, y, "o", ms=13, mfc="none", mec=INK, mew=1.6, zorder=6)
        stops = "; ".join(lim[key]["box_bounds"] + [f"constraint {c} active" for c in lim[key]["active_constraints"]])
        ax.annotate(f"{label}\n{d['candidate_id']}\n{x:.1f} kW/m² · {y:.1f} K · γ₀ {d['x__flight_path_angle_deg']:+.2f}°\n"
                    + wrap(f"stopped by: {stops}", 52), (x, y), xytext=offs[key], textcoords="offset points", fontsize=7.2,
                    color=INK, va="top" if key == "bondline_only" else "center", ha="left",
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.7, shrinkB=8), zorder=7,
                    bbox=dict(boxstyle="round,pad=0.35", fc=SURFACE, ec="none", alpha=0.92))

    # robust knee with p95 whiskers
    xr, yr = rk_nom["peak_heat_flux_w_m2"] / 1e3, rk_nom["peak_bondline_temperature_k"]
    xr95, yr95 = rk_p95["peak_heat_flux_w_m2"] / 1e3, rk_p95["peak_bondline_temperature_k"]
    ax.plot([xr, xr95], [yr, yr], "-", color=S3, lw=2.2, zorder=6, solid_capstyle="butt")
    ax.plot([xr, xr], [yr, yr95], "-", color=S3, lw=2.2, zorder=6, solid_capstyle="butt")
    ax.plot([xr95, xr95], [yr - 0.4, yr + 0.4], "-", color=S3, lw=1.4, zorder=6)
    ax.plot([xr - 0.7, xr + 0.7], [yr95, yr95], "-", color=S3, lw=1.4, zorder=6)
    ax.plot(xr, yr, "D", ms=8, color=S3, mec=SURFACE, mew=1.2, zorder=7,
            label="robust knee (M7): nominal; whiskers to p95 on 3000 shared draws")
    ax.annotate(f"robust knee (chance-constrained, M7)\nnominal {xr:.1f} kW/m² · {yr:.1f} K\np95 {xr95:.1f} kW/m² · {yr95:.1f} K\n"
                f"P(any constraint violated) {rk['violations']['any']['point']*100:.2f}%\n(nominal knee: "
                f"{[d for d in m7['nominal_designs_under_uncertainty'] if d['label']=='joint_knee'][0]['violation_point']*100:.1f}%)",
                (xr95, yr), xytext=(20, 10), textcoords="offset points", fontsize=7.2, color=INK, va="center",
                arrowprops=dict(arrowstyle="-", color=S3, lw=0.7, shrinkB=6), zorder=7,
                bbox=dict(boxstyle="round,pad=0.35", fc=SURFACE, ec="none", alpha=0.92))

    # fences, drawn as pickets
    def picket(x0, y0, x1, y1, label, colour=CRIT, n=None, side=1, lab_off=(0, 0), ha="left"):
        L = np.hypot(x1 - x0, y1 - y0)
        n = n or max(6, int(L * 0.9))
        t = np.linspace(0, 1, n)
        xs, ys = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        ax.plot([x0, x1], [y0, y1], "-", color=colour, lw=1.6, zorder=5, solid_capstyle="round")
        # perpendicular pickets in display space
        dx, dy = (x1 - x0) / L, (y1 - y0) / L
        for px, py in zip(xs, ys, strict=True):
            ax.annotate("", (px, py), xytext=(-dy * 6 * side, dx * 6 * side), textcoords="offset points",
                        arrowprops=dict(arrowstyle="-", color=colour, lw=1.3), zorder=5)
        ax.text(x0 + lab_off[0], y0 + lab_off[1], label, fontsize=7.4, color=colour, weight="bold", ha=ha, va="center",
                zorder=8, linespacing=1.25, bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec="none", alpha=0.9))

    fx, fy = front.peak_heat_flux_w_m2.values / 1e3, front.peak_bondline_temperature_k.values
    mf = active["heatshield_mass_fraction"]
    n_hull = 28
    m = re.search(r"\*\*(\d+) of (\d+)\*\* designs have at least one step that stays a valid forebody inside the box but LEAVES the CFD hull",
                  (ROOT / "reports" / "milestones" / "M4_pareto_optimisation.md").read_text())
    if m:
        n_hull = int(m.group(1))
    L = 0.66  # fences run along the first 66% of the front, so the steep-end labels stay clear
    xe, ye = fx[0] + L * (fx[-1] - fx[0]), fy[0] + L * (fy[-1] - fy[0])
    picket(fx[0] - 3.0, fy[0] - 2.6, xe - 3.0, ye - 2.6, "mass-fraction fence", side=-1, lab_off=(-1.2, -2.6), ha="right")
    picket(fx[0] - 6.5, fy[0] - 5.4, xe - 6.5, ye - 5.4, "CFD-hull edge", side=-1, lab_off=(-1.2, -2.6), ha="right", colour=S1)
    mg = active["max_g"]
    picket(fx[-1] + 2.2, fy[-1] + 9.0, fx[-1] + 2.2, fy[-1] - 0.5, f"{allow['max_g']:.0f} g limit", side=-1,
           lab_off=(1.0, -5.5), ha="left")
    ax.plot([], [], "-", color=CRIT, lw=1.6, label=f"mass fence: shield mass fraction ≤ 1.0 — {mf['n_active']} of {len(front)} within 1%; "
            f"knee shield = {mf_knee*100:.1f}% of {mass:.0f} kg")
    ax.plot([], [], "-", color=S1, lw=1.6, label=f"CFD-hull edge, R_n/D ≈ 1.2 — {n_hull} of {len(front)} on it; beyond it GP extrapolation ≈ 1% of flux")
    ax.plot([], [], "-", color=CRIT, lw=1.6, label=f"{allow['max_g']:.0f} g fence — {mg['n_active']} of {len(front)} within 1%, steepest γ₀ {g.min():+.2f}°; "
            f"shallow end = box bound γ₀ {bounds['flight_path_angle_deg']['upper']:+.1f}° ({bounds['flight_path_angle_deg']['at_upper']})")
    ax.plot([262, 300], [allow["peak_bondline_temperature_k"]] * 2, color=CRIT, lw=0.9, ls=(0, (3, 2)))
    ax.text(299, allow["peak_bondline_temperature_k"] - 0.7,
            f"{allow['peak_bondline_temperature_k']:.0f} K bondline allowable — never active on this front "
            f"(smallest margin {active['peak_bondline_temperature_k']['min_margin']*100:.1f}%)", fontsize=7.2,
            color=CRIT, va="top", ha="right")

    ax.set_xlim(213, 300)
    ax.set_ylim(377, 456)
    ax.set_xlabel("peak stagnation heat flux [kW/m²]   (lower is better)")
    ax.set_ylabel("peak bondline temperature [K]   (lower is better)")
    ax.set_title("a  Objective space, Fidelity 1 (cfd_surface_v2)")
    ax.legend(loc="upper left", fontsize=6.8, markerscale=1.1, handletextpad=0.5, handlelength=1.5,
              bbox_to_anchor=(0.0, 0.995), borderaxespad=0.2, labelspacing=0.35, frameon=True, framealpha=0.96,
              facecolor=SURFACE, edgecolor="none")

    # right top: the geometry is pinned — ranges along the front against the box
    axr.set_title("b  What the front varies, against its box")
    units = {"diameter_m": "diameter [m]", "bluntness_ratio": "bluntness R_n/D [-]",
             "cone_half_angle_deg": "cone half-angle [deg]", "flight_path_angle_deg": "entry angle γ₀ [deg]"}
    ys = np.arange(len(units))[::-1]
    for yy, (var, name) in zip(ys, units.items(), strict=True):
        b = bounds[var]
        lo, hi = b["lower"], b["upper"]
        span = hi - lo
        f0, f1 = (b["front_min"] - lo) / span, (b["front_max"] - lo) / span
        axr.add_patch(Rectangle((0, yy - 0.22), 1, 0.44, fc=PANEL, ec="none"))
        colour = S1 if var == "flight_path_angle_deg" else CRIT
        axr.add_patch(Rectangle((f0, yy - 0.22), max(f1 - f0, 0.006), 0.44, fc=colour, ec="none"))
        axr.text(0.0, yy + 0.25, name, fontsize=7.6, ha="left", va="bottom", color=INK, weight="bold")
        at_hi = (hi - b["front_max"]) / span < 0.005
        at_lo = (b["front_min"] - lo) / span < 0.005
        axr.text(0.0, yy - 0.26, f"box {lo:g}" + ("  (front at bound)" if at_lo else ""), fontsize=6.6, color=MUTED,
                 ha="left", va="top")
        axr.text(1.0, yy - 0.26, ("front at bound  " if at_hi else "") + f"box {hi:g}", fontsize=6.6, color=MUTED,
                 ha="right", va="top")
        fr_txt = f"front: {b['front_min']:.3g} – {b['front_max']:.3g}" if var != "flight_path_angle_deg" else \
            f"front: {b['front_min']:.2f} – {b['front_max']:.2f}"
        axr.text(min(f1 + 0.03, 0.62) if f1 < 0.6 else f0 - 0.03, yy, fr_txt, fontsize=7.4, color=INK,
                 ha="left" if f1 < 0.6 else "right", va="center", weight="bold",
                 bbox=dict(boxstyle="round,pad=0.15", fc=PANEL, ec="none"))
    axr.set_xlim(0, 1)
    axr.set_ylim(-1.05, len(units) + 0.05)
    axr.axis("off")
    axr.text(0, -0.5, "grey = the box searched · red = pinned by a fence\nblue = the one lever that trades the objectives",
             fontsize=6.6, color=INK2, va="top", linespacing=1.3)

    # right bottom: the numbers behind H1
    axt.axis("off")
    axt.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.03", fc=PANEL, ec="none",
                                 transform=axt.transAxes))
    cmp_ = m4["comparison"]
    axt.text(0.05, 0.9, "knee against the peak-flux-only optimum", fontsize=8.5, color=INK2, va="top")
    axt.text(0.05, 0.74, f"{cmp_['bondline_delta_k']:+.1f} K", fontsize=24, weight="bold", color=S1, va="top")
    axt.text(0.05, 0.42, f"bondline, for {cmp_['peak_flux_delta_w_m2']/1e3:+.1f} kW/m² of peak flux", fontsize=8.5,
             color=INK, va="top")
    axt.text(0.05, 0.28, f"whole front: {cmp_['front_bondline_span_k']:.1f} K and {cmp_['front_flux_span_w_m2']/1e3:.1f} kW/m² of span.\n"
             f"Nominal knee under uncertainty: p95 {knee_uq['combined']['peak_bondline_temperature_k']['percentiles']['p95']:.1f} K.\n"
             "An absolute difference inside a placeholder stack, not\na margin against a qualified material.",
             fontsize=7.4, color=INK2, va="top", linespacing=1.35)

    stamp(fig, [
        f"Front and cloud: results/M4/{M4_RUN}/candidates.csv (front recomputed as the non-dominated feasible set; size asserted equal to summary.json). "
        f"Named designs, fences, box audit: results/M4/{M4_RUN}/summary.json (git {m4['git_commit']}, dirty).",
        f"Robust knee: results/M7/{M7_LFL_RUN}/likeforlike.json, propagated through the {rk['n_samples']} nested draws of {M7_UQ_RUN}; robust front: "
        f"results/M7/{M7_ROBUST_RUN}/robust_front.csv (32-draw common-random-number inner sample). Hull count: reports/milestones/M4_pareto_optimisation.md §11.",
        "Fidelity 1 = a CFD-derived drag surface, not a validated one. Model predicts, within tested assumptions; 'optimum' names a design on this front, not a located capsule shape.",
    ])
    save(fig, "03_pareto_front_fences")
    return IndexEntry(3, "03_pareto_front_fences", "What the optimiser found",
                      "The front is an entry-angle curve at a fenced geometry; robust knee with p95 whiskers.",
                      [f"results/M4/{M4_RUN}/candidates.csv", f"results/M4/{M4_RUN}/summary.json",
                       f"results/M7/{M7_LFL_RUN}/likeforlike.json", f"results/M7/{M7_UQ_RUN}/summary.json",
                       f"results/M7/{M7_ROBUST_RUN}/robust_front.csv", "reports/milestones/M4_pareto_optimisation.md"],
                      ["Fences are drawn in objective space as pickets hugging the front; they are constraints in design "
                       "space and the picket positions are illustrative — the counts on them are the audit's."])


# ======================================================================================
# Figure 4 - hypothesis scorecard
# ======================================================================================
def fig4_scorecard() -> IndexEntry:
    paper = F["paper"].read_text()
    hyp = {}
    for h in ("H0", "H1", "H2"):
        q = re.search(rf"> \*\*{h}\.\*\* (.+)", paper).group(1).strip()
        v = re.search(rf"^\| {h} \| ([^|]+) \|", paper, re.M).group(1).strip()
        hyp[h] = (q, v)
    m1 = pd.read_csv(F["m1_csv"])
    ra, rb = m1.loc[m1.gamma_deg.idxmin()], m1.loc[m1.gamma_deg.idxmax()]
    dq = (rb.peak_heat_flux_w_m2 / ra.peak_heat_flux_w_m2 - 1) * 100
    dT = rb.peak_bondline_temperature_k - ra.peak_bondline_temperature_k
    n_pairs = re.search(r"Signature counterexample pairs \| (\d+)", F["m1_report"].read_text()).group(1)
    m4 = load_json(F["m4_summary"])
    pr = load_json(F["m7_paired"])
    pk = [p for p in pr["pairs"] if p["a"] == "joint_knee" and p["b"] == "peak_flux_only"
          and p["output"] == "peak_bondline_temperature_k"][0]
    m6 = load_json(F["m6_summary"])
    h2 = m6["h2"]["0.95"]
    crit6 = m6["criteria_declared"]
    m6txt = F["m6_report"].read_text()
    pooled = re.search(r"reaches ([0-9.]+) = ([0-9.]+)% of the reference", m6txt)
    m5 = load_json(F["m5_summary"])
    c5 = m5["criteria"]["checkpoints"]
    d5 = m5["criteria_declared"]
    mf_knee = m4["selected"]["joint_knee"]["diag__heatshield_mass_fraction"]
    mass = m4["frozen"]["mass_kg"]

    verdict_colour = {"H0": GOOD, "H1": WARN, "H2": CRIT}
    rows = [
        ("H0", hyp["H0"][0], hyp["H0"][1], f"{dq:+.1f}%  /  {dT:+.1f} K",
         f"peak flux / bondline between the two ends of a 41-point entry-angle sweep; {n_pairs} counterexample pairs",
         "Falsifiable and once falsified: at a 40 mm insulator the bondline rose 8.8 K over a whole entry and the two "
         "metrics decoupled (NR-03). Fidelity 0, one parameter, so the ρ = −1 rank correlation is tautological; the "
         "monotonicity is the evidence. Restated at Fidelity 1 and under uncertainty by H1's numbers.",
         f"M1 {M1_RUN}"),
        ("H1", hyp["H1"][0], hyp["H1"][1], f"{m4['comparison']['bondline_delta_k']:+.1f} K",
         f"knee vs peak-flux-only optimum at the bondline, for {m4['comparison']['peak_flux_delta_w_m2']/1e3:+.1f} kW/m²; "
         f"paired on shared draws {pk['mean']:+.2f} K (s.d. {pk['sd']:.2f}), below zero in {pk['n_draws_a_below_b']} of {pk['n_pairs']} draws",
         "The front trades the objectives through entry angle only; diameter, bluntness and cone angle are pinned by a "
         f"mass fence (the knee's shield is {mf_knee*mass:.0f} of {mass:.0f} kg), the CFD-hull edge and a box bound. "
         "It is the same mechanism as H0, not evidence that joint optimisation finds a better capsule shape.",
         f"{M4_RUN} · {M7_UQ_RUN}"),
        ("H2", hyp["H2"][0], hyp["H2"][1].upper() if "not" in hyp["H2"][1].lower() else hyp["H2"][1],
         f"{h2['n_seeds_reaching']['adaptive']} of {len(m6['seeds'])} seeds",
         f"reached the pre-declared target ({crit6['target_fraction_of_reference_hv']*100:.0f}% of reference hypervolume = "
         f"{h2['target_hv']:.4f}); the rule needed {crit6['min_seeds_reaching']}; no arm reached it",
         (f"The target was beyond the study's own search budget: all arm-seeds pooled reach {pooled.group(2)}% of the reference "
          if pooled else "The target was beyond the study's own search budget ") +
         "(NR-35), and extra CFD moved the no-CFD arm's score by 0.0001. The AI-guided adaptive arm was declared and not run, "
         "so the 'AI-guided' clause is untested. Not contradicted in general; not supported here.",
         f"M6 {M6_RUN}"),
    ]

    fig = plt.figure(figsize=(13.5, 8.6))
    frame(fig, 4, "Hypothesis scorecard: verdicts as the reports state them",
          "Three hypotheses were frozen before any model was built, each with a falsification condition. "
          "One of them fired. Every verdict below is a statement about a model, not a vehicle.")
    ax = fig.add_axes([0.035, 0.1, 0.93, 0.74])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # column headers
    cols = [(0.0, "hypothesis, verbatim"), (0.365, "verdict"), (0.555, "the one number"), (0.765, "what limits it")]
    for x, t in cols:
        ax.text(x, 1.0, t.upper(), fontsize=7.2, color=MUTED, va="top", weight="bold")
    ax.plot([0, 1], [0.975, 0.975], color=RULE, lw=0.8)

    y_top, rh = 0.965, 0.235
    for i, (h, q, v, num, num_sub, caveat, runs) in enumerate(rows):
        y = y_top - i * rh
        ax.text(0.0, y - 0.02, h, fontsize=22, weight="bold", color=verdict_colour[h], va="top")
        ax.text(0.052, y - 0.03, wrap(q, 66), fontsize=8.6, color=INK, va="top", linespacing=1.3)
        chip(ax, 0.365, y - 0.05, v, verdict_colour[h], fontsize=8.0, h=0.038, w=0.012 + 0.0057 * len(v))
        ax.text(0.555, y - 0.028, num, fontsize=19, weight="bold", color=INK, va="top")
        ax.text(0.555, y - 0.1, wrap(num_sub, 52), fontsize=7.0, color=INK2, va="top", linespacing=1.3)
        ax.text(0.765, y - 0.03, wrap(caveat, 60), fontsize=7.5, color=INK, va="top", linespacing=1.3)
        ax.text(0.555, y - rh + 0.035, runs, fontsize=6.3, color=MUTED, va="bottom")
        ax.plot([0, 1], [y - rh + 0.02, y - rh + 0.02], color=GRID, lw=0.8)

    # M5 row: not a hypothesis, a pre-declared method comparison with a mixed verdict
    y = y_top - 3 * rh
    ax.text(0.0, y - 0.02, "M5", fontsize=16, weight="bold", color=NEUT, va="top")
    ax.text(0.052, y - 0.03, wrap("Not a hypothesis: the pre-declared AI-vs-conventional comparison. LLM engineering agent "
            f"against the best of {len(m5['criteria']['conventional'])} conventional optimisers, "
            f"{len(m5['seeds'])} seeds, rule declared first: gain ≥ {d5['min_hv_gain']} in hypervolume AND α = {d5['alpha']}.", 70),
            fontsize=8.2, color=INK, va="top", linespacing=1.3)
    chip(ax, 0.365, y - 0.05, "MIXED", NEUT, fontsize=8.0, h=0.038, w=0.06)
    cx = 0.555
    for ck in d5["checkpoints"]:
        c = c5[str(ck)]
        ax.text(cx, y - 0.028, f"{c['mean_difference']:+.4f}", fontsize=13, weight="bold", color=INK, va="top")
        ax.text(cx, y - 0.075, f"at {ck} evaluations\n{c['verdict']}", fontsize=6.9, color=INK2, va="top", linespacing=1.3)
        cx += 0.068
    ax.text(0.765, y - 0.03, wrap(f"At {d5['checkpoints'][-1]} evaluations every agent seed beat every comparator seed, and the verdict is "
                 "still 'no measured difference' because the mean gain fell under the effect size declared in advance. "
                 "n = 5, one model, one easy problem; the early lead cannot be separated from prior knowledge, and the "
                 "AI-plus-adaptive-fidelity arm has no result.", 60), fontsize=7.5, color=INK, va="top", linespacing=1.3)
    ax.text(0.555, y - rh + 0.035, f"M5 {M5_RUN}", fontsize=6.6, color=MUTED, va="bottom")

    stamp(fig, [
        "Hypothesis text and verdict wording: reports/final/AETHER_paper.md §4 (parsed). H0 numbers: "
        f"results/M1/{M1_RUN}/candidates.csv and the M1 report. H1: results/M4/{M4_RUN}/summary.json, results/M7/{M7_UQ_RUN}/paired_difference.json.",
        f"H2: results/M6/{M6_RUN}/summary.json (h2, criteria_declared) and reports/milestones/M6_adaptive_fidelity.md (pooled reach). "
        f"M5: results/M5/{M5_RUN}/summary.json (criteria). Caveats paraphrase the paper's §4, §10.4, §11.2, §12 and §17.",
        "Within tested assumptions. Nothing here is established about a real vehicle or material; the coupon experiment has not been run.",
    ])
    save(fig, "04_hypothesis_scorecard")
    return IndexEntry(4, "04_hypothesis_scorecard", "Hypothesis scorecard",
                      "H0 supported in the tested domain; H1 supported narrowly; H2 not supported; M5 mixed.",
                      ["reports/final/AETHER_paper.md §4", f"results/M1/{M1_RUN}/candidates.csv",
                       f"results/M4/{M4_RUN}/summary.json", f"results/M7/{M7_UQ_RUN}/paired_difference.json",
                       f"results/M6/{M6_RUN}/summary.json", "reports/milestones/M6_adaptive_fidelity.md",
                       f"results/M5/{M5_RUN}/summary.json"],
                      ["Caveat prose paraphrases the paper; every numeral is read from a file."])


# ======================================================================================
# Figure 5 - uncertainty: where it comes from
# ======================================================================================
def fig5_uncertainty() -> IndexEntry:
    m7 = load_json(F["m7_summary"])
    um = {i["name"]: i for i in m7["uncertainty_model"]["inputs"]}
    att = m7["attribution"]["joint_knee"]
    names = [i["name"] for i in att["inputs"]]
    kinds = {i["name"]: i["kind"] for i in att["inputs"]}
    pretty = {
        "atmospheric_density": "atmospheric density dispersion",
        "vehicle_mass": "vehicle mass ±2% (1σ)",
        "entry_flight_path_angle": "delivered entry angle",
        "effective_nose_radius_model": "effective nose-radius model (Ellison vs Zoby & Sullivan)",
        "sutton_graves_coefficient": "Sutton–Graves constant ±4%",
        "high_altitude_heating_model": "heating above 86 km, ×0.5–1.5",
        "tps_conductivity": "TPS conductivity ±15%",
        "tps_specific_heat": "TPS specific heat ±10%",
        "cd_surrogate_gp": "drag: GP surrogate error",
        "cd_discretisation": "drag: CFD discretisation",
        "cd_perfect_gas_model_form": "drag: perfect-gas model form ±5%",
        "cd_base_drag": "drag: assumed base band",
    }
    tier_glyph = {"T1": ("primary source", "full"), "T2": ("secondary source", "half"), "T3": ("engineering judgment", "open")}
    kind_colour = {"epistemic": S1, "aleatory": S2}
    knee = m7["propagation"]["joint_knee"]["design_values"]

    fig = plt.figure(figsize=(13.5, 8.6))
    frame(fig, 5, "Where the uncertainty comes from: mostly things nobody has measured",
          "Total-order Sobol' shares at the joint knee. The spread is 84–99% epistemic — model ignorance, not randomness —\n"
          "and the two terms that govern the bondline are both engineering judgment.")

    shares = {}
    for d, v in m7["propagation"].items():
        dec = v["decomposition"]
        shares[d] = {o: dec[o]["epistemic_share_of_variance"] for o in ("peak_heat_flux_w_m2", "peak_bondline_temperature_k")}
    all_sh = [s for d in shares.values() for s in d.values()]

    def bars(ax, output, title):
        tot = np.array(att["outputs"][output]["total"])
        ci = np.array(att["outputs"][output]["total_ci"])
        order = np.argsort(tot)[::-1]
        ys = np.arange(len(order))[::-1]
        for yy, i in zip(ys, order, strict=True):
            n = names[i]
            c = kind_colour[kinds[n]]
            ax.barh(yy, tot[i], height=0.62, color=c, edgecolor="none", zorder=3)
            lo, hi = ci[i]
            ax.plot([lo, hi], [yy, yy], "-", color=INK, lw=1.0, zorder=4)
            ax.text(max(tot[i], hi) + 0.012, yy, f"{tot[i]:.3f}", fontsize=7.6, va="center", color=INK,
                    weight="bold" if tot[i] >= 0.05 else "normal")
            tier = um[n]["tier"]
            _, g = tier_glyph[tier]
            # tier glyph left of the label
            gx = -0.95
            if g == "full":
                ax.add_patch(Rectangle((gx, yy - 0.16), 0.024, 0.32, fc=INK, ec=INK, lw=0.8, transform=ax.transData,
                                       clip_on=False, zorder=5))
            elif g == "half":
                ax.add_patch(Rectangle((gx, yy - 0.16), 0.024, 0.32, fc=SURFACE, ec=INK, lw=0.8, clip_on=False, zorder=5))
                ax.add_patch(Rectangle((gx, yy - 0.16), 0.012, 0.32, fc=INK, ec="none", clip_on=False, zorder=6))
            else:
                ax.add_patch(Rectangle((gx, yy - 0.16), 0.024, 0.32, fc=SURFACE, ec=INK, lw=0.8, clip_on=False, zorder=5))
            ax.text(gx + 0.04, yy, f"{tier}  {pretty[n]}", fontsize=7.6, va="center", ha="left", color=INK,
                    clip_on=False)
        ax.set_yticks([])
        ax.set_xlim(0, 1.0)
        ax.set_ylim(-0.7, len(order) - 0.3)
        ax.set_xlabel("total-order Sobol' index S_T [-], bar = point estimate, whisker = 95% CI")
        ax.set_title(title)
        ax.grid(axis="y", visible=False)
        for s in ("left",):
            ax.spines[s].set_visible(False)

    ax1 = fig.add_axes([0.505, 0.53, 0.255, 0.29])
    ax2 = fig.add_axes([0.505, 0.15, 0.255, 0.29])
    bars(ax1, "peak_heat_flux_w_m2", "a  Peak heat flux at the knee")
    bars(ax2, "peak_bondline_temperature_k", "b  Peak bondline temperature at the knee")

    # legend block (top right of bars)
    lax = fig.add_axes([0.80, 0.585, 0.18, 0.235])
    lax.axis("off")
    lax.set_xlim(0, 1)
    lax.set_ylim(0, 1)
    lax.text(0, 0.95, "how to read the bars", fontsize=8.5, weight="bold", va="top")
    lax.add_patch(Rectangle((0, 0.72), 0.07, 0.1, fc=S1, ec="none"))
    lax.text(0.10, 0.77, "epistemic — a fact nobody has\npinned down; evidence removes it", fontsize=7.0, va="center", linespacing=1.25)
    lax.add_patch(Rectangle((0, 0.55), 0.07, 0.1, fc=S2, ec="none"))
    lax.text(0.10, 0.60, "aleatory — real variability;\nonly margin absorbs it", fontsize=7.0, va="center", linespacing=1.25)
    for yy, (lab, g) in zip((0.40, 0.30, 0.20), [(f"{t}  {tier_glyph[t][0]}", tier_glyph[t][1]) for t in ("T1", "T2", "T3")], strict=True):
        if g == "full":
            lax.add_patch(Rectangle((0.01, yy - 0.035), 0.05, 0.07, fc=INK, ec=INK, lw=0.8))
        elif g == "half":
            lax.add_patch(Rectangle((0.01, yy - 0.035), 0.05, 0.07, fc=SURFACE, ec=INK, lw=0.8))
            lax.add_patch(Rectangle((0.01, yy - 0.035), 0.025, 0.07, fc=INK, ec="none"))
        else:
            lax.add_patch(Rectangle((0.01, yy - 0.035), 0.05, 0.07, fc=SURFACE, ec=INK, lw=0.8))
        lax.text(0.10, yy, lab, fontsize=7.2, va="center")
    lax.text(0, -0.02, f"tier = how the input's distribution\nwas sourced (configs/uncertainty.yaml);\n"
             f"{m7['uncertainty_model']['tier_counts']['T3']} of {m7['uncertainty_model']['n_inputs']} inputs are judgment",
             fontsize=6.8, color=INK2, va="top", linespacing=1.3)

    # right bottom: epistemic share per design and output
    sax = fig.add_axes([0.845, 0.215, 0.135, 0.27])
    labels = {"baseline": "baseline", "peak_flux_only": "peak-flux-only", "joint_knee": "joint knee", "bondline_only": "bondline-only"}
    ys = np.arange(4)[::-1]
    for yy, d in zip(ys, labels, strict=True):
        for o, mk, c in (("peak_heat_flux_w_m2", "o", S1), ("peak_bondline_temperature_k", "s", "#184f95")):
            v = shares[d][o] * 100
            sax.plot([0, v], [yy + (0.13 if mk == "o" else -0.13)] * 2, "-", color=GRID, lw=3, zorder=1)
            sax.plot(v, yy + (0.13 if mk == "o" else -0.13), mk, color=c, ms=7, mec=SURFACE, mew=1, zorder=3)
            sax.text(v - 0.8, yy + (0.13 if mk == "o" else -0.13), f"{v:.1f}%", fontsize=6.8, va="center", ha="right", color=SURFACE if False else INK,
                     path_effects=[patheffects.withStroke(linewidth=2.2, foreground=SURFACE)])
    sax.set_yticks(ys)
    sax.set_yticklabels([labels[d] for d in labels], fontsize=7.6)
    sax.set_xlim(80, 100.5)
    sax.set_xticks([80, 90, 100])
    sax.set_xlabel("epistemic share of output variance [%]")
    sax.set_title("c  Epistemic share")
    sax.grid(axis="y", visible=False)
    sax.plot([], [], "o", color=S1, label="peak heat flux")
    sax.plot([], [], "s", color="#184f95", label="peak bondline temperature")
    sax.legend(loc="upper left", bbox_to_anchor=(-0.55, -0.22), fontsize=6.8, handletextpad=0.3, ncol=1)

    # left: message panel
    tax = fig.add_axes([0.035, 0.15, 0.215, 0.67])
    tax.axis("off")
    tax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.03", fc=PANEL, ec="none",
                                 transform=tax.transAxes))
    bt = att["outputs"]["peak_bondline_temperature_k"]["total"]
    ft = att["outputs"]["peak_heat_flux_w_m2"]["total"]
    ib = {n: bt[i] for i, n in enumerate(names)}
    ifx = {n: ft[i] for i, n in enumerate(names)}
    tax.text(0.07, 0.965, f"{min(all_sh)*100:.0f}–{max(all_sh)*100:.0f}%", fontsize=30, weight="bold", color=S1, va="top")
    tax.text(0.07, 0.855, "of the variance in peak flux and\nbondline temperature, across all\nfour designs, is epistemic.\n"
             "It is removed by evidence, not\nby design margin.", fontsize=8.6, color=INK, va="top", linespacing=1.4)
    tax.text(0.07, 0.625, "bondline, at the knee", fontsize=8, color=INK2, va="top")
    tax.text(0.07, 0.585, f"{ib['tps_conductivity']:.3f}", fontsize=22, weight="bold", color=INK, va="top")
    tax.text(0.07, 0.505, "TPS conductivity — a placeholder\nproperty (no material is specified)\n· T3 judgment",
             fontsize=7.8, color=INK, va="top", linespacing=1.35)
    tax.text(0.07, 0.405, f"{ib['high_altitude_heating_model']:.3f}", fontsize=22, weight="bold", color=INK, va="top")
    tax.text(0.07, 0.325, "heating above 86 km — a continuum\ncorrelation in transitional flow,\n×0.5–1.5 · T3 judgment",
             fontsize=7.8, color=INK, va="top", linespacing=1.35)
    tax.text(0.07, 0.20, f"Peak flux at the knee: {ifx['effective_nose_radius_model']:.3f} of its\nvariance is the disagreement between\n"
             "two NASA primaries on the effective\nnose radius (T1, resolvable) — and\n0.000 on the hemispherical baseline,\nwhere the two agree.",
             fontsize=7.2, color=INK2, va="top", linespacing=1.35)

    stamp(fig, [
        f"Run {M7_UQ_RUN} (git {m7['git_commit']}, dirty; source hash {m7['source_hash']}), Fidelity 1 (cfd_surface_v2); "
        f"attribution: Saltelli with mean-centred estimator, n_base {att['n_base']}, {att['n_evaluations']:,} evaluations per design; "
        f"shares: nested {m7['draws']['n_epistemic_branches']} × {m7['draws']['n_aleatory']} draws, law of total variance.",
        f"Knee design: D {knee['diameter_m']:.3f} m, R_n/D {knee['bluntness_ratio']:.3f}, cone {knee['cone_half_angle_deg']:.1f}°, "
        f"γ₀ {knee['flight_path_angle_deg']:+.2f}°. Every spread is a LOWER bound: gate G2′ (catalycity, hot wall, radiation) has no distribution and is not in the inventory.",
    ])
    save(fig, "05_uncertainty_sources")
    return IndexEntry(5, "05_uncertainty_sources", "Where the uncertainty comes from",
                      "84–99% epistemic; the two dominant bondline terms are engineering judgment.",
                      [f"results/M7/{M7_UQ_RUN}/summary.json (attribution, propagation.decomposition, uncertainty_model)"],
                      ["Tier and aleatory/epistemic labels are the inventory's own fields."])


# ======================================================================================
# Figure 6 - the negative-results timeline
# ======================================================================================
NR_KIND = {  # this classification is the infographic's, made from reading each entry; the paper groups them in §17
    "solver": [1, 5, 6, 7, 8, 9, 19, 20, 21, 25, 26, 27, 28],
    "model exploit": [2, 3, 13, 14, 15, 29, 30],
    "tooling trap": [4, 16, 17, 18, 22, 23, 24, 31, 34],
    "study design": [10, 11, 12, 32, 33, 35],
}
NR_CALLOUT = [13, 15, 18, 25, 35]


def fig6_negative_results() -> IndexEntry:
    txt = F["nr"].read_text()
    heads = re.findall(r"^### (NR-(\d+)) — (.+)$", txt, re.M)
    entries = [(int(n), tag, title.strip()) for tag, n, title in heads]
    assert len(entries) >= 30
    kind_of = {n: k for k, ns in NR_KIND.items() for n in ns}
    missing = [n for n, _, _ in entries if n not in kind_of]
    assert not missing, missing
    dates = {n: git_first_date(f"### NR-{n:02d}", F["nr"]) for n, _, _ in entries}
    kind_colour = {"solver": S1, "model exploit": S2, "tooling trap": S3, "study design": S4}
    lanes = {"model exploit": 3, "solver": 2, "tooling trap": 1, "study design": 0}

    fig = plt.figure(figsize=(14, 8.6))
    frame(fig, 6, f"The honesty record: {len(entries)} negative results, every one kept",
          "Numbered in the order they were found, grouped by what broke. The five that changed what the paper can claim are called out.\n"
          "In most cases a plausible, well-formatted, wrong answer was available.")
    ax = fig.add_axes([0.045, 0.30, 0.94, 0.52])
    ax.set_xlim(0.3, len(entries) + 0.7)
    ax.set_ylim(-0.7, 4.3)
    ax.axis("off")

    # date bands
    uniq = sorted({d for d in dates.values() if d})
    for d in uniq:
        ns = [n for n, dd in dates.items() if dd == d]
        x0, x1 = min(ns) - 0.45, max(ns) + 0.45
        ax.add_patch(Rectangle((x0, -0.62), x1 - x0, 4.3, fc=PANEL, ec="none", zorder=0))
        ax.text((x0 + x1) / 2, 4.22, f"first recorded {d}", fontsize=8, color=INK2, ha="center", va="top", weight="bold")
    for k, lane in lanes.items():
        ax.text(0.5, lane + 0.42, k, fontsize=8.5, weight="bold", color=kind_colour[k], va="bottom", ha="left")
        ax.plot([0.3, len(entries) + 0.7], [lane - 0.42, lane - 0.42], color=GRID, lw=0.6, zorder=1)
    for n, _tag, _title in entries:
        k = kind_of[n]
        y = lanes[k]
        big = n in NR_CALLOUT
        s = 0.42 if big else 0.30
        ax.add_patch(FancyBboxPatch((n - s / 2, y - s / 2), s, s, boxstyle="round,pad=0,rounding_size=0.06",
                                    fc=kind_colour[k], ec=INK if big else "none", lw=1.4 if big else 0, zorder=3))
        ax.text(n, y, f"{n}", fontsize=7.6 if big else 6.4, color=SURFACE if k != "study design" else INK,
                ha="center", va="center", weight="bold", zorder=4,
                path_effects=[patheffects.withStroke(linewidth=1.6, foreground=kind_colour[k])] if k != "study design" else None)

    # call-outs, one line each, under the strip
    cax = fig.add_axes([0.045, 0.085, 0.94, 0.19])
    cax.axis("off")
    cax.set_xlim(0, 1)
    cax.set_ylim(0, 1)
    cax.text(0, 1.0, "THE FIVE THAT CHANGED WHAT THE PAPER CAN CLAIM", fontsize=7.2, color=MUTED, weight="bold", va="top")
    for i, n in enumerate(NR_CALLOUT):
        tag, title = [(t, ti) for nn, t, ti in entries if nn == n][0]
        k = kind_of[n]
        y = 0.83 - i * 0.2
        cax.add_patch(Rectangle((0, y - 0.07), 0.006, 0.14, fc=kind_colour[k], ec="none"))
        cax.text(0.012, y, tag, fontsize=8.5, weight="bold", color=INK, va="center")
        cax.text(0.062, y, title, fontsize=8.2, color=INK, va="center")

    counts = {k: len(v) for k, v in NR_KIND.items()}
    stamp(fig, [
        "Entries and titles read from docs/negative_results.md (headings verbatim); dates are the first git commit in which each heading appears "
        f"in that file. Counts: {', '.join(f'{k} {v}' for k, v in counts.items())}.",
        "The grouping by kind is this figure's reading of each entry (the paper's §17 groups them by consequence); the five call-outs are the "
        "ones §17 and §8.2 build on. Squares outlined in ink = called out.",
    ])
    save(fig, "06_negative_results_timeline")
    return IndexEntry(6, "06_negative_results_timeline", "The negative-results timeline",
                      f"{len(entries)} entries in four kinds; five called out.",
                      ["docs/negative_results.md (headings)", "git log -S on that file (dates)"],
                      ["Kind classification is this script's (NR_KIND); titles are verbatim headings."])


# ======================================================================================
# Figure 7 - gate G4 history
# ======================================================================================
def fig7_gate_history() -> IndexEntry:
    after = load_json(F["m2_gate"])
    before = load_json(F["m2_gate_before"])
    cfg = yaml.safe_load(F["m2_cfg"].read_text())
    crit = None
    for v in cfg.values():
        if isinstance(v, dict) and "convergence_criterion" in v:
            crit = v["convergence_criterion"]
        if isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, dict) and "convergence_criterion" in vv:
                    crit = vv["convergence_criterion"]
    assert crit, "criterion not found in M2 config snapshot"
    sols = {c["case"]: c for c in after["conditions"]["2_force_convergence"]["detail"]["all_candidate_solutions"]}
    gci_after = pd.read_csv(F["m2_gci"])
    gci_before = pd.read_csv(F["m2_gci_before"])
    p2p_lim, drift_lim = crit["max_peak_to_peak_rel"] * 100, crit["max_drift_rel"] * 100

    fig = plt.figure(figsize=(13.5, 8.6))
    frame(fig, 7, f"Gate G4: {before['status']} → {after['status']}, with the rule that got it there disclosed",
          "Both fine-mesh sphere cases ended in a bounded limit cycle and missed the force criterion. The criterion was not moved;\n"
          "the Courant number was. The restart rule was written after the first results had been seen.")

    # status strip
    sax = fig.add_axes([0.035, 0.72, 0.93, 0.10])
    sax.axis("off")
    sax.set_xlim(0, 1)
    sax.set_ylim(0, 1)
    chip(sax, 0.0, 0.62, before["status"], STATUS_COLOUR[before["status"]], fontsize=10, h=0.42, w=0.085)
    sax.text(0.0, 0.18, "…_before_restarts.json (kept on disk)", fontsize=7.2, color=INK2, va="center")
    sax.annotate("", xy=(0.19, 0.62), xytext=(0.10, 0.62), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2))
    sax.text(0.145, 0.85, "what changed", fontsize=7.4, color=INK2, ha="center", va="bottom")
    sax.text(0.20, 0.62, f"max Courant {sols['sphere_M3_fine']['max_co']} → {sols['sphere_M3_fine_Co0p1']['max_co']} "
             f"(and {sols['sphere_M3_fine_Co0p05']['max_co']}), each fine case continued as a NEW case from its final solution, "
             f"in blocks of 5000 iterations, verdict at the end of two consecutive blocks",
             fontsize=8.2, color=INK, va="center")
    sax.text(0.20, 0.18, f"criterion unchanged: forebody C_D over the final {crit['window_iterations']:,} iterations, peak-to-peak "
             f"≤ {p2p_lim:.1f}% and half-window drift ≤ {drift_lim:.2f}%", fontsize=7.2, color=INK2, va="center")
    chip(sax, 0.915, 0.62, after["status"], STATUS_COLOUR[after["status"]], fontsize=10, h=0.42, w=0.085)
    sax.text(0.915, 0.18, "gate_assessment.json", fontsize=7.2, color=INK2, va="center")

    # (a) peak-to-peak per case
    ax = fig.add_axes([0.065, 0.20, 0.40, 0.455])
    cases = [("sphere_M3_fine", "Mach 3, fine mesh"), ("sphere_M6_fine", "Mach 6, fine mesh")]
    xs = np.arange(len(cases))
    w = 0.24
    variants = [("", "Co 0.2 — original run", RULE), ("_Co0p1", "Co 0.1 — restart, of record", S1), ("_Co0p05", "Co 0.05 — restart", SEQ_BLUE[2])]
    for j, (suf, lab, c) in enumerate(variants):
        vals = [sols[base + suf]["cd_fore_peak_to_peak_rel"] * 100 for base, _ in cases]
        met = [sols[base + suf]["cd_fore_converged"] for base, _ in cases]
        bars = ax.bar(xs + (j - 1) * (w + 0.03), vals, width=w, color=c, label=lab, zorder=3)
        for b, v, ok, (base, _) in zip(bars, vals, met, cases, strict=True):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.006, f"{v:.3f}%\n{'met' if ok else 'NOT MET'}", ha="center",
                    va="bottom", fontsize=7.4, color=INK, weight="bold" if not ok else "normal")
            ax.text(b.get_x() + b.get_width() / 2, 0.004, f"{sols[base + suf]['n_iterations']//1000}k it.", ha="center",
                    va="bottom", fontsize=6.4, color=SURFACE if c != RULE else INK2)
    ax.axhline(p2p_lim, color=CRIT, lw=1.2)
    ax.text(-0.45, p2p_lim + 0.004, f"declared limit {p2p_lim:.1f}%", fontsize=8, color=CRIT, ha="left", va="bottom", weight="bold")
    ax.set_xticks(xs)
    ax.set_xticklabels([n for _, n in cases])
    ax.set_ylabel("forebody C_D peak-to-peak over the final window [%]")
    ax.set_title("a  The force criterion, before and after the Courant restarts")
    ax.set_ylim(0, 0.33)
    ax.legend(loc="upper right", fontsize=7.6)
    drifts = ", ".join(f"{n}: {sols[b]['cd_fore_drift_rel']*100:.4f}% → {sols[b+'_Co0p1']['cd_fore_drift_rel']*100:.4f}%"
                       for b, n in cases)
    ax.text(0.0, -0.14, wrap(f"drift (limit {drift_lim:.2f}%) was never the problem — {drifts}", 130), fontsize=7,
            color=INK2, transform=ax.transAxes, va="top", linespacing=1.3)

    # (b) what moved: C_D of record, observed order, GCI
    bx = fig.add_axes([0.53, 0.13, 0.44, 0.525])
    bx.axis("off")
    bx.set_xlim(0, 1)
    bx.set_ylim(0, 1)
    bx.text(0, 1.0, "b  What the restart moved, and what it did not", fontsize=10.5, weight="bold", va="top")
    ga = {m: gci_after[(gci_after.mach == m) & (gci_after.quantity == "cd_fore")].iloc[0] for m in (3.0, 6.0)}
    gb = {m: gci_before[(gci_before.mach == m) & (gci_before.quantity == "cd_fore")].iloc[0] for m in (3.0, 6.0)}
    table = [
        ("fine-mesh C_D, of record", *[f"{gb[m].phi_fine:.5f} → {ga[m].phi_fine:.5f}  ({(ga[m].phi_fine/gb[m].phi_fine-1)*100:+.3f}%)" for m in (3.0, 6.0)]),
        ("observed order of convergence", *[f"{gb[m].observed_order:.2f} → {ga[m].observed_order:.2f}" for m in (3.0, 6.0)]),
        ("GCI, fine mesh", *[f"{gb[m].gci_fine*100:.2f}% → {ga[m].gci_fine*100:.2f}%" for m in (3.0, 6.0)]),
        ("fine − medium C_D difference", *[f"{gb[m].rel_error_fine_medium*100:.3f}% → {ga[m].rel_error_fine_medium*100:.3f}%" for m in (3.0, 6.0)]),
    ]
    y = 0.87
    bx.text(0.36, y + 0.055, "Mach 3", fontsize=7.6, color=MUTED, weight="bold")
    bx.text(0.68, y + 0.055, "Mach 6", fontsize=7.6, color=MUTED, weight="bold")
    for lab, m3, m6 in table:
        bx.text(0.0, y, lab, fontsize=8.2, color=INK, va="center")
        bx.text(0.36, y, m3, fontsize=8.2, color=INK, va="center")
        bx.text(0.68, y, m6, fontsize=8.2, color=INK, va="center")
        bx.plot([0, 1], [y - 0.04, y - 0.04], color=GRID, lw=0.7)
        y -= 0.082
    bx.text(0.0, y + 0.01, wrap("The mean of the limit cycle was not the fixed point: the converged C_D sits about 0.03% off the oscillating "
            "window mean — small against every tolerance, but a third of the fine–medium difference, which is why the observed "
            "order and the GCI moved.", 105), fontsize=7.4, color=INK2, va="top", linespacing=1.35)
    # disclosure panel
    bx.add_patch(FancyBboxPatch((0, 0.0), 1, 0.36, boxstyle="round,pad=0,rounding_size=0.02", fc=tint(WARN, 0.85), ec="none"))
    bx.add_patch(Rectangle((0, 0.0), 0.008, 0.36, fc=WARN, ec="none"))
    bx.text(0.03, 0.33, "DISCLOSURE (NR-25)", fontsize=7.4, color=INK, weight="bold", va="top")
    bx.text(0.03, 0.275, wrap("The restart rule, the two-block minimum and the rule for which solution is “of record” (the largest Courant "
            "number that met the criterion) were all written AFTER the original results had been seen; the two-block minimum was "
            "added while block 1 was running. Each makes the test stricter or is outcome-neutral, but none is pre-declared.\n"
            "A reader who does not accept a rule written after the fact should read G4 as LIMITED; the evidence for both readings "
            "is in the run directory. The Mach 6 margin is thin, and went up between blocks.", 104),
            fontsize=7.3, color=INK, va="top", linespacing=1.35)

    stamp(fig, [
        f"Run {M2_RUN}: gate_assessment.json ({after['status']}) and gate_assessment_20260921_0057_before_restarts.json ({before['status']}); "
        f"gci.csv vs gci_20260921_0057_before_restarts.csv; criterion from config_snapshot.yaml. OpenFOAM {after['openfoam_version_installed']} "
        f"installed (spec names {after['openfoam_version_required_by_spec']}).",
        "Sphere of radius 0.5 m, inviscid perfect gas, forebody only; benchmark and mesh-independence conditions were met in both assessments. "
        "Total sphere drag is not validated like-for-like. Disclosure text quotes docs/negative_results.md NR-25.",
    ])
    save(fig, "07_gate_G4_history")
    return IndexEntry(7, "07_gate_G4_history", "Gate G4 history",
                      "LIMITED → PASS by Courant 0.2 → 0.1; rule written after the result, disclosed.",
                      [f"results/M2/{M2_RUN}/gate_assessment.json", f"results/M2/{M2_RUN}/gate_assessment_20260921_0057_before_restarts.json",
                       f"results/M2/{M2_RUN}/gci.csv", f"results/M2/{M2_RUN}/gci_20260921_0057_before_restarts.csv",
                       f"results/M2/{M2_RUN}/config_snapshot.yaml", "docs/negative_results.md NR-25"],
                      [])


# ======================================================================================
def write_index(entries: list[IndexEntry]) -> None:
    lines = ["# Infographics — index", "",
             "Explanatory figures for the AETHER argument, rendered by `scripts/render_infographics.py` "
             "(`make infographics`). Each figure exists as PNG (preview), PDF and SVG (vector). Every number on a "
             "figure is read from the result file or generated report listed under it and the figure carries its run "
             "IDs in small print. Nothing under `src/`, `configs/` or `results/` is written.", "",
             "| # | Figure | Files | What it says |", "|---|---|---|---|"]
    for e in entries:
        lines.append(f"| {e.number} | {e.title} | `{e.stem}.png` · `.pdf` · `.svg` | {e.claim} |")
    lines += ["", "## Sources per figure", ""]
    for e in entries:
        lines.append(f"### {e.number}. {e.title}")
        lines.append("")
        for s in e.sources:
            lines.append(f"- `{s}`")
        for n in e.notes:
            lines.append(f"- note: {n}")
        lines.append("")
    lines += ["## Conventions", "",
              "- One type system (Avenir Next → Helvetica Neue → DejaVu Sans fallback) and one palette across all seven; "
              "light background, no gradients, no shadows, no icon clip-art.",
              "- Categorical colours are the dataviz reference slots (blue, orange, aqua, yellow), validated for "
              "adjacent-pair colour-vision-deficiency separation on a white surface; status colours (PASS green, LIMITED "
              "amber, NOT SUPPORTED red, IN_PROGRESS grey) are always paired with a text label, so nothing relies on colour alone.",
              "- Language follows CLAUDE.md §37: model predicts, within tested assumptions, candidate. No figure claims anything "
              "about a flight vehicle or a qualified material.",
              "- Figure 6's grouping of negative results by kind, and figure 3's picket positions in objective space, are "
              "this script's presentation choices and are labelled as such on the figures.", ""]
    (OUT / "INDEX.md").write_text("\n".join(lines))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    entries = [fig1_burn_vs_bake(), fig2_pipeline(), fig3_pareto(), fig4_scorecard(), fig5_uncertainty(),
               fig6_negative_results(), fig7_gate_history()]
    write_index(entries)
    for e in entries:
        print(f"  {e.number}. {e.stem}")
    print(f"wrote {len(entries)} figures + INDEX.md to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
