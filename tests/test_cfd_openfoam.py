"""Gate G4 - checks that need a real OpenFOAM install. Skipped cleanly when it is absent.

Meshing only (seconds). Solver runs are the job of `make cfd-validate`, not of pytest.
"""

import pytest

from src.aether.cfd.case import FlowCondition, SolverSettings, write_case
from src.aether.cfd.mesh import MeshSettings, build_mesh_plan
from src.aether.cfd.outline import sphere_cone_capsule_outline, sphere_outline
from src.aether.cfd.runner import (
    openfoam_available,
    openfoam_version,
    parse_check_mesh,
    run_foam,
    set_patch_type,
)

pytestmark = pytest.mark.skipif(not openfoam_available(),
                                reason="OpenFOAM launcher 'openfoam' not on PATH")


def test_version_is_reported():
    assert openfoam_version().startswith("v")


@pytest.mark.parametrize("outline, mach, extent", [
    (sphere_outline(0.5), 3.0, "forebody"),
    (sphere_outline(0.5), 3.0, "full"),
    (sphere_cone_capsule_outline(0.6, 1.2, 60.0, 0.06, 30.0, 0.3), 6.0, "forebody"),
])
def test_generated_mesh_passes_checkmesh_as_a_wedge(tmp_path, outline, mach, extent):
    st = MeshSettings(n_body_cells_base=32, n_radial_cells_base=24, extent=extent)
    plan = build_mesh_plan(outline, mach, settings=st)
    case = write_case(tmp_path / "case", plan, FlowCondition(mach, 1000.0, 220.0),
                      SolverSettings(n_iterations=10))
    assert run_foam(case, "blockMesh", "blockMesh", 120).ok
    assert run_foam(case, "extrudeMesh", "extrudeMesh", 120).ok
    set_patch_type(case, "axis", "empty")
    assert run_foam(case, "checkMesh", "checkMesh", 120).ok
    log = (case / "log.checkMesh").read_text()
    q = parse_check_mesh(log)
    assert q["mesh_ok"], log[-1500:]
    assert q["n_cells"] == plan.n_cells
    assert "Wedge front with angle 2.5 degrees" in log


def test_a_crashing_command_is_a_failed_step_not_a_hang(tmp_path):
    (tmp_path / "system").mkdir()
    res = run_foam(tmp_path, "blockMesh", "blockMesh", 60)     # no controlDict: must fail
    assert not res.ok and not res.timed_out
