#!/usr/bin/env python3
"""Generate the sensor-placement drawing as a dimensioned SVG.

    python experiments/thermal_coupon/cad/make_sensor_drawing.py --out .

Writes `sensor_placement.svg`. Hand-built XML with fixed numeric formatting, so the file
is byte-identical on every run and diffs meaningfully when a dimension changes.

Why the sensors go in from the SIDE
-----------------------------------
The single most important decision in this drawing. A thermocouple inserted from the
heated face, or from the back face, runs its wire ALONG the temperature gradient. Metal
wire is orders of magnitude more conductive than the polymer, so it short-circuits the
gradient and drags the junction towards the surface temperature - it reads a number that
is not the temperature that would exist without it. The error is worst exactly where the
gradient is steepest, which is where the measurement matters.

Inserting from the side edge runs the wire along an ISOTHERM instead. The wire is at the
same temperature as its surroundings for the whole of its buried length, so it has
nothing to short-circuit. This is standard practice in in-depth TPS thermocouple
installation and it is not optional here.

The holes are staggered in the other in-plane direction so that no hole lies in another
hole's thermal shadow, and every junction sits on the coupon's centreline, as far from
the side edges as it can get - the 1-D model has no side edges, and the centre is where
that assumption is least wrong.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

INK = "#1b1b1e"
MUTED = "#7a7d85"
HOT = "#c1442a"
DEEP = "#2f5d8f"
PAPER = "#ffffff"


@dataclass(frozen=True)
class DrawingParams:
    """Dimensions in millimetres. These must match the coupon actually printed."""

    coupon_x_mm: float = 60.0
    coupon_y_mm: float = 60.0
    coupon_z_mm: float = 10.0
    hole_diameter_mm: float = 1.2
    """Suits a 1.0 mm sheathed probe or a welded bead. Bigger holes need filling."""
    insertion_depth_mm: float = 30.0
    """Half the coupon width: every junction ends on the centreline."""
    sensor_depths_mm: tuple[float, ...] = (0.0, 2.0, 5.0, 9.0)
    """Depth BELOW THE HEATED FACE. 0.0 is a surface groove, not a free-standing bead."""
    sensor_x_positions_mm: tuple[float, ...] = (15.0, 25.0, 35.0, 45.0)
    scale_px_per_mm: float = 5.0

    def __post_init__(self) -> None:
        if len(self.sensor_depths_mm) != len(self.sensor_x_positions_mm):
            raise ValueError("every sensor needs both a depth and an x position")
        if max(self.sensor_depths_mm) >= self.coupon_z_mm:
            raise ValueError("a sensor deeper than the coupon is not a sensor")
        if self.insertion_depth_mm > self.coupon_y_mm:
            raise ValueError("insertion depth exceeds the coupon")


def _f(value: float) -> str:
    """Fixed formatting - determinism depends on this, not on repr()."""
    return f"{value:.2f}"


def _line(x1, y1, x2, y2, *, colour=INK, width=1.0, dash=None) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
            f'stroke="{colour}" stroke-width="{width}"{d}/>')


def _rect(x, y, w, h, *, fill="none", stroke=INK, width=1.2) -> str:
    return (f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')


def _text(x, y, content, *, size=10, colour=INK, anchor="start", weight="normal",
          style="normal") -> str:
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="{size}" fill="{colour}" text-anchor="{anchor}" '
            f'font-weight="{weight}" font-style="{style}">{content}</text>')


def _dim_h(x1, x2, y, label, *, colour=MUTED) -> list[str]:
    """Horizontal dimension line with end arrows and a centred label."""
    return [
        _line(x1, y, x2, y, colour=colour, width=0.8),
        f'<polygon points="{_f(x1)},{_f(y)} {_f(x1 + 5)},{_f(y - 2.2)} '
        f'{_f(x1 + 5)},{_f(y + 2.2)}" fill="{colour}"/>',
        f'<polygon points="{_f(x2)},{_f(y)} {_f(x2 - 5)},{_f(y - 2.2)} '
        f'{_f(x2 - 5)},{_f(y + 2.2)}" fill="{colour}"/>',
        _text((x1 + x2) / 2, y - 4, label, size=9, colour=colour, anchor="middle"),
    ]


def _dim_v(y1, y2, x, label, *, colour=MUTED) -> list[str]:
    return [
        _line(x, y1, x, y2, colour=colour, width=0.8),
        f'<polygon points="{_f(x)},{_f(y1)} {_f(x - 2.2)},{_f(y1 + 5)} '
        f'{_f(x + 2.2)},{_f(y1 + 5)}" fill="{colour}"/>',
        f'<polygon points="{_f(x)},{_f(y2)} {_f(x - 2.2)},{_f(y2 - 5)} '
        f'{_f(x + 2.2)},{_f(y2 - 5)}" fill="{colour}"/>',
        _text(x + 4, (y1 + y2) / 2 + 3, label, size=9, colour=colour),
    ]


def build_svg(p: DrawingParams) -> str:
    s = p.scale_px_per_mm
    width, height = 980.0, 740.0
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(width)}" '
        f'height="{_f(height)}" viewBox="0 0 {_f(width)} {_f(height)}">',
        f'<rect width="{_f(width)}" height="{_f(height)}" fill="{PAPER}"/>',
        _text(40, 42, "AETHER M8 — thermal coupon, sensor placement", size=17,
              weight="bold"),
        _text(40, 60, "All dimensions in millimetres. Depths are measured from the "
                      "HEATED face. Generated by cad/make_sensor_drawing.py — do not "
                      "hand-edit.", size=10, colour=MUTED),
    ]

    # ---- PLAN VIEW ------------------------------------------------------------------
    px, py = 70.0, 110.0
    pw, ph = p.coupon_x_mm * s, p.coupon_y_mm * s
    out += [
        _text(px, py - 12, "PLAN — looking at the heated face", size=11, weight="bold"),
        _rect(px, py, pw, ph, fill="#f6f7f9"),
        _line(px, py + ph / 2, px + pw, py + ph / 2, colour=MUTED, width=0.6,
              dash="6 4"),
        _text(px + pw + 6, py + ph / 2 + 3, "centreline", size=8, colour=MUTED),
    ]
    for depth, x_mm in zip(p.sensor_depths_mm, p.sensor_x_positions_mm, strict=True):
        hx = px + x_mm * s
        entry_y = py + ph
        tip_y = py + ph - p.insertion_depth_mm * s
        out += [
            _line(hx, entry_y, hx, tip_y, colour=DEEP, width=2.0),
            f'<circle cx="{_f(hx)}" cy="{_f(tip_y)}" r="3.4" fill="{HOT}" '
            f'stroke="{PAPER}" stroke-width="1.2"/>',
            _text(hx, entry_y + 16, f"{x_mm:.0f}", size=8, colour=MUTED, anchor="middle"),
            _text(hx, tip_y - 8, f"{depth:.0f} mm", size=8.5, colour=HOT,
                  anchor="middle", weight="bold"),
        ]
    out += _dim_h(px, px + pw, py - 26, f"{p.coupon_x_mm:.0f}")
    out += _dim_v(py, py + ph, px - 24, f"{p.coupon_y_mm:.0f}")
    out += _dim_v(py + ph - p.insertion_depth_mm * s, py + ph, px + pw + 34,
                  f"{p.insertion_depth_mm:.0f} insertion")
    out += [
        _text(px, py + ph + 34, "hole entry positions, measured from the left edge",
              size=8.5, colour=MUTED),
        _text(px, py + ph + 48, "● junction on the centreline    ▬ drilled hole "
                                f"⌀{p.hole_diameter_mm:.1f}", size=8.5, colour=MUTED),
    ]

    # ---- SECTION A-A ----------------------------------------------------------------
    sx, sy = 560.0, 150.0
    sw, sh = p.coupon_x_mm * s, p.coupon_z_mm * s * 3.0   # thickness exaggerated x3
    out += [
        _text(sx, sy - 34, "SECTION — through the centreline", size=11, weight="bold"),
        _text(sx, sy - 20, "thickness shown at 3× the in-plane scale", size=8.5,
              colour=MUTED, style="italic"),
        _rect(sx, sy, sw, sh, fill="#f6f7f9"),
    ]
    # heater on the top face
    out += [
        _rect(sx, sy - 12, sw, 12, fill="#f3ded9", stroke=HOT, width=1.0),
        _text(sx + sw / 2, sy - 3, "HEATER — heated face", size=8.5, colour=HOT,
              anchor="middle", weight="bold"),
        _text(sx + sw + 8, sy + sh + 4, "back face → room air", size=8.5, colour=DEEP),
    ]
    for depth, x_mm in zip(p.sensor_depths_mm, p.sensor_x_positions_mm, strict=True):
        dy = sy + depth * s * 3.0
        jx = sx + x_mm * s
        out += [
            _line(sx, dy, sx + sw, dy, colour=MUTED, width=0.6, dash="3 3"),
            f'<circle cx="{_f(jx)}" cy="{_f(dy)}" r="4.0" fill="{HOT}" '
            f'stroke="{PAPER}" stroke-width="1.3"/>',
            _text(sx + sw + 8, dy + 3.5, f"x = {depth:.0f} mm", size=9, colour=INK),
        ]
    out += _dim_v(sy, sy + sh, sx - 22, f"{p.coupon_z_mm:.0f}")
    out += [
        _text(sx, sy + sh + 26,
              "Wires run along isotherms (into the page), never across the gradient.",
              size=8.5, colour=MUTED),
    ]

    # ---- NOTES ----------------------------------------------------------------------
    notes = [
        ("1.", "Drill or print the sensor holes PARALLEL to the heated face, entering "
               "from one side edge. A wire that runs across the temperature gradient "
               "conducts heat to its own junction and reads low."),
        ("2.", f"Hole diameter ⌀{p.hole_diameter_mm:.1f} mm, insertion "
               f"{p.insertion_depth_mm:.0f} mm so every junction sits on the "
               f"centreline, as far from the side edges as possible."),
        ("3.", "Back-fill each hole with a thermally conductive paste or the same "
               "polymer, so the junction is not sitting in an air pocket. An unfilled "
               "hole is an insulating void and will read low and lag."),
        ("4.", "The 0 mm sensor sits in a shallow surface groove under the heater, not "
               "free-standing on the face. Record the ACTUAL depth achieved, with an "
               "uncertainty, in the metadata sidecar — the model is fitted against the "
               "declared depth, so a 0.5 mm error there becomes a property error."),
        ("5.", "Measure every depth after installation (calipers on a sectioned scrap "
               "coupon printed in the same job, or an X-ray/CT if available). Nominal "
               "depths are a drawing; measured depths are data."),
        ("6.", "Route wires out through the holder's wire gap with strain relief. A "
               "tugged thermocouple moves, and a moved thermocouple invalidates every "
               "run after it moved."),
    ]
    ny = 500.0
    out.append(_text(40, ny, "NOTES", size=11, weight="bold"))
    ny += 18
    for tag, body in notes:
        out.append(_text(40, ny, tag, size=9, colour=HOT, weight="bold"))
        for i, chunk in enumerate(_wrap(body, 118)):
            out.append(_text(62, ny + i * 12.5, chunk, size=9))
        ny += 12.5 * len(_wrap(body, 118)) + 6
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _wrap(text: str, width: int) -> list[str]:
    """Deterministic greedy word wrap. No dependency on terminal width or locale."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=".")
    args = ap.parse_args(argv)

    params = DrawingParams()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / "sensor_placement.svg"
    target.write_text(build_svg(params))

    print(f"coupon {params.coupon_x_mm:.0f} x {params.coupon_y_mm:.0f} x "
          f"{params.coupon_z_mm:.0f} mm")
    print("sensor depths [mm]: " + ", ".join(f"{d:.1f}" for d in params.sensor_depths_mm))
    print("entry x positions [mm]: "
          + ", ".join(f"{x:.1f}" for x in params.sensor_x_positions_mm))
    print(f"\n  {target}")
    print("\nThese are NOMINAL depths. The metadata sidecar must carry the MEASURED "
          "depth and its uncertainty for each channel; see data_schema.md.")
    print("For a PDF: `rsvg-convert -f pdf -o sensor_placement.pdf sensor_placement.svg`, "
          "or open the SVG in any browser and print to PDF. The PDF is not generated "
          "here because it would add an external dependency to a deterministic script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
