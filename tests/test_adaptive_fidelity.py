"""M6 adaptive fidelity: policy logic, exact budget accounting, hull extension, pooled-truth
scoring and the H2 rule - all deterministic, with NO OpenFOAM and NO LLM.

The fake world
--------------
  true drag      `true_cd(mach, shape)`: a known analytic function.
  F1             `AnalyticF1Backend(true_cd)`, with a declared failure region where needed.
  starting surface  a real `CfdDragSurface` fitted through `true_cd` on a SUB-BOX of the shape
                 space, so the rest of the box is genuinely outside its hull.
  F0             `fake_evaluate`: loads whatever surface the config points at (exactly as
                 `evaluate_design` does, extrapolation guard included) and turns its C_D at the
                 top Mach into two competing objectives. No trajectory, no TPS: milliseconds.

One test (`test_real_evaluator_sees_a_refit`) puts the real `evaluate_design` behind the same
machinery. The real OpenFOAM path is exercised by `make adaptive-smoke`, not by pytest.
"""

import json
import math
import stat
import sys
import textwrap

import numpy as np
import pandas as pd
import pytest

from src.aether.aerodynamics.cfd_surface import (
    SHAPE_INPUTS,
    CfdDragSurface,
    GateNotPassedError,
    shape_of,
)
from src.aether.optimization import CandidateStore, load_design_space
from src.aether.optimization.adaptive import (
    AnalyticF1Backend,
    ArmSurface,
    CfdBudgetExhausted,
    CfdCaseStore,
    CfdLedger,
    CfdRequest,
    PromotionController,
    PromotionLog,
    TwoFidelityEvaluator,
    require_f1_gate,
)
from src.aether.optimization.adaptive_analysis import (
    arm_seed_curve,
    calls_to_target,
    h2_verdict,
    pooled_training_table,
)
from src.aether.optimization.adaptive_study import StudyContext, run_arms, score_study
from src.aether.optimization.ai_agent import CallBudget, ClaudeCLIClient, ReplayClient
from src.aether.optimization.budget import (
    DIAGNOSTIC_NAMES,
    MARGIN_NAMES,
    METRIC_NAMES,
    BudgetExhausted,
)
from src.aether.optimization.guards import GuardedStore, SourceChanged, SourceGuard
from src.aether.surrogate.gp import ExtrapolationError
from src.aether.utils.run import REPO_ROOT, load_config

CONFIG = REPO_ROOT / "configs" / "design_space.yaml"
ACTIVE = ["diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg"]
OBJECTIVES = ("peak_heat_flux_w_m2", "peak_bondline_temperature_k")
RANGES = {"mach": [3.0, 20.0], "bluntness_ratio": [0.25, 1.35],
          "cone_half_angle_deg": [20.0, 70.0], "shoulder_ratio": [0.02, 0.10]}
SUB_BOX = {"bluntness_ratio": (0.25, 0.85), "cone_half_angle_deg": (20.0, 50.0),
           "shoulder_ratio": (0.02, 0.10)}


def true_cd(mach: float, shape: dict[str, float]) -> float:
    """The fake world's TRUE forebody drag: rises with cone angle and bluntness."""
    return (0.4 + 0.012 * (shape["cone_half_angle_deg"] - 20.0)
            + 0.35 * shape["bluntness_ratio"] ** 2 + 0.02 * math.log(mach / 3.0)
            + 0.5 * shape["shoulder_ratio"])


def _base_surface(bias: float = 0.0) -> CfdDragSurface:
    """Fitted through `true_cd` (+ an optional bias that makes it WRONG) on SUB_BOX only."""
    rows, k = [], 0
    corners = [(b, c, s) for b in SUB_BOX["bluntness_ratio"]
               for c in SUB_BOX["cone_half_angle_deg"] for s in SUB_BOX["shoulder_ratio"]]
    rng = np.random.default_rng(5)
    fill = [tuple(lo + rng.random() * (hi - lo) for lo, hi in SUB_BOX.values())
            for _ in range(10)]
    for b, c, s in corners + fill:
        for mach in (3.0, 20.0):
            shape = {"bluntness_ratio": b, "cone_half_angle_deg": c, "shoulder_ratio": s}
            rows.append({"point_id": f"dp{k:03d}", "role": "anchor", "split": "train",
                         "mach": mach, **shape, "cd_fore": true_cd(mach, shape) + bias * b})
            k += 1
    meta = {"model": "cfd_surface_v1", "gate_G4_status_at_build": "IN_PROGRESS", "seed": 0,
            "mesh_level": "coarse", "input_ranges": RANGES, "sigma_inflation": 1.0,
            "model_form_rel_halfband": 0.05, "base_drag": {}}
    surface = CfdDragSurface(pd.DataFrame(rows), meta)
    surface.meta["kernel_theta"] = surface.gp.kernel_theta.tolist()
    surface.meta["training_hash"] = "base"
    return surface


def fake_evaluate(payload):
    """F0 of the fake world. Same contract as `budget.evaluate_candidate`."""
    config, _cid = payload
    geom, aero = config["vehicle"]["geometry"], config["vehicle"]["aero"]
    d = float(geom["diameter_m"])
    shape = {"bluntness_ratio": float(geom["nose_radius_m"]) / d,
             "cone_half_angle_deg": float(geom["cone_half_angle_deg"]),
             "shoulder_ratio": float(geom["shoulder_radius_m"]) / d}
    nan = float("nan")
    row = {name: nan for name in METRIC_NAMES}
    row.update({f"margin__{n}": nan for n in MARGIN_NAMES})
    row.update({f"diag__{n}": nan for n in DIAGNOSTIC_NAMES})
    row.update({"feasible": False, "failure_reason": "", "violated_constraints": [],
                "termination": "fake", "status": "OK", "fidelity": 1, "wall_time_s": 0.0})
    surface = CfdDragSurface.load(__import__("pathlib").Path(aero["surface_dir"]))
    flag = aero.get("on_extrapolation", "reject") == "flag"
    try:
        model = surface.cd_model(shape, on_extrapolation="flag" if flag else "raise",
                                 z_gp=float((aero.get("uncertainty") or {}).get("z_gp", 0.0)))
    except ExtrapolationError as exc:
        row.update(status=f"aero surface extrapolation: {exc}", failure_reason="hull")
        return row
    cd = float(model.cd_fore[-1] + (model.cd_total[-1] - model.cd_fore[-1] - model.cd_base[-1]))
    gamma = abs(float(config["entry"]["flight_path_angle_deg"]))
    row["peak_heat_flux_w_m2"] = 2.4e6 * math.sqrt(gamma / 8.0) / math.sqrt(cd * d)
    row["peak_bondline_temperature_k"] = 330.0 + 90.0 * math.sqrt(1.5 / gamma) / (1.0 + cd)
    row["max_g"] = 3.0 + gamma
    row["margin__max_g"] = (12.0 - row["max_g"]) / 12.0
    row["feasible"] = row["margin__max_g"] >= 0.0
    return row


def _space_and_hv():
    space, cfg = load_design_space(CONFIG)
    hv = {key: {n: float(v) for n, v in cfg["optimize"]["hypervolume"][key].items()}
          for key in ("reference_point", "ideal_point")}
    return space.with_active(ACTIVE), hv


def _policy(**overrides):
    policy = load_config(REPO_ROOT / "configs" / "adaptive_fidelity.yaml")[
        "adaptive_fidelity"]["policy"]
    policy.update(overrides)
    return policy


AERO = {"model": "cfd_surface_v1", "allow_provisional": True, "on_extrapolation": "reject"}


def _rig(tmp_path, strategy, *, cfd_budget=4, budget=60, backend=None, base=None, policy=None,
         seed=3, planned=3):
    space, hv = _space_and_hv()
    base = base or _base_surface()
    backend = backend or AnalyticF1Backend(true_cd)
    cases = CfdCaseStore(tmp_path / "cfd_cases.csv", backend, 3)
    surface = ArmSurface(tmp_path / "surfaces" / strategy, base, arm=strategy, seed=seed)
    ledger = CfdLedger(cfd_budget, strategy, seed)
    ev = TwoFidelityEvaluator(space, budget, CandidateStore(tmp_path / f"{strategy}.csv"),
                              run_id="T", method=strategy, seed=seed, arm_surface=surface,
                              ledger=ledger, aero_block=AERO, evaluate_fn=fake_evaluate)
    log = PromotionLog()
    ctl = PromotionController(strategy, policy or _policy(), evaluator=ev, cases=cases,
                              objectives=OBJECTIVES, hv_cfg=hv, log=log, planned_batches=planned)
    ev.on_batch = ctl.after_batch
    return ev, ctl, ledger, surface, cases, log, backend


def _x(space, **values):
    ref = {v.name: v.reference for v in space.active_variables}
    ref.update(values)
    return np.array([[ref[name] for name in space.active]])


# -- gate --------------------------------------------------------------------------------------
def test_f1_refuses_to_run_while_gate_g4_is_not_pass():
    meta = {"gate_G4_status_at_build": "IN_PROGRESS"}
    with pytest.raises(GateNotPassedError, match="section 17"):
        require_f1_gate(meta, allow_provisional=False)
    record = require_f1_gate(meta, allow_provisional=True)
    assert record["provisional"] is True and record["allow_provisional"] is True


def test_study_config_does_not_allow_provisional_and_declares_its_criterion():
    af = load_config(REPO_ROOT / "configs" / "adaptive_fidelity.yaml")["adaptive_fidelity"]
    assert af["mode"] == "study" and af["allow_provisional"] is False
    assert af["f1"]["max_concurrent_cases"] <= 3
    crit = af["success_criteria"]
    assert crit["subject"] == "adaptive" and crit["no_cfd_arm"] == "f0_only"
    assert set(crit["comparators"]) == {"random", "greedy", "upfront"}
    assert 11 not in af["seeds"]                      # the development seed is never a study seed
    smoke = load_config(REPO_ROOT / "configs" / "adaptive_fidelity_smoke.yaml")["overrides"]
    assert smoke["adaptive_fidelity"]["f1"]["max_concurrent_cases"] == 1


# -- CFD accounting ----------------------------------------------------------------------------
def test_ledger_charges_each_distinct_case_once_and_failed_cases_still_cost():
    ledger = CfdLedger(2, "arm", 1)
    a = CfdRequest.of(20.0, {"bluntness_ratio": 0.5, "cone_half_angle_deg": 30.0,
                             "shoulder_ratio": 0.05})
    b = CfdRequest.of(3.0, a.shape)
    assert ledger.charge(a, trigger="t", candidate_id="C", evaluations_used=5) is True
    assert ledger.charge(a, trigger="t", candidate_id="C", evaluations_used=6) is False
    assert (ledger.used, ledger.n_repeat_requests) == (1, 1)          # cached repeat: free
    assert ledger.charge(b, trigger="t", candidate_id="C", evaluations_used=7) is True
    with pytest.raises(CfdBudgetExhausted):
        ledger.charge(CfdRequest.of(12.0, a.shape), trigger="t", candidate_id="C",
                      evaluations_used=8)
    assert ledger.used == 2 == ledger.budget


def test_case_store_runs_a_case_once_even_when_two_arms_ask_and_caps_concurrency(tmp_path):
    backend = AnalyticF1Backend(true_cd)
    store = CfdCaseStore(tmp_path / "cases.csv", backend, 2)
    shape = {"bluntness_ratio": 0.5, "cone_half_angle_deg": 30.0, "shoulder_ratio": 0.05}
    requests = [CfdRequest.of(m, shape) for m in (20.0, 12.0, 6.0, 3.0)]
    futures = [store.submit(r) for r in requests] + [store.submit(requests[0])]
    outcomes = [f.result() for f in futures]
    store.shutdown()
    assert outcomes[0] is outcomes[-1] and len(backend.calls) == 4
    assert store.peak_concurrency <= 2 and store.n_run == 4
    assert len(pd.read_csv(tmp_path / "cases.csv")) == 4

    again = CfdCaseStore(tmp_path / "cases2.csv", AnalyticF1Backend(true_cd), 1)
    assert again.import_from(tmp_path / "cases.csv", "earlier") == 4
    reused = again.submit(requests[1]).result()
    again.shutdown()
    assert reused.source == "imported:earlier" and again.n_run == 0

    other = CfdCaseStore(tmp_path / "cases3.csv", AnalyticF1Backend(true_cd, label="other"), 1)
    assert other.import_from(tmp_path / "cases.csv", "earlier") == 0   # different backend
    other.shutdown()


def test_a_failed_cfd_case_costs_a_call_is_kept_and_yields_no_training_point(tmp_path):
    backend = AnalyticF1Backend(true_cd, fails=lambda r: r.mach > 10.0)
    ev, ctl, ledger, surface, cases, log, _ = _rig(tmp_path, "greedy", backend=backend,
                                                   cfd_budget=1, planned=1)
    n0 = len(surface.surface.table)
    ev.evaluate(_x(ev.space, bluntness_ratio=0.5, cone_half_angle_deg=30.0))
    cases.shutdown()
    assert ledger.used == 1 and ledger.records[0]["usable"] is False
    assert len(surface.surface.table) == n0 and surface.version == 0
    promo = log.promotions[0]
    assert promo["refitted"] is False and promo["after"] is None and promo["n_usable"] == 0
    assert pd.read_csv(tmp_path / "cfd_cases.csv")["verdict"].tolist() == ["REJECTED"]


# -- evaluations -------------------------------------------------------------------------------
def test_evaluations_and_cfd_calls_are_counted_separately_and_exactly(tmp_path):
    ev, ctl, ledger, surface, cases, log, _ = _rig(tmp_path, "greedy", cfd_budget=1, planned=1)
    x = _x(ev.space, bluntness_ratio=0.5, cone_half_angle_deg=30.0)
    rows = ev.evaluate(x)
    cases.shutdown()
    # 1 search evaluation + 1 charged re-evaluation under the refitted surface; 1 CFD call
    assert (ev.used, ev.n_reevaluations, ledger.used, surface.version) == (2, 1, 1, 1)
    assert rows[0]["eval_kind"] == "reeval" and rows[0]["surface_version"] == 1
    assert rows[0]["cfd_calls_used"] == 1
    promo = log.promotions[0]
    assert promo["refitted"] and promo["after"] is not None
    assert promo["surface_version_before"] == 0 and promo["surface_version_after"] == 1
    # same design, same surface version: a cache hit, free
    again = ev.evaluate(x)
    assert again[0]["cache_hit"] is True and ev.used == 2 and ev.n_cache_hits == 1
    frame = pd.read_csv(tmp_path / "greedy.csv")
    assert frame["budget_index"].tolist() == [1, 2, 2]
    assert frame["surface_version"].tolist() == [0, 1, 1]


def test_probes_are_counted_but_never_logged_or_charged(tmp_path):
    ev, *_rest, cases, _log, _b = _rig(tmp_path, "none")
    rows = ev.evaluate(_x(ev.space, bluntness_ratio=0.5, cone_half_angle_deg=30.0))
    lo, hi = ev.probe([(rows[0], -1.0, False), (rows[0], 1.0, False)])
    cases.shutdown()
    assert (ev.n_probes, ev.used) == (2, 1)
    assert lo["peak_heat_flux_w_m2"] > rows[0]["peak_heat_flux_w_m2"] > hi["peak_heat_flux_w_m2"]
    assert len(pd.read_csv(tmp_path / "none.csv")) == 1


def test_evaluation_budget_is_hard_even_for_re_evaluations(tmp_path):
    ev, _ctl, ledger, _s, cases, log, _ = _rig(tmp_path, "greedy", cfd_budget=1, budget=1,
                                              planned=1)
    with pytest.raises(BudgetExhausted):
        ev.evaluate(_x(ev.space, bluntness_ratio=0.5, cone_half_angle_deg=30.0))
    cases.shutdown()
    assert ev.used == 1 and ledger.used == 1
    assert log.promotions[0]["evaluation_budget_exhausted_during_reevaluation"] is True


# -- hull extension ----------------------------------------------------------------------------
def test_promoting_an_out_of_hull_design_extends_the_hull_and_makes_it_evaluable(tmp_path):
    ev, ctl, ledger, surface, cases, log, backend = _rig(tmp_path, "adaptive", cfd_budget=4)
    outside = {"bluntness_ratio": 1.0, "cone_half_angle_deg": 62.0}
    assert not surface.in_hull({**outside, "shoulder_ratio": 0.10})
    ev.evaluate(np.vstack([_x(ev.space, bluntness_ratio=0.5, cone_half_angle_deg=30.0),
                           _x(ev.space, bluntness_ratio=0.6, cone_half_angle_deg=40.0,
                              flight_path_angle_deg=-6.0)]))
    rows = ev.evaluate(_x(ev.space, **outside))
    cases.shutdown()
    promo = [p for p in log.promotions if p["candidate_id"] == rows[0]["candidate_id"]]
    assert len(promo) == 1 and promo[0]["scores"]["outside_hull"] is True
    assert promo[0]["before"]["status"].startswith("aero surface extrapolation")
    assert promo[0]["after"]["status"] == "OK"                      # no longer a dead end
    assert sorted(o["mach"] for o in promo[0]["cfd"]) == [3.0, 20.0]  # both ends of the range
    assert surface.in_hull({**outside, "shoulder_ratio": 0.10})
    assert rows[0]["status"] == "OK" and rows[0]["hull_rejected"] is False
    # the benefit persists: a NEIGHBOUR between the new shape and the old hull is evaluable now
    near = ev.evaluate(_x(ev.space, bluntness_ratio=0.95, cone_half_angle_deg=58.0), kind="x")
    assert near[0]["status"] == "OK"


def test_f0_only_arm_never_promotes_and_an_out_of_hull_design_stays_rejected(tmp_path):
    ev, _ctl, ledger, surface, cases, log, backend = _rig(tmp_path, "none", cfd_budget=0)
    rows = ev.evaluate(_x(ev.space, bluntness_ratio=1.0, cone_half_angle_deg=62.0))
    cases.shutdown()
    assert rows[0]["hull_rejected"] and not rows[0]["feasible"]
    assert ledger.used == 0 and backend.calls == [] and log.promotions == []


# -- the policy --------------------------------------------------------------------------------
def test_policy_keeps_clearly_poor_and_already_trusted_candidates_at_f0(tmp_path):
    ev, ctl, ledger, surface, cases, log, _ = _rig(tmp_path, "adaptive", cfd_budget=4)
    # a strong design ON a training shape (nothing to learn), and one it clearly dominates
    # (lower drag at the same size and entry angle is worse on BOTH fake objectives)
    rows = ev.evaluate(np.vstack([
        _x(ev.space, bluntness_ratio=0.85, cone_half_angle_deg=50.0, diameter_m=4.0),
        _x(ev.space, bluntness_ratio=0.25, cone_half_angle_deg=20.0, diameter_m=4.0)]))
    cases.shutdown()
    assert ledger.used == 0 and all(not d["promoted"] for d in log.decisions)
    by_id = {d["candidate_id"]: d for d in log.decisions}
    strong = by_id[rows[0]["candidate_id"]]
    assert strong["matters"] and not strong["untrusted"]
    assert "already confident" in strong["reason"]
    poor = by_id.get(rows[1]["candidate_id"])          # not even shortlisted, or gated out
    assert poor is None or "clearly poor" in poor["reason"]


def test_agent_request_is_an_input_not_an_override_and_shares_the_cfd_budget(tmp_path):
    ev, ctl, ledger, surface, cases, log, _ = _rig(tmp_path, "adaptive", cfd_budget=1)
    space = ev.space
    x = np.vstack([_x(space, bluntness_ratio=0.5, cone_half_angle_deg=30.0, diameter_m=3.0),
                   _x(space, bluntness_ratio=0.3, cone_half_angle_deg=22.0, diameter_m=0.9,
                      flight_path_angle_deg=-7.9),
                   _x(space, bluntness_ratio=0.33, cone_half_angle_deg=24.0, diameter_m=0.95,
                      flight_path_angle_deg=-7.5)])
    ids = [ev.candidate_id(space.values(row)) for row in x]
    decisions = ctl.decide_batch(x, ids, [0, 1, 1], [], None, space, OBJECTIVES, {})
    assert [d.granted_fidelity for d in decisions] == [0, 0, 0]       # nothing granted up front
    ev.evaluate(x)
    cases.shutdown()
    asked = [d for d in log.decisions if d["agent_requested_fidelity"] == 1]
    assert asked and all(d["matters"] for d in asked)                 # the request opens the gate
    assert ledger.used <= 1                                           # ...but not the budget


def test_scheduled_comparators_spend_their_budget_and_random_is_seeded(tmp_path):
    def run(name, strategy, seed):
        ev, ctl, ledger, _s, cases, log, _ = _rig(tmp_path / name, strategy, cfd_budget=3,
                                                  seed=seed, planned=3)
        rng = np.random.default_rng(1)
        for g in range(4):
            u = 0.15 + 0.3 * rng.random((5, ev.space.n_active))
            ev.evaluate(ev.space.from_unit(u), generation=g)
        cases.shutdown()
        return ledger, log
    led_a, _ = run("a", "random", 3)
    led_b, _ = run("b", "random", 3)
    led_g, log_g = run("g", "greedy", 3)
    assert led_a.used == 3
    assert [r["key"] for r in led_a.records] == [r["key"] for r in led_b.records]
    assert led_g.used == 3 and all(p["trigger"] == "greedy" for p in log_g.promotions)


def test_upfront_arm_spends_everything_before_the_first_evaluation(tmp_path):
    ev, ctl, ledger, surface, cases, log, _ = _rig(tmp_path, "upfront", cfd_budget=5)
    ctl.run_upfront()
    assert (ledger.used, ev.used, surface.version) == (5, 0, 1)
    assert all(r["evaluations_used"] == 0 for r in ledger.records)
    ev.evaluate(_x(ev.space, bluntness_ratio=0.5, cone_half_angle_deg=30.0))
    cases.shutdown()
    assert ledger.used == 5 and len(log.promotions) == 1


# -- pooled truth ------------------------------------------------------------------------------
def _mini_study(tmp_path, base, arms, *, llm_client=None, budget=40, cfd=4, seeds=(3,)):
    space, hv = _space_and_hv()
    af = load_config(REPO_ROOT / "configs" / "adaptive_fidelity.yaml")["adaptive_fidelity"]
    af.update(seeds=list(seeds), budget_evaluations=budget, cfd_budget_calls=cfd, curve_step=10,
              max_parallel_arm_seeds=4)
    af["arms"] = {a: {**af["arms"][a], "population_size": 10, "seeds": list(seeds),
                      "n_initial": 10, "rounds": 3, "max_proposals_per_call": 10}
                  for a in arms}
    af["reference"] = {"seeds": [101], "budget_evaluations": 60, "population_size": 20}
    af["holdout"] = {"cases_per_arm": 1}
    cases = CfdCaseStore(tmp_path / "cfd_cases.csv", AnalyticF1Backend(true_cd), 3)
    ctx = StudyContext(run_id="T", out_dir=tmp_path, space=space, objectives=OBJECTIVES,
                       hv_cfg=hv, cfg=af, base_surface=base, aero_block=AERO,
                       store=GuardedStore(tmp_path / "candidates.csv"), cases=cases,
                       evaluate_fn=fake_evaluate, llm_client=llm_client,
                       progress=lambda m: None)
    counters = run_arms(ctx, list(arms))
    summary = score_study(ctx, list(arms), counters)
    cases.shutdown()
    return summary, ctx


def test_pooled_truth_pools_every_arm_and_excludes_holdout_cases():
    base = _base_surface()
    cases = pd.DataFrame([
        {"point_id": "afA", "mach": 20.0, "bluntness_ratio": 1.0, "cone_half_angle_deg": 60.0,
         "shoulder_ratio": 0.1, "usable": True, "cd_fore": 1.3, "verdict": "USABLE",
         "purpose": "promotion"},
        {"point_id": "afB", "mach": 20.0, "bluntness_ratio": 1.1, "cone_half_angle_deg": 65.0,
         "shoulder_ratio": 0.1, "usable": False, "cd_fore": float("nan"), "verdict": "REJECTED",
         "purpose": "promotion"},
        {"point_id": "afC", "mach": 20.0, "bluntness_ratio": 0.9, "cone_half_angle_deg": 55.0,
         "shoulder_ratio": 0.1, "usable": True, "cd_fore": 1.2, "verdict": "USABLE",
         "purpose": "holdout"}])
    table = pooled_training_table(base.table, cases)
    assert len(table) == len(base.table) + 1 and "afA" in set(table["point_id"])
    assert not {"afB", "afC"} & set(table["point_id"])


def test_a_flattering_surface_cannot_win_it_is_scored_on_pooled_truth(tmp_path):
    """The base surface OVER-predicts drag (bias > 0), so every arm's own belief is rosier
    than truth. The no-CFD arm keeps that flattering surface to the end: its BELIEF
    hypervolume is inflated, its TRUTH hypervolume is not, and the gap is reported."""
    summary, ctx = _mini_study(tmp_path, _base_surface(bias=0.35), ("adaptive", "f0_only"))
    f0, ad = summary["arms"]["f0_only"], summary["arms"]["adaptive"]
    assert f0["cfd_calls_mean"] == 0 and ad["cfd_calls_mean"] > 0
    assert summary["truth"]["n_promotion_points"] > 0
    assert f0["optimism_gap_mean"] > 0.0                       # flattered by its own surface...
    assert f0["hv_truth_mean"] < f0["hv_belief_mean"]          # ...and not paid for it
    assert summary["truth"]["hv_reference"] >= max(f0["hv_truth_mean"], ad["hv_truth_mean"])
    # hull rejection is visible, not silent: what each arm could not see is counted, and
    # re-scored under truth (whose hull contains every arm's)
    assert f0["hull_lost_mean"] > 0 and f0["surface_versions_mean"] == 0
    assert 0 <= f0["hull_lost_truly_feasible_mean"] <= f0["hull_lost_mean"]
    assert ad["surface_versions_mean"] >= 1
    assert (tmp_path / "truth.csv").exists() and (tmp_path / "holdout.csv").exists()
    hold = pd.DataFrame(summary["holdout"])
    assert set(hold["arm"]) <= {"adaptive", "f0_only"} and "z" in hold.columns
    assert "holdout" in set(pd.read_csv(tmp_path / "cfd_cases.csv")["purpose"])
    # every arm-seed curve is a function of what was PAID
    curves = pd.read_csv(tmp_path / "curves.csv")
    assert curves.groupby(["arm", "seed"])["cfd_calls"].apply(
        lambda s: s.is_monotonic_increasing).all()


def test_curve_scores_only_the_recommended_set_and_drops_false_claims():
    space, hv = _space_and_hv()
    rows = [{"candidate_id": c, "eval_index": i + 1, "budget_index": i + 1, "feasible": True,
             "cache_hit": False, "peak_heat_flux_w_m2": f, "peak_bondline_temperature_k": t}
            for i, (c, f, t) in enumerate([("A", 1.0e6, 400.0), ("B", 1.5e6, 380.0),
                                           ("C", 2.0e6, 440.0)])]
    truth = pd.DataFrame([
        {"candidate_id": "A", "truth__feasible": False, "truth__peak_heat_flux_w_m2": 1.0e6,
         "truth__peak_bondline_temperature_k": 400.0},            # a FALSE claim
        {"candidate_id": "B", "truth__feasible": True, "truth__peak_heat_flux_w_m2": 1.6e6,
         "truth__peak_bondline_temperature_k": 385.0},
        {"candidate_id": "C", "truth__feasible": True, "truth__peak_heat_flux_w_m2": 0.5e6,
         "truth__peak_bondline_temperature_k": 320.0}])           # LUCK: believed dominated
    calls = pd.DataFrame({"evaluations_used": [2]})
    curve = arm_seed_curve(pd.DataFrame(rows), calls, truth, OBJECTIVES, hv, np.array([1, 3]))
    last = curve.iloc[-1]
    assert (last["n_recommended"], last["n_false_claims"]) == (2, 1)
    only_b = (2.5e6 - 1.6e6) / 2.5e6 * (450.0 - 385.0) / 150.0
    assert last["hv_truth"] == pytest.approx(only_b)             # C's luck earns nothing
    assert last["hv_truth_oracle"] > last["hv_truth"] and last["hv_belief"] > last["hv_truth"]
    assert curve["cfd_calls"].tolist() == [0, 1]
    assert calls_to_target(curve, only_b * 0.99) == {"reached": True, "cfd_calls": 1,
                                                     "n_evaluations": 3}
    assert calls_to_target(curve, 0.99)["reached"] is False


# -- the H2 rule -------------------------------------------------------------------------------
CRITERIA = {"subject": "adaptive", "comparators": ["random", "greedy", "upfront"],
            "no_cfd_arm": "f0_only", "min_seeds_reaching": 3, "alpha": 0.05}


def _reach(calls):
    return [{"reached": c is not None, "cfd_calls": c, "n_evaluations": 10} for c in calls]


def test_h2_rule_supported_contradicted_and_null():
    miss = [None] * 5
    base = {"f0_only": _reach(miss), "greedy": _reach(miss)}
    won = h2_verdict({**base, "adaptive": _reach([2, 2, 3, 2, 3]),
                      "random": _reach([6, 7, 8, 7, None]), "upfront": _reach([8] * 5)},
                     CRITERIA, 8)
    assert won["status"] == "SUPPORTED" and won["best_comparator"] == "random"
    lost = h2_verdict({**base, "adaptive": _reach([7, 8, 8, 7, 8]),
                       "random": _reach([2, 3, 2, 3, 2]), "upfront": _reach([8] * 5)},
                      CRITERIA, 8)
    assert lost["status"] == "CONTRADICTED"
    null = h2_verdict({**base, "adaptive": _reach([4, 6, 5, 7, 3]),
                       "random": _reach([5, 4, 6, 6, 4]), "upfront": _reach([8] * 5)},
                      CRITERIA, 8)
    assert null["status"] == "NO_MEASURED_DIFFERENCE"


def test_an_arm_that_never_promotes_cannot_win_by_looking_cheap():
    """Zero calls only counts if the POOLED-TRUTH target is actually reached; and when the
    no-CFD arm does reach it, the verdict is 'not testable', never 'adaptive saved calls'."""
    everyone = {"random": _reach([5] * 5), "greedy": _reach([5] * 5), "upfront": _reach([8] * 5)}
    idle = h2_verdict({**everyone, "f0_only": _reach([None] * 5),
                       "adaptive": _reach([None] * 5)}, CRITERIA, 8)
    assert idle["status"] == "NOT_SUPPORTED" and idle["median_calls_censored"]["adaptive"] == 9
    free = h2_verdict({**everyone, "f0_only": _reach([0] * 5), "adaptive": _reach([0] * 5)},
                      CRITERIA, 8)
    assert free["status"] == "NOT_TESTABLE"


def test_hull_membership_of_a_boundary_design_does_not_depend_on_the_triangulation():
    """NR-23: a variable frozen AT a box edge arrives as 1 + 2e-16 (ratio -> length -> ratio).
    Adding a training point must never turn such a design into an 'extrapolation'."""
    from src.aether.surrogate.gp import TrainingHull
    rng = np.random.default_rng(0)
    corners = np.array(np.meshgrid(*[[0.0, 1.0]] * 4)).T.reshape(-1, 4)
    query = np.column_stack([rng.random((200, 3)) * 0.98 + 0.01,
                             np.full(200, 1.0 + 2.220446049250313e-16)])
    for n_extra in range(0, 12):
        extra = np.column_stack([rng.random((n_extra, 3)), np.ones(n_extra)])
        hull = TrainingHull(np.vstack([corners, rng.random((20, 4)), extra]))
        assert hull.contains(query).all(), n_extra
    assert not hull.contains(np.array([[0.5, 0.5, 0.5, 1.001]])).any()   # still a real guard


# -- guards, shared with M5 --------------------------------------------------------------------
def test_source_guard_aborts_a_run_after_logging_what_was_paid_for(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "physics.py").write_text("K = 1.0\n")
    guard = SourceGuard(package, tmp_path / "run")
    store = GuardedStore(tmp_path / "run" / "candidates.csv")
    store.after_append = guard.check
    row = {"run_id": "r", "candidate_id": "C-1", "parent_ids": [], "violated_constraints": []}
    store.append([row])
    (package / "physics.py").write_text("K = 2.0\n")
    with pytest.raises(SourceChanged, match="NR-18"):
        store.append([{**row, "candidate_id": "C-2"}])
    assert len(pd.read_csv(tmp_path / "run" / "candidates.csv")) == 2   # logged FIRST
    assert "DO NOT ANALYSE" in (tmp_path / "run" / "ABORTED.md").read_text()


def test_m5_and_m6_runners_share_one_guard_implementation():
    from src.aether.optimization import ablation, guards
    assert ablation.source_tree_hash is guards.source_tree_hash
    assert ablation.screening_is_current is guards.screening_is_current
    for script in ("run_ai_ablation.py", "run_adaptive_fidelity.py"):
        text = (REPO_ROOT / "scripts" / script).read_text()
        assert "SourceGuard(" in text and "load_current_screening(" in text
        assert "def check_source" not in text and "hashlib" not in text


# -- AI + adaptive fidelity, from replay fixtures ----------------------------------------------
FAKE_CLI = textwrap.dedent('''\
    #!{python}
    import json, sys
    data = json.loads(sys.stdin.read().split("DATA:\\n", 1)[1])
    n_round = len(data["your_previous_rounds"])
    rows = [r for r in data["feasible_non_dominated"] + data["most_recent"]
            if r.get("peak_heat_flux_w_m2") is not None] or data["most_recent"]
    quota = data["budget"]["proposals_requested_now"]
    props = [{{"parent_id": rows[0]["id"], "rationale": "fake", "uncertainty": "high",
              "parameter_changes": {{
                  "bluntness_ratio": round(0.80 + 0.03 * i + 0.011 * n_round, 4),
                  "cone_half_angle_deg": round(48.0 + 1.5 * i + n_round, 3)}},
              "reason_to_simulate": "edge of what the drag data covers",
              "expected_outcome": {{"peak_heat_flux_w_m2": 9.0e5,
                                   "peak_bondline_temperature_k": 380.0, "feasible": True}},
              "requested_fidelity": 1 if i < 2 else 0}} for i in range(quota)]
    result = json.dumps({{"observation": "o", "evidence": [rows[0]["id"]], "mechanism": "m",
                         "uncertainty": "u", "proposals": props}})
    print(json.dumps({{"type": "result", "is_error": False, "result": result,
                      "usage": {{"input_tokens": 1, "output_tokens": 1}},
                      "modelUsage": {{"fake-model": {{}}}}, "duration_api_ms": 1,
                      "total_cost_usd": 0.0}}))
''')


def test_ai_adaptive_arm_is_real_and_replays_without_an_llm(tmp_path):
    cli = tmp_path / "fake_claude"
    cli.write_text(FAKE_CLI.format(python=sys.executable))
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
    base = _base_surface()

    def live(arm, seed):
        return ClaudeCLIClient(tmp_path / "rec" / "llm" / arm / f"seed_{seed}", model="fake",
                               max_calls=4, timeout_s=30, study_budget=CallBudget(8),
                               executable=str(cli))

    def replay(arm, seed):
        return ReplayClient(tmp_path / "rec" / "llm" / arm / f"seed_{seed}", max_calls=4,
                            strict=True)

    first, _ = _mini_study(tmp_path / "live", base, ("ai_adaptive",), llm_client=live, cfd=3)
    again, _ = _mini_study(tmp_path / "replay", base, ("ai_adaptive",), llm_client=replay, cfd=3)
    arm = first["arms"]["ai_adaptive"]
    assert 0 < arm["cfd_calls_mean"] <= 3                     # granted for real, same budget cap
    log = json.loads((tmp_path / "live" / "promotion_log.json").read_text())
    assert any(d.get("agent_requested_fidelity") == 1 for d in log["decisions"])
    agent = json.loads((tmp_path / "live" / "agent_log.json").read_text())["ai_adaptive"]
    assert agent["fidelity_decisions"] and first["llm_calls_total"] > 0
    assert again["arms"]["ai_adaptive"]["per_seed"] == arm["per_seed"]   # strict replay
    a = pd.read_csv(tmp_path / "live" / "cfd_calls.csv")["key"].tolist()
    assert a == pd.read_csv(tmp_path / "replay" / "cfd_calls.csv")["key"].tolist()


# -- the real evaluator behind the same machinery ----------------------------------------------
def test_real_evaluator_sees_a_refit(tmp_path):
    """`evaluate_design` itself, on a copy of the project's provisional surface, with the fake
    F1: a promotion changes the surface the canonical evaluator reads, and the promoted
    design's re-evaluation is a new, charged row."""
    from src.aether.aerodynamics.cfd_surface import SURFACE_DIR, load_surface
    from src.aether.geometry import CapsuleGeometry
    from src.aether.optimization.adaptive import dry_run_truth

    if not (SURFACE_DIR / "surface.json").exists():
        pytest.skip("no cfd_surface_v1 on disk")
    base = load_surface(SURFACE_DIR)
    space, hv = _space_and_hv()
    cases = CfdCaseStore(tmp_path / "cases.csv", AnalyticF1Backend(dry_run_truth(base, 0.08)), 1)
    surface = ArmSurface(tmp_path / "s", base, arm="greedy", seed=1)
    assert surface.training_hash == base.meta["training_hash"]      # v000 is the base, bit for bit
    ledger = CfdLedger(1, "greedy", 1)
    ev = TwoFidelityEvaluator(space, 5, CandidateStore(tmp_path / "c.csv"), run_id="T",
                              method="greedy", seed=1, arm_surface=surface, ledger=ledger,
                              aero_block=AERO)
    log = PromotionLog()
    ctl = PromotionController("greedy", _policy(), evaluator=ev, cases=cases,
                              objectives=OBJECTIVES, hv_cfg=hv, log=log, planned_batches=1)
    ev.on_batch = ctl.after_batch
    rows = ev.evaluate(_x(space, diameter_m=3.0, bluntness_ratio=0.6, cone_half_angle_deg=45.0,
                          flight_path_angle_deg=-2.5))
    cases.shutdown()
    assert ledger.used == 1 and surface.version == 1
    assert len(surface.surface.table) == len(base.table) + 1
    promo = log.promotions[0]
    assert promo["refitted"] and promo["after"]["status"] == "OK"
    assert promo["after"]["peak_heat_flux_w_m2"] != promo["before"]["peak_heat_flux_w_m2"]
    assert rows[0]["surface_version"] == 1 and rows[0]["fidelity"] == 1
    geometry = CapsuleGeometry(nose_radius_m=1.8, diameter_m=3.0, shoulder_radius_m=0.3,
                               cone_half_angle_deg=45.0, aft_cone_angle_deg=20.0,
                               length_m=2.625)
    assert shape_of(geometry)["bluntness_ratio"] == pytest.approx(0.6)
    assert set(SHAPE_INPUTS) == set(shape_of(geometry))
