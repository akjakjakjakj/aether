"""M7 robust optimisation: chance-constraint logic, the optimiser's accounting, and the
verification of the common-random-number shortcut.

The shortcut check is itself checked here: `verify_shortcut` has to PASS when the two
estimates agree and FAIL on each of the three ways it can disagree, or it is a rubber
stamp rather than a verification.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.aether.optimization import BudgetedEvaluator, CandidateStore, load_design_space
from src.aether.uncertainty import (
    RobustScore,
    RobustSettings,
    UncertaintyModel,
    common_random_numbers,
    make_uncertain_space,
    robust_front,
    run_robust_nsga2,
    score_sample,
    verify_shortcut,
)
from src.aether.utils.run import REPO_ROOT

UQ_CONFIG = REPO_ROOT / "configs" / "uncertainty.yaml"
DS_CONFIG = REPO_ROOT / "configs" / "design_space.yaml"
ACTIVE = ["diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg"]
OBJECTIVES = ("peak_heat_flux_w_m2", "peak_bondline_temperature_k")


def settings(**overrides) -> RobustSettings:
    base = {"objective_percentile": 95.0, "quantile_estimator": "empirical",
            "chance_constraints": {"max_g": 0.05, "any": 0.10}, "inner_samples": 20,
            "inner_seed": 1, "population_size": 8, "budget_evaluations": 160,
            "seeds": (37,)}
    base.update(overrides)
    return RobustSettings(
        objective_percentile=base["objective_percentile"],
        quantile_estimator=base["quantile_estimator"],
        chance_alpha=base["chance_constraints"],
        inner_samples=base["inner_samples"], inner_seed=base["inner_seed"],
        population_size=base["population_size"],
        budget_evaluations=base["budget_evaluations"], seeds=tuple(base["seeds"]))


def sample_frame(n: int, *, flux, bondline, g_margin, feasible=None, status=None
                 ) -> pd.DataFrame:
    return pd.DataFrame({
        "peak_heat_flux_w_m2": np.asarray(flux, dtype=float),
        "peak_bondline_temperature_k": np.asarray(bondline, dtype=float),
        "margin__max_g": np.asarray(g_margin, dtype=float),
        "feasible": (np.asarray(feasible, dtype=bool) if feasible is not None
                     else np.asarray(g_margin, dtype=float) >= 0.0),
        "status": (list(status) if status is not None else ["OK"] * n),
    })


# =======================================================================================
# 1. declaring the problem
# =======================================================================================

def test_the_declared_settings_are_validated():
    with pytest.raises(ValueError, match="objective_percentile"):
        settings(objective_percentile=100.0)
    with pytest.raises(ValueError, match="quantile_estimator"):
        settings(quantile_estimator="kernel")
    with pytest.raises(ValueError, match="inner_samples"):
        settings(inner_samples=1)
    with pytest.raises(ValueError, match="probability"):
        settings(chance_constraints={"max_g": 1.5})


def test_the_inner_sample_resolution_is_reported_not_assumed():
    """An inner sample of S draws can only express p_hat in multiples of 1/S, so an alpha
    below 1/S silently means ZERO violations. The settings say so rather than letting a
    reader assume alpha is met continuously."""
    coarse = settings(inner_samples=8, chance_constraints={"max_g": 0.05})
    assert coarse.probability_resolution == pytest.approx(0.125)
    assert "ZERO violations" in coarse.effective_chance_rule["max_g"]

    fine = settings(inner_samples=32, chance_constraints={"max_g": 0.05})
    assert "at most 1 of 32" in fine.effective_chance_rule["max_g"]
    assert "ZERO violations" not in fine.effective_chance_rule["max_g"]


# =======================================================================================
# 2. scoring one design's inner sample
# =======================================================================================

def test_the_robust_objective_is_the_declared_percentile():
    flux = np.arange(1.0, 21.0)
    frame = sample_frame(20, flux=flux, bondline=flux * 10.0, g_margin=np.ones(20))
    score = score_sample(frame, OBJECTIVES, settings())
    assert score.objectives["peak_heat_flux_w_m2"] == pytest.approx(
        np.percentile(flux, 95.0))
    assert score.objectives["peak_bondline_temperature_k"] == pytest.approx(
        np.percentile(flux * 10.0, 95.0))


def test_chance_violation_is_the_empirical_probability_minus_alpha():
    margins = np.ones(20)
    margins[:3] = -0.1                     # 3 of 20 violate max_g => p_hat = 0.15
    frame = sample_frame(20, flux=np.ones(20), bondline=np.ones(20), g_margin=margins)
    score = score_sample(frame, OBJECTIVES, settings())
    assert score.violation_probability["max_g"] == pytest.approx(0.15)
    assert score.chance_violation["max_g"] == pytest.approx(0.15 - 0.05)
    assert score.worst_chance_violation > 0.0


def test_a_chance_constraint_is_met_when_the_probability_is_below_alpha():
    margins = np.ones(20)
    margins[0] = -0.1                      # 1 of 20 => 0.05, exactly alpha
    frame = sample_frame(20, flux=np.ones(20), bondline=np.ones(20), g_margin=margins)
    score = score_sample(frame, OBJECTIVES, settings())
    assert score.chance_violation["max_g"] == pytest.approx(0.0)
    assert score.worst_chance_violation <= 0.0


def test_draws_with_no_physics_violate_every_chance_constraint_and_leave_the_percentile():
    status = ["OK"] * 20
    status[0] = status[1] = "trajectory terminated as skip_out"
    flux = np.arange(1.0, 21.0)
    flux[0] = flux[1] = np.nan
    frame = sample_frame(20, flux=flux, bondline=np.arange(1.0, 21.0) * 10.0,
                         g_margin=np.ones(20), status=status)
    score = score_sample(frame, OBJECTIVES, settings())
    assert score.n_not_evaluable == 2
    for name in ("max_g", "any"):
        assert score.violation_probability[name] == pytest.approx(2 / 20)
    # the non-finite draws are excluded from the percentile, not counted as zero
    assert score.objectives["peak_heat_flux_w_m2"] == pytest.approx(
        np.percentile(flux[2:], 95.0))


def test_a_design_that_never_completes_an_entry_scores_as_fully_violating():
    frame = sample_frame(10, flux=np.full(10, np.nan), bondline=np.full(10, np.nan),
                         g_margin=np.full(10, np.nan), feasible=np.zeros(10, dtype=bool),
                         status=["trajectory terminated as skip_out"] * 10)
    score = score_sample(frame, OBJECTIVES, settings())
    assert score.violation_probability["any"] == pytest.approx(1.0)
    assert np.isnan(score.objectives["peak_heat_flux_w_m2"])


# =======================================================================================
# 3. the optimiser, through the same budget wrapper
# =======================================================================================

@pytest.fixture(scope="module")
def uncertain_space():
    space, _ = load_design_space(DS_CONFIG)
    space = space.with_active(ACTIVE)
    model, _ = UncertaintyModel.load(UQ_CONFIG, space.base_config)
    unit = common_random_numbers(model.n_inputs, 4, seed=99)
    return make_uncertain_space(space, model, unit)


def test_robust_nsga2_spends_exactly_its_budget_through_the_wrapper(tmp_path,
                                                                    uncertain_space):
    cfg = settings(inner_samples=4, population_size=4, budget_evaluations=48,
                   chance_constraints={"any": 0.30})
    store = CandidateStore(tmp_path / "c.csv")
    evaluator = BudgetedEvaluator(uncertain_space, cfg.budget_evaluations, store,
                                  run_id="T", method="robust_nsga2", seed=37)
    record: list[dict] = []
    info = run_robust_nsga2(evaluator, uncertain_space, OBJECTIVES, cfg,
                            inner_indices=np.arange(4), record=record)
    assert info["generations"] >= 1
    assert evaluator.used <= cfg.budget_evaluations
    assert evaluator.remaining < cfg.inner_samples     # stopped because it could not
    # every candidate is in the persisted log, and every row went through the evaluator
    frame = store.load()
    assert len(frame) == evaluator.n_submitted
    assert set(frame["method"]) == {"robust_nsga2"}
    # one record per candidate design, four evaluations behind each
    assert len(record) * cfg.inner_samples == int((~frame["cache_hit"]).sum()) + \
        int(frame["cache_hit"].sum())


def test_the_optimiser_never_optimises_the_draw_coordinate(tmp_path, uncertain_space):
    cfg = settings(inner_samples=4, population_size=4, budget_evaluations=32,
                   chance_constraints={"any": 0.50})
    store = CandidateStore(tmp_path / "c.csv")
    evaluator = BudgetedEvaluator(uncertain_space, cfg.budget_evaluations, store,
                                  run_id="T", method="robust_nsga2", seed=41)
    record: list[dict] = []
    run_robust_nsga2(evaluator, uncertain_space, OBJECTIVES, cfg,
                     inner_indices=np.arange(4), record=record)
    frame = store.load()
    # each design's block covers exactly the four declared draws, in order
    draws = frame["x___uq_draw"].to_numpy(dtype=float)
    assert np.array_equal(np.unique(draws), np.arange(4.0))
    for start in range(0, len(draws) - 3, 4):
        assert np.array_equal(draws[start:start + 4], np.arange(4.0))
    # and the record carries no draw column at all
    assert not any(k.endswith("_uq_draw") for k in record[0])


def test_robust_front_keeps_only_chance_feasible_non_dominated_designs():
    record = [
        {"candidate_id": "a", "robust__peak_heat_flux_w_m2": 1.0,
         "robust__peak_bondline_temperature_k": 400.0, "worst_chance_violation": -0.01},
        {"candidate_id": "b", "robust__peak_heat_flux_w_m2": 2.0,
         "robust__peak_bondline_temperature_k": 390.0, "worst_chance_violation": 0.0},
        {"candidate_id": "c", "robust__peak_heat_flux_w_m2": 3.0,
         "robust__peak_bondline_temperature_k": 410.0, "worst_chance_violation": -0.2},
        {"candidate_id": "d", "robust__peak_heat_flux_w_m2": 0.5,
         "robust__peak_bondline_temperature_k": 380.0, "worst_chance_violation": 0.3},
    ]
    front = robust_front(record, OBJECTIVES)
    assert list(front["candidate_id"]) == ["a", "b"]    # c dominated, d chance-infeasible


# =======================================================================================
# 4. verifying the shortcut - including that the verification can FAIL
# =======================================================================================

def _scores(flux, bondline, p_any):
    return [RobustScore(objectives={"peak_heat_flux_w_m2": f,
                                    "peak_bondline_temperature_k": b},
                        violation_probability={"max_g": 0.0, "any": p},
                        chance_violation={"max_g": 0.0, "any": p - 0.10},
                        n_samples=32, n_not_evaluable=0)
            for f, b, p in zip(flux, bondline, p_any, strict=True)]


TOLERANCES = {"max_abs_relative_bias": 0.05, "min_rank_correlation": 0.80,
              "max_abs_probability_difference": 0.05}


def test_verification_passes_when_the_two_estimates_agree():
    flux = [1.0, 2.0, 3.0, 4.0, 5.0]
    bond = [400.0, 405.0, 410.0, 415.0, 420.0]
    zeros = [0.0] * 5
    result = verify_shortcut(_scores(flux, bond, zeros), _scores(flux, bond, zeros),
                             OBJECTIVES, settings(), labels=[f"d{i}" for i in range(5)],
                             n_full=1000, full_seed=1, tolerances=TOLERANCES)
    assert result.verdict["passed"]
    assert result.objectives["peak_heat_flux_w_m2"]["mean_relative_bias"] == \
        pytest.approx(0.0)
    assert result.objectives["peak_heat_flux_w_m2"]["spearman_rank_correlation"] == \
        pytest.approx(1.0)


def test_verification_fails_on_a_biased_robust_objective():
    full_flux = [1.0, 2.0, 3.0, 4.0, 5.0]
    short_flux = [f * 1.20 for f in full_flux]           # 20% high, rank preserved
    bond = [400.0, 405.0, 410.0, 415.0, 420.0]
    zeros = [0.0] * 5
    result = verify_shortcut(_scores(short_flux, bond, zeros),
                             _scores(full_flux, bond, zeros), OBJECTIVES, settings(),
                             labels=[f"d{i}" for i in range(5)], n_full=1000,
                             full_seed=1, tolerances=TOLERANCES)
    assert not result.verdict["passed"]
    assert any("relative bias" in f for f in result.verdict["failures"])
    assert result.objectives["peak_heat_flux_w_m2"]["mean_relative_bias"] == \
        pytest.approx(0.20)


def test_verification_fails_when_the_ranking_is_not_preserved():
    full_flux = [1.0, 2.0, 3.0, 4.0, 5.0]
    short_flux = [5.0, 4.0, 3.0, 2.0, 1.0]               # exactly reversed
    bond = [400.0, 405.0, 410.0, 415.0, 420.0]
    zeros = [0.0] * 5
    result = verify_shortcut(_scores(short_flux, bond, zeros),
                             _scores(full_flux, bond, zeros), OBJECTIVES, settings(),
                             labels=[f"d{i}" for i in range(5)], n_full=1000,
                             full_seed=1, tolerances=TOLERANCES)
    assert not result.verdict["passed"]
    assert any("rank correlation" in f for f in result.verdict["failures"])


def test_verification_fails_on_a_wrong_violation_probability():
    flux = [1.0, 2.0, 3.0, 4.0, 5.0]
    bond = [400.0, 405.0, 410.0, 415.0, 420.0]
    result = verify_shortcut(_scores(flux, bond, [0.00] * 5),
                             _scores(flux, bond, [0.00, 0.00, 0.20, 0.00, 0.00]),
                             OBJECTIVES, settings(),
                             labels=[f"d{i}" for i in range(5)], n_full=1000,
                             full_seed=1, tolerances=TOLERANCES)
    assert not result.verdict["passed"]
    assert any("max absolute difference" in f for f in result.verdict["failures"])
    assert result.probabilities["any"]["n_verdict_disagreements"] == 1


def test_verification_records_every_compared_design_for_the_figure():
    flux = [1.0, 2.0, 3.0]
    bond = [400.0, 405.0, 410.0]
    result = verify_shortcut(_scores(flux, bond, [0.0] * 3),
                             _scores(flux, bond, [0.0] * 3), OBJECTIVES, settings(),
                             labels=["a", "b", "c"], n_full=500, full_seed=2,
                             tolerances=TOLERANCES)
    assert len(result.per_design) == 3
    for row in result.per_design:
        assert "shortcut__peak_heat_flux_w_m2" in row
        assert "full__peak_heat_flux_w_m2" in row
    assert result.n_full == 500 and result.n_inner == 20
