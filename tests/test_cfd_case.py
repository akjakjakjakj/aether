"""Gate G4 - outline handling, mesh layout and case-dictionary generation (no OpenFOAM)."""

import re

import numpy as np
import pytest
import yaml

from src.aether.cfd.case import (
    FlowCondition,
    SolverSettings,
    render_template,
    template_values,
    write_case,
)
from src.aether.cfd.mesh import MeshSettings, block_mesh_dict, build_mesh_plan
from src.aether.cfd.outline import make_outline, sphere_cone_capsule_outline, sphere_outline
from src.aether.cfd.reference import billig_standoff_over_radius
from src.aether.cfd.runner import parse_check_mesh, set_patch_type


def _capsule():
    return sphere_cone_capsule_outline(0.6, 1.2, 60.0, 0.06, 30.0, 0.3)


def test_sphere_outline_geometry():
    o = sphere_outline(0.5)
    assert o.x_m[0] == 0.0 and o.r_m[0] == 0.0 and o.r_m[-1] == 0.0
    assert o.length_m == pytest.approx(1.0)
    assert o.max_radius_m == pytest.approx(0.5)
    assert np.allclose((o.x_m - 0.5) ** 2 + o.r_m**2, 0.25, atol=1e-12)
    assert o.arc_length_m[-1] == pytest.approx(np.pi * 0.5, rel=1e-5)


def test_capsule_outline_is_tangent_continuous_and_bounded():
    o = _capsule()
    assert o.max_radius_m == pytest.approx(0.6, abs=1e-9)
    ang = np.unwrap(np.arctan2(np.diff(o.r_m), np.diff(o.x_m)))
    fore = slice(0, int(np.argmax(o.r_m)))
    # forebody: no corner sharper than the arc discretisation step
    assert np.max(np.abs(np.diff(ang[fore]))) < np.radians(2.0)


@pytest.mark.parametrize("bad", [
    ([0, 1, 2, 3, 4], [0.1, 1, 1, 1, 0]),       # nose off the axis
    ([0, 1, 2, 3, 4], [0, 1, 0, 1, 0]),         # touches the axis mid-body
    ([0, 1, 1, 3, 4], [0, 1, 1, 1, 0]),         # repeated point
    ([0, 1, 2, 3, 4], [0, 1, -1, 1, 0]),        # negative radius
    ([0, 1, 2], [0, 1, 0]),                     # too few points
])
def test_invalid_outlines_are_rejected(bad):
    with pytest.raises(ValueError):
        make_outline(*bad)


def test_arbitrary_xr_arrays_are_accepted():
    """The contract with aether.geometry.capsule: plain (x, r) numpy arrays."""
    o = _capsule()
    plan = build_mesh_plan(make_outline(o.x_m + 3.0, o.r_m), mach=6.0)   # offset nose is fine
    assert plan.outline.x_m[0] == 0.0
    assert plan.n_cells == 80 * 60


@pytest.mark.parametrize("extent", ["forebody", "full"])
@pytest.mark.parametrize("mach", [2.0, 3.0, 6.0])
def test_domain_encloses_billig_shock_with_margin(extent, mach):
    st = MeshSettings(extent=extent)
    plan = build_mesh_plan(sphere_outline(0.5), mach, sizing_radius_m=0.5, settings=st)
    delta = billig_standoff_over_radius(mach) * 0.5
    assert plan.upstream_axis_x_m == pytest.approx(-st.standoff_margin * delta, rel=1e-9)
    for b in plan.blocks:
        assert np.all(np.isfinite(b.outer_xy))
        gap = np.hypot(*(b.outer_xy - b.body_xy[[0] * len(b.outer_xy)]).T)
        assert gap.min() > 0


def test_refinement_is_geometrically_similar_with_ratio_two():
    plans = [build_mesh_plan(sphere_outline(0.5), 3.0, 0.5, MeshSettings(refinement_factor=f))
             for f in (1, 2, 4)]
    n = [p.n_cells for p in plans]
    h = [p.representative_cell_size_m for p in plans]
    assert n[1] == 4 * n[0] and n[2] == 16 * n[0]
    assert h[0] / h[1] == pytest.approx(2.0, rel=1e-12)
    assert h[1] / h[2] == pytest.approx(2.0, rel=1e-12)
    assert plans[0].domain_area_m2 == pytest.approx(plans[2].domain_area_m2, rel=1e-12)


def test_forebody_extent_stops_at_max_radius_and_has_no_aft_patch():
    plan = build_mesh_plan(_capsule(), 6.0)
    assert plan.body_patches == ("body_fore",)
    x_max = plan.outline.x_m[int(np.argmax(plan.outline.r_m))]
    assert plan.outflow_x_m == pytest.approx(x_max)
    assert plan.blocks[-1].body_xy[-1] == pytest.approx([x_max, plan.outline.max_radius_m])
    assert plan.blocks[-1].outer_xy[-1, 0] == pytest.approx(x_max, abs=1e-9)


def test_full_extent_has_fore_and_aft_and_an_outlet_corner_on_a_block_boundary():
    plan = build_mesh_plan(sphere_outline(0.5), 3.0, 0.5, MeshSettings(extent="full"))
    assert plan.body_patches == ("body_fore", "body_aft")
    kinds = [b.outer_patch for b in plan.blocks]
    k = kinds.index("outlet")
    assert set(kinds[:k]) == {"freestream"} and set(kinds[k:]) == {"outlet"}
    assert plan.blocks[k].outer_xy[0, 0] == pytest.approx(plan.outflow_x_m)


def test_block_mesh_dict_is_structurally_valid():
    plan = build_mesh_plan(sphere_outline(0.5), 3.0, 0.5, MeshSettings(refinement_factor=2))
    text = block_mesh_dict(plan)
    assert text.count("(") == text.count(")") and text.count("{") == text.count("}")
    assert len(re.findall(r"^\s*hex ", text, flags=re.M)) == len(plan.blocks)
    n_vertices = len(re.findall(r"^    \([-\d.e+ ]+\)$", text.split("blocks")[0], flags=re.M))
    assert n_vertices == 4 * (len(plan.blocks) + 1)
    assert "(8 120 1) simpleGrading (1 4 1)" in text
    for patch in ("body_fore", "freestream", "outlet", "axis", "front", "back"):
        assert re.search(rf"^\s*{patch}\s*$", text, flags=re.M)
    labels = [int(v) for h in re.findall(r"hex \(([\d ]+)\)", text) for v in h.split()]
    assert max(labels) == n_vertices - 1


def test_flow_condition_is_self_consistent():
    f = FlowCondition(mach=3.0, pressure_pa=1000.0, temperature_k=220.0)
    assert f.velocity_m_s / f.speed_of_sound_m_s == pytest.approx(3.0)
    assert 0.5 * f.density_kg_m3 * f.velocity_m_s**2 == pytest.approx(f.dynamic_pressure_pa)
    assert f.cp_j_kgk * (1 - 1 / f.gamma) == pytest.approx(f.gas_constant_j_kgk)
    assert f.mol_weight_g_mol == pytest.approx(28.9644, rel=1e-6)


def test_unfilled_placeholder_is_an_error():
    with pytest.raises(KeyError):
        render_template("maxCo @MAX_CO@; endTime @MISSING@;", {"MAX_CO": 0.5})


def test_write_case_produces_complete_consistent_dictionaries(tmp_path):
    flow = FlowCondition(3.0, 1000.0, 220.0)
    plan = build_mesh_plan(sphere_outline(0.5), 3.0, 0.5)
    case = write_case(tmp_path / "case", plan, flow, SolverSettings(n_iterations=1234))
    for rel in ("system/controlDict", "system/fvSchemes", "system/fvSolution",
                "system/blockMeshDict", "system/extrudeMeshDict", "system/setFieldsDict",
                "system/sampleLine", "system/sampleBody", "system/sampleOutlet",
                "constant/thermophysicalProperties", "constant/turbulenceProperties",
                "0/p", "0/T", "0/U", "0.orig/U", "aether_case.yaml"):
        text = (case / rel).read_text()
        assert "@" not in text.replace("@ ", ""), f"unfilled placeholder in {rel}"
        assert text.count("{") == text.count("}"), rel
    ctrl = (case / "system/controlDict").read_text()
    assert re.search(r"endTime\s+1234;", ctrl)
    assert "forcesAft" not in ctrl                       # forebody domain: no aft patch
    assert f"pRef            {flow.pressure_pa:.12g};" in ctrl
    u = (case / "0/U").read_text()
    assert f"uniform ({flow.velocity_m_s:.12g} 0 0)" in u and "slip" in u
    thermo = (case / "constant/thermophysicalProperties").read_text()
    assert re.search(r"mu\s+0;", thermo) and "perfectGas" in thermo
    record = yaml.safe_load((case / "aether_case.yaml").read_text())
    assert record["equations"] == "axisymmetric compressible Euler"
    assert record["mesh"]["n_cells"] == plan.n_cells
    with pytest.raises(FileExistsError):
        write_case(case, plan, flow, SolverSettings())


def test_full_body_case_gets_an_aft_force_object(tmp_path):
    plan = build_mesh_plan(sphere_outline(0.5), 3.0, 0.5, MeshSettings(extent="full"))
    values = template_values(plan, FlowCondition(3.0, 1000.0, 220.0), SolverSettings())
    assert "body_aft" in values["FORCES_AFT_BLOCK"]
    assert values["BODY_PATCHES"] == "body_fore body_aft"


def test_parse_check_mesh_and_patch_retyping(tmp_path):
    log = ("    cells:            4800\n    Max aspect ratio = 6.05 OK.\n"
           "    Mesh non-orthogonality Max: 72.8 average: 24.9\n"
           "   *Number of severely non-orthogonal (> 70 degrees) faces: 58.\n"
           "    Max skewness = 2.35 OK.\nMesh OK.\n")
    q = parse_check_mesh(log)
    assert q["mesh_ok"] and q["n_cells"] == 4800 and q["max_non_orthogonality_deg"] == 72.8
    assert q["n_severely_non_orthogonal_faces"] == 58 and q["max_skewness"] == 2.35
    assert not parse_check_mesh("Failed 2 mesh checks.")["mesh_ok"]

    b = tmp_path / "constant" / "polyMesh"
    b.mkdir(parents=True)
    (b / "boundary").write_text("axis\n{\n    type patch;\n    nFaces 0;\n}\n"
                                "front\n{\n    type wedge;\n}\n")
    set_patch_type(tmp_path, "axis", "empty")
    assert "axis\n{\n    type empty;" in (b / "boundary").read_text()
    with pytest.raises(RuntimeError):
        set_patch_type(tmp_path, "nonexistent", "empty")


def test_set_end_iteration_rewrites_only_the_two_controls(tmp_path):
    from src.aether.cfd.case import set_end_iteration
    plan = build_mesh_plan(sphere_outline(0.5), 3.0, 0.5)
    case = write_case(tmp_path / "c", plan, FlowCondition(3.0, 1000.0, 220.0),
                      SolverSettings(n_iterations=1000))
    before = (case / "system/controlDict").read_text()
    set_end_iteration(case, 1500)
    after = (case / "system/controlDict").read_text()
    assert re.search(r"(?m)^endTime\s+1500;", after)
    assert re.search(r"(?m)^writeInterval\s+1500;", after)
    changed = [a for a, b in zip(after.splitlines(), before.splitlines(), strict=True) if a != b]
    assert len(changed) == 2
    assert "startFrom       latestTime;" in after
