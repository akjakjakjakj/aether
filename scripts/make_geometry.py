#!/usr/bin/env python3
"""Phase F: build the baseline parametric capsule, export STLs, and plot the family
figure across the geometry bounds. Thin CLI driver - no physics here (ARCHITECTURE.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.geometry import CapsuleGeometry  # noqa: E402
from src.aether.utils.run import load_config  # noqa: E402
from src.aether.viz import plot_capsule_family  # noqa: E402

# A small family spanning configs/geometry_bounds.yaml, each independently valid,
# picked to show the design space's extremes: the baseline general case, a
# near-critical-angle (Apollo-like, small fore-cone) forebody, a slender sharp
# sphere-cone, a capsule with an unusually wide rounded shoulder, and a cylindrical
# (zero-angle) afterbody.
FAMILY = {
    "baseline": None,  # filled in from geometry/parametric/baseline.yaml below
    "near-Apollo (small fore cone)": dict(
        nose_radius_m=1.10, diameter_m=1.30, shoulder_radius_m=0.10,
        cone_half_angle_deg=60.0, aft_cone_angle_deg=25.0, length_m=1.00,
    ),
    "sharp sphere-cone": dict(
        nose_radius_m=0.20, diameter_m=1.50, shoulder_radius_m=0.08,
        cone_half_angle_deg=15.0, aft_cone_angle_deg=10.0, length_m=2.80,
    ),
    "wide shoulder": dict(
        nose_radius_m=0.70, diameter_m=1.60, shoulder_radius_m=0.45,
        cone_half_angle_deg=30.0, aft_cone_angle_deg=20.0, length_m=1.30,
    ),
    "cylindrical afterbody": dict(
        nose_radius_m=0.50, diameter_m=1.00, shoulder_radius_m=0.15,
        cone_half_angle_deg=20.0, aft_cone_angle_deg=0.0, length_m=1.20,
    ),
}


def main() -> int:
    cfg = load_config(ROOT / "geometry" / "parametric" / "baseline.yaml")
    FAMILY["baseline"] = dict(cfg["geometry"])

    geometries = {name: CapsuleGeometry(**params) for name, params in FAMILY.items()}
    for geom in geometries.values():
        geom.validate()

    baseline = geometries["baseline"]
    baseline_yaml = ROOT / "geometry" / "parametric" / "baseline.yaml"
    print(f"AETHER Phase F - baseline capsule  ({baseline_yaml})\n")
    print(f"  nose_radius_m           {baseline.nose_radius_m:10.4f}")
    print(f"  diameter_m              {baseline.diameter_m:10.4f}")
    print(f"  reference_area_m2       {baseline.reference_area_m2:10.4f}")
    print(f"  effective_nose_radius_m {baseline.effective_nose_radius_m:10.4f}")
    print(f"  wetted_forebody_area_m2 {baseline.wetted_forebody_area_m2:10.4f}")
    print(f"  enclosed_volume_m3      {baseline.enclosed_volume_m3:10.4f}")

    stl_dir = ROOT / "geometry" / "stl"
    written_stl = []
    for name, geom in geometries.items():
        slug = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
        path = geom.to_stl(stl_dir / f"{slug}.stl", n_circumferential=64, n_profile_points=200)
        written_stl.append(path)
    print(f"\n  STL       -> {', '.join(str(p.relative_to(ROOT)) for p in written_stl)}")

    figs = plot_capsule_family(
        list(geometries.values()), list(geometries.keys()), ROOT / "reports" / "figures"
    )
    print(f"  figure    -> {', '.join(str(f.relative_to(ROOT)) for f in figs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
