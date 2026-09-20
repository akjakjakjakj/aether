"""Variance-based attribution: which uncertain input drives which output (spec §27).

Conceptual anchor
-----------------
"The 95th-percentile bondline is 421 K" is a result. "And 78% of that spread is the
effective-nose-radius model form" is a DECISION: it says which piece of evidence to go and
buy next. Sobol' indices answer exactly that question -

    S_i   how much of the output variance disappears if input i were pinned down
    ST_i  the same, plus everything i does through interaction with the others

- and they are computed with the SAME estimator M4 uses, on the mean-centred output,
because an uncentred first-order estimator on an output with a 400 K mean and a 20 K
spread produces confidence intervals wider than [0, 1] (NR-16). That trap has been hit in
this repository once already; it is not re-derived here, it is imported.

An index on an epistemic input is not a variance share
-------------------------------------------------------
S_i for "which of two NASA reports is right" is not the fraction of real-world
variability that input explains - there is no real-world variability in it. It is the
fraction of the MODELLED spread that would vanish if the disagreement were resolved,
under the declared (uniform or discrete) reading of that disagreement. That is still the
useful number - it ranks what to go and measure - but it must be reported as a sensitivity
and not as a share of nature, so every row carries its input's `kind`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..optimization.sampling import saltelli_sample, sobol_indices
from .inputs import UncertaintyModel


@dataclass
class Attribution:
    """Sobol' indices for one design, over every uncertain input, for several outputs."""

    label: str
    n_base: int
    n_evaluations: int
    input_names: tuple[str, ...]
    input_kinds: tuple[str, ...]
    outputs: dict[str, Any]
    not_computed: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "n_base": self.n_base,
                "n_evaluations": self.n_evaluations,
                "inputs": [{"name": n, "kind": k} for n, k in
                           zip(self.input_names, self.input_kinds, strict=True)],
                "outputs": self.outputs, "not_computed": self.not_computed}

    def ranking(self, output: str) -> list[dict[str, Any]]:
        """Inputs sorted by total-order index, descending. [] if it was not computed."""
        block = self.outputs.get(output)
        if block is None:
            return []
        rows = [{"name": n, "kind": k, "first": f, "first_ci": fc,
                 "total": t, "total_ci": tc}
                for n, k, f, fc, t, tc in zip(
                    self.input_names, self.input_kinds, block["first"], block["first_ci"],
                    block["total"], block["total_ci"], strict=True)]
        return sorted(rows, key=lambda r: -r["total"])


def saltelli_unit_points(n_inputs: int, n_base: int, seed: int) -> np.ndarray:
    """The Saltelli design on the unit cube: (n_base * (n_inputs + 2), n_inputs) rows."""
    return saltelli_sample(n_base, n_inputs, seed)


def attribute(label: str, frame: pd.DataFrame, model: UncertaintyModel, *,
              n_base: int, outputs: tuple[str, ...], n_bootstrap: int = 500,
              confidence: float = 0.95, seed: int = 0) -> Attribution:
    """Sobol' indices from a frame of outputs evaluated on `saltelli_unit_points`.

    `frame` rows MUST be in the Saltelli design's own order (A block, B block, then the
    AB_i blocks). The caller guarantees that by submitting the design-vector matrix built
    from those unit points in order.

    Refusal, not repair
    -------------------
    A Saltelli design tolerates no missing points: dropping a row breaks the A/B/AB_i
    correspondence and biases every index by an unknown amount. If any output is
    non-finite for any row - a trajectory that skipped out under an extreme draw, say -
    that output is reported as NOT COMPUTED with the count, and no index is produced for
    it. The other outputs are unaffected.
    """
    k = model.n_inputs
    expected = n_base * (k + 2)
    if len(frame) != expected:
        raise ValueError(f"{label}: Saltelli design needs {expected} rows "
                         f"(n_base {n_base} x (k + 2) with k = {k}), got {len(frame)}")

    result = Attribution(label=label, n_base=n_base, n_evaluations=expected,
                         input_names=model.names,
                         input_kinds=tuple(i.kind for i in model.inputs),
                         outputs={}, not_computed={})
    for name in outputs:
        y = frame[name].to_numpy(dtype=float)
        bad = int(np.sum(~np.isfinite(y)))
        if bad:
            result.not_computed[name] = (
                f"{bad} of {expected} Saltelli points produced no finite value; indices "
                "would be biased by an unknown amount if those rows were dropped, so "
                "none is reported for this output")
            continue
        res = sobol_indices(y, k, n_bootstrap=n_bootstrap, confidence=confidence,
                            seed=seed)
        result.outputs[name] = {
            "first": res.first.tolist(),
            "first_ci": res.first_ci.tolist(),
            "total": res.total.tolist(),
            "total_ci": res.total_ci.tolist(),
            "variance": res.variance,
            "n_base": res.n_base,
        }
    return result
