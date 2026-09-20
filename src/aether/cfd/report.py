"""Build the M2 tables, figures and milestone report FROM RESULT FILES.

No number in the report is typed by hand: every value is formatted out of a DataFrame that
was itself read from ``results/M2/<run-id>/``. Re-running this stage on the same run
directory reproduces the report byte-for-byte apart from the generation timestamp.
"""

from __future__ import annotations

import json
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
    demo = _collect_single(run_dir, "capsuledemo")
    neg = _collect_single(run_dir, "spherefullbody")
    gate = val.assess_gate(cfg, study, gci, bench, demo)
    meta = yaml.safe_load((run_dir / "config_snapshot.yaml").read_text())["_meta"]
    val.write_tables(run_dir, mesh_study=study, gci=gci, benchmark_comparison=bench,
                     gate_assessment=gate,
                     **({"pipeline_demo": demo} if demo is not None else {}),
                     **({"negative_cases": neg} if neg is not None else {}))

    figs = [plots.plot_force_histories(study, run_dir, cfg, run_id, fig_dir),
            plots.plot_residuals(study, run_dir, run_id, fig_dir),
            plots.plot_benchmark(study, run_dir, cfg, run_id, fig_dir)]
    if len(gci):
        figs.append(plots.plot_mesh_convergence(study, gci, run_id, fig_dir))

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
    if demo is not None and (demo["status"] == "OK").all():
        d = demo.iloc[0]
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

    text = _render(cfg, run_id, meta, study, gci, bench, demo, neg, gate, figs, repo_root)
    out = repo_root / "reports" / "milestones" / "M2_cfd_validation.md"
    out.write_text(text)
    return gate


def _render(cfg, run_id, meta, study, gci, bench, demo, neg, gate, figs, repo_root) -> str:
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

    add(f"## Gate G4 status: **{gate['status']}**\n")
    names = {"1_mesh_independence": "1. Mesh independence completed",
             "2_force_convergence": "2. Force convergence demonstrated",
             "3_published_benchmark": "3. Published blunt-body case compared",
             "4_model_limitations_documented": "4. Model-form limitations documented"}
    add(_md_table(pd.DataFrame(
        [{"spec §17 condition": names[k], "met": "yes" if c["met"] else "**no**"}
         for k, c in gate["conditions"].items()])))
    add("\nThe rules that decide each condition were written into the config before the "
        "validation cases were run; they are restated in each section below. `PASS` requires "
        "all four.\n")

    # -- what was run -----------------------------------------------------------------
    s = cfg["solver"]
    add("## What was computed\n")
    add(f"A sphere of radius {cfg['benchmark']['radius_m']} m in a uniform supersonic stream "
        f"of calorically perfect air (γ = {cfg['gas']['gamma']}), at Mach "
        f"{' and '.join(f'{m:g}' for m in cfg['benchmark']['mach_numbers'])}. Solver "
        f"`{s['application']}`, axisymmetric **Euler** equations on a "
        f"{cfg['mesh']['wedge_angle_deg']:g}° wedge, {s['flux_scheme']} flux with "
        f"{s['limiter']} reconstruction, local time stepping at max Courant number "
        f"{s['max_co']}. The domain covers the **{cfg['mesh']['extent']}** only (nose to the "
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
    add(f"\nWall times are single runs on this machine with {s['n_ranks']} MPI rank(s); they "
        f"are what M3 should budget per design point at each level.\n")

    # -- condition 2 ------------------------------------------------------------------
    add("## Condition 2 — force convergence\n")
    add(f"**Criterion (declared before the runs).** Over the final "
        f"{crit['window_iterations']} iterations the forebody drag coefficient must have "
        f"peak-to-peak variation ≤ {100 * crit['max_peak_to_peak_rel']:g}% of its mean **and** "
        f"a drift between the two halves of that window ≤ {100 * crit['max_drift_rel']:g}% "
        f"of its mean. The reported C_D is the mean over that window.\n")
    ok = study[study["status"] == "OK"]
    t = pd.DataFrame({
        "case": ok["case"], "C_D forebody": ok["cd_fore"].map("{:.5f}".format),
        "peak-to-peak": ok["cd_fore_peak_to_peak_rel"].map(lambda v: pct(v, 4).lstrip("+")),
        "drift": ok["cd_fore_drift_rel"].map(lambda v: pct(v, 4).lstrip("+")),
        "residual drop": (ok["final_mean_abs_drho_dtau"] / ok["initial_mean_abs_drho_dtau"]
                          ).map("{:.2e}".format),
        "criterion met": ok["cd_fore_converged"].map(lambda b: "yes" if b else "**no**"),
    })
    add(_md_table(t))
    add("\n*Residual drop* is the final volume-mean |∂ρ/∂τ| over its first recorded value. "
        "It is reported because the spec asks for residuals, and it is **not** part of the "
        "criterion: with a TVD limiter the density residual of this solver stalls once the "
        "captured shock starts flickering between neighbouring cells, while the integrated "
        "force has long since stopped moving. A reader who wants machine-zero residuals will "
        "not find them here.\n")
    add("![force convergence](../figures/M2_force_convergence.png)\n")
    add("![residuals](../figures/M2_residuals.png)\n")

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
        add("The flow contains a captured shock, where any TVD scheme is locally first order, "
            "so an observed order between 1 and 2 is the expected outcome for integrated "
            "quantities. The shock position moves in steps tied to the cell size "
            f"(the captured shock is "
            f"{ok['shock_thickness_cells'].min():.1f}–{ok['shock_thickness_cells'].max():.1f} "
            "cells thick on the stagnation line), which is why its convergence is less clean "
            "than that of C_D.\n")
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
        add(f"The full-body configuration (sphere plus inviscid wake) was re-run inside the "
            f"audited pipeline as case `{n['case']}`: status {n['status']}, "
            f"{int(n['n_iterations']):,} iterations. Forebody C_D peak-to-peak "
            f"{pct(n['cd_fore_peak_to_peak_rel'], 3).lstrip('+')}, **afterbody C_D "
            f"{n['cd_aft']:.4f} with drift {pct(n['cd_aft_drift_rel'], 3).lstrip('+')} and "
            f"peak-to-peak {pct(n['cd_aft_peak_to_peak_rel'], 3).lstrip('+')}** over the "
            f"assessment window; total-C_D criterion met: "
            f"{'yes' if bool(n['cd_total_converged']) else 'no'}. ")
    add("Every failed or abandoned attempt is logged in `docs/negative_results.md` "
        "(NR-05 onwards); none has been deleted.\n")

    add("## Pipeline demonstration on a capsule-like body\n")
    if demo is not None and len(demo):
        d = demo.iloc[0]
        pd_cfg = cfg["pipeline_demo"]
        add(f"One generic blunted cone (nose radius {pd_cfg['nose_radius_m']} m, diameter "
            f"{pd_cfg['diameter_m']} m, {pd_cfg['cone_half_angle_deg']:g}° half-angle, "
            f"shoulder radius {pd_cfg['shoulder_radius_m']} m) was passed to the same "
            f"`run_case` call as an (x, r) outline at Mach {d['mach']:g}, refinement factor "
            f"{int(d['refinement_factor'])}. Status: **{d['status']}**"
            + (f" — {d['failure_reason']}" if d["status"] != "OK" else "") + ".")
        if d["status"] == "OK":
            add(f"\n{int(d['n_cells']):,} cells, checkMesh max non-orthogonality "
                f"{d['max_non_orthogonality_deg']:.1f}°, solver wall time "
                f"{d['solver_wall_time_s']:.0f} s. Model predicts forebody C_D = "
                f"{d['cd_fore']:.4f} (convergence criterion "
                f"{'met' if bool(d['cd_fore_converged']) else '**not met**'}: peak-to-peak "
                f"{pct(d['cd_fore_peak_to_peak_rel'], 4).lstrip('+')}), stand-off "
                f"Δ/R_max = {d['standoff_over_max_radius']:.4f}, p0/p∞ = "
                f"{d['p_stag_over_p_inf']:.3f}, minimum outflow Mach "
                f"{d['outlet_min_mach']:.2f}.")
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
    add("## Deviations from the specification\n")
    add(f"- **OpenFOAM version.** Spec §16 standardises on "
        f"{gate['openfoam_version_required_by_spec']}; the build installed and used is "
        f"**{gate['openfoam_version_installed']}**. Nothing was installed or upgraded for "
        f"this milestone. Recorded as ASSUMPTIONS A-CFD-6.")
    add("- **Base drag is outside the validated envelope** (see above and A-CFD-5).\n")
    add("## Evidence\n")
    add(f"- Tables: `{rel}/mesh_study.csv`, `gci.csv`, `benchmark_comparison.csv`, "
        f"`gate_assessment.json`, `pipeline_demo.csv`, `negative_cases.csv`")
    add(f"- Per case: `{rel}/<case>/` — `force_history.csv`, `stagnation_line.csv`, "
        f"`body_pressure.csv`, `metrics.csv`, `case_result.json`, `dictionaries/`, "
        f"`log_tails/`")
    add("- Figures: " + ", ".join(f"`reports/figures/{f.name}`" for f in figs) + " (+ PDF)")
    add("- Reproduce: `make cfd-validate` (solver stages take hours; "
        "`make cfd-report RUN_ID=<id>` rebuilds tables, figures and this file only)")
    return "\n".join(L) + "\n"
