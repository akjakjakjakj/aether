"""`UncertainDesignSpace`: one uncertainty draw becomes one more coordinate of the design.

Conceptual anchor
-----------------
Spec section 19 says no study may reach the physics except through `evaluate_design`, and
M4 added a second rule on top: nothing reaches `evaluate_design` except through
`BudgetedEvaluator`, which is the meter every method is charged by. M7 has to obey both
while evaluating the SAME design under many different atmospheres.

The trick is to stop thinking of the uncertainty draw as something that happens outside
the design space and make it a coordinate INSIDE it. A `DesignSpace` already knows how to
turn a vector into an evaluator config; this subclass turns the vector

    (design variables..., draw index)

into that same config with draw `index`'s perturbations applied. Everything then falls out
for free and nothing in `budget.py`, `persistence.py` or `evaluate.py` had to change:

  * each (design, draw) pair gets its own candidate ID, so all of them are logged;
  * the budget meter charges one evaluation per pair, which is what one pair costs;
  * common random numbers become free CACHE HITS - an optimiser that re-proposes a design
    pays nothing to re-test it on the same weather, and the log says `cache_hit` so the
    saving is visible rather than assumed;
  * the draw index is written into the evaluated config at `uncertainty.draw_index`, so
    every config snapshot says which draw produced it. `evaluate_design` ignores the key.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from ..optimization.design_space import DesignSpace, DesignVariable
from .inputs import UncertaintyModel

UQ_DRAW = "_uq_draw"
"""Name of the synthetic variable that carries the uncertainty draw index."""

UQ_DRAW_PATH = "uncertainty.draw_index"


@dataclass(frozen=True)
class UncertainDesignSpace(DesignSpace):
    """A `DesignSpace` whose last active coordinate selects a precomputed draw."""

    model: UncertaintyModel | None = None
    draws: tuple[dict[str, Any], ...] = ()
    """Physical draw values, keyed by input name - one entry per uncertainty sample."""
    unit_points: tuple[tuple[float, ...], ...] = ()
    """The unit-cube point behind each draw, kept so a run can be reproduced exactly."""

    @property
    def n_draws(self) -> int:
        return len(self.draws)

    def config_for(self, values: dict[str, float]) -> dict[str, Any]:
        cfg = super().config_for(values)
        if self.model is None or not self.draws:
            return cfg
        index = int(round(float(values[UQ_DRAW])))
        if not 0 <= index < len(self.draws):
            raise IndexError(f"uncertainty draw index {index} is outside "
                             f"[0, {len(self.draws) - 1}]")
        for item in self.model.inputs:
            if item.name in self.draws[index]:
                item.patch(cfg, self.draws[index][item.name])
        return cfg

    def design_vectors(self, x_design: np.ndarray, draw_indices) -> np.ndarray:
        """Cartesian product of design vectors and draw indices, as ACTIVE vectors.

        Rows run draw-fastest, so a block of `len(draw_indices)` consecutive rows is one
        design's whole inner sample - which is what the propagation and robust code slice
        on. The design columns come first, in this space's active order, with the draw
        index last.
        """
        x_design = np.atleast_2d(np.asarray(x_design, dtype=float))
        draws = np.asarray(draw_indices, dtype=float).ravel()
        n_design_cols = self.n_active - 1
        if x_design.shape[1] != n_design_cols:
            raise ValueError(f"expected {n_design_cols} design columns, "
                             f"got {x_design.shape[1]}")
        tiled = np.repeat(x_design, draws.size, axis=0)
        column = np.tile(draws, x_design.shape[0])[:, None]
        return np.hstack([tiled, column])


def make_uncertain_space(space: DesignSpace, model: UncertaintyModel,
                         unit_points: np.ndarray) -> UncertainDesignSpace:
    """Add the draw coordinate to `space` and precompute every draw's physical values.

    The draw variable is given role `given` - it is not a design variable and no optimiser
    is ever allowed to choose it. It is placed LAST in both the variable tuple and the
    active list so that a design vector is simply the first `n - 1` columns.
    """
    unit_points = np.atleast_2d(np.asarray(unit_points, dtype=float))
    if unit_points.shape[1] != model.n_inputs:
        raise ValueError(f"unit points have {unit_points.shape[1]} columns but the "
                         f"uncertainty model declares {model.n_inputs} inputs")
    if UQ_DRAW in {v.name for v in space.variables}:
        raise ValueError(f"'{UQ_DRAW}' is already a variable of this design space")
    n = unit_points.shape[0]
    draw_var = DesignVariable(
        name=UQ_DRAW, kind="direct", path=UQ_DRAW_PATH, units="index", role="given",
        lower=0.0, upper=float(max(n - 1, 1)), reference=0.0)
    draws = tuple(model.draw(point) for point in unit_points)
    return UncertainDesignSpace(
        variables=(*space.variables, draw_var),
        active=(*space.active, UQ_DRAW),
        base_config=space.base_config,
        model=model,
        draws=draws,
        unit_points=tuple(tuple(float(v) for v in row) for row in unit_points),
    )


def design_only(space: UncertainDesignSpace) -> DesignSpace:
    """The same space without the draw coordinate - what an optimiser searches in."""
    return replace(DesignSpace(variables=tuple(v for v in space.variables
                                               if v.name != UQ_DRAW),
                               active=tuple(n for n in space.active if n != UQ_DRAW),
                               base_config=space.base_config))
