"""M4 infrastructure: design space, sampling, persistence, budget accounting, determinism."""

import numpy as np
import pytest

from src.aether.evaluate import evaluate_design
from src.aether.geometry import CapsuleGeometry
from src.aether.optimization import (
    METHODS,
    BudgetedEvaluator,
    BudgetExhausted,
    CandidateStore,
    given_data_first_order,
    latin_hypercube,
    load_candidates,
    load_design_space,
    one_at_a_time,
    saltelli_sample,
    sobol_indices,
)
from src.aether.optimization.design_space import DesignSpace
from src.aether.utils.run import REPO_ROOT, load_config

CONFIG = REPO_ROOT / "configs" / "design_space.yaml"
SMALL = ["diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg"]
VOLATILE = ["wall_time_s"]


@pytest.fixture(scope="module")
def loaded():
    return load_design_space(CONFIG)


@pytest.fixture()
def small_space(loaded):
    return loaded[0].with_active(SMALL)


def _evaluator(space, tmp_path, budget, method="test", seed=1, name="c.csv"):
    store = CandidateStore(tmp_path / name)
    return BudgetedEvaluator(space, budget, store, run_id="T", method=method, seed=seed), store


# -- design space -----------------------------------------------------------------------
def test_reference_design_maps_to_the_phase_f_baseline_capsule(loaded):
    space, _ = loaded
    cfg = space.config_for({v.name: v.reference for v in space.variables})
    geom = cfg["vehicle"]["geometry"]
    baseline = load_config(REPO_ROOT / "geometry" / "parametric" / "baseline.yaml")["geometry"]
    for key, value in baseline.items():
        assert geom[key] == pytest.approx(value)
    CapsuleGeometry(**{k: geom[k] for k in baseline}).validate()
    assert cfg["tps"]["layers"][0]["thickness_m"] == pytest.approx(0.015)


def test_ratio_variables_scale_with_diameter(small_space):
    values = small_space.values(np.array([2.0, 0.8, 65.0, -4.0]))
    geom = small_space.config_for(values)["vehicle"]["geometry"]
    assert geom["nose_radius_m"] == pytest.approx(1.6)
    assert geom["length_m"] == pytest.approx(0.875 * 2.0)
    assert geom["shoulder_radius_m"] == pytest.approx(0.10 * 2.0)


def test_unit_mapping_round_trips(small_space):
    u = np.array([0.0, 0.25, 0.5, 1.0])
    assert small_space.to_unit(small_space.from_unit(u)) == pytest.approx(u)
    assert small_space.from_unit(np.zeros(4)) == pytest.approx(small_space.lower)


def test_a_range_outside_geometry_bounds_is_refused(loaded):
    _, cfg = loaded
    bad = {**cfg, "variables": {k: dict(v) for k, v in cfg["variables"].items()}}
    bad["variables"]["cone_half_angle_deg"]["max"] = 85.0  # geometry bound is 70
    with pytest.raises(ValueError, match="leaves the geometry bound"):
        DesignSpace.from_config(bad)


# -- evaluator contract -------------------------------------------------------------------
def test_invalid_geometry_is_an_infeasible_result_not_an_exception(loaded):
    space, _ = loaded
    values = {v.name: v.reference for v in space.variables}
    values.update(bluntness_ratio=1.3, cone_half_angle_deg=20.0)  # nose sphere overlaps shoulder
    ev = evaluate_design(space.config_for(values))
    assert not ev.performance.feasible
    assert ev.performance.status.startswith("invalid geometry: cone_half_angle_deg")
    assert np.isnan(ev.performance.peak_heat_flux_w_m2)
    assert ev.trajectory is None


def test_full_geometry_path_reproduces_the_legacy_two_parameter_result(loaded):
    """Same nose radius, diameter and constant Cd => identical physics (Fidelity 0)."""
    space, _ = loaded
    full = evaluate_design(space.config_for({v.name: v.reference for v in space.variables}))
    legacy = evaluate_design(load_config(REPO_ROOT / "configs" / "baseline.yaml"))
    assert full.fidelity == 0
    for name in ("peak_heat_flux_w_m2", "peak_bondline_temperature_k", "max_g"):
        assert getattr(full.performance, name) == getattr(legacy.performance, name)
    assert "heatshield_mass_fraction" in full.performance.constraint_margins
    assert "heatshield_mass_fraction" not in legacy.performance.constraint_margins


def test_unknown_aero_model_is_a_config_error(loaded):
    space, _ = loaded
    cfg = space.config_for({v.name: v.reference for v in space.variables})
    cfg["vehicle"]["aero"] = {"model": "cfd_response_surface"}
    with pytest.raises(KeyError, match="G4"):
        evaluate_design(cfg)


# -- sampling -----------------------------------------------------------------------------
@pytest.mark.parametrize("n,d", [(10, 3), (64, 7), (257, 2)])
def test_lhs_has_exactly_one_point_per_stratum_in_every_dimension(n, d):
    sample = latin_hypercube(n, d, seed=5)
    assert sample.shape == (n, d)
    assert np.all((sample >= 0.0) & (sample < 1.0))
    for dim in range(d):
        strata = np.floor(sample[:, dim] * n).astype(int)
        assert sorted(strata.tolist()) == list(range(n))


def test_lhs_is_seeded():
    assert np.array_equal(latin_hypercube(30, 4, 9), latin_hypercube(30, 4, 9))
    assert not np.array_equal(latin_hypercube(30, 4, 9), latin_hypercube(30, 4, 10))


def test_oat_varies_exactly_one_dimension_per_row():
    ref = np.array([0.3, 0.6, 0.9])
    sample, swept = one_at_a_time(3, 5, ref)
    assert sample.shape == (15, 3)
    for row, dim in zip(sample, swept, strict=True):
        others = [j for j in range(3) if j != dim]
        assert row[others] == pytest.approx(ref[others])
    assert sample[swept == 1][:, 1] == pytest.approx(np.linspace(0, 1, 5))


def test_sobol_indices_recover_the_ishigami_analytical_values():
    # Ishigami (a=7, b=0.1): S1 = (0.3139, 0.4424, 0), ST = (0.5576, 0.4424, 0.2437)
    unit = saltelli_sample(4096, 3, seed=1)
    x = -np.pi + 2.0 * np.pi * unit
    y = np.sin(x[:, 0]) + 7.0 * np.sin(x[:, 1]) ** 2 + 0.1 * x[:, 2] ** 4 * np.sin(x[:, 0])
    res = sobol_indices(y, 3, n_bootstrap=100, seed=2)
    assert res.first == pytest.approx([0.3139, 0.4424, 0.0], abs=0.03)
    assert res.total == pytest.approx([0.5576, 0.4424, 0.2437], abs=0.03)
    assert np.all(res.total_ci[:, 0] <= res.total) and np.all(res.total <= res.total_ci[:, 1])


def test_sobol_refuses_nan_outputs():
    y = np.ones(5 * 8)
    y[3] = np.nan
    with pytest.raises(ValueError, match="biased"):
        sobol_indices(y, 3)


def test_given_data_estimator_separates_an_active_input_from_an_inert_one():
    rng = np.random.default_rng(0)
    x = rng.random((4000, 2))
    y = 3.0 * x[:, 0] + 0.05 * rng.standard_normal(4000)
    index, ci = given_data_first_order(x, y, n_bins=20, n_bootstrap=50)
    assert index[0] > 0.95
    assert ci[1, 1] < 0.03


# -- persistence ----------------------------------------------------------------------------
def test_candidate_log_round_trips_through_csv_and_parquet(small_space, tmp_path):
    evaluator, store = _evaluator(small_space, tmp_path, budget=6)
    x = small_space.from_unit(latin_hypercube(5, 4, seed=2))
    x[0] = [1.2, 1.3, 20.0, -3.0]  # geometrically invalid
    rows = evaluator.evaluate(x, generation=3, parent_ids=[["C-a", "C-b"]] + [[]] * 4)

    frame = store.load()
    assert len(frame) == 5
    assert frame["parent_ids"].iloc[0] == ["C-a", "C-b"]
    assert frame["generation"].unique().tolist() == [3]
    assert frame["failure_reason"].iloc[0].startswith("invalid geometry")
    assert not frame["feasible"].iloc[0]
    assert np.isnan(frame["peak_heat_flux_w_m2"].iloc[0])
    for row, (_, saved) in zip(rows, frame.iterrows(), strict=True):
        assert saved["candidate_id"] == row["candidate_id"]
        if not np.isnan(row["peak_bondline_temperature_k"]):
            assert saved["peak_bondline_temperature_k"] == row["peak_bondline_temperature_k"]
        assert saved["violated_constraints"] == row["violated_constraints"]

    parquet = load_candidates(store.export_parquet())
    assert parquet["candidate_id"].tolist() == frame["candidate_id"].tolist()
    assert parquet["parent_ids"].tolist() == frame["parent_ids"].tolist()


def test_store_appends_rather_than_overwrites(small_space, tmp_path):
    evaluator, store = _evaluator(small_space, tmp_path, budget=4)
    evaluator.evaluate(small_space.from_unit(latin_hypercube(2, 4, seed=1)))
    reopened = CandidateStore(store.csv_path)
    second = BudgetedEvaluator(small_space, 4, reopened, run_id="T2", method="test", seed=2)
    second.evaluate(small_space.from_unit(latin_hypercube(2, 4, seed=3)))
    assert store.load()["run_id"].tolist() == ["T", "T", "T2", "T2"]


# -- budget accounting ----------------------------------------------------------------------
def test_budget_counts_distinct_designs_and_duplicates_are_free(small_space, tmp_path):
    evaluator, store = _evaluator(small_space, tmp_path, budget=5)
    x = small_space.from_unit(latin_hypercube(3, 4, seed=4))
    evaluator.evaluate(np.vstack([x, x[:1]]))        # duplicate inside one batch
    assert evaluator.used == 3 and evaluator.n_cache_hits == 1
    evaluator.evaluate(x[1:2])                          # duplicate across batches
    assert evaluator.used == 3 and evaluator.n_cache_hits == 2
    frame = store.load()
    assert frame["cache_hit"].tolist() == [False, False, False, True, True]
    assert frame["budget_index"].tolist() == [1, 2, 3, 3, 3]
    assert frame["eval_index"].tolist() == [1, 2, 3, 4, 5]


def test_invalid_geometry_is_charged(small_space, tmp_path):
    evaluator, _ = _evaluator(small_space, tmp_path, budget=3)
    evaluator.evaluate(np.array([[1.2, 1.3, 20.0, -3.0]]))
    assert evaluator.used == 1


def test_budget_is_never_exceeded_and_overrun_raises(small_space, tmp_path):
    evaluator, store = _evaluator(small_space, tmp_path, budget=4)
    x = small_space.from_unit(latin_hypercube(7, 4, seed=6))
    with pytest.raises(BudgetExhausted):
        evaluator.evaluate(x)
    assert evaluator.used == 4 and evaluator.remaining == 0
    assert len(store.load()) == 4
    with pytest.raises(BudgetExhausted):
        evaluator.evaluate(x[5:6])
    assert evaluator.evaluate(x[:1])[0]["cache_hit"]   # cached designs stay answerable


@pytest.mark.parametrize("method", list(METHODS))
def test_every_optimiser_spends_exactly_its_budget(method, loaded, small_space, tmp_path):
    _, cfg = loaded
    opt = cfg["optimize"]
    settings = {**opt["methods"][method], "population_size": 8, "n_weights": 2}
    evaluator, store = _evaluator(small_space, tmp_path, budget=37, method=method)
    METHODS[method](evaluator, settings, tuple(cfg["objectives"]), opt["hypervolume"])
    frame = store.load()
    assert evaluator.used == 37
    assert int((~frame["cache_hit"]).sum()) == 37
    assert frame.loc[~frame["cache_hit"], "candidate_id"].is_unique
    assert set(frame["fidelity"]) == {0}


def test_nsga2_offspring_carry_parent_ids_that_exist(loaded, small_space, tmp_path):
    _, cfg = loaded
    opt = cfg["optimize"]
    evaluator, store = _evaluator(small_space, tmp_path, budget=30, method="nsga2")
    METHODS["nsga2"](evaluator, {"population_size": 8}, tuple(cfg["objectives"]),
                     opt["hypervolume"])
    frame = store.load()
    assert all(p == [] for p in frame.loc[frame["generation"] == 0, "parent_ids"])
    offspring = frame[frame["generation"] > 0]
    assert len(offspring) and all(len(p) == 2 for p in offspring["parent_ids"])
    known = set(frame["candidate_id"])
    assert all(pid in known for parents in offspring["parent_ids"] for pid in parents)


@pytest.mark.parametrize("method", list(METHODS))
def test_fixed_seed_gives_an_identical_candidate_log(method, loaded, small_space, tmp_path):
    _, cfg = loaded
    opt = cfg["optimize"]
    settings = {**opt["methods"][method], "population_size": 8, "n_weights": 2}
    frames = []
    for name in ("a.csv", "b.csv"):
        evaluator, store = _evaluator(small_space, tmp_path, budget=24, method=method,
                                      seed=7, name=name)
        METHODS[method](evaluator, settings, tuple(cfg["objectives"]), opt["hypervolume"])
        frames.append(store.load().drop(columns=VOLATILE))
    assert frames[0].equals(frames[1])


# -- analysis -----------------------------------------------------------------------------
def test_front_and_hypervolume_curve_from_a_hand_built_log():
    import pandas as pd

    from src.aether.optimization import feasible_front, hypervolume_curve

    objs = ("peak_heat_flux_w_m2", "peak_bondline_temperature_k")
    frame = pd.DataFrame({
        "candidate_id": ["a", "b", "c", "c2", "d", "a"],
        "feasible": [True, True, True, True, False, True],
        "cache_hit": [False, False, False, False, False, True],
        "budget_index": [1, 2, 3, 4, 5, 5],
        "peak_heat_flux_w_m2": [1.0e6, 2.0e6, 0.5e6, 0.5e6, 0.1e6, 1.0e6],
        "peak_bondline_temperature_k": [420.0, 440.0, 435.0, 435.0, 310.0, 420.0],
    })
    front = feasible_front(frame, objs)
    # b is dominated by a; d is infeasible; c2 has c's objectives exactly (inert variable)
    assert front["candidate_id"].tolist() == ["c", "a"]

    hv_cfg = {"reference_point": {objs[0]: 2.5e6, objs[1]: 450.0},
              "ideal_point": {objs[0]: 0.0, objs[1]: 300.0}}
    curve = hypervolume_curve(frame, objs, hv_cfg, np.array([1, 2, 3, 5]))
    # a alone: (1 - 0.4) * (1 - 0.8) = 0.12; b adds nothing; c adds (0.4 - 0.2) * (1 - 0.9)
    assert curve == pytest.approx([0.12, 0.12, 0.14, 0.14])
