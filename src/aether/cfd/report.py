"""Build the M2 tables, figures and milestone report FROM RESULT FILES.

No number in the report is typed by hand: every value is formatted out of a DataFrame that
was itself read from ``results/M2/<run-id>/``. Re-running this stage on the same run
directory reproduces the report byte-for-byte apart from the generation timestamp.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

from . import plots
from . import validation as val
from .case import FlowCondition
from .postprocess import read_meridional_fields
from .runner import openfoam_available, run_foam


def _load_csv(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def _collect_single(run_dir: Path, prefix: str) -> pd.DataFrame | None:
    rows = []
    for f in sorted(run_dir.glob(f"{prefix}_*/case_result.json")):
        res = val.CaseResult(**json.loads(f.read_text()))
        flow = yaml.safe_load((f.parent / "dictionaries" / "aether_case.yaml").read_text())
        rows.append(val._row(res, float(flow["flow"]["mach"]), f.parent.name.split("_")[-1],
                             int(flow["mesh"]["refinement_factor"])))
    return pd.DataFrame(rows) if rows else None


def _fields_for(case_dir: Path, flow: FlowCondition) -> pd.DataFrame | None:
    """Export cell-centre fields for a figure; None if the heavy case data is gone."""
    if not case_dir.exists() or not openfoam_available():
        return None
    if not run_foam(case_dir, "writeCellCentres",
                    "postProcess -func writeCellCentres -latestTime").ok:
        return None
    try:
        return read_meridional_fields(case_dir, flow)
    except (FileNotFoundError, ValueError):
        return None


def run_dir_of(rel: str, repo_root: Path) -> Path:
    return repo_root / rel


def _clearance(case_results_dir: Path, standoff_m: float) -> str:
    """1 - standoff / (nose-to-inflow-boundary distance on the axis), from the sampled line."""
    f = case_results_dir / "stagnation_line.csv"
    if not f.exists() or pd.isna(standoff_m):
        return "n/a"
    x_up = abs(float(pd.read_csv(f)["x_m"].min()))
    return f"{1.0 - standoff_m / x_up:.2f}"


def pct(x: float, digits: int = 2) -> str:
    return "n/a" if pd.isna(x) else f"{100 * x:+.{digits}f}%"


def _md_table(df: pd.DataFrame) -> str:
    head = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.to_numpy()]
    return "\n".join([head, sep, *body])


def build_report(cfg: dict, run_id: str, run_dir: Path, generated_dir: Path,
                 repo_root: Path) -> dict:
    fig_dir = repo_root / "reports" / "figures"
    study = val.collect_mesh_study(cfg, run_dir)
    if study.empty:
        raise RuntimeError(f"no benchmark case results under {run_dir}")
    gci = val.gci_table(study)
    bench = val.benchmark_table(cfg, study, gci)
    demo = val.collect_pipeline_demo(cfg, run_dir)
    neg = _collect_single(run_dir, "spherefullbody")
    candidates = val.collect_level_candidates(cfg, run_dir)
    gate = val.assess_gate(cfg, study, gci, bench, demo, candidates)
    cycles = val.limit_cycle_table(cfg, run_dir)
    originals = candidates[~candidates["is_restart"]]
    gci_orig = val.gci_table(originals)
    meta = yaml.safe_load((run_dir / "config_snapshot.yaml").read_text())["_meta"]
    val.write_tables(run_dir, mesh_study=study, gci=gci, benchmark_comparison=bench,
                     gate_assessment=gate, level_candidates=candidates,
                     limit_cycle=cycles, gci_original_fine_cases=gci_orig,
                     **({"pipeline_demo": demo} if demo is not None else {}),
                     **({"negative_cases": neg} if neg is not None else {}))

    figs = [plots.plot_force_histories(study, run_dir, cfg, run_id, fig_dir, candidates),
            plots.plot_residuals(originals, run_dir, run_id, fig_dir),
            plots.plot_benchmark(study, run_dir, cfg, run_id, fig_dir)]
    if len(gci):
        figs.append(plots.plot_mesh_convergence(study, gci, run_id, fig_dir))
    diags = []
    for f in sorted(run_dir.glob("*_cyclediag/limit_cycle_summary.json")):
        summ = json.loads(f.read_text())
        row = candidates[candidates["case"] == summ["source_case"]]
        if len(row):
            diags.append((summ["source_case"], float(row["mach"].iloc[0]), summ,
                          pd.read_parquet(f.parent / "limit_cycle_cells.parquet"),
                          pd.read_csv(f.parent / "force_history_every_iteration.csv")))
    if diags:
        figs.append(plots.plot_limit_cycle(diags, run_id, fig_dir))

    ok = study[study["status"] == "OK"]
    radius = float(cfg["benchmark"]["radius_m"])
    sphere = val.sphere_outline(radius)
    for _, c in ok[ok["level"] == "fine"].iterrows():
        fields = _fields_for(generated_dir / c["case"], val._flow(cfg, c["mach"]))
        if fields is not None:
            fields.to_parquet(run_dir / c["case"] / "fields.parquet")
            figs.append(plots.plot_flow_field(
                fields, (sphere.x_m, sphere.r_m), float(c["mach"]), radius,
                f"sphere forebody, $M_\\infty$ = {c['mach']:g}, fine mesh",
                f"M2_flowfield_sphere_M{c['mach']:g}".replace(".", "p"),
                f"AETHER M2 · run {run_id} · case {c['case']}. Density from the Euler "
                f"solution. Dashed: Billig's correlation for the shock SHAPE, which is an "
                f"independent empirical curve, not a fit to this solution.", fig_dir))
    if demo is not None and demo["status"].iloc[-1] == "OK":
        d = demo.iloc[-1]
        body = pd.read_csv(run_dir / d["case"] / "body_pressure.csv")
        figs.append(plots.plot_demo_pressure(
            body, f"pipeline demonstration body, $M_\\infty$ = {d['mach']:g}",
            "M2_demo_capsule_pressure",
            f"AETHER M2 · run {run_id} · case {d['case']}. Generic blunted cone defined in "
            f"configs/cfd_validation.yaml; NOT a flown vehicle and NOT a validated result - "
            f"it shows the pipeline accepts an arbitrary (x, r) outline.", fig_dir))
        o = val.demo_outline(cfg)
        fields = _fields_for(generated_dir / d["case"], val._flow(cfg, d["mach"]))
        if fields is not None:
            figs.append(plots.plot_flow_field(
                fields, (o.x_m, o.r_m), float(d["mach"]), None,
                f"pipeline demonstration body, $M_\\infty$ = {d['mach']:g}",
                "M2_flowfield_demo_capsule",
                f"AETHER M2 · run {run_id} · case {d['case']}. Density, Euler, perfect gas. "
                f"Demonstration only.", fig_dir))

    text = _render(cfg, run_id, meta, study, gci, bench, demo, neg, gate, figs, repo_root,
                   candidates, cycles, gci_orig, [d[2] for d in diags])
    out = repo_root / "reports" / "milestones" / "M2_cfd_validation.md"
    out.write_text(text)
    return gate


BILLIG_EXPONENT_USED, BILLIG_EXPONENT_ALSO_PRINTED = 3.24, 3.2


def _billig_alt(mach: float) -> float:
    """Billig's stand-off with the exponent one secondary source prints (3.2, not 3.24)."""
    return 0.143 * math.exp(BILLIG_EXPONENT_ALSO_PRINTED / mach**2)


def _outcome_paragraph(cfg, gate, candidates, study, gci, bench) -> str:
    """First paragraph of the report: the outcome and its reason, from the gate file."""
    crit = cfg["convergence_criterion"]
    unmet = [k for k, c in gate["conditions"].items() if not c["met"]]
    orig_miss = candidates[~candidates["is_restart"] & (candidates["status"] == "OK")
                           & ~candidates["cd_fore_converged"].astype(bool)]
    rec_restart = study[study["is_restart"].astype(bool)]
    out = [f"**Outcome: gate G4 is {gate['status']}.** "]
    if gate["status"] == "PASS":
        out.append("All four spec §17 conditions are met by the rules declared in the config. ")
    else:
        out.append("Not met: " + ", ".join(f"`{k}`" for k in unmet) + ". `LIMITED` is not "
                   "`PASS` (spec §30) and nothing below should be read as if it were. ")
    if len(orig_miss):
        out.append(
            f"**{len(orig_miss)} original case(s) did NOT meet the declared force criterion** "
            f"(peak-to-peak ≤ {100 * crit['max_peak_to_peak_rel']:g}%, drift ≤ "
            f"{100 * crit['max_drift_rel']:g}% over {crit['window_iterations']} iterations): "
            + "; ".join(f"`{c.case}` ended in a bounded limit cycle, peak-to-peak "
                        f"{100 * c.cd_fore_peak_to_peak_rel:.3f}%, drift "
                        f"{100 * c.cd_fore_drift_rel:.4f}%, after {int(c.n_iterations):,} "
                        f"iterations" for c in orig_miss.itertuples()) + ". ")
        if len(rec_restart):
            out.append(
                "The criterion was not changed. Following spec §36 (check the Courant number "
                "before anything else) each was continued from its final solution as a new, "
                "separately named case at a lower Courant limit; the solution of record at "
                "that level is " + "; ".join(
                    f"`{c.case}` (max Co {c.max_co:g}, peak-to-peak "
                    f"{100 * c.cd_fore_peak_to_peak_rel:.3f}%, drift "
                    f"{100 * c.cd_fore_drift_rel:.4f}%)" for c in rec_restart.itertuples())
                + ". The original cases are kept, tabulated and plotted below. ")
        else:
            out.append("No lower-Courant restart met the criterion either; the original "
                       "cases remain the solutions of record and are marked as not "
                       "converged everywhere they appear. ")
    cd = gci[gci["quantity"] == "cd_fore"]
    p0 = gci[(gci["quantity"] == "p_stag_over_p_inf") & (gci["convergence_type"] != "monotone")]
    if len(cd):
        out.append("Four things a reader should know before trusting any number here: (1) the "
                   "observed order of convergence of forebody C_D is "
                   + " and ".join(f"{r.observed_order:.2f} at Mach {r.mach:g}"
                                  for r in cd.itertuples())
                   + ", against a formal order of 2 away from the shock and 1 at it; ")
        out.append("(2) " + ("; ".join(
            f"the stagnation pressure at Mach {r.mach:g} converges *{r.convergence_type}* "
            f"with mesh ({r.phi_coarse:.3f} / {r.phi_medium:.3f} / {r.phi_fine:.3f}), so its "
            f"Richardson value is not reliable (single final-iteration snapshots; which Mach "
            f"number shows this depends on the snapshot - see Condition 1)"
            for r in p0.itertuples())
            if len(p0) else "stagnation pressure converges monotonically at every Mach") + "; ")
        out.append(f"(3) Billig's stand-off correlation is used with the exponent "
                   f"{BILLIG_EXPONENT_USED}, but one of the three secondary sources prints "
                   f"{BILLIG_EXPONENT_ALSO_PRINTED} and the original paper could not be "
                   f"opened; (4) sphere drag is compared with a **forebody pressure-drag "
                   f"expression**, not like-for-like with measured total drag, because this "
                   f"CFD computes no base pressure.\n")
    return "".join(out)


def _downstream_facts(gate, gci, repo_root: Path) -> str:
    """Sizes of the uncertainty terms, side by side. Facts for whoever decides what the gate
    status permits; this report does not make that decision."""
    cd = gci[gci["quantity"] == "cd_fore"] if len(gci) else gci
    if cd.empty or "band_coarse_rel" not in cd:
        return ""
    surf_cfg = yaml.safe_load((repo_root / "configs" / "aero_surface.yaml").read_text())

    def find(d, key):
        if isinstance(d, dict):
            if key in d:
                return d[key]
            for v in d.values():
                hit = find(v, key)
                if hit is not None:
                    return hit
        return None

    mf = find(surf_cfg, "model_form_rel_halfband")
    L = ["## Sizes of the uncertainty terms (facts for the downstream decision)\n",
         f"Gate status in `gate_assessment.json`: **{gate['status']}**. What that status "
         f"permits downstream is not decided here. The terms, largest value over the "
         f"benchmark Mach numbers, relative to C_D,fore:\n"]
    rows = [("discretisation band, COARSE mesh (what the M3 surface is built on; "
             "1.25 × Richardson error)", cd["band_coarse_rel"].max()),
            ("… same, with the fine value at its cycle extremes",
             cd["band_coarse_at_cycle_extremes_max"].max()),
            ("GCI, medium mesh", cd["gci_medium"].max()),
            ("GCI, fine mesh", cd["gci_fine"].max()),
            ("iterative band (± half peak-to-peak), coarse",
             cd["limit_cycle_half_p2p_rel_coarse"].max()),
            ("iterative band, medium", cd["limit_cycle_half_p2p_rel_medium"].max()),
            ("iterative band, fine (solution of record)",
             cd["limit_cycle_half_p2p_rel_fine"].max())]
    t = pd.DataFrame({"term": [a for a, _ in rows],
                      "size": [f"{100 * b:.3f}%" for _, b in rows]})
    if mf is not None:
        t["as a fraction of the declared perfect-gas model-form half-band"] = [
            f"{b / float(mf):.3f}" for _, b in rows]
    L.append(_md_table(t))
    if mf is not None:
        L.append(f"\nThe declared perfect-gas model-form half-band is ±{100 * float(mf):g}% "
                 f"(`configs/aero_surface.yaml`, A-CFD-12) - a project declaration that is "
                 f"**not validated** by this milestone.")
    L.append("\nThe sphere's bands are transferred to capsules by assumption (A-CFD-9). The "
             "M3 design-point runner accepts a case only if it individually met the same "
             "force criterion, so no limit-cycling case is in the M3 surface (NR-21).\n")
    return "\n".join(L)


def _limit_cycle_section(cfg, candidates, cycles, diag_summaries, rel) -> str:
    miss = candidates[~candidates["is_restart"] & (candidates["status"] == "OK")
                      & ~candidates["cd_fore_converged"].astype(bool)]
    if miss.empty:
        return ""
    rc = cfg.get("courant_restarts", {})
    L = ["### The fine-mesh limit cycle, and what was done about it (NR-25)\n"]
    L.append(
        f"The original fine cases ran their planned iterations plus all "
        f"{cfg['solver']['max_extensions']} extensions and still missed the peak-to-peak "
        f"limit. Their drift is one to two orders below its limit, so this is **a bounded "
        f"oscillation about a fixed mean, not slow convergence** - waiting longer could not "
        f"cure it. The criterion was left alone. Spec §36 puts the Courant number ahead of "
        f"solver settings and physics, and NR-07 had already shown a C_D limit cycle on the "
        f"coarse mesh that max Co 0.5 → 0.2 removed; so the same lever was pulled one level "
        f"finer. Each fine case was continued from its final solution as a new case at max "
        f"Co {' and '.join(f'{c:g}' for c in rc.get('max_co', []))}, in blocks of "
        f"{rc.get('block_iterations')} iterations, for at least {rc.get('min_blocks', 1)} and "
        f"at most {rc.get('max_blocks')} blocks, the verdict being the one at the end of the "
        f"last block. This restart rule was written AFTER the original fine results had been "
        f"seen; that is disclosed here and in the config.\n")
    t = pd.DataFrame({
        "case": cycles["case"], "max Co": cycles["max_co"].map("{:g}".format),
        "criterion met": cycles["criterion_met"].map(lambda b: "yes" if b else "**NO**"),
        "window mean C_D": cycles["mean"].map("{:.6f}".format),
        "peak-to-peak": cycles["peak_to_peak_rel"].map(lambda v: f"{100 * v:.4f}%"),
        "± half p-p": cycles["half_peak_to_peak_rel"].map(lambda v: f"{100 * v:.4f}%"),
        "rms": cycles["rms_rel"].map(lambda v: f"{100 * v:.4f}%"),
        "dominant period [iterations]": cycles["dominant_period_iterations"].map(
            "{:.0f}".format),
        "period [cell-transit times]": cycles["dominant_period_cell_transit_times"].map(
            "{:.1f}".format),
        "share of spectral power": cycles["dominant_period_power_fraction"].map(
            "{:.2f}".format),
    })
    L.append(_md_table(t))
    L.append(
        "\nForce sampled every 5 iterations over the judged window; a period under 20 "
        "iterations would not be resolved. Under local time stepping each cell advances by "
        "max Co of its own transit time per iteration, so there is no global physical time "
        "and no meaningful 'flow-through time'; *cell-transit times* = period × max Co is "
        "the natural unit. A 'dominant period' with a small share of the spectral power "
        "means there is no clean cycle left, only broadband noise inside the band.\n")
    for c in miss.itertuples():
        same = candidates[(candidates["mach"] == c.mach) & (candidates["level"] == c.level)
                          & candidates["is_restart"] & (candidates["status"] == "OK")]
        for q in same.itertuples():
            L.append(f"- Mach {c.mach:g}: max Co {c.max_co:g} → {q.max_co:g} changed the "
                     f"peak-to-peak from {100 * c.cd_fore_peak_to_peak_rel:.3f}% to "
                     f"{100 * q.cd_fore_peak_to_peak_rel:.3f}% and moved the window-mean C_D "
                     f"by {pct(q.cd_fore / c.cd_fore - 1.0, 4)} "
                     f"({c.cd_fore:.6f} → {q.cd_fore:.6f}); criterion "
                     f"{'met' if bool(q.cd_fore_converged) else '**not met**'}.")
    L.append("")
    for d in diag_summaries:
        fc = d["force_cycle_every_iteration"]
        L.append(
            f"**Where it lives, `{d['source_case']}`** (field written every "
            f"{d['snapshot_interval_iterations']} iterations for {d['n_snapshots']} snapshots, "
            f"force every iteration): C_D peak-to-peak {100 * fc['peak_to_peak_rel']:.3f}%, "
            f"period {fc['dominant_period_iterations']:.0f} iterations = "
            f"{fc['dominant_period_cell_transit_times']:.1f} cell-transit times. The pressure "
            f"fluctuation is **not** confined to the shock: 90% of its variance is spread over "
            f"{100 * d['fraction_of_cells_holding_90pct_of_variance']:.0f}% of the cells, all at "
            f"or behind the shock (mean p/p∞ from "
            f"{d['top90_mean_p_over_p_inf_range'][0]:.1f} to "
            f"{d['top90_mean_p_over_p_inf_range'][1]:.1f}), from "
            f"{d['top90_polar_angle_from_axis_deg_range'][0]:.0f}° to the outflow plane. The "
            f"largest single-cell swing, {d['max_cell_p_peak_to_peak_over_p_inf']:.2f} p∞ "
            f"peak-to-peak, is at x = {d['max_cell_location_x_m']:.3f} m, r = "
            f"{d['max_cell_location_r_m']:.3f} m.")
    if diag_summaries:
        L.append(
            "\nRead with the map below: the stagnation region is the quietest part of the "
            "shock layer and the fluctuation grows along the body towards the supersonic "
            "outflow, in ray-like bands that start at the captured shock. That pattern is what "
            "pressure disturbances shed by a captured shock that jitters between neighbouring "
            "cells, and then carried downstream, would look like; it is *not* what a badly "
            "posed outflow boundary or a stagnation-point instability would look like. This "
            "is an interpretation of the map, not something that was separately tested.\n")
        L.append("![limit cycle](../figures/M2_limit_cycle.png)\n")
    L.append(f"Evidence: `{rel}/level_candidates.csv`, `limit_cycle.csv`, "
             f"`<case>_Co*/restart_blocks.json`, `<case>_cyclediag/`.\n")
    return "\n".join(L)


def _render(cfg, run_id, meta, study, gci, bench, demo, neg, gate, figs, repo_root,
            candidates, cycles, gci_orig, diag_summaries) -> str:
    crit, mi = cfg["convergence_criterion"], cfg["mesh_independence"]
    rel = f"results/M2/{run_id}"
    L: list[str] = []
    add = L.append
    add("# M2 — OpenFOAM CFD validation (gate G4)\n")
    add(f"> **Generated file.** Written by `src/aether/cfd/report.py` from `{rel}/`. Every "
        f"number below is read from a result file; edit the code or the config, never this "
        f"file.\n")
    add(f"- Run ID: `{run_id}` · config hash `{meta['config_hash']}` · git "
        f"`{meta['git_commit']}`{' (**dirty working tree**)' if meta['git_dirty'] else ''}")
    add(f"- Generated: {datetime.now(UTC).isoformat(timespec='seconds')}")
    add(f"- OpenFOAM installed: **{gate['openfoam_version_installed']}** · specification "
        f"asks for {gate['openfoam_version_required_by_spec']} — see *Deviations*.")
    add(f"- Config: `configs/cfd_validation.yaml` (snapshot in `{rel}/config_snapshot.yaml`)\n")

    add(_outcome_paragraph(cfg, gate, candidates, study, gci, bench))
    add(f"## Gate G4 status: **{gate['status']}**\n")
    names = {"1_mesh_independence": "1. Mesh independence completed",
             "2_force_convergence": "2. Force convergence demonstrated",
             "3_published_benchmark": "3. Published blunt-body case compared",
             "4_model_limitations_documented": "4. Model-form limitations documented"}
    add(_md_table(pd.DataFrame(
        [{"spec §17 condition": names[k], "met": "yes" if c["met"] else "**no**"}
         for k, c in gate["conditions"].items()])))
    add("\nThe convergence criterion, the mesh-independence rule and the benchmark tolerances "
        "were written into the config before the validation cases were run, and none was "
        "changed afterwards. **Two things were added after the original results had been "
        "seen**, and the status above depends on both: the lower-Courant restart of the fine "
        "cases (`courant_restarts` in the config) and the rule for which solution is 'of "
        "record' at a level. Both are described under Condition 2 and in NR-25; a reader who "
        "does not accept them should read the gate as it stood before them, **LIMITED** "
        f"(`{rel}/gate_assessment_20260921_0057_before_restarts.json`). `PASS` requires all "
        "four conditions.\n")

    # -- what was run -----------------------------------------------------------------
    s = cfg["solver"]
    add("## What was computed\n")
    add(f"A sphere of radius {cfg['benchmark']['radius_m']} m in a uniform supersonic stream "
        f"of calorically perfect air (γ = {cfg['gas']['gamma']}), at Mach "
        f"{' and '.join(f'{m:g}' for m in cfg['benchmark']['mach_numbers'])}. Solver "
        f"`{s['application']}`, axisymmetric **Euler** equations on a "
        f"{cfg['mesh']['wedge_angle_deg']:g}° wedge, {s['flux_scheme']} flux with "
        f"{s['limiter']} reconstruction, local time stepping at max Courant number "
        f"{s['max_co']} (lower for the fine-level restarts: see Condition 2). "
        f"The domain covers the **{cfg['mesh']['extent']}** only (nose to the "
        f"maximum-radius station) and ends in an outflow plane; the smallest Mach number "
        f"found anywhere on that plane is reported per case, because the zero-gradient "
        f"outflow condition is only well posed if it exceeds 1.\n")
    add("Why inviscid, why forebody-only, and what that rules out: "
        "`docs/validation/M2_model_form_limits.md` and ASSUMPTIONS A-CFD-1…6.\n")

    cols = {"case": "case", "n_cells": "cells", "n_iterations": "iterations",
            "n_extensions": "extensions",
            "status": "status", "max_non_orthogonality_deg": "max non-orth [deg]",
            "max_skewness": "max skew", "outlet_min_mach": "min outlet Mach",
            "solver_wall_time_s": "solver wall time [s]"}
    t = study[list(cols)].rename(columns=cols).copy()
    t["shock clearance"] = [_clearance(run_dir_of(rel, repo_root) / c, so) for c, so in
                            zip(study["case"], study["standoff_m"], strict=True)]
    for c_ in ("max non-orth [deg]", "max skew", "min outlet Mach"):
        t[c_] = t[c_].map(lambda v: "n/a" if pd.isna(v) else f"{v:.2f}")
    t["solver wall time [s]"] = t["solver wall time [s]"].map(lambda v: f"{v:.0f}")
    t["iterations"] = t["iterations"].map(lambda v: "n/a" if pd.isna(v) else f"{int(v):,}")
    t["cells"] = t["cells"].map(lambda v: f"{int(v):,}")
    t["extensions"] = t["extensions"].map(lambda v: "n/a" if pd.isna(v) else f"{int(v)}")
    add(_md_table(t))
    add("\n*Shock clearance* is 1 − Δ / (distance from the nose to the inflow boundary on the "
        "axis): how much room is left between the captured shock and the fixed-value inflow "
        "boundary. Near zero would mean the shock is sitting on the boundary and the case is "
        "invalid.")
    add("\n*Extensions* counts how many times a case had to be continued past its planned "
        "iteration count before the force criterion was met (run-until-converged, NR-09).")
    add(f"\nWall times are single runs on this machine with {s['n_ranks']} MPI rank(s), with "
        f"other solver processes running beside them, so they are upper-ish bounds rather "
        f"than benchmarks (REPRODUCIBILITY.md). A restart's wall time covers the restart "
        f"only; the original fine cases' wall times are in the Condition 2 table.\n")

    # -- condition 2 ------------------------------------------------------------------
    add("## Condition 2 — force convergence\n")
    add(f"**Criterion (declared before the runs).** Over the final "
        f"{crit['window_iterations']} iterations the forebody drag coefficient must have "
        f"peak-to-peak variation ≤ {100 * crit['max_peak_to_peak_rel']:g}% of its mean **and** "
        f"a drift between the two halves of that window ≤ {100 * crit['max_drift_rel']:g}% "
        f"of its mean. The reported C_D is the mean over that window.\n")
    ok = study[study["status"] == "OK"]
    allc = candidates[candidates["status"] == "OK"]
    record = set(study["case"])
    t = pd.DataFrame({
        "case": allc["case"], "max Co": allc["max_co"].map("{:g}".format),
        "iterations": allc["n_iterations"].map(lambda v: f"{int(v):,}"),
        "C_D forebody": allc["cd_fore"].map("{:.5f}".format),
        "peak-to-peak": allc["cd_fore_peak_to_peak_rel"].map(lambda v: pct(v, 4).lstrip("+")),
        "drift": allc["cd_fore_drift_rel"].map(lambda v: pct(v, 4).lstrip("+")),
        "residual drop": (allc["final_mean_abs_drho_dtau"]
                          / allc["initial_mean_abs_drho_dtau"]).map("{:.2e}".format),
        "solver wall time [s]": allc["solver_wall_time_s"].map("{:.0f}".format),
        "criterion met": allc["cd_fore_converged"].map(lambda b: "yes" if b else "**NO**"),
        "solution of record": allc["case"].map(lambda c: "yes" if c in record else "no"),
    })
    add(_md_table(t))
    add("\nEvery solution that exists is listed, not only the ones used. *Solution of "
        "record* (rule fixed in `validation.collect_mesh_study`, the same for every level): "
        "the first of [original case, then restarts by descending Courant number] that met "
        "the criterion; if none did, the original. For a restart, *iterations* is the "
        "iteration count at its end including the source case's, and its *residual drop* is "
        "relative to the first residual of the restart, not of the original run.\n")
    add("\n*Residual drop* is the final volume-mean |∂ρ/∂τ| over its first recorded value. "
        "It is reported because the spec asks for residuals, and it is **not** part of the "
        "criterion: with a TVD limiter the density residual of this solver stalls once the "
        "captured shock starts flickering between neighbouring cells, while the integrated "
        "force has long since stopped moving. A reader who wants machine-zero residuals will "
        "not find them here.\n")
    add("![force convergence](../figures/M2_force_convergence.png)\n")
    add("![residuals](../figures/M2_residuals.png)\n")
    add(_limit_cycle_section(cfg, candidates, cycles, diag_summaries, rel))

    # -- condition 1 ------------------------------------------------------------------
    add("## Condition 1 — mesh independence\n")
    add(f"Three geometrically similar meshes, refinement factors "
        f"{cfg['mesh']['refinement_factors']} in both directions (constant ratio r = 2), "
        f"same block layout and grading. Richardson extrapolation and GCI follow Celik et al. "
        f"(2008) with safety factor 1.25. **Rule:** forebody C_D must converge monotonically "
        f"with GCI_fine ≤ {100 * mi['max_gci_fine_cd_rel']:g}% and a fine–medium change ≤ "
        f"{100 * mi['max_fine_medium_change_cd_rel']:g}%. The stand-off distance and "
        f"stagnation pressure are reported with their GCI but are judged against the "
        f"references (condition 3), not against this rule.\n")
    if len(gci):
        label = {"cd_fore": "C_D forebody", "standoff_over_max_radius": "Δ/R",
                 "p_stag_over_p_inf": "p0/p∞"}
        t = pd.DataFrame({
            "Mach": gci["mach"].map("{:g}".format),
            "quantity": gci["quantity"].map(label),
            "coarse": gci["phi_coarse"].map("{:.5f}".format),
            "medium": gci["phi_medium"].map("{:.5f}".format),
            "fine": gci["phi_fine"].map("{:.5f}".format),
            "behaviour": gci["convergence_type"],
            "observed order p": gci["observed_order"].map(
                lambda v: "n/a" if pd.isna(v) else f"{v:.2f}"),
            "Richardson": gci["phi_extrapolated"].map(
                lambda v: "n/a" if pd.isna(v) else f"{v:.5f}"),
            "fine–medium": gci["rel_error_fine_medium"].map(lambda v: pct(v, 3).lstrip("+")),
            "GCI_fine": gci["gci_fine"].map(lambda v: pct(v, 3).lstrip("+")),
            "asymptotic ratio": gci["asymptotic_ratio"].map(
                lambda v: "n/a" if pd.isna(v) else f"{v:.3f}"),
        })
        add(_md_table(t))
        odd = gci[gci["convergence_type"] != "monotone"]
        add("")
        if len(odd):
            add("**Not monotone:** " + "; ".join(
                f"{label[r.quantity]} at Mach {r.mach:g} is *{r.convergence_type}* "
                f"({r.note})" for r in odd.itertuples()) + "\n")
        low = gci[(gci["convergence_type"] == "monotone") & (gci["observed_order"] < 0.5)]
        high = gci[(gci["convergence_type"] == "monotone") & (gci["observed_order"] > 3.0)]
        if len(low) or len(high):
            add("**Pathological observed order:** " + "; ".join(
                f"{label[r.quantity]} at Mach {r.mach:g} has p = {r.observed_order:.2f}"
                for r in pd.concat([low, high]).itertuples())
                + ". An order far from the scheme's formal 1–2 means the three meshes are not "
                  "in the asymptotic range for that quantity, so its Richardson value and GCI "
                  "should be read as indicative only.\n")
        cdg = gci[gci["quantity"] == "cd_fore"]
        if len(cdg) and (cdg["observed_order"] < 1.0).any():
            lowm = cdg[cdg["observed_order"] < 1.0]
            add("**The observed order of forebody C_D is below first order at Mach "
                + " and ".join(f"{m:g}" for m in lowm["mach"]) + "** ("
                + ", ".join(f"p = {r_.observed_order:.2f} at Mach {r_.mach:g}"
                            for r_ in cdg.itertuples())
                + "). The milestone's written hypothesis was 'between 1 and 2'; it is **not** "
                "borne out there. A captured shock makes a TVD scheme locally first order, "
                "and NASA's NPARC verification tutorial (*Examining Spatial (Grid) "
                "Convergence*, opened 2026-09-21) says the observed order 'will likely be "
                "lower' than the theoretical one and lists the 'presence of shocks' among the "
                "causes - but it gives no number, and no opened source states that a "
                "sub-first-order p is normal for this problem. Two consequences: a low p makes "
                "the Richardson correction and the GCI LARGER than a first-order assumption "
                "would (conservative); and an asymptotic ratio near 1 only shows the three "
                "meshes are mutually consistent with that p, not that p is the scheme's true "
                "order. The 'p range' column of the next table shows how weakly p is "
                "determined: it is computed from a fine–medium difference of about 0.1%, which "
                "is not large against the iterative band.\n")
        else:
            add("The flow contains a captured shock, where any TVD scheme is locally first "
                "order, so an observed order between 1 and 2 is the expected outcome for "
                "integrated quantities.\n")
        snap = []
        for (mach_, level_), grp in candidates[candidates["status"] == "OK"].groupby(
                ["mach", "level"]):
            if len(grp) > 1:
                p0s, sos = grp["p_stag_over_p_inf"], grp["standoff_over_max_radius"]
                snap.append(f"Mach {mach_:g} {level_}: p0/p∞ from {p0s.min():.3f} to "
                            f"{p0s.max():.3f} ({100 * (p0s.max() / p0s.min() - 1):.2f}%), Δ/R "
                            f"from {sos.min():.5f} to {sos.max():.5f} "
                            f"({100 * (sos.max() / sos.min() - 1):.2f}%)")
        if snap:
            add("**p0/p∞ and Δ/R are read from the field at the LAST iteration, not averaged "
                "over a window** (only the force has a history). Where several solutions "
                "exist on the same mesh, that snapshot noise can be read directly - "
                + "; ".join(snap) + ". For p0/p∞ it is as large as the differences between "
                "mesh levels, so whether its mesh convergence comes out 'monotone' or "
                "'oscillatory' depends on which snapshot is used: with the original fine cases "
                "it was oscillatory at Mach 3, with the solutions of record it is oscillatory "
                "at Mach 6 (compare `gci_original_fine_cases.csv`). Its Richardson value and "
                "GCI should not be relied on at either Mach number; it is judged against the "
                "exact Rayleigh-pitot value in condition 3 instead.\n")
        add("The shock position moves in steps tied to the cell size (the captured shock is "
            f"{ok['shock_thickness_cells'].min():.1f}–{ok['shock_thickness_cells'].max():.1f} "
            "cells thick on the stagnation line), which is why its convergence is less clean "
            "than that of C_D.\n")
        if len(cdg) and "limit_cycle_half_p2p_rel_fine" in cdg:
            add("**Iterative (limit-cycle) band, kept separate from the GCI.** Columns of "
                "the same names are in `gci.csv` for the M3 surface's GCI hook to read.\n")
            t = pd.DataFrame({
                "Mach": cdg["mach"].map("{:g}".format),
                "fine case of record": cdg["fine_case_of_record"],
                "± half p-p, coarse": cdg["limit_cycle_half_p2p_rel_coarse"].map(
                    lambda v: f"{100 * v:.4f}%"),
                "medium": cdg["limit_cycle_half_p2p_rel_medium"].map(
                    lambda v: f"{100 * v:.4f}%"),
                "fine": cdg["limit_cycle_half_p2p_rel_fine"].map(lambda v: f"{100 * v:.4f}%"),
                "discretisation band, coarse": cdg["band_coarse_rel"].map(
                    lambda v: f"{100 * v:.3f}%"),
                "… with fine at its cycle extremes (max)": cdg[
                    "band_coarse_at_cycle_extremes_max"].map(lambda v: f"{100 * v:.3f}%"),
                "GCI_medium … (max)": cdg["gci_medium_at_cycle_extremes_max"].map(
                    lambda v: f"{100 * v:.3f}%"),
                "GCI_fine … (max)": cdg["gci_fine_at_cycle_extremes_max"].map(
                    lambda v: f"{100 * v:.3f}%"),
                "p range": [f"{a:.2f}–{b:.2f}" for a, b in zip(
                    cdg["observed_order_at_cycle_extremes_min"],
                    cdg["observed_order_at_cycle_extremes_max"], strict=True)],
            })
            add(_md_table(t))
            add("\n*± half p-p* is half the peak-to-peak of each level's judged window: the "
                "most the instantaneous C_D departs from the reported window mean. The "
                "*cycle extremes* columns repeat the whole Celik procedure with the fine value "
                "moved to the top and bottom of its cycle. The *coarse* band is 1.25 × the "
                "Richardson error estimate of the coarse mesh - the quantity the M3 surface "
                "(built on the coarse mesh, A-CFD-10) actually consumes.\n")
        og = gci_orig[gci_orig["quantity"] == "cd_fore"] if len(gci_orig) else gci_orig
        if len(og) and len(cdg) and not og["phi_fine"].reset_index(drop=True).equals(
                cdg["phi_fine"].reset_index(drop=True)):
            add("**Same study computed with the ORIGINAL (non-converged) fine cases**, window "
                "means, for comparison - `gci_original_fine_cases.csv`:\n")
            t = pd.DataFrame({
                "Mach": og["mach"].map("{:g}".format),
                "fine C_D (original)": og["phi_fine"].map("{:.6f}".format),
                "fine C_D (of record)": cdg["phi_fine"].map("{:.6f}".format).to_numpy(),
                "p (original)": og["observed_order"].map("{:.2f}".format),
                "p (of record)": cdg["observed_order"].map("{:.2f}".format).to_numpy(),
                "GCI_fine (original)": og["gci_fine"].map(lambda v: f"{100 * v:.3f}%"),
                "GCI_fine (of record)": cdg["gci_fine"].map(
                    lambda v: f"{100 * v:.3f}%").to_numpy(),
                "coarse band (original)": og["band_coarse_rel"].map(
                    lambda v: f"{100 * v:.3f}%"),
                "coarse band (of record)": cdg["band_coarse_rel"].map(
                    lambda v: f"{100 * v:.3f}%").to_numpy(),
            })
            add(_md_table(t))
            add("\nThe mean of a limit cycle is not the fixed point: the window-mean of the "
                "oscillating solution and the converged value differ by a few hundredths of "
                "a percent, which is small against every tolerance here but not small against "
                "the fine–medium difference the observed order is computed from.\n")
    else:
        add("*GCI not available: fewer than three successful mesh levels at any Mach.*\n")
    if any(f.name == "M2_mesh_convergence.png" for f in figs):
        add("![mesh convergence](../figures/M2_mesh_convergence.png)\n")

    # -- condition 3 ------------------------------------------------------------------
    add("## Condition 3 — comparison with published references\n")
    add("Fine-mesh values. *Like-for-like* marks references that describe the same physics "
        "as the computation (inviscid, perfect gas, pressure only); only those decide the "
        "condition. The others are shown because a reader will want them, with the reason "
        "they are not decisive.\n")
    if bench.empty:
        add("*No fine-mesh result yet - nothing to compare.*\n")
        bench = pd.DataFrame(columns=["mach", "quantity", "cfd_fine", "reference",
                                      "rel_difference", "tolerance", "within_tolerance",
                                      "gci_fine", "like_for_like", "reference_source",
                                      "how_reference_was_read", "note"])
    t = pd.DataFrame({
        "Mach": bench["mach"].map("{:g}".format), "quantity": bench["quantity"],
        "CFD (fine)": bench["cfd_fine"].map("{:.4f}".format),
        "reference": bench["reference"].map("{:.4f}".format),
        "difference": bench["rel_difference"].map(pct),
        "tolerance": bench["tolerance"].map(
            lambda v: "—" if pd.isna(v) else f"±{100 * v:g}%"),
        "within": bench["within_tolerance"].map(
            lambda v: "—" if v is None or pd.isna(v) else ("yes" if v else "**NO**")),
        "GCI_fine": bench["gci_fine"].map(lambda v: "—" if pd.isna(v) else pct(v).lstrip("+")),
        "like-for-like": bench["like_for_like"].map(lambda b: "yes" if b else "no"),
        "source (how read)": bench["reference_source"] + " (" +
        bench["how_reference_was_read"] + ")",
    })
    add(_md_table(t))
    add("")
    for r in bench[bench["note"].astype(str).str.len() > 0].itertuples():
        add(f"- Mach {r.mach:g}, {r.quantity}: {r.note}")
    add("\nTolerances and their justification are in `configs/cfd_validation.yaml`; the "
        "reference values and exactly how each was verified are in "
        "`data/reference/sphere_supersonic.yaml`, including the list of values that could "
        "**not** be verified from a fetched source and were therefore not used.\n")
    bl = bench[bench["quantity"] == "standoff/R (Billig)"]
    if len(bl):
        add("**Billig's exponent is ambiguous in the sources that could be opened.** The "
            f"comparison above uses Δ/R = 0.143 exp({BILLIG_EXPONENT_USED}/M²), confirmed in "
            f"two secondary sources; a third prints {BILLIG_EXPONENT_ALSO_PRINTED}. The original "
            "paper (J. Spacecraft Rockets 4(6), 822–823, 1967; bibliographic record verified "
            "via Crossref) is paywalled and was not read. With the other exponent: "
            + "; ".join(
                f"Mach {b.mach:g}: reference {_billig_alt(b.mach):.4f} instead of "
                f"{b.reference:.4f}, CFD difference {pct(b.cfd_fine / _billig_alt(b.mach) - 1)} "
                f"instead of {pct(b.rel_difference)}" for b in bl.itertuples())
            + f". Either way inside the ±{100 * bl['tolerance'].iloc[0]:g}% project tolerance, "
              "and either way this row is not like-for-like and does not decide condition 3.\n")
    add("**Total sphere drag is not validated.** The published free-flight C_D is a total "
        "(forebody + base + friction). This CFD computes the forebody pressure drag only, so "
        "the row above is a statement of how much is left over, not a comparison. Comparison "
        "(c) of the milestone brief is therefore **LIMITED**: it was made against the "
        "forebody pressure-drag expression quoted in the same AEDC report, not against the "
        "measured totals.\n")
    add("![benchmark](../figures/M2_benchmark.png)\n")
    for f in figs:
        if f.name.startswith("M2_flowfield_sphere"):
            add(f"![flow field](../figures/{f.name})\n")

    # -- negative + demo --------------------------------------------------------------
    add("## What did not work\n")
    if neg is not None and len(neg):
        n = neg.iloc[0]
        add(f"**The negative case: can the gate say no?** The full-body configuration (sphere "
            f"plus inviscid wake, NR-06) is re-run inside the audited pipeline as case "
            f"`{n['case']}`. It is SUPPOSED to fail the force criterion; a criterion that "
            f"this case passed would be worthless. Status {n['status']}"
            + (f" — {n['failure_reason']}" if n["status"] != "OK" else "") + ".")
        if n["status"] == "OK":
            add(f"After {int(n['n_iterations']):,} iterations ({int(n['n_extensions'])} "
                f"extensions): total-C_D criterion met: "
                f"**{'yes' if bool(n['cd_total_converged']) else 'no'}** (peak-to-peak "
                f"{pct(n['cd_total_peak_to_peak_rel'], 3).lstrip('+')}, drift "
                f"{pct(n['cd_total_drift_rel'], 3).lstrip('+')}). Forebody C_D "
                f"{n['cd_fore']:.4f}, peak-to-peak "
                f"{pct(n['cd_fore_peak_to_peak_rel'], 3).lstrip('+')}; **afterbody C_D "
                f"{n['cd_aft']:.4f} with drift {pct(n['cd_aft_drift_rel'], 3).lstrip('+')} and "
                f"peak-to-peak {pct(n['cd_aft_peak_to_peak_rel'], 3).lstrip('+')}** over the "
                f"assessment window; minimum outflow Mach {n['outlet_min_mach']:.2f}. ")
    add("Every failed or abandoned attempt is logged in `docs/negative_results.md` "
        "(NR-05 onwards); none has been deleted.\n")

    add("## Pipeline demonstration on a capsule-like body\n")
    if demo is not None and len(demo):
        d = demo.iloc[-1]
        pd_cfg = cfg["pipeline_demo"]
        add(f"One generic blunted cone (nose radius {pd_cfg['nose_radius_m']} m, diameter "
            f"{pd_cfg['diameter_m']} m, {pd_cfg['cone_half_angle_deg']:g}° half-angle, "
            f"shoulder radius {pd_cfg['shoulder_radius_m']} m) was passed to the same "
            f"`run_case` call as an (x, r) outline at Mach {d['mach']:g}, refinement factor "
            f"{int(d['refinement_factor'])}. {len(demo)} attempt(s); every one is kept.\n")
        t = pd.DataFrame({
            "attempt": demo["case"],
            "Billig sizing radius [m]": demo["sizing_radius_m"].map("{:.2f}".format),
            "inflow boundary on axis x [m]": demo["upstream_axis_x_m"].map("{:.3f}".format),
            "status": demo["status"],
            "verdict (M3 acceptance rules)": demo["verdict"],
            "reason": [" ".join(str(v) for v in (a, b) if isinstance(v, str) and v)
                       for a, b in zip(demo["failure_reason"], demo["reasons"], strict=True)],
        })
        add(_md_table(t))
        add("\nAttempt 0 uses the domain M2 sizes for a sphere (Billig stand-off of the NOSE "
            "radius). Later attempts reuse, unchanged, what M3 built for capsules: blunt-cone "
            "domain sizing (NR-20), a first-order start (NR-19), on- and off-axis "
            "shock-clearance checks, and automatic domain enlargement (`design_points.py`, "
            "parameters read from `configs/cfd_design_points.yaml`).")
        iso = run_dir_of(rel, repo_root) / val.demo_isolation_name(cfg) / "case_result.json"
        if iso.exists():
            i_ = json.loads(iso.read_text())
            add(f"\nBecause the first retry changes two things at once, one more case "
                f"separates them: `{i_['case_name']}` keeps attempt 0's domain and adds ONLY "
                f"the first-order start. Status: **{i_['status']}**"
                + (f" ({i_['failure_reason']})" if i_["status"] != "OK" else "") + ". "
                + ("It fails the same way, so the start-up is not the cause and the domain "
                   "is: a 60° cone at Mach 6 carries a detached shock that the sphere-sized "
                   "inflow boundary does not contain. Where the shock meets the boundary was "
                   "not observed (a crashed case writes no field)."
                   if i_["status"] != "OK" else
                   "It runs, so the impulsive second-order start, not the domain, killed "
                   "attempt 0.") + " NR-26.\n")
        if d["status"] == "OK":
            add(f"Final attempt `{d['case']}`: {int(d['n_cells']):,} cells, checkMesh max "
                f"non-orthogonality {d['max_non_orthogonality_deg']:.1f}°, solver wall time "
                f"{d['solver_wall_time_s']:.0f} s, {int(d['n_iterations']):,} iterations. "
                f"Model predicts forebody C_D = "
                f"{d['cd_fore']:.4f} (convergence criterion "
                f"{'met' if bool(d['cd_fore_converged']) else '**not met**'}: peak-to-peak "
                f"{pct(d['cd_fore_peak_to_peak_rel'], 4).lstrip('+')}, drift "
                f"{pct(d['cd_fore_drift_rel'], 4).lstrip('+')}), stand-off "
                f"Δ/R_max = {d['standoff_over_max_radius']:.4f}, p0/p∞ = "
                f"{d['p_stag_over_p_inf']:.3f}, minimum outflow Mach "
                f"{d['outlet_min_mach']:.2f}, shock clearance on the axis "
                f"{d['upstream_clearance_fraction']:.2f}, outer-outflow Mach deficit "
                f"{pct(d['outer_outlet_mach_deficit_rel'], 3).lstrip('+')}.")
        else:
            add(f"Final attempt `{d['case']}`: **{d['status']}** — {d['failure_reason']}.")
        add("\nThis is a demonstration that the pipeline generalises beyond the sphere. It is "
            "**one mesh, no mesh study, no reference data**, and its numbers are not "
            "validated results. The project capsule (`aether.geometry.capsule`) exposes "
            "`.profile(n) -> (x_m, r_m)`, which is exactly what `make_outline` accepts.\n")
        if d["status"] == "OK":
            add("![demo pressure](../figures/M2_demo_capsule_pressure.png)\n")
            if any(f.name == "M2_flowfield_demo_capsule.png" for f in figs):
                add("![demo flow field](../figures/M2_flowfield_demo_capsule.png)\n")
    else:
        add("*Not run.*\n")

    # -- condition 4 + deviations -----------------------------------------------------
    add("## Condition 4 — what this CFD may and may not be used for\n")
    add("Written out in full in `docs/validation/M2_model_form_limits.md`. In one paragraph: "
        "the model is inviscid, calorically perfect, chemistry-free, radiation-free, steady, "
        "axisymmetric at zero incidence, and stops at the maximum-radius station. Within "
        "tested assumptions it may be used for **forebody pressure-drag coefficients, "
        "forebody surface pressure, and perfect-gas shock shape**, preferably for comparing "
        "geometries with each other. It may **not** be used for heating of any kind — "
        "heating stays with Sutton–Graves — nor for base drag, flight shock stand-off, "
        "shock-layer temperatures, lift, moments or stability.\n")
    add(_downstream_facts(gate, gci, repo_root))
    add("## Deviations from the specification\n")
    add(f"- **OpenFOAM version.** Spec §16 standardises on "
        f"{gate['openfoam_version_required_by_spec']}; the build installed and used is "
        f"**{gate['openfoam_version_installed']}**. Nothing was installed or upgraded for "
        f"this milestone. Recorded as ASSUMPTIONS A-CFD-6.")
    add("- **Base drag is outside the validated envelope** (see above and A-CFD-5).\n")
    add("## Evidence\n")
    add(f"- Tables: `{rel}/mesh_study.csv`, `gci.csv`, `benchmark_comparison.csv`, "
        f"`gate_assessment.json`, `level_candidates.csv`, `limit_cycle.csv`, "
        f"`gci_original_fine_cases.csv`, `pipeline_demo.csv`, `negative_cases.csv`")
    add(f"- Per case: `{rel}/<case>/` — `force_history.csv`, `stagnation_line.csv`, "
        f"`body_pressure.csv`, `metrics.csv`, `case_result.json`, `dictionaries/`, "
        f"`log_tails/`")
    add("- Figures: " + ", ".join(f"`reports/figures/{f.name}`" for f in figs) + " (+ PDF)")
    add("- Reproduce: `make cfd-validate` (solver stages take hours; "
        "`make cfd-report RUN_ID=<id>` rebuilds tables, figures and this file only)")
    return "\n".join(L) + "\n"
