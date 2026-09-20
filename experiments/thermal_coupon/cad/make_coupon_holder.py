#!/usr/bin/env python3
"""Generate the printable coupon holder: ASCII STL plus editable OpenSCAD source.

    python experiments/thermal_coupon/cad/make_coupon_holder.py --out .

Writes `coupon_holder.stl`, `coupon_holder.scad` and `coupon_holder_params.json` into
`--out`. Byte-identical on every run and every machine: no timestamps, no floating-point
drift (every coordinate is formatted to a fixed number of decimals), no dependency
beyond the standard library.

What the holder has to do, and why it looks like this
----------------------------------------------------
The coupon is heated on one face and must be free to lose heat from the other, because
the model has a loss coefficient on both faces and a calibration that cannot see the
back face cannot constrain it. So the frame is OPEN on both sides: it is a rectangular
picture frame, not a tray.

The coupon rests on four CORNER PADS rather than a continuous ledge. A continuous ledge
would touch the coupon all the way around and conduct heat into the holder along a path
the 1-D model does not have, and the error would grow with run duration - exactly where
the long calibration run is trying to measure the loss coefficients. Four small pads cut
that contact to about 4% of the back-face area (the script prints the exact figure for
whatever parameters are used). It is not zero, and `protocol.md` tells the student to
bound it rather than ignore it.

One rail carries a gap for the thermocouple wires to leave without being pinched or bent
sharply, and four legs lift the whole thing off the bench so the back face sees room air
rather than a worktop at an unknown temperature.

Geometry construction
---------------------
The solid is a set of axis-aligned boxes that touch at faces but never interpenetrate, so
the STL is a valid multi-solid file. It is NOT the output of a CSG kernel and is not
guaranteed to be a single closed manifold; slicers handle multi-solid STLs, but if you
want a true manifold, or want to change the shape rather than its dimensions, edit the
generated `.scad` and let OpenSCAD do the union. The `.scad` is the authoritative source;
the STL is a convenience so a student without OpenSCAD can still print.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

PRECISION = 4
"""Decimals in the STL. Fixed so the file is byte-identical across runs and platforms."""


@dataclass(frozen=True)
class HolderParams:
    """Every dimension in millimetres. Change these, not the geometry code."""

    coupon_x_mm: float = 60.0
    coupon_y_mm: float = 60.0
    coupon_z_mm: float = 10.0
    clearance_mm: float = 0.4
    """Gap per side between coupon and frame. 0.4 mm suits a 0.4 mm nozzle; tighten it
    and a coupon that is 0.2 mm oversize will not go in, which is a bad day."""
    rail_mm: float = 6.0
    """Frame wall thickness."""
    frame_height_mm: float = 18.0
    pad_mm: float = 6.0
    """Corner support pad, square. Small on purpose - see `supported_area_fraction`."""
    pad_height_mm: float = 3.0
    """How far the coupon sits above the bottom of the frame."""
    leg_mm: float = 10.0
    leg_height_mm: float = 20.0
    """Standoff height. Must exceed the boundary-layer scale of natural convection off
    the back face, which for a 60 mm plate is of order 10 mm; 20 mm is a margin."""
    wire_gap_mm: float = 14.0
    """Width of the gap in the +Y rail through which thermocouple wires leave."""

    def __post_init__(self) -> None:
        if self.pad_mm >= min(self.coupon_x_mm, self.coupon_y_mm) / 2.0:
            raise ValueError("corner pads would meet in the middle; reduce pad_mm")
        if self.wire_gap_mm >= self.opening_x_mm:
            raise ValueError("wire gap is wider than the frame rail it is cut from")
        if self.pad_height_mm >= self.frame_height_mm:
            raise ValueError("pads must sit below the top of the frame")
        for name, value in asdict(self).items():
            if value <= 0.0:
                raise ValueError(f"{name} must be positive")

    @property
    def opening_x_mm(self) -> float:
        return self.coupon_x_mm + 2.0 * self.clearance_mm

    @property
    def opening_y_mm(self) -> float:
        return self.coupon_y_mm + 2.0 * self.clearance_mm

    @property
    def outer_x_mm(self) -> float:
        return self.opening_x_mm + 2.0 * self.rail_mm

    @property
    def outer_y_mm(self) -> float:
        return self.opening_y_mm + 2.0 * self.rail_mm

    @property
    def supported_area_fraction(self) -> float:
        """Fraction of the coupon's BACK FACE resting on the holder [-].

        This is the parasitic conduction path the 1-D model does not have: heat leaving
        the coupon into the plastic frame instead of into the air. Quoted in the
        protocol so it is a number the student has seen and bounded, not an unexamined
        assumption. The lateral gap to the rails is `clearance_mm` and is nominally
        non-contacting, so the pads are the whole of it.
        """
        return 4.0 * self.pad_mm**2 / (self.coupon_x_mm * self.coupon_y_mm)


Box = tuple[float, float, float, float, float, float]
"""(x0, y0, z0, x1, y1, z1) in mm."""


def build_boxes(p: HolderParams) -> list[tuple[str, Box]]:
    """Named axis-aligned boxes. They touch at faces; none interpenetrates another."""
    r, h = p.rail_mm, p.frame_height_mm
    ox, oy = p.outer_x_mm, p.outer_y_mm
    inner_x0, inner_x1 = r, ox - r
    gap_half = p.wire_gap_mm / 2.0
    mid = ox / 2.0
    lz0, lz1 = -p.leg_height_mm, 0.0

    boxes: list[tuple[str, Box]] = [
        ("rail_minus_x", (0.0, 0.0, 0.0, r, oy, h)),
        ("rail_plus_x", (ox - r, 0.0, 0.0, ox, oy, h)),
        ("rail_minus_y", (inner_x0, 0.0, 0.0, inner_x1, r, h)),
        # +Y rail is split: the gap is the wire exit.
        ("rail_plus_y_a", (inner_x0, oy - r, 0.0, mid - gap_half, oy, h)),
        ("rail_plus_y_b", (mid + gap_half, oy - r, 0.0, inner_x1, oy, h)),
    ]

    pad, ph = p.pad_mm, p.pad_height_mm
    for name, x0, y0 in (
        ("pad_mm_corner", r, r),
        ("pad_pm_corner", ox - r - pad, r),
        ("pad_mp_corner", r, oy - r - pad),
        ("pad_pp_corner", ox - r - pad, oy - r - pad),
    ):
        boxes.append((name, (x0, y0, 0.0, x0 + pad, y0 + pad, ph)))

    leg = p.leg_mm
    for name, x0, y0 in (
        ("leg_mm", 0.0, 0.0),
        ("leg_pm", ox - leg, 0.0),
        ("leg_mp", 0.0, oy - leg),
        ("leg_pp", ox - leg, oy - leg),
    ):
        boxes.append((name, (x0, y0, lz0, x0 + leg, y0 + leg, lz1)))

    return boxes


def _box_triangles(b: Box) -> list[tuple[tuple[float, float, float], ...]]:
    """12 outward-facing triangles for one box, in a fixed order."""
    x0, y0, z0, x1, y1, z1 = b
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    quads = [
        ((0, 3, 2, 1), (0.0, 0.0, -1.0)),   # bottom
        ((4, 5, 6, 7), (0.0, 0.0, 1.0)),    # top
        ((0, 1, 5, 4), (0.0, -1.0, 0.0)),   # -y
        ((2, 3, 7, 6), (0.0, 1.0, 0.0)),    # +y
        ((1, 2, 6, 5), (1.0, 0.0, 0.0)),    # +x
        ((3, 0, 4, 7), (-1.0, 0.0, 0.0)),   # -x
    ]
    tris = []
    for (a, b_, c, d), normal in quads:
        tris.append((normal, v[a], v[b_], v[c]))
        tris.append((normal, v[a], v[c], v[d]))
    return tris


def box_volume_mm3(boxes: list[tuple[str, Box]]) -> float:
    """Total solid volume [mm^3]. Exact, because no box interpenetrates another."""
    return sum((x1 - x0) * (y1 - y0) * (z1 - z0) for _, (x0, y0, z0, x1, y1, z1) in boxes)


def write_stl(boxes: list[tuple[str, Box]], path: str | Path, name: str = "coupon_holder"
              ) -> Path:
    """ASCII STL. Text, so it diffs, and deterministic, so the diff means something."""
    fmt = f"%.{PRECISION}f"
    lines = [f"solid {name}"]
    for _, box in boxes:
        for normal, a, b, c in _box_triangles(box):
            lines.append("  facet normal " + " ".join(fmt % x for x in normal))
            lines.append("    outer loop")
            for vertex in (a, b, c):
                lines.append("      vertex " + " ".join(fmt % x for x in vertex))
            lines.append("    endloop")
            lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path = Path(path)
    path.write_text("\n".join(lines) + "\n")
    return path


def write_scad(p: HolderParams, path: str | Path) -> Path:
    """OpenSCAD source: the authoritative, editable, genuinely-manifold version."""
    body = f"""// AETHER M8 thermal-coupon holder - generated by cad/make_coupon_holder.py
// Edit the parameters, then: openscad -o coupon_holder.stl coupon_holder.scad
// This file is the authoritative geometry. The generated ASCII STL is a convenience
// copy built from non-interpenetrating boxes; OpenSCAD's union() is what makes a true
// manifold.

coupon_x     = {p.coupon_x_mm};
coupon_y     = {p.coupon_y_mm};
coupon_z     = {p.coupon_z_mm};
clearance    = {p.clearance_mm};
rail         = {p.rail_mm};
frame_h      = {p.frame_height_mm};
pad          = {p.pad_mm};
pad_h        = {p.pad_height_mm};
leg          = {p.leg_mm};
leg_h        = {p.leg_height_mm};
wire_gap     = {p.wire_gap_mm};

opening_x = coupon_x + 2 * clearance;
opening_y = coupon_y + 2 * clearance;
outer_x   = opening_x + 2 * rail;
outer_y   = opening_y + 2 * rail;

module frame() {{
    difference() {{
        cube([outer_x, outer_y, frame_h]);
        // through opening: BOTH faces of the coupon must see air
        translate([rail, rail, -1])
            cube([opening_x, opening_y, frame_h + 2]);
        // wire exit in the +Y rail
        translate([(outer_x - wire_gap) / 2, outer_y - rail - 1, -1])
            cube([wire_gap, rail + 2, frame_h + 2]);
    }}
}}

module pads() {{
    for (px = [rail, outer_x - rail - pad])
        for (py = [rail, outer_y - rail - pad])
            translate([px, py, 0]) cube([pad, pad, pad_h]);
}}

module legs() {{
    for (px = [0, outer_x - leg])
        for (py = [0, outer_y - leg])
            translate([px, py, -leg_h]) cube([leg, leg, leg_h]);
}}

union() {{ frame(); pads(); legs(); }}

// Reference only - not printed. Uncomment to check the coupon fits.
// %translate([rail + clearance, rail + clearance, pad_h])
//     cube([coupon_x, coupon_y, coupon_z]);
"""
    path = Path(path)
    path.write_text(body)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=".", help="output directory")
    for field_name, default in asdict(HolderParams()).items():
        ap.add_argument(f"--{field_name.replace('_', '-')}", type=float, default=default)
    args = ap.parse_args(argv)

    params = HolderParams(**{
        name: getattr(args, name) for name in asdict(HolderParams())
    })
    boxes = build_boxes(params)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    stl = write_stl(boxes, out / "coupon_holder.stl")
    scad = write_scad(params, out / "coupon_holder.scad")
    volume = box_volume_mm3(boxes)
    meta = {
        "generated_by": "experiments/thermal_coupon/cad/make_coupon_holder.py",
        "parameters_mm": asdict(params),
        "derived_mm": {
            "opening_x": params.opening_x_mm,
            "opening_y": params.opening_y_mm,
            "outer_x": params.outer_x_mm,
            "outer_y": params.outer_y_mm,
        },
        "solid_volume_mm3": volume,
        "supported_area_fraction": params.supported_area_fraction,
        "n_boxes": len(boxes),
        "n_triangles": 12 * len(boxes),
        "note": "Deterministic output: no timestamps, fixed decimal formatting.",
    }
    (out / "coupon_holder_params.json").write_text(json.dumps(meta, indent=2) + "\n")

    print(f"holder  {params.outer_x_mm:.1f} x {params.outer_y_mm:.1f} mm footprint, "
          f"{params.frame_height_mm:.1f} mm frame + {params.leg_height_mm:.1f} mm legs")
    print(f"opening {params.opening_x_mm:.1f} x {params.opening_y_mm:.1f} mm "
          f"(coupon {params.coupon_x_mm:.0f} x {params.coupon_y_mm:.0f} mm, "
          f"{params.clearance_mm:.1f} mm clearance per side)")
    print(f"coupon back face resting on the holder: "
          f"{100 * params.supported_area_fraction:.1f}%")
    print(f"solid volume {volume / 1000.0:.1f} cm3 "
          f"(filament mass depends on infill; this is 100% solid)")
    print(f"\n  {stl}\n  {scad}\n  {out / 'coupon_holder_params.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
