"""`cfd_surface_v1`: the CFD-derived drag response surface (spec §18, §25), Fidelity 1.

Conceptual anchor
-----------------
    C_D(M, shape) = C_D,fore(M, shape)      Gaussian process through converged CFD cases
                  + C_D,base(M)             stated assumption with a band (base_drag.py)

The trajectory integrator never calls CFD and never calls the GP either: for ONE capsule the
shape is fixed for the whole entry, so the GP is evaluated once on a grid of Mach numbers and
the integrator gets a smooth 1-D interpolant in log(Mach). That is what makes a coupled
evaluation cost the same as a constant-C_D one.

Where the surface may be used, and what happens elsewhere (spec §25: never silently)
------------------------------------------------------------------------------------
* SHAPE outside the convex hull of the CFD design: refused. The builder raises
  `ExtrapolationError`; `evaluate_design` turns that into a rejected candidate that stays in
  the log (`on_extrapolation: flag` overrides, and the result then carries the flag).
* MACH above the highest CFD Mach: the value at the highest CFD Mach is HELD. Justified by
  Mach-number independence of blunt-body pressure drag, and measured on this surface itself
  (the report prints how much C_D,fore still changes over the top of the range).
* MACH below the lowest CFD Mach: the value at the lowest CFD Mach is HELD. This is a
  modelling convenience, not physics - transonic/subsonic capsule drag is base-dominated and
  this model says nothing about it. It is tolerable only because that part of the entry
  carries a negligible share of the heating; the report quantifies the share and the effect
  on every objective of perturbing the held value.
  Both are reported on every evaluation as the fraction of heat load and of flight time
  spent outside the CFD Mach range.

Uncertainty, exposed for M7 (all default to the nominal surface)
----------------------------------------------------------------
    C_D = C_D,fore * (1 + z_disc * s_disc + u_form * h_form) + z_gp * s_gp(M) + C_D,base(M; u_base)

    z_gp    N(0,1)   GP predictive std of C_D,fore at this shape, WIDENED by the k-fold
                     z-score spread measured at build time when that exceeds 1 (one draw per
                     trajectory: the surface error is a smooth function of Mach, not noise)
    z_disc  N(0,1)   s_disc = (GCI of the surface's mesh level) / 2, M2 sphere study, READ by
                     `discretisation_band`. None until M2 has produced it - then z_disc != 0
                     is an error, never a silent zero.
    u_form  U(-1,1)  h_form: declared perfect-gas model-form half-band (A-CFD-1). An
                     argument from theory, NOT validated here.
    u_base  U(-1,1)  position in the base-pressure band.

Gate
----
A surface built while G4 was not PASS is PROVISIONAL. The builder refuses to serve it unless
the config says `allow_provisional: true`, and every result records the gate status both at
build time and at evaluation time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

from ..utils.run import REPO_ROOT
from .base_drag import BaseDragModel

MODEL_NAME = "cfd_surface_v1"
SURFACE_DIR = REPO_ROOT / "data" / "aero" / MODEL_NAME
SHAPE_INPUTS = ("bluntness_ratio", "cone_half_angle_deg", "shoulder_ratio")
INPUTS = ("log_mach", *SHAPE_INPUTS)
N_MACH_NODES = 48
M2_RESULTS = REPO_ROOT / "results" / "M2"


class GateNotPassedError(RuntimeError):
    """A CFD-derived model was requested while validation gate G4 is not PASS."""


# ---------------------------------------------------------------------------------------
# Hooks into M2 - read at call time, never typed
# ---------------------------------------------------------------------------------------

def _latest_m2_file(name: str, root: Path = M2_RESULTS) -> Path | None:
    hits = sorted(p for p in root.glob(f"M2-*/{name}") if p.is_file())
    return hits[-1] if hits else None


def gate_g4_status(root: Path = M2_RESULTS) -> dict[str, Any]:
    """Status of gate G4 as the latest M2 run's `gate_assessment.json` states it."""
    path = _latest_m2_file("gate_assessment.json", root)
    if path is None:
        return {"status": "NOT_STARTED", "source": None}
    return {"status": str(json.loads(path.read_text()).get("status", "UNKNOWN")),
            "source": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT)
            else str(path)}


def discretisation_band(level: str = "medium", root: Path = M2_RESULTS,
                        quantity: str = "cd_fore") -> dict[str, Any]:
    """*** GCI HOOK *** Relative discretisation band of mesh `level`, from M2's gci.csv.

    Nothing is typed here: the band is computed from the latest `results/M2/<run>/gci.csv`.
        fine / medium   the file's `gci_fine` / `gci_medium` columns (Celik et al. 2008)
        coarse          1.25 * |phi_coarse - phi_extrapolated| / |phi_extrapolated|, the same
                        safety factor applied to the Richardson error estimate of the
                        coarse mesh (the file carries no gci_coarse column)
    Returns {'available': False, ...} until the M2 fine-mesh cases exist. The largest value
    over the benchmark Mach numbers is used. Transferring a SPHERE's GCI to a capsule on the
    same mesh family is an assumption (A-CFD-9).
    """
    path = _latest_m2_file("gci.csv", root)
    out: dict[str, Any] = {"available": False, "rel_band": None, "source": None,
                           "quantity": quantity, "mesh_level": level}
    if level not in ("coarse", "medium", "fine"):
        raise ValueError(f"unknown mesh level {level!r}")
    if path is None or path.stat().st_size < 5:
        return out
    try:
        table = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return out
    if "quantity" not in table.columns:
        return out
    rows = table[table["quantity"] == quantity]
    if level == "coarse":
        if not {"phi_coarse", "phi_extrapolated"} <= set(rows.columns):
            return out
        band = 1.25 * (rows["phi_coarse"] - rows["phi_extrapolated"]).abs() \
            / rows["phi_extrapolated"].abs()
    else:
        if f"gci_{level}" not in rows.columns:
            return out
        band = rows[f"gci_{level}"].abs()
    band = band.dropna()
    if band.empty:
        return out
    out.update(available=True, rel_band=float(band.max()), n_mach=int(len(band)),
               source=str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT)
               else str(path))
    return out


# ---------------------------------------------------------------------------------------
# The surface
# ---------------------------------------------------------------------------------------

def shape_of(geometry: Any) -> dict[str, float]:
    d = float(geometry.diameter_m)
    return {"bluntness_ratio": float(geometry.nose_radius_m) / d,
            "cone_half_angle_deg": float(geometry.cone_half_angle_deg),
            "shoulder_ratio": float(geometry.shoulder_radius_m) / d}


def training_hash(table: pd.DataFrame) -> str:
    cols = ["point_id", "mach", *SHAPE_INPUTS, "cd_fore"]
    blob = table[cols].sort_values("point_id").to_csv(index=False, float_format="%.12g")
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


class CfdDragSurface:
    """GP for C_D,fore over (log Mach, bluntness, cone half-angle, shoulder ratio)."""

    def __init__(self, table: pd.DataFrame, meta: dict[str, Any],
                 theta: np.ndarray | None = None):
        from ..surrogate.gp import GPSurrogate  # lazy: surrogate imports the evaluator

        self.table = table.reset_index(drop=True)
        self.meta = dict(meta)
        rng = meta["input_ranges"]
        self._lo = np.array([np.log(rng["mach"][0]), *[rng[k][0] for k in SHAPE_INPUTS]])
        self._hi = np.array([np.log(rng["mach"][1]), *[rng[k][1] for k in SHAPE_INPUTS]])
        self.mach_min = float(self.table["mach"].min())
        self.mach_max = float(self.table["mach"].max())
        self.gp = GPSurrogate("cd_fore", seed=int(meta.get("seed", 0)), n_restarts=4)
        self.gp.fit(self.unit(self.table["mach"], self.table[list(SHAPE_INPUTS)].to_numpy()),
                    self.table["cd_fore"].to_numpy(), theta=theta)
        self.base = BaseDragModel(**{k: v for k, v in meta.get("base_drag", {}).items()
                                     if k in BaseDragModel.__dataclass_fields__})

    # -- inputs ------------------------------------------------------------------------
    def unit(self, mach, shapes: np.ndarray) -> np.ndarray:
        mach = np.atleast_1d(np.asarray(mach, dtype=float))
        shapes = np.atleast_2d(np.asarray(shapes, dtype=float))
        if shapes.shape[0] == 1 and mach.size > 1:
            shapes = np.repeat(shapes, mach.size, axis=0)
        x = np.column_stack([np.log(mach), shapes])
        return (x - self._lo) / (self._hi - self._lo)

    # -- persistence -------------------------------------------------------------------
    def save(self, directory: Path = SURFACE_DIR) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        self.table.to_csv(directory / "training_data.csv", index=False)
        meta = {**self.meta, "kernel_theta": self.gp.kernel_theta.tolist(),
                "training_hash": training_hash(self.table), "n_train": int(len(self.table))}
        (directory / "surface.json").write_text(json.dumps(meta, indent=2, default=str))
        self.meta = meta
        return directory

    @classmethod
    def load(cls, directory: Path = SURFACE_DIR) -> CfdDragSurface:
        meta = json.loads((directory / "surface.json").read_text())
        table = pd.read_csv(directory / "training_data.csv")
        if training_hash(table) != meta["training_hash"]:
            raise ValueError(f"{directory}: training_data.csv does not match the hash in "
                             "surface.json - the surface was edited by hand or is corrupt")
        return cls(table, meta, theta=np.array(meta["kernel_theta"], dtype=float))

    # -- prediction --------------------------------------------------------------------
    def predict_fore(self, mach, shape: dict[str, float], *, on_extrapolation: str = "raise"):
        """GP prediction of C_D,fore inside the CFD Mach range (Mach is NOT clamped here)."""
        vec = np.array([[shape[k] for k in SHAPE_INPUTS]])
        return self.gp.predict(self.unit(mach, vec), on_extrapolation=on_extrapolation)

    def cd_model(self, shape: dict[str, float], *, on_extrapolation: str = "raise",
                 z_gp: float = 0.0, z_discretisation: float = 0.0,
                 u_model_form: float = 0.0, u_base: float = 0.0) -> TabulatedCd:
        nodes = np.exp(np.linspace(np.log(self.mach_min), np.log(self.mach_max), N_MACH_NODES))
        pred = self.predict_fore(nodes, shape, on_extrapolation=on_extrapolation)
        disc = discretisation_band(str(self.meta.get("mesh_level", "medium")))
        if z_discretisation != 0.0 and not disc["available"]:
            raise GateNotPassedError(
                "z_discretisation != 0 requested but results/M2/<run>/gci.csv has no "
                "medium-mesh GCI yet; the discretisation band cannot be sampled before G4")
        s_disc = 0.5 * disc["rel_band"] if disc["available"] else 0.0
        h_form = float(self.meta.get("model_form_rel_halfband", 0.0))
        if not (-1.0 <= u_model_form <= 1.0):
            raise ValueError("u_model_form must lie in [-1, +1]")
        # Recalibration measured at build time: the k-fold z-score spread (>= 1). A GP that
        # cross-validation shows to be overconfident has its sigma widened by that factor
        # before anyone samples it; the raw sigma stays available as `cd_fore_std_raw`.
        inflation = float(self.meta.get("sigma_inflation", 1.0))
        std = pred.std * inflation
        fore = (pred.central * (1.0 + z_discretisation * s_disc + u_model_form * h_form)
                + z_gp * std)
        total = fore + self.base.cd_base(nodes, u_base)
        return TabulatedCd(
            mach_nodes=nodes, cd_total=total, cd_fore=pred.central, cd_fore_std=std,
            cd_base=self.base.cd_base(nodes, u_base),
            provenance={
                "aero_model": MODEL_NAME,
                "surface_training_hash": self.meta["training_hash"],
                "surface_source_run": self.meta.get("source_run"),
                "surface_n_train": int(len(self.table)),
                "gate_G4_status_at_build": self.meta["gate_G4_status_at_build"],
                "gate_G4_status_at_evaluation": gate_g4_status()["status"],
                "mesh_level": self.meta.get("mesh_level"),
                "gp_sigma_inflation": inflation,
                "discretisation_band_available": bool(disc["available"]),
                "discretisation_rel_band": disc["rel_band"],
                "discretisation_source": disc["source"],
                "shape": dict(shape),
                "shape_extrapolated": bool(np.any(pred.extrapolated)),
                "mach_range": [self.mach_min, self.mach_max],
                "uncertainty_draw": {"z_gp": z_gp, "z_discretisation": z_discretisation,
                                     "u_model_form": u_model_form, "u_base": u_base},
            })


@dataclass
class TabulatedCd:
    """(mach, altitude) -> C_D for ONE capsule. Smooth (PCHIP in log Mach), held outside."""

    mach_nodes: np.ndarray
    cd_total: np.ndarray
    cd_fore: np.ndarray
    cd_fore_std: np.ndarray
    cd_base: np.ndarray
    provenance: dict[str, Any]
    low_mach_scale: float = 1.0
    """SENSITIVITY TEST ONLY (`vehicle.aero.test_low_mach_scale`): multiplies the HELD value
    below the lowest CFD Mach, ramped in over a factor 1.5 in Mach so the integrator sees no
    step. It exists to measure how little the objectives care about that held value."""

    def __post_init__(self) -> None:
        self._ln_lo, self._ln_hi = np.log(self.mach_nodes[0]), np.log(self.mach_nodes[-1])
        self._f = PchipInterpolator(np.log(self.mach_nodes), self.cd_total)

    def _low_mach_factor(self, ln_m):
        ramp = np.clip((self._ln_lo - ln_m) / np.log(1.5), 0.0, 1.0)
        return 1.0 + (self.low_mach_scale - 1.0) * ramp

    def __call__(self, mach: float, altitude_m: float = 0.0) -> float:
        ln_raw = np.log(max(mach, 1e-12))
        ln_m = min(max(ln_raw, self._ln_lo), self._ln_hi)
        return float(self._f(ln_m) * self._low_mach_factor(ln_raw))

    def evaluate(self, mach: np.ndarray) -> np.ndarray:
        ln_raw = np.log(np.maximum(mach, 1e-12))
        return self._f(np.clip(ln_raw, self._ln_lo, self._ln_hi)) * self._low_mach_factor(ln_raw)

    def report(self, mach: np.ndarray, time_s: np.ndarray,
               heat_flux_w_m2: np.ndarray) -> dict[str, float]:
        """Per-evaluation extrapolation bookkeeping (spec §25): how much of THIS entry was
        flown outside the CFD Mach range, by flight time and by heat load."""
        mach = np.asarray(mach, dtype=float)
        below, above = mach < self.mach_nodes[0], mach > self.mach_nodes[-1]
        load = float(np.trapezoid(heat_flux_w_m2, time_s))
        span = float(time_s[-1] - time_s[0])

        def share(mask: np.ndarray, weight: np.ndarray, total: float) -> float:
            return float(np.trapezoid(np.where(mask, weight, 0.0), time_s) / total) \
                if total > 0 else 0.0
        ones = np.ones_like(time_s)
        i_peak = int(np.argmax(heat_flux_w_m2))
        return {
            "aero_shape_extrapolated": float(self.provenance["shape_extrapolated"]),
            "aero_time_fraction_below_cfd_mach": share(below, ones, span),
            "aero_time_fraction_above_cfd_mach": share(above, ones, span),
            "aero_heat_fraction_below_cfd_mach": share(below, heat_flux_w_m2, load),
            "aero_heat_fraction_above_cfd_mach": share(above, heat_flux_w_m2, load),
            "aero_cd_at_peak_heating": float(self.evaluate(mach[i_peak:i_peak + 1])[0]),
            "aero_mach_at_peak_heating": float(mach[i_peak]),
            "aero_cd_fore_std_max": float(self.cd_fore_std.max()),
        }


@lru_cache(maxsize=4)
def _load_cached(directory: str, stamp: float) -> CfdDragSurface:
    return CfdDragSurface.load(Path(directory))


def load_surface(directory: Path = SURFACE_DIR) -> CfdDragSurface:
    meta = directory / "surface.json"
    if not meta.exists():
        raise FileNotFoundError(f"no CFD drag surface at {directory}; run `make aero-surface`")
    return _load_cached(str(directory), meta.stat().st_mtime)


def build_cfd_surface_model(aero_cfg: dict[str, Any], geometry: Any):
    """`register_aero_model` builder. Returns (cd_model, fidelity=1)."""
    if geometry is None:
        raise ValueError(f"vehicle.aero.model '{MODEL_NAME}' needs a full capsule geometry; "
                         "the legacy nose-radius/diameter config has no shape to look up")
    directory = Path(aero_cfg["surface_dir"]) if aero_cfg.get("surface_dir") else SURFACE_DIR
    if not directory.is_absolute():
        directory = REPO_ROOT / directory
    surface = load_surface(directory)
    g4_now = gate_g4_status()["status"]
    provisional = g4_now != "PASS" or surface.meta["gate_G4_status_at_build"] != "PASS"
    if provisional and not bool(aero_cfg.get("allow_provisional", False)):
        raise GateNotPassedError(
            f"'{MODEL_NAME}' is PROVISIONAL: gate G4 is {g4_now} now and was "
            f"{surface.meta['gate_G4_status_at_build']} when the surface was built. Spec §17 "
            "forbids CFD data in the optimisation loop until G4 is PASS. For coupled-model "
            "TESTING only, set vehicle.aero.allow_provisional: true - the result is labelled.")
    unc = aero_cfg.get("uncertainty", {}) or {}
    policy = str(aero_cfg.get("on_extrapolation", "reject"))
    if policy not in ("reject", "flag"):
        raise ValueError("vehicle.aero.on_extrapolation must be 'reject' or 'flag'")
    model = surface.cd_model(
        shape_of(geometry), on_extrapolation="raise" if policy == "reject" else "flag",
        z_gp=float(unc.get("z_gp", 0.0)),
        z_discretisation=float(unc.get("z_discretisation", 0.0)),
        u_model_form=float(unc.get("u_model_form", 0.0)),
        u_base=float(unc.get("u_base", 0.0)))
    model.provenance["provisional"] = bool(provisional)
    model.low_mach_scale = float(aero_cfg.get("test_low_mach_scale", 1.0))
    model.provenance["test_low_mach_scale"] = model.low_mach_scale
    return model, 1
