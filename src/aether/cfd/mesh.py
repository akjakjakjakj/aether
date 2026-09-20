"""Structured body-fitted mesh for ANY axisymmetric outline, as a blockMeshDict.

Topology
--------
One strip of hexahedral blocks wraps the body from the nose (upstream axis) to the tail
(downstream axis). The first block edge is the stagnation streamline, the last is the
wake centreline. Block boundaries are straight rays of constant polar angle about a point
on the axis inside the body, so the outline only has to be star-shaped about that point -
true of every blunt capsule this project considers, and checked explicitly.

The outer boundary is Billig's hyperbolic shock shape evaluated with a stand-off margin
and a widened asymptote, closed by a vertical outflow plane. Sizing the domain from the
correlation keeps the bow shock inside the inflow boundary at every Mach number without
wasting cells on undisturbed freestream. Billig is used here ONLY to place the boundary.

The mesh is generated planar (x-r plane, one cell thick) and then rotated into a wedge by
OpenFOAM's ``extrudeMesh``; see :mod:`aether.cfd.case`.

Extent
------
``extent = "forebody"`` (the default) stops the strip at the maximum-radius station and
closes it with an outflow plane there. For a blunt body the flow at that station is
supersonic, so the forebody solution is independent of anything downstream and the Euler
problem has a genuine steady state. ``extent = "full"`` wraps the whole body and its wake;
it is kept because it is how the wake problem documented in negative result NR-06 was found,
not because its base pressure should be trusted.

Refinement
----------
``refinement_factor`` multiplies every block's cell count in both directions, with the
block layout and grading fixed. Meshes at factors 1, 2, 4 are therefore geometrically
similar with a constant refinement ratio of exactly 2 - what the GCI procedure assumes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

from .outline import Outline
from .reference import billig_shock_x_m


@dataclass(frozen=True)
class MeshSettings:
    """Mesh controls. Base counts describe the COARSE level (refinement_factor = 1)."""

    n_body_cells_base: int = 80
    n_radial_cells_base: int = 60
    cells_per_block_base: int = 4
    refinement_factor: int = 1
    radial_expansion_ratio: float = 4.0
    standoff_margin: float = 2.0
    asymptote_margin_deg: float = 6.0
    wake_length_diameters: float = 3.0
    wedge_angle_deg: float = 5.0
    outer_samples_per_block: int = 24
    extent: str = "forebody"   # 'forebody' | 'full'


@dataclass(frozen=True)
class Block:
    i_start: int
    n_cells_base: int
    body_xy: np.ndarray    # (n, 2) polyline INCLUDING both end vertices
    outer_xy: np.ndarray
    body_patch: str        # 'body_fore' | 'body_aft'
    outer_patch: str       # 'freestream' | 'outlet'


@dataclass
class MeshPlan:
    """Everything needed to write a blockMeshDict, plus the numbers reports quote."""

    outline: Outline
    settings: MeshSettings
    mach: float
    sizing_radius_m: float
    centre_x_m: float
    outflow_x_m: float
    upstream_axis_x_m: float
    blocks: list[Block] = field(default_factory=list)

    @property
    def body_patches(self) -> tuple[str, ...]:
        return tuple(sorted({b.body_patch for b in self.blocks}, reverse=True))

    @property
    def n_body_cells(self) -> int:
        return sum(b.n_cells_base for b in self.blocks) * self.settings.refinement_factor

    @property
    def n_radial_cells(self) -> int:
        return self.settings.n_radial_cells_base * self.settings.refinement_factor

    @property
    def n_cells(self) -> int:
        return self.n_body_cells * self.n_radial_cells

    @property
    def domain_area_m2(self) -> float:
        """Meridional-plane area of the fluid domain (shoelace), for the GCI cell size."""
        body = np.vstack([b.body_xy[:-1] for b in self.blocks] + [self.blocks[-1].body_xy[-1:]])
        outer = np.vstack([b.outer_xy[:-1] for b in self.blocks]
                          + [self.blocks[-1].outer_xy[-1:]])
        poly = np.vstack([body, outer[::-1]])
        x, y = poly[:, 0], poly[:, 1]
        return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))

    @property
    def representative_cell_size_m(self) -> float:
        """h = sqrt(A / N), the 2-D form of Celik et al. (2008) eq. (1)."""
        return math.sqrt(self.domain_area_m2 / self.n_cells)


def _find_centre(outline: Outline, forebody_only: bool) -> float:
    """A point on the axis about which the outline's polar angle is strictly monotone.

    In forebody mode the point is pinned to the maximum-radius station, which makes the
    closing ray - and therefore the outflow plane - exactly perpendicular to the axis.
    """
    i_max = int(np.argmax(outline.r_m))
    if forebody_only:
        xc = float(outline.x_m[i_max])
        phi = np.arctan2(outline.r_m[:i_max + 1], outline.x_m[:i_max + 1] - xc)
        phi[0] = math.pi
        if np.all(np.diff(phi) < 0.0):
            return xc
        raise ValueError("forebody is not star-shaped about its maximum-radius station")
    candidates = [outline.x_m[i_max]] + list(np.linspace(0.15, 0.85, 15) * outline.length_m)
    for xc in candidates:
        if not 0.0 < xc < outline.length_m:
            continue
        phi = np.arctan2(outline.r_m, outline.x_m - xc)
        phi[0], phi[-1] = math.pi, 0.0
        if np.all(np.diff(phi) < 0.0):
            return float(xc)
    raise ValueError(
        "outline is not star-shaped about any trial point on its axis; the single-strip "
        "topology cannot mesh it (re-entrant afterbody?)"
    )


def build_mesh_plan(outline: Outline, mach: float, sizing_radius_m: float | None = None,
                    settings: MeshSettings | None = None) -> MeshPlan:
    """Lay out blocks around ``outline`` for a freestream Mach number.

    ``sizing_radius_m`` is the radius handed to Billig's correlation to size the domain.
    It defaults to the larger of the nose radius of curvature estimate and the maximum
    body radius, which over-estimates the stand-off of a truncated blunt body and is
    therefore conservative for keeping the shock inside the domain.
    """
    st = settings or MeshSettings()
    if st.n_body_cells_base % st.cells_per_block_base:
        raise ValueError("n_body_cells_base must be a multiple of cells_per_block_base")
    if sizing_radius_m is None:
        sizing_radius_m = max(_nose_radius_estimate(outline), outline.max_radius_m)

    if st.extent not in ("forebody", "full"):
        raise ValueError(f"unknown mesh extent {st.extent!r}")
    forebody_only = st.extent == "forebody"
    xc = _find_centre(outline, forebody_only)
    s = outline.arc_length_m
    i_max = int(np.argmax(outline.r_m))
    s_split, s_tot = s[i_max], s[-1]

    # Base-level cell boundaries: uniform in arc length separately fore and aft of the
    # maximum-radius point, so the fore/aft force split is exact on every mesh level.
    cpb = st.cells_per_block_base
    if forebody_only:
        n_fore = st.n_body_cells_base
        s_nodes = np.linspace(0.0, s_split, n_fore + 1)
    else:
        n_fore = int(round(st.n_body_cells_base * s_split / s_tot / cpb)) * cpb
        n_fore = min(max(n_fore, cpb), st.n_body_cells_base - cpb)
        n_aft = st.n_body_cells_base - n_fore
        s_nodes = np.concatenate([np.linspace(0.0, s_split, n_fore + 1),
                                  np.linspace(s_split, s_tot, n_aft + 1)[1:]])
    block_nodes = np.arange(0, st.n_body_cells_base + 1, cpb)

    beta = math.asin(1.0 / mach) + math.radians(st.asymptote_margin_deg)

    def shock_x(r):
        return billig_shock_x_m(r, mach, sizing_radius_m, asymptote_angle_rad=beta,
                                standoff_scale=st.standoff_margin)

    def ray_hit_hyperbola(phi: float) -> np.ndarray:
        c, sn = math.cos(phi), math.sin(phi)

        def f(t):  # > 0 inside the hyperbola (downstream of it)
            return (xc + t * c) - float(shock_x(t * sn))
        t_hi = 1e3 * (outline.length_m + sizing_radius_m)
        if f(t_hi) > 0:
            return np.array([np.nan, np.nan])
        t = brentq(f, 1e-9, t_hi, xtol=1e-13)
        return np.array([xc + t * c, t * sn])

    # Place the freestream/outlet corner ON a block-boundary ray so the patch split is a
    # block boundary on every mesh level.
    xb, rb = outline.point_at(s_nodes[block_nodes])
    phi_nodes = np.arctan2(rb, xb - xc)
    phi_nodes[0] = math.pi
    if forebody_only:
        phi_nodes[-1] = 0.5 * math.pi
        k_corner = len(block_nodes) - 1          # no block lies on the outflow plane
        corner = ray_hit_hyperbola(phi_nodes[-1])
        x_out = xc
    else:
        phi_nodes[-1] = 0.0
        x_out_target = (outline.length_m
                        + st.wake_length_diameters * 2.0 * outline.max_radius_m)
        r_corner = brentq(lambda r: float(shock_x(r)) - x_out_target, 0.0,
                          1e3 * (outline.length_m + sizing_radius_m))
        phi_corner = math.atan2(r_corner, x_out_target - xc)
        k_corner = int(np.argmin(np.abs(phi_nodes - phi_corner)))
        k_corner = min(max(k_corner, 1), len(block_nodes) - 2)
        corner = ray_hit_hyperbola(phi_nodes[k_corner])
        x_out = float(corner[0])

    def outer_point(phi: float, on_outlet: bool) -> np.ndarray:
        if on_outlet:
            if phi <= 0.0:
                return np.array([x_out, 0.0])
            return np.array([x_out, (x_out - xc) * math.tan(phi)])
        return ray_hit_hyperbola(phi)

    plan = MeshPlan(outline, st, mach, float(sizing_radius_m), xc, x_out,
                    float(shock_x(0.0)))
    for k in range(len(block_nodes) - 1):
        i0, i1 = block_nodes[k], block_nodes[k + 1]
        s0, s1 = s_nodes[i0], s_nodes[i1]
        inner = (s > s0 + 1e-12) & (s < s1 - 1e-12)
        s_body = np.concatenate(([s0], s[inner], [s1]))
        bx, br = outline.point_at(s_body)
        on_outlet = k >= k_corner
        phis = np.linspace(phi_nodes[k], phi_nodes[k + 1], st.outer_samples_per_block + 1)
        outer = np.array([outer_point(p, on_outlet) for p in phis])
        if k == k_corner:
            outer[0] = corner
        if k == k_corner - 1:
            outer[-1] = corner
        plan.blocks.append(Block(
            i_start=int(i0), n_cells_base=int(i1 - i0),
            body_xy=np.column_stack([bx, br]), outer_xy=outer,
            body_patch="body_fore" if i1 <= n_fore else "body_aft",
            outer_patch="outlet" if on_outlet else "freestream",
        ))
    _check_plan(plan)
    return plan


def _nose_radius_estimate(outline: Outline) -> float:
    """Radius of curvature at the nose from the osculating parabola x = r^2 / (2 R)."""
    i = min(5, outline.x_m.size - 1)
    x, r = outline.x_m[1:i + 1], outline.r_m[1:i + 1]
    good = x > 0
    if not np.any(good):
        return math.inf  # flat-faced
    return float(np.median(r[good] ** 2 / (2.0 * x[good])))


def _check_plan(plan: MeshPlan) -> None:
    for b in plan.blocks:
        if not np.all(np.isfinite(b.outer_xy)):
            raise ValueError("a block ray never meets the outer boundary")
        if np.any(b.outer_xy[:, 1] < -1e-12):
            raise ValueError("outer boundary crosses the axis")
        gap = np.hypot(*(b.outer_xy[0] - b.body_xy[0]))
        if gap <= 0:
            raise ValueError("outer boundary touches the body")


# ---------------------------------------------------------------------------------------
# blockMeshDict
# ---------------------------------------------------------------------------------------

_HEADER = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      {obj};
}}
// Generated by aether.cfd - do not edit by hand. Regenerate from the run config.
"""


def _pt(x: float, y: float, z: float) -> str:
    return f"({x:.12g} {y:.12g} {z:.12g})"


def block_mesh_dict(plan: MeshPlan, thickness_m: float | None = None) -> str:
    """Render the planar (one cell thick) blockMeshDict for a plan.

    The 'front' patch lies in the z = 0 plane, which contains the symmetry axis;
    extrudeMesh rotates it about that axis to form the wedge.
    """
    st = plan.settings
    f = st.refinement_factor
    t = thickness_m or 0.05 * plan.outline.max_radius_m
    nb = len(plan.blocks)

    # vertex k: 4k body@back, 4k+1 outer@back, 4k+2 body@front, 4k+3 outer@front
    verts = []
    for k in range(nb + 1):
        body = plan.blocks[k].body_xy[0] if k < nb else plan.blocks[-1].body_xy[-1]
        outer = plan.blocks[k].outer_xy[0] if k < nb else plan.blocks[-1].outer_xy[-1]
        for z in (-t, 0.0):
            verts += [_pt(body[0], body[1], z), _pt(outer[0], outer[1], z)]

    blocks, edges = [], []
    patches: dict[str, list[str]] = {p: [] for p in
                                     ("body_fore", "body_aft", "freestream", "outlet",
                                      "axis", "front", "back")}
    for k, b in enumerate(plan.blocks):
        a0, o0, a0f, o0f = 4 * k, 4 * k + 1, 4 * k + 2, 4 * k + 3
        a1, o1, a1f, o1f = a0 + 4, o0 + 4, a0f + 4, o0f + 4
        blocks.append(
            f"    hex ({a0} {a1} {o1} {o0} {a0f} {a1f} {o1f} {o0f}) "
            f"({b.n_cells_base * f} {st.n_radial_cells_base * f} 1) "
            f"simpleGrading (1 {st.radial_expansion_ratio:g} 1)"
        )
        for (va, vb, xy) in ((a0, a1, b.body_xy), (o0, o1, b.outer_xy)):
            if len(xy) > 2:
                for dv, z in ((0, -t), (2, 0.0)):
                    pts = " ".join(_pt(x, y, z) for x, y in xy[1:-1])
                    edges.append(f"    polyLine {va + dv} {vb + dv} ({pts})")
        patches[b.body_patch].append(f"({a0} {a0f} {a1f} {a1})")
        patches[b.outer_patch].append(f"({o0} {o1} {o1f} {o0f})")
        patches["front"].append(f"({a0f} {a1f} {o1f} {o0f})")
        patches["back"].append(f"({a0} {o0} {o1} {a1})")
    patches["axis"].append("(0 1 3 2)")
    last = 4 * nb
    closing_face = f"({last} {last + 2} {last + 3} {last + 1})"
    # full body: the strip ends on the wake centreline; forebody: on the outflow plane
    patches["axis" if st.extent == "full" else "outlet"].append(closing_face)

    types = {"body_fore": "wall", "body_aft": "wall", "freestream": "patch",
             "outlet": "patch", "axis": "patch", "front": "patch", "back": "patch"}
    out = [_HEADER.format(obj="blockMeshDict"), "scale 1;", "", "vertices", "("]
    out += [f"    {v}" for v in verts]
    out += [");", "", "blocks", "("] + blocks + [");", "", "edges", "("] + edges
    out += [");", "", "boundary", "("]
    for name, faces in patches.items():
        if not faces:
            continue
        out += [f"    {name}", "    {", f"        type {types[name]};", "        faces",
                "        ("]
        out += [f"            {fc}" for fc in faces]
        out += ["        );", "    }"]
    out += [");", ""]
    return "\n".join(out)
