"""Milestone M2: the CFD validation study that decides gate G4 (spec §17).

Runs the sphere benchmark on three geometrically similar meshes at each Mach number,
computes Richardson extrapolation / GCI, compares the fine-mesh solution with published
references, runs one capsule-like body through the same pipeline, and writes every number
to CSV/JSON. The milestone report is generated FROM those files (see ``report.py``).

The study is resumable: a case whose ``case_result.json`` already exists under the run
directory is loaded, not re-run. Failed cases are kept and reported, never deleted.
"""

from __future__ import annotations

import json
import math
from dataclasses import fields
from pathlib import Path

import pandas as pd
import yaml

from ..utils.run import REPO_ROOT
from .case import FlowCondition, SolverSettings
from .gci import grid_convergence_index
from .mesh import MeshSettings
from .outline import Outline, sphere_cone_capsule_outline, sphere_outline
from .pipeline import CaseResult, run_case
from .postprocess import ConvergenceCriterion
from .reference import (
    billig_standoff_over_radius,
    modified_newtonian_sphere_forebody_cd,
    rayleigh_pitot_ratio,
)
from .runner import openfoam_version

LEVEL_NAMES = {0: "coarse", 1: "medium", 2: "fine"}
# The benchmark domain is forebody-only, so cd_total == cd_fore there and cd_aft is absent.
GCI_QUANTITIES = ("cd_fore", "standoff_over_max_radius", "p_stag_over_p_inf")
GATE_FORCE_QUANTITY = "cd_fore"
LIMITATIONS_DOC = REPO_ROOT / "docs" / "validation" / "M2_model_form_limits.md"


def _mesh_settings(cfg: dict, factor: int) -> MeshSettings:
    m = cfg["mesh"]
    names = {f.name for f in fields(MeshSettings)}
    kwargs = {k: v for k, v in m.items() if k in names}
    return MeshSettings(refinement_factor=factor, **kwargs)


def _solver_settings(cfg: dict, factor: int) -> SolverSettings:
    s = cfg["solver"]
    if s["equations"] != "euler":
        raise ValueError("M2 is declared inviscid; a viscous run needs its own validation")
    return SolverSettings(
        n_iterations=int(s["n_iterations"][factor]), max_co=float(s["max_co"]),
        rdeltat_smoothing=float(s["rdeltat_smoothing"]), flux_scheme=s["flux_scheme"],
        limiter=s["limiter"], force_interval=int(s["force_interval"]),
        n_ranks=int(s["n_ranks"]), dynamic_viscosity_pa_s=0.0,
        max_extensions=int(s.get("max_extensions", 0)),
        extension_fraction=float(s.get("extension_fraction", 0.5)),
    )


def _flow(cfg: dict, mach: float) -> FlowCondition:
    g = cfg["gas"]
    return FlowCondition(mach=float(mach), pressure_pa=float(g["pressure_pa"]),
                         temperature_k=float(g["temperature_k"]), gamma=float(g["gamma"]))


def _run_or_load(case_name: str, run_dir: Path, **kwargs) -> CaseResult:
    cached = run_dir / case_name / "case_result.json"
    if cached.exists():
        return CaseResult(**json.loads(cached.read_text()))
    return run_case(case_name, results_dir=run_dir, **kwargs)


def case_name_for(body: str, mach: float, level: str) -> str:
    return f"{body}_M{mach:g}_{level}".replace(".", "p")


# ---------------------------------------------------------------------------------------
# Stage 1+2: benchmark on three meshes
# ---------------------------------------------------------------------------------------

def run_mesh_study(cfg: dict, run_id: str, run_dir: Path, generated_root: Path,
                   mach_numbers: list[float] | None = None,
                   levels: list[int] | None = None) -> pd.DataFrame:
    crit = ConvergenceCriterion(**cfg["convergence_criterion"])
    bench = cfg["benchmark"]
    outline = sphere_outline(float(bench["radius_m"]))
    factors = list(cfg["mesh"]["refinement_factors"])
    rows = []
    # Levels outermost: every cheap case finishes before the first expensive one starts, so
    # a broken setup is found in minutes rather than after an hour-long fine-mesh run.
    for i, factor in enumerate(factors):
        if levels is not None and i not in levels:
            continue
        for mach in (mach_numbers or bench["mach_numbers"]):
            name = case_name_for("sphere", mach, LEVEL_NAMES[i])
            res = _run_or_load(
                name, run_dir, outline=outline, flow=_flow(cfg, mach),
                mesh_settings=_mesh_settings(cfg, factor),
                solver=_solver_settings(cfg, factor), criterion=crit,
                generated_root=generated_root / run_id,
                sizing_radius_m=float(bench["radius_m"]),
            )
            rows.append(_row(res, mach, LEVEL_NAMES[i], factor))
    return pd.DataFrame(rows).sort_values(["mach", "refinement_factor"]).reset_index(drop=True)


def _row(res: CaseResult, mach: float, level: str, factor: int) -> dict:
    conv = res.convergence or {}
    row = {
        "case": res.case_name, "mach": mach, "level": level, "refinement_factor": factor,
        "status": res.status, "failure_reason": res.failure_reason,
        "n_cells": res.n_cells, "h_m": res.representative_cell_size_m,
        "solver_wall_time_s": res.solver_wall_time_s,
        "total_wall_time_s": res.total_wall_time_s,
        "max_non_orthogonality_deg": res.mesh_quality.get("max_non_orthogonality_deg"),
        "max_skewness": res.mesh_quality.get("max_skewness"),
        "max_aspect_ratio": res.mesh_quality.get("max_aspect_ratio"),
    }
    row.update(res.metrics)
    for q, c in conv.items():
        row[f"{q}_converged"] = c["converged"]
        row[f"{q}_peak_to_peak_rel"] = c["peak_to_peak_rel"]
        row[f"{q}_drift_rel"] = c["drift_rel"]
    return row


def collect_mesh_study(cfg: dict, run_dir: Path) -> pd.DataFrame:
    """Rebuild the mesh-study table from whatever case results exist on disk."""
    rows = []
    for mach in cfg["benchmark"]["mach_numbers"]:
        for i, factor in enumerate(cfg["mesh"]["refinement_factors"]):
            cached = run_dir / case_name_for("sphere", mach, LEVEL_NAMES[i]) / "case_result.json"
            if cached.exists():
                res = CaseResult(**json.loads(cached.read_text()))
                rows.append(_row(res, mach, LEVEL_NAMES[i], factor))
    return pd.DataFrame(rows)


def gci_table(study: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mach, grp in study[study["status"] == "OK"].groupby("mach"):
        g = grp.set_index("level")
        if not {"coarse", "medium", "fine"} <= set(g.index):
            continue
        for q in GCI_QUANTITIES:
            r = grid_convergence_index(
                q, g.loc["fine", q], g.loc["medium", q], g.loc["coarse", q],
                g.loc["fine", "h_m"], g.loc["medium", "h_m"], g.loc["coarse", "h_m"])
            rows.append({"mach": mach, **r.to_dict()})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------
# Stage 3: comparison with published references
# ---------------------------------------------------------------------------------------

def _nearest_row(rows: list[dict], mach: float, max_gap: float) -> dict | None:
    best = min(rows, key=lambda r: abs(r["mach"] - mach))
    return best if abs(best["mach"] - mach) <= max_gap else None


def benchmark_table(cfg: dict, study: pd.DataFrame, gci: pd.DataFrame) -> pd.DataFrame:
    bench = cfg["benchmark"]
    tol = {k: v["value"] for k, v in bench["tolerances"].items()}
    ref = yaml.safe_load((REPO_ROOT / bench["reference_data"]).read_text())
    gamma = float(cfg["gas"]["gamma"])
    rows = []

    def add(mach, quantity, cfd, reference, source, how_read, tolerance, like_for_like,
            gci_quantity, note=""):
        g = gci[(gci["mach"] == mach) & (gci["quantity"] == gci_quantity)]
        rel = (cfd - reference) / reference
        rows.append({
            "mach": mach, "quantity": quantity, "cfd_fine": cfd, "reference": reference,
            "rel_difference": rel, "tolerance": tolerance,
            "within_tolerance": bool(abs(rel) <= tolerance),
            "gci_fine": float(g["gci_fine"].iloc[0]) if len(g) else float("nan"),
            "like_for_like": like_for_like, "reference_source": source,
            "how_reference_was_read": how_read, "note": note,
        })

    fine = study[(study["level"] == "fine") & (study["status"] == "OK")]
    for _, c in fine.iterrows():
        mach = float(c["mach"])
        add(mach, "p_stag/p_inf", c["p_stag_over_p_inf"], rayleigh_pitot_ratio(mach, gamma),
            "Rayleigh pitot relation, NACA Report 1135 eq. 100", "closed form",
            tol["stagnation_pressure_rel"], True, "p_stag_over_p_inf")
        vdg = _nearest_row(ref["sphere_standoff_over_radius"]["rows"], mach, 1e-9)
        if vdg:
            add(mach, "standoff/R", c["standoff_over_max_radius"],
                vdg["standoff_over_radius"],
                "Van Dyke & Gordon, NASA TR R-1 (1959), Table III", "tabulated",
                tol["standoff_vs_van_dyke_gordon_rel"], True, "standoff_over_max_radius",
                "inviscid numerical reference")
        add(mach, "standoff/R (Billig)", c["standoff_over_max_radius"],
            billig_standoff_over_radius(mach),
            "Billig, J. Spacecraft Rockets 4(6) 1967 (formula verified via secondary sources)",
            "correlation", tol["standoff_vs_billig_rel"], False, "standoff_over_max_radius",
            "empirical correlation of experiments; no verified accuracy statement")
        clark = ref["sphere_forebody_pressure_cd"]
        add(mach, "C_D forebody (pressure)", c["cd_fore"], clark["a"] - clark["b"] / mach**2,
            "Clark's expression as quoted in Bailey & Hiatt, AEDC-TR-70-291 Sec. 4.5",
            "equation in text", tol["forebody_cd_vs_clark_rel"], True, "cd_fore")
        bh = _nearest_row(ref["sphere_total_cd"]["rows"], mach, tol["mach_match_abs"])
        if bh:
            # NOT a validation comparison: the forebody domain computes no base pressure.
            # Reported so the reader can see how much of the measured total is left over.
            rows.append({
                "mach": mach, "quantity": "C_D total (measured) vs C_D forebody (CFD)",
                "cfd_fine": c["cd_fore"], "reference": bh["cd"],
                "rel_difference": (c["cd_fore"] - bh["cd"]) / bh["cd"],
                "tolerance": float("nan"), "within_tolerance": None,
                "gci_fine": float("nan"), "like_for_like": False,
                "reference_source": "Bailey & Hiatt, AEDC-TR-70-291 (1971), Table II",
                "how_reference_was_read": "tabulated",
                "note": f"NOT COMPARED LIKE-FOR-LIKE. Reference row M={bh['mach']}, "
                        f"Re={bh['reynolds']}: free-flight TOTAL drag (forebody + base + "
                        f"friction). The difference is the part this CFD does not compute.",
            })
        rows.append({
            "mach": mach, "quantity": "C_D forebody (modified Newtonian, sanity only)",
            "cfd_fine": c["cd_fore"],
            "reference": modified_newtonian_sphere_forebody_cd(mach, gamma),
            "rel_difference": c["cd_fore"] / modified_newtonian_sphere_forebody_cd(mach, gamma)
            - 1.0,
            "tolerance": float("nan"), "within_tolerance": None, "gci_fine": float("nan"),
            "like_for_like": False, "reference_source": "modified Newtonian theory",
            "how_reference_was_read": "closed form",
            "note": "engineering estimate, not a validation reference; no tolerance applied",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------
# Stage 4: pipeline demonstration on a capsule-like body
# ---------------------------------------------------------------------------------------

def demo_outline(cfg: dict) -> Outline:
    d = cfg["pipeline_demo"]
    return sphere_cone_capsule_outline(
        d["nose_radius_m"], d["diameter_m"], d["cone_half_angle_deg"],
        d["shoulder_radius_m"], d["aft_cone_angle_deg"], d["base_radius_m"])


def run_pipeline_demo(cfg: dict, run_id: str, run_dir: Path,
                      generated_root: Path) -> pd.DataFrame:
    d = cfg["pipeline_demo"]
    factor = int(d["refinement_factor"])
    res = _run_or_load(
        case_name_for("capsuledemo", d["mach"], f"x{factor}"), run_dir,
        outline=demo_outline(cfg), flow=_flow(cfg, d["mach"]),
        mesh_settings=_mesh_settings(cfg, factor), solver=_solver_settings(cfg, factor),
        criterion=ConvergenceCriterion(**cfg["convergence_criterion"]),
        generated_root=generated_root / run_id,
    )
    return pd.DataFrame([_row(res, float(d["mach"]), f"x{factor}", factor)])


def run_negative_cases(cfg: dict, run_id: str, run_dir: Path,
                       generated_root: Path) -> pd.DataFrame:
    """Re-run, inside the audited pipeline, the configuration that was tried and abandoned:
    a FULL-body sphere with its inviscid wake (negative result NR-06). Kept so the failure
    is reproducible evidence rather than an anecdote."""
    n = cfg["negative_cases"]["full_body_sphere"]
    factor = int(n["refinement_factor"])
    mesh = _mesh_settings(cfg, factor)
    mesh = MeshSettings(**{**mesh.__dict__, "extent": "full"})
    res = _run_or_load(
        case_name_for("spherefullbody", n["mach"], f"x{factor}"), run_dir,
        outline=sphere_outline(float(cfg["benchmark"]["radius_m"])),
        flow=_flow(cfg, n["mach"]), mesh_settings=mesh,
        solver=_solver_settings(cfg, factor),
        criterion=ConvergenceCriterion(**cfg["convergence_criterion"]),
        generated_root=generated_root / run_id,
        sizing_radius_m=float(cfg["benchmark"]["radius_m"]),
    )
    return pd.DataFrame([_row(res, float(n["mach"]), f"x{factor}", factor)])


# ---------------------------------------------------------------------------------------
# Stage 5: the gate
# ---------------------------------------------------------------------------------------

def assess_gate(cfg: dict, study: pd.DataFrame, gci: pd.DataFrame,
                bench: pd.DataFrame, demo: pd.DataFrame | None) -> dict:
    """Apply spec §17's four conditions. PASS requires ALL of them, with no judgement call
    made after the fact: each rule below was fixed in the config before the runs."""
    mi = cfg["mesh_independence"]
    n_expected = len(cfg["benchmark"]["mach_numbers"]) * len(cfg["mesh"]["refinement_factors"])
    all_ran = len(study) == n_expected and bool((study["status"] == "OK").all())

    cd = gci[gci["quantity"] == GATE_FORCE_QUANTITY] if len(gci) else gci
    so = gci[gci["quantity"] == "standoff_over_max_radius"] if len(gci) else gci
    cond1_detail = {
        "all_three_levels_ran_at_every_mach": all_ran,
        "cd_fore_gci_fine_max": float(cd["gci_fine"].max()) if len(cd) else math.nan,
        "cd_fore_fine_medium_change_max": (float(cd["rel_error_fine_medium"].max())
                                            if len(cd) else math.nan),
        "cd_fore_convergence_types": sorted(set(cd["convergence_type"])) if len(cd) else [],
        "standoff_gci_fine_max": float(so["gci_fine"].max()) if len(so) else math.nan,
        "standoff_convergence_types": sorted(set(so["convergence_type"])) if len(so) else [],
    }
    cond1 = (all_ran and len(cd) > 0
             and cond1_detail["cd_fore_gci_fine_max"] <= mi["max_gci_fine_cd_rel"]
             and cond1_detail["cd_fore_fine_medium_change_max"]
             <= mi["max_fine_medium_change_cd_rel"]
             and set(cond1_detail["cd_fore_convergence_types"])
             <= {"monotone", "converged_to_tolerance"})

    conv_cols = ["cd_fore_converged"]
    have_conv = all(c in study.columns for c in conv_cols)
    cond2_detail = {c: (study.set_index("case")[c].astype(bool).to_dict() if have_conv else {})
                    for c in conv_cols}
    cond2 = have_conv and all_ran and bool(study["cd_fore_converged"].astype(bool).all())

    lfl = bench[bench["like_for_like"] == True] if len(bench) else bench  # noqa: E712
    other = bench[(bench["like_for_like"] == False)  # noqa: E712
                  & bench["within_tolerance"].notna()] if len(bench) else bench
    cond3 = len(lfl) > 0 and bool(lfl["within_tolerance"].astype(bool).all())
    cond3_detail = {
        "like_for_like_all_within_tolerance": cond3,
        "like_for_like_misses": lfl[~lfl["within_tolerance"].astype(bool)][
            ["mach", "quantity", "rel_difference", "tolerance"]].to_dict("records")
        if len(lfl) else [],
        "not_like_for_like_misses": other[~other["within_tolerance"].astype(bool)][
            ["mach", "quantity", "rel_difference", "tolerance"]].to_dict("records")
        if len(other) else [],
    }
    cond4 = LIMITATIONS_DOC.exists()

    conditions = {
        "1_mesh_independence": {"met": bool(cond1), "detail": cond1_detail},
        "2_force_convergence": {"met": bool(cond2), "detail": cond2_detail},
        "3_published_benchmark": {"met": bool(cond3), "detail": cond3_detail},
        "4_model_limitations_documented": {
            "met": bool(cond4),
            "detail": {"document": str(LIMITATIONS_DOC.relative_to(REPO_ROOT))}},
    }
    n_met = sum(c["met"] for c in conditions.values())
    if n_met == 4:
        status = "PASS"
    elif not all_ran:
        status = "IN_PROGRESS" if len(study) < n_expected else "FAIL"
    else:
        status = "LIMITED"
    return {
        "gate": "G4", "status": status, "conditions": conditions,
        "openfoam_version_installed": openfoam_version(),
        "openfoam_version_required_by_spec": cfg["openfoam"]["required_by_spec"],
        "pipeline_demo_status": (demo["status"].iloc[0] if demo is not None and len(demo)
                                 else "NOT_RUN"),
    }


def write_tables(run_dir: Path, **tables: pd.DataFrame | dict) -> None:
    for name, obj in tables.items():
        if isinstance(obj, pd.DataFrame):
            obj.to_csv(run_dir / f"{name}.csv", index=False)
        else:
            with open(run_dir / f"{name}.json", "w") as fh:
                json.dump(obj, fh, indent=2, default=str)
