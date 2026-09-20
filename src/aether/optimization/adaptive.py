"""M6: adaptive-fidelity optimisation (spec section 26, hypothesis H2).

Conceptual anchor
-----------------
Every design is scored by `evaluate_design`, which takes its drag from a Gaussian-process
surface fitted through CFD cases. That surface is cheap and imperfect. The expensive thing
the project can buy is ONE MORE CFD CASE, which makes the surface locally better - for the
design that triggered it and for every later design near it. M6 asks who should get those
cases.

Two fidelities, as M6 uses the words (A-AF-1):

  F0   `evaluate_design` with the arm's CURRENT drag surface (~0.2 s).
  F1   a real OpenFOAM case for the candidate's forebody shape at the Mach number(s) that
       matter, through M3's design-point runner unchanged (shock-clearance check, first-order
       start, M2's force-convergence criterion, domain retry, patience pass). A usable case is
       ADDED to the arm's training set, the surface is refitted, and the candidate is
       re-evaluated through `evaluate_design`. A case that fails the criterion is kept,
       logged, costs a call, and yields no training point.

(The evaluator's own `fidelity` column labels the AERO MODEL - 1 for any CFD-derived surface -
and is 1 on every row of an M6 run. Promotion is recorded in `eval_kind` and the promotion log.)

The pieces
----------
  CfdRequest / CfdOutcome   one (Mach, forebody shape) case and what came back
  F1 backends               `OpenFoamF1Backend` (real) and `AnalyticF1Backend` (a known "true"
                            drag function: tests and labelled dry runs only)
  CfdCaseStore              run-level: each distinct case is RUN once, at most
                            `max_concurrent` serial solvers side by side
  CfdLedger                 per (arm, seed): each distinct case is CHARGED once; a failed case
                            still costs a call; a repeat of a case this arm already paid for is
                            free; a case another arm already ran is charged but not re-run
  ArmSurface                per (arm, seed): versioned copies of the drag surface; the hull
                            grows when a promotion lands outside it
  TwoFidelityEvaluator      the budget meter (`BudgetedEvaluator`) with a surface that can
                            change under it: evaluations and CFD calls are counted separately
                            and exactly
  PromotionController       decides, after every batch, which candidates get CFD. One
                            controller, five strategies - so the arms differ ONLY in who is
                            promoted, never in how a promotion is executed or charged

The section-26 policy (strategy `adaptive`)
-------------------------------------------
For each shortlisted candidate the surface's own error bar is pushed THROUGH the canonical
evaluator: the design is evaluated at z_gp = -1 and +1 (the M3 uncertainty hook), which gives
every objective and every constraint margin as a linear function of the surface error z. From
that, with z ~ N(0,1) on a fixed quantile grid (no random numbers):

  (a) value        P(feasible AND non-dominated against the arm's believed front), and the
                   expected hypervolume gain
  (b) uncertainty  half-range of the objectives over z = -1..+1, normalised by the
                   hypervolume rectangle - C_D uncertainty expressed as objective uncertainty
  (c) novelty      distance from the nearest CFD training shape (unit shape space); a shape
                   OUTSIDE the training hull has novelty 1 by definition
  (d) cost         share of the arm's remaining CFD budget the promotion would consume

  score = w_v*value + w_u*min(unc/scale,1) + w_n*min(nov/scale,1) + w_a*agent_request - w_c*cost

Promote iff the design MATTERS (value >= gate, or the LLM agent asked for fidelity 1) AND the
cheap model is UNTRUSTED there (outside the hull, or uncertainty >= gate, or novelty >= gate)
AND it is affordable AND score >= min_score. A clearly poor candidate stays at F0; so does a
promising one the surface is already sure about.

Out-of-hull is not a dead end. `evaluate_design` refuses a shape outside the CFD hull (A-AERO-1),
so such a design has no F0 value at all. The policy looks at it with `on_extrapolation: flag`
(a labelled guess, allowed because it is about to BUY the evaluation, A-AI-4), and if it looks
promising promotes it at BOTH ends of the Mach range - the only way a new shape enters the 4-D
hull - which costs two CFD calls. After the refit the design is evaluable, and so is everything
between it and the old hull.

The probes cost `evaluate_design` calls but return no new design, only the sensitivity of an
already-submitted one to the surface's error bar. They are counted and capped, reported per
arm, never enter a hypervolume, and are NOT charged to the search budget (A-AF-5).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd
from scipy.stats import norm, qmc

from ..aerodynamics.cfd_surface import (
    SHAPE_INPUTS,
    CfdDragSurface,
    GateNotPassedError,
    gate_g4_status,
)
from .budget import MARGIN_NAMES, BudgetedEvaluator, BudgetExhausted, evaluate_candidate
from .design_space import DesignSpace
from .fidelity import FidelityDecision
from .pareto import hypervolume_2d, normalise, pareto_front
from .persistence import CandidateStore

HULL_REJECT_PREFIX = "aero surface extrapolation"
STRATEGIES = ("adaptive", "random", "greedy", "upfront", "none")
N_Z_QUANTILES = 64
_Z_GRID = norm.ppf((np.arange(N_Z_QUANTILES) + 0.5) / N_Z_QUANTILES)


class CfdBudgetExhausted(RuntimeError):
    """The arm has no CFD calls left."""


# ---------------------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------------------
def require_f1_gate(surface_meta: dict[str, Any], allow_provisional: bool) -> dict[str, Any]:
    """Spec section 17: no CFD in an optimisation loop until gate G4 is PASS.

    Returns the gate record that goes into every M6 artefact. Raises `GateNotPassedError`
    unless BOTH the surface was built under a PASS gate and the gate reads PASS now - or the
    config carries `allow_provisional: true`, which exists for smoke tests only and labels
    the run."""
    now = gate_g4_status()
    at_build = str(surface_meta.get("gate_G4_status_at_build", "UNKNOWN"))
    record = {"gate_G4_status_at_build": at_build, "gate_G4_status_now": now["status"],
              "gate_source": now["source"], "allow_provisional": bool(allow_provisional),
              "provisional": at_build != "PASS" or now["status"] != "PASS"}
    if record["provisional"] and not allow_provisional:
        raise GateNotPassedError(
            f"M6 Fidelity 1 refused: gate G4 was {at_build} when the drag surface was built "
            f"and is {now['status']} now. Spec section 17 forbids CFD data in the optimisation "
            "loop until G4 is PASS. `allow_provisional: true` exists for smoke tests only.")
    return record


# ---------------------------------------------------------------------------------------
# CFD requests, outcomes, backends
# ---------------------------------------------------------------------------------------
def _sig(value: float, digits: int = 6) -> float:
    return float(f"{float(value):.{digits}g}")


@dataclass(frozen=True)
class CfdRequest:
    """One CFD case: a Mach number and a forebody shape. Diameter is free (scale invariance,
    checked at M3), so it is not part of the identity of a case."""

    mach: float
    bluntness_ratio: float
    cone_half_angle_deg: float
    shoulder_ratio: float

    @classmethod
    def of(cls, mach: float, shape: dict[str, float]) -> CfdRequest:
        return cls(_sig(mach), *(_sig(shape[k]) for k in SHAPE_INPUTS))

    @property
    def shape(self) -> dict[str, float]:
        return {k: getattr(self, k) for k in SHAPE_INPUTS}

    @property
    def key(self) -> str:
        return (f"M{self.mach:g}_b{self.bluntness_ratio:g}_c{self.cone_half_angle_deg:g}"
                f"_s{self.shoulder_ratio:g}")

    @property
    def point_id(self) -> str:
        return "af" + hashlib.sha1(self.key.encode()).hexdigest()[:10]


@dataclass
class CfdOutcome:
    key: str
    point_id: str
    mach: float
    bluntness_ratio: float
    cone_half_angle_deg: float
    shoulder_ratio: float
    usable: bool
    cd_fore: float
    verdict: str
    reasons: str
    attempts: int
    wall_time_s: float
    backend: str
    source: str = "run"            # 'run' | 'imported:<run_id>'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _outcome(request: CfdRequest, *, usable: bool, cd_fore: float, verdict: str, reasons: str,
             attempts: int, wall_time_s: float, backend: str) -> CfdOutcome:
    return CfdOutcome(request.key, request.point_id, request.mach, request.bluntness_ratio,
                      request.cone_half_angle_deg, request.shoulder_ratio, bool(usable),
                      float(cd_fore), verdict, reasons, int(attempts), float(wall_time_s),
                      backend)


class F1Backend(Protocol):
    name: str
    fingerprint: str

    def run(self, request: CfdRequest) -> CfdOutcome: ...


class AnalyticF1Backend:
    """A FAKE Fidelity 1: a known analytic 'true' drag function, optional declared failures.

    For tests and for labelled dry runs of the pipeline. Nothing it produces is evidence."""

    def __init__(self, cd_fore: Callable[[float, dict[str, float]], float], *,
                 fails: Callable[[CfdRequest], bool] | None = None, label: str = "analytic"):
        self._cd, self._fails = cd_fore, fails
        self.name = f"FAKE:{label}"
        self.fingerprint = self.name
        self.calls: list[str] = []
        self._lock = threading.Lock()

    def run(self, request: CfdRequest) -> CfdOutcome:
        with self._lock:
            self.calls.append(request.key)
        if self._fails is not None and self._fails(request):
            return _outcome(request, usable=False, cd_fore=float("nan"), verdict="REJECTED",
                            reasons="force criterion not met (declared fake failure)",
                            attempts=1, wall_time_s=0.0, backend=self.name)
        return _outcome(request, usable=True, cd_fore=self._cd(request.mach, request.shape),
                        verdict="USABLE", reasons="", attempts=1, wall_time_s=0.0,
                        backend=self.name)


class OpenFoamF1Backend:
    """The real Fidelity 1: M3's `run_design_point`, unchanged, on the surface's mesh level."""

    def __init__(self, dp_cfg: dict[str, Any], run_dir: Path, generated_root: Path,
                 level: str):
        from ..cfd import design_points as dp  # lazy: needs the CFD stack
        from ..utils.run import REPO_ROOT, config_hash, load_config

        self._dp, self.dp_cfg, self.level = dp, dp_cfg, level
        self.val_cfg = load_config(REPO_ROOT / dp_cfg["inherit"]["cfd_validation_config"])
        self.run_dir, self.generated_root = Path(run_dir), Path(generated_root)
        self.name = "openfoam"
        self.fingerprint = (f"openfoam:{level}:{config_hash(dp_cfg)}:"
                            f"{config_hash(self.val_cfg)}")
        threads = str(int(dp_cfg["execution"]["threads_per_case"]))
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS"):
            os.environ[var] = threads                  # inherited by every solver child

    def run(self, request: CfdRequest) -> CfdOutcome:
        dp = self._dp
        point = dp.DesignPoint(request.point_id, "promotion", "train", request.mach,
                               diameter_m=float(self.dp_cfg["fixed"]["diameter_m"]),
                               label="m6", **request.shape)
        start = time.perf_counter()
        try:
            row = dp.run_design_point(point, self.dp_cfg, self.val_cfg, self.run_dir,
                                      self.generated_root, self.level)
        except Exception as exc:                       # noqa: BLE001 - the failure IS the result
            return _outcome(request, usable=False, cd_fore=float("nan"),
                            verdict="RUNNER_ERROR", reasons=f"{type(exc).__name__}: {exc}",
                            attempts=0, wall_time_s=time.perf_counter() - start,
                            backend=self.name)
        attempts = row.pop("_attempt_rows", [])
        self.run_dir.mkdir(parents=True, exist_ok=True)
        with open(self.run_dir / "attempts.jsonl", "a") as fh:
            fh.writelines(json.dumps({"point_id": request.point_id, **a}, default=str) + "\n"
                          for a in attempts)
        usable = row.get("verdict") == dp.USABLE
        cd = float(row.get("cd_fore", float("nan"))) if usable else float("nan")
        wall = float(sum(float(a.get("total_wall_time_s") or 0.0) for a in attempts))
        return _outcome(request, usable=usable and math.isfinite(cd), cd_fore=cd,
                        verdict=str(row.get("verdict")), reasons=str(row.get("reasons") or ""),
                        attempts=int(row.get("attempts") or len(attempts)),
                        wall_time_s=wall or time.perf_counter() - start, backend=self.name)


class CfdCaseStore:
    """Run-level store: every distinct case is RUN at most once, `max_concurrent` at a time.

    Charging is the ledger's business, not the store's: two arms that ask for the same case
    are each charged, and the solver runs once."""

    COLUMNS = ("key", "point_id", "mach", *SHAPE_INPUTS, "usable", "cd_fore", "verdict",
               "reasons", "attempts", "wall_time_s", "backend", "source", "fingerprint",
               "purpose")

    def __init__(self, csv_path: Path, backend: F1Backend, max_concurrent: int):
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        self.csv_path, self.backend = Path(csv_path), backend
        self.max_concurrent = int(max_concurrent)
        self._pool = ThreadPoolExecutor(max_workers=self.max_concurrent,
                                        thread_name_prefix="cfd")
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()
        self._running, self.peak_concurrency, self.n_run = 0, 0, 0
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    def import_from(self, other_csv: Path, run_label: str) -> int:
        """Reuse finished cases of an earlier run (e.g. one the source guard aborted). Only
        cases produced by the SAME backend, mesh level and CFD configs are taken."""
        frame = pd.read_csv(other_csv)
        taken = 0
        for rec in frame.to_dict("records"):
            if rec.get("fingerprint") != self.backend.fingerprint or rec["key"] in self._futures:
                continue
            outcome = CfdOutcome(**{k: rec[k] for k in CfdOutcome.__dataclass_fields__
                                    if k != "source"}, source=f"imported:{run_label}")
            outcome.reasons = "" if pd.isna(outcome.reasons) else str(outcome.reasons)
            done: Future = Future()
            done.set_result(outcome)
            self._futures[outcome.key] = done
            self._write(outcome, str(rec.get("purpose", "promotion")))
            taken += 1
        return taken

    def _write(self, outcome: CfdOutcome, purpose: str) -> None:
        row = {**outcome.to_dict(), "fingerprint": self.backend.fingerprint,
               "purpose": purpose}
        with self._lock:
            new = not self.csv_path.exists()
            pd.DataFrame([row], columns=list(self.COLUMNS)).to_csv(
                self.csv_path, mode="a", header=new, index=False)

    def _run(self, request: CfdRequest, purpose: str) -> CfdOutcome:
        with self._lock:
            self._running += 1
            self.peak_concurrency = max(self.peak_concurrency, self._running)
        try:
            outcome = self.backend.run(request)
        finally:
            with self._lock:
                self._running -= 1
                self.n_run += 1
        self._write(outcome, purpose)
        return outcome

    def submit(self, request: CfdRequest, purpose: str = "promotion") -> Future:
        with self._lock:
            future = self._futures.get(request.key)
            if future is None:
                future = self._pool.submit(self._run, request, purpose)
                self._futures[request.key] = future
        return future

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True)


class CfdLedger:
    """CFD-call accounting for ONE (arm, seed). Exact by construction:

      * every distinct case this arm asks for costs 1 - usable or not;
      * a case this arm has already paid for is free and is never re-run;
      * nothing can be charged beyond `budget` (`CfdBudgetExhausted`).
    """

    def __init__(self, budget: int, arm: str, seed: int):
        if budget < 0:
            raise ValueError("CFD budget cannot be negative")
        self.budget, self.arm, self.seed = int(budget), arm, int(seed)
        self.records: list[dict[str, Any]] = []
        self._keys: set[str] = set()
        self.n_repeat_requests = 0

    @property
    def used(self) -> int:
        return len(self._keys)

    @property
    def remaining(self) -> int:
        return self.budget - self.used

    def has_paid(self, request: CfdRequest) -> bool:
        return request.key in self._keys

    def charge(self, request: CfdRequest, *, trigger: str, candidate_id: str,
               evaluations_used: int) -> bool:
        """True if a call was charged, False if this arm had already paid for the case."""
        if request.key in self._keys:
            self.n_repeat_requests += 1
            return False
        if self.remaining < 1:
            raise CfdBudgetExhausted(f"{self.arm} seed {self.seed}: CFD budget of "
                                     f"{self.budget} calls spent")
        self._keys.add(request.key)
        self.records.append({"arm": self.arm, "seed": self.seed, "call_index": self.used,
                             "key": request.key, "point_id": request.point_id,
                             "mach": request.mach, **request.shape, "trigger": trigger,
                             "candidate_id": candidate_id,
                             "evaluations_used": int(evaluations_used),
                             "usable": None, "cd_fore": None, "verdict": None,
                             "wall_time_s": None, "case_source": None})
        return True

    def settle(self, outcome: CfdOutcome) -> None:
        for rec in self.records:
            if rec["key"] == outcome.key and rec["usable"] is None:
                rec.update(usable=bool(outcome.usable), cd_fore=outcome.cd_fore,
                           verdict=outcome.verdict, wall_time_s=outcome.wall_time_s,
                           case_source=outcome.source)


# ---------------------------------------------------------------------------------------
# The arm's surface
# ---------------------------------------------------------------------------------------
class ArmSurface:
    """Versioned drag surface of one (arm, seed). Version 0 is the shared starting surface,
    rebuilt bit-for-bit (pinned kernel). Every absorbed batch of usable CFD points writes a
    NEW version directory, so workers never see a half-written surface and every belief in
    the candidate log can be traced to the exact training set behind it."""

    def __init__(self, root: Path, base: CfdDragSurface, *, arm: str, seed: int):
        self.root, self.arm, self.seed = Path(root), arm, int(seed)
        self.version = 0
        self.base_hash = base.meta["training_hash"]
        self.history: list[dict[str, Any]] = []
        self.surface = CfdDragSurface(
            base.table, {**base.meta, "adaptive_arm": arm, "adaptive_seed": int(seed),
                         "adaptive_version": 0, "adaptive_base_hash": self.base_hash},
            theta=np.array(base.meta["kernel_theta"], dtype=float))
        self._save()
        rng = self.surface.meta["input_ranges"]
        self._shape_lo = np.array([rng[k][0] for k in SHAPE_INPUTS], dtype=float)
        self._shape_hi = np.array([rng[k][1] for k in SHAPE_INPUTS], dtype=float)

    # -- persistence -------------------------------------------------------------------
    @property
    def directory(self) -> Path:
        return self.root / f"v{self.version:03d}"

    def _save(self) -> None:
        self.surface.save(self.directory)
        self.history.append({"arm": self.arm, "seed": self.seed, "version": self.version,
                             "n_train": int(len(self.surface.table)),
                             "training_hash": self.surface.meta["training_hash"],
                             "directory": str(self.directory)})

    @property
    def training_hash(self) -> str:
        return str(self.surface.meta["training_hash"])

    # -- geometry of what the surface knows --------------------------------------------
    def unit_shape(self, shape: dict[str, float]) -> np.ndarray:
        vec = np.array([shape[k] for k in SHAPE_INPUTS], dtype=float)
        return (vec - self._shape_lo) / (self._shape_hi - self._shape_lo)

    def mach_nodes(self) -> np.ndarray:
        return np.exp(np.linspace(np.log(self.surface.mach_min), np.log(self.surface.mach_max),
                                  48))

    def in_hull(self, shape: dict[str, float]) -> bool:
        pred = self.surface.predict_fore(self.mach_nodes(), shape, on_extrapolation="flag")
        return not bool(np.any(pred.extrapolated))

    def novelty(self, shape: dict[str, float]) -> float:
        """Unit-shape-space distance to the nearest CFD training shape."""
        train = self.surface.table[list(SHAPE_INPUTS)].to_numpy(dtype=float)
        unit = (train - self._shape_lo) / (self._shape_hi - self._shape_lo)
        return float(np.min(np.linalg.norm(unit - self.unit_shape(shape), axis=1)))

    def sigma(self, shape: dict[str, float], machs: np.ndarray) -> np.ndarray:
        """Inflated GP std of C_D,fore at `machs` (clamped into the CFD Mach range)."""
        machs = np.clip(np.asarray(machs, dtype=float), self.surface.mach_min,
                        self.surface.mach_max)
        pred = self.surface.predict_fore(machs, shape, on_extrapolation="flag")
        return pred.std * float(self.surface.meta.get("sigma_inflation", 1.0))

    def separation(self, request: CfdRequest) -> float:
        """Unit 4-D distance from a requested case to the nearest training point."""
        x = self.surface.unit(np.array([request.mach]),
                              np.array([[request.shape[k] for k in SHAPE_INPUTS]]))
        train = self.surface.unit(self.surface.table["mach"],
                                  self.surface.table[list(SHAPE_INPUTS)].to_numpy())
        return float(np.min(np.linalg.norm(train - x, axis=1)))

    # -- learning ------------------------------------------------------------------------
    def absorb(self, outcomes: list[CfdOutcome]) -> bool:
        """Add the USABLE outcomes as training points and refit. Returns True if it refitted.
        Kernel hyper-parameters are re-optimised on every refit; the sigma inflation factor
        measured by M3's k-fold is inherited unchanged (A-AF-6)."""
        known = set(self.surface.table["point_id"].astype(str))
        rows = [{"point_id": o.point_id, "role": "promotion", "split": "train", "mach": o.mach,
                 **{k: getattr(o, k) for k in SHAPE_INPUTS}, "cd_fore": o.cd_fore,
                 "verdict": o.verdict, "label": f"m6:{self.arm}:{self.seed}"}
                for o in outcomes if o.usable and o.point_id not in known]
        rows = list({r["point_id"]: r for r in rows}.values())
        if not rows:
            return False
        table = pd.concat([self.surface.table, pd.DataFrame(rows)], ignore_index=True)
        now = gate_g4_status()["status"]
        at_build = self.surface.meta["gate_G4_status_at_build"]
        meta = {k: v for k, v in self.surface.meta.items()
                if k not in ("kernel_theta", "training_hash", "n_train")}
        meta.update(adaptive_version=self.version + 1,
                    gate_G4_status_at_build=at_build if now == "PASS" else
                    (at_build if at_build != "PASS" else now),
                    n_promotion_points=int((table["role"] == "promotion").sum()))
        self.surface = CfdDragSurface(table, meta)
        self.version += 1
        self._save()
        return True


def load_base_surface(directory: Path) -> CfdDragSurface:
    return CfdDragSurface.load(Path(directory))


# ---------------------------------------------------------------------------------------
# The meter
# ---------------------------------------------------------------------------------------
EvaluateFn = Callable[[tuple[dict[str, Any], str]], dict[str, Any]]


class TwoFidelityEvaluator(BudgetedEvaluator):
    """`BudgetedEvaluator` for a surface that can change during the run.

    Accounting (extends A-OPT-3):
      * a design costs 1 evaluation each time it is evaluated under a surface version it has
        not been evaluated under before. A RE-EVALUATION after a refit is new information and
        is charged like any other evaluation (`eval_kind = reeval`);
      * the same design under the same surface version is a cache hit and costs 0;
      * probes (`probe`) are counted separately and never enter the candidate log;
      * CFD calls are counted by the arm's `CfdLedger`, never here. Each row records how many
        had been charged when it was produced (`cfd_calls_used`).
    """

    def __init__(self, space: DesignSpace, budget: int, store: CandidateStore, *, run_id: str,
                 method: str, seed: int, arm_surface: ArmSurface, ledger: CfdLedger,
                 aero_block: dict[str, Any], executor: Executor | None = None,
                 evaluate_fn: EvaluateFn = evaluate_candidate):
        super().__init__(space, budget, store, run_id=run_id, method=method, seed=seed,
                         executor=executor)
        self.arm_surface, self.ledger = arm_surface, ledger
        self._aero_block, self._evaluate_fn = dict(aero_block), evaluate_fn
        self._versioned: dict[tuple[str, int], dict[str, Any]] = {}
        self._charged = 0
        self.latest: dict[str, dict[str, Any]] = {}
        self.on_batch: Callable[[list[dict[str, Any]], int], None] | None = None
        self.n_probes, self.n_reevaluations = 0, 0

    @property
    def used(self) -> int:
        return self._charged

    def config_for(self, values: dict[str, float], **aero_overrides: Any) -> dict[str, Any]:
        cfg = self.space.config_for(values)
        aero = {**(cfg["vehicle"].get("aero") or {}), **self._aero_block,
                "surface_dir": str(self.arm_surface.directory), **aero_overrides}
        cfg["vehicle"]["aero"] = aero
        return cfg

    def _map(self, payloads: list[tuple[dict[str, Any], str]]) -> list[dict[str, Any]]:
        mapper = map if self._executor is None else self._executor.map
        return list(mapper(self._evaluate_fn, payloads))

    def evaluate(self, x_batch: np.ndarray, *, generation: int = 0,
                 parent_ids: list[list[str]] | None = None,
                 kind: str = "search") -> list[dict[str, Any]]:
        x_batch = np.atleast_2d(np.asarray(x_batch, dtype=float))
        parent_ids = parent_ids or [[] for _ in range(len(x_batch))]
        version = self.arm_surface.version
        values = [self.space.values(x) for x in x_batch]
        ids = [self.candidate_id(v) for v in values]

        new_order: list[str] = []
        for cid in ids:
            if (cid, version) not in self._versioned and cid not in new_order:
                new_order.append(cid)
        affordable = new_order[: max(self.remaining, 0)]
        first = {cid: ids.index(cid) for cid in affordable}
        results = dict(zip(affordable, self._map(
            [(self.config_for(values[first[cid]]), cid) for cid in affordable]), strict=True))

        rows: list[dict[str, Any]] = []
        fresh: set[str] = set()
        overrun = False
        for cid, vals, parents in zip(ids, values, parent_ids, strict=True):
            if cid in results and cid not in fresh:
                fresh.add(cid)
                self._versioned[(cid, version)] = results[cid]
                self._charged += 1
                hit = False
            elif (cid, version) in self._versioned:
                hit = True
                self.n_cache_hits += 1
            else:
                overrun = True
                continue
            self.n_submitted += 1
            result = self._versioned[(cid, version)]
            row = {
                "run_id": self.run_id, "method": self.method, "seed": self.seed,
                "eval_index": self.n_submitted, "budget_index": self.used,
                "generation": int(generation), "candidate_id": cid,
                "parent_ids": list(parents), "cache_hit": hit,
                **{f"x__{k}": v for k, v in vals.items()}, **result,
                "eval_kind": kind, "surface_version": version,
                "surface_hash": self.arm_surface.training_hash,
                "surface_n_train": int(len(self.arm_surface.surface.table)),
                "cfd_calls_used": self.ledger.used,
                "hull_rejected": str(result["status"]).startswith(HULL_REJECT_PREFIX),
            }
            rows.append(row)
            self.latest[cid] = row
        if kind == "reeval":
            self.n_reevaluations += len(fresh)
        self.store.append(rows)
        if overrun:
            raise BudgetExhausted(f"{self.method} seed {self.seed}: budget of "
                                  f"{self.budget} evaluations spent")
        if kind == "search" and self.on_batch is not None:
            self.on_batch(rows, int(generation))
            rows = [self.latest[row["candidate_id"]] for row in rows]
        return rows

    def reevaluate(self, rows: list[dict[str, Any]], *, generation: int) -> list[dict[str, Any]]:
        """Re-evaluate already-submitted designs under the CURRENT surface (charged)."""
        if not rows:
            return []
        x = np.array([[row[f"x__{name}"] for name in self.space.active] for row in rows])
        return self.evaluate(x, generation=generation,
                             parent_ids=[[row["candidate_id"]] for row in rows], kind="reeval")

    def probe(self, requests: list[tuple[dict[str, Any], float, bool]]) -> list[dict[str, Any]]:
        """`evaluate_design` at a given surface-error draw z_gp, for designs already submitted.
        `requests`: (row, z_gp, flag_extrapolation). Counted in `n_probes`; never logged as a
        candidate, never part of any hypervolume, not charged to the search budget (A-AF-5)."""
        payloads = []
        for row, z_gp, flag in requests:
            values = {name.removeprefix("x__"): float(v) for name, v in row.items()
                      if name.startswith("x__")}
            payloads.append((self.config_for(
                values, uncertainty={"z_gp": float(z_gp)},
                on_extrapolation="flag" if flag else "reject"), row["candidate_id"]))
        self.n_probes += len(payloads)
        return self._map(payloads)


# ---------------------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------------------
@dataclass
class PromotionLog:
    """Everything about promotion that is not a candidate row or a CFD call."""

    decisions: list[dict[str, Any]] = field(default_factory=list)
    promotions: list[dict[str, Any]] = field(default_factory=list)
    probes: list[dict[str, Any]] = field(default_factory=list)
    skipped_upfront: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"decisions": self.decisions, "promotions": self.promotions,
                "probes": self.probes, "skipped_upfront": self.skipped_upfront}


def _has_physics(row: dict[str, Any]) -> bool:
    return row["status"] == "OK"


def _shape_of_row(row: dict[str, Any], space: DesignSpace) -> dict[str, float]:
    """Forebody shape ratios of a candidate row (frozen variables come from the space)."""
    values = {v.name: v.reference for v in space.variables}
    values.update({k.removeprefix("x__"): float(v) for k, v in row.items()
                   if k.startswith("x__")})
    return {k: float(values[k]) for k in SHAPE_INPUTS}


class PromotionController:
    """Runs after every search batch of one (arm, seed) and decides who gets CFD.

    Strategies
      adaptive  the section-26 policy (module docstring)
      random    a uniformly random submitted design of the batch, on an even spending schedule
      greedy    the believed-front member with the largest exclusive hypervolume contribution
                that has not been promoted yet, on the same schedule
      upfront   the whole CFD budget on a seeded space-filling design BEFORE the search
      none      never promotes

    Everything downstream of "who" is shared: the Mach rule, the charging, the refit, the
    charged re-evaluation of the promoted design and of the believed front.
    """

    def __init__(self, strategy: str, policy: dict[str, Any], *, evaluator: TwoFidelityEvaluator,
                 cases: CfdCaseStore, objectives: tuple[str, ...], hv_cfg: dict[str, Any],
                 log: PromotionLog, planned_batches: int,
                 shape_is_valid: Callable[[dict[str, float]], str] | None = None):
        if strategy not in STRATEGIES:
            raise ValueError(f"unknown promotion strategy '{strategy}', expected {STRATEGIES}")
        self.strategy, self.policy = strategy, policy
        self.ev, self.cases, self.log = evaluator, cases, log
        self.surface, self.ledger = evaluator.arm_surface, evaluator.ledger
        self.objectives = tuple(objectives)
        self.ideal = np.array([hv_cfg["ideal_point"][n] for n in objectives], dtype=float)
        self.ref = np.array([hv_cfg["reference_point"][n] for n in objectives], dtype=float)
        self.planned_batches = max(int(planned_batches), 1)
        self.shape_is_valid = shape_is_valid or (lambda shape: "")
        self.rng = np.random.default_rng([evaluator.seed, 606])
        self.batch_index = 0
        self.idle_batches = 0
        self.promoted: set[str] = set()
        self.agent_requests: dict[str, int] = {}
        self.exploration_calls = 0

    # -- shared mechanics ----------------------------------------------------------------
    def _norm(self, rows: list[dict[str, Any]]) -> np.ndarray:
        f = np.array([[row[n] for n in self.objectives] for row in rows], dtype=float)
        return normalise(f, self.ideal, self.ref) if len(rows) else np.empty((0, 2))

    def believed_front(self) -> list[dict[str, Any]]:
        feasible = [row for row in self.ev.latest.values() if row["feasible"]]
        if not feasible:
            return []
        idx = pareto_front(np.array([[row[n] for n in self.objectives] for row in feasible]))
        return [feasible[i] for i in idx]

    def mach_requests(self, shape: dict[str, float], outside: bool) -> list[CfdRequest]:
        """The Mach rule, identical for every promoting strategy.

        Outside the hull: BOTH ends of the CFD Mach range, high end first - the only way a new
        shape enters the 4-D hull the evaluator checks. Inside: the ONE declared Mach node
        where (heat-load weight x surface sigma) is largest, skipping nodes this arm has
        already paid for or that sit on top of an existing training point."""
        s = self.surface.surface
        if outside:
            return [CfdRequest.of(s.mach_max, shape), CfdRequest.of(s.mach_min, shape)]
        nodes = np.array([float(m) for m in self.policy["mach_rule"]["nodes"]])
        weights = np.array([float(w) for w in self.policy["mach_rule"]["weights"]])
        worth = weights * self.surface.sigma(shape, nodes)
        min_sep = float(self.policy["min_training_separation"])
        for i in np.argsort(-worth):
            request = CfdRequest.of(float(np.clip(nodes[i], s.mach_min, s.mach_max)), shape)
            if not self.ledger.has_paid(request) and self.surface.separation(request) >= min_sep:
                return [request]
        return []

    def _execute(self, picks: list[dict[str, Any]], generation: int, *,
                 reevaluate: bool = True) -> None:
        """Charge, run, absorb, refit, re-evaluate. `picks`: row, requests, trigger, scores."""
        submitted: list[tuple[dict[str, Any], list[Future]]] = []
        for pick in picks:
            futures = []
            for request in pick["requests"]:
                if self.ledger.remaining < 1 and not self.ledger.has_paid(request):
                    break
                self.ledger.charge(request, trigger=pick["trigger"],
                                   candidate_id=pick["row"]["candidate_id"],
                                   evaluations_used=self.ev.used)
                futures.append(self.cases.submit(request))
            if futures:
                submitted.append((pick, futures))
                self.promoted.add(pick["row"]["candidate_id"])
        if not submitted:
            return
        outcomes = [[f.result() for f in futures] for _, futures in submitted]
        for group in outcomes:
            for outcome in group:
                self.ledger.settle(outcome)
        version_before = self.surface.version
        refitted = self.surface.absorb([o for group in outcomes for o in group])
        before = {pick["row"]["candidate_id"]: dict(pick["row"]) for pick, _ in submitted}
        after: dict[str, dict[str, Any]] = {}
        exhausted = False
        if refitted and reevaluate:
            front = [row for row in self.believed_front()
                     if row["candidate_id"] not in before]
            front = front[: int(self.policy["max_front_reevaluations"])]
            try:
                fresh = self.ev.reevaluate([pick["row"] for pick, _ in submitted] + front,
                                           generation=generation)
                after = {row["candidate_id"]: row for row in fresh}
            except BudgetExhausted:
                exhausted = True
                after = {cid: self.ev.latest[cid] for cid in before}
        for (pick, _), group in zip(submitted, outcomes, strict=True):
            cid = pick["row"]["candidate_id"]
            new = after.get(cid)
            self.log.promotions.append({
                "arm": self.ev.method, "seed": self.ev.seed, "batch": self.batch_index,
                "strategy": self.strategy, "trigger": pick["trigger"], "candidate_id": cid,
                "scores": pick.get("scores", {}),
                "cfd": [o.to_dict() for o in group],
                "n_usable": sum(o.usable for o in group),
                "surface_version_before": version_before,
                "surface_version_after": self.surface.version, "refitted": bool(refitted),
                "evaluation_budget_exhausted_during_reevaluation": exhausted,
                "before": {"status": before[cid]["status"],
                           "feasible": bool(before[cid]["feasible"]),
                           **{n: before[cid][n] for n in self.objectives}},
                "after": (None if new is None or new["surface_version"] == version_before
                          else {"status": new["status"], "feasible": bool(new["feasible"]),
                                **{n: new[n] for n in self.objectives}}),
            })
        if exhausted:
            raise BudgetExhausted(f"{self.ev.method} seed {self.ev.seed}: evaluation budget "
                                  "spent while re-evaluating after a refit")

    # -- hooks ----------------------------------------------------------------------------
    def decide_batch(self, x_batch, candidate_ids, agent_requests, rows, surrogate, space,
                     objectives, hv_cfg) -> list[FidelityDecision]:
        """`run_ai_agent`'s policy hook (M5 signature). The agent's `requested_fidelity` is
        QUEUED as one input of the promotion policy; the decision is taken after the batch has
        been evaluated, by the same rule and against the same CFD budget as everything else."""
        out = []
        for cid, wanted in zip(candidate_ids, agent_requests, strict=True):
            self.agent_requests[cid] = int(wanted)
            out.append(FidelityDecision(
                candidate_id=cid, agent_requested_fidelity=int(wanted),
                predicted_hv_gain=float("nan"), uncertainty=float("nan"),
                novelty=float("nan"), extrapolated=False, policy_fidelity=int(wanted),
                granted_fidelity=0,
                reason="queued for the M6 promotion controller; the decision and its scores "
                       "are in promotion_log.json"))
        return out

    def run_upfront(self) -> None:
        """Strategy `upfront`: the whole CFD budget on a seeded scrambled-Sobol design over
        (log Mach, shape) before any evaluation - what M3 did, at this arm's budget."""
        if self.strategy != "upfront" or self.ledger.budget < 1:
            return
        s = self.surface.surface
        rng = s.meta["input_ranges"]
        lo = np.array([rng[k][0] for k in SHAPE_INPUTS], dtype=float)
        hi = np.array([rng[k][1] for k in SHAPE_INPUTS], dtype=float)
        draws = qmc.Sobol(d=4, scramble=True, seed=self.ev.seed).random(
            int(self.policy["upfront"]["max_draws"]))
        requests: list[CfdRequest] = []
        for k, u in enumerate(draws):
            if len(requests) == self.ledger.budget:
                break
            mach = float(np.exp(np.log(s.mach_min) + u[0] * np.log(s.mach_max / s.mach_min)))
            shape = dict(zip(SHAPE_INPUTS, map(float, lo + u[1:] * (hi - lo)), strict=True))
            reason = self.shape_is_valid(shape)
            if reason:
                self.log.skipped_upfront.append({"arm": self.ev.method, "seed": self.ev.seed,
                                                 "draw": k, **shape, "reason": reason})
                continue
            requests.append(CfdRequest.of(mach, shape))
        row = {"candidate_id": "upfront-design", "status": "n/a", "feasible": False,
               **{n: float("nan") for n in self.objectives}}
        self._execute([{"row": row, "requests": requests, "trigger": "upfront space-filling",
                        "scores": {}}], generation=-1, reevaluate=False)
        self.promoted.discard("upfront-design")

    def after_batch(self, rows: list[dict[str, Any]], generation: int) -> None:
        self.batch_index += 1
        if self.strategy in ("none", "upfront") or self.ledger.remaining < 1:
            return
        paid = [row for row in rows if not row["cache_hit"]]
        if self.strategy == "adaptive":
            picks = self._adaptive(paid)
        elif self.strategy == "random":
            picks = self._scheduled(paid, self._pick_random)
        else:
            picks = self._scheduled(paid, self._pick_greedy)
        self.idle_batches = 0 if picks else self.idle_batches + 1
        if picks:
            self._execute(picks, generation)

    # -- comparators ------------------------------------------------------------------------
    def _allowance(self) -> int:
        """Calls the even spending schedule allows by now, minus what has been spent."""
        due = math.ceil(self.ledger.budget * min(self.batch_index / self.planned_batches, 1.0))
        return due - self.ledger.used

    def _promotable(self, row: dict[str, Any]) -> bool:
        return (row["candidate_id"] not in self.promoted
                and (_has_physics(row) or row["hull_rejected"]))

    def _scheduled(self, paid, picker) -> list[dict[str, Any]]:
        picks: list[dict[str, Any]] = []
        planned = 0
        taken: set[str] = set()
        while self._allowance() - planned >= 1:
            row = picker(paid, taken)
            if row is None:
                break
            taken.add(row["candidate_id"])
            shape = _shape_of_row(row, self.ev.space)
            requests = self.mach_requests(shape, bool(row["hull_rejected"]))
            if not requests or len(requests) > self.ledger.remaining - planned:
                continue
            planned += len(requests)
            picks.append({"row": row, "requests": requests, "trigger": self.strategy,
                          "scores": {}})
        return picks

    def _pick_random(self, paid, taken) -> dict[str, Any] | None:
        pool = [row for row in paid if self._promotable(row)
                and row["candidate_id"] not in taken]
        return pool[int(self.rng.integers(len(pool)))] if pool else None

    def _pick_greedy(self, paid, taken) -> dict[str, Any] | None:
        front = self.believed_front()
        pool = [row for row in front if self._promotable(row)
                and row["candidate_id"] not in taken]
        if not pool:
            return None
        f_all = self._norm(front)
        total = hypervolume_2d(f_all, np.ones(2))
        gains = []
        for row in pool:
            others = self._norm([r for r in front if r["candidate_id"] != row["candidate_id"]])
            gains.append(total - hypervolume_2d(others, np.ones(2)))
        return pool[int(np.argmax(gains))]

    # -- the section-26 policy -----------------------------------------------------------------
    def _epsilon(self, f: np.ndarray, front: np.ndarray) -> float:
        """Smallest uniform improvement (normalised objectives) that would make `f`
        non-dominated against `front`. 0 when it already is."""
        if not len(front):
            return 0.0
        return float(max(0.0, np.max(np.min(f[None, :] - front, axis=1))))

    def _shortlist(self, paid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        p = self.policy["prescreen"]
        front_rows = self.believed_front()
        recent_out = [row for row in self.ev.latest.values() if row["hull_rejected"]]
        recent_out = recent_out[-int(p["recent_hull_rejected"]):]
        pool = {row["candidate_id"]: row for row in [*paid, *front_rows, *recent_out]
                if self._promotable(row)}
        x_front = (self.ev.space.to_unit(np.array(
            [[r[f"x__{n}"] for n in self.ev.space.active] for r in front_rows]))
            if front_rows else np.empty((0, self.ev.space.n_active)))
        inside, outside = [], []
        for row in pool.values():
            row = self.ev.latest.get(row["candidate_id"], row)
            if row["hull_rejected"]:
                x = self.ev.space.to_unit(np.array([row[f"x__{n}"]
                                                    for n in self.ev.space.active]))
                dist = (float(np.min(np.linalg.norm(x_front - x, axis=1)))
                        if len(x_front) else 0.0)
                outside.append((dist, row))
            elif _has_physics(row):
                margins = [row[f"margin__{n}"] for n in MARGIN_NAMES
                           if not math.isnan(row[f"margin__{n}"])]
                if margins and min(margins) < -float(p["max_constraint_violation"]):
                    continue
                others = self._norm([r for r in front_rows
                                     if r["candidate_id"] != row["candidate_id"]])
                eps = self._epsilon(self._norm([row])[0], others)
                if eps <= float(p["max_epsilon_to_front"]) or \
                        self.agent_requests.get(row["candidate_id"], 0) >= 1:
                    inside.append((eps, row))
        inside.sort(key=lambda item: item[0])
        outside.sort(key=lambda item: item[0])
        n_max, n_out = int(p["max_candidates"]), int(p["max_outside_hull"])
        chosen_out = [row for _, row in outside[:n_out]]
        chosen_in = [row for _, row in inside[: n_max - len(chosen_out)]]
        return chosen_in + chosen_out

    def _probe_scores(self, row: dict[str, Any]) -> dict[str, Any] | None:
        """(a) and (b): the surface's error bar pushed through the canonical evaluator."""
        outside = bool(row["hull_rejected"])
        stale = row["surface_version"] != self.surface.version
        zs = [-1.0, 1.0] + ([0.0] if outside or stale else [])
        results = self.ev.probe([(row, z, outside) for z in zs])
        by_z = dict(zip(zs, results, strict=True))
        centre = by_z.get(0.0, row)
        self.log.probes.append({
            "arm": self.ev.method, "seed": self.ev.seed, "batch": self.batch_index,
            "candidate_id": row["candidate_id"], "outside_hull": outside,
            "surface_version": self.surface.version,
            "results": {str(z): {"status": r["status"], "feasible": bool(r["feasible"]),
                                 **{n: r[n] for n in self.objectives}}
                        for z, r in by_z.items()}})
        if not all(_has_physics(r) for r in (by_z[-1.0], by_z[1.0], centre)):
            return None

        def line(name: str) -> np.ndarray:
            slope = 0.5 * (by_z[1.0][name] - by_z[-1.0][name])
            return centre[name] + slope * _Z_GRID

        f_z = normalise(np.column_stack([line(n) for n in self.objectives]), self.ideal,
                        self.ref)
        feasible_z = np.ones(N_Z_QUANTILES, dtype=bool)
        for name in MARGIN_NAMES:
            key = f"margin__{name}"
            if not math.isnan(centre[key]):
                feasible_z &= line(key) >= 0.0
        front = self._norm([r for r in self.believed_front()
                            if r["candidate_id"] != row["candidate_id"]])
        base = hypervolume_2d(front, np.ones(2))
        nondominated = np.array([self._epsilon(f, front) == 0.0 for f in f_z])
        gains = np.array([hypervolume_2d(np.vstack([front, f]), np.ones(2)) - base
                          if ok else 0.0 for f, ok in zip(f_z, feasible_z, strict=True)])
        half_range = 0.5 * np.abs(
            normalise(np.array([[by_z[1.0][n] for n in self.objectives]]), self.ideal, self.ref)
            - normalise(np.array([[by_z[-1.0][n] for n in self.objectives]]), self.ideal,
                        self.ref))[0]
        return {"p_nondominated": float(np.mean(nondominated & feasible_z)),
                "p_feasible": float(np.mean(feasible_z)),
                "expected_hv_gain": float(np.mean(gains)),
                "objective_uncertainty": float(np.max(half_range))}

    def _adaptive(self, paid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pol = self.policy
        w, scale, gate = pol["weights"], pol["scales"], pol["gates"]
        scored = []
        for row in self._shortlist(paid):
            cid = row["candidate_id"]
            shape = _shape_of_row(row, self.ev.space)
            outside = bool(row["hull_rejected"])
            requests = self.mach_requests(shape, outside)
            probe = self._probe_scores(row)
            novelty = 1.0 if outside else self.surface.novelty(shape)
            agent = int(self.agent_requests.get(cid, 0) >= 1)
            record = {"arm": self.ev.method, "seed": self.ev.seed, "batch": self.batch_index,
                      "candidate_id": cid, "outside_hull": outside, "novelty": novelty,
                      "agent_requested_fidelity": agent, "calls_needed": len(requests),
                      "cfd_remaining": self.ledger.remaining, "promoted": False}
            if probe is None or not requests:
                record["reason"] = ("no physics result under the surface's +-1 sigma draws"
                                    if probe is None else
                                    "every useful Mach node is already a training point")
                self.log.decisions.append(record)
                continue
            cost = len(requests) / max(self.ledger.remaining, 1)
            score = (float(w["value"]) * probe["p_nondominated"]
                     + float(w["uncertainty"]) * min(probe["objective_uncertainty"]
                                                     / float(scale["uncertainty"]), 1.0)
                     + float(w["novelty"]) * min(novelty / float(scale["novelty"]), 1.0)
                     + float(w["agent_request"]) * agent - float(w["cost"]) * cost)
            matters = probe["p_nondominated"] >= float(gate["min_p_nondominated"]) or agent
            u_gate = float(gate["min_objective_uncertainty"])
            untrusted = (outside or probe["objective_uncertainty"] >= u_gate
                         or novelty >= float(gate["min_novelty"]))
            affordable = len(requests) <= self.ledger.remaining
            record.update(probe, cost=cost, score=score, matters=bool(matters),
                          untrusted=bool(untrusted), affordable=bool(affordable))
            if not matters:
                record["reason"] = "clearly poor: P(non-dominated) below the gate, stays at F0"
            elif not untrusted:
                record["reason"] = "surface already confident here and the shape is not novel"
            elif not affordable:
                record["reason"] = "would promote, but the CFD budget cannot cover it"
            elif score < float(pol["min_score"]):
                record["reason"] = "score below min_score"
            else:
                record["reason"] = "promising, and the cheap model is untrusted here"
                scored.append((score, row, requests, record))
            self.log.decisions.append(record)

        scored.sort(key=lambda item: -item[0])
        picks, planned = [], 0
        for _score, row, requests, record in scored[: int(pol["max_promotions_per_batch"])]:
            if planned + len(requests) > self.ledger.remaining:
                continue
            planned += len(requests)
            record["promoted"] = True
            picks.append({"row": row, "requests": requests, "trigger": "adaptive policy",
                          "scores": {k: record[k] for k in (
                              "p_nondominated", "expected_hv_gain", "objective_uncertainty",
                              "novelty", "cost", "score", "outside_hull",
                              "agent_requested_fidelity")}})
        if not picks:
            picks = self._explore(paid)
        return picks

    def _explore(self, paid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Section 26: a poor-looking candidate stays at F0 'unless needed for exploration'.
        After `after_idle_batches` batches without a promotion, the hull-rejected design of
        this batch nearest the believed front is promoted, up to `max_calls` calls per run."""
        ex = self.policy["exploration"]
        if (self.idle_batches + 1 < int(ex["after_idle_batches"])
                or self.exploration_calls + 2 > int(ex["max_calls"])
                or self.ledger.remaining < 2):
            return []
        outside = [row for row in paid if row["hull_rejected"] and self._promotable(row)]
        if not outside:
            return []
        front_rows = self.believed_front()
        if front_rows:
            x_front = self.ev.space.to_unit(np.array(
                [[r[f"x__{n}"] for n in self.ev.space.active] for r in front_rows]))
            dist = [float(np.min(np.linalg.norm(
                x_front - self.ev.space.to_unit(np.array(
                    [row[f"x__{n}"] for n in self.ev.space.active])), axis=1)))
                    for row in outside]
            row = outside[int(np.argmin(dist))]
        else:
            row = outside[0]
        requests = self.mach_requests(_shape_of_row(row, self.ev.space), True)
        self.exploration_calls += len(requests)
        self.log.decisions.append({
            "arm": self.ev.method, "seed": self.ev.seed, "batch": self.batch_index,
            "candidate_id": row["candidate_id"], "outside_hull": True, "promoted": True,
            "reason": "exploration: no promotion for "
                      f"{self.idle_batches + 1} batches; nearest hull-rejected design"})
        return [{"row": row, "requests": requests, "trigger": "adaptive exploration",
                 "scores": {"outside_hull": True}}]


def forebody_validity(diameter_m: float) -> Callable[[dict[str, float]], str]:
    """'' if M3's neutral-afterbody capsule with this forebody exists, else the reason."""
    from ..cfd.design_points import forebody_capsule

    def check(shape: dict[str, float]) -> str:
        try:
            forebody_capsule(diameter_m=diameter_m, **shape)
        except ValueError as exc:
            return str(exc)
        return ""
    return check


def dry_run_truth(base: CfdDragSurface, amplitude: float = 0.04
                  ) -> Callable[[float, dict[str, float]], float]:
    """A FAKE 'true' C_D,fore for labelled dry runs of the pipeline: the starting surface's own
    (flagged) prediction times a smooth, declared perturbation of `amplitude`. It exists so
    the whole M6 pipeline can be exercised without OpenFOAM; it says nothing about drag."""
    rng = base.meta["input_ranges"]

    def cd(mach: float, shape: dict[str, float]) -> float:
        m = float(np.clip(mach, base.mach_min, base.mach_max))
        pred = base.predict_fore(np.array([m]), shape, on_extrapolation="flag")
        u = [(shape[k] - rng[k][0]) / (rng[k][1] - rng[k][0]) for k in SHAPE_INPUTS]
        bump = math.sin(3.0 * u[0] + 1.0) * math.cos(2.0 * u[1]) + 0.5 * (u[2] - 0.5)
        return float(pred.central[0] * (1.0 + amplitude * bump))
    return cd
