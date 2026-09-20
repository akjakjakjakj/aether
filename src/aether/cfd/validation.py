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
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields, replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import yaml

from ..utils.run import REPO_ROOT, load_config
from .case import FlowCondition, SolverSettings
from .gci import SAFETY_FACTOR_THREE_GRIDS, grid_convergence_index
from .mesh import MeshSettings
from .outline import Outline, sphere_cone_capsule_outline, sphere_outline
from .pipeline import CaseResult, restart_case, run_case
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
    """Load a FINISHED case; run a missing one; set an ABORTED one aside and re-run.

    A case is finished iff its ``case_result.json`` exists (``run_case`` writes it last, for
    failures too). A generated case directory WITHOUT that file is what a killed driver
    leaves behind: its state is unknown, so it is never resumed and never deleted - it is
    renamed ``<case>__aborted_<UTC time>`` next to where it was, logged in
    ``aborted_attempts.json``, and the case is run again from scratch."""
    cached = run_dir / case_name / "case_result.json"
    if cached.exists():
        return CaseResult(**json.loads(cached.read_text()))
    leftover = Path(kwargs["generated_root"]) / case_name
    if leftover.exists() and any(leftover.iterdir()):
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        aside = leftover.with_name(f"{case_name}__aborted_{stamp}")
        leftover.rename(aside)
        log = run_dir / "aborted_attempts.json"
        entries = json.loads(log.read_text()) if log.exists() else []
        entries.append({"case": case_name, "moved_to": str(aside), "when_utc": stamp,
                        "contents": sorted(p.name for p in aside.iterdir()),
                        "reason": "generated case directory existed without a "
                                  "case_result.json (driver killed mid-case)"})
        log.write_text(json.dumps(entries, indent=2))
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


def restart_case_name(mach: float, level: str, max_co: float) -> str:
    return f"{case_name_for('sphere', mach, level)}_Co{max_co:g}".replace(".", "p")


def run_courant_restarts(cfg: dict, run_id: str, run_dir: Path, generated_root: Path,
                         progress=print) -> pd.DataFrame:
    """Spec §36 step 6 on the benchmark cases that ran but missed the force criterion:
    continue each from its final solution under every lower Courant limit declared in
    ``courant_restarts``, as new, separately named cases. Serial solvers run side by side
    (NR-08). Resumable; a finished restart is loaded, not re-run."""
    rc = cfg["courant_restarts"]
    level = rc["level"]
    i = {v: k for k, v in LEVEL_NAMES.items()}[level]
    factor = list(cfg["mesh"]["refinement_factors"])[i]
    crit = ConvergenceCriterion(**cfg["convergence_criterion"])
    outline = sphere_outline(float(cfg["benchmark"]["radius_m"]))
    jobs = []
    for mach in cfg["benchmark"]["mach_numbers"]:
        src_name = case_name_for("sphere", mach, level)
        src = run_dir / src_name / "case_result.json"
        if not src.exists():
            continue
        if CaseResult(**json.loads(src.read_text())).convergence.get(
                GATE_FORCE_QUANTITY, {}).get("converged", False):
            continue                       # nothing to cure
        for co in rc["max_co"]:
            jobs.append((float(mach), float(co), src_name))

    def one(mach: float, co: float, src_name: str) -> dict:
        name = restart_case_name(mach, level, co)
        cached = run_dir / name / "case_result.json"
        res = CaseResult(**json.loads(cached.read_text())) if cached.exists() else None
        # finished == ran every block it owes; a restart that stopped short is resumed
        if res is None or (res.status == "OK" and int(res.metrics.get(
                "restart_blocks_run", 0)) < int(rc.get("min_blocks", 1))):
            res = restart_case(
                name, generated_root / run_id / src_name, outline, _flow(cfg, mach),
                _mesh_settings(cfg, factor),
                replace(_solver_settings(cfg, factor), max_co=co), crit,
                generated_root=generated_root / run_id, results_dir=run_dir,
                block_iterations=int(rc["block_iterations"]),
                max_blocks=int(rc["max_blocks"]), min_blocks=int(rc.get("min_blocks", 1)),
                sizing_radius_m=float(cfg["benchmark"]["radius_m"]))
        progress(f"{name}: {res.status} converged="
                 f"{res.convergence.get(GATE_FORCE_QUANTITY, {}).get('converged')}")
        return {**_row(res, mach, level, factor), "max_co": co, "source_case": src_name}

    with ThreadPoolExecutor(max_workers=int(rc.get("max_concurrent", 2))) as pool:
        rows = list(pool.map(lambda j: one(*j), jobs))
    return pd.DataFrame(rows)


def limit_cycle_table(cfg: dict, run_dir: Path) -> pd.DataFrame:
    """Amplitude and dominant period of C_D,fore over the judged window, for EVERY
    candidate solution - so the effect of the Courant number on the cycle can be read."""
    from .limit_cycle import force_cycle

    cand = collect_level_candidates(cfg, run_dir)
    rows = []
    for c in cand[cand["status"] == "OK"].itertuples():
        h = pd.read_csv(run_dir / c.case / "force_history.csv")
        rows.append({"case": c.case, "mach": c.mach, "level": c.level, "max_co": c.max_co,
                     "criterion_met": bool(c.cd_fore_converged), "drift_rel": c.cd_fore_drift_rel,
                     **force_cycle(h, GATE_FORCE_QUANTITY,
                                   int(cfg["convergence_criterion"]["window_iterations"]),
                                   float(c.max_co))})
    return pd.DataFrame(rows)


def run_limit_cycle_diagnostics(cfg: dict, run_id: str, run_dir: Path,
                                generated_root: Path) -> list[str]:
    """Field-level diagnosis (where does the cycle live?) of every ORIGINAL benchmark case
    that ran but missed the force criterion. Copies the case; the source is untouched."""
    from .limit_cycle import field_cycle, write_field_cycle

    outline = sphere_outline(float(cfg["benchmark"]["radius_m"]))
    cand = collect_level_candidates(cfg, run_dir)
    done = []
    for c in cand[(cand["status"] == "OK") & ~cand["is_restart"]
                  & ~cand["cd_fore_converged"].astype(bool)].itertuples():
        out = run_dir / f"{c.case}_cyclediag"
        if not (out / "limit_cycle_summary.json").exists():
            summary, cells, history = field_cycle(
                generated_root / run_id / c.case, generated_root / run_id / f"{c.case}_cyclediag",
                _flow(cfg, c.mach), outline.frontal_area_m2,
                float(cfg["mesh"]["wedge_angle_deg"]), float(c.max_co))
            write_field_cycle(out, summary, cells, history)
        done.append(c.case)
    return done


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


def _restart_wall_time_s(case_results_dir: Path) -> float:
    """Sum of the solver's own final 'ExecutionTime' over every archived block log (CPU
    seconds of a serial solver, so equal to wall time unless the machine is oversubscribed)."""
    total = 0.0
    for tail in sorted((case_results_dir / "log_tails").glob("log.rhoCentralFoam_block*.tail")):
        hits = re.findall(r"ExecutionTime = ([\d.]+) s", tail.read_text())
        total += float(hits[-1]) if hits else math.nan
    return total


def collect_level_candidates(cfg: dict, run_dir: Path) -> pd.DataFrame:
    """Every solution that exists for every (Mach, level): the original case first, then its
    lower-Courant restarts in DESCENDING Courant number. One row each, none hidden."""
    rc = cfg.get("courant_restarts", {})
    rows = []
    for mach in cfg["benchmark"]["mach_numbers"]:
        for i, factor in enumerate(cfg["mesh"]["refinement_factors"]):
            level = LEVEL_NAMES[i]
            names = [(case_name_for("sphere", mach, level), float(cfg["solver"]["max_co"]))]
            if rc.get("level") == level:
                names += [(restart_case_name(mach, level, co), float(co))
                          for co in sorted(rc["max_co"], reverse=True)]
            for k, (name, co) in enumerate(names):
                cached = run_dir / name / "case_result.json"
                if cached.exists():
                    res = CaseResult(**json.loads(cached.read_text()))
                    row = {**_row(res, mach, level, factor), "max_co": co, "is_restart": k > 0}
                    if k > 0:
                        # A resumed restart's case_result.json times only its last session;
                        # the archived solver logs time every block.
                        row["solver_wall_time_s"] = _restart_wall_time_s(run_dir / name)
                    rows.append(row)
    return pd.DataFrame(rows)


def collect_mesh_study(cfg: dict, run_dir: Path) -> pd.DataFrame:
    """Rebuild the mesh-study table from whatever case results exist on disk.

    One row per (Mach, level): the SOLUTION OF RECORD. Rule, fixed in code and applied
    identically to every level: the first candidate, in the order original case then
    restarts by descending Courant number, that ran and met the declared force criterion;
    if none did, the original case (so a non-converged level stays visible as such)."""
    cand = collect_level_candidates(cfg, run_dir)
    if cand.empty:
        return cand
    rows = []
    for (_, _), grp in cand.groupby(["mach", "refinement_factor"], sort=False):
        met = (grp["cd_fore_converged"].fillna(False).astype(bool)
               if "cd_fore_converged" in grp else pd.Series(False, index=grp.index))
        good = grp[(grp["status"] == "OK") & met]
        pick = (good.iloc[0] if len(good) else grp.iloc[0]).copy()
        pick["n_candidates"] = len(grp)
        rows.append(pick)
    return pd.DataFrame(rows).reset_index(drop=True)


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
            row = {"mach": mach, **r.to_dict()}
            if q == GATE_FORCE_QUANTITY:
                row.update(_limit_cycle_columns(q, g))
            rows.append(row)
    return pd.DataFrame(rows)


def _limit_cycle_columns(q: str, g: pd.DataFrame) -> dict:
    """Iterative (limit-cycle) band of each level's window-mean, kept SEPARATE from the GCI.

    ``limit_cycle_half_p2p_rel_<level>`` is half the peak-to-peak of the judged window over
    its mean: the most the instantaneous value departs from the reported mean. The
    ``*_cycle_extremes`` columns repeat the whole Celik procedure with the fine value moved
    to the top and to the bottom of its cycle (medium and coarse held), and report the
    largest resulting band; ``discretisation_plus_cycle_rel_<level>`` is the plain sum of a
    level's discretisation band and its own cycle band (not a root-sum-square: the two are
    not independent random errors). All relative to the fine / extrapolated value as in
    Celik et al."""
    out: dict = {}
    for level in ("fine", "medium", "coarse"):
        out[f"limit_cycle_half_p2p_rel_{level}"] = 0.5 * float(
            g.loc[level, f"{q}_peak_to_peak_rel"])
        out[f"criterion_met_{level}"] = bool(g.loc[level, f"{q}_converged"])
    out["fine_case_of_record"] = g.loc["fine", "case"]
    a = out["limit_cycle_half_p2p_rel_fine"] * g.loc["fine", q]
    ext = [grid_convergence_index(q, g.loc["fine", q] + s * a, g.loc["medium", q],
                                  g.loc["coarse", q], g.loc["fine", "h_m"],
                                  g.loc["medium", "h_m"], g.loc["coarse", "h_m"])
           for s in (-1.0, 0.0, 1.0)]
    out["convergence_types_at_cycle_extremes"] = "/".join(e.convergence_type for e in ext)
    out["observed_order_at_cycle_extremes_min"] = min(e.observed_order for e in ext)
    out["observed_order_at_cycle_extremes_max"] = max(e.observed_order for e in ext)
    for level in ("fine", "medium"):
        out[f"gci_{level}_at_cycle_extremes_max"] = max(getattr(e, f"gci_{level}") for e in ext)
    coarse = [SAFETY_FACTOR_THREE_GRIDS * abs(e.phi_coarse - e.phi_extrapolated)
              / abs(e.phi_extrapolated) for e in ext]
    out["band_coarse_rel"] = coarse[1]
    out["band_coarse_at_cycle_extremes_max"] = max(coarse)
    bands = {"fine": ext[1].gci_fine, "medium": ext[1].gci_medium, "coarse": coarse[1]}
    for level, band in bands.items():
        out[f"discretisation_plus_cycle_rel_{level}"] = band + out[
            f"limit_cycle_half_p2p_rel_{level}"]
    return out


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


def _demo_shape(cfg: dict) -> SimpleNamespace:
    """The three numbers M3's domain-sizing heuristics read from a capsule (duck-typed: the
    demo body is deliberately NOT the project capsule class)."""
    d = cfg["pipeline_demo"]
    return SimpleNamespace(cone_half_angle_deg=float(d["cone_half_angle_deg"]),
                           nose_radius_m=float(d["nose_radius_m"]),
                           diameter_m=float(d["diameter_m"]))


def demo_attempt_names(cfg: dict) -> list[str]:
    d = cfg["pipeline_demo"]
    base = case_name_for("capsuledemo", d["mach"], f"x{int(d['refinement_factor'])}")
    dp = load_config(REPO_ROOT / d["shock_clearance"]["design_points_config"])
    n_retry = int(dp["acceptance"]["domain_retry"]["max_retries"])
    return [base] + [f"{base}_a{k}" for k in range(1, n_retry + 2)]


def demo_isolation_name(cfg: dict) -> str:
    return demo_attempt_names(cfg)[0] + "_isolate_startup"


def run_demo_isolation(cfg: dict, run_id: str, run_dir: Path, generated_root: Path) -> dict:
    """Spec §36 'isolate the reason': attempt 1 changes TWO things relative to the failed
    attempt 0 (domain sizing and the first-order start). This case changes only ONE - it
    keeps attempt 0's sphere-sized domain and adds the first-order start - so the two
    candidate causes can be told apart. Run only if attempt 0 did not end OK."""
    d = cfg["pipeline_demo"]
    dp = load_config(REPO_ROOT / d["shock_clearance"]["design_points_config"])
    factor = int(d["refinement_factor"])
    first = run_dir / demo_attempt_names(cfg)[0] / "case_result.json"
    if not first.exists() or json.loads(first.read_text())["status"] == "OK":
        return {}
    res = _run_or_load(
        demo_isolation_name(cfg), run_dir, outline=demo_outline(cfg),
        flow=_flow(cfg, d["mach"]), mesh_settings=_mesh_settings(cfg, factor),
        solver=_solver_settings(cfg, factor),
        criterion=ConvergenceCriterion(**cfg["convergence_criterion"]),
        generated_root=generated_root / run_id,
        startup_first_order_iterations=int(
            dp["startup"]["first_order_iterations_per_refinement_factor"]) * factor)
    return {"case": res.case_name, "status": res.status, "failure_reason": res.failure_reason,
            "what_differs_from_attempt_0": "first-order start only; same domain"}


def collect_pipeline_demo(cfg: dict, run_dir: Path) -> pd.DataFrame | None:
    """Every demo attempt on disk, in order, each judged by M3's acceptance rules (ran;
    force criterion; supersonic outflow; bow shock clear of the inflow boundary)."""
    from .design_points import assess_case  # design_points imports this module

    d = cfg["pipeline_demo"]
    dp = load_config(REPO_ROOT / d["shock_clearance"]["design_points_config"])
    flow, factor = _flow(cfg, d["mach"]), int(d["refinement_factor"])
    rows = []
    for k, name in enumerate(demo_attempt_names(cfg)):
        cached = run_dir / name / "case_result.json"
        if not cached.exists():
            continue
        res = CaseResult(**json.loads(cached.read_text()))
        verdict = assess_case(res, flow, dp["acceptance"])
        rec = run_dir / name / "dictionaries" / "aether_case.yaml"
        mesh = yaml.safe_load(rec.read_text())["mesh"] if rec.exists() else {}
        rows.append({**_row(res, float(d["mach"]), f"x{factor}", factor), "attempt": k,
                     "sizing_radius_m": mesh.get("sizing_radius_m"),
                     "upstream_axis_x_m": mesh.get("upstream_axis_x_m"),
                     "standoff_margin": mesh.get("settings", {}).get("standoff_margin"),
                     "asymptote_margin_deg": mesh.get("settings", {}).get(
                         "asymptote_margin_deg"),
                     "verdict": verdict["verdict"], "reasons": " | ".join(verdict["reasons"]),
                     "shock_clearance_ok": verdict["shock_clearance_ok"],
                     "outer_outlet_mach_deficit_rel": verdict.get(
                         "outer_outlet_mach_deficit_rel")})
    return pd.DataFrame(rows) if rows else None


def run_pipeline_demo(cfg: dict, run_id: str, run_dir: Path,
                      generated_root: Path) -> pd.DataFrame:
    """One capsule-like body through the whole pipeline, shock clearance handled.

    Attempt 0 is the body in the domain M2 sizes for a SPHERE (nose-radius Billig sizing).
    If that attempt does not end USABLE, the body is re-run with the machinery M3 built for
    exactly this (NR-19, NR-20; ``design_points.py``): blunt-cone domain sizing, a
    first-order start, and automatic domain enlargement while the clearance checks fail.
    Every attempt is a separate case and a separate row; nothing is overwritten."""
    from .design_points import (
        USABLE,
        asymptote_margin_deg,
        domain_sizing_radius_m,
    )

    d = cfg["pipeline_demo"]
    dp = load_config(REPO_ROOT / d["shock_clearance"]["design_points_config"])
    retry = dp["acceptance"]["domain_retry"]
    factor = int(d["refinement_factor"])
    flow, shape, names = _flow(cfg, d["mach"]), _demo_shape(cfg), demo_attempt_names(cfg)
    common = dict(outline=demo_outline(cfg), flow=flow, solver=_solver_settings(cfg, factor),
                  criterion=ConvergenceCriterion(**cfg["convergence_criterion"]),
                  generated_root=generated_root / run_id)
    base_mesh = _mesh_settings(cfg, factor)
    _run_or_load(names[0], run_dir, mesh_settings=base_mesh, **common)
    sized = replace(base_mesh, asymptote_margin_deg=asymptote_margin_deg(
        shape, flow.mach, flow.gamma, dp["domain_sizing"], base_mesh.asymptote_margin_deg))
    n_startup = int(dp["startup"]["first_order_iterations_per_refinement_factor"]) * factor
    for k, name in enumerate(names[1:]):
        table = collect_pipeline_demo(cfg, run_dir)
        if table["verdict"].iloc[-1] == USABLE:
            break
        mesh = replace(
            sized,
            standoff_margin=sized.standoff_margin * float(retry["standoff_margin_factor"]) ** k,
            asymptote_margin_deg=sized.asymptote_margin_deg
            + k * float(retry["asymptote_margin_add_deg"]))
        _run_or_load(name, run_dir, mesh_settings=mesh,
                     sizing_radius_m=domain_sizing_radius_m(shape, dp["domain_sizing"]),
                     startup_first_order_iterations=n_startup, **common)
    return collect_pipeline_demo(cfg, run_dir)


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
                bench: pd.DataFrame, demo: pd.DataFrame | None,
                candidates: pd.DataFrame | None = None) -> dict:
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
    if candidates is not None and len(candidates):
        # Every solution that exists, including the ones NOT of record, so that a level
        # which needed a restart to meet the criterion can never look as if it had not.
        keep = [c for c in ("case", "mach", "level", "max_co", "is_restart", "status",
                            "cd_fore", "cd_fore_converged", "cd_fore_peak_to_peak_rel",
                            "cd_fore_drift_rel", "n_iterations") if c in candidates]
        cond2_detail["all_candidate_solutions"] = candidates[keep].to_dict("records")
        cond2_detail["solutions_of_record"] = study["case"].tolist()
        cond2_detail["criterion"] = dict(cfg["convergence_criterion"])

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
        # last row == last attempt; earlier attempts are kept in pipeline_demo.csv
        "pipeline_demo_status": (demo["status"].iloc[-1] if demo is not None and len(demo)
                                 else "NOT_RUN"),
    }


def write_tables(run_dir: Path, **tables: pd.DataFrame | dict) -> None:
    for name, obj in tables.items():
        if isinstance(obj, pd.DataFrame):
            obj.to_csv(run_dir / f"{name}.csv", index=False)
        else:
            with open(run_dir / f"{name}.json", "w") as fh:
                json.dump(obj, fh, indent=2, default=str)
