"""M5 surrogates: accuracy, calibration, and the refusal to extrapolate silently."""

import numpy as np
import pytest

from src.aether.optimization import BudgetedEvaluator, CandidateStore, load_design_space
from src.aether.optimization.bayes import run_bo_parego
from src.aether.optimization.budget import MARGIN_NAMES
from src.aether.surrogate import (
    DesignSurrogate,
    ExtrapolationError,
    GPSurrogate,
    TrainingHull,
    holdout_validation,
    regression_metrics,
)
from src.aether.utils.run import REPO_ROOT

CONFIG = REPO_ROOT / "configs" / "design_space.yaml"
SMALL = ["diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg"]


def _smooth(x):
    return np.sin(3.0 * x[:, 0]) + 0.5 * x[:, 1] ** 2


# -- hull ---------------------------------------------------------------------------------
def test_hull_contains_the_centre_and_excludes_a_far_corner():
    rng = np.random.default_rng(0)
    hull = TrainingHull(0.25 + 0.5 * rng.random((60, 3)))
    assert hull.defined
    assert hull.contains(np.full((1, 3), 0.5))[0]
    assert not hull.contains(np.full((1, 3), 0.99))[0]


def test_degenerate_hull_reports_everything_as_extrapolated():
    too_few = TrainingHull(np.random.default_rng(0).random((3, 4)))
    collinear = TrainingHull(np.linspace(0, 1, 10)[:, None] * np.ones((1, 2)))
    for hull in (too_few, collinear):
        assert not hull.defined
        assert not hull.contains(np.full((1, hull.n_dims), 0.5))[0]


# -- GP -----------------------------------------------------------------------------------
def test_gp_refuses_to_extrapolate_by_default_and_flags_on_request():
    rng = np.random.default_rng(1)
    x = 0.2 + 0.6 * rng.random((50, 2))
    model = GPSurrogate("f", seed=0).fit(x, _smooth(x))
    inside, outside = np.array([[0.5, 0.5]]), np.array([[0.98, 0.02]])
    assert not model.predict(inside).extrapolated[0]
    with pytest.raises(ExtrapolationError, match="refusing to extrapolate"):
        model.predict(np.vstack([inside, outside]))
    flagged = model.predict(np.vstack([inside, outside]), on_extrapolation="flag")
    assert flagged.extrapolated.tolist() == [False, True]
    assert flagged.std[1] > flagged.std[0]      # and it is less sure out there


def test_gp_is_accurate_and_roughly_calibrated_on_held_out_data():
    rng = np.random.default_rng(2)
    x_train, x_test = rng.random((80, 2)), 0.1 + 0.8 * rng.random((200, 2))
    noise = 0.05
    result = holdout_validation(
        GPSurrogate("f", seed=0), x_train, _smooth(x_train) + noise * rng.standard_normal(80),
        x_test, _smooth(x_test) + noise * rng.standard_normal(200))
    inside = result["inside_hull"]
    assert inside["n"] + result["n_test_outside_hull"] == 200
    assert inside["rmse"] < 2.0 * noise
    assert inside["r2"] > 0.90
    assert 0.85 <= inside["coverage"]["0.95"] <= 1.0
    assert 0.5 <= inside["z_std"] <= 1.5


def test_log_transform_round_trips_and_rejects_non_positive_outputs():
    x = np.random.default_rng(3).random((30, 2))
    y = 10.0 ** (5.0 + x[:, 0])
    model = GPSurrogate("q", transform="log10", seed=0).fit(x, y)
    pred = model.predict(x[:5], on_extrapolation="flag")
    assert pred.central == pytest.approx(y[:5], rel=1e-2)
    with pytest.raises(ValueError, match="log10"):
        GPSurrogate("q", transform="log10").fit(x, y - y.max())


def test_gp_refuses_non_finite_training_data():
    x = np.random.default_rng(4).random((10, 2))
    y = _smooth(x)
    y[3] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        GPSurrogate("f").fit(x, y)


def test_regression_metrics_hand_case():
    truth, mean, std = np.array([0.0, 0.0, 0.0, 0.0]), np.array([1.0, -1.0, 3.0, 0.0]), np.ones(4)
    m = regression_metrics(truth + np.array([0.0, 1.0, 2.0, 3.0]), mean, std)
    # errors: 1, -2, 1, -3
    assert m["rmse"] == pytest.approx(np.sqrt(15.0 / 4.0))
    assert m["mae"] == pytest.approx(7.0 / 4.0)
    assert m["coverage"]["0.68"] == pytest.approx(0.0)     # |z| <= 0.994: none, 1 > 0.994
    assert m["coverage"]["0.95"] == pytest.approx(0.5)     # |z| <= 1.960: the two 1s


# -- run-level bundle ---------------------------------------------------------------------
def _fake_rows(space, n, rng, *, valid):
    rows = []
    for _ in range(n):
        x = space.from_unit(rng.random(space.n_active))
        u = space.to_unit(x)
        row = {f"x__{name}": float(v) for name, v in zip(space.active, x, strict=True)}
        row.update({"cache_hit": False, "status": "OK" if valid else "invalid geometry: test",
                    "feasible": valid,
                    "peak_heat_flux_w_m2": 1e5 * (1.0 + u[0]) if valid else float("nan"),
                    "peak_bondline_temperature_k": 350.0 + 50.0 * u[3] if valid
                    else float("nan")})
        for name in MARGIN_NAMES:
            row[f"margin__{name}"] = float("nan")
        row["margin__max_g"] = 0.5 - u[3] if valid else float("nan")
        rows.append(row)
    return rows


def test_design_surrogate_needs_enough_physics_and_handles_a_single_class():
    space = load_design_space(CONFIG)[0].with_active(SMALL)
    rng = np.random.default_rng(5)
    objectives = ("peak_heat_flux_w_m2", "peak_bondline_temperature_k")
    model = DesignSurrogate(space, objectives, seed=0,
                            transforms={"peak_heat_flux_w_m2": "log10"})
    with pytest.raises(ValueError, match="need 6"):
        model.fit(_fake_rows(space, 3, rng, valid=True) + _fake_rows(space, 9, rng, valid=False))
    model.fit(_fake_rows(space, 25, rng, valid=True))
    query = rng.random((7, space.n_active))
    assert np.all(model.probability_valid(query) == 1.0)       # never saw an invalid one
    assert set(model.margin_models) == {"max_g"}               # null limits are not modelled
    p = model.probability_feasible(query)
    assert np.all((p >= 0.0) & (p <= 1.0))
    with pytest.raises(ExtrapolationError):
        model.predict_objectives(np.ones((1, space.n_active)))


def test_bo_parego_spends_exactly_its_budget_and_logs_predictions_first(tmp_path):
    space, cfg = load_design_space(CONFIG)
    space = space.with_active(SMALL)
    store = CandidateStore(tmp_path / "c.csv")
    evaluator = BudgetedEvaluator(space, 26, store, run_id="T", method="bo_parego", seed=11)
    log: list[dict] = []
    hv = {key: {n: float(v) for n, v in cfg["optimize"]["hypervolume"][key].items()}
          for key in ("reference_point", "ideal_point")}
    run_bo_parego(evaluator, dict(n_initial=14, batch_size=6, pool_size=256, mc_samples=16,
                                  local_sigma=0.05, min_probability_feasible=0.05,
                                  gp_restarts=0, transforms={"peak_heat_flux_w_m2": "log10"}),
                  tuple(cfg["objectives"]), hv, prediction_log=log)
    frame = store.load()
    assert evaluator.used == 26
    assert len(log) == 12                                       # two batches of six
    assert {rec["candidate_id"] for rec in log} <= set(frame["candidate_id"])
    assert all(0.0 <= rec["p_feasible"] <= 1.0 for rec in log)
