"""Forward model, data loading and provenance helpers for the M8 thermal coupon.

Conceptual anchor
-----------------
The coupon experiment is not a re-entry simulator. It is a test of one specific claim
the re-entry model makes: that a slab of solid material, heated by a short intense pulse
and by a longer milder pulse carrying the SAME total energy, ends up with different
interior temperature histories, and that the project's 1-D conduction solver predicts
which is which without being shown the answer first.

The physics needed for a bench coupon is the physics already in
`src/aether/tps/conduction1d.py`, plus the three things a bench has and space does not:
convective loss from both faces, re-radiation into a room at ~295 K rather than into a
4 K sky, and a real contact interface between the heater and the coupon. Those are
boundary options on the same solver (added 2026-09-20), not a second solver. Using a
different model for calibration than for prediction would make the whole exercise
circular.

Units
-----
Everything in this module is SI and Kelvin. Acquisition files are in degrees Celsius,
because that is what a thermocouple logger emits; conversion happens once, in
`load_run`, and nothing downstream ever sees a Celsius value. Column names carry
`_degc` so a mistake is visible in the file rather than inferred from a docstring.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

KELVIN_OFFSET = 273.15
"""T[K] = T[degC] + 273.15. Exact by definition of the Celsius scale."""

FREE_PARAMETER_NAMES = (
    "conductivity_w_mk",
    "specific_heat_j_kgk",
    "contact_resistance_m2k_w",
    "h_front_w_m2k",
    "h_back_w_m2k",
)
"""The parameters `calibrate.py` is allowed to fit. Density is NOT among them: it is
measured on a scale and a set of calipers, and letting a fit absorb it would hide a
measurement error inside an 'effective' property."""


@dataclass(frozen=True)
class CouponGeometry:
    """The physical coupon. Every number here is MEASURED, never fitted."""

    thickness_m: float
    density_kg_m3: float
    heated_area_m2: float
    n_cells: int = 120

    def __post_init__(self) -> None:
        for name in ("thickness_m", "density_kg_m3", "heated_area_m2"):
            if getattr(self, name) <= 0.0:
                raise ValueError(f"CouponGeometry.{name} must be positive")
        if self.n_cells < 10:
            raise ValueError("n_cells < 10 will not resolve a thermal front in a coupon")

    @property
    def cell_size_m(self) -> float:
        return self.thickness_m / self.n_cells


@dataclass(frozen=True)
class CouponParameters:
    """The model parameters. These are what calibration produces and freezing locks."""

    conductivity_w_mk: float
    specific_heat_j_kgk: float
    contact_resistance_m2k_w: float = 0.0
    h_front_w_m2k: float = 0.0
    h_back_w_m2k: float = 0.0
    emissivity: float = 0.90
    """Surface emissivity, FIXED not fitted. A printed polymer is a near-black emitter in
    the infrared, and emissivity is strongly degenerate with the convective coefficients
    at these temperatures - fitting both would produce two precise-looking numbers whose
    sum is the only thing the data actually constrains. Fixing it and saying so is
    honest; fitting it and reporting a standard error is not."""

    def __post_init__(self) -> None:
        for name in FREE_PARAMETER_NAMES:
            if getattr(self, name) < 0.0:
                raise ValueError(f"CouponParameters.{name} must be non-negative")
        if self.conductivity_w_mk <= 0.0 or self.specific_heat_j_kgk <= 0.0:
            raise ValueError("conductivity and specific heat must be strictly positive")
        if not 0.0 <= self.emissivity <= 1.0:
            raise ValueError("emissivity must be in [0, 1]")

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CouponParameters:
        return cls(**{k: float(v) for k, v in data.items() if k in cls.__dataclass_fields__})

    def as_vector(self) -> np.ndarray:
        return np.array([getattr(self, n) for n in FREE_PARAMETER_NAMES], dtype=float)

    @classmethod
    def from_vector(cls, vector: np.ndarray, *, emissivity: float = 0.90
                    ) -> CouponParameters:
        return cls(**dict(zip(FREE_PARAMETER_NAMES, map(float, vector), strict=True)),
                   emissivity=emissivity)

    def thermal_diffusivity_m2_s(self, density_kg_m3: float) -> float:
        return self.conductivity_w_mk / (density_kg_m3 * self.specific_heat_j_kgk)


@dataclass
class RunData:
    """One acquisition run: what the logger recorded, plus its declared metadata."""

    run_id: str
    run_type: str
    time_s: np.ndarray
    heat_flux_w_m2: np.ndarray
    sensor_depths_m: np.ndarray
    sensor_temperatures_k: np.ndarray
    """Shape (n_time, n_sensors)."""
    sensor_channels: list[str]
    t_ambient_k: float
    t_initial_k: float
    synthetic: bool
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None
    quality_flag: np.ndarray | None = None

    @property
    def duration_s(self) -> float:
        return float(self.time_s[-1] - self.time_s[0])

    def geometry(self, n_cells: int = 120) -> CouponGeometry:
        """The coupon geometry declared in this run's metadata sidecar."""
        c = self.metadata["coupon"]
        return CouponGeometry(
            thickness_m=float(c["thickness_m"]),
            density_kg_m3=float(c["density_kg_m3"]),
            heated_area_m2=float(self.metadata["heater"]["heated_area_m2"]),
            n_cells=n_cells,
        )


def sha256_file(path: str | Path) -> str:
    """SHA-256 of a file's bytes. Used to bind a prediction to its exact inputs."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar_path(csv_path: str | Path) -> Path:
    """Metadata sidecar for an acquisition file: `<name>.csv` -> `<name>.meta.yaml`."""
    p = Path(csv_path)
    return p.with_suffix("").with_suffix(".meta.yaml") if p.suffixes[-2:] == [".run", ".csv"] \
        else p.with_name(p.stem + ".meta.yaml")


def load_run(csv_path: str | Path, *, require_sidecar: bool = True) -> RunData:
    """Read one acquisition CSV plus its YAML sidecar into SI/Kelvin arrays.

    The sidecar is mandatory by default. A temperature history without the sensor depths
    that produced it, the heated area, and the coupon it came from is not data - it is a
    column of numbers - and every one of those lives in the sidecar, not in the CSV.
    """
    csv_path = Path(csv_path)
    meta_path = sidecar_path(csv_path)
    if not meta_path.exists():
        if require_sidecar:
            raise FileNotFoundError(
                f"metadata sidecar {meta_path.name} not found next to {csv_path.name}; "
                f"see experiments/thermal_coupon/data_schema.md"
            )
        metadata: dict[str, Any] = {}
    else:
        metadata = yaml.safe_load(meta_path.read_text()) or {}

    with open(csv_path, newline="") as fh:
        rows = [r for r in csv.reader(fh) if r and not r[0].lstrip().startswith("#")]
    header = [c.strip() for c in rows[0]]
    body = np.array([[float(v) if v.strip() != "" else np.nan for v in r] for r in rows[1:]])
    col = {name: i for i, name in enumerate(header)}

    for required in ("time_s", "heater_flux_w_m2"):
        if required not in col:
            raise ValueError(f"{csv_path.name}: required column {required!r} is missing")

    channels = [c for c in header if c.startswith("t_ch") and c.endswith("_degc")]
    if not channels:
        raise ValueError(f"{csv_path.name}: no sensor columns matching t_ch*_degc")

    declared = {s["channel"]: s for s in metadata.get("sensors", [])}
    missing = [c for c in channels if c not in declared]
    if missing and require_sidecar:
        raise ValueError(
            f"{csv_path.name}: channels {missing} have no depth declared in "
            f"{meta_path.name}. A sensor with an undeclared depth cannot be compared "
            f"against a model."
        )

    depths = np.array([float(declared[c]["depth_m"]) for c in channels])
    temps_k = np.column_stack([body[:, col[c]] for c in channels]) + KELVIN_OFFSET

    if "t_ambient_degc" in col:
        ambient_k = float(np.nanmean(body[:, col["t_ambient_degc"]])) + KELVIN_OFFSET
    else:
        ambient_k = float(metadata.get("ambient", {}).get("t_ambient_k", 295.15))

    order = np.argsort(depths)
    return RunData(
        run_id=str(metadata.get("run_id", csv_path.stem)),
        run_type=str(metadata.get("run_type", "unknown")),
        time_s=body[:, col["time_s"]],
        heat_flux_w_m2=body[:, col["heater_flux_w_m2"]],
        sensor_depths_m=depths[order],
        sensor_temperatures_k=temps_k[:, order],
        sensor_channels=[channels[i] for i in order],
        t_ambient_k=ambient_k,
        t_initial_k=float(np.nanmean(temps_k[0])),
        synthetic=bool(metadata.get("synthetic", False)),
        metadata=metadata,
        source_path=csv_path,
        quality_flag=(body[:, col["quality_flag"]] if "quality_flag" in col else None),
    )


def build_stack(geometry: CouponGeometry, params: CouponParameters,
                *, t_initial_k: float, t_ambient_k: float):
    """The coupon as a one-layer TPSStack with bench boundary conditions.

    The radiation sink is the ROOM, not deep space: a coupon on a bench exchanges
    radiation with surfaces at ambient temperature, so `t_radiation_sink_k = t_ambient`.
    Leaving the entry default of 4 K here would make the model radiate away roughly
    `epsilon*sigma*T_amb^4` ~ 400 W/m^2 that does not exist, and the calibration would
    absorb that error into an apparently large heater flux.
    """
    import sys

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from src.aether.tps import Layer, TPSStack

    return TPSStack(
        layers=[Layer(
            name="coupon",
            thickness_m=geometry.thickness_m,
            conductivity_w_mk=params.conductivity_w_mk,
            density_kg_m3=geometry.density_kg_m3,
            specific_heat_j_kgk=params.specific_heat_j_kgk,
            n_cells=geometry.n_cells,
        )],
        emissivity=params.emissivity,
        back_emissivity=params.emissivity,
        t_initial_k=t_initial_k,
        t_ambient_k=t_ambient_k,
        t_radiation_sink_k=t_ambient_k,
        h_front_w_m2k=params.h_front_w_m2k,
        h_back_w_m2k=params.h_back_w_m2k,
        front_contact_resistance_m2k_w=params.contact_resistance_m2k_w,
    )


def _sample_at_depths(depth_m: np.ndarray, field_k: np.ndarray,
                      probe_depths_m: np.ndarray) -> np.ndarray:
    """Linearly interpolate a cell-centred field onto sensor depths.

    Cell centres do not reach the faces, so a sensor at x = 0 or x = L sits just outside
    the sampled range. Those are linearly EXTRAPOLATED from the two nearest cells rather
    than clamped: clamping would bias a surface sensor by half a cell times the local
    gradient, which at the heated face is the steepest gradient in the problem.
    """
    out = np.empty((field_k.shape[0], len(probe_depths_m)))
    for j, x in enumerate(probe_depths_m):
        if depth_m[0] <= x <= depth_m[-1]:
            out[:, j] = np.array([np.interp(x, depth_m, row) for row in field_k])
        elif x < depth_m[0]:
            slope = (field_k[:, 1] - field_k[:, 0]) / (depth_m[1] - depth_m[0])
            out[:, j] = field_k[:, 0] + slope * (x - depth_m[0])
        else:
            slope = (field_k[:, -1] - field_k[:, -2]) / (depth_m[-1] - depth_m[-2])
            out[:, j] = field_k[:, -1] + slope * (x - depth_m[-1])
    return out


def predict_sensors(geometry: CouponGeometry, params: CouponParameters,
                    time_s: np.ndarray, heat_flux_w_m2: np.ndarray,
                    sensor_depths_m: np.ndarray, *,
                    t_initial_k: float, t_ambient_k: float) -> np.ndarray:
    """Forward model: heater flux history -> temperature at each sensor depth [K].

    Returns an array of shape (n_time, n_sensors) aligned with `time_s`.
    """
    import sys

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from src.aether.tps import solve_tps

    stack = build_stack(geometry, params, t_initial_k=t_initial_k, t_ambient_k=t_ambient_k)
    result = solve_tps(stack, np.asarray(time_s, dtype=float),
                       np.asarray(heat_flux_w_m2, dtype=float))
    return _sample_at_depths(result.depth_m, result.temperature_k,
                             np.asarray(sensor_depths_m, dtype=float))


def predict_run(run: RunData, params: CouponParameters, *, n_cells: int = 120
                ) -> np.ndarray:
    """Forward model applied to one loaded run, using that run's own declared geometry."""
    return predict_sensors(
        run.geometry(n_cells=n_cells), params, run.time_s, run.heat_flux_w_m2,
        run.sensor_depths_m, t_initial_k=run.t_initial_k, t_ambient_k=run.t_ambient_k,
    )


def diffusion_time_s(geometry: CouponGeometry, params: CouponParameters) -> float:
    """L^2 / alpha - the clock that decides whether a coupon run is long enough [s].

    The protocol uses this to set run durations: a heating pulse much shorter than this
    never reaches the back face, and a calibration run much shorter than this cannot
    constrain conductivity.
    """
    alpha = params.thermal_diffusivity_m2_s(geometry.density_kg_m3)
    return geometry.thickness_m**2 / alpha
