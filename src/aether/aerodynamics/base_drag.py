"""Base (afterbody) pressure drag: a stated ASSUMPTION with a band, not a computation.

Conceptual anchor
-----------------
The Fidelity-1 CFD stops at the maximum-radius station (A-CFD-4), so it returns the drag of
the forebody only, measured against freestream pressure acting on the back. The real back of
a capsule sits in a separated wake at some base pressure p_b. If p_b is below p_inf the wake
sucks on the body and adds drag; if it is above, it pushes and removes some:

    C_D,base = -Cp_b * (A_base / A_ref),    Cp_b = (p_b - p_inf) / q_inf
             = (1 - p_b/p_inf) * 2 / (gamma * M^2) * (A_base / A_ref)

The second line is algebra (q_inf = gamma/2 * p_inf * M^2), not a correlation. Everything
uncertain is in ONE number, the base-pressure ratio beta = p_b / p_inf, and the 1/M^2 factor
is why the whole term fades at hypersonic speed whatever beta is.

What is known about beta, and from where
-----------------------------------------
* beta >= 0 exactly (a pressure cannot be negative): the "vacuum limit" Cp_b = -2/(gamma M^2).
* Supersonic bluff-body wakes are below freestream pressure (beta < 1): NACA Report 1051
  (Chapman 1951) and NACA TN 3819 (Love 1957) - opened for the sourcing report
  (docs/validation/sourcing_report.md item 4), which found that neither gives a closed-form
  Cp_b(M) usable here. They are cited for the DIRECTION only; no number is taken from them.
* At Mach 10-20 the ratio RISES ABOVE ONE for blunted bodies: NASA TN D-4800 (Miller 1968,
  NTRS 19680026196), figure 11(b), area-mean p_b/p_inf for 9-deg cones of bluntness 0-0.8,
  laminar. Opened and read for this module on 2026-09-20: the plotted points lie between
  about 0.2 and about 3, increasing with Mach number and with bluntness. Those two end
  values are READ OFF A LOG-SCALE GRAPH by eye and are good to perhaps +/-30%; they are used
  only to set the width of a band. The same report's text (p. 12-13) states that base drag
  was "less than approximately 2 percent of the total drag coefficient for bluntness ratios
  of 0.55 and 0.8" at Mach 10.6-19.6 - for slender 9-deg cones whose forebody drag is far
  smaller than a capsule's, so for a capsule the fraction is smaller still.

The model
---------
beta is bounded, not predicted:

    Mach <= mach_lo (6):   beta in [0, 1],            nominal 0.5
    Mach >= mach_hi (10):  beta in [0, beta_hi (3)],  nominal 1.0
    in between:            linear in Mach

The nominal values are the midpoint of the exact interval at low Mach and "base at
freestream pressure" at high Mach. They are DECLARED CHOICES inside a sourced band, not
measurements, and no source found gives a flight-Reynolds-number value (sourcing report,
unresolved gap). `position` in [-1, +1] moves C_D,base across the band (+1 = most drag,
beta = 0); M7 should sample it UNIFORMLY - a band is not a standard deviation.

A_base / A_ref is taken as 1: the whole aft-facing projected area is assumed to see p_b.
That is the largest it can be, so the band is not narrowed by an afterbody-shape argument
this project has not made.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from ..utils.constants import GAMMA_AIR


@dataclass(frozen=True)
class BaseDragModel:
    gamma: float = GAMMA_AIR
    mach_lo: float = 6.0
    mach_hi: float = 10.0
    beta_nominal_lo_mach: float = 0.5
    beta_nominal_hi_mach: float = 1.0
    beta_max_lo_mach: float = 1.0
    beta_max_hi_mach: float = 3.0     # NASA TN D-4800 fig. 11(b), read by eye
    beta_min: float = 0.0             # exact
    base_area_ratio: float = 1.0

    def _blend(self, mach: np.ndarray, lo: float, hi: float) -> np.ndarray:
        w = np.clip((mach - self.mach_lo) / (self.mach_hi - self.mach_lo), 0.0, 1.0)
        return lo + w * (hi - lo)

    def vacuum_limit(self, mach) -> np.ndarray:
        """Largest possible base drag coefficient, p_b = 0."""
        mach = np.asarray(mach, dtype=float)
        return self.base_area_ratio * 2.0 / (self.gamma * mach**2)

    def beta(self, mach, position: float = 0.0) -> np.ndarray:
        """Base-pressure ratio p_b/p_inf at `position` in [-1, +1] of the band."""
        if not -1.0 <= position <= 1.0:
            raise ValueError("base-drag band position must lie in [-1, +1]")
        mach = np.asarray(mach, dtype=float)
        nominal = self._blend(mach, self.beta_nominal_lo_mach, self.beta_nominal_hi_mach)
        top = self._blend(mach, self.beta_max_lo_mach, self.beta_max_hi_mach)
        # position +1 -> beta_min (most drag); -1 -> top of the band (least drag)
        return np.where(position >= 0.0, nominal - position * (nominal - self.beta_min),
                        nominal - position * (top - nominal))

    def cd_base(self, mach, position: float = 0.0) -> np.ndarray:
        """Additive base drag coefficient, referenced to the frontal area."""
        return (1.0 - self.beta(mach, position)) * self.vacuum_limit(mach)

    def band(self, mach) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(lowest, nominal, highest) C_D,base."""
        return self.cd_base(mach, -1.0), self.cd_base(mach, 0.0), self.cd_base(mach, 1.0)

    def to_dict(self) -> dict:
        return {**asdict(self), "source_of_band":
                "exact vacuum limit; NASA TN D-4800 fig. 11(b) read by eye for beta_max"}
