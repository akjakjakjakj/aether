#!/usr/bin/env python3
"""Milestone M5: AI vs conventional optimiser ablation under matched budgets.

    python scripts/run_ai_ablation.py                       live run (makes LLM calls)
    python scripts/run_ai_ablation.py --replay M5-ABL-...   re-run from recorded responses
    python scripts/run_ai_ablation.py --report-only RUN_ID  rebuild summary/figures/report

Every method - LHS floor, NSGA-II, GP/ParEGO Bayesian optimisation, the LLM agent and the
LLM agent with the adaptive-fidelity hook - runs through the same `BudgetedEvaluator`, on
the active variables of the latest M4 DOE, against M4's hypervolume reference point.

LIVE mode shells out to the Claude Code CLI (`claude -p`), which must be installed and
signed in; no API key is read or accepted. Calls are hard-capped per seed and for the
whole study (configs/ai_ablation.yaml). Every prompt and raw response is written under
results/M5/<run_id>/llm/.

REPLAY mode needs no LLM access. It reads an earlier run's config snapshot and recorded
responses, re-runs EVERY evaluation, and checks that the hypervolumes come out the same.
It writes to its own run directory and never overwrites the published report.

Writes (live):
    results/M5/<run_id>/candidates.csv|.parquet   every candidate of every method and seed
    results/M5/<run_id>/llm/<method>/seed_<n>/    prompts, raw responses, calls.jsonl
    results/M5/<run_id>/agent_log.json            rounds, proposals, rejections, fidelity
    results/M5/<run_id>/bo_predictions.jsonl      surrogate predictions made before evaluation
    results/M5/<run_id>/summary.json              every number the report quotes
    results/M5/<run_id>/config_snapshot.yaml
    reports/figures/M5_*.png|.pdf
    reports/milestones/M5_ai_ablation.md

Takes tens of minutes (LLM latency dominates) - run it in the background.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

# One BLAS thread per process: see scripts/run_optimize.py.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")

import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.optimization import (  # noqa: E402
    BudgetedEvaluator,
    CandidateStore,
    feasible_front,
    hypervolume_curve,
    load_candidates,
    normalised_hypervolume,
    run_lhs_search,
    run_nsga2,
)
from src.aether.optimization.ablation import (  # noqa: E402
    LLM_KINDS,
    SourceChanged,
    evaluate_success_criteria,
    gaming_audit,
    method_table,
    score_agent,
    score_prediction_log,
    screening_is_current,
    source_tree_hash,
    static_surrogate_validation,
)
from src.aether.optimization.ablation_plots import plot_ablation_figures  # noqa: E402
from src.aether.optimization.ablation_report import write_m5_report  # noqa: E402
from src.aether.optimization.ai_agent import (  # noqa: E402
    AgentLog,
    CallBudget,
    ClaudeCLIClient,
    ReplayClient,
    run_ai_agent,
)
from src.aether.optimization.bayes import run_bo_parego  # noqa: E402
from src.aether.optimization.design_space import DesignSpace  # noqa: E402
from src.aether.optimization.fidelity import PromotionPolicy  # noqa: E402
from src.aether.utils.run import (  # noqa: E402
    RunMeta,
    config_hash,
    load_config,
    new_run_id,
    snapshot_config,
)


class _LockedStore(CandidateStore):
    """The LLM seeds run in threads; the append-only log gets one writer at a time."""

    def __init__(self, csv_path):
        super().__init__(csv_path)
        self._lock = threading.Lock()
        self.after_append = None     # set to the source-hash guard once the run has started

    def append(self, rows):
        with self._lock:
            super().append(rows)     # what was paid for is logged first, THEN the guard
        if self.after_append is not None:
            self.after_append("after a batch was logged")


def _latest(results: Path, pattern: str, marker: str) -> Path:
    runs = sorted(p for p in results.glob(pattern) if (p / marker).exists())
    if not runs:
        raise SystemExit(f"no run matching {pattern} with a {marker} under {results}")
    return runs[-1]


def _m4_reference(m4_results: Path, objectives, hv_cfg, budget: int, seeds) -> dict:
    """M4's NSGA-II: what 1000 evaluations reach, and - as a determinism check - its
    hypervolume after the first `budget` evaluations on the seeds shared with M5."""
    try:
        run = _latest(m4_results, "M4-OPT-*", "summary.json")
    except SystemExit:
        return {}
    saved = json.loads((run / "summary.json").read_text())
    nsga = saved["methods"].get("nsga2")
    if nsga is None:
        return {}
    out = {"run_id": saved["run_id"], "budget": saved["budget"], "n_seeds": len(saved["seeds"]),
           "nsga2_hv_mean_at_full_budget": nsga["hv_mean"],
           "nsga2_hv_std_at_full_budget": nsga["hv_std"]}
    frame = load_candidates(run / "candidates.csv")
    sub = frame[frame["method"] == "nsga2"]
    out["nsga2_hv_at_m5_budget"] = {
        str(seed): float(hypervolume_curve(sub[sub["seed"] == seed], objectives, hv_cfg,
                                           np.array([budget]))[0])
        for seed in seeds if seed in set(sub["seed"])}
    return out


def _run_one(kind, evaluator, settings, objectives, hv_cfg, *, client=None, agent_log=None,
             prediction_log=None):
    if kind == "lhs_search":
        run_lhs_search(evaluator, settings, objectives, hv_cfg)
    elif kind == "nsga2":
        run_nsga2(evaluator, settings, objectives, hv_cfg)
    elif kind == "bo_parego":
        run_bo_parego(evaluator, settings, objectives, hv_cfg, prediction_log=prediction_log)
    elif kind in LLM_KINDS:
        policy = (PromotionPolicy(settings["promotion_policy"], budget=evaluator.budget)
                  if kind == "ai_adaptive" else None)
        run_ai_agent(evaluator, settings, objectives, hv_cfg, client=client, log=agent_log,
                     policy=policy)
    else:
        raise ValueError(f"unknown method kind '{kind}'")


def summarise(frame, space, study, abl, run_meta, agent_logs, predictions, m4_ref) -> tuple:
    objectives = tuple(study["objectives"])
    hv_cfg = {key: {n: float(v) for n, v in study["optimize"]["hypervolume"][key].items()}
              for key in ("reference_point", "ideal_point")}
    budget, step = int(abl["budget_evaluations"]), int(abl["curve_step"])
    checkpoints = np.arange(step, budget + 1, step)
    methods = [m for m in abl["methods"] if m in set(frame["method"])]
    kinds = {m: abl["methods"][m]["kind"] for m in methods}
    table, curves = method_table(frame, space, objectives, hv_cfg, checkpoints, methods)

    # bo_parego and the agent start from the same seeded initial design: pair them
    paired = tuple(m for m in methods if kinds[m] == "bo_parego")
    criteria = evaluate_success_criteria(curves, checkpoints, table, kinds,
                                         abl["success_criteria"], paired)
    ideal = np.array([hv_cfg["ideal_point"][n] for n in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][n] for n in objectives], dtype=float)
    feas = frame[frame["feasible"]].drop_duplicates("candidate_id")
    if m4_ref.get("nsga2_hv_at_m5_budget") and "nsga2" in table:
        mine = dict(zip(table["nsga2"]["seeds"], table["nsga2"]["hv_final_per_seed"],
                        strict=True))
        diffs = [abs(mine[int(s)] - v) for s, v in m4_ref["nsga2_hv_at_m5_budget"].items()
                 if int(s) in mine]
        m4_ref["max_abs_hv_difference_vs_m5_nsga2"] = max(diffs) if diffs else None

    summary = {
        **run_meta,
        "fidelity": int(frame["fidelity"].max()),
        "objectives": list(objectives), "active": list(space.active),
        "frozen": {v.name: v.reference for v in space.variables if v.name not in space.active},
        "variables": {v.name: {"units": v.units, "lower": v.lower, "upper": v.upper}
                      for v in space.active_variables},
        "budget": budget, "seeds": [int(s) for s in abl["seeds"]],
        "checkpoints": checkpoints.tolist(), "hypervolume": hv_cfg,
        "method_kinds": kinds,
        "method_settings": {m: abl["methods"][m] for m in methods},
        "methods": table,
        "criteria_declared": abl["success_criteria"], "criteria": criteria,
        "surrogate": {
            "static": static_surrogate_validation(frame, space, objectives,
                                                  abl["surrogate_validation"]),
            "prospective": score_prediction_log(predictions, frame)},
        "agent": score_agent(agent_logs, frame, objectives),
        "llm": {**abl["llm"],
                "calls_total": int(sum(len(log["rounds"]) for log in agent_logs.values()))},
        "gaming": gaming_audit(frame, space, objectives, study["optimize"]["exploit_audit"],
                               methods),
        "combined": {"n_front": int(len(feasible_front(frame, objectives))),
                     "hv": normalised_hypervolume(
                         feas[list(objectives)].to_numpy(dtype=float), ideal, ref)},
        "m4_reference": m4_ref,
        "cost": {
            "eval_wall_s_median": float(frame.loc[~frame["cache_hit"], "wall_time_s"].median()),
            "llm_round_wall_s_mean": (float(np.mean(rounds)) if (rounds := [
                e["wall_s"] for log in agent_logs.values() for e in log["rounds"]
                if "wall_s" in e]) else None)},
    }
    return summary, curves, checkpoints


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/ai_ablation.yaml")
    ap.add_argument("--doe-run", default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--replay", default=None, metavar="RUN_ID",
                    help="re-run every evaluation from RUN_ID's recorded LLM responses")
    ap.add_argument("--strict-replay", action="store_true",
                    help="fail if a regenerated prompt differs from the recorded one")
    ap.add_argument("--report-only", default=None, metavar="RUN_ID",
                    help="rebuild summary, figures and report from an existing run's logs")
    args = ap.parse_args()
    if args.replay and args.report_only:
        raise SystemExit("--replay and --report-only are mutually exclusive")

    results = ROOT / "results" / "M5"
    source_dir = results / (args.replay or args.report_only or "")
    if args.replay or args.report_only:
        # the snapshot, not today's config files, is the record of what that run was
        snap = yaml.safe_load((source_dir / "config_snapshot.yaml").read_text())["config"]
        study, abl, screening = snap["study"], snap["ablation"], snap["screening"]
        space = replace(DesignSpace.from_config(study, ROOT), base_config=snap["base"]
                        ).with_active(screening["active"])
    else:
        abl_cfg = load_config(ROOT / args.config)
        abl = abl_cfg["ablation"]
        study = load_config(ROOT / abl_cfg["meta"]["design_space"])
        doe_dir = (ROOT / "results" / "M4" / args.doe_run if args.doe_run
                   else _latest(ROOT / "results" / "M4", "M4-DOE-*", "screening.json"))
        screening = json.loads((doe_dir / "screening.json").read_text())
        full_space = DesignSpace.from_config(study, ROOT)
        doe_snapshot = yaml.safe_load((doe_dir / "config_snapshot.yaml").read_text())["config"]
        stale = screening_is_current(doe_snapshot, study, full_space.base_config)
        if stale:
            raise SystemExit(
                f"REFUSING TO RUN: the screening of DOE run {doe_dir.name} is void for the "
                "current design space:\n  - " + "\n  - ".join(stale) + "\nThe active-variable "
                "list is a property of the model it was screened on. Re-run `make doe` (and "
                "`make optimize`) first, or pin a current DOE run with DOE_RUN=...")
        # the ONLY source of the active-variable list: whatever the screening activated
        space = full_space.with_active(screening["active"])
    objectives = tuple(study["objectives"])
    hv_cfg = study["optimize"]["hypervolume"]
    hv_float = {key: {n: float(v) for n, v in hv_cfg[key].items()}
                for key in ("reference_point", "ideal_point")}

    if args.report_only:
        run_id, out_dir = args.report_only, source_dir
        saved = json.loads((out_dir / "summary.json").read_text())
        run_meta = {k: saved.get(k) for k in ("run_id", "replay_of", "doe_run_id", "git_commit",
                                          "git_dirty", "config_hash", "aero_model",
                                          "workers", "wall_s", "source_hash", "replay_check")}
    else:
        run_id = new_run_id("M5-REPLAY" if args.replay else "M5-ABL")
        out_dir = results / run_id
        snapshot = {"study": study, "ablation": abl, "base": space.base_config,
                    "screening": screening}
        meta = RunMeta(run_id=run_id, config_hash=config_hash(snapshot),
                       notes=(f"M5 replay of {args.replay}" if args.replay
                              else "M5 AI ablation, live LLM calls"))
        snapshot_config(snapshot, out_dir, meta)
        store = _LockedStore(out_dir / "candidates.csv")
        workers = int(args.workers or abl["workers"])
        llm = abl["llm"]
        study_calls = CallBudget(int(llm["max_llm_calls_study"]))
        mode = f"REPLAY of {args.replay}" if args.replay else "LIVE"
        print(f"AETHER M5 ablation  run={run_id}  mode={mode}"
              f"  git={meta.git_commit}{' (dirty)' if meta.git_dirty else ''}  "
              f"workers={workers}\nactive variables: {list(space.active)}", flush=True)

        source_hash = source_tree_hash(ROOT / "src" / "aether")
        print(f"evaluator source hash at launch: {source_hash}", flush=True)

        def check_source(where: str) -> None:
            now = source_tree_hash(ROOT / "src" / "aether")
            if now == source_hash:
                return
            message = (f"ABORTED {where}: src/aether changed while the study was running "
                       f"(hash {source_hash} at launch, {now} now). Worker processes may "
                       "already hold either version, so this run's candidates are not one "
                       "experiment. Do not analyse this directory. See NR-18.")
            (out_dir / "ABORTED.md").write_text("# ABORTED RUN - DO NOT ANALYSE\n\n"
                                                + message + "\n")
            raise SourceChanged(message)

        store.after_append = check_source   # every batch, so a 45-minute LLM seed is covered

        wall: dict[str, list[float]] = {}
        agent_logs: dict[str, AgentLog] = {}
        predictions: list[dict] = []
        replay_mismatches = 0
        with ProcessPoolExecutor(max_workers=workers) as pool:

            def job(method: str, seed: int) -> tuple[str, int, float, int]:
                settings = abl["methods"][method]
                kind = settings["kind"]
                check_source(f"before {method} seed {seed}")
                evaluator = BudgetedEvaluator(space, int(abl["budget_evaluations"]), store,
                                              run_id=run_id, method=method, seed=int(seed),
                                              executor=pool)
                client = None
                if kind in LLM_KINDS:
                    sub = Path("llm") / method / f"seed_{seed}"
                    client = (ReplayClient(source_dir / sub,
                                           max_calls=int(llm["max_llm_calls"]),
                                           strict=args.strict_replay)
                              if args.replay else
                              ClaudeCLIClient(out_dir / sub, model=str(llm["model"]),
                                              max_calls=int(llm["max_llm_calls"]),
                                              timeout_s=float(llm["timeout_s"]),
                                              study_budget=study_calls))
                start = time.perf_counter()
                _run_one(kind, evaluator, settings, objectives, hv_float, client=client,
                         agent_log=agent_logs.get(method), prediction_log=predictions)
                elapsed = time.perf_counter() - start
                check_source(f"after {method} seed {seed}")
                print(f"  {method:<12} seed {seed:>3}: spent {evaluator.used} of "
                      f"{evaluator.budget}, {evaluator.n_cache_hits} cache hits, "
                      f"{client.calls_made if client else 0} LLM calls, {elapsed:.0f} s",
                      flush=True)
                return (method, int(seed), elapsed,
                        getattr(client, "prompt_mismatches", 0))

            for method, settings in abl["methods"].items():
                if not settings.get("enabled", False):
                    continue
                seeds = settings.get("seeds", abl["seeds"])
                if settings["kind"] in LLM_KINDS:
                    agent_logs[method] = AgentLog()
                    with ThreadPoolExecutor(max_workers=int(llm["concurrency"])) as threads:
                        done = list(threads.map(lambda s, m=method: job(m, s), seeds))
                else:
                    done = [job(method, seed) for seed in seeds]
                wall[method] = [d[2] for d in done]
                replay_mismatches += sum(d[3] for d in done)
        store.export_parquet()
        logs = {m: log.to_dict() for m, log in agent_logs.items()}
        (out_dir / "agent_log.json").write_text(json.dumps(logs, indent=1, default=float))
        with open(out_dir / "bo_predictions.jsonl", "w") as fh:
            fh.writelines(json.dumps(rec) + "\n" for rec in predictions)
        run_meta = {
            "run_id": run_id, "replay_of": args.replay, "doe_run_id": screening["doe_run_id"],
            "git_commit": meta.git_commit, "git_dirty": meta.git_dirty,
            "config_hash": meta.config_hash, "workers": workers, "wall_s": wall,
            "aero_model": space.base_config["vehicle"]["aero"]["model"],
            "source_hash": source_hash,
            "replay_check": None,
        }
        if args.replay:
            run_meta["replay_check"] = {"prompt_mismatches": replay_mismatches}

    frame = load_candidates(out_dir / "candidates.csv")
    agent_logs_d = json.loads((out_dir / "agent_log.json").read_text())
    predictions_d = [json.loads(line) for line in
                     (out_dir / "bo_predictions.jsonl").read_text().splitlines() if line]
    m4_ref = _m4_reference(ROOT / "results" / "M4", objectives, hv_float,
                           int(abl["budget_evaluations"]), [int(s) for s in abl["seeds"]])
    summary, curves, checkpoints = summarise(frame, space, study, abl, run_meta, agent_logs_d,
                                             predictions_d, m4_ref)
    if summary.get("replay_of"):
        original = json.loads((results / summary["replay_of"] / "summary.json").read_text())
        same = {m: bool(np.allclose(summary["methods"][m]["hv_final_per_seed"],
                                    original["methods"][m]["hv_final_per_seed"],
                                    rtol=0.0, atol=1e-12))
                for m in summary["methods"] if m in original["methods"]}
        summary["replay_check"] = {**(summary.get("replay_check") or {}),
                                   "source_hash_original": original.get("source_hash"),
                                   "source_hash_matches_original":
                                       original.get("source_hash") == summary.get("source_hash"),
                                   "hv_per_seed_identical": same,
                                   "all_identical": all(same.values())}
    with open(out_dir / "summary.json", "w") as fh:
        json.dump(summary, fh, indent=2, default=float)

    # a replay documents itself inside its own run directory; only a live run (or a
    # report-only rebuild of one) publishes to reports/
    publish = not summary.get("replay_of")
    fig_dir = ROOT / "reports" / "figures" if publish else out_dir / "figures"
    report_path = (ROOT / "reports" / "milestones" / "M5_ai_ablation.md" if publish
                   else out_dir / "M5_ai_ablation.md")
    figures = plot_ablation_figures(summary, frame, curves, checkpoints, fig_dir)
    report = write_m5_report(ROOT, summary, report_path, figure_prefix=(
        "../figures" if publish else "figures"))

    print()
    for method, m in summary["methods"].items():
        print(f"  {method:<12} HV = {m['hv_mean']:.4f} +/- {m['hv_std']:.4f} "
              f"[{m['hv_min']:.4f}, {m['hv_max']:.4f}]  (n = {m['n_seeds']})")
    for n_eval, cell in summary["criteria"].get("checkpoints", {}).items():
        print(f"  @{n_eval}: ai_agent vs {cell['comparator']}: diff {cell['mean_difference']:+.4f}"
              f", A12 {cell['a12']:.2f} -> {cell['verdict']}")
    print(f"LLM calls: {summary['llm']['calls_total']}")
    if summary.get("replay_check"):
        print(f"replay check: {summary['replay_check']}")
    print(f"figures: {[p.name for p in figures]}\nreport -> {report}\nresults -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
