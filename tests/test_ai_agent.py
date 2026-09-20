"""M5 AI agent: strict schema, rejection without clipping, call caps, persistence, replay.

NO TEST HERE MAKES A LIVE LLM CALL. `ClaudeCLIClient` is pointed at a fake executable - a
small script that reads the prompt on stdin and prints a CLI-shaped JSON envelope - so the
subprocess path, the persistence and the replay are exercised end to end offline.
"""

import json
import stat
import sys
import textwrap

import numpy as np
import pytest

from src.aether.optimization import BudgetedEvaluator, CandidateStore, load_design_space
from src.aether.optimization.ablation import (
    a12,
    holm,
    permutation_rank_test,
    signed_rank_test,
)
from src.aether.optimization.ai_agent import (
    AgentLog,
    CallBudget,
    ClaudeCLIClient,
    LLMCallLimit,
    MalformedResponse,
    ReplayClient,
    parse_response,
    run_ai_agent,
    validate_proposals,
)
from src.aether.optimization.fidelity import UNAVAILABLE_REASON, PromotionPolicy
from src.aether.utils.run import REPO_ROOT

CONFIG = REPO_ROOT / "configs" / "design_space.yaml"
SMALL = ["diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg"]
OBJECTIVES = ("peak_heat_flux_w_m2", "peak_bondline_temperature_k")
BOUNDS = {"diameter_m": (0.8, 4.5), "bluntness_ratio": (0.25, 1.35)}
PARENTS = {"C-parent": {"diameter_m": 2.0, "bluntness_ratio": 0.8}}


def _proposal(**overrides):
    base = {"parent_id": "C-parent", "rationale": "larger drag area", "uncertainty": "medium",
            "parameter_changes": {"diameter_m": 2.5}, "reason_to_simulate": "test the trend",
            "expected_outcome": {"peak_heat_flux_w_m2": 3.0e5,
                                 "peak_bondline_temperature_k": 400.0, "feasible": True},
            "requested_fidelity": 0}
    base.update(overrides)
    return base


def _response(proposals):
    return {"observation": "o", "evidence": ["C-parent shows it"], "mechanism": "m",
            "uncertainty": "u", "proposals": proposals}


def _validate(proposals, quota=10, seen=frozenset()):
    return validate_proposals(_response(proposals), bounds=BOUNDS, objectives=OBJECTIVES,
                              parents=PARENTS, seen_keys=set(seen), quota=quota)


# -- parsing ------------------------------------------------------------------------------
def test_parse_accepts_bare_json_and_one_fence_and_nothing_else():
    body = json.dumps(_response([_proposal()]))
    assert parse_response(body)["mechanism"] == "m"
    assert parse_response(f"```json\n{body}\n```")["mechanism"] == "m"
    for bad in (f"Here you go:\n{body}", "[1, 2]", "not json", body[:-1]):
        with pytest.raises(MalformedResponse):
            parse_response(bad)


def test_parse_rejects_missing_and_extra_top_level_fields():
    full = _response([_proposal()])
    missing = {k: v for k, v in full.items() if k != "mechanism"}
    for bad in (missing, {**full, "shell": "rm -rf /"}, {**full, "evidence": []},
                {**full, "observation": ""}, {**full, "proposals": []}):
        with pytest.raises(MalformedResponse):
            parse_response(json.dumps(bad))


# -- proposal validation ------------------------------------------------------------------
def test_a_valid_proposal_inherits_its_parent_and_overrides_only_what_it_changes():
    accepted, rejected = _validate([_proposal()])
    assert not rejected
    assert accepted[0].values == {"diameter_m": 2.5, "bluntness_ratio": 0.8}
    assert accepted[0].parent_id == "C-parent"


@pytest.mark.parametrize(("proposal", "reason"), [
    (_proposal(parameter_changes={"diameter_m": 4.6}), "out_of_bounds"),
    (_proposal(parameter_changes={"bluntness_ratio": 0.2}), "out_of_bounds"),
    (_proposal(parent_id="C-nonexistent"), "unknown_parent"),
    (_proposal(parameter_changes={"mass_kg": 100.0}), "unknown_variable"),
    (_proposal(parameter_changes={"diameter_m": float("nan")}), "non_finite"),
    (_proposal(parameter_changes={"diameter_m": 2.0}), "no_change"),
    (_proposal(parameter_changes={"diameter_m": "2.5"}), "schema"),
    (_proposal(parameter_changes={"diameter_m": True}), "schema"),
    (_proposal(parameter_changes={}), "schema"),
    (_proposal(requested_fidelity=2), "schema"),
    (_proposal(uncertainty="certain"), "schema"),
    (_proposal(expected_outcome={"peak_heat_flux_w_m2": 1.0, "feasible": True}), "schema"),
    ({**_proposal(), "geometry_stl": "free-form"}, "schema"),
    ("just a string", "schema"),
])
def test_bad_proposals_are_rejected_with_a_reason_never_repaired(proposal, reason):
    accepted, rejected = _validate([proposal])
    assert accepted == []
    assert [r["reason"] for r in rejected] == [reason]
    assert rejected[0]["proposal"] == proposal          # logged verbatim for the audit


def test_an_out_of_bounds_value_is_not_clipped_into_the_batch():
    accepted, rejected = _validate([_proposal(parameter_changes={"diameter_m": 9.0}),
                                    _proposal(parameter_changes={"diameter_m": 4.5})])
    assert [p.values["diameter_m"] for p in accepted] == [4.5]   # the honest one, only
    assert rejected[0]["reason"] == "out_of_bounds" and "9" in rejected[0]["detail"]


def test_duplicates_and_over_quota_are_rejected():
    same = _proposal(parameter_changes={"diameter_m": 3.0})
    accepted, rejected = _validate([same, dict(same),
                                    _proposal(parameter_changes={"diameter_m": 3.1}),
                                    _proposal(parameter_changes={"diameter_m": 3.2})],
                                   quota=2, seen={(3.2, 0.8)})
    assert [p.values["diameter_m"] for p in accepted] == [3.0, 3.1]
    assert [r["reason"] for r in rejected] == ["duplicate", "duplicate"]
    accepted, rejected = _validate([_proposal(parameter_changes={"diameter_m": d})
                                    for d in (3.0, 3.1, 3.3)], quota=2)
    assert len(accepted) == 2 and [r["reason"] for r in rejected] == ["over_quota"]


# -- fake CLI, caps, persistence, replay --------------------------------------------------
FAKE_CLI = textwrap.dedent('''\
    #!{python}
    """Stands in for `claude -p`: reads the prompt, answers like the CLI would."""
    import json, os, sys
    prompt = sys.stdin.read()
    data = json.loads(prompt.split("DATA:\\n", 1)[1])
    n_round = len(data["your_previous_rounds"])
    rows = (data["feasible_non_dominated"] + data["nearly_feasible"] + data["most_recent"])
    rows = [r for r in rows if r.get("peak_heat_flux_w_m2") is not None] or data["most_recent"]
    parent = rows[0]
    quota = data["budget"]["proposals_requested_now"]
    def proposal(i, **changes):
        return {{"parent_id": parent["id"], "rationale": "fake", "uncertainty": "high",
                "parameter_changes": changes, "reason_to_simulate": "fake",
                "expected_outcome": {{"peak_heat_flux_w_m2": 2.0e5,
                                     "peak_bondline_temperature_k": 400.0, "feasible": True}},
                "requested_fidelity": i % 2}}
    state = sys.argv[0] + ".state"
    if n_round == 1 and not os.path.exists(state):       # answer badly exactly once
        open(state, "w").write("done")
        result = "Sure! Here are my proposals: {{not json"
    else:
        span = (-1.5) - (-8.0)
        good = [proposal(i, flight_path_angle_deg=round(-7.9 + span * (i + 1 + 10 * n_round)
                                                        / 40.0, 4)) for i in range(quota)]
        if n_round == 0:                       # one out of bounds, one unknown parent
            good[0] = proposal(0, diameter_m=99.0)
            good[1] = {{**proposal(1, diameter_m=2.0), "parent_id": "C-made-up"}}
        result = json.dumps({{"observation": "o", "evidence": [parent["id"]],
                             "mechanism": "fake mechanism", "uncertainty": "u",
                             "proposals": good}})
    print(json.dumps({{"type": "result", "is_error": False, "result": result,
                      "usage": {{"input_tokens": 10, "output_tokens": 20}},
                      "modelUsage": {{"fake-model": {{}}}}, "duration_api_ms": 5,
                      "total_cost_usd": 0.0}}))
''')


@pytest.fixture()
def fake_cli(tmp_path):
    path = tmp_path / "fake_claude"
    path.write_text(FAKE_CLI.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


SETTINGS = {"n_initial": 6, "rounds": 2, "max_proposals_per_call": 10,
            "tables": {"front": 4, "near_feasible": 4, "recent": 6, "failures": 2}}


def _run(tmp_path, name, client, policy=None):
    space, cfg = load_design_space(CONFIG)
    space = space.with_active(SMALL)
    hv = {key: {n: float(v) for n, v in cfg["optimize"]["hypervolume"][key].items()}
          for key in ("reference_point", "ideal_point")}
    store = CandidateStore(tmp_path / f"{name}.csv")
    evaluator = BudgetedEvaluator(space, 14, store, run_id="T", method="ai_agent", seed=11)
    log = AgentLog()
    run_ai_agent(evaluator, SETTINGS, OBJECTIVES, hv, client=client, log=log, policy=policy)
    return evaluator, store.load(), log


def test_agent_run_persists_everything_and_replays_identically(tmp_path, fake_cli):
    llm_dir = tmp_path / "llm"
    live = ClaudeCLIClient(llm_dir, model="fake", max_calls=5, timeout_s=30,
                           study_budget=CallBudget(5), executable=str(fake_cli))
    evaluator, frame, log = _run(tmp_path, "live", live)

    assert evaluator.used == 14                                  # budget matched exactly
    outcomes = [r["outcome"] for r in log.rounds]
    assert outcomes == ["ok", "malformed_response", "ok"]        # the bad answer cost a call
    assert sorted(r["reason"] for r in log.rejections) == ["out_of_bounds", "unknown_parent"]
    assert frame["x__diameter_m"].max() <= 4.5                   # 99 m was never clipped in
    proposed = frame[frame["generation"].between(1, 8000)]
    assert all(len(p) == 1 for p in proposed["parent_ids"])      # every proposal has a parent
    assert set(sum(proposed["parent_ids"], [])) <= set(frame["candidate_id"])
    assert len(log.proposals) == len(proposed)
    assert log.fallback_evaluations == 14 - 6 - len(proposed)    # unfilled budget -> LHS floor

    for n in (1, 2, 3):                                          # verbatim audit trail
        assert (llm_dir / f"call_{n:02d}.prompt.txt").read_text().startswith("Propose exactly")
        assert (llm_dir / f"call_{n:02d}.response.raw").exists()
    assert len((llm_dir / "calls.jsonl").read_text().splitlines()) == 3

    replay = ReplayClient(llm_dir, max_calls=5, strict=True)     # strict: prompts must match
    _, frame2, log2 = _run(tmp_path, "replay", replay)
    assert replay.prompt_mismatches == 0
    volatile = ["wall_time_s"]
    assert frame2.drop(columns=volatile).equals(frame.drop(columns=volatile))
    assert [r["outcome"] for r in log2.rounds] == outcomes
    assert all(r["replayed"] for r in log2.rounds)


def test_call_caps_are_hard(tmp_path, fake_cli):
    client = ClaudeCLIClient(tmp_path / "a", model="fake", max_calls=1, timeout_s=30,
                             study_budget=CallBudget(5), executable=str(fake_cli))
    evaluator, _, log = _run(tmp_path, "capped", client)
    assert client.calls_made == 1 and len(log.rounds) == 1
    assert evaluator.used == 14 and log.fallback_evaluations > 0   # budget still matched

    shared = CallBudget(1)
    first = ClaudeCLIClient(tmp_path / "b", model="fake", max_calls=9, timeout_s=30,
                            study_budget=shared, executable=str(fake_cli))
    second = ClaudeCLIClient(tmp_path / "c", model="fake", max_calls=9, timeout_s=30,
                             study_budget=shared, executable=str(fake_cli))
    first.study_budget.take()
    with pytest.raises(LLMCallLimit, match="study-wide"):
        second.complete("anything")


def test_a_hung_or_missing_cli_is_a_failed_call_not_a_crash(tmp_path):
    slow = tmp_path / "slow"
    slow.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
    slow.chmod(slow.stat().st_mode | stat.S_IEXEC)
    for executable, message in ((str(slow), "timed out"), (str(tmp_path / "absent"), "could not")):
        client = ClaudeCLIClient(tmp_path / f"log_{message[:4]}", model="fake", max_calls=3,
                                 timeout_s=0.5, study_budget=CallBudget(3),
                                 executable=executable)
        result = client.complete("prompt")
        assert result.text is None and message in result.meta["error"]


def test_strict_replay_refuses_a_prompt_that_changed(tmp_path, fake_cli):
    llm_dir = tmp_path / "llm"
    live = ClaudeCLIClient(llm_dir, model="fake", max_calls=1, timeout_s=30,
                           study_budget=CallBudget(1), executable=str(fake_cli))
    prompt = "Propose exactly 1\nDATA:\n" + json.dumps({
        "your_previous_rounds": [], "feasible_non_dominated": [], "nearly_feasible": [],
        "most_recent": [{"id": "C-x", "peak_heat_flux_w_m2": 1.0}],
        "budget": {"proposals_requested_now": 3}})
    assert live.complete(prompt).text is not None
    with pytest.raises(ValueError, match="differs from the recorded"):
        ReplayClient(llm_dir, max_calls=1, strict=True).complete(prompt + " ")
    lenient = ReplayClient(llm_dir, max_calls=1)
    assert lenient.complete(prompt + " ").text is not None and lenient.prompt_mismatches == 1


# -- adaptive-fidelity hook ---------------------------------------------------------------
def test_promotion_policy_requests_but_is_never_granted_without_a_second_fidelity(
        tmp_path, fake_cli):
    policy = PromotionPolicy({"min_predicted_hv_gain": 0.0, "min_uncertainty": 0.0,
                              "min_novelty": 0.0, "max_high_fidelity_fraction": 0.5},
                             budget=14)
    client = ClaudeCLIClient(tmp_path / "llm", model="fake", max_calls=5, timeout_s=30,
                             study_budget=CallBudget(5), executable=str(fake_cli))
    _, frame, log = _run(tmp_path, "adaptive", client, policy=policy)
    assert len(log.fidelity_decisions) == len(log.proposals) > 0
    assert policy.n_granted == 0 and all(d["granted_fidelity"] == 0
                                         for d in log.fidelity_decisions)
    assert (frame["fidelity"] == 0).all()


def test_promotion_policy_promotes_what_matters_and_stops_at_its_cost_cap():
    from src.aether.optimization.budget import MARGIN_NAMES
    from src.aether.surrogate import DesignSurrogate

    space, cfg = load_design_space(CONFIG)
    space = space.with_active(SMALL)
    hv = {key: {n: float(v) for n, v in cfg["optimize"]["hypervolume"][key].items()}
          for key in ("reference_point", "ideal_point")}
    rng = np.random.default_rng(0)
    rows = []
    for _ in range(30):
        u = 0.3 + 0.4 * rng.random(space.n_active)
        x = space.from_unit(u)
        rows.append({**{f"x__{n}": float(v) for n, v in zip(space.active, x, strict=True)},
                     **{f"margin__{n}": float("nan") for n in MARGIN_NAMES},
                     "margin__max_g": 0.5, "cache_hit": False, "status": "OK",
                     "feasible": True, "peak_heat_flux_w_m2": 1.0e6 * (1.5 - u[0]),
                     "peak_bondline_temperature_k": 440.0 - 30.0 * u[3]})
    surrogate = DesignSurrogate(space, OBJECTIVES, seed=0).fit(rows)
    policy = PromotionPolicy({"min_predicted_hv_gain": 1e-4, "min_uncertainty": 0.25,
                              "min_novelty": 0.10, "max_high_fidelity_fraction": 0.01},
                             budget=200)                         # cap: 2 promotions
    better = space.from_unit(np.full((4, space.n_active), 0.95))   # novel, outside the hull
    better[:, 0] -= np.arange(4) * 0.01
    seen = np.array([[rows[0][f"x__{n}"] for n in space.active]])  # nothing new to learn
    decisions = policy.decide_batch(np.vstack([better, seen]), [f"C-{i}" for i in range(5)],
                                    [0, 0, 0, 0, 0], rows, surrogate, space, OBJECTIVES, hv)
    assert [d.policy_fidelity for d in decisions] == [1, 1, 0, 0, 0]
    assert "budget is spent" in decisions[2].reason
    assert decisions[4].novelty == pytest.approx(0.0, abs=1e-9)
    assert all(d.granted_fidelity == 0 for d in decisions)
    assert all(UNAVAILABLE_REASON in d.reason for d in decisions[:2])
    assert policy.n_requested == 2 and policy.n_granted == 0


# -- exact small-sample statistics --------------------------------------------------------
def test_exact_tests_reach_their_known_extreme_values():
    low, high = np.arange(5.0), np.arange(5.0) + 10.0
    rank = permutation_rank_test(high, low)
    assert rank["p_greater"] == pytest.approx(1 / 252)
    assert rank["p_less"] == pytest.approx(1.0)
    assert rank["p_two_sided"] == pytest.approx(2 / 252)
    assert a12(high, low) == 1.0 and a12(low, low) == 0.5
    paired = signed_rank_test(high - low + np.arange(5.0))
    assert paired["p_greater"] == pytest.approx(1 / 32)
    assert paired["p_two_sided"] == pytest.approx(2 / 32)         # can never reach 0.05
    assert signed_rank_test(np.zeros(5))["p_two_sided"] == 1.0


def test_permutation_test_is_exact_with_ties():
    rank = permutation_rank_test(np.zeros(5), np.zeros(5))
    assert rank["p_greater"] == rank["p_less"] == rank["p_two_sided"] == 1.0


def test_holm_matches_a_hand_worked_case():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


# -- provenance guards (NR-18) ------------------------------------------------------------
def test_source_tree_hash_changes_when_any_source_file_changes(tmp_path):
    from src.aether.optimization.ablation import source_tree_hash

    (tmp_path / "pkg" / "sub").mkdir(parents=True)
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n")
    (tmp_path / "pkg" / "sub" / "b.py").write_text("y = 2\n")
    (tmp_path / "pkg" / "notes.txt").write_text("not source")
    first = source_tree_hash(tmp_path / "pkg")
    assert first == source_tree_hash(tmp_path / "pkg")
    (tmp_path / "pkg" / "notes.txt").write_text("still not source")
    assert source_tree_hash(tmp_path / "pkg") == first
    (tmp_path / "pkg" / "sub" / "b.py").write_text("y = 3\n")
    assert source_tree_hash(tmp_path / "pkg") != first


def test_a_screening_made_on_a_different_model_is_reported_as_void():
    from src.aether.optimization.ablation import screening_is_current

    space, study = load_design_space(CONFIG)
    snapshot = {"study": json.loads(json.dumps(study)),
                "base": json.loads(json.dumps(space.base_config))}
    assert screening_is_current(snapshot, study, space.base_config) == []
    snapshot["base"]["vehicle"]["cd"] = 9.9
    snapshot["study"]["variables"]["diameter_m"]["max"] = 9.0
    reasons = screening_is_current(snapshot, study, space.base_config)
    assert len(reasons) == 2 and "variables" in reasons[0]


# -- the whole pipeline, offline: summary -> figures -> report ----------------------------
def test_report_is_generated_from_data_and_asserts_nothing_it_did_not_compute(
        tmp_path, fake_cli):
    import importlib.util

    from src.aether.optimization import run_lhs_search

    spec = importlib.util.spec_from_file_location(
        "run_ai_ablation", REPO_ROOT / "scripts" / "run_ai_ablation.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)

    space, study = load_design_space(CONFIG)
    # the active list comes from wherever the caller got it - here, deliberately NOT the
    # four M4 variables, to prove nothing downstream assumes them
    active = ["diameter_m", "shoulder_ratio", "flight_path_angle_deg"]
    space = space.with_active(active)
    hv = {key: {n: float(v) for n, v in study["optimize"]["hypervolume"][key].items()}
          for key in ("reference_point", "ideal_point")}
    store = CandidateStore(tmp_path / "candidates.csv")
    logs = {"ai_agent": AgentLog()}
    settings = {**SETTINGS, "kind": "ai_agent"}
    del settings["n_initial"]
    settings["n_initial_per_variable"] = 2                      # -> 6 for three variables
    for seed in (3, 5):
        run_lhs_search(BudgetedEvaluator(space, 14, store, run_id="T", method="lhs_search",
                                         seed=seed), {}, OBJECTIVES, hv)
        client = ClaudeCLIClient(tmp_path / f"llm_{seed}", model="fake", max_calls=5,
                                 timeout_s=30, study_budget=CallBudget(9),
                                 executable=str(fake_cli))
        run_ai_agent(BudgetedEvaluator(space, 14, store, run_id="T", method="ai_agent",
                                       seed=seed), settings, OBJECTIVES, hv, client=client,
                     log=logs["ai_agent"])
    frame = store.load()
    assert (frame[frame["method"] == "ai_agent"]["generation"] == 0).sum() == 12

    abl = {"budget_evaluations": 14, "seeds": [3, 5], "curve_step": 7,
           "methods": {"lhs_search": {"kind": "lhs_search"}, "ai_agent": settings},
           "success_criteria": {"subject": "ai_agent", "checkpoints": [7, 14],
                                "min_hv_gain": 0.005, "alpha": 0.05},
           "surrogate_validation": {"train_method": "lhs_search", "transforms": {}},
           "llm": {"model": "fake", "max_llm_calls": 5, "max_llm_calls_study": 9}}
    meta = {"run_id": "T", "replay_of": None, "doe_run_id": "none", "git_commit": "x",
            "git_dirty": False, "config_hash": "x", "workers": 1, "source_hash": "abc",
            "wall_s": {"lhs_search": [1.0, 1.0], "ai_agent": [2.0, 2.0]},
            "aero_model": "constant", "replay_check": None}
    summary, curves, checkpoints = driver.summarise(
        frame, space, study, abl, meta, {m: log.to_dict() for m, log in logs.items()}, [], {})
    assert summary["active"] == active
    json.dumps(summary, default=float)                          # serialisable

    from src.aether.optimization.ablation_plots import plot_ablation_figures
    from src.aether.optimization.ablation_report import write_m5_report

    figures = plot_ablation_figures(summary, frame, curves, checkpoints, tmp_path / "fig")
    assert all(path.exists() for path in figures)
    text = write_m5_report(tmp_path, summary, tmp_path / "report.md").read_text()
    assert "`shoulder_ratio`" in text and "3 active design variables" in text
    assert "1/6 = 0.1667" in text                               # power computed from n = 2
    for stale in ("M4 showed", "two fences", "four active", "n = 5", "1/252"):
        assert stale not in text
    assert "Not yet written for run `T`" in text                # no stale qualitative audit
    verdicts = [c["verdict"] for c in summary["criteria"]["checkpoints"].values()]
    assert verdicts == ["no measured difference"] * 2           # n = 2 cannot reach 0.05
