"""M6 study driver: run the arms, then score them on pooled truth. The CLI is
`scripts/run_adaptive_fidelity.py`; everything that decides a number lives here.

One (arm, seed) = one search (NSGA-II, or the LLM agent) through a `TwoFidelityEvaluator`,
with a `PromotionController` called after every batch. All (arm, seed) runs go side by side in
threads: they spend most of their life waiting for CFD, and the shared `CfdCaseStore` keeps at
most `cfd.max_concurrent` serial solvers running whatever the number of waiting arms. Each
run depends only on its own seed and on (deterministic) CFD outcomes, so the order in which
threads are served cannot change a result.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..aerodynamics.cfd_surface import SHAPE_INPUTS, CfdDragSurface
from .adaptive import (
    ArmSurface,
    CfdCaseStore,
    CfdLedger,
    CfdRequest,
    EvaluateFn,
    PromotionController,
    PromotionLog,
    TwoFidelityEvaluator,
    _shape_of_row,
)
from .adaptive_analysis import (
    arm_seed_curve,
    arm_table,
    belief_at,
    build_truth_surface,
    calls_to_target,
    compare_final,
    distinct_designs,
    h2_verdict,
    holdout_table,
    hv_points,
    recommended,
    surface_error_table,
    truth_evaluate,
    truth_sigma_at,
)
from .ai_agent import AgentLog, run_ai_agent
from .budget import evaluate_candidate
from .design_space import DesignSpace
from .optimizers import run_nsga2
from .pareto import normalised_hypervolume, pareto_front
from .persistence import CandidateStore, load_candidates

LLM_SEARCH = "ai_agent"


@dataclass
class StudyContext:
    run_id: str
    out_dir: Path
    space: DesignSpace
    objectives: tuple[str, ...]
    hv_cfg: dict[str, Any]
    cfg: dict[str, Any]                      # the `adaptive_fidelity` block
    base_surface: CfdDragSurface
    aero_block: dict[str, Any]
    store: CandidateStore
    cases: CfdCaseStore
    executor: Executor | None = None
    evaluate_fn: EvaluateFn = evaluate_candidate
    shape_is_valid: Callable[[dict[str, float]], str] | None = None
    llm_client: Callable[[str, int], Any] | None = None     # (arm, seed) -> LLM client
    check_source: Callable[[str], None] = lambda where: None
    progress: Callable[[str], None] = print


def arm_seeds(cfg: dict[str, Any], arm: str) -> list[int]:
    return [int(s) for s in cfg["arms"][arm].get("seeds", cfg["seeds"])]


def planned_batches(cfg: dict[str, Any], settings: dict[str, Any]) -> int:
    """Batches over which the scheduled comparators spread their CFD budget."""
    if settings["search"] == LLM_SEARCH:
        n = int(settings["rounds"])
    else:
        n = int(cfg["budget_evaluations"]) // int(settings["population_size"])
    return max(1, math.floor(float(cfg["policy"]["spend_by_fraction"]) * n))


def run_arm_seed(ctx: StudyContext, arm: str, seed: int, agent_log: AgentLog | None
                 ) -> dict[str, Any]:
    settings = ctx.cfg["arms"][arm]
    start = time.perf_counter()
    ctx.check_source(f"before {arm} seed {seed}")
    surface = ArmSurface(ctx.out_dir / "surfaces" / arm / f"seed_{seed}", ctx.base_surface,
                         arm=arm, seed=seed)
    ledger = CfdLedger(int(settings.get("cfd_budget", ctx.cfg["cfd_budget_calls"])), arm, seed)
    evaluator = TwoFidelityEvaluator(
        ctx.space, int(ctx.cfg["budget_evaluations"]), ctx.store, run_id=ctx.run_id,
        method=arm, seed=seed, arm_surface=surface, ledger=ledger, aero_block=ctx.aero_block,
        executor=ctx.executor, evaluate_fn=ctx.evaluate_fn)
    log = PromotionLog()
    controller = PromotionController(
        settings["strategy"], ctx.cfg["policy"], evaluator=evaluator, cases=ctx.cases,
        objectives=ctx.objectives, hv_cfg=ctx.hv_cfg, log=log,
        planned_batches=planned_batches(ctx.cfg, settings),
        shape_is_valid=ctx.shape_is_valid)
    evaluator.on_batch = controller.after_batch
    controller.run_upfront()
    llm_calls = 0
    if settings["search"] == LLM_SEARCH:
        if ctx.llm_client is None:
            raise RuntimeError(f"arm '{arm}' needs an LLM client (live or replay)")
        client = ctx.llm_client(arm, seed)
        run_ai_agent(evaluator, settings, ctx.objectives, ctx.hv_cfg, client=client,
                     log=agent_log, policy=controller)
        llm_calls = int(client.calls_made)
    elif settings["search"] == "nsga2":
        run_nsga2(evaluator, settings, ctx.objectives, ctx.hv_cfg)
    else:
        raise ValueError(f"arm '{arm}': unknown search '{settings['search']}'")
    ctx.check_source(f"after {arm} seed {seed}")
    wall = time.perf_counter() - start
    ctx.progress(f"  {arm:<12} seed {seed:>3}: {evaluator.used}/{evaluator.budget} evaluations "
                 f"({evaluator.n_reevaluations} re-evaluations, {evaluator.n_probes} probes), "
                 f"{ledger.used}/{ledger.budget} CFD calls, surface v{surface.version} "
                 f"({len(surface.surface.table)} points), {wall:.0f} s")
    return {"arm": arm, "seed": seed, "wall_s": wall, "evaluations_used": evaluator.used,
            "n_probes": evaluator.n_probes, "n_reevaluations": evaluator.n_reevaluations,
            "n_cache_hits": evaluator.n_cache_hits, "cfd_budget": ledger.budget,
            "cfd_calls": ledger.used, "n_repeat_requests": ledger.n_repeat_requests,
            "surface_version": surface.version, "surface_history": surface.history,
            "llm_calls": llm_calls, "ledger": ledger.records, "promotion_log": log.to_dict()}


def run_arms(ctx: StudyContext, arms: list[str]) -> dict[str, Any]:
    """Every enabled (arm, seed), side by side. Persists the ledgers and logs."""
    jobs = [(arm, seed) for arm in arms for seed in arm_seeds(ctx.cfg, arm)]
    agent_logs = {arm: AgentLog() for arm in arms
                  if ctx.cfg["arms"][arm]["search"] == LLM_SEARCH}
    with ThreadPoolExecutor(max_workers=max(1, int(ctx.cfg["max_parallel_arm_seeds"])),
                            thread_name_prefix="arm") as threads:
        futures = [threads.submit(run_arm_seed, ctx, arm, seed, agent_logs.get(arm))
                   for arm, seed in jobs]
        done = [f.result() for f in futures]
    calls = pd.DataFrame([rec for d in done for rec in d["ledger"]])
    calls.to_csv(ctx.out_dir / "cfd_calls.csv", index=False)
    merged = {key: [item for d in done for item in d["promotion_log"][key]]
              for key in ("decisions", "promotions", "probes", "skipped_upfront")}
    (ctx.out_dir / "promotion_log.json").write_text(json.dumps(merged, indent=1, default=float))
    (ctx.out_dir / "agent_log.json").write_text(json.dumps(
        {arm: log.to_dict() for arm, log in agent_logs.items()}, indent=1, default=float))
    counters = {f"{d['arm']}|{d['seed']}": {k: v for k, v in d.items()
                                            if k not in ("ledger", "promotion_log")}
                for d in done}
    (ctx.out_dir / "counters.json").write_text(json.dumps(counters, indent=1, default=float))
    return counters


# ---------------------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------------------
def _reference_search(ctx: StudyContext, truth: CfdDragSurface) -> pd.DataFrame:
    """A dedicated large-budget search ON THE TRUTH SURFACE, so the reference front does not
    depend on how well the arms happened to cover it. F0 on pooled truth: no CFD, no arm sees
    it, no arm is charged for it."""
    ref_cfg = ctx.cfg["reference"]
    store = CandidateStore(ctx.out_dir / "reference_candidates.csv")
    for seed in ref_cfg["seeds"]:
        surface = ArmSurface(ctx.out_dir / "truth" / f"reference_seed_{seed}", truth,
                             arm="REFERENCE", seed=int(seed))
        evaluator = TwoFidelityEvaluator(
            ctx.space, int(ref_cfg["budget_evaluations"]), store, run_id=ctx.run_id,
            method="reference", seed=int(seed), arm_surface=surface,
            ledger=CfdLedger(0, "reference", int(seed)), aero_block=ctx.aero_block,
            executor=ctx.executor, evaluate_fn=ctx.evaluate_fn)
        run_nsga2(evaluator, {"population_size": int(ref_cfg["population_size"])},
                  ctx.objectives, ctx.hv_cfg)
    return load_candidates(store.csv_path)


def _holdout_picks(ctx: StudyContext, truth_surface: CfdDragSurface, frame: pd.DataFrame,
                   truth: pd.DataFrame, arms: list[str]) -> list[dict[str, Any]]:
    """Per arm: the truly-feasible recommended design whose Mach-max case is FARTHEST from
    every point the truth surface was fitted to - where truth is least supported."""
    n_per_arm = int(ctx.cfg["holdout"]["cases_per_arm"])
    min_sep = float(ctx.cfg["policy"]["min_training_separation"])
    probe = ArmSurface(ctx.out_dir / "truth" / "holdout_probe", truth_surface,
                       arm="HOLDOUT-PROBE", seed=0)
    ok = set(truth[truth["truth__feasible"]]["candidate_id"])
    picks: list[dict[str, Any]] = []
    taken: set[str] = set()
    for arm in arms:
        sub = frame[frame["method"] == arm]
        rows = []
        for seed in sorted(sub["seed"].unique()):
            run = sub[sub["seed"] == seed]
            rec = recommended(belief_at(run, int(run["budget_index"].max())), ctx.objectives)
            rows.extend(r for r in rec.to_dict("records") if r["candidate_id"] in ok)
        scored = []
        for row in rows:
            request = CfdRequest.of(truth_surface.mach_max, _shape_of_row(row, ctx.space))
            sep = probe.separation(request)
            if sep >= min_sep and request.key not in taken:
                scored.append((sep, request))
        scored.sort(key=lambda item: -item[0])
        for sep, request in scored[:n_per_arm]:
            taken.add(request.key)
            picks.append({"arm": arm, "key": request.key, "mach": request.mach,
                          **request.shape, "separation_from_truth_training": sep,
                          "request": request})
    return picks


def score_study(ctx: StudyContext, arms: list[str], counters: dict[str, Any]
                ) -> dict[str, Any]:
    cfg, objectives = ctx.cfg, ctx.objectives
    ideal, ref = hv_points(ctx.hv_cfg, objectives)
    frame = load_candidates(ctx.out_dir / "candidates.csv")
    calls_path, cases_path = ctx.out_dir / "cfd_calls.csv", ctx.cases.csv_path
    calls = (pd.read_csv(calls_path) if calls_path.exists() and calls_path.stat().st_size > 2
             else pd.DataFrame(columns=["arm", "seed", "evaluations_used", "usable",
                                        "wall_time_s", "mach", *SHAPE_INPUTS]))
    cases = pd.read_csv(cases_path) if cases_path.exists() else pd.DataFrame(
        columns=list(CfdCaseStore.COLUMNS))

    # -- pooled truth -------------------------------------------------------------------
    truth_surface = build_truth_surface(ctx.base_surface, cases, ctx.out_dir / "truth" / "surface")
    truth_block = {**ctx.aero_block, "surface_dir": str(ctx.out_dir / "truth" / "surface")}
    reference = _reference_search(ctx, truth_surface)
    designs = distinct_designs(frame)
    truth = truth_evaluate(designs, ctx.space, truth_block, objectives,
                           executor=ctx.executor, evaluate_fn=ctx.evaluate_fn)
    truth.to_csv(ctx.out_dir / "truth.csv", index=False)

    ref_feasible = reference[reference["feasible"]].drop_duplicates("candidate_id")
    pool = np.vstack([
        truth[truth["truth__feasible"]][[f"truth__{n}" for n in objectives]].to_numpy(float),
        ref_feasible[list(objectives)].to_numpy(float)])
    hv_reference = float(normalised_hypervolume(pool, ideal, ref)) if len(pool) else 0.0
    arms_only = truth[truth["truth__feasible"]]
    hv_arms_union = float(normalised_hypervolume(
        arms_only[[f"truth__{n}" for n in objectives]].to_numpy(float), ideal, ref)) \
        if len(arms_only) else 0.0
    hv_reference_search = float(normalised_hypervolume(
        ref_feasible[list(objectives)].to_numpy(float), ideal, ref)) if len(ref_feasible) \
        else 0.0

    # reference front: ids of ARM designs on it, shapes of every design on it
    ids = [*arms_only["candidate_id"], *ref_feasible["candidate_id"]]
    front_idx = pareto_front(pool) if len(pool) else np.array([], dtype=int)
    reference_front_ids = {ids[i] for i in front_idx}
    x_by_id = {**{r["candidate_id"]: r for r in designs.to_dict("records")},
               **{r["candidate_id"]: r for r in ref_feasible.to_dict("records")}}
    front_shapes = [_shape_of_row(x_by_id[i], ctx.space) for i in sorted(reference_front_ids)]
    front_shapes = front_shapes[: int(cfg["analysis"]["max_probe_shapes"])]
    pd.DataFrame(front_shapes, columns=list(SHAPE_INPUTS)).to_csv(
        ctx.out_dir / "reference_front_shapes.csv", index=False)

    # -- curves ---------------------------------------------------------------------------
    step, budget = int(cfg["curve_step"]), int(cfg["budget_evaluations"])
    checkpoints = np.arange(step, budget + 1, step)
    curves: dict[tuple[str, int], pd.DataFrame] = {}
    curve_rows = []
    for arm in arms:
        for seed in arm_seeds(cfg, arm):
            run = frame[(frame["method"] == arm) & (frame["seed"] == seed)]
            mine = calls[(calls["arm"] == arm) & (calls["seed"] == seed)]
            curve = arm_seed_curve(run, mine, truth, objectives, ctx.hv_cfg, checkpoints)
            curves[(arm, seed)] = curve
            curve_rows.append(curve.assign(arm=arm, seed=seed))
    pd.concat(curve_rows, ignore_index=True).to_csv(ctx.out_dir / "curves.csv", index=False)

    # -- H2 -------------------------------------------------------------------------------
    crit = cfg["success_criteria"]
    fractions = [float(crit["target_fraction_of_reference_hv"]),
                 *[float(f) for f in crit.get("sensitivity_fractions", [])]]
    h2 = {}
    for fraction in fractions:
        reach = {arm: [calls_to_target(curves[(arm, seed)], fraction * hv_reference)
                       for seed in arm_seeds(cfg, arm)] for arm in arms
                 if arm in (crit["subject"], crit["no_cfd_arm"], *crit["comparators"])}
        h2[f"{fraction:g}"] = {"fraction": fraction, "target_hv": fraction * hv_reference,
                               "reach": reach,
                               **h2_verdict(reach, crit, int(cfg["cfd_budget_calls"]))}

    table = arm_table(frame, calls, truth, curves, counters, reference_front_ids, arms)

    # -- surfaces -----------------------------------------------------------------------------
    finals = {}
    for key, c in counters.items():
        arm, seed = key.split("|")
        finals[(arm, int(seed))] = CfdDragSurface.load(Path(c["surface_history"][-1]["directory"]))
    machs = [float(m) for m in cfg["policy"]["mach_rule"]["nodes"]]
    errors = surface_error_table(finals, truth_surface, front_shapes, machs)
    errors.to_csv(ctx.out_dir / "surface_error.csv", index=False)
    for arm in arms:
        sub = frame[frame["method"] == arm]
        shapes = []
        for seed in sorted(sub["seed"].unique()):
            run = sub[sub["seed"] == seed]
            rec = recommended(belief_at(run, int(run["budget_index"].max())), objectives)
            shapes.extend(_shape_of_row(r, ctx.space) for r in rec.to_dict("records"))
        table[arm]["truth_sigma_cd_at_recommended_mach_max"] = truth_sigma_at(
            truth_surface, shapes, truth_surface.mach_max)
        mine = errors[errors["arm"] == arm]
        table[arm]["surface_rmse_vs_truth_mean"] = float(mine["cd_fore_rmse_vs_truth"].mean())

    # -- hold-out: how good is "truth" where each arm makes its claims? -----------------------
    holdout = pd.DataFrame()
    if int(cfg["holdout"]["cases_per_arm"]) > 0:
        picks = _holdout_picks(ctx, truth_surface, frame, truth, arms)
        for f in [ctx.cases.submit(p["request"], purpose="holdout") for p in picks]:
            f.result()
        cases = pd.read_csv(cases_path) if cases_path.exists() else cases
        holdout = holdout_table(cases, truth_surface, picks)
        holdout.to_csv(ctx.out_dir / "holdout.csv", index=False)

    case_wall = cases["wall_time_s"].astype(float) if len(cases) else pd.Series(dtype=float)
    return {
        "objectives": list(objectives), "active": list(ctx.space.active),
        "hypervolume": ctx.hv_cfg, "arms": table,
        "arm_settings": {arm: cfg["arms"][arm] for arm in arms},
        "budget_evaluations": budget, "cfd_budget_calls": int(cfg["cfd_budget_calls"]),
        "seeds": [int(s) for s in cfg["seeds"]], "checkpoints": checkpoints.tolist(),
        "policy_declared": cfg["policy"], "criteria_declared": crit, "h2": h2,
        "final_hv_comparison": compare_final(
            table, crit["subject"], [a for a in arms if a != crit["subject"]]),
        "truth": {
            "n_train": int(len(truth_surface.table)),
            "n_base": int(len(ctx.base_surface.table)),
            "n_promotion_points": int(len(truth_surface.table) - len(ctx.base_surface.table)),
            "training_hash": truth_surface.meta["training_hash"],
            "base_training_hash": ctx.base_surface.meta["training_hash"],
            "hv_reference": hv_reference, "hv_union_of_arms": hv_arms_union,
            "hv_reference_search_alone": hv_reference_search,
            "n_reference_front": int(len(reference_front_ids)),
            "n_distinct_designs_scored": int(len(truth)),
            "reference_search": cfg["reference"]},
        "cfd": {
            "backend": ctx.cases.backend.name, "fingerprint": ctx.cases.backend.fingerprint,
            "max_concurrent": ctx.cases.max_concurrent,
            "peak_concurrency_observed": ctx.cases.peak_concurrency,
            "n_cases_run": int(ctx.cases.n_run), "n_calls_charged": int(len(calls)),
            "n_cases_in_store": int(len(cases)),
            "n_cases_usable": int(cases["usable"].astype(bool).sum()) if len(cases) else 0,
            "n_cases_imported": int(cases["source"].astype(str).str.startswith("imported").sum())
            if len(cases) else 0,
            "case_wall_s_sum": float(case_wall.sum()) if len(case_wall) else 0.0,
            "case_wall_s_median": float(case_wall.median()) if len(case_wall) else None},
        "holdout": holdout.drop(columns=["request"], errors="ignore").to_dict("records"),
        "surface_error": errors.to_dict("records"),
        "llm_calls_total": int(sum(c.get("llm_calls", 0) for c in counters.values())),
        "wall_s_by_arm_seed": {k: c["wall_s"] for k, c in counters.items()},
    }
