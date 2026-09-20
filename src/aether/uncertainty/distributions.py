"""Distribution families for the M7 uncertain inputs, addressed by inverse CDF.

Conceptual anchor
-----------------
Everything here is a map from a number in [0, 1) to a value. That is deliberate: it is
what lets a Latin Hypercube, a Sobol' design and a plain Monte-Carlo sample all drive the
SAME declared distributions without any of them knowing what those distributions are, and
it is what makes common random numbers possible - two designs handed the same unit vector
see the same physical draw.

So there is exactly one required method, `ppf(u)`, and every family is defined by it.

Why a family list and not `scipy.stats` by name
-----------------------------------------------
An open door to `scipy.stats` would let a config ask for a distribution nobody has
argued for. The five families below cover what this project can actually defend:

    normal        a symmetric measurement/variability spread with a standard deviation
    lognormal     the same when the quantity is positive and multiplicative
    uniform       a BAND, not a spread - what a bounded-but-unknown quantity gets
    triangular    a band with a declared most-likely value
    discrete      a finite set of MODELS or states, each with a probability

`uniform` and `discrete` are the epistemic workhorses. A band read off two primaries that
disagree is not a standard deviation and must not be given one; calling it uniform says
"somewhere in here, no idea where", which is the honest content of the evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import lognorm, norm, triang


class Distribution:
    """Inverse-CDF interface. `ppf` maps [0, 1) to the support."""

    family: str = ""

    def ppf(self, u):  # pragma: no cover - interface
        raise NotImplementedError

    def describe(self) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    @property
    def is_degenerate(self) -> bool:
        """True if every draw is the same value, i.e. the input is switched off."""
        lo, hi = float(self.ppf(1e-9)), float(self.ppf(1.0 - 1e-9))
        return lo == hi


@dataclass(frozen=True)
class Normal(Distribution):
    mean: float
    std: float
    family: str = "normal"

    def __post_init__(self) -> None:
        if self.std < 0.0:
            raise ValueError(f"normal std must be non-negative, got {self.std}")

    def ppf(self, u):
        return norm.ppf(np.asarray(u, dtype=float), loc=self.mean, scale=self.std) \
            if self.std > 0.0 else np.full_like(np.asarray(u, dtype=float), self.mean)

    def describe(self) -> str:
        return f"N(mean={self.mean:g}, sd={self.std:g})"

    def to_dict(self) -> dict[str, Any]:
        return {"family": self.family, "mean": self.mean, "std": self.std}


@dataclass(frozen=True)
class LogNormal(Distribution):
    """Multiplicative spread: log(X) ~ N(log(median), sigma_log)."""

    median: float
    sigma_log: float
    family: str = "lognormal"

    def __post_init__(self) -> None:
        if self.median <= 0.0:
            raise ValueError("lognormal median must be positive")
        if self.sigma_log < 0.0:
            raise ValueError("lognormal sigma_log must be non-negative")

    def ppf(self, u):
        u = np.asarray(u, dtype=float)
        if self.sigma_log == 0.0:
            return np.full_like(u, self.median)
        return lognorm.ppf(u, s=self.sigma_log, scale=self.median)

    def describe(self) -> str:
        return f"logN(median={self.median:g}, sigma_log={self.sigma_log:g})"

    def to_dict(self) -> dict[str, Any]:
        return {"family": self.family, "median": self.median, "sigma_log": self.sigma_log}


@dataclass(frozen=True)
class Uniform(Distribution):
    """A BAND. Use this, not a normal, for anything bounded-but-unknown."""

    low: float
    high: float
    family: str = "uniform"

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(f"uniform needs low <= high, got [{self.low}, {self.high}]")

    def ppf(self, u):
        return self.low + np.asarray(u, dtype=float) * (self.high - self.low)

    def describe(self) -> str:
        return f"U[{self.low:g}, {self.high:g}]"

    def to_dict(self) -> dict[str, Any]:
        return {"family": self.family, "low": self.low, "high": self.high}


@dataclass(frozen=True)
class Triangular(Distribution):
    low: float
    mode: float
    high: float
    family: str = "triangular"

    def __post_init__(self) -> None:
        if not self.low <= self.mode <= self.high:
            raise ValueError("triangular needs low <= mode <= high, got "
                             f"[{self.low}, {self.mode}, {self.high}]")

    def ppf(self, u):
        u = np.asarray(u, dtype=float)
        span = self.high - self.low
        if span == 0.0:
            return np.full_like(u, self.low)
        return triang.ppf(u, c=(self.mode - self.low) / span, loc=self.low, scale=span)

    def describe(self) -> str:
        return f"Tri({self.low:g}, {self.mode:g}, {self.high:g})"

    def to_dict(self) -> dict[str, Any]:
        return {"family": self.family, "low": self.low, "mode": self.mode,
                "high": self.high}


@dataclass(frozen=True)
class Discrete(Distribution):
    """A finite set of states with probabilities. The model-form workhorse.

    `values` may be numbers or strings (a model NAME is a perfectly good uncertain
    quantity). `ppf` returns an INDEX into `values`, because the unit-cube interface has
    to return something numeric; `select` turns an index back into the state.
    """

    values: tuple[Any, ...]
    probabilities: tuple[float, ...]
    family: str = "discrete"

    def __post_init__(self) -> None:
        if len(self.values) != len(self.probabilities):
            raise ValueError("discrete: values and probabilities differ in length")
        if len(self.values) == 0:
            raise ValueError("discrete: needs at least one value")
        p = np.asarray(self.probabilities, dtype=float)
        if np.any(p < 0.0):
            raise ValueError("discrete: probabilities must be non-negative")
        if not np.isclose(p.sum(), 1.0, rtol=0.0, atol=1e-9):
            raise ValueError(f"discrete: probabilities sum to {p.sum():g}, not 1")

    @property
    def edges(self) -> np.ndarray:
        return np.cumsum(np.asarray(self.probabilities, dtype=float))

    def ppf(self, u):
        """Index of the selected state. `searchsorted` on the cumulative probabilities."""
        u = np.asarray(u, dtype=float)
        idx = np.searchsorted(self.edges, np.clip(u, 0.0, 1.0 - 1e-12), side="right")
        return np.clip(idx, 0, len(self.values) - 1).astype(float)

    def select(self, index: float) -> Any:
        return self.values[int(np.clip(round(float(index)), 0, len(self.values) - 1))]

    @property
    def is_degenerate(self) -> bool:
        return len(self.values) == 1 or max(self.probabilities) == 1.0

    def describe(self) -> str:
        return "{" + ", ".join(f"{v!r}:{p:g}" for v, p in
                               zip(self.values, self.probabilities, strict=True)) + "}"

    def to_dict(self) -> dict[str, Any]:
        return {"family": self.family, "values": list(self.values),
                "probabilities": list(self.probabilities)}


FAMILIES: dict[str, type[Distribution]] = {
    "normal": Normal,
    "lognormal": LogNormal,
    "uniform": Uniform,
    "triangular": Triangular,
    "discrete": Discrete,
}


def build_distribution(spec: dict[str, Any]) -> Distribution:
    """Build a distribution from its config mapping. Unknown keys are an error.

    Rejecting unknown keys matters more than it looks: `{family: normal, low: 0, high: 1}`
    would otherwise sample a standard normal and nobody would notice.
    """
    spec = dict(spec)
    family = str(spec.pop("family", "")).strip()
    if family not in FAMILIES:
        raise ValueError(f"unknown distribution family {family!r}; "
                         f"expected one of {sorted(FAMILIES)}")
    cls = FAMILIES[family]
    fields = {f for f in cls.__dataclass_fields__ if f != "family"}  # type: ignore[attr-defined]
    unknown = set(spec) - fields
    if unknown:
        raise ValueError(f"distribution family {family!r} got unknown parameters "
                         f"{sorted(unknown)}; it takes {sorted(fields)}")
    missing = fields - set(spec)
    if missing:
        raise ValueError(f"distribution family {family!r} is missing {sorted(missing)}")
    if family == "discrete":
        return Discrete(values=tuple(spec["values"]),
                        probabilities=tuple(float(p) for p in spec["probabilities"]))
    return cls(**{k: float(v) for k, v in spec.items()})  # type: ignore[arg-type]
