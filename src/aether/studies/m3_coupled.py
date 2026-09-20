"""Milestone M3: coupled-model gate G5 and the constant-C_D vs CFD-surface comparison.

Conceptual anchor
-----------------
Swapping the drag model is supposed to be a config change. This study checks that it IS one
(same config -> identical result, and the result says which surface produced it), and then
asks the engineering question the swap was built for: how far do peak heat flux, bondline
temperature and peak deceleration move when a constant C_D is replaced by the CFD-derived
C_D(Mach, shape) - and does the capsule's SHAPE, which was aerodynamically inert at constant
C_D, now matter?

Everything goes through `evaluate_design`. The CFD-surface arm runs with
`allow_provisional: true` because gate G4 was IN_PROGRESS at build time; every row written
here carries the gate status the evaluator recorded.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..aerodynamics.cfd_surface import MODEL_NAME, SHAPE_INPUTS
from ..evaluate import DesignEvaluation, evaluate_design
from ..utils.run import REPO_ROOT, load_config

GATE_G4_STATUS_AT_BUILD = "IN_PROGRESS"
METRICS = ("peak_heat_flux_w_m2", "peak_bondline_temperature_k", "max_g",
           "integrated_external_heat_j_m2", "peak_surface_temperature_k",
           "max_dynamic_pressure_pa", "entry_duration_s")


# ---------------------------------------------------------------------------------------
# Configs
# ---------------------------------------------------------------------------------------

def capsule_config(base: dict[str, Any], capsule: dict[str, float], nose_model: str,
                   overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    d = float(capsule["diameter_m"])
    cfg["vehicle"]["geometry"] = {
        "nose_radius_m": capsule["bluntness_ratio"] * d, "diameter_m": d,
        "shoulder_radius_m": capsule["shoulder_ratio"] * d,
        "cone_half_angle_deg": float(capsule["cone_half_angle_deg"]),
        "aft_cone_angle_deg": float(capsule["aft_cone_angle_deg"]),
        "length_m": capsule["fineness_ratio"] * d,
        "effective_nose_radius_model": nose_model,
    }
    for dotted, value in (overrides or {}).items():
        node = cfg
        *parents, leaf = dotted.split(".")
        for key in parents:
            node = node[key]
        node[leaf] = value
    return cfg


def with_aero(cfg: dict[str, Any], arm: str, **aero: Any) -> dict[str, Any]:
    out = copy.deepcopy(cfg)
    if arm == "constant":
        out["vehicle"]["aero"] = {"model": "constant"}
    else:
        out["vehicle"]["aero"] = {"model": MODEL_NAME, "allow_provisional": True,
                                  "on_extrapolation": "flag", **aero}
    return out


def _row(label: str, arm: str, ev: DesignEvaluation) -> dict[str, Any]:
    perf = ev.performance
    row: dict[str, Any] = {"design": label, "arm": arm, "fidelity": ev.fidelity,
                           "status": perf.status, "feasible": perf.feasible}
    row.update({m: getattr(perf, m) for m in METRICS})
    row.update({k: v for k, v in ev.design_vector.items()
                if k in ("diameter_m", "nose_radius_m", "mass_kg", "cd",
                         "entry_flight_path_angle_deg", "cone_half_angle_deg",
                         "shoulder_radius_m")})
    row.update({k: v for k, v in ev.diagnostics.items() if k.startswith("aero_")})
    prov = ev.aero_provenance
    row["surface_training_hash"] = prov.get("surface_training_hash", "")
    row["gate_G4_status_at_build"] = prov.get("gate_G4_status_at_build", "")
    row["gate_G4_status_at_evaluation"] = prov.get("gate_G4_status_at_evaluation", "")
    return row


def fingerprint(ev: DesignEvaluation) -> str:
    """Hash of everything a result is judged on, bit for bit (floats via repr)."""
    perf = ev.performance
    payload = {
        "metrics": {m: repr(getattr(perf, m)) for m in METRICS},
        "margins": {k: repr(v) for k, v in sorted(perf.constraint_margins.items())},
        "feasible": perf.feasible, "status": perf.status,
        "diagnostics": {k: repr(v) for k, v in sorted(ev.diagnostics.items())},
        "provenance": json.dumps(ev.aero_provenance, sort_keys=True, default=str),
        "trajectory_sha": hashlib.sha256(
            np.ascontiguousarray(ev.trajectory.velocity_m_s).tobytes()).hexdigest()[:16],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------------------
# Gate G5
# ---------------------------------------------------------------------------------------

REQUIRED_PROVENANCE = ("aero_model", "surface_training_hash", "surface_source_run",
                       "gate_G4_status_at_build", "gate_G4_status_at_evaluation",
                       "shape_extrapolated", "mach_range", "provisional", "mesh_level",
                       "discretisation_band_available")
REQUIRED_DIAGNOSTICS = ("aero_shape_extrapolated", "aero_heat_fraction_below_cfd_mach",
                        "aero_heat_fraction_above_cfd_mach", "aero_time_fraction_below_cfd_mach",
                        "aero_time_fraction_above_cfd_mach")


def gate_g5(cfg_surface: dict[str, Any], repeats: int) -> dict[str, Any]:
    evals = [evaluate_design(copy.deepcopy(cfg_surface)) for _ in range(repeats)]
    prints = [fingerprint(e) for e in evals]
    prov, diag = evals[0].aero_provenance, evals[0].diagnostics
    missing_prov = [k for k in REQUIRED_PROVENANCE if k not in prov]
    missing_diag = [k for k in REQUIRED_DIAGNOSTICS if k not in diag]
    checks = {
        "deterministic": len(set(prints)) == 1,
        "design_id_stable": len({e.design_id for e in evals}) == 1,
        "fidelity_is_1": all(e.fidelity == 1 for e in evals),
        "provenance_complete": not missing_prov,
        "extrapolation_flags_recorded": not missing_diag,
        "gate_status_recorded": prov.get("gate_G4_status_at_build") == GATE_G4_STATUS_AT_BUILD,
    }
    return {"gate": "G5", "checks": checks, "all_checks_met": all(checks.values()),
            "fingerprints": prints, "missing_provenance": missing_prov,
            "missing_diagnostics": missing_diag, "provenance_example": prov,
            "repeats": repeats,
            # G5 can be no better than the gate it stands on.
            "status": "LIMITED" if all(checks.values()) else "FAIL",
            "status_reason": ("determinism and provenance checks met, but the drag surface is "
                              "PROVISIONAL (G4 IN_PROGRESS at build, coarse mesh) - see report")
            if all(checks.values()) else "one or more checks failed"}


# ---------------------------------------------------------------------------------------
# The study
# ---------------------------------------------------------------------------------------

def _m4_front_designs(run: Path, n: int) -> list[tuple[str, dict[str, Any]]]:
    """n designs evenly spaced along the M4 combined feasible front, as full configs."""
    from ..optimization.analysis import feasible_front
    from ..optimization.design_space import DesignSpace, DesignVariable

    frame = pd.read_parquet(run / "candidates.parquet")
    summary = json.loads((run / "summary.json").read_text())
    snapshot = load_config(run / "config_snapshot.yaml")["config"]
    variables = tuple(
        DesignVariable(name, str(s["kind"]), str(s["path"]), str(s.get("units", "")),
                       str(s["role"]), float(s["min"]), float(s["max"]), float(s["reference"]))
        for name, s in snapshot["study"]["variables"].items())
    space = DesignSpace(variables, tuple(v.name for v in variables), snapshot["base"])
    front = feasible_front(frame, tuple(summary["objectives"])).sort_values(
        "peak_heat_flux_w_m2").reset_index(drop=True)
    picks = np.unique(np.linspace(0, len(front) - 1, n).round().astype(int))
    out = []
    for i in picks:
        row = front.iloc[i]
        values = {c[3:]: float(row[c]) for c in front.columns if c.startswith("x__")}
        out.append((f"M4:{row['candidate_id']}", copy.deepcopy(space.config_for(values))))
    return out


MACH_BANDS = ((0.0, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 10.0), (10.0, 20.0), (20.0, 99.0))


def mach_band_table(ev: DesignEvaluation, label: str) -> pd.DataFrame:
    """Where in Mach the entry actually happens: share of heat load and of flight time per
    Mach band, plus the Mach number at peak heating and at peak deceleration. This is the
    evidence for the CFD Mach range and for holding the boundary values outside it."""
    traj, q = ev.trajectory, ev.heat_flux_w_m2
    t, mach = traj.time_s, traj.mach
    load = float(np.trapezoid(q, t))
    rows = []
    for lo, hi in MACH_BANDS:
        mask = (mach >= lo) & (mach < hi)
        rows.append({"design": label, "mach_lo": lo, "mach_hi": hi,
                     "heat_load_fraction": float(np.trapezoid(np.where(mask, q, 0.0), t) / load),
                     "time_s": float(np.trapezoid(mask.astype(float), t)),
                     "mach_at_peak_heating": float(mach[int(np.argmax(q))]),
                     "mach_at_peak_g": float(mach[int(np.argmax(traj.deceleration_g))]),
                     "mach_at_entry": float(mach[0]), "mach_max": float(mach.max()),
                     "mach_at_end": float(mach[-1])})
    return pd.DataFrame(rows)


def run_study(cfg: dict[str, Any], run_dir: Path, progress=print,
              inclusive_surface_dir: Path | None = None) -> dict[str, Any]:
    c = cfg["coupled"]
    base = load_config(REPO_ROOT / c["base_config"])
    nose_model = str(c["effective_nose_radius_model"])
    ref_cfg = capsule_config(base, c["reference_capsule"], nose_model)
    run_dir.mkdir(parents=True, exist_ok=True)

    # -- G5 --------------------------------------------------------------------------------
    gate = gate_g5(with_aero(ref_cfg, "surface"), int(c["determinism_repeats"]))
    (run_dir / "gate_G5.json").write_text(json.dumps(gate, indent=2, default=str))
    progress(f"G5 checks: {gate['checks']}")

    # -- constant C_D vs surface -------------------------------------------------------------
    designs = [("baseline_capsule", ref_cfg)]
    designs += _m4_front_designs(REPO_ROOT / c["m4_run"], int(c["m4_front_n"]))
    rows, bands = [], []
    for label, dcfg in designs:
        dcfg = copy.deepcopy(dcfg)
        dcfg["vehicle"]["geometry"]["effective_nose_radius_model"] = nose_model
        for arm in ("constant", "surface"):
            ev = evaluate_design(with_aero(dcfg, arm))
            rows.append(_row(label, arm, ev))
            if arm == "constant" and ev.trajectory is not None:
                bands.append(mach_band_table(ev, label))
        if inclusive_surface_dir is not None:
            rows.append(_row(label, "surface_inclusive", evaluate_design(with_aero(
                dcfg, "surface", surface_dir=str(inclusive_surface_dir)))))
        progress(f"compared {label}")
    pd.concat(bands).to_csv(run_dir / "mach_bands_constant_cd.csv", index=False)
    comparison = pd.DataFrame(rows)
    comparison.to_csv(run_dir / "constant_vs_surface.csv", index=False)

    # -- does shape matter? ------------------------------------------------------------------
    sweep = c["shape_sweep"]
    rows = []
    for b in sweep["bluntness_ratio"]:
        for theta in sweep["cone_half_angle_deg"]:
            capsule = {**c["reference_capsule"], "bluntness_ratio": float(b),
                       "cone_half_angle_deg": float(theta),
                       "fineness_ratio": float(sweep["fineness_ratio"])}
            scfg = capsule_config(base, capsule, nose_model)
            for arm in ("constant", "surface"):
                row = _row(f"b{b:g}_t{theta:g}", arm, evaluate_design(with_aero(scfg, arm)))
                row.update(bluntness_ratio=float(b), cone_half_angle_deg=float(theta))
                rows.append(row)
    shape = pd.DataFrame(rows)
    shape.to_csv(run_dir / "shape_sweep.csv", index=False)
    progress("shape sweep done")

    # -- sensitivity of the objectives to what the surface cannot know ------------------------
    rows = [_row("baseline_capsule", "surface:nominal",
                 evaluate_design(with_aero(ref_cfg, "surface")))]
    for scale in c["low_mach_hold_test"]["scale_factors"]:
        rows.append(_row("baseline_capsule", f"surface:low_mach_x{scale:g}", evaluate_design(
            with_aero(ref_cfg, "surface", test_low_mach_scale=float(scale)))))
    for name, unc in (("u_base=+1", {"u_base": 1.0}), ("u_base=-1", {"u_base": -1.0}),
                      ("z_gp=+2", {"z_gp": 2.0}), ("z_gp=-2", {"z_gp": -2.0}),
                      ("u_model_form=+1", {"u_model_form": 1.0}),
                      ("u_model_form=-1", {"u_model_form": -1.0})):
        rows.append(_row("baseline_capsule", f"surface:{name}", evaluate_design(
            with_aero(ref_cfg, "surface", uncertainty=unc))))
    sens = pd.DataFrame(rows)
    sens.to_csv(run_dir / "surface_sensitivity.csv", index=False)

    summary = summarise(comparison, shape, sens, gate)
    summary["inclusive_surface_used"] = inclusive_surface_dir is not None
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


def _rel(a: float, b: float) -> float:
    return float(b / a - 1.0)


def summarise(comparison: pd.DataFrame, shape: pd.DataFrame, sens: pd.DataFrame,
              gate: dict[str, Any]) -> dict[str, Any]:
    moves = []
    for design, grp in comparison.groupby("design", sort=False):
        g = grp.set_index("arm")
        if not {"constant", "surface"} <= set(g.index):
            continue
        k, s = g.loc["constant"], g.loc["surface"]
        moves.append({
            "design": design,
            "cd_constant": float(k["cd"]),
            "cd_surface_at_peak_heating": float(s["aero_cd_at_peak_heating"]),
            "shape_extrapolated": bool(s["aero_shape_extrapolated"]),
            "peak_heat_flux_rel_change": _rel(k["peak_heat_flux_w_m2"], s["peak_heat_flux_w_m2"]),
            "peak_bondline_change_k": float(s["peak_bondline_temperature_k"]
                                            - k["peak_bondline_temperature_k"]),
            "max_g_rel_change": _rel(k["max_g"], s["max_g"]),
            "heat_load_rel_change": _rel(k["integrated_external_heat_j_m2"],
                                         s["integrated_external_heat_j_m2"]),
            "feasible_constant": bool(k["feasible"]), "feasible_surface": bool(s["feasible"]),
            "heat_fraction_below_cfd_mach": float(s["aero_heat_fraction_below_cfd_mach"]),
            "heat_fraction_above_cfd_mach": float(s["aero_heat_fraction_above_cfd_mach"]),
        })
        if "surface_inclusive" in g.index:
            i = g.loc["surface_inclusive"]
            moves[-1].update({
                "inclusive_shape_extrapolated": bool(i["aero_shape_extrapolated"]),
                "inclusive_cd_at_peak_heating": float(i["aero_cd_at_peak_heating"]),
                "inclusive_peak_heat_flux_rel_change": _rel(k["peak_heat_flux_w_m2"],
                                                            i["peak_heat_flux_w_m2"]),
                "inclusive_peak_bondline_change_k": float(i["peak_bondline_temperature_k"]
                                                          - k["peak_bondline_temperature_k"]),
                "inclusive_max_g_rel_change": _rel(k["max_g"], i["max_g"]),
            })

    # Shape effect THROUGH DRAG ALONE: for each swept shape, surface arm relative to the
    # constant arm of the SAME shape (the heating model's own shape dependence cancels).
    ok = shape[shape["status"].astype(str).str.len() > 0]
    piv = ok.pivot_table(index=["bluntness_ratio", "cone_half_angle_deg"], columns="arm",
                         values=["peak_heat_flux_w_m2", "peak_bondline_temperature_k", "max_g",
                                 "aero_cd_at_peak_heating", "aero_shape_extrapolated"],
                         aggfunc="first")
    inside = piv[piv[("aero_shape_extrapolated", "surface")] == 0.0].dropna(
        subset=[("peak_heat_flux_w_m2", "surface"), ("peak_heat_flux_w_m2", "constant")])
    shape_effect: dict[str, Any] = {"n_shapes_in_hull": int(len(inside)),
                                    "n_shapes_swept": int(len(piv))}
    if len(inside):
        ratio = inside[("peak_heat_flux_w_m2", "surface")] / inside[
            ("peak_heat_flux_w_m2", "constant")] - 1.0
        dbond = inside[("peak_bondline_temperature_k", "surface")] - inside[
            ("peak_bondline_temperature_k", "constant")]
        gratio = inside[("max_g", "surface")] / inside[("max_g", "constant")] - 1.0
        cd = inside[("aero_cd_at_peak_heating", "surface")]
        shape_effect.update({
            "cd_at_peak_heating_min": float(cd.min()), "cd_at_peak_heating_max": float(cd.max()),
            "peak_flux_change_via_drag_min": float(ratio.min()),
            "peak_flux_change_via_drag_max": float(ratio.max()),
            "peak_flux_spread_via_drag": float(ratio.max() - ratio.min()),
            "bondline_change_via_drag_min_k": float(dbond.min()),
            "bondline_change_via_drag_max_k": float(dbond.max()),
            "bondline_spread_via_drag_k": float(dbond.max() - dbond.min()),
            "max_g_change_via_drag_min": float(gratio.min()),
            "max_g_change_via_drag_max": float(gratio.max()),
            # at constant C_D the spread via drag is identically zero
            "shape_matters_through_drag": bool(ratio.max() - ratio.min() > 0.0),
        })

    nominal = sens[sens["arm"] == "surface:nominal"].iloc[0]
    sens_rows = []
    for _, r in sens[sens["arm"] != "surface:nominal"].iterrows():
        sens_rows.append({
            "case": r["arm"],
            "peak_heat_flux_rel_change": _rel(nominal["peak_heat_flux_w_m2"],
                                              r["peak_heat_flux_w_m2"]),
            "peak_bondline_change_k": float(r["peak_bondline_temperature_k"]
                                            - nominal["peak_bondline_temperature_k"]),
            "max_g_rel_change": _rel(nominal["max_g"], r["max_g"]),
        })
    return {"gate_G4_status_at_build": GATE_G4_STATUS_AT_BUILD,
            "gate_G5": {k: gate[k] for k in ("status", "status_reason", "checks",
                                             "all_checks_met")},
            "surface_training_hash": gate["provenance_example"].get("surface_training_hash"),
            "constant_vs_surface": moves, "shape_effect": shape_effect,
            "sensitivity_baseline_capsule": sens_rows,
            "shape_inputs": list(SHAPE_INPUTS)}
