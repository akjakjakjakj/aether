#!/usr/bin/env python3
"""NR-27 isolation experiment (spec §36 order): why does the slender 20-degree cone die at
Mach 27 right after the first-order start hands over to van Leer?

Same shape, mesh, domain and BCs as dp062_coarse_a0. One thing changed per variant:
    A_fo6000      first-order start 6000 iterations instead of 1500         (§36 step 4: ICs)
    B_fo1500_co01 first-order start 1500, max Courant 0.1 throughout         (§36 step 6)
    C_fo6000_co01 both
NOT a design point; nothing here enters any surface. Usage: run_exp.py <variant>
"""
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.aether.cfd import design_points as dp  # noqa: E402
from src.aether.cfd.pipeline import run_case  # noqa: E402
from src.aether.cfd.postprocess import ConvergenceCriterion  # noqa: E402
from src.aether.cfd.validation import _flow, _mesh_settings, _solver_settings  # noqa: E402
from src.aether.utils.run import load_config  # noqa: E402

VARIANTS = {"A_fo6000": (6000, 0.2), "B_fo1500_co01": (1500, 0.1), "C_fo6000_co01": (6000, 0.1)}
name = sys.argv[1]
n_fo, co = VARIANTS[name]
cfg = load_config(ROOT / "configs" / "cfd_design_points.yaml")
val = load_config(ROOT / cfg["inherit"]["cfd_validation_config"])
pid = sys.argv[2] if len(sys.argv) > 2 else "dp062"
point = next(p for p in dp.build_design(cfg)[0] if p.point_id == pid)
flow = _flow(val, point.mach)
capsule = dp.forebody_capsule(diameter_m=point.diameter_m, **point.shape())
mesh = _mesh_settings(val, 1)
mesh = replace(mesh, asymptote_margin_deg=dp.asymptote_margin_deg(
    capsule, point.mach, flow.gamma, cfg["domain_sizing"], mesh.asymptote_margin_deg))
solver = replace(_solver_settings(val, 1), max_co=co)
res = run_case(f"{point.point_id}_{name}", dp.capsule_outline(capsule, point.point_id), flow, mesh,
               solver, ConvergenceCriterion(**val["convergence_criterion"]),
               generated_root=ROOT / "cfd" / "generated" / "M3-mach27-startup-exp",
               results_dir=Path(__file__).parent,
               sizing_radius_m=dp.domain_sizing_radius_m(capsule, cfg["domain_sizing"]),
               startup_first_order_iterations=n_fo)
print(name, res.status, res.failure_reason, res.metrics.get("cd_fore"),
      res.convergence.get("cd_fore", {}).get("converged"), res.metrics.get("n_iterations"))
