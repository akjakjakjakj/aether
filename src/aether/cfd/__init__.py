"""Fidelity-1 CFD: automated rhoCentralFoam pipeline for axisymmetric blunt bodies.

GATED by G4 (spec §17). Nothing here may feed the optimisation loop until the validation
matrix says so; see docs/validation/M2_model_form_limits.md for what it may be used for.
"""

from .case import FlowCondition, SolverSettings, write_case
from .gci import GciResult, grid_convergence_index
from .mesh import MeshSettings, build_mesh_plan
from .outline import Outline, make_outline, sphere_cone_capsule_outline, sphere_outline
from .pipeline import CaseResult, run_case
from .postprocess import ConvergenceCriterion
from .runner import openfoam_available, openfoam_version

__all__ = [
    "CaseResult", "ConvergenceCriterion", "FlowCondition", "GciResult", "MeshSettings",
    "Outline", "SolverSettings", "build_mesh_plan", "grid_convergence_index", "make_outline",
    "openfoam_available", "openfoam_version", "run_case", "sphere_cone_capsule_outline",
    "sphere_outline", "write_case",
]
