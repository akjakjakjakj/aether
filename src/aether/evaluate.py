"""The canonical design evaluator.

CONTRACT: no optimisation, DOE, sweep or study code may integrate a trajectory or a TPS
stack directly. Everything goes through `evaluate_design`. That is what makes results
from different studies comparable, and it is the single place where the Fidelity-1
aerodynamic surrogate will later be swapped in without touching any caller.

    evaluate_design(config) -> DesignEvaluation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .atmosphere import USStandardAtmosphere1976
from .heating import heat_flux_history
from .scoring import PerformanceVector, compute_metrics
from .tps import Layer, TPSStack, solve_tps
from .trajectory import EntryState, VehicleAero, integrate_entry
from .utils.run import config_hash


@dataclass
class DesignEvaluation:
    """Everything one design evaluation produced."""

    design_id: str
    design_vector: dict[str, Any]
    performance: PerformanceVector
    trajectory: Any
    heat_flux_w_m2: np.ndarray
    tps: Any
    fidelity: int = 0


def _build_stack(cfg: dict[str, Any]) -> TPSStack:
    layers = [
        Layer(
            name=layer["name"],
            thickness_m=float(layer["thickness_m"]),
            conductivity_w_mk=float(layer["conductivity_w_mk"]),
            density_kg_m3=float(layer["density_kg_m3"]),
            specific_heat_j_kgk=float(layer["specific_heat_j_kgk"]),
            n_cells=int(layer.get("n_cells", 40)),
        )
        for layer in cfg["layers"]
    ]
    return TPSStack(
        layers=layers,
        emissivity=float(cfg.get("emissivity", 0.85)),
        bondline_after_layer=cfg.get("bondline_after_layer"),
        t_initial_k=float(cfg.get("t_initial_k", 300.0)),
        t_radiation_sink_k=float(cfg.get("t_radiation_sink_k", 4.0)),
    )


def evaluate_design(config: dict[str, Any], design_id: str | None = None) -> DesignEvaluation:
    """Run the full Fidelity-0 chain for one design.

    1. validate inputs
    2. obtain aerodynamics (constant Cd at Fidelity 0)
    3. integrate the trajectory
    4. compute the heat-flux history
    5. solve the TPS response
    6. reduce to the canonical performance vector

    Returns a DesignEvaluation. Never raises on a *physically* bad design - it comes
    back with feasible=False and a status string, because the optimiser needs to see
    failures, not exceptions.
    """
    veh = config["vehicle"]
    ent = config["entry"]
    tps_cfg = config["tps"]
    num = config.get("numerics", {})
    lim = config.get("limits", {})

    geom = veh["geometry"]
    nose_radius = float(geom["nose_radius_m"])
    diameter = float(geom["diameter_m"])
    area = np.pi * (diameter / 2.0) ** 2

    vehicle = VehicleAero(
        mass_kg=float(veh["mass_kg"]),
        reference_area_m2=area,
        cd=float(veh["cd"]),
        cl=float(veh.get("cl", 0.0)),
        bank_angle_rad=np.radians(float(veh.get("bank_angle_deg", 0.0))),
    )
    initial = EntryState(
        altitude_m=float(ent["altitude_m"]),
        velocity_m_s=float(ent["velocity_m_s"]),
        flight_path_angle_rad=np.radians(float(ent["flight_path_angle_deg"])),
    )

    atm = USStandardAtmosphere1976(warn_above_86km=False)
    traj = integrate_entry(
        initial, vehicle,
        terminal_altitude_m=float(num.get("terminal_altitude_m", 20_000.0)),
        max_time_s=float(num.get("max_time_s", 3_000.0)),
        rtol=float(num.get("rtol", 1e-9)),
        atol=float(num.get("atol", 1e-9)),
        max_step_s=float(num.get("max_step_s", 0.5)),
        atmosphere=atm,
    )

    q = heat_flux_history(traj, nose_radius)

    # ---- post-entry soak-out --------------------------------------------------------
    # The bondline peak LAGS the heat pulse. Heat already inside the TPS keeps diffusing
    # inward after aeroheating has effectively stopped, so truncating the thermal solve
    # at the trajectory's terminal altitude systematically UNDER-predicts the bondline
    # temperature - by ~50 K for a 20 mm stack in this study. The conduction solve is
    # therefore continued at zero incident flux for `soak_time_s`. Re-radiation stays
    # active, so the surface cools while the interior is still warming.
    soak_s = float(num.get("soak_time_s", 1200.0))
    t_thermal, q_thermal = traj.time_s, q
    if soak_s > 0.0:
        n_soak = int(num.get("soak_samples", 400))
        t_soak = np.linspace(traj.time_s[-1] + 1.0, traj.time_s[-1] + soak_s, n_soak)
        t_thermal = np.concatenate([traj.time_s, t_soak])
        q_thermal = np.concatenate([q, np.zeros_like(t_soak)])

    stack = _build_stack(tps_cfg)
    tps_res = solve_tps(stack, t_thermal, q_thermal)

    perf = compute_metrics(
        traj, q, tps_res,
        limits={
            "max_g": lim.get("max_g"),
            "max_dynamic_pressure_pa": lim.get("max_dynamic_pressure_pa"),
            "t_bondline_allowable_k": lim.get("t_bondline_allowable_k"),
            "t_surface_allowable_k": lim.get("t_surface_allowable_k"),
        },
        t_bondline_reference_k=float(tps_cfg.get("t_bondline_reference_k", 400.0)),
        t_penetration_threshold_k=float(tps_cfg.get("t_penetration_threshold_k", 500.0)),
    )

    design_vector = {
        "nose_radius_m": nose_radius,
        "diameter_m": diameter,
        "mass_kg": vehicle.mass_kg,
        "cd": vehicle.cd,
        "ballistic_coefficient_kg_m2": vehicle.ballistic_coefficient,
        "entry_altitude_m": initial.altitude_m,
        "entry_velocity_m_s": initial.velocity_m_s,
        "entry_flight_path_angle_deg": float(ent["flight_path_angle_deg"]),
    }

    return DesignEvaluation(
        design_id=design_id or f"D-{config_hash(design_vector)}",
        design_vector=design_vector,
        performance=perf,
        trajectory=traj,
        heat_flux_w_m2=q,
        tps=tps_res,
    )
