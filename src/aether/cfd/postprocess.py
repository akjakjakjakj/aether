"""Turn raw OpenFOAM output into the metrics the validation gate is judged on.

Every function reads files written by the solver or by sampling utilities. Nothing here
accepts a number typed by a person, and nothing here knows what the reference values are.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .case import FlowCondition
from .reference import normal_shock_density_ratio

# ---------------------------------------------------------------------------------------
# Force history
# ---------------------------------------------------------------------------------------

def _load_dat(path: Path) -> np.ndarray:
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        rows.append([float(v) for v in re.sub(r"[()]", " ", line).split()])
    return np.atleast_2d(np.array(rows, dtype=float))


def _concat_restarts(case_dir: Path, function_object: str, filename: str) -> np.ndarray:
    """Stitch a function-object file across restarts (one sub-directory per start time)."""
    root = Path(case_dir) / "postProcessing" / function_object
    parts = sorted(root.glob(f"*/{filename}"), key=lambda p: float(p.parent.name))
    if not parts:
        raise FileNotFoundError(f"no {filename} under {root}")
    data = np.vstack([_load_dat(p) for p in parts])
    _, last = np.unique(data[::-1, 0], return_index=True)   # later restarts win
    return data[::-1][last]


def force_coefficient_history(case_dir: Path, flow: FlowCondition, reference_area_m2: float,
                              wedge_angle_deg: float) -> pd.DataFrame:
    """Axial force coefficient history, fore and aft patches separately and summed.

    ``cd_total`` is the sum over the body patches that EXIST in the case: fore + aft for a
    full-body domain, forebody only for a forebody domain (where ``cd_aft`` is NaN).

    The wedge carries ``wedge_angle_deg`` of the full 360 degrees, so the axial force on
    the full body is the wedge force times 360 / angle. ``cd_fore`` and ``cd_aft`` are
    pressure forces relative to p_inf (the forces function object is given pRef = p_inf),
    split at the maximum-radius station.
    """
    scale = 360.0 / wedge_angle_deg / (flow.dynamic_pressure_pa * reference_area_m2)
    fore = _concat_restarts(case_dir, "forcesFore", "force.dat")
    has_aft = (Path(case_dir) / "postProcessing" / "forcesAft").exists()
    aft = _concat_restarts(case_dir, "forcesAft", "force.dat") if has_aft else None
    n = min(len(fore), len(aft)) if has_aft else len(fore)
    df = pd.DataFrame({
        "iteration": fore[:n, 0].astype(int),
        "cd_fore": fore[:n, 1] * scale,
        # a forebody-only domain has no aft patch: its contribution is ABSENT, not zero
        "cd_aft": aft[:n, 1] * scale if has_aft else np.full(n, np.nan),
        "cd_viscous": (fore[:n, 7] + (aft[:n, 7] if has_aft else 0.0)) * scale,
    })
    df["cd_total"] = df["cd_fore"] + df["cd_aft"] if has_aft else df["cd_fore"]
    try:
        res = _concat_restarts(case_dir, "residualRho", "volFieldValue.dat")
        df = df.merge(pd.DataFrame({"iteration": res[:, 0].astype(int),
                                    "mean_abs_drho_dtau_kg_m3_s": res[:, 1]}),
                      on="iteration", how="left")
    except FileNotFoundError:
        df["mean_abs_drho_dtau_kg_m3_s"] = np.nan
    return df


# ---------------------------------------------------------------------------------------
# Convergence criterion
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ConvergenceCriterion:
    """Declared in the run config BEFORE any case is run (spec §17, condition 2).

    Over the final ``window_iterations`` iterations a coefficient must satisfy BOTH:
      * peak-to-peak variation / |mean|  <=  ``max_peak_to_peak_rel``
      * |mean(2nd half) - mean(1st half)| / |mean|  <=  ``max_drift_rel``
    """

    window_iterations: int = 2000
    max_peak_to_peak_rel: float = 1.0e-3
    max_drift_rel: float = 2.0e-4


@dataclass(frozen=True)
class ConvergenceResult:
    quantity: str
    mean: float
    peak_to_peak_rel: float
    drift_rel: float
    window_iterations: int
    converged: bool

    def to_dict(self) -> dict:
        return asdict(self)


def assess_convergence(history: pd.DataFrame, quantity: str,
                       criterion: ConvergenceCriterion) -> ConvergenceResult:
    it = history["iteration"].to_numpy()
    y = history[quantity].to_numpy()
    window = it >= it[-1] - criterion.window_iterations
    if it[-1] - it[0] < criterion.window_iterations or window.sum() < 8:
        return ConvergenceResult(quantity, float(y[-1]), float("nan"), float("nan"),
                                 criterion.window_iterations, False)
    w = y[window]
    mean = float(w.mean())
    denom = abs(mean) if mean != 0 else float("nan")
    p2p = float((w.max() - w.min()) / denom)
    half = len(w) // 2
    drift = float(abs(w[half:].mean() - w[:half].mean()) / denom)
    ok = p2p <= criterion.max_peak_to_peak_rel and drift <= criterion.max_drift_rel
    return ConvergenceResult(quantity, mean, p2p, drift, criterion.window_iterations, bool(ok))


# ---------------------------------------------------------------------------------------
# Shock stand-off and stagnation pressure
# ---------------------------------------------------------------------------------------

def _latest_sample(case_dir: Path, function_object: str, pattern: str) -> Path:
    root = Path(case_dir) / "postProcessing" / function_object
    hits = sorted(root.glob(f"*/{pattern}"), key=lambda p: float(p.parent.name))
    if not hits:
        raise FileNotFoundError(f"no {pattern} under {root}")
    return hits[-1]


def read_stagnation_line(case_dir: Path) -> pd.DataFrame:
    """Cell values along the stagnation streamline, upstream boundary to nose."""
    path = _latest_sample(case_dir, "sampleLine", "stagnationLine_*.xy")
    fields = path.stem.split("_")[1:]            # e.g. ['T', 'p', 'rho', 'U']
    cols = ["x_m"]
    for f in fields:
        cols += [f"{f}x", f"{f}y", f"{f}z"] if f == "U" else [f]
    data = _load_dat(path)
    if data.shape[1] != len(cols):
        raise ValueError(f"unexpected column count in {path}")
    return pd.DataFrame(data, columns=cols).sort_values("x_m").reset_index(drop=True)


def read_body_pressure(case_dir: Path) -> pd.DataFrame:
    """Face-centre pressure on the body surface: columns x_m, r_m, p_pa."""
    data = _load_dat(_latest_sample(case_dir, "sampleBody", "p_body.raw"))
    return (pd.DataFrame({"x_m": data[:, 0], "r_m": np.hypot(data[:, 1], data[:, 2]),
                          "p_pa": data[:, 3]})
            .sort_values("x_m").reset_index(drop=True))


@dataclass(frozen=True)
class ShockMetrics:
    standoff_m: float
    """Distance from the nose to the 50% density-rise point on the stagnation line."""
    shock_thickness_m: float
    """10%-90% density-rise distance: the numerical smearing of the captured shock."""
    local_cell_size_m: float
    shock_thickness_cells: float

    def to_dict(self) -> dict:
        return asdict(self)


def shock_metrics(line: pd.DataFrame, flow: FlowCondition) -> ShockMetrics:
    """Locate the bow shock on the stagnation line.

    The shock position is defined as the point where density has risen half-way from the
    freestream value to the Rankine-Hugoniot post-shock value. Those two levels are exact
    jump conditions, used only as a threshold; the position itself comes from the CFD
    field, linearly interpolated between cell centres.
    """
    x = line["x_m"].to_numpy()
    rho = line["rho"].to_numpy()
    rho1 = flow.density_kg_m3
    rho2 = rho1 * normal_shock_density_ratio(flow.mach, flow.gamma)

    def first_crossing(fraction: float) -> float:
        level = rho1 + fraction * (rho2 - rho1)
        above = np.nonzero(rho >= level)[0]
        if above.size == 0 or above[0] == 0:
            raise ValueError("no bow shock found on the stagnation line (is it inside the "
                             "domain, and is the solution converged?)")
        i = above[0]
        return float(x[i - 1] + (level - rho[i - 1]) * (x[i] - x[i - 1]) / (rho[i] - rho[i - 1]))

    x50, x10, x90 = first_crossing(0.5), first_crossing(0.1), first_crossing(0.9)
    i = int(np.searchsorted(x, x50))
    dx = float(x[min(i, len(x) - 1)] - x[max(i - 1, 0)])
    thick = x90 - x10
    return ShockMetrics(standoff_m=-x50, shock_thickness_m=thick, local_cell_size_m=dx,
                        shock_thickness_cells=thick / dx if dx > 0 else float("nan"))


def stagnation_pressure_pa(body: pd.DataFrame, line: pd.DataFrame) -> dict:
    """Stagnation-point pressure, two independent ways.

    ``wall_face``: the body face nearest the axis. ``line_extrapolated``: linear
    extrapolation of the last two stagnation-line cell values to the wall at x = 0.
    """
    wall = float(body.sort_values("r_m").iloc[0]["p_pa"])
    tail = line.tail(2)
    x, p = tail["x_m"].to_numpy(), tail["p"].to_numpy()
    extrap = float(p[1] + (0.0 - x[1]) * (p[1] - p[0]) / (x[1] - x[0]))
    return {"wall_face": wall, "line_extrapolated": extrap,
            "max_on_body": float(body["p_pa"].max())}


def outlet_min_mach(case_dir: Path, flow: FlowCondition) -> float:
    """Smallest Mach number on the outflow plane.

    A zero-gradient outflow is only well posed where the flow leaves supersonically. A
    value below 1 means downstream influence could enter the domain through the outlet.
    """
    t = _load_dat(_latest_sample(case_dir, "sampleOutlet", "T_outlet.raw"))
    u = _load_dat(_latest_sample(case_dir, "sampleOutlet", "U_outlet.raw"))
    speed = np.linalg.norm(u[:, 3:6], axis=1)
    a = np.sqrt(flow.gamma * flow.gas_constant_j_kgk * t[:, 3])
    return float((speed / a).min())


# ---------------------------------------------------------------------------------------
# Whole-field export (for figures only; no metric is computed from it)
# ---------------------------------------------------------------------------------------

_LIST = re.compile(r"internalField\s+nonuniform\s+List<(\w+)>\s*(\d+)\s*\(")


def read_internal_field(path: Path) -> np.ndarray:
    """Internal field of an ASCII OpenFOAM vol field: (n,) for scalars, (n, 3) for vectors."""
    text = Path(path).read_text()
    m = _LIST.search(text)
    if not m:
        raise ValueError(f"{path} has no nonuniform internalField")
    kind, n = m.group(1), int(m.group(2))
    width = 3 if kind == "vector" else 1
    body = text[m.end():]
    end = body.index("\n)") if "\n)" in body else len(body)
    values = np.array(re.sub(r"[()]", " ", body[:end]).split(), dtype=float)
    if values.size != n * width:
        raise ValueError(f"{path}: expected {n * width} values, found {values.size}")
    return values.reshape(n, 3) if width == 3 else values


def read_meridional_fields(case_dir: Path, flow: FlowCondition) -> pd.DataFrame:
    """Cell-centre x, r, rho/rho_inf, p/p_inf and Mach at the latest time.

    Needs ``postProcess -func writeCellCentres -latestTime`` to have been run.
    """
    case_dir = Path(case_dir)
    times = [d for d in case_dir.iterdir() if d.is_dir() and re.fullmatch(r"[\d.]+", d.name)
             and float(d.name) > 0]
    latest = max(times, key=lambda d: float(d.name))
    c = read_internal_field(latest / "C")
    rho, p, t = (read_internal_field(latest / f) for f in ("rho", "p", "T"))
    u = read_internal_field(latest / "U")
    a = np.sqrt(flow.gamma * flow.gas_constant_j_kgk * t)
    return pd.DataFrame({
        "x_m": c[:, 0], "r_m": np.hypot(c[:, 1], c[:, 2]),
        "rho_over_rho_inf": rho / flow.density_kg_m3, "p_over_p_inf": p / flow.pressure_pa,
        "mach": np.linalg.norm(u, axis=1) / a,
    })
