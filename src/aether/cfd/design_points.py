"""Milestone M3: CFD design points for the forebody-drag response surface (spec §18).

Conceptual anchor
-----------------
The trajectory integrator asks for C_D thousands of times per entry; a CFD case takes
minutes. So CFD is run ONCE, on a planned set of (Mach, forebody shape) points, and a
response surface is fitted through the results. This module plans that set, runs it through
the unchanged M2 pipeline (:func:`aether.cfd.pipeline.run_case`), decides case by case
whether the result is usable, and writes one table. It fits nothing.

What is planned, and why it is not a plain space-filling design
----------------------------------------------------------------
* **Inputs.** log(Mach) and three forebody ratios: bluntness R_n/D, cone half-angle,
  shoulder ratio R_c/D. The forebody-only domain (A-CFD-4) ends at the maximum-radius
  station, so the aft cone angle and the length CANNOT influence C_D,fore and are not inputs.
  Inviscid perfect-gas flow has no length scale, so the diameter is not an input either;
  that claim is checked by a dedicated pair of cases rather than assumed.
* **Anchors + fill.** A GP may not extrapolate (spec §25), and the guard is the convex hull
  of the training inputs. A hull of interior space-filling points never reaches the corners
  of the box - where the M4 front sits. So every valid vertex of the shape box, a few points
  on the geometric-validity boundary and named reference shapes are run at BOTH ends of the
  Mach range; a scrambled-Sobol sequence fills the interior.
* **Invalid geometry** is skipped with the reason logged (``design_skipped.csv``).
* **Held-out test set** is drawn from the fill points with the design seed BEFORE any case
  runs, so it cannot be chosen after looking at results.

Acceptance
----------
A case is USABLE only if it (1) ran, (2) met the M2 force-convergence criterion, (3) left
the outflow plane supersonic everywhere (A-CFD-4), and (4) kept the bow shock clear of the
fixed-value inflow boundary (A-CFD-8). (4) is checked two ways: on the axis, from the
stand-off distance against the distance to the inflow boundary; and off the axis, by
requiring the outermost faces of the outflow plane to still be at freestream Mach number -
if the shock had reached the inflow boundary anywhere upstream, they would not be. A case
that fails (4) is re-run in an enlarged domain and BOTH attempts are kept.

Nothing in this module changes the behaviour of the M2 pipeline.
"""

from __future__ import annotations

import itertools
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import qmc

from ..geometry.capsule import CapsuleGeometry
from ..utils.run import REPO_ROOT, load_config
from .case import FlowCondition
from .mesh import MeshSettings
from .outline import Outline, make_outline
from .pipeline import CaseResult, restart_case, run_case
from .postprocess import ConvergenceCriterion, _latest_sample, _load_dat
from .reference import rayleigh_pitot_ratio
from .validation import _flow, _mesh_settings, _solver_settings


def gate_g4_status_at_build() -> str:
    """Gate G4 status recorded in every M3 artefact: READ from the latest M2 run's
    ``gate_assessment.json`` at the moment the artefact is written. Never a typed string."""
    from ..aerodynamics.cfd_surface import gate_g4_status  # lazy: keeps cfd importable alone

    return str(gate_g4_status()["status"])


SHAPE_INPUTS = ("bluntness_ratio", "cone_half_angle_deg", "shoulder_ratio")
PROFILE_POINTS = 1600
USABLE = "USABLE"


# ---------------------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------------------

def forebody_capsule(bluntness_ratio: float, cone_half_angle_deg: float,
                     shoulder_ratio: float, diameter_m: float) -> CapsuleGeometry:
    """The project capsule with the given FOREBODY and a neutral afterbody.

    The afterbody (cylindrical, just long enough to contain the shoulder) is chosen so that
    a capsule is rejected here only for reasons that concern its forebody. It has no effect
    on the CFD: the forebody-only domain stops at the maximum-radius station.
    Raises ValueError (from ``CapsuleGeometry.validate``) if the forebody cannot exist.
    """
    probe = CapsuleGeometry(
        nose_radius_m=bluntness_ratio * diameter_m, diameter_m=diameter_m,
        shoulder_radius_m=shoulder_ratio * diameter_m,
        cone_half_angle_deg=cone_half_angle_deg, aft_cone_angle_deg=0.0,
        length_m=2.5 * diameter_m)   # provisional; stays inside geometry_bounds at D = 3 m
    probe.validate()
    length = max(0.35 * diameter_m, float(probe._joins.x3) + 0.05 * diameter_m)
    capsule = replace(probe, length_m=length)
    capsule.validate()
    return capsule


def capsule_outline(capsule: CapsuleGeometry, name: str) -> Outline:
    x, r = capsule.profile(PROFILE_POINTS)
    return make_outline(x, r, name=name)


def domain_sizing_radius_m(capsule: CapsuleGeometry, sizing: dict[str, Any]) -> float:
    """Radius handed to Billig's correlation to PLACE the inflow boundary (A-CFD-8).

    The M2 default, max(nose radius, body radius), is right for a sphere and too small for
    a wide-angle cone with a small nose cap, whose detached shock stands off like a disk's,
    not like its nose sphere's (NR-20). The body-radius term is therefore scaled up linearly
    from 1 at ``angle_lo_deg`` to ``max_body_radius_factor`` at ``angle_hi_deg``. A heuristic
    for boundary PLACEMENT only: the clearance checks, not this function, decide validity.
    """
    lo, hi = float(sizing["angle_lo_deg"]), float(sizing["angle_hi_deg"])
    w = min(max((capsule.cone_half_angle_deg - lo) / (hi - lo), 0.0), 1.0)
    factor = 1.0 + w * (float(sizing["max_body_radius_factor"]) - 1.0)
    return max(capsule.nose_radius_m, factor * 0.5 * capsule.diameter_m)


def asymptote_margin_deg(capsule: CapsuleGeometry, mach: float, gamma: float,
                         sizing: dict[str, Any], base_margin_deg: float) -> float:
    """Margin added to the Mach angle for the asymptote of the inflow boundary (A-CFD-8).

    The M2 boundary opens at the Mach angle plus a fixed margin: right for a sphere, whose
    domain ends one radius downstream. A sphere-CONE forebody is long, and far from the nose
    its shock lies at the cone-shock angle, which at Mach 20 is several times the Mach angle
    - the M2 boundary would cut straight through it (NR-20). For an attached-shock cone the
    boundary therefore opens at Rasmussen's hypersonic cone-shock angle,
        sin(beta) = sin(theta) * sqrt((gamma + 1)/2 + 1/(M sin(theta))^2),
    plus ``cone_shock_margin_deg``. Above ``detached_above_deg`` (or where the formula has no
    solution) the shock is detached and the blunt-body sizing of
    :func:`domain_sizing_radius_m` applies instead. Boundary PLACEMENT only.
    """
    theta = math.radians(capsule.cone_half_angle_deg)
    if capsule.cone_half_angle_deg > float(sizing["detached_above_deg"]):
        return base_margin_deg
    arg = math.sin(theta) * math.sqrt(0.5 * (gamma + 1.0) + 1.0 / (mach * math.sin(theta)) ** 2)
    if arg >= 1.0:
        return base_margin_deg
    needed = math.degrees(math.asin(arg)) + float(sizing["cone_shock_margin_deg"]) \
        - math.degrees(math.asin(1.0 / mach))
    return max(base_margin_deg, needed)


def critical_cone_angle_deg(bluntness_ratio: float, shoulder_ratio: float) -> float:
    """Smallest cone half-angle at which the fore cone has non-negative length.

    From ``CapsuleGeometry._joins``: r2 >= r1 with r1 = R_n cos(t), r2 = R_b - R_c (1 - cos t)
    gives cos(t) <= (R_b - R_c) / (R_n - R_c). All radii in units of the diameter.
    """
    rb, rn, rc = 0.5, bluntness_ratio, shoulder_ratio
    if rn - rc <= 0:
        return 0.0
    c = (rb - rc) / (rn - rc)
    return 0.0 if c >= 1.0 else math.degrees(math.acos(c))


# ---------------------------------------------------------------------------------------
# Design
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class DesignPoint:
    point_id: str
    role: str            # 'anchor' | 'fill' | 'scale_check'
    split: str           # 'train' | 'test' | 'check'
    mach: float
    bluntness_ratio: float
    cone_half_angle_deg: float
    shoulder_ratio: float
    diameter_m: float
    label: str = ""

    def shape(self) -> dict[str, float]:
        return {k: getattr(self, k) for k in SHAPE_INPUTS}


def _valid_or_reason(shape: dict[str, float], diameter_m: float) -> str:
    try:
        forebody_capsule(diameter_m=diameter_m, **shape)
    except ValueError as exc:
        return str(exc)
    return ""


def build_design(cfg: dict[str, Any]) -> tuple[list[DesignPoint], pd.DataFrame]:
    """Deterministic design from the config. Returns (points, skipped-draws table)."""
    inp, des = cfg["inputs"], cfg["design"]
    d = float(cfg["fixed"]["diameter_m"])
    m_lo, m_hi = float(inp["mach"]["min"]), float(inp["mach"]["max"])
    lo = np.array([inp[k]["min"] for k in SHAPE_INPUTS], dtype=float)
    hi = np.array([inp[k]["max"] for k in SHAPE_INPUTS], dtype=float)
    skipped: list[dict] = []
    shapes: list[tuple[str, dict[str, float]]] = []

    def consider(label: str, shape: dict[str, float], source: str) -> None:
        reason = _valid_or_reason(shape, d)
        if reason:
            skipped.append({"source": source, "label": label, **shape, "reason": reason})
        else:
            shapes.append((label, shape))

    anc = des["anchors"]
    if anc.get("box_vertices", False):
        for k, corner in enumerate(itertools.product(*zip(lo, hi, strict=True))):
            consider(f"vertex{k}", dict(zip(SHAPE_INPUTS, map(float, corner), strict=True)),
                     "anchor:box_vertex")
    vb = anc.get("validity_boundary", {})
    for k, p in enumerate(vb.get("points", [])):
        theta = critical_cone_angle_deg(p["bluntness_ratio"], p["shoulder_ratio"]) \
            + float(vb["margin_deg"])
        theta = min(max(theta, lo[1]), hi[1])
        consider(f"boundary{k}", {"bluntness_ratio": float(p["bluntness_ratio"]),
                                  "cone_half_angle_deg": float(theta),
                                  "shoulder_ratio": float(p["shoulder_ratio"])},
                 "anchor:validity_boundary")
    for p in anc.get("explicit", []):
        consider(str(p["name"]), {k: float(p[k]) for k in SHAPE_INPUTS}, "anchor:explicit")

    points: list[DesignPoint] = []
    for label, shape in shapes:
        for mach in (m_lo, m_hi):
            points.append(DesignPoint(f"dp{len(points):03d}", "anchor", "train", mach,
                                      diameter_m=d, label=label, **shape))

    # -- scrambled-Sobol fill over (log Mach, shape) ---------------------------------------
    n_fill, max_draws = int(des["n_fill"]), int(des["max_fill_draws"])
    sob = qmc.Sobol(d=4, scramble=True, seed=int(des["seed"]))
    u = sob.random(max_draws)
    fill: list[DesignPoint] = []
    for k, row in enumerate(u):
        if len(fill) == n_fill:
            break
        mach = float(math.exp(math.log(m_lo) + row[0] * (math.log(m_hi) - math.log(m_lo))))
        vals = lo + row[1:] * (hi - lo)
        shape = dict(zip(SHAPE_INPUTS, map(float, vals), strict=True))
        reason = _valid_or_reason(shape, d)
        if reason:
            skipped.append({"source": "fill:sobol", "label": f"draw{k}", "mach": mach,
                            **shape, "reason": reason})
            continue
        fill.append(DesignPoint("", "fill", "train", mach, diameter_m=d,
                                label=f"draw{k}", **shape))
    if len(fill) < n_fill:
        raise RuntimeError(f"only {len(fill)} valid fill points in {max_draws} draws")

    rng = np.random.default_rng(int(des["seed"]))
    test_idx = set(rng.choice(n_fill, size=int(des["holdout"]["n_test"]), replace=False)
                   .tolist())
    for k, p in enumerate(fill):
        points.append(replace(p, point_id=f"dp{len(points):03d}",
                              split="test" if k in test_idx else "train"))

    # Late anchors: appended AFTER the fill so that adding one never renumbers a point that
    # has already been run. Same treatment as any anchor (both ends of the Mach range).
    for p in des.get("late_anchors", []):
        shape = {k: float(p.get(k, 0.0)) for k in SHAPE_INPUTS}
        if "cone_half_angle_deg_above_critical" in p:
            shape["cone_half_angle_deg"] = critical_cone_angle_deg(
                shape["bluntness_ratio"], shape["shoulder_ratio"]) + float(
                p["cone_half_angle_deg_above_critical"])
        reason = _valid_or_reason(shape, d)
        if reason:
            skipped.append({"source": "anchor:late", "label": str(p["name"]), **shape,
                            "reason": reason})
            continue
        for mach in (m_lo, m_hi):
            points.append(DesignPoint(f"dp{len(points):03d}", "anchor", "train", mach,
                                      diameter_m=d, label=str(p["name"]), **shape))

    # Mach extension (surface v2): appended AFTER everything above so no existing point is
    # renumbered. Every anchor SHAPE already in the design (the hull of the shape space) plus
    # the named extra shapes, at each extension Mach number. The fill design and the held-out
    # set are untouched: `inputs.mach.max` still bounds the Sobol fill.
    ext = des.get("mach_extension", {})
    if ext.get("enabled", False):
        ext_shapes = list(dict.fromkeys(
            (p.label, tuple(p.shape().items())) for p in points if p.role == "anchor"))
        ext_list = [(label, dict(items)) for label, items in ext_shapes]
        for p in ext.get("extra_shapes", []):
            shape = {k: float(p[k]) for k in SHAPE_INPUTS}
            reason = _valid_or_reason(shape, d)
            if reason:
                skipped.append({"source": "anchor:mach_extension", "label": str(p["name"]),
                                **shape, "reason": reason})
                continue
            ext_list.append((str(p["name"]), shape))
            if ext.get("extra_shapes_at_design_mach_max", False):
                points.append(DesignPoint(f"dp{len(points):03d}", "anchor", "train", m_hi,
                                          diameter_m=d, label=str(p["name"]), **shape))
        for mach in ext["mach"]:
            for label, shape in ext_list:
                points.append(DesignPoint(f"dp{len(points):03d}", "anchor", "train",
                                          float(mach), diameter_m=d,
                                          label=f"{label}@M{float(mach):g}", **shape))

    sc = cfg.get("scale_check", {})
    if sc.get("enabled", False):
        shape = {k: float(sc["shape"][k]) for k in SHAPE_INPUTS}
        for dia in (d, float(sc["diameter_m"])):
            points.append(DesignPoint(f"sc{dia:g}".replace(".", "p"), "scale_check", "check",
                                      float(sc["mach"]), diameter_m=dia,
                                      label=f"scale_D{dia:g}", **shape))
    return points, pd.DataFrame(skipped)


# ---------------------------------------------------------------------------------------
# Acceptance
# ---------------------------------------------------------------------------------------

def outer_outlet_mach(case_dir: Path, flow: FlowCondition, outer_fraction: float) -> dict:
    """Mach number on the outermost faces of the outflow plane, from the sampled patch."""
    t = _load_dat(_latest_sample(case_dir, "sampleOutlet", "T_outlet.raw"))
    u = _load_dat(_latest_sample(case_dir, "sampleOutlet", "U_outlet.raw"))
    radius = np.hypot(t[:, 1], t[:, 2])
    mach = np.linalg.norm(u[:, 3:6], axis=1) / np.sqrt(
        flow.gamma * flow.gas_constant_j_kgk * t[:, 3])
    r_in, r_out = float(radius.min()), float(radius.max())
    outer = radius >= r_out - outer_fraction * (r_out - r_in)
    return {"outer_outlet_min_mach": float(mach[outer].min()),
            "outer_outlet_n_faces": int(outer.sum())}


def assess_case(res: CaseResult, flow: FlowCondition, acc: dict[str, Any]) -> dict[str, Any]:
    """Apply the declared acceptance rules to one finished case. Pure bookkeeping."""
    out: dict[str, Any] = {"verdict": "", "reasons": [], "shock_clearance_ok": None}
    if res.status != "OK":
        out["verdict"] = res.status
        out["reasons"] = [res.failure_reason]
        return out
    m = res.metrics
    reasons = []
    conv = res.convergence.get("cd_fore", {})
    if acc.get("require_force_converged", True) and not conv.get("converged", False):
        reasons.append(
            f"force criterion not met (p2p {conv.get('peak_to_peak_rel')}, drift "
            f"{conv.get('drift_rel')}) after {m.get('n_extensions')} extensions")
    if not m["outlet_min_mach"] > float(acc["min_outlet_mach"]):
        reasons.append(f"outflow plane not supersonic: min Mach {m['outlet_min_mach']:.3f}")
    try:
        outer = outer_outlet_mach(Path(res.case_dir), flow, float(acc["outer_outlet_fraction"]))
    except (FileNotFoundError, ValueError) as exc:
        outer = {"outer_outlet_min_mach": float("nan"), "outer_outlet_n_faces": 0}
        reasons.append(f"outer-outlet check unavailable: {exc}")
    out.update(outer)
    deficit = 1.0 - outer["outer_outlet_min_mach"] / flow.mach
    out["outer_outlet_mach_deficit_rel"] = deficit
    clear_axis = m["upstream_clearance_fraction"] >= float(acc["min_upstream_clearance_fraction"])
    clear_outer = deficit <= float(acc["max_outer_outlet_mach_deficit_rel"])
    out["shock_clearance_ok"] = bool(clear_axis and clear_outer)
    if not clear_axis:
        reasons.append("bow shock too close to the inflow boundary on the axis: clearance "
                       f"{m['upstream_clearance_fraction']:.3f}")
    if not clear_outer:
        reasons.append("outermost outflow faces are not freestream (shock reached the "
                       f"inflow boundary?): Mach deficit {deficit:.4f}")
    pitot = rayleigh_pitot_ratio(flow.mach, flow.gamma)
    out["p_stag_rel_error_vs_rayleigh_pitot"] = m["p_stag_over_p_inf"] / pitot - 1.0
    out["verdict"] = USABLE if not reasons else "REJECTED"
    out["reasons"] = reasons
    return out


# ---------------------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------------------

def _load_case(path: Path) -> CaseResult | None:
    return CaseResult(**json.loads(path.read_text())) if path.exists() else None


LEVELS = {"coarse": 1, "medium": 2, "fine": 4}
"""Mesh level name -> refinement factor of the M2 sequence (configs/cfd_validation.yaml)."""


def _attempt_row(name: str, k: int, sizing: float, mesh: MeshSettings, res: CaseResult,
                 verdict: dict[str, Any], **extra: Any) -> dict[str, Any]:
    conv = res.convergence.get("cd_fore", {})
    return {"case": name, "attempt": k, "sizing_radius_m": sizing,
            "standoff_margin": mesh.standoff_margin,
            "asymptote_margin_deg": mesh.asymptote_margin_deg, "status": res.status,
            "n_cells": res.n_cells, "h_m": res.representative_cell_size_m,
            "solver_wall_time_s": res.solver_wall_time_s,
            "total_wall_time_s": res.total_wall_time_s,
            **{k2: v for k2, v in verdict.items() if k2 != "reasons"},
            "reasons": " | ".join(verdict["reasons"]), **res.metrics,
            "cd_fore_peak_to_peak_rel": conv.get("peak_to_peak_rel"),
            "cd_fore_drift_rel": conv.get("drift_rel"),
            "cd_fore_converged": conv.get("converged"), **extra}


def _only_force_criterion_missed(attempt: dict[str, Any]) -> bool:
    reasons = str(attempt["reasons"])
    return (attempt["verdict"] == "REJECTED"
            and reasons.startswith("force criterion not met") and "|" not in reasons)


def _passed_in_a_row(case_results_dir: Path, n: int) -> bool:
    """Did a Courant restart meet the force criterion at the end of its last `n` blocks?"""
    path = Path(case_results_dir) / "restart_blocks.json"
    if not path.exists():
        return False
    tail = json.loads(path.read_text())[-n:]
    return len(tail) == n and all(b["converged"] for b in tail)


def courant_case_name(point_id: str, level: str, max_co: float) -> str:
    return f"{point_id}_{level}_Co{max_co:g}".replace(".", "p")


def run_design_point(point: DesignPoint, cfg: dict[str, Any], val_cfg: dict[str, Any],
                     run_dir: Path, generated_root: Path, level: str) -> dict[str, Any]:
    """Run one design point, enlarging the domain and re-running if the shock is not clear.

    Every attempt is a separate case directory and a separate row of ``attempts``; nothing
    is overwritten. Returns the row for the design table.
    """
    factor = LEVELS[level]
    acc = cfg["acceptance"]
    retry = acc["domain_retry"]
    flow = _flow(val_cfg, point.mach)
    base_mesh = _mesh_settings(val_cfg, factor)
    solver = _solver_settings(val_cfg, factor)
    crit = ConvergenceCriterion(**val_cfg["convergence_criterion"])
    row: dict[str, Any] = {**asdict(point), "mesh_level": level, "attempts": 0,
                           "verdict": "", "reasons": ""}

    try:
        capsule = forebody_capsule(diameter_m=point.diameter_m, **point.shape())
        outline = capsule_outline(capsule, point.point_id)
    except ValueError as exc:                     # cannot happen for a planned point
        row.update(verdict="INVALID_GEOMETRY", reasons=str(exc))
        return row

    sizing = domain_sizing_radius_m(capsule, cfg["domain_sizing"])
    base_mesh = replace(base_mesh, asymptote_margin_deg=asymptote_margin_deg(
        capsule, point.mach, flow.gamma, cfg["domain_sizing"], base_mesh.asymptote_margin_deg))
    n_startup = int(cfg["startup"]["first_order_iterations_per_refinement_factor"]) * factor
    attempts = []
    for k in range(int(retry["max_retries"]) + 1):
        mesh: MeshSettings = replace(
            base_mesh,
            standoff_margin=base_mesh.standoff_margin * float(retry["standoff_margin_factor"]) ** k,
            asymptote_margin_deg=base_mesh.asymptote_margin_deg
            + k * float(retry["asymptote_margin_add_deg"]))
        name = f"{point.point_id}_{level}_a{k}"
        res = _load_case(run_dir / "cases" / name / "case_result.json")
        if res is None:
            try:
                res = run_case(name, outline, flow, mesh, solver, crit,
                               generated_root=generated_root, results_dir=run_dir / "cases",
                               sizing_radius_m=sizing,
                               solver_timeout_s=float(cfg["execution"]["solver_timeout_s"]),
                               startup_first_order_iterations=n_startup)
            except (ValueError, FileExistsError, RuntimeError) as exc:
                res = CaseResult(name, str(generated_root / name), "MESH_FAILED",
                                 failure_reason=f"{type(exc).__name__}: {exc}")
        verdict = assess_case(res, flow, acc)
        attempt = {"case": name, "attempt": k, "sizing_radius_m": sizing,
                   "standoff_margin": mesh.standoff_margin,
                   "asymptote_margin_deg": mesh.asymptote_margin_deg, "status": res.status,
                   "n_cells": res.n_cells, "h_m": res.representative_cell_size_m,
                   "solver_wall_time_s": res.solver_wall_time_s,
                   "total_wall_time_s": res.total_wall_time_s,
                   **{k2: v for k2, v in verdict.items() if k2 != "reasons"},
                   "reasons": " | ".join(verdict["reasons"]), **res.metrics,
                   "cd_fore_peak_to_peak_rel": res.convergence.get("cd_fore", {}).get(
                       "peak_to_peak_rel"),
                   "cd_fore_drift_rel": res.convergence.get("cd_fore", {}).get("drift_rel"),
                   "cd_fore_converged": res.convergence.get("cd_fore", {}).get("converged"),
                   "max_non_orthogonality_deg": res.mesh_quality.get(
                       "max_non_orthogonality_deg"),
                   "max_skewness": res.mesh_quality.get("max_skewness")}
        attempts.append(attempt)
        # A bigger domain cures a shock that reached the inflow boundary. That shows up
        # either as a failed clearance check or - when the shock is pinned on the
        # fixed-value patch hard enough - as a solver crash (NR-20), so both are retried.
        retryable = verdict["shock_clearance_ok"] is False or res.status == "SOLVER_FAILED"
        if verdict["verdict"] == USABLE or not retryable:
            break
    # -- patience pass -----------------------------------------------------------------------
    # A case rejected ONLY for missing the force criterion gets one more attempt with more
    # extensions. The criterion is untouched - M2's own rule: "the criterion never changes;
    # only how long we wait for it" (NR-09). The first attempt stays on disk and in the table.
    patience = acc.get("convergence_retry", {})
    last_reasons = attempts[-1]["reasons"]
    if (patience.get("enabled", False) and attempts[-1]["verdict"] == "REJECTED"
            and last_reasons.startswith("force criterion not met") and "|" not in last_reasons):
        solver_long = replace(solver, max_extensions=int(patience["max_extensions"]))
        name = f"{point.point_id}_{level}_c0"
        res = _load_case(run_dir / "cases" / name / "case_result.json")
        if res is None:
            try:
                res = run_case(name, outline, flow, mesh, solver_long, crit,
                               generated_root=generated_root, results_dir=run_dir / "cases",
                               sizing_radius_m=sizing,
                               solver_timeout_s=float(cfg["execution"]["solver_timeout_s"]),
                               startup_first_order_iterations=n_startup)
            except (ValueError, FileExistsError, RuntimeError) as exc:
                res = CaseResult(name, str(generated_root / name), "MESH_FAILED",
                                 failure_reason=f"{type(exc).__name__}: {exc}")
        verdict = assess_case(res, flow, acc)
        attempts.append({"case": name, "attempt": len(attempts), "sizing_radius_m": sizing,
                         "standoff_margin": mesh.standoff_margin,
                         "asymptote_margin_deg": mesh.asymptote_margin_deg,
                         "status": res.status, "n_cells": res.n_cells,
                         "h_m": res.representative_cell_size_m,
                         "solver_wall_time_s": res.solver_wall_time_s,
                         "total_wall_time_s": res.total_wall_time_s,
                         **{k2: v for k2, v in verdict.items() if k2 != "reasons"},
                         "reasons": " | ".join(verdict["reasons"]), **res.metrics,
                         "cd_fore_peak_to_peak_rel": res.convergence.get("cd_fore", {}).get(
                             "peak_to_peak_rel"),
                         "cd_fore_drift_rel": res.convergence.get("cd_fore", {}).get("drift_rel"),
                         "cd_fore_converged": res.convergence.get("cd_fore", {}).get(
                             "converged"),
                         "patience_pass": True})
    # -- Courant pass (surface v2; NR-25's lever applied to NR-21's cases) ---------------------
    # A case STILL rejected only for the force criterion is continued from its final solution
    # as a NEW, separately named case under each lower Courant limit in turn (spec §36 step 6)
    # - exactly what M2 did to its fine sphere cases. Criterion unchanged; never stops before
    # `min_blocks` blocks, so a pass is seen in two consecutive windows and the verdict of
    # record is the later one. The source case is never modified and stays in the table.
    cr = acc.get("courant_retry", {})
    if cr.get("enabled", False):
        for co in cr["max_co"]:
            if not _only_force_criterion_missed(attempts[-1]):
                break
            src_name = attempts[-1]["case"]
            name = courant_case_name(point.point_id, level, float(co))
            res = _load_case(run_dir / "cases" / name / "case_result.json")
            n_row = int(cr.get("consecutive_passes", 1))
            unfinished = res is not None and res.status == "OK" and (
                int(res.metrics.get("restart_blocks_run", 0)) < int(cr["min_blocks"])
                or (int(res.metrics.get("restart_blocks_run", 0)) < int(cr["max_blocks"])
                    and not _passed_in_a_row(run_dir / "cases" / name, n_row)))
            if res is None or unfinished:
                try:
                    res = restart_case(
                        name, generated_root / src_name, outline, flow, mesh,
                        replace(solver, max_co=float(co)), crit,
                        generated_root=generated_root, results_dir=run_dir / "cases",
                        block_iterations=int(cr["block_iterations"]),
                        max_blocks=int(cr["max_blocks"]), min_blocks=int(cr["min_blocks"]),
                        consecutive_passes=n_row, sizing_radius_m=sizing,
                        solver_timeout_s=float(cfg["execution"]["solver_timeout_s"]))
                except (ValueError, FileNotFoundError, RuntimeError) as exc:
                    res = CaseResult(name, str(generated_root / name), "MESH_FAILED",
                                     failure_reason=f"{type(exc).__name__}: {exc}")
            verdict = assess_case(res, flow, acc)
            if (verdict["verdict"] == USABLE
                    and not _passed_in_a_row(run_dir / "cases" / name, n_row)):
                # met the criterion in the LAST window only: not two in a row (NR-25's rule)
                verdict["verdict"] = "REJECTED"
                verdict["reasons"] = [
                    f"force criterion not met in {n_row} consecutive blocks (restart ran "
                    f"{res.metrics.get('restart_blocks_run')} blocks)"]
            attempts.append(_attempt_row(name, len(attempts), sizing, mesh, res, verdict,
                                         courant_pass=True, max_co=float(co),
                                         restart_source_case=src_name))
    row.update(attempts[-1])
    row["attempts"] = len(attempts)
    row["nose_radius_m"] = capsule.nose_radius_m
    row["shoulder_radius_m"] = capsule.shoulder_radius_m
    row["_attempt_rows"] = attempts
    return row


def mesh_check_ids(cfg: dict[str, Any], points: list[DesignPoint]) -> list[str]:
    """Design points re-run one mesh level finer, drawn with the design seed (not chosen by
    looking at results). Scale-check points are excluded."""
    mc = cfg["mesh_check"]
    late = {str(a["name"]) for a in cfg["design"].get("late_anchors", [])}
    # late anchors are excluded so that adding one never changes an already-drawn subset
    late |= {str(a["name"]) for a in cfg["design"].get("mach_extension", {}).get(
        "extra_shapes", [])}
    pool = [p.point_id for p in points if p.role != "scale_check" and p.label not in late
            and "@M" not in p.label]      # Mach-extension points never change the subset
    rng = np.random.default_rng(int(cfg["design"]["seed"]) + 1)
    picked = rng.choice(len(pool), size=min(int(mc["n_points"]), len(pool)), replace=False)
    forced = [pid for pid in mc.get("always_include", []) if pid in pool]
    return sorted(set(forced) | {pool[i] for i in picked})


def run_design(cfg: dict[str, Any], run_dir: Path, generated_root: Path, level: str,
               only: list[str] | None = None, progress=print) -> pd.DataFrame:
    """Run (or resume) the design at one mesh level, ``max_concurrent_cases`` serial solvers
    at a time. Tables are written per level: ``design_points_<level>.csv``."""
    val_cfg = load_config(REPO_ROOT / cfg["inherit"]["cfd_validation_config"])
    threads = str(int(cfg["execution"]["threads_per_case"]))
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS"):
        os.environ[var] = threads                 # inherited by every solver child process
    points, skipped = build_design(cfg)
    run_dir.mkdir(parents=True, exist_ok=True)
    skipped.to_csv(run_dir / "design_skipped.csv", index=False)
    pd.DataFrame([asdict(p) for p in points]).to_csv(run_dir / "design_planned.csv",
                                                     index=False)
    todo = [p for p in points if only is None or p.point_id in only]
    # Expensive-looking cases first does not matter for a serial pool; keep the plan order
    # except that the scale check and the anchors (which define the hull) go first.
    todo.sort(key=lambda p: {"scale_check": 0, "anchor": 1, "fill": 2}[p.role])
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=int(cfg["execution"]["max_concurrent_cases"])) as pool:
        futures = {pool.submit(run_design_point, p, cfg, val_cfg, run_dir, generated_root,
                               level): p for p in todo}
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            progress(f"[{len(rows):3d}/{len(todo)}] {row['point_id']} M={row['mach']:.2f} "
                     f"{row['verdict']:<10s} cd_fore={row.get('cd_fore', float('nan')):.5f} "
                     f"wall={row.get('solver_wall_time_s', float('nan')):.0f}s "
                     f"attempts={row['attempts']} {row['reasons']}")
            write_tables(rows, run_dir, level)
    return write_tables(rows, run_dir, level)


def write_tables(rows: list[dict], run_dir: Path, level: str) -> pd.DataFrame:
    attempts = [a for r in rows for a in r.get("_attempt_rows", [])]
    table = pd.DataFrame([{k: v for k, v in r.items() if k != "_attempt_rows"} for r in rows])
    if len(table):
        table = table.sort_values("point_id").reset_index(drop=True)
        table["gate_G4_status_at_build"] = gate_g4_status_at_build()
    table.to_csv(run_dir / f"design_points_{level}.csv", index=False)
    pd.DataFrame(attempts).to_csv(run_dir / f"attempts_{level}.csv", index=False)
    return table


def scale_check(table: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, Any]:
    """Is C_D,fore the same at two diameters? Read from the design table, never assumed."""
    rows = table[(table["role"] == "scale_check") & (table["verdict"] == USABLE)]
    out: dict[str, Any] = {"performed": False,
                           "tolerance": float(cfg["scale_check"]["max_rel_difference"])}
    if len(rows) == 2:
        a, b = rows.sort_values("diameter_m").itertuples()
        rel = abs(b.cd_fore - a.cd_fore) / a.cd_fore
        out.update(performed=True, diameters_m=[a.diameter_m, b.diameter_m],
                   cd_fore=[a.cd_fore, b.cd_fore], rel_difference=float(rel),
                   scale_invariant=bool(rel <= out["tolerance"]))
    return out
