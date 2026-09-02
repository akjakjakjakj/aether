#!/usr/bin/env python3
"""Evaluate the nominal configuration and print its performance vector."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.evaluate import evaluate_design  # noqa: E402
from src.aether.utils.run import (  # noqa: E402
    RunMeta,
    config_hash,
    load_config,
    new_run_id,
    snapshot_config,
)
from src.aether.viz import plot_baseline  # noqa: E402


def main() -> int:
    cfg = load_config(ROOT / "configs" / "baseline.yaml")
    run_id = new_run_id("baseline")
    out = ROOT / "results" / "baseline" / run_id
    meta = RunMeta(run_id=run_id, config_hash=config_hash(cfg), notes="nominal entry")
    snapshot_config(cfg, out, meta)

    ev = evaluate_design(cfg, design_id="BASELINE")
    p, d = ev.performance, ev.design_vector

    print(f"AETHER baseline   run={run_id}  git={meta.git_commit}"
          f"{' (dirty)' if meta.git_dirty else ''}\n")
    print(f"  ballistic coefficient   {d['ballistic_coefficient_kg_m2']:10.1f} kg m^-2")
    print(f"  peak heat flux          {p.peak_heat_flux_w_m2/1e4:10.2f} W cm^-2 "
          f"(t = {p.time_of_peak_heating_s:.1f} s)")
    print(f"  integrated heat load    {p.integrated_external_heat_j_m2/1e6:10.2f} MJ m^-2")
    print(f"  peak surface temp       {p.peak_surface_temperature_k:10.1f} K")
    print(f"  peak bondline temp      {p.peak_bondline_temperature_k:10.1f} K")
    print(f"  bondline exposure (M4)  {p.bondline_exposure_metric_k_s:10.1f} K s")
    print(f"  penetration depth (M5)  {p.thermal_penetration_depth_m*1e3:10.2f} mm")
    print(f"  max deceleration        {p.max_g:10.2f} g")
    print(f"  max dynamic pressure    {p.max_dynamic_pressure_pa/1e3:10.2f} kPa")
    print(f"  entry duration          {p.entry_duration_s:10.1f} s")
    print(f"  energy balance residual {p.energy_balance_residual:10.2e}")
    print(f"\n  feasible = {p.feasible}   termination = {p.termination}   status = {p.status}")
    for name, margin in p.constraint_margins.items():
        flag = "OK " if margin >= 0 else "VIOLATED"
        print(f"    {flag} {name:32s} margin {margin*100:+7.1f}%")

    figs = plot_baseline(ev, ROOT / "reports" / "figures")
    print(f"\n  figures -> {', '.join(str(f.relative_to(ROOT)) for f in figs)}")
    print(f"  results -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
