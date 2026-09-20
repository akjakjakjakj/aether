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


def save_figure(fig, out_dir: Path, stem: str, caption: str) -> Path:
    """Public entry point for the house figure standard (spec §34).

    Exists so that code outside this module - the M8 coupon analysis scripts, which are
    not part of the `aether` package - can produce figures that obey the same rules
    without reaching for a private name or re-implementing the caption placement.
    """
    return _save(fig, Path(out_dir), stem, caption)


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


def plot_tpi_figures(study, verdict, out_dir: Path) -> list[Path]:
    """Figures for the section-44 Thermal Penetration Index study.

    The job of these four is to let a reader reject the verdict. Two of them are built
    so that a *useful* TPI would look obviously different: a scatter that would show
    scatter, and a residual plot that would show structure.
    """
    from .studies.tpi_study import rank_regression_r2

    out_dir = Path(out_dir)
    written: list[Path] = []
    tag = "AETHER TPI study · Fidelity 0 · trajectory × geometry grid"
    tpi = study.reference.values_k_m_s
    bond = study.metrics["peak_bondline_temperature_k"]
    q_int = study.metrics["integrated_external_heat_j_m2"]
    diam = np.array([e.design_vector["diameter_m"] for e in study.sweep.evaluations])
    rho = study.correlations(study.reference)["peak_bondline_temperature_k"]

    # -- T1: is TPI just bondline temperature? ----------------------------------------
    fig, ax = plt.subplots(figsize=(5.8, 4.1))
    sc = ax.scatter(bond, tpi, c=diam, cmap="cividis", s=30, edgecolor="white",
                    linewidth=0.4)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("capsule diameter  $D$  [m]")
    cb.outline.set_edgecolor(MUTED)
    ax.set_xlabel("peak bondline temperature  $T_{bond,max}$  [K]")
    ax.set_ylabel("TPI  [K m s]")
    ax.set_title(f"TPI against the metric it would have to beat\n"
                 f"Spearman $\\rho$ = {rho:+.4f} over {len(tpi)} designs")
    written.append(_save(fig, out_dir, "TPI_vs_bondline",
                         f"{tag}. Reference configuration: {study.reference.label}. "
                         f"A metric carrying independent information would scatter; a "
                         f"tight monotone curve means it restates the x-axis."))

    # -- T2: where in the stack does the index come from? -----------------------------
    fig, (axp, axw) = plt.subplots(1, 2, figsize=(8.0, 3.8))
    order = np.argsort(tpi)
    picks = [(order[0], "lowest TPI", DEEP, "-"),
             (order[len(order) // 2], "median TPI", ACCENT, "--"),
             (order[-1], "highest TPI", HOT, ":")]
    for idx, lbl, colour, style in picks:
        ev = study.sweep.evaluations[idx]
        from .scoring import thermal_penetration_index
        out = thermal_penetration_index(ev.tps, study.reference.config)
        axp.plot(out.depth_m * 1e3, out.exceedance_profile_k_s, style, color=colour,
                 lw=1.6, label=f"{lbl}: {ev.design_id}")
    axp.set_xlabel("depth into TPS  [mm]")
    axp.set_ylabel("$\\int \\max(T - T_{ref},0)\\,dt$  [K s]")
    axp.set_title("Unweighted exceedance profile")
    axp.legend(fontsize=7)

    depths = study.reference.config.depth_limit_m or 0.015
    xs = np.linspace(0.0, depths, 200)
    from .scoring import TPIConfig, weight_profile
    for weighting, params, colour, style in (
        ("uniform", {}, INK, "-"),
        ("linear_depth", {}, DEEP, "--"),
        ("exponential_depth", {"decay": 4.0}, ACCENT, "-."),
        ("bondline_gaussian", {"sigma_m": 0.003}, HOT, ":"),
    ):
        cfg = TPIConfig(t_reference_k=study.reference.config.t_reference_k,
                        weighting=weighting, weight_params=params)
        w = weight_profile(xs, depths, cfg)
        w = w / (np.trapezoid(w, xs) / depths)
        axw.plot(xs * 1e3, w, style, color=colour, lw=1.5, label=weighting)
    axw.set_xlabel("depth into TPS  [mm]")
    axw.set_ylabel("normalised weight  $w(x)$  [-]")
    axw.set_title("Weighting families (depth-average = 1)")
    axw.legend(fontsize=7)
    fig.tight_layout()
    written.append(_save(fig, out_dir, "TPI_weighting_and_profile",
                         f"{tag}. Left: which depths actually contribute to the index. "
                         f"Right: the four candidate weightings, each normalised so a "
                         f"uniform field scores identically under all of them."))

    # -- T3: the redundancy residual --------------------------------------------------
    from scipy.stats import rankdata
    y = rankdata(tpi)
    design = np.column_stack([np.ones_like(y), rankdata(bond), rankdata(q_int)])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    predicted = design @ coef
    r2 = rank_regression_r2(tpi, [bond, q_int])

    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    ax.axhline(0.0, color=MUTED, lw=0.9)
    ax.scatter(predicted, y - predicted, s=30, color=DEEP, edgecolor="white",
               linewidth=0.4)
    ax.set_xlabel("TPI rank predicted from (peak bondline T, integrated heat)  [-]")
    ax.set_ylabel("residual: actual TPI rank − predicted rank  [-]")
    ax.set_title(f"What TPI knows that the existing metrics do not\n"
                 f"rank $R^2$ = {r2:.4f}  (max residual "
                 f"{np.max(np.abs(y - predicted)):.1f} of {len(y)} ranks)")
    written.append(_save(fig, out_dir, "TPI_rank_residual",
                         f"{tag}. Structure or spread here would be TPI's independent "
                         f"content. A flat band at zero means there is none."))

    # -- T4: does the verdict survive T_ref and weighting? ----------------------------
    #
    # Plotted as the UNEXPLAINED fraction 1 - R^2, on a log axis. Every configuration
    # lands above R^2 = 0.99, so a linear [0, 1] axis would show sixteen bars of
    # identical length and hide the one thing the figure is for: how the residual
    # information varies with T_ref and weighting. The log axis is a deliberate choice
    # to make small differences visible, and it is labelled as such rather than left for
    # the reader to infer.
    def _short(cfg) -> str:
        params = ", ".join(f"{k}={v:g}" for k, v in sorted(cfg.weight_params.items()))
        return (f"{cfg.weighting}{f' ({params})' if params else ''}  ·  "
                f"$T_{{ref}}$={cfg.t_reference_k:.0f} K")

    labels = [_short(v.config) for v in study.variants]
    r2s = np.array([study.redundancy_r2(v) for v in study.variants])
    rhos = np.array([study.correlations(v)["peak_bondline_temperature_k"]
                     for v in study.variants])
    unexplained = np.clip(1.0 - r2s, 1e-6, None)
    threshold = 1.0 - study.thresholds["redundancy_r2_threshold"]
    order = np.argsort(unexplained)

    fig, ax = plt.subplots(figsize=(7.6, max(3.4, 0.30 * len(labels) + 1.8)))
    ypos = np.arange(len(labels))
    ax.barh(ypos, unexplained[order], color=DEEP, height=0.6,
            label="$1-R^2$: TPI's ordering NOT carried by the existing metrics")
    ax.axvline(threshold, color=INK, ls="--", lw=1.1,
               label=f"discard threshold ($R^2$ = "
                     f"{study.thresholds['redundancy_r2_threshold']:.2f})")
    for i, j in enumerate(order):
        ax.annotate(f"$R^2$={r2s[j]:.4f}   $\\rho$={rhos[j]:+.4f}",
                    (unexplained[j], i), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=6.5, color=MUTED)
    ax.set_xscale("log")
    ax.set_yticks(ypos)
    ax.set_yticklabels([labels[j] for j in order], fontsize=7)
    ax.set_xlabel("unexplained fraction of TPI's design ordering,  $1-R^2$  [-]  "
                  "(log scale — lower is MORE redundant)")
    ax.set_xlim(min(unexplained.min(), threshold) / 3.0, threshold * 6.0)
    ax.set_title(f"Sensitivity of the verdict to $T_{{ref}}$ and weighting "
                 f"({verdict.decision}: {int(np.sum(unexplained <= threshold))} of "
                 f"{len(labels)} configurations redundant)")
    ax.legend(fontsize=7, loc="lower right", bbox_to_anchor=(1.0, 1.02), ncol=1,
              framealpha=0.0)
    fig.tight_layout()
    written.append(_save(fig, out_dir, "TPI_sensitivity",
                         f"{tag}. Every bar is one declared TPI configuration from "
                         f"configs/tpi_study.yaml. Bars LEFT of the dashed line are "
                         f"redundant by the pre-declared criterion. Note the axis: all "
                         f"sixteen sit above R^2 = 0.99, so the log scale is what makes "
                         f"their differences visible at all."))
    return written


def plot_joint_figures(sweep, comparison, out_dir: Path) -> list[Path]:
    """Figures for the (trajectory x geometry) sweep and the H1 optimiser comparison."""
    out_dir = Path(out_dir)
    written: list[Path] = []
    tag = "AETHER M1b · Fidelity 0 · trajectory × geometry grid"

    t_bond = sweep.field(lambda e: e.performance.peak_bondline_temperature_k)
    feas = sweep.feasible_mask
    G, D = np.meshgrid(sweep.gamma_deg, sweep.diameter_m, indexing="ij")

    # -- F6: where a design is allowed to exist --------------------------------------
    fig, ax = plt.subplots(figsize=(6.2, 4.1))
    cs = ax.contourf(G, D, t_bond, levels=14, cmap="magma_r")
    cb = fig.colorbar(cs, ax=ax)
    cb.set_label("peak bondline temperature  [K]")
    cb.outline.set_edgecolor(MUTED)

    # Wash OUT the infeasible area rather than hatching it, so the eye reads the
    # remaining clear region as "designs that are allowed to exist".
    ax.contourf(G, D, feas.astype(float), levels=[-0.5, 0.5], colors=["white"], alpha=0.68)
    ax.contour(G, D, feas.astype(float), levels=[0.5], colors="white", linewidths=2.0)

    ax.set_xlabel("entry flight-path angle  $\\gamma_0$  [deg]")
    ax.set_ylabel("capsule diameter  $D$  [m]")
    ax.set_title("Only two dimensions open a feasible region at all")
    ax.grid(False)
    # Breathing room so optimum markers on the domain edge are never clipped.
    ax.margins(x=0.04, y=0.05)

    if comparison.peak_only is not None:
        for e, colour, mark, lbl in (
            (comparison.peak_only, "#1b1b1e", "o", "peak-flux-only optimum"),
            (comparison.joint, HOT, "D", "joint O1 optimum"),
        ):
            ax.plot(e.design_vector["entry_flight_path_angle_deg"],
                    e.design_vector["diameter_m"], mark, color=colour, ms=9,
                    markeredgecolor="white", markeredgewidth=1.4, label=lbl,
                    clip_on=False, zorder=6)
        ax.legend(fontsize=8, loc="lower left", facecolor="white", framealpha=0.85,
                  frameon=True, edgecolor="none")
    written.append(_save(fig, out_dir, "M1b_feasible_region",
                         f"{tag}. The washed-out area fails the deceleration or bondline "
                         f"constraint; only the clear region inside the white boundary "
                         f"satisfies both. Both optima sit on the diameter bound - an open "
                         f"item, see PROJECT_STATUS.md."))

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


def plot_capsule_family(geometries, labels, out_dir: Path) -> list[Path]:
    """Phase F: outlines of several valid CapsuleGeometry instances, one figure.

    `geometries` and `labels` must be the same length (4-5 recommended - enough to
    show the design space's extremes without becoming illegible).
    """
    out_dir = Path(out_dir)
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    palette = [INK, HOT, DEEP, ACCENT, MUTED]

    for i, (geom, label) in enumerate(zip(geometries, labels, strict=True)):
        geom.validate()
        x, r = geom.profile(400)
        colour = palette[i % len(palette)]
        ax.plot(x, r, color=colour, lw=1.6, label=label)
        ax.plot(x, -r, color=colour, lw=1.6)  # mirror below the axis: full silhouette

    ax.axhline(0.0, color=GRID, lw=0.8, zorder=0)
    ax.set_xlabel("axial position from nose tip  $x$  [m]")
    ax.set_ylabel("radius  $r$  [m]")
    ax.set_title("Capsule geometry family across the parametric bounds")
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(fontsize=7.5, loc="center left", bbox_to_anchor=(1.02, 0.5),
              frameon=False)
    fig.tight_layout()
    return [_save(fig, out_dir, "M3_capsule_family",
                  "AETHER Phase F · sphere-cone-torus-cone-flat-base capsules, "
                  "each independently valid under configs/geometry_bounds.yaml.")]
