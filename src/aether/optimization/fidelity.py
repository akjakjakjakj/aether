"""Adaptive-fidelity promotion policy: interface and hook (spec section 26).

Conceptual anchor
-----------------
With two evaluators - a cheap reduced-order one (Fidelity 0) and an expensive CFD-backed
one (Fidelity 1) - the question for each candidate is "is this design worth the expensive
look?". Section 26 names the four inputs of that decision; this module turns them into
one documented rule:

  predicted Pareto value   expected hypervolume gain of the design, from the surrogate
  uncertainty              how unsure the surrogate is about that design
  novelty                  distance from anything already evaluated
  cost                     how many expensive evaluations the run may still afford

Rule: promote iff the design is predicted to matter (it would extend the front, or the
agent asked for the higher fidelity) AND the cheap models cannot be trusted on it
(uncertain or novel) AND the expensive budget is not spent. A clearly poor design stays
at Fidelity 0; so does a promising design the surrogate is already sure about.

STATE AT M5: Fidelity 1 does not exist (CFD gate G4 is not PASS). `available` is (0,),
so every promotion is recorded as REQUESTED and NOT GRANTED, and the candidate is
evaluated at Fidelity 0. The policy is exercised so its plumbing is tested; nothing it
produces at M5 is evidence about adaptive fidelity. M6 supplies Fidelity 1 and the
thresholds below must be set then, against real cost data - they are placeholders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from ..surrogate.model import DesignSurrogate, unit_inputs
from .design_space import DesignSpace
from .pareto import hypervolume_2d, normalise

UNAVAILABLE_REASON = "fidelity 1 unavailable: CFD gate G4 not PASS, no CFD-backed evaluator"


@dataclass(frozen=True)
class FidelityDecision:
    candidate_id: str
    agent_requested_fidelity: int
    predicted_hv_gain: float
    uncertainty: float
    novelty: float
    extrapolated: bool
    policy_fidelity: int
    granted_fidelity: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PromotionPolicy:
    """Decides, per candidate, which fidelity to evaluate at. Stateful only in its count
    of expensive evaluations requested so far (the cost term)."""

    def __init__(self, settings: dict[str, Any], *, budget: int,
                 available: tuple[int, ...] = (0,)):
        self.min_hv_gain = float(settings["min_predicted_hv_gain"])
        self.min_uncertainty = float(settings["min_uncertainty"])
        self.min_novelty = float(settings["min_novelty"])
        self.max_high = int(float(settings["max_high_fidelity_fraction"]) * budget)
        self.available = tuple(available)
        self.n_requested = 0
        self.n_granted = 0

    def decide_batch(self, x_batch: np.ndarray, candidate_ids: list[str],
                     agent_requests: list[int], rows: list[dict[str, Any]],
                     surrogate: DesignSurrogate | None, space: DesignSpace,
                     objectives: tuple[str, ...], hv_cfg: dict[str, Any]
                     ) -> list[FidelityDecision]:
        x_unit = space.to_unit(np.atleast_2d(x_batch))
        n = len(x_unit)
        seen = unit_inputs([row for row in rows if not row["cache_hit"]], space)
        novelty = (np.min(np.linalg.norm(x_unit[:, None, :] - seen[None, :, :], axis=2),
                          axis=1) if len(seen) else np.full(n, np.inf))
        gain, sigma = np.full(n, np.nan), np.full(n, np.nan)
        outside = np.ones(n, dtype=bool)
        if surrogate is not None and surrogate.fitted:
            ideal = np.array([hv_cfg["ideal_point"][name] for name in objectives], dtype=float)
            ref = np.array([hv_cfg["reference_point"][name] for name in objectives],
                           dtype=float)
            pred = surrogate.predict_objectives(x_unit, on_extrapolation="flag")
            centre = normalise(np.column_stack([pred[name].central for name in objectives]),
                               ideal, ref)
            feasible = [row for row in rows if row["feasible"]]
            front = (normalise(np.array([[row[name] for name in objectives]
                                         for row in feasible], dtype=float), ideal, ref)
                     if feasible else np.empty((0, 2)))
            base = hypervolume_2d(front, np.ones(2))
            p_feasible = surrogate.probability_feasible(x_unit)
            for i in range(n):
                with_point = hypervolume_2d(np.vstack([front, centre[i]]), np.ones(2))
                gain[i] = (with_point - base) * p_feasible[i]
            # uncertainty: largest predictive std over the objectives, in units of that
            # objective's spread over the training data (both in the modelled space)
            spreads = []
            for name in objectives:
                model = surrogate.objective_models[name]
                train = model.forward(np.array([row[name] for row in rows
                                                if row["status"] == "OK"]))
                spreads.append(pred[name].std / max(float(np.std(train)), 1e-12))
            sigma = np.max(np.array(spreads), axis=0)
            outside = pred[objectives[0]].extrapolated

        decisions = []
        for i in range(n):
            matters = (gain[i] >= self.min_hv_gain) or agent_requests[i] >= 1
            untrusted = (bool(outside[i]) or sigma[i] >= self.min_uncertainty
                         or novelty[i] >= self.min_novelty)
            affordable = self.n_requested < self.max_high
            if surrogate is None or not surrogate.fitted:
                wanted, reason = 0, "no surrogate yet: not enough evaluated designs"
            elif matters and untrusted and affordable:
                wanted, reason = 1, "predicted to matter and cheap models untrusted here"
            elif matters and untrusted:
                wanted, reason = 0, "would promote, but the high-fidelity budget is spent"
            elif not matters:
                wanted, reason = 0, "predicted hypervolume gain below threshold"
            else:
                wanted, reason = 0, "surrogate already confident and design not novel"
            granted = wanted if wanted in self.available else 0
            if wanted >= 1:
                self.n_requested += 1
                if granted >= 1:
                    self.n_granted += 1
                else:
                    reason += f"; NOT GRANTED - {UNAVAILABLE_REASON}"
            decisions.append(FidelityDecision(
                candidate_id=candidate_ids[i], agent_requested_fidelity=int(agent_requests[i]),
                predicted_hv_gain=float(gain[i]), uncertainty=float(sigma[i]),
                novelty=float(novelty[i]), extrapolated=bool(outside[i]),
                policy_fidelity=int(wanted), granted_fidelity=int(granted), reason=reason))
        return decisions
