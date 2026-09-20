"""Unit-cube sample designs for M7: mixed, nested (aleatory/epistemic) and CRN.

Conceptual anchor
-----------------
Two questions need two sample shapes.

**"What does this design do in service?"** - one sample over every uncertain input at
once. Its output distribution is the honest MIXTURE of a real frequency (the day's
atmosphere) and a state of knowledge (which of two reports is right). That mixture is
reportable, and the report must say that is what it is.

**"How much of the spread is my ignorance rather than the world's?"** - a NESTED sample.
Fix the epistemic inputs at one of E states; inside it, draw A aleatory samples. Each
branch gives a complete output distribution; E of them give a BAND of distributions (a
p-box). The width of any one curve is variability, which no amount of study will remove.
The gap between the curves is ignorance, which study would. Collapsing them into one
number destroys exactly that distinction, which is why the default is nested.

Common random numbers
---------------------
The same A aleatory unit points are reused inside every epistemic branch, and - in the
robust optimiser - inside every candidate design. Two designs are then compared on the
SAME weather, so the difference between them is not confounded with sampling noise. This
is the shortcut that makes robust optimisation affordable at all, and it is verified
against full independent Monte Carlo rather than trusted (`robust.verify_shortcut`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..optimization.sampling import latin_hypercube

MIXED = "mixed"
NESTED = "nested"
MODES = (MIXED, NESTED)


@dataclass(frozen=True)
class DrawSet:
    """A sample design on the unit cube, with its aleatory/epistemic bookkeeping."""

    unit: np.ndarray
    """(n_samples, n_inputs) points in [0, 1)."""
    epistemic_index: np.ndarray
    """(n_samples,) which epistemic branch each row belongs to; all 0 in mixed mode."""
    aleatory_index: np.ndarray
    """(n_samples,) which shared aleatory draw each row uses."""
    mode: str
    seed: int
    n_epistemic_branches: int
    n_aleatory: int

    def __len__(self) -> int:
        return int(self.unit.shape[0])

    @property
    def n_inputs(self) -> int:
        return int(self.unit.shape[1])

    def branch(self, index: int) -> np.ndarray:
        """Row indices belonging to epistemic branch `index`."""
        return np.flatnonzero(self.epistemic_index == index)

    def to_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "seed": self.seed, "n_samples": len(self),
                "n_inputs": self.n_inputs,
                "n_epistemic_branches": self.n_epistemic_branches,
                "n_aleatory": self.n_aleatory}


def make_draws(n_inputs: int, aleatory_dims: tuple[int, ...],
               epistemic_dims: tuple[int, ...], *, mode: str, seed: int,
               n_aleatory: int, n_epistemic_branches: int = 1) -> DrawSet:
    """Build a `DrawSet`.

    mixed
        One Latin Hypercube of `n_aleatory` points over ALL inputs. The epistemic inputs
        are sampled from their declared distributions like everything else, so the result
        is the pooled mixture. `n_epistemic_branches` is ignored.
    nested
        `n_epistemic_branches` LHS points over the epistemic dimensions only; inside each,
        the SAME `n_aleatory` LHS points over the aleatory dimensions (common random
        numbers). Total rows = branches * n_aleatory.

    Every LHS is seeded from `seed`, with distinct offsets per block, so a run is
    reproducible from its seed alone.
    """
    if mode not in MODES:
        raise ValueError(f"unknown sampling mode {mode!r}, expected one of {MODES}")
    if n_aleatory < 1:
        raise ValueError("n_aleatory must be at least 1")
    overlap = set(aleatory_dims) & set(epistemic_dims)
    if overlap:
        raise ValueError(f"dimensions {sorted(overlap)} are both aleatory and epistemic")
    if sorted([*aleatory_dims, *epistemic_dims]) != list(range(n_inputs)):
        raise ValueError("aleatory_dims and epistemic_dims must partition range(n_inputs)")

    if mode == MIXED:
        unit = latin_hypercube(n_aleatory, n_inputs, seed)
        return DrawSet(unit=unit, epistemic_index=np.zeros(n_aleatory, dtype=int),
                       aleatory_index=np.arange(n_aleatory), mode=mode, seed=seed,
                       n_epistemic_branches=1, n_aleatory=n_aleatory)

    if n_epistemic_branches < 1:
        raise ValueError("nested mode needs at least one epistemic branch")
    n_e, n_a = len(epistemic_dims), len(aleatory_dims)
    # The shared aleatory block - identical in every branch. This IS the CRN.
    a_unit = latin_hypercube(n_aleatory, n_a, seed) if n_a else np.zeros((n_aleatory, 0))
    e_unit = (latin_hypercube(n_epistemic_branches, n_e, seed + 1_000_003) if n_e
              else np.zeros((n_epistemic_branches, 0)))

    rows, e_idx, a_idx = [], [], []
    for b in range(n_epistemic_branches):
        for a in range(n_aleatory):
            point = np.empty(n_inputs)
            for j, dim in enumerate(epistemic_dims):
                point[dim] = e_unit[b, j]
            for j, dim in enumerate(aleatory_dims):
                point[dim] = a_unit[a, j]
            rows.append(point)
            e_idx.append(b)
            a_idx.append(a)
    return DrawSet(unit=np.array(rows), epistemic_index=np.array(e_idx, dtype=int),
                   aleatory_index=np.array(a_idx, dtype=int), mode=mode, seed=seed,
                   n_epistemic_branches=n_epistemic_branches, n_aleatory=n_aleatory)


def common_random_numbers(n_inputs: int, n_samples: int, seed: int) -> np.ndarray:
    """The fixed inner sample every candidate design is judged on (robust optimisation).

    A Latin Hypercube over ALL inputs - aleatory and epistemic together - because a
    robust objective is a statement about the design's performance under everything that
    is not known, and a chance constraint has to count violations from both sources. The
    separated view is the propagation study's job, not the optimiser's.
    """
    return latin_hypercube(n_samples, n_inputs, seed)
