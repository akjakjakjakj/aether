#!/usr/bin/env python
"""Regenerate the CFD flow-field gallery (reports/figures/cfd/ + INDEX.md) from the case
directories under cfd/generated/ and the result tables under results/. Read-only on both.

    make cfd-gallery
    .venv/bin/python scripts/render_cfd_gallery.py [--m2 RUN] [--m3 RUN] [--m6 RUN]
                                                   [--only sphere,limit,demo,grid,m27,m6,cp]
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aether.cfd import gallery_figures as F  # noqa: E402
from aether.cfd.gallery import Gallery  # noqa: E402
from aether.utils.run import REPO_ROOT  # noqa: E402


def _latest(prefix: str, milestone: str, marker: str | None = None) -> str:
    runs = sorted(d for d in (REPO_ROOT / "results" / milestone).glob(f"{prefix}*") if d.is_dir()
                  and (marker is None or (d / marker).exists()))
    if not runs:
        raise SystemExit(f"no {prefix}* run under results/{milestone}")
    return runs[-1].name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m2", default=None, help="M2 run ID (default: latest with ALL_STAGES_DONE)")
    ap.add_argument("--m3", default=None, help="M3 design-point run ID (default: latest M3-DP-*)")
    ap.add_argument("--m6", default=None,
                    help="M6 adaptive-fidelity run ID (default: latest M6-AF-*)")
    ap.add_argument("--m27-exp", default="M3-mach27-startup-exp",
                    help="generated-case directory of the NR-28 isolation experiment")
    ap.add_argument("--only", default="", help="comma list of figure groups to render")
    ap.add_argument("--out", default=str(REPO_ROOT / "reports" / "figures" / "cfd"))
    a = ap.parse_args()
    m2 = a.m2 or _latest("M2-", "M2", "ALL_STAGES_DONE")
    m3 = a.m3 or _latest("M3-DP-", "M3")
    m6 = a.m6 or _latest("M6-AF-", "M6")
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    g = Gallery(Path(a.out), [], [])
    g.out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("sphere", "sphere M3 four-panel", lambda: F.fig_sphere_four_panel(g, m2, 3.0)),
        ("sphere", "sphere M6 four-panel", lambda: F.fig_sphere_four_panel(g, m2, 6.0)),
        ("sphere", "sphere M6 mesh levels", lambda: F.fig_sphere_mesh_levels(g, m2, 6.0)),
        ("sphere", "sphere stagnation lines", lambda: F.fig_stagnation_lines(g, m2)),
        ("limit", "limit cycle M3", lambda: F.fig_limit_cycle(g, m2, 3.0)),
        ("limit", "limit cycle M6", lambda: F.fig_limit_cycle(g, m2, 6.0)),
        ("demo", "demo capsule", lambda: F.fig_demo_capsule(g, m2)),
        ("grid", "design-point grid", lambda: F.fig_design_grid(g, m3)),
        ("m27", "Mach-27 failure", lambda: F.fig_mach27_failure(g, m3, a.m27_exp)),
        ("m6", "M6 promotions", lambda: F.fig_m6_promotions(g, m6)),
        ("cp", "sphere Cp", lambda: F.fig_cp_sphere(g, m2)),
        ("cp", "design-point Cp", lambda: F.fig_cp_design_points(g, m3)),
    ]
    for group, name, job in jobs:
        if only and group not in only:
            continue
        print(f"[gallery] {name} ...", flush=True)
        try:
            job()
        except Exception as e:  # a missing field must be reported, never crash the gallery
            g.cannot(f"{name}: {type(e).__name__}: {e}")
            traceback.print_exc()
    index = g.write_index(f"scripts/render_cfd_gallery.py --m2 {m2} --m3 {m3} --m6 {m6}")
    print(f"[gallery] {len(g.entries)} figures, {len(g.missing)} items not rendered -> {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
