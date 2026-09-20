"""Grid Convergence Index - the five-step procedure of Celik et al. (2008).

I. B. Celik, U. Ghia, P. J. Roache, C. J. Freitas, H. Coleman, P. E. Raad, "Procedure for
estimation and reporting of uncertainty due to discretization in CFD applications",
ASME J. Fluids Engineering 130(7), 078001, 2008.

Index convention follows the paper: 1 = fine, 2 = medium, 3 = coarse, so h1 < h2 < h3.

The procedure is only meaningful for monotone convergence. Oscillatory convergence
(eps32/eps21 < 0) and divergence (|eps21| > |eps32|) are reported as such, never hidden:
shock-capturing schemes are formally first-order at the shock, so a pathological
observed order on a shock-position metric is an expected outcome, not a bug.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

SAFETY_FACTOR_THREE_GRIDS = 1.25  # Celik et al. (2008), step 5; Roache's Fs for 3 grids


@dataclass(frozen=True)
class GciResult:
    """Outcome of the three-grid study for ONE scalar quantity."""

    quantity: str
    phi_fine: float
    phi_medium: float
    phi_coarse: float
    r21: float
    r32: float
    eps21: float
    eps32: float
    convergence_type: str
    """'monotone', 'oscillatory', 'divergent' or 'converged_to_tolerance'."""
    observed_order: float
    phi_extrapolated: float
    rel_error_fine_medium: float
    rel_error_extrapolated: float
    gci_fine: float
    gci_medium: float
    asymptotic_ratio: float
    """GCI_32 / (r21^p GCI_21); ~1 when the grids are in the asymptotic range."""
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def observed_order(eps21: float, eps32: float, r21: float, r32: float,
                   tol: float = 1e-12, max_iter: int = 200) -> float:
    """Apparent order p from Celik et al. eq. (3), by fixed-point iteration.

    For a constant refinement ratio q(p) vanishes and p = ln|eps32/eps21| / ln r21.
    """
    ratio = eps32 / eps21
    s = 1.0 if ratio > 0 else -1.0
    base = math.log(abs(ratio))
    p = abs(base) / math.log(r21)
    for _ in range(max_iter):
        q = math.log((r21**p - s) / (r32**p - s))
        p_new = abs(base + q) / math.log(r21)
        if abs(p_new - p) < tol:
            return p_new
        p = p_new
    return p


def grid_convergence_index(
    quantity: str,
    phi_fine: float,
    phi_medium: float,
    phi_coarse: float,
    h_fine: float,
    h_medium: float,
    h_coarse: float,
    negligible_change: float = 1e-10,
) -> GciResult:
    """Richardson extrapolation and GCI for a three-grid sequence.

    ``h`` is the representative cell size, h = (total volume / N)^(1/dim). Only the
    ratios matter. NaNs are returned, with an explanatory note, wherever the procedure
    is undefined rather than silently substituting an assumed order.
    """
    if not (h_fine < h_medium < h_coarse):
        raise ValueError("require h_fine < h_medium < h_coarse")
    r21, r32 = h_medium / h_fine, h_coarse / h_medium
    eps21, eps32 = phi_medium - phi_fine, phi_coarse - phi_medium
    nan = float("nan")

    def _result(kind: str, p=nan, ext=nan, e_ext=nan, gci21=nan, gci32=nan, ar=nan, note=""):
        ea21 = abs(eps21 / phi_fine) if phi_fine != 0 else nan
        return GciResult(quantity, phi_fine, phi_medium, phi_coarse, r21, r32, eps21, eps32,
                         kind, p, ext, ea21, e_ext, gci21, gci32, ar, note)

    scale = max(abs(phi_fine), abs(phi_medium), abs(phi_coarse), 1e-300)
    if abs(eps21) / scale < negligible_change and abs(eps32) / scale < negligible_change:
        return _result("converged_to_tolerance", gci21=0.0, gci32=0.0, ext=phi_fine, e_ext=0.0,
                       note="all three grids agree to within the negligible-change tolerance")
    if abs(eps21) / scale < negligible_change or abs(eps32) / scale < negligible_change:
        return _result("oscillatory", note="one of the two differences is ~0; the observed "
                       "order is undefined (Celik et al. note this indicates oscillatory "
                       "convergence or, rarely, an exact solution)")

    p = observed_order(eps21, eps32, r21, r32)
    ratio = eps32 / eps21
    if ratio < 0:
        kind = "oscillatory"
        note = ("eps32/eps21 < 0: oscillatory convergence. p and GCI are computed per Celik "
                "et al. but Richardson extrapolation is not reliable here.")
    elif abs(eps21) > abs(eps32):
        kind = "divergent"
        note = ("|eps21| > |eps32|: the solution changes MORE between the two finest grids "
                "than between the two coarsest. Not in the asymptotic range.")
    else:
        kind, note = "monotone", ""

    ext = (r21**p * phi_fine - phi_medium) / (r21**p - 1.0)
    e_ext = abs((ext - phi_fine) / ext) if ext != 0 else nan
    ea21 = abs(eps21 / phi_fine)
    ea32 = abs(eps32 / phi_medium)
    gci21 = SAFETY_FACTOR_THREE_GRIDS * ea21 / (r21**p - 1.0)
    gci32 = SAFETY_FACTOR_THREE_GRIDS * ea32 / (r32**p - 1.0)
    ar = gci32 / (r21**p * gci21) if gci21 > 0 else nan
    return _result(kind, p, ext, e_ext, gci21, gci32, ar, note)
