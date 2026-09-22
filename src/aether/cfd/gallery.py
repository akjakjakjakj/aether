"""Flow-field gallery: meridional-plane pictures read straight from the case directories.

Additive helper for ``scripts/render_cfd_gallery.py``. Nothing here changes how a case is
run or judged; it only READS what the solver wrote (``constant/polyMesh``, the saved time
directories, ``aether_case.yaml``) plus the result tables the milestones already carry.

Conceptual anchor
-----------------
Every case is an axisymmetric wedge: one layer of prism cells, 5 degrees wide, between the
``front`` and ``back`` wedge patches. Each ``front`` face is therefore exactly one cell seen
in the meridional plane, and its owner is that cell. Reading the ``front`` patch of the
polyMesh gives the true cell polygons in (x, r) with r = sqrt(y^2 + z^2) - so a field can be
drawn cell by cell, flat, with no interpolation, and no OpenFOAM utility has to be run.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.tri as mtri
import numpy as np
import yaml
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

from ..viz import ACCENT, DEEP, HOT, INK, MUTED, plt
from .case import FlowCondition
from .postprocess import read_internal_field

BODY_FILL = "#e4e5ea"
SONIC = "white"
CMAP = {"mach": "viridis", "p": "magma", "T": "cividis", "rho": "viridis"}
LABEL = {"mach": "Mach number  $M$  [-]", "p": "pressure ratio  $p/p_\\infty$  [-]",
         "T": "temperature ratio  $T/T_\\infty$  [-]",
         "rho": "density ratio  $\\rho/\\rho_\\infty$  [-]"}

# ---------------------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------------------

_COUNT_BLOCK = re.compile(r"\n(\d+)\s*\n\(\n")


def _list_block(text: str) -> tuple[int, str]:
    m = _COUNT_BLOCK.search(text)
    if not m:
        raise ValueError("no OpenFOAM list block found")
    body = text[m.end():]
    return int(m.group(1)), body[:body.index("\n)")]


@dataclass(frozen=True)
class WedgeMesh:
    """Cell polygons of the meridional plane, in cell order."""

    polys: list[np.ndarray]
    cx: np.ndarray
    cr: np.ndarray

    @property
    def n_cells(self) -> int:
        return len(self.polys)

    @property
    def x_range(self) -> tuple[float, float]:
        allx = np.concatenate([p[:, 0] for p in self.polys])
        return float(allx.min()), float(allx.max())

    @property
    def r_max(self) -> float:
        return float(max(p[:, 1].max() for p in self.polys))


def read_wedge_mesh(case_dir: Path) -> WedgeMesh:
    """The ``front`` wedge patch of ``constant/polyMesh`` as one polygon per cell."""
    pm = Path(case_dir) / "constant" / "polyMesh"
    n, body = _list_block((pm / "points").read_text())
    pts = np.array(body.replace("(", " ").replace(")", " ").split(), dtype=float).reshape(n, 3)
    xr = np.column_stack([pts[:, 0], np.hypot(pts[:, 1], pts[:, 2])])
    _, body = _list_block((pm / "faces").read_text())
    faces = re.findall(r"(\d+)\(([^)]*)\)", body)
    _, body = _list_block((pm / "owner").read_text())
    owner = np.array(body.split(), dtype=int)
    bnd = (pm / "boundary").read_text()
    m = re.search(r"\bfront\s*\{[^}]*?nFaces\s+(\d+);\s*startFace\s+(\d+);", bnd)
    if not m:
        raise ValueError(f"{pm}/boundary has no 'front' wedge patch")
    n_faces, start = int(m.group(1)), int(m.group(2))
    n_cells = int(owner.max()) + 1
    if n_faces != n_cells:
        raise ValueError(f"front patch has {n_faces} faces but the mesh has {n_cells} cells")
    polys: list[np.ndarray | None] = [None] * n_cells
    for i in range(start, start + n_faces):
        ids = np.array(faces[i][1].split(), dtype=int)
        polys[owner[i]] = xr[ids]
    if any(p is None for p in polys):
        raise ValueError("a cell has no front face")
    cx = np.array([p[:, 0].mean() for p in polys])
    cr = np.array([p[:, 1].mean() for p in polys])
    return WedgeMesh(polys, cx, cr)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------
# Fields
# ---------------------------------------------------------------------------------------

def saved_times(case_dir: Path) -> list[int]:
    """Written iterations (pseudo-time steps) that carry a pressure field, ascending."""
    out = []
    for d in Path(case_dir).iterdir():
        if d.is_dir() and re.fullmatch(r"\d+", d.name) and (d / "p").exists():
            out.append(int(d.name))
    return sorted(out)


def load_flow(case_dir: Path) -> FlowCondition:
    f = yaml.safe_load((Path(case_dir) / "aether_case.yaml").read_text())["flow"]
    return FlowCondition(float(f["mach"]), float(f["pressure_pa"]), float(f["temperature_k"]),
                         float(f["gamma"]), float(f["gas_constant_j_kgk"]))


def load_fields(case_dir: Path, time: int, flow: FlowCondition) -> dict[str, np.ndarray]:
    """p/p_inf, T/T_inf, rho/rho_inf and Mach at one saved iteration, per cell."""
    d = Path(case_dir) / str(time)
    p, t, rho = (read_internal_field(d / f) for f in ("p", "T", "rho"))
    u = read_internal_field(d / "U")
    with np.errstate(invalid="ignore"):
        a = np.sqrt(flow.gamma * flow.gas_constant_j_kgk * np.where(t > 0, t, np.nan))
    speed = np.linalg.norm(u, axis=1)
    e_int = flow.gas_constant_j_kgk / (flow.gamma - 1.0) * t      # c_v T of a perfect gas
    return {"p": p / flow.pressure_pa, "T": t / flow.temperature_k,
            "rho": rho / flow.density_kg_m3, "mach": speed / a,
            "T_K": t, "p_Pa": p, "speed": speed,
            "ke_fraction": 0.5 * speed**2 / (0.5 * speed**2 + e_int)}


def case_meta(case_dir: Path) -> dict:
    return yaml.safe_load((Path(case_dir) / "aether_case.yaml").read_text())


def last_logged_iteration(log_path: Path) -> int | None:
    """The last 'Time = N' a solver log reached (where a crashed run died)."""
    if not Path(log_path).exists():
        return None
    hits = re.findall(r"(?m)^Time = (\d+)", Path(log_path).read_text())
    return int(hits[-1]) if hits else None


# ---------------------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------------------

def forebody_part(x: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Outline from the nose to the maximum-radius station (the forebody domain's extent)."""
    i = int(np.argmax(r))
    return np.asarray(x[:i + 1]), np.asarray(r[:i + 1])


def draw_cells(ax, mesh: WedgeMesh, values: np.ndarray, field: str, vmin: float, vmax: float,
               edges: bool = False, cmap: str | None = None, norm=None) -> PolyCollection:
    pc = PolyCollection(mesh.polys, array=np.asarray(values, dtype=float),
                        cmap=cmap or CMAP[field], norm=norm,
                        edgecolors=(INK if edges else "face"),
                        linewidths=(0.18 if edges else 0.25), rasterized=True)
    if norm is None:
        pc.set_clim(vmin, vmax)
    if edges:
        pc.set_alpha(None)
    ax.add_collection(pc)
    return pc


def draw_body(ax, xb: np.ndarray, rb: np.ndarray) -> None:
    ax.fill_between(xb, 0.0, rb, color=BODY_FILL, zorder=3, lw=0)
    ax.plot(xb, rb, color=INK, lw=1.0, zorder=4)
    ax.plot([xb[-1], xb[-1]], [0.0, rb[-1]], color=INK, lw=0.6, ls=":", zorder=4)


def frame(ax, mesh: WedgeMesh, xb: np.ndarray, rb: np.ndarray, x_pad: float = 0.0) -> None:
    x0, x1 = mesh.x_range
    ax.set_xlim(x0 - x_pad, x1 + x_pad)
    ax.set_ylim(0.0, mesh.r_max)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xlabel("axial position  $x$  [m]")
    ax.set_ylabel("radius  $r$  [m]")


def _masked_triangulation(mesh: WedgeMesh, xb: np.ndarray, rb: np.ndarray) -> mtri.Triangulation:
    tri = mtri.Triangulation(mesh.cx, mesh.cr)
    tx = mesh.cx[tri.triangles].mean(axis=1)
    tr = mesh.cr[tri.triangles].mean(axis=1)
    inside = (tx > xb.min()) & (tx < xb.max()) & (tr < np.interp(tx, xb, rb))
    tri.set_mask(inside)
    return tri


def draw_contour(ax, mesh: WedgeMesh, values: np.ndarray, level: float, xb, rb,
                 color: str = SONIC, lw: float = 1.1, ls: str = "-"):
    tri = _masked_triangulation(mesh, xb, rb)
    v = np.where(np.isfinite(values), values, np.nanmax(values))
    return ax.tricontour(tri, v, levels=[level], colors=[color], linewidths=[lw],
                         linestyles=[ls], zorder=5)


def colorbar(fig, ax, pc, label: str, **kw):
    """A colour bar that matches the height of an equal-aspect axes (single-axes case), or
    a shared bar stolen from a list of axes (fig.colorbar semantics)."""
    from matplotlib.axes import Axes
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    if isinstance(ax, Axes) and kw.get("orientation", "vertical") == "vertical":
        cax = make_axes_locatable(ax).append_axes("right", size="4.5%", pad=0.08)
        cb = fig.colorbar(pc, cax=cax)
    else:
        cb = fig.colorbar(pc, ax=ax, **kw)
    cb.set_label(label)
    cb.outline.set_edgecolor(MUTED)
    return cb


def tag(ax, text: str, color: str = INK, loc: str = "upper right", fontsize: float = 7.0):
    xy = {"upper right": (0.985, 0.97), "upper left": (0.015, 0.97), "lower right": (0.985, 0.04),
          "lower left": (0.015, 0.04)}[loc]
    ha = "right" if "right" in loc else "left"
    va = "top" if "upper" in loc else "bottom"
    ax.text(*xy, text, transform=ax.transAxes, ha=ha, va=va, fontsize=fontsize, color=color,
            zorder=8, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.88))


def save_with_caption(fig, out_dir: Path, stem: str, caption: str) -> Path:
    """The house standard of ``aether.viz._save`` (vector PDF + PNG, caption BELOW the axes)
    without its ``subplots_adjust`` call, which re-expands axes that a colour bar shared by
    several panels has already shrunk and puts the bar on top of a panel."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.text(0.01, -0.02, caption, fontsize=6.5, color=MUTED, ha="left", va="top", wrap=True,
             transform=fig.transFigure)
    png = out_dir / f"{stem}.png"
    fig.savefig(png, bbox_inches="tight")
    fig.savefig(out_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    return png


# ---------------------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------------------

@dataclass
class IndexEntry:
    stem: str
    caption: str
    run_id: str
    cases: str
    mach: str
    mesh_level: str
    time_step: str
    field: str


@dataclass
class Gallery:
    out_dir: Path
    entries: list[IndexEntry]
    missing: list[str]

    def save(self, fig, stem: str, caption: str, *, run_id: str, cases: str, mach: str,
             mesh_level: str, time_step: str, field: str) -> Path:
        path = save_with_caption(fig, self.out_dir, stem, caption)
        self.entries.append(IndexEntry(stem, caption, run_id, cases, mach, mesh_level,
                                       time_step, field))
        return path

    def cannot(self, what: str) -> None:
        self.missing.append(what)

    def write_index(self, generated_by: str) -> Path:
        lines = ["# CFD flow-field gallery", "",
                 f"Generated by `{generated_by}` from the case directories under "
                 f"`cfd/generated/` and the result tables under `results/`. Every figure is "
                 f"written as PNG and vector PDF. Colour scales are perceptually uniform "
                 f"(viridis / magma / cividis) and stated on each colour bar. All fields are "
                 f"drawn in the meridional plane (x, r), axis equal, one flat-shaded polygon "
                 f"per cell of the wedge mesh (no interpolation). \"time step\" is the saved "
                 f"iteration of the local-time-stepping pseudo-time march.", ""]
        if self.missing:
            lines += ["## Not rendered (and why)", ""]
            lines += [f"- {m}" for m in self.missing]
            lines += [""]
        lines += ["## Figures", "",
                  "| figure | run ID | case(s) | Mach | mesh level | time step | field(s) | "
                  "caption |",
                  "|---|---|---|---|---|---|---|---|"]
        for e in self.entries:
            cap = e.caption.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| [{e.stem}]({e.stem}.png) ([pdf]({e.stem}.pdf)) | {e.run_id} | "
                         f"{e.cases} | {e.mach} | {e.mesh_level} | {e.time_step} | {e.field} | "
                         f"{cap} |")
        path = self.out_dir / "INDEX.md"
        path.write_text("\n".join(lines) + "\n")
        return path


# ---------------------------------------------------------------------------------------
# Shared building blocks used by several figures
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class CaseView:
    """Everything one panel needs: mesh, flow, fields at one time, outline, metadata."""

    case_dir: Path
    name: str
    time: int
    flow: FlowCondition
    mesh: WedgeMesh
    fields: dict[str, np.ndarray]
    xb: np.ndarray
    rb: np.ndarray
    meta: dict


def load_case(case_dir: Path, outline_xr: tuple[np.ndarray, np.ndarray],
              time: int | None = None, flow: FlowCondition | None = None) -> CaseView:
    case_dir = Path(case_dir)
    times = saved_times(case_dir)
    if not times:
        raise FileNotFoundError(f"{case_dir}: no saved field")
    t = times[-1] if time is None else int(time)
    if t not in times:
        raise FileNotFoundError(f"{case_dir}: no field at iteration {t} (have {times})")
    fl = flow or load_flow(case_dir)
    mesh = read_wedge_mesh(case_dir)
    fields = load_fields(case_dir, t, fl)
    if len(fields["p"]) != mesh.n_cells:
        raise ValueError(f"{case_dir}: field has {len(fields['p'])} cells, mesh {mesh.n_cells}")
    xb, rb = forebody_part(*outline_xr)
    meta = case_meta(case_dir) if (case_dir / "aether_case.yaml").exists() else {}
    return CaseView(case_dir, case_dir.name, t, fl, mesh, fields, xb, rb, meta)


def result_json(path: Path) -> dict:
    return json.loads(Path(path).read_text()) if Path(path).exists() else {}


def panel_size(view: CaseView, width_in: float) -> float:
    x0, x1 = view.mesh.x_range
    return width_in * view.mesh.r_max / (x1 - x0)


def field_panel(fig, ax, view: CaseView, field: str, vmin: float, vmax: float,
                title: str, cbar: bool = True, edges: bool = False, sonic: bool = True,
                cmap: str | None = None):
    pc = draw_cells(ax, view.mesh, view.fields[field], field, vmin, vmax, edges=edges, cmap=cmap)
    draw_body(ax, view.xb, view.rb)
    if sonic:
        draw_contour(ax, view.mesh, view.fields["mach"], 1.0, view.xb, view.rb)
    frame(ax, view.mesh, view.xb, view.rb)
    ax.set_title(title, fontsize=8.5)
    if cbar:
        colorbar(fig, ax, pc, LABEL[field], shrink=0.85, pad=0.02)
    return pc


def sonic_handle() -> Line2D:
    return Line2D([], [], color=SONIC, lw=1.1, label="sonic line, $M$ = 1")


def annotate_standoff(ax, standoff_m: float, r_text: float, label: str, color: str = HOT,
                      y: float | None = None) -> None:
    y = 0.012 * r_text if y is None else y
    ax.annotate("", xy=(-standoff_m, y), xytext=(0.0, y),
                arrowprops=dict(arrowstyle="<->", color=color, lw=0.9, shrinkA=0, shrinkB=0),
                zorder=7)
    ax.text(-0.5 * standoff_m, y + 0.02 * r_text, label, ha="center", va="bottom",
            fontsize=6.5, color=color, zorder=8,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))


def level_of(meta: dict) -> str:
    f = int(meta.get("mesh", {}).get("refinement_factor", 0))
    return {1: "coarse", 2: "medium", 4: "fine"}.get(f, f"x{f}")


def cells_of(view: CaseView) -> str:
    return f"{view.mesh.n_cells:,} cells"


CAT_COLOURS = [INK, DEEP, HOT, ACCENT, "#3f8f6b", "#7a4ea3"]
CAT_STYLES = ["-", "--", "-.", ":", "-", "--"]
