"""Effective nose radius of a blunt spherical-segment forebody with a rounded corner.

Conceptual anchor
-----------------
Sutton-Graves says stagnation heating goes as 1/sqrt(R_n). The R_n in that expression is
not really "the radius of the thing at the front" - it is a stand-in for the
stagnation-point VELOCITY GRADIENT (dU/dS)_s, the rate at which flow accelerates away
from the stagnation point along the surface. A steep gradient thins the boundary layer
and drives heat into the wall; a gentle gradient does not. For a hemisphere the two are
interchangeable, because Newtonian flow gives

    (dU/dS)_s,hemi = (1/R) sqrt(2 p_s / rho_s)

and the only length in sight is the sphere's own radius.

For a SHALLOW spherical segment - a wide, nearly flat cap of radius R_n sitting on a body
of much smaller radius R_b - that identification breaks. The flow does not get to feel
the cap's gentle curvature all the way out: it is turned by the body's shoulder long
before. The gradient stops scaling with R_n and comes to be set by R_b and by the corner
radius R_c instead. In the limit of a genuinely flat face the cap radius is infinite, yet
the gradient is emphatically finite - so the heating does NOT fall to zero, as a naive
1/sqrt(R_n) would insist. The benefit of flattening the nose saturates.

This module supplies the saturation, as an EFFECTIVE radius R_eff to hand to
Sutton-Graves in place of R_n. Full derivation and worked numbers, written to be followed
and defended without this code in front of you: `docs/theory/effective_nose_radius.md`.

Definition - the sources' own, not this project's
--------------------------------------------------
Zoby & Sullivan (NASA TM X-1067, p. 4) define R_eff by declaring the blunt body's
gradient to be that of a hemisphere of some other radius:

    (dU/dS)_s,BB = (1/R_eff) sqrt(2 p_s / rho_s)                              (their eq. 4)
    R_b / R_eff  = (dU/dS)_s,BB / (dU/dS)_s,hemi                              (their eq. 5)

with the reference hemisphere having the BODY radius R_b. Converting a velocity-gradient
ratio into an effective radius is therefore the primary's step, not an inference made
here. Zoby himself later used exactly this R_eff inside a Sutton-Graves-form heating
correlation (NASA TN D-4799, eq. 1), which is the same substitution this project makes.

Two dimensionless groups, in the sources' notation:

    K = R_b / R_n     body radius over nose radius.  K = 0 is a flat face,
                      K = 1 is a hemisphere. NOTE this is the RECIPROCAL of the
                      "bluntness" the rest of AETHER talks in.
    R = R_c / R_b     corner radius over body radius. R = 0 is a sharp corner.

Where the numbers come from
---------------------------
`_RB_OVER_REFF` below is NASA TN D-5121 (Ellison, 1969) TABLE I, the alpha = 0 rows, read
off a 400 dpi render of the printed page. It is a measurement: local pressures on nine
models at M = 8, Re_D = 1.37e6, reduced to a velocity gradient by isentropic expansion.
Mirrored in `data/reference/stagnation_velocity_gradient.yaml` with its full provenance,
and pinned against it by `tests/test_stagnation_gradient.py` so the two cannot drift.

The K = 1 row is NOT measured and is not read off anything. Ellison's experiment stops at
K = 0.707. When R_n = R_b the segment IS a hemisphere, eq. (5) gives R_eff = R_b = R_n
identically, and a corner radius has nothing left to blend - so the row is 1.0 for every
corner ratio, exactly, and Zoby & Sullivan's figure 4 shows all five of their curves
meeting there.

Neither source publishes a formula. Zoby & Sullivan print faired curves; Ellison prints a
3x3 table and two charts; Stallings (NASA TN, 1967) tells the reader in as many words to
interpolate from the charts. **The interpolation here is this project's construction over
the primaries' data points, and nothing else.** It is deliberately the dullest choice that
cannot invent behaviour between the nodes: shape-preserving cubic (PCHIP) in K, linear in
R. PCHIP because the K dependence has real curvature and a monotone interpolant cannot
overshoot into a non-physical wiggle; linear in R because the three measured points are
very nearly on a line and the whole AETHER design box sits inside the first interval.

How wrong this can be
---------------------
Ellison compared his measurements with Zoby & Sullivan directly (his p. 5, verbatim):
"The data of the present investigation agree with the results of Zoby and Sullivan
(ref. 6) within 10 percent for K = 0 and K = 0.707; however, for K = 0.417 and R = 0, the
disagreement is about 20 percent."

That is the primary's own number and it is the uncertainty this project carries. It is
worst at K ~ 0.42 - which is, awkwardly, exactly where AETHER's M4 front sits. R_eff
enters heating as 1/sqrt(R_eff), so 20% on R_eff is about 10% on heat flux. Bigger than
the Sutton-Graves constant's own +-4% (A-HEAT-1), and it must be propagated in M7 rather
than assumed away. Ellison's table is the CONSERVATIVE of the two (higher R_b/R_eff,
hence smaller R_eff, hence more heating), which is why it and not the figure read is what
the model is built on.

Where this must not be used
---------------------------
- **K > 1**, i.e. a nose radius SMALLER than the body radius: a sphere-cone (Viking,
  Pathfinder, MSL), not a spherical segment. Neither source covers it, and the little that
  is said about it points the other way - a conical flank RAISES R_eff above R_n. The
  caller is given R_eff = R_n there, flagged, which is both the conventional engineering
  choice and, if that hint is right, the conservative one.
- **Angle of attack.** Both sources' numbers used here are alpha = 0. AETHER's trajectory
  is ballistic and non-lifting (A-TRAJ-2), so this costs nothing today and blocks any
  future lifting entry.
- **M < 3.5.** The entire transfer of M = 8 tunnel data to a 7.4 km/s flight condition
  rests on Zoby & Sullivan's finding that the stagnation-region pressure distribution -
  and therefore this RATIO, though not the gradient itself - is invariant above about
  M = 3.5. Below that it is unsupported.
- **A long straight fore-cone.** The sources' bodies are a spherical segment blended
  straight into a cylinder by the corner. AETHER's capsule can put a conical segment in
  between; when that segment is long the body is not the one that was measured.
  `effective_nose_radius_report` returns its length as a fraction of the body radius so a
  caller can see this rather than be told it is fine.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.interpolate import PchipInterpolator

CAP_RADIUS = "cap_radius"
"""Legacy model: R_eff = R_n. Correct only at the hemisphere, K = 1 (A-GEO-3)."""

VELOCITY_GRADIENT = "velocity_gradient"
"""Corrected model: R_eff from the measured stagnation velocity gradient (A-GEO-3a)."""

MODELS = (CAP_RADIUS, VELOCITY_GRADIENT)

# NASA TN D-5121 (Ellison 1969) TABLE I, alpha = 0 rows, plus the exact hemisphere row.
# Values are R_B/R_eff. Rows are K = R_b/R_n, columns are R = R_c/R_b.
_K_NODES = (0.0, 0.417, 0.707, 1.0)
_R_NODES = (0.0, 0.2, 0.4)
_RB_OVER_REFF = (
    (0.317, 0.377, 0.455),   # K = 0      flat face            | Ellison Table I
    (0.587, 0.609, 0.640),   # K = 0.417                       | Ellison Table I
    (0.738, 0.772, 0.817),   # K = 0.707                       | Ellison Table I
    (1.000, 1.000, 1.000),   # K = 1      hemisphere           | exact, by eq. (5)
)

MAX_CORNER_RATIO = 0.4
"""Largest R_c/R_b measured (Ellison). Zoby & Sullivan stop at 0.30."""

ELLISON_MACH = 8.0
ELLISON_REYNOLDS_D = 1.37e6

# Declared here rather than discovered later: how much straight fore-cone between the
# spherical cap and the corner is still "a spherical segment blended into a cylinder".
# This is an ENGINEERING JUDGMENT with no source - the sources' bodies have none at all -
# and it only ever raises a flag, never changes a number. Expressed as the span in radius
# that the cone covers, divided by the body radius.
CONE_SPAN_FLAG_FRACTION = 0.10


@lru_cache(maxsize=1)
def _interpolators() -> tuple[PchipInterpolator, ...]:
    """One monotone cubic in K per corner-ratio node. Built once, deterministic."""
    table = np.asarray(_RB_OVER_REFF, dtype=float)
    return tuple(
        PchipInterpolator(np.asarray(_K_NODES, dtype=float), table[:, j], extrapolate=False)
        for j in range(table.shape[1])
    )


def rb_over_reff(k_body_over_nose: float, corner_ratio: float) -> float:
    """R_b/R_eff = (dU/dS)_s,BB / (dU/dS)_s,hemi, interpolated over the Ellison table.

    `k_body_over_nose` must be in [0, 1]; `corner_ratio` is clamped to [0, 0.4] (the
    measured range) by the caller, not here. Monotone increasing in both arguments, so
    R_eff is monotone DECREASING in K - equivalently, increasing in nose radius, which is
    the physical direction - and decreasing as the corner is rounded.
    """
    k = float(k_body_over_nose)
    if not 0.0 <= k <= 1.0:
        raise ValueError(
            f"k_body_over_nose (= R_b/R_n) must be in [0, 1]; got {k}. Above 1 the body "
            "is a sphere-cone, which neither source covers - callers handle that case "
            "before reaching here."
        )
    r = float(np.clip(corner_ratio, _R_NODES[0], _R_NODES[-1]))
    column_values = np.array([float(f(k)) for f in _interpolators()])
    return float(np.interp(r, np.asarray(_R_NODES, dtype=float), column_values))


@dataclass(frozen=True)
class EffectiveNoseRadiusReport:
    """What the model did, and every reason a reader might distrust it.

    Returned alongside the number so that "the correction was extrapolated" is visible in
    a candidate log rather than buried. `notes` is empty when nothing is off-nominal.
    """

    model: str
    effective_nose_radius_m: float
    nose_radius_m: float
    body_radius_m: float
    k_body_over_nose: float
    corner_ratio: float
    cone_span_fraction: float
    extrapolated: bool
    notes: tuple[str, ...]

    @property
    def ratio_to_cap_radius(self) -> float:
        """R_eff / R_n. 1.0 means the legacy model would have given the same answer."""
        return self.effective_nose_radius_m / self.nose_radius_m


def effective_nose_radius_report(
    nose_radius_m: float,
    body_radius_m: float,
    corner_radius_m: float,
    model: str = VELOCITY_GRADIENT,
    cone_span_fraction: float = 0.0,
) -> EffectiveNoseRadiusReport:
    """Effective nose radius [m] plus its validity flags. Never raises on a valid capsule.

    `cone_span_fraction` is the radial span of any straight fore-cone between the cap and
    the corner, divided by the body radius. It changes no number; it only raises a note.
    """
    if model not in MODELS:
        raise ValueError(f"unknown effective_nose_radius_model {model!r}, expected one of {MODELS}")
    for name, value in (("nose_radius_m", nose_radius_m), ("body_radius_m", body_radius_m)):
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be finite and positive, got {value}")

    k = body_radius_m / nose_radius_m
    corner_ratio = corner_radius_m / body_radius_m
    notes: list[str] = []
    extrapolated = False

    if model == CAP_RADIUS:
        return EffectiveNoseRadiusReport(
            model=model, effective_nose_radius_m=float(nose_radius_m),
            nose_radius_m=float(nose_radius_m), body_radius_m=float(body_radius_m),
            k_body_over_nose=float(k), corner_ratio=float(corner_ratio),
            cone_span_fraction=float(cone_span_fraction), extrapolated=False,
            notes=("legacy model: R_eff = R_n, exact only at the hemisphere K = 1",),
        )

    if k > 1.0:
        # Sphere-cone family. Outside both sources; fall back to the cap radius, which is
        # continuous with the K = 1 anchor (there R_eff = R_b = R_n) and is the
        # conventional choice. See the module docstring.
        notes.append(
            f"R_b/R_n = {k:.3f} > 1 (sphere-cone, not a spherical segment): outside "
            "NASA TN D-5121 and TM X-1067; fell back to R_eff = R_n"
        )
        return EffectiveNoseRadiusReport(
            model=model, effective_nose_radius_m=float(nose_radius_m),
            nose_radius_m=float(nose_radius_m), body_radius_m=float(body_radius_m),
            k_body_over_nose=float(k), corner_ratio=float(corner_ratio),
            cone_span_fraction=float(cone_span_fraction), extrapolated=True,
            notes=tuple(notes),
        )

    if corner_ratio > MAX_CORNER_RATIO:
        extrapolated = True
        notes.append(
            f"R_c/R_b = {corner_ratio:.3f} exceeds the measured maximum "
            f"{MAX_CORNER_RATIO}; clamped to it"
        )
    if cone_span_fraction > CONE_SPAN_FLAG_FRACTION:
        notes.append(
            f"straight fore-cone spans {cone_span_fraction:.3f} of the body radius "
            f"(flag above {CONE_SPAN_FLAG_FRACTION}); the reference bodies blend the "
            "spherical cap directly into the corner"
        )

    r_eff = body_radius_m / rb_over_reff(k, corner_ratio)
    return EffectiveNoseRadiusReport(
        model=model, effective_nose_radius_m=float(r_eff),
        nose_radius_m=float(nose_radius_m), body_radius_m=float(body_radius_m),
        k_body_over_nose=float(k), corner_ratio=float(corner_ratio),
        cone_span_fraction=float(cone_span_fraction), extrapolated=extrapolated,
        notes=tuple(notes),
    )


def effective_nose_radius_m(
    nose_radius_m: float,
    body_radius_m: float,
    corner_radius_m: float,
    model: str = VELOCITY_GRADIENT,
) -> float:
    """Effective nose radius [m] only. See `effective_nose_radius_report` for the flags."""
    return effective_nose_radius_report(
        nose_radius_m, body_radius_m, corner_radius_m, model
    ).effective_nose_radius_m
