"""Summary statistics, interval estimates and convergence checks for M7.

Conceptual anchor
-----------------
A Monte-Carlo study reports statistics of a FINITE sample, so every number it prints is
itself uncertain. Three habits are enforced here because their absence is how uncertainty
studies mislead:

**A percentile, not a mean.** The mean bondline temperature is the temperature of no
vehicle. A design is safe if it is safe on a bad day, so the reported design quantity is a
high percentile and the mean is carried only as context.

**Zero events is not zero probability.** Observing 0 violations in 500 samples does not
mean the violation probability is 0 - it means it is below roughly 3/n. Every violation
probability here comes back with a confidence interval, and a zero count prints as
"< x% at 95% confidence" rather than as "0".

**Convergence is measured, not assumed.** Statistics are recomputed at increasing sample
sizes and the bootstrap half-width of each is reported against a declared tolerance. A
study that never shows this is claiming a number it has not earned.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import beta, norm

DEFAULT_PERCENTILES = (5.0, 50.0, 95.0, 99.0)


# ---------------------------------------------------------------------------------------
# continuous outputs
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class SampleSummary:
    """Everything reported about one output over one sample."""

    n: int
    n_finite: int
    mean: float
    std: float
    percentiles: dict[str, float]
    minimum: float
    maximum: float

    def to_dict(self) -> dict[str, Any]:
        return {"n": self.n, "n_finite": self.n_finite, "mean": self.mean,
                "std": self.std, "percentiles": dict(self.percentiles),
                "min": self.minimum, "max": self.maximum}


def summarise(values, percentiles: tuple[float, ...] = DEFAULT_PERCENTILES) -> SampleSummary:
    """Mean, sample s.d. (ddof=1) and percentiles of the FINITE entries of `values`.

    Non-finite entries are excluded and COUNTED, never silently dropped: a design whose
    trajectory skipped out on 3% of draws has a different meaning from one that did not,
    and `n_finite` is where that shows.
    """
    arr = np.asarray(values, dtype=float).ravel()
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        nan = float("nan")
        return SampleSummary(n=int(arr.size), n_finite=0, mean=nan, std=nan,
                             percentiles={_pct_key(p): nan for p in percentiles},
                             minimum=nan, maximum=nan)
    return SampleSummary(
        n=int(arr.size), n_finite=int(finite.size),
        mean=float(np.mean(finite)),
        std=float(np.std(finite, ddof=1)) if finite.size > 1 else 0.0,
        percentiles={_pct_key(p): float(np.percentile(finite, p)) for p in percentiles},
        minimum=float(np.min(finite)), maximum=float(np.max(finite)),
    )


def _pct_key(p: float) -> str:
    return f"p{p:g}"


def quantile(values, q: float) -> float:
    """The q-th percentile (0-100) of the finite entries, linear interpolation.

    This is the estimator the robust objective is DECLARED to use
    (`configs/uncertainty.yaml`, `robust.quantile_estimator: empirical`). At the small
    inner sample sizes robust optimisation can afford it is a noisy and slightly biased
    estimator of the true quantile - which is exactly why `robust.verify_shortcut`
    measures that bias against full Monte Carlo instead of arguing about it.
    """
    arr = np.asarray(values, dtype=float).ravel()
    finite = arr[np.isfinite(arr)]
    return float(np.percentile(finite, q)) if finite.size else float("nan")


def bootstrap_ci(values, statistic: Callable[[np.ndarray], float], *,
                 n_bootstrap: int = 1000, confidence: float = 0.95,
                 seed: int = 0) -> tuple[float, float]:
    """Percentile-bootstrap interval for any statistic of a 1-D sample."""
    arr = np.asarray(values, dtype=float).ravel()
    finite = arr[np.isfinite(arr)]
    if finite.size < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    draws = np.array([statistic(finite[rng.integers(0, finite.size, finite.size)])
                      for _ in range(n_bootstrap)])
    alpha = 100.0 * (1.0 - confidence) / 2.0
    lo, hi = np.percentile(draws, [alpha, 100.0 - alpha])
    return (float(lo), float(hi))


# ---------------------------------------------------------------------------------------
# binomial outputs: constraint violation probability
# ---------------------------------------------------------------------------------------

def wilson_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

        centre = (p + z^2/2n) / (1 + z^2/n)
        half   = z/(1 + z^2/n) * sqrt( p(1-p)/n + z^2/(4n^2) )

    Chosen over the normal (Wald) interval because Wald collapses to the single point 0
    when k = 0, which is the failure this function exists to prevent. Wilson stays inside
    [0, 1] and gives a sensible upper bound at zero counts.
    """
    if n <= 0:
        return (float("nan"), float("nan"))
    if not 0 <= k <= n:
        raise ValueError(f"k = {k} must lie in [0, n] with n = {n}")
    z = float(norm.ppf(0.5 + confidence / 2.0))
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z / denom) * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def clopper_pearson_interval(k: int, n: int, confidence: float = 0.95
                             ) -> tuple[float, float]:
    """Exact (conservative) binomial interval, as an independent check on Wilson.

    At k = 0 the upper limit is 1 - alpha^(1/n) - the exact form of the familiar
    "rule of three", 3/n.
    """
    if n <= 0:
        return (float("nan"), float("nan"))
    if not 0 <= k <= n:
        raise ValueError(f"k = {k} must lie in [0, n] with n = {n}")
    alpha = 1.0 - confidence
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return (lo, hi)


@dataclass(frozen=True)
class ViolationProbability:
    """P(constraint violated) from a finite sample, with its interval and a plain phrase."""

    name: str
    n_violations: int
    n_samples: int
    n_not_evaluable: int
    point: float
    wilson: tuple[float, float]
    clopper_pearson: tuple[float, float]
    confidence: float

    @property
    def phrase(self) -> str:
        """How this must be written in prose. Never 'zero'."""
        hi = self.wilson[1]
        pct = 100.0 * self.confidence
        if self.n_violations == 0:
            return (f"0 of {self.n_samples} draws violated it, i.e. below "
                    f"{hi * 100:.2f}% at {pct:g}% confidence - not zero")
        return (f"{self.point * 100:.2f}% "
                f"[{self.wilson[0] * 100:.2f}, {hi * 100:.2f}] at {pct:g}% confidence "
                f"({self.n_violations} of {self.n_samples})")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "n_violations": self.n_violations,
                "n_samples": self.n_samples, "n_not_evaluable": self.n_not_evaluable,
                "point": self.point, "wilson_lo": self.wilson[0],
                "wilson_hi": self.wilson[1],
                "clopper_pearson_lo": self.clopper_pearson[0],
                "clopper_pearson_hi": self.clopper_pearson[1],
                "confidence": self.confidence, "phrase": self.phrase}


def violation_probability(name: str, violated, *, not_evaluable=None,
                          confidence: float = 0.95) -> ViolationProbability:
    """P(violation) with intervals.

    `violated` is a boolean array over the sample. `not_evaluable` marks draws that
    produced no physics at all (a skipped-out or timed-out trajectory). Those are counted
    as VIOLATIONS - a design that does not complete an entry has not satisfied the
    constraint - and reported separately so the reader can see which kind of failure it
    was.
    """
    flags = np.asarray(violated, dtype=bool).ravel()
    bad = np.asarray(not_evaluable, dtype=bool).ravel() if not_evaluable is not None \
        else np.zeros_like(flags)
    if bad.shape != flags.shape:
        raise ValueError("violated and not_evaluable must have the same shape")
    combined = flags | bad
    n, k = int(combined.size), int(combined.sum())
    return ViolationProbability(
        name=name, n_violations=k, n_samples=n, n_not_evaluable=int(bad.sum()),
        point=k / n if n else float("nan"),
        wilson=wilson_interval(k, n, confidence),
        clopper_pearson=clopper_pearson_interval(k, n, confidence),
        confidence=confidence,
    )


# ---------------------------------------------------------------------------------------
# convergence
# ---------------------------------------------------------------------------------------

def convergence_table(values, checkpoints, statistics: dict[str, Callable[[np.ndarray], float]],
                      *, n_bootstrap: int = 400, confidence: float = 0.95,
                      seed: int = 0) -> list[dict[str, Any]]:
    """Each statistic recomputed on the first N draws, with its bootstrap half-width.

    The sample is used IN DRAW ORDER, which for a Latin Hypercube is already the
    unstratified order the sampler produced; the prefix of an LHS is not itself an LHS, so
    the early rows are ordinary Monte Carlo and the half-widths are, if anything,
    pessimistic. Stated rather than hidden, because the alternative - re-drawing a fresh
    LHS at every checkpoint - costs N_checkpoints times the budget.
    """
    arr = np.asarray(values, dtype=float).ravel()
    rows: list[dict[str, Any]] = []
    for n in checkpoints:
        n = int(n)
        if n < 2 or n > arr.size:
            continue
        prefix = arr[:n]
        row: dict[str, Any] = {"n": n, "n_finite": int(np.sum(np.isfinite(prefix)))}
        for label, fn in statistics.items():
            value = fn(prefix[np.isfinite(prefix)]) if row["n_finite"] else float("nan")
            lo, hi = bootstrap_ci(prefix, fn, n_bootstrap=n_bootstrap,
                                  confidence=confidence, seed=seed)
            row[label] = float(value)
            row[f"{label}__ci_lo"] = lo
            row[f"{label}__ci_hi"] = hi
            row[f"{label}__half_width"] = (hi - lo) / 2.0
            row[f"{label}__half_width_rel"] = (
                abs((hi - lo) / 2.0 / value) if value not in (0.0,) and np.isfinite(value)
                else float("nan"))
        rows.append(row)
    return rows


def converged(table: list[dict[str, Any]], label: str, tolerance_rel: float) -> dict[str, Any]:
    """Verdict on a convergence table: is the final relative half-width within tolerance?

    Returns the measured value rather than only a boolean, so a report can state the
    number it was judged on.
    """
    if not table:
        return {"label": label, "converged": False, "reason": "no checkpoints"}
    last = table[-1]
    measured = last.get(f"{label}__half_width_rel", float("nan"))
    return {"label": label, "n": last["n"], "value": last.get(label),
            "half_width_rel": measured, "tolerance_rel": tolerance_rel,
            "converged": bool(np.isfinite(measured) and measured <= tolerance_rel)}
