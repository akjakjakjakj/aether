"""Figure generation.

House rules (spec §34): every figure carries units on both axes, a caption, the run or
design IDs that produced it, a legible legend, and is written as BOTH a vector PDF (for
the paper) and a PNG preview. Colour never carries meaning without a legend.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Restrained, colour-blind-safe pairing. Two series that must be told apart use hue AND
# line style, never hue alone.
INK = "#1b1b1e"
MUTED = "#7a7d85"
GRID = "#dfe1e6"
HOT = "#c1442a"     # peak / surface quantities
DEEP = "#2f5d8f"    # bondline / in-depth quantities
ACCENT = "#c98a1c"

plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 200,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "legend.frameon": False,
    "figure.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _save(fig, out_dir: Path, stem: str, caption: str) -> Path:
    """Write a figure as vector PDF plus PNG preview, with its caption attached.

    The caption is placed BELOW the axes rather than inside them so it can never
    overlap an axis label - a figure whose provenance line covers its own x-axis is
    worse than no caption.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(bottom=fig.subplotpars.bottom + 0.06)
    fig.text(0.01, -0.04, caption, fontsize=6.5, color=MUTED, ha="left", va="top",
             wrap=True, transform=fig.transFigure)
    png = out_dir / f"{stem}.png"
    fig.savefig(png, bbox_inches="tight")
    fig.savefig(out_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    return png


def plot_m1_figures(study, out_dir: Path) -> list[Path]:
    """All Milestone-1 figures. Returns the paths written."""
    out_dir = Path(out_dir)
    written: list[Path] = []
    tag = "AETHER M1 · Fidelity 0 · flight-path-angle sweep"

    # -- F1: the anti-correlation, the headline figure --------------------------------
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.plot(study.gamma_deg, study.peak_flux_w_m2 / 1e4, "-o", ms=3, color=HOT,
            label="peak heat flux  $q''_{max}$")
    ax.set_xlabel("entry flight-path angle  $\\gamma_0$  [deg]")
    ax.set_ylabel("peak heat flux  [W cm$^{-2}$]", color=HOT)
    ax.tick_params(axis="y", labelcolor=HOT)

    ax2 = ax.twinx()
    ax2.plot(study.gamma_deg, study.peak_bondline_k, "--s", ms=3, color=DEEP,
             label="peak bondline temperature  $T_{bond,max}$")
    ax2.set_ylabel("peak bondline temperature  [K]", color=DEEP)
    ax2.tick_params(axis="y", labelcolor=DEEP)
    ax2.grid(False)

    i_q, i_t = int(np.argmin(study.peak_flux_w_m2)), int(np.argmin(study.peak_bondline_k))
    ax.axvline(study.gamma_deg[i_q], color=HOT, lw=0.8, alpha=0.45)
    ax2.axvline(study.gamma_deg[i_t], color=DEEP, lw=0.8, alpha=0.45)
    ax.annotate("min $q''_{max}$", (study.gamma_deg[i_q], ax.get_ylim()[1]),
                xytext=(0, -12), textcoords="offset points", color=HOT, fontsize=8, ha="center")
    ax2.annotate("min $T_{bond}$", (study.gamma_deg[i_t], ax2.get_ylim()[1]),
                 xytext=(0, -12), textcoords="offset points", color=DEEP, fontsize=8, ha="center")

    ax.set_title("The two safety metrics are minimised by different trajectories")
    lines = ax.get_lines()[:1] + ax2.get_lines()[:1]
    ax.legend(lines, [ln.get_label() for ln in lines], loc="upper center", fontsize=8)
    written.append(_save(fig, out_dir, "M1_anticorrelation",
                         f"{tag}. Shallower entry (right) lowers peak surface flux while "
                         f"raising bondline temperature."))

    # -- F2: trade space, peak flux against bondline ----------------------------------
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    sc = ax.scatter(study.peak_flux_w_m2 / 1e4, study.peak_bondline_k,
                    c=study.gamma_deg, cmap="cividis", s=26, edgecolor="white", linewidth=0.4)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("entry flight-path angle  [deg]")
    cb.outline.set_edgecolor(MUTED)
    ax.set_xlabel("peak heat flux  $q''_{max}$  [W cm$^{-2}$]")
    ax.set_ylabel("peak bondline temperature  $T_{bond,max}$  [K]")
    ax.set_title("Lower peak flux buys a hotter bondline")
    if study.counterexamples:
        p = study.counterexamples[0]
        ax.annotate("", xy=(p.peak_q_b_w_m2 / 1e4, p.t_bond_b_k),
                    xytext=(p.peak_q_a_w_m2 / 1e4, p.t_bond_a_k),
                    arrowprops=dict(arrowstyle="->", color=HOT, lw=1.4))
        ax.plot([p.peak_q_a_w_m2 / 1e4], [p.t_bond_a_k], "o", color=INK, ms=6, label="A")
        ax.plot([p.peak_q_b_w_m2 / 1e4], [p.t_bond_b_k], "o", color=HOT, ms=6, label="B")
        ax.legend(fontsize=8, title="strongest\ncounterexample", title_fontsize=7.5)
    written.append(_save(fig, out_dir, "M1_trade_space",
                         f"{tag}. Every point is one full coupled evaluation."))

    # -- F3: the mechanism, flux histories and bondline response ----------------------
    if study.counterexamples:
        p = study.counterexamples[0]
        ev = {e.design_id: e for e in study.evaluations}
        a, b = ev[p.design_a], ev[p.design_b]

        fig, (axq, axt) = plt.subplots(2, 1, figsize=(6.2, 5.4), sharex=True)
        for e, colour, style, lbl in ((a, INK, "-", "A"), (b, HOT, "--", "B")):
            g = e.design_vector["entry_flight_path_angle_deg"]
            axq.plot(e.trajectory.time_s, e.heat_flux_w_m2 / 1e4, style, color=colour, lw=1.5,
                     label=f"{lbl}: $\\gamma_0$={g:+.2f}°, $q''_{{max}}$="
                           f"{e.performance.peak_heat_flux_w_m2/1e4:.1f} W cm$^{{-2}}$")
            axt.plot(e.tps.time_s, e.tps.bondline_temperature_k, style, color=colour, lw=1.5,
                     label=f"{lbl}: $T_{{bond,max}}$="
                           f"{e.performance.peak_bondline_temperature_k:.0f} K")
        axq.set_ylabel("external heat flux  [W cm$^{-2}$]")
        axq.set_title("A shorter, hotter pulse is the safer one")
        axq.legend(fontsize=8)
        axt.set_ylabel("bondline temperature  [K]")
        axt.set_xlabel("time from entry interface  [s]")
        axt.legend(fontsize=8, loc="lower right")
        # Mark where aeroheating ends for EACH design - they differ, and the gap between
        # the two markers is itself part of the mechanism.
        for e, colour, style in ((a, INK, "-"), (b, HOT, "--")):
            axt.axvline(e.trajectory.time_s[-1], color=colour, ls=style, lw=0.8, alpha=0.5)
            axq.axvline(e.trajectory.time_s[-1], color=colour, ls=style, lw=0.8, alpha=0.5)
        axt.annotate("aeroheating ends;\nbondline keeps rising",
                     xy=(b.trajectory.time_s[-1], axt.get_ylim()[0]),
                     xytext=(14, 22), textcoords="offset points", fontsize=7.5, color=MUTED,
                     arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.7))
        written.append(_save(fig, out_dir, "M1_mechanism",
                             f"{tag}. Designs {p.design_a} and {p.design_b}. "
                             f"B has {p.peak_flux_reduction_pct:.1f}% lower peak flux "
                             f"and a {p.bondline_penalty_k:.0f} K hotter bondline."))

        # -- F4: through-thickness temperature field for both cases -------------------
        fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.6), sharey=True)
        vmax = max(a.tps.temperature_k.max(), b.tps.temperature_k.max())
        for ax, e, lbl in ((axes[0], a, "A"), (axes[1], b, "B")):
            im = ax.pcolormesh(e.tps.time_s, e.tps.depth_m * 1e3, e.tps.temperature_k.T,
                               cmap="inferno", vmin=300.0, vmax=vmax, shading="auto")
            ax.axhline(e.tps.depth_m[e.tps.bond_index] * 1e3, color="white", lw=1.0, ls=":")
            ax.invert_yaxis()
            ax.set_xlabel("time  [s]")
            ax.set_title(f"{lbl}: $\\gamma_0$="
                         f"{e.design_vector['entry_flight_path_angle_deg']:+.2f}°", fontsize=9)
            ax.grid(False)
        axes[0].set_ylabel("depth into TPS  [mm]")
        cb = fig.colorbar(im, ax=axes, pad=0.02)
        cb.set_label("temperature  [K]")
        cb.outline.set_edgecolor(MUTED)
        written.append(_save(fig, out_dir, "M1_temperature_field",
                             f"{tag}. Dotted line marks the bondline. The thermal front in B "
                             f"reaches it; in A it does not."))

    # -- F5: why integrated load, not peak, tracks the bondline -----------------------
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.scatter(study.integrated_q_j_m2 / 1e6, study.peak_bondline_k, s=24, color=DEEP,
               edgecolor="white", linewidth=0.4)
    ax.set_xlabel("integrated external heat load  $Q_{ext}$  [MJ m$^{-2}$]")
    ax.set_ylabel("peak bondline temperature  [K]")
    ax.set_title("Bondline temperature tracks the integral, not the peak")
    written.append(_save(fig, out_dir, "M1_integrated_vs_bondline",
                         f"{tag}. Compare with the scatter against peak flux in "
                         f"M1_trade_space."))
    return written


def plot_baseline(evaluation, out_dir: Path) -> list[Path]:
    """Four-panel summary of a single nominal entry."""
    out_dir = Path(out_dir)
    e = evaluation
    t, tr = e.trajectory.time_s, e.trajectory
    fig, axes = plt.subplots(2, 2, figsize=(8.0, 5.4))

    axes[0, 0].plot(t, tr.altitude_m / 1e3, color=INK, lw=1.5)
    axes[0, 0].set_ylabel("altitude  [km]")
    axes[0, 0].set_title("trajectory")

    axes[0, 1].plot(t, tr.velocity_m_s / 1e3, color=INK, lw=1.5)
    axes[0, 1].set_ylabel("velocity  [km s$^{-1}$]")
    ax2 = axes[0, 1].twinx()
    ax2.plot(t, tr.deceleration_g, color=ACCENT, lw=1.2, ls="--")
    ax2.set_ylabel("deceleration  [g]", color=ACCENT)
    ax2.tick_params(axis="y", labelcolor=ACCENT)
    ax2.grid(False)
    axes[0, 1].set_title("velocity and deceleration")

    axes[1, 0].plot(t, e.heat_flux_w_m2 / 1e4, color=HOT, lw=1.5)
    axes[1, 0].set_ylabel("$q''$  [W cm$^{-2}$]")
    axes[1, 0].set_xlabel("time  [s]")
    axes[1, 0].set_title("stagnation-point heat flux")

    axes[1, 1].plot(e.tps.time_s, e.tps.surface_temperature_k, color=HOT, lw=1.5,
                    label="surface")
    axes[1, 1].plot(e.tps.time_s, e.tps.bondline_temperature_k, color=DEEP, lw=1.5, ls="--",
                    label="bondline")
    axes[1, 1].set_ylabel("temperature  [K]")
    axes[1, 1].set_xlabel("time  [s]")
    axes[1, 1].set_title("TPS response")
    axes[1, 1].legend(fontsize=8)

    fig.tight_layout()
    p = e.performance
    return [_save(fig, out_dir, "baseline_summary",
                  f"AETHER baseline · design {e.design_id} · "
                  f"q''max={p.peak_heat_flux_w_m2/1e4:.1f} W cm-2, "
                  f"T_bond,max={p.peak_bondline_temperature_k:.0f} K, "
                  f"max {p.max_g:.1f} g, feasible={p.feasible}")]


def plot_joint_figures(sweep, comparison, out_dir: Path) -> list[Path]:
    """Figures for the (trajectory x geometry) sweep and the H1 optimiser comparison."""
    out_dir = Path(out_dir)
    written: list[Path] = []
    tag = "AETHER M1b · Fidelity 0 · trajectory × geometry grid"

    t_bond = sweep.field(lambda e: e.performance.peak_bondline_temperature_k)
    feas = sweep.feasible_mask
    G, D = np.meshgrid(sweep.gamma_deg, sweep.diameter_m, indexing="ij")

    # -- F6: where a design is allowed to exist --------------------------------------
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    cs = ax.contourf(G, D, t_bond, levels=14, cmap="magma_r")
    cb = fig.colorbar(cs, ax=ax)
    cb.set_label("peak bondline temperature  [K]")
    cb.outline.set_edgecolor(MUTED)
    ax.contourf(G, D, feas.astype(float), levels=[0.5, 1.5], colors="none",
                hatches=["////"], alpha=0.0)
    ax.contour(G, D, feas.astype(float), levels=[0.5], colors="white", linewidths=1.8)
    ax.set_xlabel("entry flight-path angle  $\\gamma_0$  [deg]")
    ax.set_ylabel("capsule diameter  $D$  [m]")
    ax.set_title("Feasible region (inside white contour) opens only in two dimensions")
    ax.grid(False)

    if comparison.peak_only is not None:
        for e, colour, mark, lbl in (
            (comparison.peak_only, "#1b1b1e", "o", "peak-flux-only optimum"),
            (comparison.joint, HOT, "D", "joint O1 optimum"),
        ):
            ax.plot(e.design_vector["entry_flight_path_angle_deg"],
                    e.design_vector["diameter_m"], mark, color=colour, ms=8,
                    markeredgecolor="white", markeredgewidth=1.2, label=lbl)
        ax.legend(fontsize=8, loc="lower left")
    written.append(_save(fig, out_dir, "M1b_feasible_region",
                         f"{tag}. Hatch-free area inside the white contour satisfies both the "
                         f"deceleration and bondline constraints."))

    # -- F7: the two optimisers disagree ---------------------------------------------
    if comparison.peak_only is not None:
        feas_evals = sweep.feasible_evaluations()
        qs = np.array([e.performance.peak_heat_flux_w_m2 for e in feas_evals]) / 1e4
        tb = np.array([e.performance.peak_bondline_temperature_k for e in feas_evals])
        fig, ax = plt.subplots(figsize=(5.6, 4.0))
        ax.scatter(qs, tb, s=28, color=MUTED, edgecolor="white", linewidth=0.4,
                   label=f"feasible designs (n={len(feas_evals)})")
        pq = np.array([e.performance.peak_heat_flux_w_m2 for e in comparison.pareto]) / 1e4
        pt = np.array([e.performance.peak_bondline_temperature_k for e in comparison.pareto])
        order = np.argsort(pq)
        ax.plot(pq[order], pt[order], "-", color=DEEP, lw=1.4, label="Pareto front")
        po, jo = comparison.peak_only.performance, comparison.joint.performance
        ax.plot(po.peak_heat_flux_w_m2 / 1e4, po.peak_bondline_temperature_k, "o",
                color=INK, ms=9, markeredgecolor="white", label="peak-flux-only optimum")
        ax.plot(jo.peak_heat_flux_w_m2 / 1e4, jo.peak_bondline_temperature_k, "D",
                color=HOT, ms=9, markeredgecolor="white", label="joint O1 optimum")
        ax.set_xlabel("peak heat flux  $q''_{max}$  [W cm$^{-2}$]")
        ax.set_ylabel("peak bondline temperature  $T_{bond,max}$  [K]")
        ax.set_title("What each objective actually selects")
        ax.legend(fontsize=8)
        written.append(_save(fig, out_dir, "M1b_optimiser_comparison",
                             f"{tag}. The peak-flux-only optimum sits "
                             f"{comparison.bondline_saving_k:.0f} K hotter at the bondline."))
    return written
