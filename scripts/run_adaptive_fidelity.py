#!/usr/bin/env python3
"""Milestone M6: adaptive-fidelity optimisation (spec section 26, hypothesis H2).

    python scripts/run_adaptive_fidelity.py                      THE STUDY: hours, OpenFOAM,
                                                                 refuses unless gate G4 is PASS
    python scripts/run_adaptive_fidelity.py --report-only RUN_ID rebuild figures + report only
    python scripts/run_adaptive_fidelity.py --config configs/adaptive_fidelity_smoke.yaml
                                                                 smoke: 1 seed, 2 real CFD calls
    python scripts/run_adaptive_fidelity.py --config configs/adaptive_fidelity_dryrun.yaml --fake-f1
                                                                 whole pipeline, FAKE analytic F1

Thin CLI: the policy is src/aether/optimization/adaptive.py, the scoring is
adaptive_analysis.py, the orchestration adaptive_study.py. Only `mode: study` with the real
OpenFOAM backend publishes to reports/; everything else documents itself inside its own run
directory under a banner.

Guards (shared with M5, src/aether/optimization/guards.py): the evaluator source hash is
recorded at launch and re-checked after every logged batch (NR-18), and in study mode the
active variables come ONLY from a DOE screening that is current for the design space AND was
made with the CFD drag surface. CFD cases finished by an aborted run can be reused with
`--reuse-cfd RUN_ID` (each arm is still charged for them).

Writes results/M6/<run_id>/: candidates.csv, cfd_calls.csv (the ledgers), cfd_cases.csv (every
case run), cfd/ (OpenFOAM case results), surfaces/<arm>/seed_<n>/v###/, promotion_log.json,
truth/, truth.csv, curves.csv, surface_error.csv, holdout.csv, summary.json, config_snapshot.yaml.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.optimization.adaptive import (  # noqa: E402
    AnalyticF1Backend,
    CfdCaseStore,
    OpenFoamF1Backend,
    dry_run_truth,
    forebody_validity,
    load_base_surface,
    require_f1_gate,
)
from src.aether.optimization.adaptive_plots import (  # noqa: E402
    plot_adaptive_figures,
    reference_shape_frame,
)
from src.aether.optimization.adaptive_report import write_m6_report  # noqa: E402
from src.aether.optimization.adaptive_study import (  # noqa: E402
    LLM_SEARCH,
    StudyContext,
    run_arms,
    score_study,
)
from src.aether.optimization.ai_agent import (  # noqa: E402
    CallBudget,
    ClaudeCLIClient,
    ReplayClient,
)
from src.aether.optimization.design_space import DesignSpace, _deep_update  # noqa: E402
from src.aether.optimization.guards import (  # noqa: E402
    GuardedStore,
    SourceGuard,
    StaleScreening,
    latest_run,
    load_current_screening,
)
from src.aether.utils.run import (  # noqa: E402
    RunMeta,
    config_hash,
    load_config,
    new_run_id,
    snapshot_config,
)

PREFIX = {"study": "M6-AF", "smoke": "M6-SMOKE", "dry-run": "M6-DRY"}


def load_m6_config(path: Path) -> dict:
    cfg = load_config(path)
    if "inherit" in cfg:
        base = load_config(ROOT / cfg["inherit"])
        _deep_update(base, cfg.get("overrides") or {})
        cfg = base
    return cfg


def resolve_space(af: dict, study: dict, doe_run: str | None):
    """(space with its active variables, where they came from, doe run id or None)."""
    full = DesignSpace.from_config(study, ROOT)
    model = str(full.base_config["vehicle"].get("aero", {}).get("model", "constant"))
    if af["mode"] == "study":
        if model != af["require_aero_model"]:
            raise SystemExit(
                f"REFUSING TO RUN: configs/design_space.yaml selects vehicle.aero.model "
                f"'{model}', M6 needs '{af['require_aero_model']}'. The study runs on the design "
                "space M4 was optimised on: switch the model there, re-run `make doe` and "
                "`make optimize`, then run M6.")
        doe_dir = (ROOT / "results" / "M4" / doe_run if doe_run
                   else latest_run(ROOT / "results" / "M4", "M4-DOE-*", "screening.json"))
        try:
            screening = load_current_screening(doe_dir, study, full.base_config)
        except StaleScreening as exc:
            raise SystemExit(str(exc)) from exc
        return (full.with_active(screening["active"]),
                f"screening of {screening['doe_run_id']}", screening["doe_run_id"])
    active = af.get("active_variables")
    if not active:
        raise SystemExit("a smoke / dry-run config must declare `active_variables`")
    return full.with_active(active), "DECLARED in the smoke config, not screened", None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="configs/adaptive_fidelity.yaml")
    ap.add_argument("--doe-run", default=None)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--fake-f1", action="store_true",
                    help="DRY RUN: analytic fake Fidelity 1, no OpenFOAM; never published")
    ap.add_argument("--skip-llm-arms", action="store_true")
    ap.add_argument("--replay-llm", default=None, metavar="RUN_ID",
                    help="serve the LLM arms from RUN_ID's recorded responses (no live call)")
    ap.add_argument("--reuse-cfd", nargs="*", default=[], metavar="RUN_ID",
                    help="reuse finished CFD cases of earlier runs (arms are still charged)")
    ap.add_argument("--report-only", default=None, metavar="RUN_ID")
    args = ap.parse_args()
    results = ROOT / "results" / "M6"

    if args.report_only:
        out_dir = results / args.report_only
        summary = json.loads((out_dir / "summary.json").read_text())
        return publish(summary, out_dir)

    cfg = load_m6_config(ROOT / args.config)
    af = copy.deepcopy(cfg["adaptive_fidelity"])
    mode = str(af["mode"])
    if mode not in PREFIX:
        raise SystemExit(f"unknown mode '{mode}'")
    if mode == "study" and af["allow_provisional"]:
        raise SystemExit("REFUSING TO RUN: `allow_provisional: true` is for smoke tests only "
                         "and is not accepted in `mode: study` (spec section 17).")
    if mode == "study" and args.fake_f1:
        raise SystemExit("--fake-f1 is a dry run; use configs/adaptive_fidelity_dryrun.yaml")
    if mode == "dry-run" and not args.fake_f1:
        raise SystemExit("the dry-run config must be run with --fake-f1")

    study = load_config(ROOT / cfg["meta"]["design_space"])
    dp_cfg = load_config(ROOT / cfg["meta"]["design_points_config"])
    space, active_source, doe_run_id = resolve_space(af, study, args.doe_run)
    objectives = tuple(study["objectives"])
    hv = {key: {n: float(v) for n, v in study["optimize"]["hypervolume"][key].items()}
          for key in ("reference_point", "ideal_point")}

    base = load_base_surface(ROOT / af["initial_surface"]["directory"])
    gate = require_f1_gate(base.meta, bool(af["allow_provisional"]))   # raises unless allowed
    level = (str(base.meta["mesh_level"]) if af["f1"]["mesh_level"] == "from_surface"
             else str(af["f1"]["mesh_level"]))
    if level != str(base.meta["mesh_level"]):
        raise SystemExit(f"F1 mesh level '{level}' differs from the surface's "
                         f"'{base.meta['mesh_level']}': mixing them in one GP is not allowed")

    arms = [a for a, s in af["arms"].items() if s.get("enabled", False)
            and not (args.skip_llm_arms and s["search"] == LLM_SEARCH)]
    run_id = new_run_id(PREFIX[mode] + ("-FAKE" if args.fake_f1 and mode != "dry-run" else ""))
    out_dir = results / run_id
    snapshot = {"study": study, "adaptive_fidelity": af, "base": space.base_config,
                "active": list(space.active), "design_points": dp_cfg,
                "base_surface_hash": base.meta["training_hash"]}
    meta = RunMeta(run_id=run_id, config_hash=config_hash(snapshot),
                   notes=f"M6 adaptive fidelity, mode={mode}, fake_f1={args.fake_f1}")
    snapshot_config(snapshot, out_dir, meta)

    if args.fake_f1:
        backend = AnalyticF1Backend(dry_run_truth(base), label="surface x declared perturbation")
        banner = ("DRY RUN - the 'CFD' in this run is a FORMULA (fake analytic Fidelity 1). "
                  "Nothing here is a result.")
    else:
        from src.aether.cfd.runner import openfoam_available, openfoam_version
        if not openfoam_available():
            raise SystemExit("OpenFOAM launcher not found - cannot run Fidelity 1")
        backend = OpenFoamF1Backend(dp_cfg, out_dir / "cfd", ROOT / "cfd" / "generated" / run_id,
                                    level)
        banner = ("" if mode == "study" else
                  f"SMOKE TEST ({openfoam_version()}) - plumbing check only. No number in this "
                  "document is a result, and none may be quoted.")
    cases = CfdCaseStore(out_dir / "cfd_cases.csv", backend,
                         int(af["f1"]["max_concurrent_cases"]))
    for other in args.reuse_cfd:
        n = cases.import_from(results / other / "cfd_cases.csv", other)
        print(f"reused {n} finished CFD cases from {other}", flush=True)

    exclude = tuple(af.get("source_guard_exclude") or ())
    if mode == "study" and exclude:
        raise SystemExit("REFUSING TO RUN: `source_guard_exclude` is not accepted in `mode: "
                         "study` - the study is guarded on the whole source tree (NR-18).")
    guard = SourceGuard(ROOT / "src" / "aether", out_dir, exclude)
    store = GuardedStore(out_dir / "candidates.csv")
    store.after_append = guard.check
    aero_block = {"model": af["require_aero_model"],
                  "allow_provisional": bool(af["allow_provisional"]),
                  "on_extrapolation": "reject"}
    llm = af["llm"]
    study_calls = CallBudget(int(llm["max_llm_calls_study"]))

    def llm_client(arm: str, seed: int):
        sub = Path("llm") / arm / f"seed_{seed}"
        if args.replay_llm:
            return ReplayClient(results / args.replay_llm / sub,
                                max_calls=int(llm["max_llm_calls"]))
        return ClaudeCLIClient(out_dir / sub, model=str(llm["model"]),
                               max_calls=int(llm["max_llm_calls"]),
                               timeout_s=float(llm["timeout_s"]), study_budget=study_calls)

    workers = int(args.workers or af["workers"])
    print(f"AETHER M6 adaptive fidelity  run={run_id}  mode={mode}  F1={backend.name}  "
          f"mesh={level}\ngit={meta.git_commit}{' (dirty)' if meta.git_dirty else ''}  "
          f"source hash={guard.hash_at_launch}  gate G4: built {gate['gate_G4_status_at_build']}"
          f", now {gate['gate_G4_status_now']}  allow_provisional={gate['allow_provisional']}\n"
          f"arms={arms}\nactive variables: {list(space.active)} ({active_source})", flush=True)
    start = time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            ctx = StudyContext(
                run_id=run_id, out_dir=out_dir, space=replace(space), objectives=objectives,
                hv_cfg=hv, cfg=af, base_surface=base, aero_block=aero_block, store=store,
                cases=cases, executor=pool,
                shape_is_valid=forebody_validity(float(dp_cfg["fixed"]["diameter_m"])),
                llm_client=llm_client, check_source=guard.check,
                progress=lambda m: print(m, flush=True))
            counters = run_arms(ctx, arms)
            store.after_append = None
            guard.check("before scoring")
            scored = score_study(ctx, arms, counters)
            guard.check("after scoring")
    finally:
        cases.shutdown()
    store.export_parquet()
    summary = {
        "run_id": run_id, "mode": mode, "banner": banner, "gate": gate, "mesh_level": level,
        "git_commit": meta.git_commit, "git_dirty": meta.git_dirty,
        "config_hash": meta.config_hash, "source_hash": guard.hash_at_launch,
        "source_guard_exclude": list(exclude),
        "doe_run_id": doe_run_id, "active_source": active_source, "workers": workers,
        "fake_f1": bool(args.fake_f1), "reused_cfd_from": list(args.reuse_cfd),
        "replayed_llm_from": args.replay_llm, "wall_s": time.perf_counter() - start, **scored,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    return publish(summary, out_dir)


def publish(summary: dict, out_dir: Path) -> int:
    official = (summary["mode"] == "study" and not summary["fake_f1"]
                and not summary["gate"]["provisional"])
    fig_dir = ROOT / "reports" / "figures" if official else out_dir / "figures"
    report_path = (ROOT / "reports" / "milestones" / "M6_adaptive_fidelity.md" if official
                   else out_dir / "M6_adaptive_fidelity.md")
    calls_path = out_dir / "cfd_calls.csv"
    calls = (pd.read_csv(calls_path) if calls_path.stat().st_size > 2 else pd.DataFrame())
    snap = yaml.safe_load((out_dir / "config_snapshot.yaml").read_text())["config"]
    base = load_base_surface(ROOT / snap["adaptive_fidelity"]["initial_surface"]["directory"])
    shapes = pd.read_csv(out_dir / "reference_front_shapes.csv")
    figures = plot_adaptive_figures(summary, pd.read_csv(out_dir / "curves.csv"), calls,
                                    base.table, reference_shape_frame(shapes.to_dict("records")),
                                    fig_dir)
    companion = ROOT / "reports" / "milestones" / "M6_addendum_posthoc.md"
    addendum = (companion.name if official and companion.exists()
                and summary["run_id"] in companion.read_text() else None)   # never a stale one
    report = write_m6_report(summary, report_path,
                             figure_prefix="../figures" if official else "figures",
                             snapshot=snap, addendum=addendum)
    print()
    for arm, a in summary["arms"].items():
        print(f"  {arm:<12} truth HV {a['hv_truth_mean']:.4f}  belief {a['hv_belief_mean']:.4f}"
              f"  CFD calls {a['cfd_calls_mean']:.1f}  (n = {a['n_seeds']})")
    first = next(iter(summary["h2"].values()))
    print(f"H2 @ {100 * first['fraction']:.0f}%: {first['status']} - {first['verdict']}")
    if summary.get("banner"):
        print(summary["banner"])
    print(f"figures: {[p.name for p in figures]}\nreport -> {report}\nresults -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
