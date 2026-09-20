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

from .case import FlowCondition, SolverSettings, set_end_iteration, write_case
from .mesh import MeshSettings, build_mesh_plan
from .outline import Outline
from .postprocess import (
    ConvergenceCriterion,
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

    quantities = ["cd_total", "cd_fore"] + (["cd_aft"] if "body_aft" in plan.body_patches
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
        "upstream_clearance_fraction": 1.0 - shock.standoff_m / abs(plan.upstream_axis_x_m),
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
        "n_iterations_planned": solver.n_iterations,
        "n_extensions": n_ext,
    }
    if startup_first_order_iterations > 0:      # key absent == M2 behaviour
        result.metrics["startup_first_order_iterations"] = int(startup_first_order_iterations)
    pd.DataFrame([{**{"case": case_name, "mach": flow.mach, "n_cells": plan.n_cells,
                      "h_m": plan.representative_cell_size_m}, **result.metrics}]
                 ).to_csv(out_dir / "metrics.csv", index=False)
    return finish("OK")


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
