"""Write a complete rhoCentralFoam case directory from templates plus a mesh plan.

Pure file generation: nothing here needs OpenFOAM, which is what makes it testable on a
machine without it.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from ..utils.constants import GAMMA_AIR, R_AIR, R_UNIVERSAL_USSA76
from ..utils.run import REPO_ROOT
from .mesh import MeshPlan, block_mesh_dict

TEMPLATE_DIR = REPO_ROOT / "cfd" / "templates" / "rhoCentralFoam_axisym"
_PLACEHOLDER = re.compile(r"@([A-Z0-9_]+)@")


@dataclass(frozen=True)
class FlowCondition:
    """Freestream state of a calorically perfect gas. SI throughout."""

    mach: float
    pressure_pa: float
    temperature_k: float
    gamma: float = GAMMA_AIR
    gas_constant_j_kgk: float = R_AIR

    @property
    def speed_of_sound_m_s(self) -> float:
        return math.sqrt(self.gamma * self.gas_constant_j_kgk * self.temperature_k)

    @property
    def velocity_m_s(self) -> float:
        return self.mach * self.speed_of_sound_m_s

    @property
    def density_kg_m3(self) -> float:
        return self.pressure_pa / (self.gas_constant_j_kgk * self.temperature_k)

    @property
    def dynamic_pressure_pa(self) -> float:
        return 0.5 * self.gamma * self.pressure_pa * self.mach**2

    @property
    def cp_j_kgk(self) -> float:
        return self.gamma * self.gas_constant_j_kgk / (self.gamma - 1.0)

    @property
    def mol_weight_g_mol(self) -> float:
        return 1000.0 * R_UNIVERSAL_USSA76 / self.gas_constant_j_kgk


@dataclass(frozen=True)
class SolverSettings:
    """Numerical controls. Defaults are the values declared in configs/cfd_validation.yaml."""

    n_iterations: int = 6000
    max_co: float = 0.5
    rdeltat_smoothing: float = 0.02
    flux_scheme: str = "Kurganov"
    limiter: str = "vanLeer"
    force_interval: int = 5
    n_ranks: int = 1
    dynamic_viscosity_pa_s: float = 0.0   # 0 => Euler equations (see ASSUMPTIONS A-CFD-2)
    prandtl: float = 1.0
    # Run-until-converged: if the declared force criterion is not met after n_iterations,
    # continue from the latest time in blocks of extension_fraction * n_iterations, at most
    # max_extensions times. The CRITERION never changes; only how long we wait for it.
    max_extensions: int = 0
    extension_fraction: float = 0.5


_FORCES_AFT_BLOCK = """    forcesAft
    {
        $forcesFore;
        patches         (body_aft);
    }"""


def set_end_iteration(case_dir: Path, n_iterations: int) -> None:
    """Move endTime (and the single field write) of an existing case to ``n_iterations``."""
    path = Path(case_dir) / "system" / "controlDict"
    text = path.read_text()
    text, n1 = re.subn(r"(?m)^endTime\s+\d+;", f"endTime         {n_iterations};", text)
    text, n2 = re.subn(r"(?m)^writeInterval\s+\d+;", f"writeInterval   {n_iterations};", text)
    if (n1, n2) != (1, 1):
        raise RuntimeError(f"could not update endTime/writeInterval in {path}")
    path.write_text(text)


def render_template(text: str, values: dict[str, object]) -> str:
    """Substitute @NAME@ placeholders. An unfilled placeholder is an error, not a default."""
    def sub(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(f"template placeholder @{key}@ has no value")
        v = values[key]
        return f"{v:.12g}" if isinstance(v, float) else str(v)
    return _PLACEHOLDER.sub(sub, text)


def template_values(plan: MeshPlan, flow: FlowCondition, solver: SolverSettings) -> dict:
    r_ref = plan.outline.max_radius_m
    return {
        "N_ITERATIONS": solver.n_iterations,
        "WRITE_INTERVAL": solver.n_iterations,
        "MAX_CO": float(solver.max_co),
        "RDELTAT_SMOOTHING": float(solver.rdeltat_smoothing),
        "FORCE_INTERVAL": solver.force_interval,
        "FLUX_SCHEME": solver.flux_scheme,
        "LIMITER": solver.limiter,
        "WEDGE_ANGLE_DEG": float(plan.settings.wedge_angle_deg),
        "N_RANKS": solver.n_ranks,
        "P_INF": float(flow.pressure_pa),
        "T_INF": float(flow.temperature_k),
        "U_INF": float(flow.velocity_m_s),
        "MOL_WEIGHT_G_MOL": float(flow.mol_weight_g_mol),
        "CP_J_KGK": float(flow.cp_j_kgk),
        "MU_PA_S": float(solver.dynamic_viscosity_pa_s),
        "PRANDTL": float(solver.prandtl),
        "X_UPSTREAM": float(plan.upstream_axis_x_m + 1e-6 * r_ref),
        "X_NOSE": float(-1e-9 * r_ref),
        "R_SAMPLE": float(1e-4 * r_ref),
        "BODY_PATCHES": " ".join(plan.body_patches),
        "FORCES_AFT_BLOCK": _FORCES_AFT_BLOCK if "body_aft" in plan.body_patches else "",
        "X_WAKE_START": float(plan.outline.x_m[int(plan.outline.r_m.argmax())]),
        "R_WAKE": float(1.2 * r_ref),
    }


def write_case(case_dir: str | Path, plan: MeshPlan, flow: FlowCondition,
               solver: SolverSettings, template_dir: Path = TEMPLATE_DIR) -> Path:
    """Create ``case_dir`` with every dictionary needed to mesh and run the case.

    Also writes ``aether_case.yaml``: the machine-readable record of solver, equations,
    gas model, boundary conditions and mesh that spec §16 requires for every case.
    """
    case_dir = Path(case_dir)
    if case_dir.exists() and any(case_dir.iterdir()):
        raise FileExistsError(f"{case_dir} already exists and is not empty")
    values = template_values(plan, flow, solver)
    for src in sorted(template_dir.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(template_dir)
        text = render_template(src.read_text(), values)
        # 0.orig is kept pristine (setFields rewrites 0/U as a per-cell list).
        targets = [rel, Path("0", *rel.parts[1:])] if rel.parts[0] == "0.orig" else [rel]
        for target in targets:
            dst = case_dir / target
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text)
    (case_dir / "system" / "blockMeshDict").write_text(block_mesh_dict(plan))
    (case_dir / "case.foam").write_text("")

    inviscid = solver.dynamic_viscosity_pa_s == 0.0
    record = {
        "solver": "rhoCentralFoam",
        "equations": ("axisymmetric compressible Euler" if inviscid
                      else "axisymmetric compressible laminar Navier-Stokes"),
        "time_integration": "localEuler pseudo-time marching to steady state",
        "flux_scheme": f"{solver.flux_scheme} central-upwind, {solver.limiter} reconstruction",
        "gas_model": "calorically perfect gas, single species, no chemistry",
        "flow": {**asdict(flow),
                 "velocity_m_s": flow.velocity_m_s, "density_kg_m3": flow.density_kg_m3,
                 "dynamic_pressure_pa": flow.dynamic_pressure_pa},
        "boundary_conditions": {
            "freestream": "fixedValue p, T, U (supersonic inflow; bow shock stays inside)",
            "outlet": "zeroGradient p, T, U",
            "body_fore/body_aft": ("slip U, zeroGradient p and T" if inviscid
                                   else "see 0/ dictionaries"),
            "front/back": "wedge", "axis": "empty (collapsed by extrudeMesh)",
        },
        "mesh": {
            "generator": "blockMesh (planar strip) + extrudeMesh wedge",
            "n_body_cells": plan.n_body_cells, "n_radial_cells": plan.n_radial_cells,
            "n_cells": plan.n_cells, "n_blocks": len(plan.blocks),
            "extent": plan.settings.extent, "body_patches": list(plan.body_patches),
            "refinement_factor": plan.settings.refinement_factor,
            "representative_cell_size_m": plan.representative_cell_size_m,
            "domain_area_m2": plan.domain_area_m2,
            "outflow_x_m": plan.outflow_x_m, "upstream_axis_x_m": plan.upstream_axis_x_m,
            "sizing_radius_m": plan.sizing_radius_m,
            "settings": asdict(plan.settings),
        },
        "solver_settings": asdict(solver),
        "body": {"name": plan.outline.name, "length_m": plan.outline.length_m,
                 "max_radius_m": plan.outline.max_radius_m,
                 "frontal_area_m2": plan.outline.frontal_area_m2},
    }
    with open(case_dir / "aether_case.yaml", "w") as fh:
        yaml.safe_dump(record, fh, sort_keys=False)
    return case_dir
