"""Build, validate and persist `cfd_surface_v1` from a CFD design-point run (spec §25).

Two questions, kept apart (as in `surrogate/validation.py`): how ACCURATE is the surface on
CFD cases it never saw, and how HONEST is its error bar. Both are answered twice:

  held-out test   the fill points marked `split == 'test'` BEFORE any case ran. The model
                  scored on them is fitted on the training split only.
  k-fold CV       every usable point is predicted once by a model that did not see it.
                  Anchor points are hull vertices, so a fold that holds one out must
                  extrapolate to predict it; those predictions are reported separately.

The surface that is SAVED is fitted on all usable points (train + test): with a few dozen
CFD cases, throwing a fifth of them away to keep a test set pristine would cost more accuracy
than it buys. The held-out numbers therefore describe a slightly WEAKER model than the one
shipped, which is the conservative direction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..surrogate.gp import GPSurrogate
from ..surrogate.validation import holdout_validation, regression_metrics
from ..utils.run import REPO_ROOT
from .base_drag import BaseDragModel
from .cfd_surface import (
    MODEL_NAME,
    SHAPE_INPUTS,
    SURFACE_DIR,
    CfdDragSurface,
    discretisation_band,
    gate_g4_status,
)

GATE_G4_STATUS_AT_BUILD = "IN_PROGRESS"
USABLE = "USABLE"


def usable_points(table: pd.DataFrame) -> pd.DataFrame:
    """Rows the surface may be trained on: accepted verdict, a design (not check) point."""
    keep = (table["verdict"] == USABLE) & (table["role"] != "scale_check")
    return table[keep].reset_index(drop=True)


def bounded_unconverged_points(table: pd.DataFrame, max_p2p_rel: float) -> pd.DataFrame:
    """Cases that ran cleanly and passed every acceptance rule EXCEPT the force-convergence
    criterion, and whose C_D,fore stayed inside a `max_p2p_rel` band over the final window.

    They are NOT usable by the declared rules and never enter `cfd_surface_v1`. They feed
    only the clearly labelled INCLUSIVE sensitivity surface, which exists to answer one
    question: how different would the answer be in the corner of the shape space that the
    strict rules removed?"""
    reasons = table["reasons"].fillna("").astype(str)
    only_force = reasons.str.startswith("force criterion not met") & ~reasons.str.contains(
        r"\|", regex=True)
    keep = ((table["verdict"] == "REJECTED") & only_force & (table["role"] != "scale_check")
            & (table["cd_fore_peak_to_peak_rel"] <= max_p2p_rel))
    return table[keep].reset_index(drop=True)


def build_inclusive(run_dir: Path, cfg: dict[str, Any], surface_cfg: dict[str, Any],
                    level: str) -> dict[str, Any] | None:
    """Fit the INCLUSIVE sensitivity surface into `<run>/surface_<level>_inclusive/`."""
    inc = surface_cfg.get("inclusive_sensitivity", {})
    if not inc.get("enabled", False):
        return None
    table = pd.read_csv(run_dir / f"design_points_{level}.csv")
    extra = bounded_unconverged_points(table, float(inc["max_peak_to_peak_rel"]))
    if extra.empty:
        return None
    rows = pd.concat([usable_points(table), extra], ignore_index=True)
    meta = _meta(cfg, run_dir.name, level, surface_cfg)
    meta["variant"] = "INCLUSIVE-SENSITIVITY: contains cases that FAILED the convergence rule"
    CfdDragSurface(rows, meta).save(run_dir / f"surface_{level}_inclusive")
    extra[["point_id", "mach", *SHAPE_INPUTS, "cd_fore", "cd_fore_peak_to_peak_rel",
           "cd_fore_drift_rel"]].to_csv(run_dir / f"inclusive_extra_points_{level}.csv",
                                        index=False)
    return {"n_extra": int(len(extra)), "extra_point_ids": extra["point_id"].tolist(),
            "max_peak_to_peak_rel_allowed": float(inc["max_peak_to_peak_rel"]),
            "n_train": int(len(rows))}


def _meta(cfg: dict[str, Any], run_id: str, level: str, surface_cfg: dict[str, Any]) -> dict:
    inp = cfg["inputs"]
    return {
        "model": MODEL_NAME,
        "gate_G4_status_at_build": GATE_G4_STATUS_AT_BUILD,
        "gate_G4_status_read_at_build": gate_g4_status(),
        "provisional": True,
        "source_run": run_id,
        "mesh_level": level,
        "seed": int(cfg["design"]["seed"]),
        "input_ranges": {"mach": [inp["mach"]["min"], inp["mach"]["max"]],
                         **{k: [inp[k]["min"], inp[k]["max"]] for k in SHAPE_INPUTS}},
        "gas_model": "calorically perfect, gamma = 1.4, inviscid, alpha = 0 (A-CFD-1..3)",
        "model_form_rel_halfband": float(surface_cfg["model_form_rel_halfband"]),
        "base_drag": BaseDragModel().to_dict(),
    }


def _xy(surface: CfdDragSurface, rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return (surface.unit(rows["mach"], rows[list(SHAPE_INPUTS)].to_numpy()),
            rows["cd_fore"].to_numpy())


def k_fold(surface: CfdDragSurface, rows: pd.DataFrame, k: int, seed: int) -> pd.DataFrame:
    """Out-of-fold predictions for every usable point."""
    x, y = _xy(surface, rows)
    order = np.random.default_rng(seed).permutation(len(rows))
    out = []
    for f, idx in enumerate(np.array_split(order, k)):
        train = np.setdiff1d(order, idx)
        gp = GPSurrogate("cd_fore", seed=seed, n_restarts=4).fit(x[train], y[train])
        pred = gp.predict(x[idx], on_extrapolation="flag")
        for j, i in enumerate(idx):
            out.append({"point_id": rows["point_id"].iloc[i], "fold": f,
                        "role": rows["role"].iloc[i], "mach": rows["mach"].iloc[i],
                        "cd_fore_cfd": y[i], "cd_fore_pred": float(pred.mean[j]),
                        "cd_fore_std": float(pred.std[j]),
                        "outside_fold_hull": bool(pred.extrapolated[j])})
    return pd.DataFrame(out).sort_values("point_id").reset_index(drop=True)


def _metrics_block(frame: pd.DataFrame) -> dict[str, Any]:
    def block(sub: pd.DataFrame) -> dict[str, Any]:
        m = regression_metrics(sub["cd_fore_cfd"], sub["cd_fore_pred"], sub["cd_fore_std"])
        if m.get("n", 0):
            m["rmse_rel_to_mean_cd"] = m["rmse"] / float(sub["cd_fore_cfd"].mean())
            m["max_abs_error"] = float((sub["cd_fore_pred"] - sub["cd_fore_cfd"]).abs().max())
        return m
    inside = frame[~frame["outside_fold_hull"]]
    return {"all": block(frame), "inside_hull": block(inside),
            "outside_hull": block(frame[frame["outside_fold_hull"]])}


def mesh_check_table(coarse: pd.DataFrame, finer: pd.DataFrame | None) -> pd.DataFrame:
    """Same design point on two mesh levels: the measured discretisation change."""
    if finer is None or finer.empty:
        return pd.DataFrame()
    a = coarse[coarse["verdict"] == USABLE].set_index("point_id")
    b = finer[finer["verdict"] == USABLE].set_index("point_id")
    both = a.index.intersection(b.index)
    out = pd.DataFrame({
        "point_id": both, "mach": a.loc[both, "mach"].to_numpy(),
        **{k: a.loc[both, k].to_numpy() for k in SHAPE_INPUTS},
        "cd_fore_coarse": a.loc[both, "cd_fore"].to_numpy(),
        "cd_fore_finer": b.loc[both, "cd_fore"].to_numpy(),
        "finer_level": b.loc[both, "mesh_level"].to_numpy(),
    })
    out["rel_change"] = out["cd_fore_finer"] / out["cd_fore_coarse"] - 1.0
    return out


def mach_independence_table(surface: CfdDragSurface, shapes: dict[str, dict[str, float]],
                            mach_pairs=((10.0, 20.0), (6.0, 20.0))) -> pd.DataFrame:
    """How much C_D,fore still changes over the top of the CFD Mach range, per shape.
    This is the measured basis for HOLDING the top value above the range."""
    rows = []
    for name, shape in shapes.items():
        for lo, hi in mach_pairs:
            if lo < surface.mach_min or hi > surface.mach_max:
                continue
            p = surface.predict_fore(np.array([lo, hi]), shape, on_extrapolation="flag")
            rows.append({"shape": name, "mach_lo": lo, "mach_hi": hi,
                         "cd_fore_lo": float(p.central[0]), "cd_fore_hi": float(p.central[1]),
                         "rel_change": float(p.central[1] / p.central[0] - 1.0),
                         "extrapolated": bool(np.any(p.extrapolated))})
    return pd.DataFrame(rows)


def base_fraction_table(surface: CfdDragSurface, shapes: dict[str, dict[str, float]],
                        machs=(3.0, 4.0, 6.0, 8.0, 10.0, 15.0, 20.0)) -> pd.DataFrame:
    rows = []
    for name, shape in shapes.items():
        m = np.array([x for x in machs if surface.mach_min <= x <= surface.mach_max])
        p = surface.predict_fore(m, shape, on_extrapolation="flag")
        lo, nom, hi = surface.base.band(m)
        for i, mach in enumerate(m):
            fore = float(p.central[i])
            rows.append({"shape": name, "mach": float(mach), "cd_fore": fore,
                         "cd_base_low": float(lo[i]), "cd_base_nominal": float(nom[i]),
                         "cd_base_high": float(hi[i]),
                         "base_fraction_low": float(lo[i] / (fore + lo[i])),
                         "base_fraction_nominal": float(nom[i] / (fore + nom[i])),
                         "base_fraction_high": float(hi[i] / (fore + hi[i])),
                         "extrapolated": bool(p.extrapolated[i])})
    return pd.DataFrame(rows)


def build(run_dir: Path, cfg: dict[str, Any], surface_cfg: dict[str, Any], level: str,
          save_to: Path | None = SURFACE_DIR) -> dict[str, Any]:
    """Fit + validate + persist. Returns the summary that is also written to disk."""
    table = pd.read_csv(run_dir / f"design_points_{level}.csv")
    rows = usable_points(table)
    seed = int(cfg["design"]["seed"])
    if len(rows) < int(surface_cfg["min_usable_points"]):
        raise RuntimeError(f"only {len(rows)} usable CFD points; refusing to fit a surface")
    surface = CfdDragSurface(rows, _meta(cfg, run_dir.name, level, surface_cfg))

    # -- held-out test ---------------------------------------------------------------------
    train, test = rows[rows["split"] == "train"], rows[rows["split"] == "test"]
    holdout: dict[str, Any] = {"n_test_planned": int(cfg["design"]["holdout"]["n_test"]),
                               "n_test_usable": int(len(test))}
    if len(test) >= 2:
        holdout.update(holdout_validation(
            GPSurrogate("cd_fore", seed=seed, n_restarts=4), *_xy(surface, train),
            *_xy(surface, test)))

    # -- k-fold ----------------------------------------------------------------------------
    folds = k_fold(surface, rows, int(surface_cfg["k_folds"]), seed)
    folds.to_csv(run_dir / f"surface_cv_predictions_{level}.csv", index=False)

    shapes = {str(s["name"]): {k: float(s[k]) for k in SHAPE_INPUTS}
              for s in surface_cfg["report_shapes"]}
    finer_path = run_dir / f"design_points_{surface_cfg['mesh_check_level']}.csv"
    finer = pd.read_csv(finer_path) if finer_path.exists() and \
        surface_cfg["mesh_check_level"] != level else None
    mesh = mesh_check_table(table, finer)
    mesh.to_csv(run_dir / f"mesh_check_{level}.csv", index=False)
    mach_ind = mach_independence_table(surface, shapes)
    mach_ind.to_csv(run_dir / f"mach_independence_{level}.csv", index=False)
    base = base_fraction_table(surface, shapes)
    base.to_csv(run_dir / f"base_drag_fraction_{level}.csv", index=False)

    z_std = _metrics_block(folds)["all"].get("z_std", float("nan"))
    surface.meta["sigma_inflation"] = float(max(1.0, z_std)) if np.isfinite(z_std) else 1.0
    surface.meta["sigma_inflation_basis"] = "k-fold z-score std over all usable points"
    surface.save(run_dir / f"surface_{level}")
    if save_to is not None:
        surface.save(save_to)

    inclusive = build_inclusive(run_dir, cfg, surface_cfg, level)
    verdicts = table[table["role"] != "scale_check"]["verdict"].value_counts().to_dict()
    summary = {
        "model": MODEL_NAME, "run_id": run_dir.name, "mesh_level": level,
        "gate_G4_status_at_build": GATE_G4_STATUS_AT_BUILD,
        "gate_G4_status_read_at_build": gate_g4_status(),
        "provisional": True,
        "n_design_points": int((table["role"] != "scale_check").sum()),
        "verdicts": verdicts, "n_usable": int(len(rows)),
        "training_hash": surface.meta["training_hash"],
        "kernel_theta": surface.meta["kernel_theta"],
        "hull_defined": bool(surface.gp.hull.defined),
        "sigma_inflation": surface.meta["sigma_inflation"],
        "inclusive_sensitivity_surface": inclusive,
        "holdout": holdout,
        "k_fold": {"k": int(surface_cfg["k_folds"]), **_metrics_block(folds)},
        "mesh_check": ({"n": int(len(mesh)),
                        "finer_level": surface_cfg["mesh_check_level"],
                        "max_abs_rel_change": float(mesh["rel_change"].abs().max()),
                        "mean_rel_change": float(mesh["rel_change"].mean())}
                       if len(mesh) else {"n": 0}),
        "discretisation_band_hook": discretisation_band(level),
        "model_form_rel_halfband_declared": float(surface_cfg["model_form_rel_halfband"]),
        "cd_fore_range": [float(rows["cd_fore"].min()), float(rows["cd_fore"].max())],
        "saved_to": str(save_to.relative_to(REPO_ROOT)) if save_to is not None else None,
    }
    (run_dir / f"surface_summary_{level}.json").write_text(
        json.dumps(summary, indent=2, default=str))
    return summary
