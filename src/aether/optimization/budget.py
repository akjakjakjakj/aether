"""The budgeted-evaluation wrapper: the ONLY way an optimiser reaches `evaluate_design`.

Conceptual anchor
-----------------
M5 will compare optimisers "under matched evaluation budgets" (spec sections 24, 46).
That comparison is only meaningful if every method is charged by the same meter. This
wrapper is that meter. It owns the call to the canonical evaluator, counts what it
costs, refuses to go over budget, and logs every candidate - so no optimiser can bypass
the evaluator, under-report its spending, or lose a failed design.

Budget accounting (A-OPT-3) - decided once, here:

  * Every DISTINCT design submitted costs exactly 1, whether it turns out feasible,
    infeasible or geometrically invalid. An invalid geometry costs almost no compute, but
    it still buys the optimiser information about where the valid region ends; letting
    it be free would let a method map the boundary for nothing.
  * A design this evaluator has ALREADY seen (same variable values to 12 significant
    digits) is answered from cache, is logged with `cache_hit = True`, and costs 0. It
    buys no new information, so it is not charged - but it is still counted and
    reported, because a method that keeps re-proposing old designs is wasting its
    iterations even if not its budget.
  * When a batch would overrun, only as many NEW designs as the remaining budget allows
    are evaluated (in submission order); the rest are dropped unevaluated and
    `BudgetExhausted` is raised. Every run therefore spends exactly `budget`
    evaluations, never budget + (population - 1).
"""

from __future__ import annotations

import math
import time
from concurrent.futures import Executor
from typing import Any

import numpy as np

from ..evaluate import evaluate_design
from ..utils.run import config_hash
from .design_space import DesignSpace
from .persistence import CandidateStore

METRIC_NAMES = (
    "peak_heat_flux_w_m2", "integrated_external_heat_j_m2", "peak_surface_temperature_k",
    "peak_bondline_temperature_k", "bondline_exposure_metric_k_s",
    "thermal_penetration_depth_m", "max_g", "max_dynamic_pressure_pa", "entry_duration_s",
    "time_of_peak_heating_s", "energy_balance_residual",
)
MARGIN_NAMES = (
    "max_g", "max_dynamic_pressure_pa", "peak_bondline_temperature_k",
    "peak_surface_temperature_k", "bluntness_ratio", "heatshield_mass_fraction",
)
DIAGNOSTIC_NAMES = (
    "bluntness_ratio", "heatshield_mass_fraction", "wetted_forebody_area_m2",
    "heat_load_fraction_above_86km", "bondline_peak_time_s", "thermal_window_end_s",
    "bondline_end_rate_k_s",
    # Fidelity 1 only (NaN at Fidelity 0): where THIS design's entry left the CFD Mach range,
    # and what the drag surface said at peak heating. Needed by the metric-gaming audit.
    "aero_heat_fraction_above_cfd_mach", "aero_heat_fraction_below_cfd_mach",
    "aero_mach_top_of_table", "aero_cd_at_peak_heating", "aero_mach_at_peak_heating",
)

NOT_EVALUABLE_VIOLATION = 10.0
"""Constraint violation assigned to a design with no physics result (invalid geometry,
trajectory that skipped out or timed out). Larger than any normalised margin violation
seen in practice, so such a design always ranks below an evaluated-but-infeasible one.
It carries no gradient; optimisers are expected to work in a box that is mostly valid."""

_NAN = float("nan")


class BudgetExhausted(RuntimeError):
    """Raised by `BudgetedEvaluator.evaluate` once the budget is spent."""


def evaluate_candidate(payload: tuple[dict[str, Any], str]) -> dict[str, Any]:
    """Worker entry point: one config in, one flat, picklable result row out.

    Top-level so it can cross a process boundary. It returns scalars only - shipping the
    full T(x, t) field back from every worker would cost more than the solve.
    """
    config, candidate_id = payload
    start = time.perf_counter()
    ev = evaluate_design(config, design_id=candidate_id)
    perf = ev.performance
    row: dict[str, Any] = {name: float(getattr(perf, name)) for name in METRIC_NAMES}
    for name in MARGIN_NAMES:
        row[f"margin__{name}"] = float(perf.constraint_margins.get(name, _NAN))
    for name in DIAGNOSTIC_NAMES:
        row[f"diag__{name}"] = float(ev.diagnostics.get(name, _NAN))
    violated = sorted(k for k, v in perf.constraint_margins.items() if v < 0.0)
    if perf.feasible:
        reason = ""
    elif perf.status != "OK":
        reason = perf.status
    else:
        reason = "constraint violated: " + ", ".join(violated)
    row.update({
        "feasible": bool(perf.feasible), "failure_reason": reason,
        "violated_constraints": violated, "termination": perf.termination,
        "status": perf.status, "fidelity": int(ev.fidelity),
        "wall_time_s": time.perf_counter() - start,
    })
    return row


def _round_sig(value: float, digits: int = 12) -> float:
    if value == 0.0 or not math.isfinite(value):
        return value
    return round(value, digits - 1 - int(math.floor(math.log10(abs(value)))))


class BudgetedEvaluator:
    """Charges, caches, parallelises and logs evaluations for one (method, seed) run."""

    def __init__(self, space: DesignSpace, budget: int, store: CandidateStore, *,
                 run_id: str, method: str, seed: int, executor: Executor | None = None):
        if budget < 1:
            raise ValueError("budget must be at least 1 evaluation")
        self.space, self.budget, self.store = space, int(budget), store
        self.run_id, self.method, self.seed = run_id, method, int(seed)
        self._executor = executor
        self._cache: dict[str, dict[str, Any]] = {}
        self.n_submitted = 0
        self.n_cache_hits = 0

    @property
    def used(self) -> int:
        """Budget spent == number of distinct designs evaluated."""
        return len(self._cache)

    @property
    def remaining(self) -> int:
        return self.budget - self.used

    def candidate_id(self, values: dict[str, float]) -> str:
        return "C-" + config_hash({k: _round_sig(float(v)) for k, v in values.items()})

    def evaluate(self, x_batch: np.ndarray, *, generation: int = 0,
                 parent_ids: list[list[str]] | None = None) -> list[dict[str, Any]]:
        """Evaluate a batch of ACTIVE-variable vectors, in order.

        Returns one row per submitted vector. Raises `BudgetExhausted` (after logging
        everything it did evaluate) if the batch could not be completed within budget.
        """
        x_batch = np.atleast_2d(np.asarray(x_batch, dtype=float))
        parent_ids = parent_ids or [[] for _ in range(len(x_batch))]
        values = [self.space.values(x) for x in x_batch]
        ids = [self.candidate_id(v) for v in values]

        new_order: list[str] = []
        for cid in ids:
            if cid not in self._cache and cid not in new_order:
                new_order.append(cid)
        affordable = new_order[: max(self.remaining, 0)]
        first_index = {cid: ids.index(cid) for cid in affordable}
        payloads = [(self.space.config_for(values[first_index[cid]]), cid)
                    for cid in affordable]
        mapper = map if self._executor is None else self._executor.map
        results = dict(zip(affordable, mapper(evaluate_candidate, payloads), strict=True))

        rows: list[dict[str, Any]] = []
        fresh: set[str] = set()
        overrun = False
        for cid, vals, parents in zip(ids, values, parent_ids, strict=True):
            if cid in results and cid not in fresh:
                fresh.add(cid)
                self._cache[cid] = results[cid]
                hit = False
            elif cid in self._cache:
                hit = True
                self.n_cache_hits += 1
            else:
                overrun = True  # not affordable: dropped unevaluated
                continue
            self.n_submitted += 1
            rows.append({
                "run_id": self.run_id, "method": self.method, "seed": self.seed,
                "eval_index": self.n_submitted, "budget_index": self.used,
                "generation": int(generation), "candidate_id": cid,
                "parent_ids": list(parents), "cache_hit": hit,
                **{f"x__{k}": v for k, v in vals.items()},
                **self._cache[cid],
            })
        self.store.append(rows)
        if overrun:
            raise BudgetExhausted(f"{self.method} seed {self.seed}: budget of "
                                  f"{self.budget} evaluations spent")
        return rows


def objective_matrix(rows: list[dict[str, Any]], objectives: tuple[str, ...]) -> np.ndarray:
    """(n, n_obj) objective values, NaN where no physics ran."""
    return np.array([[row[name] for name in objectives] for row in rows], dtype=float)


def constraint_violation(rows: list[dict[str, Any]]) -> np.ndarray:
    """Scalar violation per row: 0 == feasible, else the sum of normalised margin deficits.

    A design that produced no trustworthy physics gets `NOT_EVALUABLE_VIOLATION`.
    """
    out = np.zeros(len(rows))
    for i, row in enumerate(rows):
        if row["feasible"]:
            continue
        deficits = [max(0.0, -row[f"margin__{name}"]) for name in MARGIN_NAMES
                    if not math.isnan(row[f"margin__{name}"])]
        if row["status"] != "OK" or not deficits or sum(deficits) == 0.0:
            out[i] = NOT_EVALUABLE_VIOLATION
        else:
            out[i] = float(sum(deficits))
    return out
