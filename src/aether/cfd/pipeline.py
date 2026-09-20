"""The automated case pipeline (spec §16):

    outline -> domain -> mesh -> checkMesh -> solver -> convergence -> postprocess -> metrics

One call, :func:`run_case`, takes ANY axisymmetric outline and a freestream condition and
returns a :class:`CaseResult`. Heavy field data stays in ``cfd/generated/<case>``; the
small, citable artefacts (dictionaries, log tails, force history, line and surface samples,
metrics) are copied to ``results/<milestone>/<run-id>/<case>/``.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from .case import (
    FlowCondition,
    SolverSettings,
    set_end_iteration,
    set_max_courant,
    write_case,
)
from .mesh import MeshSettings, build_mesh_plan
from .outline import Outline
from .postprocess import (
    ConvergenceCriterion,
    ConvergenceResult,
    assess_convergence,
    force_coefficient_history,
    outlet_min_mach,
    read_body_pressure,
    read_stagnation_line,
    shock_metrics,
    stagnation_pressure_pa,
)
from .runner import StepResult, parse_check_mesh, run_foam, set_patch_type

LOG_TAIL_LINES = 60


@dataclass
class CaseResult:
    case_name: str
    case_dir: str
    status: str
    """'OK' | 'MESH_FAILED' | 'SOLVER_FAILED' | 'POSTPROCESS_FAILED'."""
    failure_reason: str = ""
    steps: list[dict] = field(default_factory=list)
    mesh_quality: dict = field(default_factory=dict)
    n_cells: int = 0
    representative_cell_size_m: float = float("nan")
    solver_wall_time_s: float = float("nan")
    total_wall_time_s: float = float("nan")
    metrics: dict = field(default_factory=dict)
    convergence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _tail(path: Path, n: int = LOG_TAIL_LINES) -> str:
    if not path.exists():
        return ""
    return "\n".join(path.read_text(errors="replace").splitlines()[-n:]) + "\n"


def run_case(
    case_name: str,
    outline: Outline,
    flow: FlowCondition,
    mesh_settings: MeshSettings,
    solver: SolverSettings,
    criterion: ConvergenceCriterion,
    generated_root: Path,
    results_dir: Path,
    sizing_radius_m: float | None = None,
    solver_timeout_s: float = 6 * 3600.0,
    startup_first_order_iterations: int = 0,
) -> CaseResult:
    """Run one case end to end. Never raises on a CFD failure: the failure IS the result.

    ``startup_first_order_iterations`` (default 0 == the M2 behaviour, unchanged): run that
    many iterations with first-order (upwind) reconstruction before switching to the
    declared limiter. Added at M3 because an impulsive start at Mach 20 drove the
    second-order scheme to a negative temperature (NR-19). It changes the path to the
    steady state, not the scheme the steady state is converged and judged with.
    """
    case_dir = Path(generated_root) / case_name
    out_dir = Path(results_dir) / case_name
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = build_mesh_plan(outline, flow.mach, sizing_radius_m, mesh_settings)
    write_case(case_dir, plan, flow, solver)
    result = CaseResult(case_name, str(case_dir), "OK", n_cells=plan.n_cells,
                        representative_cell_size_m=plan.representative_cell_size_m)
    steps: list[StepResult] = []

    def step(name: str, command: str, timeout_s: float = 1800.0) -> bool:
        s = run_foam(case_dir, name, command, timeout_s)
        steps.append(s)
        return s.ok

    def finish(status: str, reason: str = "") -> CaseResult:
        result.status, result.failure_reason = status, reason
        result.steps = [s.to_dict() for s in steps]
        result.total_wall_time_s = sum(s.wall_time_s for s in steps)
        _archive(case_dir, out_dir)
        with open(out_dir / "case_result.json", "w") as fh:
            json.dump(result.to_dict(), fh, indent=2, default=str)
        return result

    # -- mesh ---------------------------------------------------------------------------
    if not (step("blockMesh", "blockMesh") and step("extrudeMesh", "extrudeMesh")):
        return finish("MESH_FAILED", f"{steps[-1].name} returned {steps[-1].returncode}")
    set_patch_type(case_dir, "axis", "empty")
    step("checkMesh", "checkMesh")
    result.mesh_quality = parse_check_mesh((case_dir / "log.checkMesh").read_text())
    if not result.mesh_quality["mesh_ok"]:
        return finish("MESH_FAILED", "checkMesh did not report 'Mesh OK.'")

    # -- solve --------------------------------------------------------------------------
    if not step("setFields", "setFields"):
        return finish("SOLVER_FAILED", "setFields failed")
    def solve(tag: str) -> bool:
        if solver.n_ranks > 1:
            return (step(f"decomposePar{tag}", "decomposePar -force")
                    and step(f"rhoCentralFoam{tag}",
                             f"mpirun -np {solver.n_ranks} rhoCentralFoam -parallel",
                             solver_timeout_s)
                    and step(f"reconstructPar{tag}", "reconstructPar -latestTime"))
        return step(f"rhoCentralFoam{tag}", "rhoCentralFoam", solver_timeout_s)

    def force_converged() -> bool:
        h = force_coefficient_history(case_dir, flow, outline.frontal_area_m2,
                                      mesh_settings.wedge_angle_deg)
        return assess_convergence(h, "cd_total", criterion).converged

    ok = True
    if startup_first_order_iterations > 0:
        schemes = case_dir / "system" / "fvSchemes"
        declared = schemes.read_text()
        schemes.write_text(declared.replace(f"{solver.limiter}V;", "upwind;")
                           .replace(f"{solver.limiter};", "upwind;"))
        set_end_iteration(case_dir, int(startup_first_order_iterations))
        ok = solve("_startup")
        schemes.write_text(declared)
        set_end_iteration(case_dir, solver.n_iterations)
    ok = ok and solve("")
    n_end, n_ext = solver.n_iterations, 0
    while ok and n_ext < solver.max_extensions and not force_converged():
        n_ext += 1
        n_end += int(round(solver.extension_fraction * solver.n_iterations))
        set_end_iteration(case_dir, n_end)
        ok = solve(f"_ext{n_ext}")
    result.solver_wall_time_s = sum(s.wall_time_s for s in steps
                                    if s.name.startswith("rhoCentralFoam"))
    if not ok:
        return finish("SOLVER_FAILED",
                      f"{steps[-1].name} returned {steps[-1].returncode}"
                      + (" (timeout)" if steps[-1].timed_out else ""))

    return _postprocess(case_dir, out_dir, case_name, outline, flow, mesh_settings,
                        plan.body_patches, plan.n_cells, plan.representative_cell_size_m,
                        abs(plan.upstream_axis_x_m), solver.n_iterations, n_ext,
                        startup_first_order_iterations, criterion, result, step, finish)


def _postprocess(case_dir, out_dir, case_name, outline, flow, mesh_settings, body_patches,
                 n_cells, h_m, upstream_distance_m, n_iterations_planned, n_ext,
                 startup_first_order_iterations, criterion, result, step, finish,
                 extra_metrics: dict | None = None) -> CaseResult:
    """Sample the latest time, compute the metrics, judge convergence, archive. Shared by
    :func:`run_case` and :func:`restart_case` so both are judged by the same code."""
    # -- postprocess --------------------------------------------------------------------
    if not (step("sampleLine", "postProcess -func sampleLine -latestTime")
            and step("sampleBody", "postProcess -func sampleBody -latestTime")
            and step("sampleOutlet", "postProcess -func sampleOutlet -latestTime")):
        return finish("POSTPROCESS_FAILED", "sampling failed")
    try:
        history = force_coefficient_history(case_dir, flow, outline.frontal_area_m2,
                                            mesh_settings.wedge_angle_deg)
        line = read_stagnation_line(case_dir)
        body = read_body_pressure(case_dir)
        shock = shock_metrics(line, flow)
        p0 = stagnation_pressure_pa(body, line)
        min_mach_out = outlet_min_mach(case_dir, flow)
    except (FileNotFoundError, ValueError) as exc:
        return finish("POSTPROCESS_FAILED", str(exc))

    history.to_csv(out_dir / "force_history.csv", index=False)
    line.to_csv(out_dir / "stagnation_line.csv", index=False)
    body["cp"] = (body["p_pa"] - flow.pressure_pa) / flow.dynamic_pressure_pa
    body.to_csv(out_dir / "body_pressure.csv", index=False)

    quantities = ["cd_total", "cd_fore"] + (["cd_aft"] if "body_aft" in body_patches
                                            else [])
    conv = {q: assess_convergence(history, q, criterion) for q in quantities}
    result.convergence = {q: c.to_dict() for q, c in conv.items()}
    result.metrics = {
        "cd_total": conv["cd_total"].mean,
        "cd_fore": conv["cd_fore"].mean,
        "cd_aft": conv["cd_aft"].mean if "cd_aft" in conv else float("nan"),
        "mesh_extent": mesh_settings.extent,
        "outlet_min_mach": min_mach_out,
        "cd_total_last_iteration": float(history["cd_total"].iloc[-1]),
        "standoff_m": shock.standoff_m,
        "standoff_over_max_radius": shock.standoff_m / outline.max_radius_m,
        # 1 - standoff / (distance from nose to the inflow boundary on the axis). Near 0 means
        # the bow shock is touching the fixed-value inflow boundary and the case is invalid.
        "upstream_clearance_fraction": 1.0 - shock.standoff_m / upstream_distance_m,
        "shock_thickness_m": shock.shock_thickness_m,
        "shock_thickness_cells": shock.shock_thickness_cells,
        "stagnation_line_cell_size_at_shock_m": shock.local_cell_size_m,
        "p_stag_wall_face_pa": p0["wall_face"],
        "p_stag_line_extrapolated_pa": p0["line_extrapolated"],
        "p_max_on_body_pa": p0["max_on_body"],
        "p_stag_over_p_inf": p0["line_extrapolated"] / flow.pressure_pa,
        "final_mean_abs_drho_dtau": float(history["mean_abs_drho_dtau_kg_m3_s"].iloc[-1]),
        "initial_mean_abs_drho_dtau": float(history["mean_abs_drho_dtau_kg_m3_s"].iloc[0]),
        "n_iterations": int(history["iteration"].iloc[-1]),
        "n_iterations_planned": n_iterations_planned,
        "n_extensions": n_ext,
    }
    if startup_first_order_iterations > 0:      # key absent == M2 behaviour
        result.metrics["startup_first_order_iterations"] = int(startup_first_order_iterations)
    result.metrics.update(extra_metrics or {})
    pd.DataFrame([{**{"case": case_name, "mach": flow.mach, "n_cells": n_cells,
                      "h_m": h_m}, **result.metrics}]
                 ).to_csv(out_dir / "metrics.csv", index=False)
    return finish("OK")


def _latest_time_dir(case_dir: Path) -> Path:
    times = [d for d in Path(case_dir).iterdir()
             if d.is_dir() and d.name.replace(".", "", 1).isdigit() and float(d.name) > 0]
    if not times:
        raise FileNotFoundError(f"no written solution under {case_dir}")
    return max(times, key=lambda d: float(d.name))


def restart_case(
    case_name: str,
    source_case_dir: Path,
    outline: Outline,
    flow: FlowCondition,
    mesh_settings: MeshSettings,
    solver: SolverSettings,
    criterion: ConvergenceCriterion,
    generated_root: Path,
    results_dir: Path,
    block_iterations: int,
    max_blocks: int,
    sizing_radius_m: float | None = None,
    solver_timeout_s: float = 6 * 3600.0,
    min_blocks: int = 1,
    consecutive_passes: int = 1,
) -> CaseResult:
    """Continue a FINISHED case under different numerical controls, as a NEW case.

    Spec §36 step 6 ("check Courant/time step") applied to a case that ran but did not meet
    the force criterion: the source case's mesh and final solution are copied into
    ``generated_root/case_name``, ``solver.max_co`` replaces the source's Courant limit, and
    the solver is advanced in blocks of ``block_iterations`` until the UNCHANGED ``criterion``
    is met or ``max_blocks`` blocks have run. The source case is never modified. The force
    history of the new case starts at the source's last iteration, so the judged window
    contains only iterations computed under the new controls (enforced: at least one full
    window must have been computed here before the criterion can be met).

    ``min_blocks`` makes the test STRICTER, never looser: the run does not stop before that
    many blocks even if the criterion is already met, so a pass has to be seen in
    ``min_blocks`` separate windows, and the verdict is always the one at the end of the
    last block run. ``consecutive_passes`` (default 1 == the M2 behaviour, unchanged) is
    stricter again: the run stops early only once the criterion has been met at the end of
    that many blocks IN A ROW; a case that never does runs to ``max_blocks`` and is judged
    there like any other. Added for M3's capsule restarts (NR-27), where a slowly drifting
    case met the criterion in one window after one that had not. Resumable: if the new
    case directory already holds solutions, it continues from its own latest time. The
    check after every block is appended to ``restart_blocks.json`` next to the case result.
    """
    source_case_dir = Path(source_case_dir)
    case_dir = Path(generated_root) / case_name
    out_dir = Path(results_dir) / case_name
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = build_mesh_plan(outline, flow.mach, sizing_radius_m, mesh_settings)
    result = CaseResult(case_name, str(case_dir), "OK", n_cells=plan.n_cells,
                        representative_cell_size_m=plan.representative_cell_size_m)
    steps: list[StepResult] = []

    def step(name: str, command: str, timeout_s: float = 1800.0) -> bool:
        s = run_foam(case_dir, name, command, timeout_s)
        steps.append(s)
        return s.ok

    def finish(status: str, reason: str = "") -> CaseResult:
        result.status, result.failure_reason = status, reason
        result.steps = [s.to_dict() for s in steps]
        result.total_wall_time_s = sum(s.wall_time_s for s in steps)
        _archive(case_dir, out_dir)
        with open(out_dir / "case_result.json", "w") as fh:
            json.dump(result.to_dict(), fh, indent=2, default=str)
        return result

    source_latest = _latest_time_dir(source_case_dir)
    start_iteration = int(float(source_latest.name))
    if not case_dir.exists() or not any(case_dir.iterdir()):
        case_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("constant", "system", "0.orig", "0"):
            shutil.copytree(source_case_dir / sub, case_dir / sub)
        shutil.copytree(source_latest, case_dir / source_latest.name)
        shutil.copy2(source_case_dir / "log.checkMesh", case_dir / "log.checkMesh")
        (case_dir / "case.foam").write_text("")
        record = yaml.safe_load((source_case_dir / "aether_case.yaml").read_text())
        source_max_co = record.get("solver_settings", {}).get("max_co")
        record["solver_settings"] = asdict(solver)
        record["restart"] = {
            "source_case_dir": str(source_case_dir), "source_iteration": start_iteration,
            "source_max_co": source_max_co,
            "block_iterations": block_iterations, "max_blocks": max_blocks,
            "reason": "spec §36 step 6: lower Courant limit on a case that ran but did not "
                      "meet the declared force criterion; criterion unchanged"}
        with open(case_dir / "aether_case.yaml", "w") as fh:
            yaml.safe_dump(record, fh, sort_keys=False)
    set_max_courant(case_dir, solver.max_co)
    result.mesh_quality = parse_check_mesh((case_dir / "log.checkMesh").read_text())

    def check() -> ConvergenceResult:
        h = force_coefficient_history(case_dir, flow, outline.frontal_area_m2,
                                      mesh_settings.wedge_angle_deg)
        return assess_convergence(h, "cd_total", criterion)

    blocks_file = out_dir / "restart_blocks.json"
    blocks: list[dict] = json.loads(blocks_file.read_text()) if blocks_file.exists() else []
    n_now = int(float(_latest_time_dir(case_dir).name))
    ok, n_done = True, (n_now - start_iteration) // block_iterations
    def passed_in_a_row() -> bool:
        tail = blocks[-consecutive_passes:]
        return len(tail) == consecutive_passes and all(b["converged"] for b in tail)

    while ok and n_done < max_blocks:
        if (n_done >= min_blocks and n_now - start_iteration >= criterion.window_iterations
                and check().converged and (consecutive_passes <= 1 or passed_in_a_row())):
            break
        n_done += 1
        n_now = start_iteration + n_done * block_iterations
        set_end_iteration(case_dir, n_now)
        ok = step(f"rhoCentralFoam_block{n_done}", "rhoCentralFoam", solver_timeout_s)
        if ok:
            c = check()
            blocks.append({"end_iteration": n_now, "mean": c.mean,
                           "peak_to_peak_rel": c.peak_to_peak_rel, "drift_rel": c.drift_rel,
                           "converged": c.converged})
            with open(blocks_file, "w") as fh:
                json.dump(blocks, fh, indent=2)
    result.solver_wall_time_s = sum(s.wall_time_s for s in steps
                                    if s.name.startswith("rhoCentralFoam"))
    if not ok:
        return finish("SOLVER_FAILED", f"{steps[-1].name} returned {steps[-1].returncode}"
                      + (" (timeout)" if steps[-1].timed_out else ""))
    return _postprocess(case_dir, out_dir, case_name, outline, flow, mesh_settings,
                        plan.body_patches, plan.n_cells, plan.representative_cell_size_m,
                        abs(plan.upstream_axis_x_m), block_iterations * max_blocks, 0, 0,
                        criterion, result, step, finish,
                        extra_metrics={"restart_source_case": source_case_dir.name,
                                       "restart_source_iteration": start_iteration,
                                       "max_co": solver.max_co,
                                       "restart_blocks_run": n_done,
                                       **({"restart_consecutive_passes_required":
                                           int(consecutive_passes),
                                           "restart_passed_in_a_row": bool(passed_in_a_row())}
                                          if consecutive_passes > 1 else {})})


def _archive(case_dir: Path, out_dir: Path) -> None:
    """Copy the light-weight, citable parts of a case next to the results."""
    for sub in ("system", "constant/thermophysicalProperties", "constant/turbulenceProperties",
                "0.orig", "aether_case.yaml"):
        src = case_dir / sub
        if src.is_dir():
            shutil.copytree(src, out_dir / "dictionaries" / sub, dirs_exist_ok=True)
        elif src.exists():
            dst = out_dir / "dictionaries" / sub
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    logs = out_dir / "log_tails"
    logs.mkdir(exist_ok=True)
    for log in sorted(case_dir.glob("log.*")):
        (logs / f"{log.name}.tail").write_text(_tail(log))
    check = case_dir / "log.checkMesh"
    if check.exists():
        shutil.copy2(check, logs / "log.checkMesh.full")
