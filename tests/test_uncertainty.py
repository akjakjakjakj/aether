"""M7 infrastructure: distributions, sampling, interval maths, propagation, attribution.

The maths here is checked against CLOSED FORMS wherever one exists - a Wilson interval
against its own algebra, a percentile against the order statistic that defines it, and the
whole propagation chain against a toy linear model whose output mean and variance are
known analytically. An uncertainty study that is only checked against itself is not
checked.
"""

from __future__ import annotations

import copy
import math

import numpy as np
import pytest
from scipy.stats import norm

from src.aether.atmosphere import (
    DensityMultiplierProfile,
    PerturbedAtmosphere,
    USStandardAtmosphere1976,
    build_atmosphere,
)
from src.aether.evaluate import evaluate_design
from src.aether.geometry import (
    CAP_RADIUS,
    VELOCITY_GRADIENT,
    VELOCITY_GRADIENT_ZOBY,
    CapsuleGeometry,
    effective_nose_radius_report,
    zoby_sullivan_shift,
)
from src.aether.optimization import BudgetedEvaluator, CandidateStore, load_design_space
from src.aether.uncertainty import (
    Discrete,
    InputUnavailable,
    Normal,
    UncertaintyModel,
    Uniform,
    analyse,
    build_distribution,
    clopper_pearson_interval,
    common_random_numbers,
    convergence_table,
    evaluate_under_uncertainty,
    make_draws,
    make_uncertain_space,
    quantile,
    summarise,
    violation_probability,
    wilson_interval,
)
from src.aether.uncertainty.space import UQ_DRAW
from src.aether.utils.run import REPO_ROOT, load_config

UQ_CONFIG = REPO_ROOT / "configs" / "uncertainty.yaml"
DS_CONFIG = REPO_ROOT / "configs" / "design_space.yaml"
ACTIVE = ["diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg"]


@pytest.fixture(scope="module")
def design_space():
    space, _ = load_design_space(DS_CONFIG)
    return space.with_active(ACTIVE)


@pytest.fixture(scope="module")
def model(design_space):
    built, _ = UncertaintyModel.load(UQ_CONFIG, design_space.base_config)
    return built


# =======================================================================================
# 1. distribution sampling: reproducibility and inverse-CDF correctness
# =======================================================================================

def test_normal_ppf_matches_scipy_and_is_exactly_reproducible():
    dist = Normal(mean=3.0, std=2.0)
    u = np.linspace(0.01, 0.99, 25)
    expected = norm.ppf(u, loc=3.0, scale=2.0)
    assert np.allclose(dist.ppf(u), expected, rtol=0.0, atol=1e-12)
    assert np.array_equal(dist.ppf(u), dist.ppf(u))


def test_uniform_ppf_is_the_affine_map_and_hits_both_ends():
    dist = Uniform(low=-1.0, high=3.0)
    assert dist.ppf(0.0) == pytest.approx(-1.0)
    assert dist.ppf(1.0) == pytest.approx(3.0)
    assert dist.ppf(0.25) == pytest.approx(0.0)


def test_discrete_ppf_partitions_the_unit_interval_by_probability():
    dist = Discrete(values=("a", "b", "c"), probabilities=(0.2, 0.5, 0.3))
    u = np.linspace(0.0, 1.0, 100_001)[:-1]
    picked = np.array([dist.select(i) for i in dist.ppf(u)])
    for value, p in zip(dist.values, dist.probabilities, strict=True):
        assert np.mean(picked == value) == pytest.approx(p, abs=2e-4)


def test_discrete_probabilities_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to"):
        Discrete(values=("a", "b"), probabilities=(0.4, 0.4))


def test_build_distribution_rejects_parameters_the_family_does_not_take():
    # `{family: normal, low: 0, high: 1}` would otherwise silently sample N(0, 1).
    with pytest.raises(ValueError, match="unknown parameters"):
        build_distribution({"family": "normal", "low": 0.0, "high": 1.0})
    with pytest.raises(ValueError, match="missing"):
        build_distribution({"family": "uniform", "low": 0.0})
    with pytest.raises(ValueError, match="unknown distribution family"):
        build_distribution({"family": "beta", "a": 1.0, "b": 1.0})


def test_latin_hypercube_draws_are_reproducible_from_the_seed_alone(model):
    a = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                   model.indices_of_kind("epistemic"), mode="nested", seed=7,
                   n_aleatory=5, n_epistemic_branches=3)
    b = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                   model.indices_of_kind("epistemic"), mode="nested", seed=7,
                   n_aleatory=5, n_epistemic_branches=3)
    c = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                   model.indices_of_kind("epistemic"), mode="nested", seed=8,
                   n_aleatory=5, n_epistemic_branches=3)
    assert np.array_equal(a.unit, b.unit)
    assert not np.array_equal(a.unit, c.unit)


def test_nested_draws_share_common_random_numbers_across_branches(model):
    draws = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                       model.indices_of_kind("epistemic"), mode="nested", seed=3,
                       n_aleatory=6, n_epistemic_branches=4)
    aleatory = list(model.indices_of_kind("aleatory"))
    first = draws.unit[draws.branch(0)][:, aleatory]
    for b in range(1, 4):
        assert np.array_equal(draws.unit[draws.branch(b)][:, aleatory], first)
    # ...and the epistemic block is constant WITHIN a branch and different between them
    epistemic = list(model.indices_of_kind("epistemic"))
    for b in range(4):
        block = draws.unit[draws.branch(b)][:, epistemic]
        assert np.allclose(block, block[0])
    heads = np.array([draws.unit[draws.branch(b)][0, epistemic] for b in range(4)])
    assert len(np.unique(heads, axis=0)) == 4


def test_draw_partition_is_enforced(model):
    with pytest.raises(ValueError, match="partition"):
        make_draws(model.n_inputs, (0,), (1,), mode="nested", seed=1, n_aleatory=2,
                   n_epistemic_branches=2)


# =======================================================================================
# 2. interval maths against closed forms
# =======================================================================================

def test_wilson_interval_matches_its_own_algebra():
    k, n, conf = 7, 120, 0.95
    z = float(norm.ppf(0.5 + conf / 2.0))
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4.0 * n * n))
    lo, hi = wilson_interval(k, n, conf)
    assert lo == pytest.approx(centre - half, rel=1e-12)
    assert hi == pytest.approx(centre + half, rel=1e-12)


def test_zero_violations_is_not_zero_probability():
    lo, hi = wilson_interval(0, 500)
    assert lo == pytest.approx(0.0, abs=1e-12)
    assert 0.004 < hi < 0.008          # ~0.57%, of the order of the rule of three
    exact_lo, exact_hi = clopper_pearson_interval(0, 500)
    assert exact_lo == 0.0
    # Clopper-Pearson at k = 0 is exactly 1 - alpha^(1/n): the rule of three, closed form
    assert exact_hi == pytest.approx(1.0 - 0.025 ** (1.0 / 500), rel=1e-9)


def test_violation_probability_phrase_never_says_zero():
    result = violation_probability("max_g", np.zeros(500, dtype=bool))
    assert result.n_violations == 0
    assert "not zero" in result.phrase
    assert "below" in result.phrase


def test_not_evaluable_draws_count_as_violations():
    violated = np.zeros(10, dtype=bool)
    missing = np.zeros(10, dtype=bool)
    missing[:3] = True
    result = violation_probability("any", violated, not_evaluable=missing)
    assert result.n_violations == 3
    assert result.n_not_evaluable == 3


def test_percentile_matches_the_order_statistic_it_interpolates():
    values = np.arange(1.0, 101.0)      # 1..100
    # numpy's linear ('inverse CDF with interpolation') definition: q = (n-1)*p
    assert quantile(values, 95.0) == pytest.approx(1.0 + 0.95 * 99.0)
    assert quantile(values, 50.0) == pytest.approx(50.5)
    assert quantile(values, 0.0) == pytest.approx(1.0)


def test_summarise_excludes_non_finite_values_but_counts_them():
    values = np.array([1.0, 2.0, np.nan, 3.0, np.inf])
    summary = summarise(values, percentiles=(50.0,))
    assert summary.n == 5
    assert summary.n_finite == 3
    assert summary.mean == pytest.approx(2.0)
    assert summary.std == pytest.approx(1.0)
    assert summary.percentiles["p50"] == pytest.approx(2.0)


def test_convergence_table_half_width_shrinks_with_sample_size():
    rng = np.random.default_rng(0)
    values = rng.normal(100.0, 10.0, 4000)
    table = convergence_table(values, (50, 200, 1000, 4000),
                              {"mean": lambda a: float(np.mean(a))},
                              n_bootstrap=200, seed=1)
    widths = [row["mean__half_width"] for row in table]
    assert widths == sorted(widths, reverse=True)
    # a mean's bootstrap half-width should track 1.96 * sigma / sqrt(n) to within ~25%
    assert widths[-1] == pytest.approx(1.96 * 10.0 / math.sqrt(4000), rel=0.25)


# =======================================================================================
# 3. the declared inventory: sourcing gates, availability, refusal
# =======================================================================================

def test_every_declared_input_carries_a_source_and_a_tier(model):
    assert model.n_inputs > 0
    for item in model.inputs:
        assert item.source.strip()
        assert item.tier in ("T1", "T2", "T3")
        assert item.kind in ("aleatory", "epistemic")


def test_a_t3_input_must_say_it_is_judgment_in_its_own_source_line(model):
    base = {"kind": "aleatory", "distribution": {"family": "uniform", "low": 0.9,
                                                 "high": 1.1},
            "apply": {"type": "multiply", "path": "vehicle.mass_kg"},
            "tier": "T3"}
    good = {"inputs": {"x": {**base, "source": "engineering judgment, no source"}}}
    bad = {"inputs": {"x": {**base, "source": "NASA TM-1234 table 5"}}}
    cfg = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    UncertaintyModel.from_config(good, cfg)
    with pytest.raises(ValueError, match="does not say so"):
        UncertaintyModel.from_config(bad, cfg)


CFD_TERMS = ("cd_surrogate_gp", "cd_discretisation", "cd_perfect_gas_model_form",
             "cd_base_drag")


def _fidelity0_base(design_space):
    base = copy.deepcopy(design_space.base_config)
    base["vehicle"]["aero"] = {"model": "constant"}
    return base


def test_fidelity0_skips_the_cfd_terms_and_says_which(design_space):
    model, _ = UncertaintyModel.load(UQ_CONFIG, _fidelity0_base(design_space))
    skipped = dict(model.skipped)
    for name in CFD_TERMS:
        assert name in skipped
        assert "cfd_surface_v2" in skipped[name]
    assert "cd_fidelity0_judgment" in model.names


def test_fidelity1_carries_all_four_cfd_terms_and_drops_the_fidelity0_band(model, design_space):
    """The design space selects `cfd_surface_v2` since 2026-09-21 and M2's GCI exists, so none
    of the four sourced C_D terms may be skipped - and the unsourced Fidelity-0 band must be."""
    assert design_space.base_config["vehicle"]["aero"]["model"] == "cfd_surface_v2"
    for name in CFD_TERMS:
        assert name in model.names
    assert "cd_fidelity0_judgment" in dict(model.skipped)


def test_the_run_refuses_when_the_gci_term_is_unavailable(design_space, monkeypatch):
    """A-CFD-9: sampling the discretisation band RAISES rather than silently becoming 0.

    Hermetic since 2026-09-21: the test used to read the live `results/M2/`, so it started
    failing the moment M2 produced a three-level GCI (i.e. when the band became available,
    which is the behaviour working). The 'no GCI yet' state is now constructed."""
    import src.aether.uncertainty.inputs as uq_inputs

    monkeypatch.setattr(uq_inputs, "discretisation_band",
                        lambda level, *a, **k: {"available": False, "rel_band": None,
                                                "source": None, "mesh_level": level})
    study = load_config(UQ_CONFIG)
    base = copy.deepcopy(design_space.base_config)
    base["vehicle"]["aero"] = {"model": "cfd_surface_v2", "allow_provisional": True}
    with pytest.raises(InputUnavailable) as excinfo:
        UncertaintyModel.from_config(study, base)
    message = str(excinfo.value)
    assert "cd_discretisation" in message
    assert "gci.csv" in message
    assert "refuse" in message


def test_refusal_names_the_requirement_not_just_the_input(design_space):
    study = copy.deepcopy(load_config(UQ_CONFIG))
    # make the Fidelity-1-only requirement a refusal too, and check it fires FIRST
    study["inputs"]["cd_base_drag"]["when_unavailable"] = {"aero_model": "refuse"}
    with pytest.raises(InputUnavailable, match="aero_model"):
        UncertaintyModel.from_config(study, _fidelity0_base(design_space))


# =======================================================================================
# 4. the physics hooks are identity by default
# =======================================================================================

def test_absent_uncertainty_blocks_leave_the_evaluator_bit_identical():
    config = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    reference = evaluate_design(copy.deepcopy(config))
    for block in ({"atmosphere": {}},
                  {"heating": {}},
                  {"heating": {"sutton_graves_coefficient_scale": 1.0,
                               "high_altitude_flux_multiplier": 1.0}},
                  {"atmosphere": {"density_multiplier_profile":
                                  {"altitude_km": [0.0, 150.0], "multiplier": [1.0, 1.0]}}}):
        patched = {**copy.deepcopy(config), **block}
        result = evaluate_design(patched)
        assert result.performance.peak_heat_flux_w_m2 == \
            reference.performance.peak_heat_flux_w_m2
        assert result.performance.peak_bondline_temperature_k == \
            reference.performance.peak_bondline_temperature_k
        assert result.performance.max_g == reference.performance.max_g


def test_build_atmosphere_returns_the_bare_model_for_an_identity_profile():
    assert isinstance(build_atmosphere(None), USStandardAtmosphere1976)
    assert isinstance(build_atmosphere({}), USStandardAtmosphere1976)
    identity = {"density_multiplier_profile": {"altitude_km": [0.0, 150.0],
                                               "multiplier": [1.0, 1.0]}}
    assert isinstance(build_atmosphere(identity), USStandardAtmosphere1976)
    perturbed = {"density_multiplier_profile": {"altitude_km": [0.0, 150.0],
                                                "multiplier": [1.0, 1.2]}}
    assert isinstance(build_atmosphere(perturbed), PerturbedAtmosphere)


def test_density_perturbation_keeps_the_ideal_gas_closure_and_the_speed_of_sound():
    profile = DensityMultiplierProfile(altitude_m=(0.0, 150_000.0), multiplier=(1.2, 1.2))
    base = USStandardAtmosphere1976(warn_above_86km=False)
    perturbed = PerturbedAtmosphere(base, profile)
    for altitude in (0.0, 30_000.0, 70_000.0, 100_000.0):
        a, b = base.state(altitude), perturbed.state(altitude)
        assert b.density_kg_m3 == pytest.approx(1.2 * a.density_kg_m3, rel=1e-12)
        assert b.pressure_pa == pytest.approx(1.2 * a.pressure_pa, rel=1e-12)
        assert b.temperature_k == a.temperature_k
        assert b.speed_of_sound_m_s == a.speed_of_sound_m_s
        assert b.extrapolated == a.extrapolated
        assert b.pressure_pa / (b.density_kg_m3 * b.temperature_k) == \
            pytest.approx(a.pressure_pa / (a.density_kg_m3 * a.temperature_k), rel=1e-12)


def test_density_profile_is_held_outside_its_tabulated_range():
    profile = DensityMultiplierProfile(altitude_m=(10_000.0, 50_000.0),
                                       multiplier=(1.1, 1.5))
    assert profile.at(0.0) == pytest.approx(1.1)
    assert profile.at(100_000.0) == pytest.approx(1.5)
    assert profile.at(30_000.0) == pytest.approx(1.3)


def test_sutton_graves_scale_moves_the_flux_exactly_proportionally():
    config = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    reference = evaluate_design(copy.deepcopy(config))
    scaled = evaluate_design({**copy.deepcopy(config),
                              "heating": {"sutton_graves_coefficient_scale": 1.04}})
    assert scaled.performance.peak_heat_flux_w_m2 == pytest.approx(
        1.04 * reference.performance.peak_heat_flux_w_m2, rel=1e-12)


def test_high_altitude_multiplier_touches_only_the_flagged_band():
    config = load_config(REPO_ROOT / "configs" / "baseline.yaml")
    reference = evaluate_design(copy.deepcopy(config))
    boosted = evaluate_design({**copy.deepcopy(config),
                               "heating": {"high_altitude_flux_multiplier": 2.0}})
    # peak heating happens well below 86 km, so the PEAK is untouched...
    assert boosted.performance.peak_heat_flux_w_m2 == pytest.approx(
        reference.performance.peak_heat_flux_w_m2, rel=1e-12)
    # ...while the integrated load, which NR-14 says draws 5-20% from up there, is not
    assert boosted.performance.integrated_external_heat_j_m2 > \
        reference.performance.integrated_external_heat_j_m2


# =======================================================================================
# 5. the effective-nose-radius model-form switch
# =======================================================================================

def test_zoby_shift_reproduces_ellisons_published_disagreement_at_its_stated_points():
    assert zoby_sullivan_shift(0.0) == pytest.approx(0.10)
    assert zoby_sullivan_shift(0.417) == pytest.approx(0.20)
    assert zoby_sullivan_shift(0.707) == pytest.approx(0.10)
    assert zoby_sullivan_shift(1.0) == pytest.approx(0.0, abs=1e-12)


def test_the_two_sources_agree_identically_at_the_hemisphere():
    """At K = 1 the body IS a hemisphere; Zoby & Sullivan eq. (5) gives R_eff = R_n
    whichever table is read, so the model-form switch can move nothing there."""
    kwargs = {"nose_radius_m": 0.6, "body_radius_m": 0.6, "corner_radius_m": 0.12}
    a = effective_nose_radius_report(**kwargs, model=VELOCITY_GRADIENT)
    b = effective_nose_radius_report(**kwargs, model=VELOCITY_GRADIENT_ZOBY)
    assert a.effective_nose_radius_m == pytest.approx(b.effective_nose_radius_m, rel=1e-12)


def test_zoby_state_raises_the_effective_radius_where_the_front_sits():
    """K ~ 0.42 is where the M4 front lives and where the sources disagree by ~20%."""
    kwargs = {"nose_radius_m": 1.2, "body_radius_m": 0.5, "corner_radius_m": 0.1}
    ellison = effective_nose_radius_report(**kwargs, model=VELOCITY_GRADIENT)
    zoby = effective_nose_radius_report(**kwargs, model=VELOCITY_GRADIENT_ZOBY)
    k = kwargs["body_radius_m"] / kwargs["nose_radius_m"]
    assert zoby.effective_nose_radius_m == pytest.approx(
        ellison.effective_nose_radius_m * (1.0 + zoby_sullivan_shift(k)), rel=1e-12)
    assert zoby.effective_nose_radius_m > ellison.effective_nose_radius_m
    assert any("MODEL-FORM ALTERNATIVE" in note for note in zoby.notes)


def test_the_new_model_is_accepted_by_the_capsule_validator():
    # An M4-front-like capsule: K = R_b/R_n ~ 0.42, where the two sources disagree most.
    shape = {"nose_radius_m": 4.013, "diameter_m": 3.377, "shoulder_radius_m": 0.3377,
             "cone_half_angle_deg": 69.7, "aft_cone_angle_deg": 20.0, "length_m": 2.955}
    capsule = CapsuleGeometry(**shape,
                              effective_nose_radius_model=VELOCITY_GRADIENT_ZOBY)
    capsule.validate()
    ellison = CapsuleGeometry(**shape, effective_nose_radius_model=VELOCITY_GRADIENT)
    legacy = CapsuleGeometry(**shape, effective_nose_radius_model=CAP_RADIUS)
    assert legacy.effective_nose_radius_m == pytest.approx(shape["nose_radius_m"])
    assert ellison.effective_nose_radius_m < legacy.effective_nose_radius_m
    assert capsule.effective_nose_radius_m > ellison.effective_nose_radius_m


# =======================================================================================
# 6. propagation through a toy LINEAR model with a known analytic answer
# =======================================================================================

class _LinearToy:
    """y = a + b1*x1 + b2*x2, with x1 ~ N(m1, s1) and x2 ~ N(m2, s2) independent.

    Then E[y] = a + b1*m1 + b2*m2 and Var(y) = b1^2 s1^2 + b2^2 s2^2 exactly, and the
    p-th percentile of y is E[y] + z_p * sd(y). Propagating this through the SAME
    machinery the coupled model uses is the only way to know the machinery is right;
    checking a nonlinear physics model against itself proves nothing.
    """

    a, b1, b2 = 10.0, 3.0, -2.0
    m1, s1, m2, s2 = 1.0, 0.5, 4.0, 0.25

    @property
    def mean(self) -> float:
        return self.a + self.b1 * self.m1 + self.b2 * self.m2

    @property
    def std(self) -> float:
        return math.hypot(self.b1 * self.s1, self.b2 * self.s2)

    def percentile(self, p: float) -> float:
        return self.mean + float(norm.ppf(p / 100.0)) * self.std

    def sample(self, unit: np.ndarray) -> np.ndarray:
        x1 = norm.ppf(unit[:, 0], loc=self.m1, scale=self.s1)
        x2 = norm.ppf(unit[:, 1], loc=self.m2, scale=self.s2)
        return self.a + self.b1 * x1 + self.b2 * x2


def test_propagation_reproduces_a_linear_models_analytic_mean_and_variance():
    toy = _LinearToy()
    unit = common_random_numbers(2, 20_000, seed=11)
    y = toy.sample(unit)
    summary = summarise(y, percentiles=(5.0, 50.0, 95.0))
    assert summary.mean == pytest.approx(toy.mean, rel=2e-3)
    assert summary.std == pytest.approx(toy.std, rel=2e-2)
    # Tolerance is set against the output's OWN standard deviation, not against the
    # percentile's magnitude: a tail percentile of a 20 000-point Latin Hypercube is
    # accurate to a few percent of a sigma, which is not the same as a few percent of
    # its own value.
    for p in (5.0, 50.0, 95.0):
        assert summary.percentiles[f"p{p:g}"] == pytest.approx(
            toy.percentile(p), abs=0.05 * toy.std)


def test_analytic_violation_probability_is_recovered_within_its_own_interval():
    toy = _LinearToy()
    unit = common_random_numbers(2, 20_000, seed=13)
    y = toy.sample(unit)
    threshold = toy.mean + 1.2 * toy.std
    exact = float(norm.sf(1.2))
    result = violation_probability("toy", y > threshold)
    assert result.wilson[0] <= exact <= result.wilson[1]
    assert result.point == pytest.approx(exact, abs=0.01)


# =======================================================================================
# 7. the uncertain design space: one draw becomes one more coordinate
# =======================================================================================

def test_uncertain_space_applies_the_right_draw_and_records_its_index(design_space, model):
    unit = common_random_numbers(model.n_inputs, 5, seed=2)
    uspace = make_uncertain_space(design_space, model, unit)
    assert uspace.active[-1] == UQ_DRAW
    assert uspace.n_draws == 5
    reference = {v.name: v.reference for v in design_space.variables}
    for index in range(5):
        values = {**reference, UQ_DRAW: float(index)}
        config = uspace.config_for(values)
        assert config["uncertainty"]["draw_index"] == float(index)
        assert config["vehicle"]["mass_kg"] == pytest.approx(
            design_space.base_config["vehicle"]["mass_kg"]
            * uspace.draws[index]["vehicle_mass"])
        assert config["vehicle"]["geometry"]["effective_nose_radius_model"] == \
            uspace.draws[index]["effective_nose_radius_model"]


def test_patching_never_mutates_the_base_config(design_space, model):
    before = copy.deepcopy(design_space.base_config)
    unit = common_random_numbers(model.n_inputs, 3, seed=4)
    uspace = make_uncertain_space(design_space, model, unit)
    reference = {v.name: v.reference for v in design_space.variables}
    uspace.config_for({**reference, UQ_DRAW: 2.0})
    assert design_space.base_config == before


def test_design_vectors_run_draw_fastest(design_space, model):
    unit = common_random_numbers(model.n_inputs, 4, seed=5)
    uspace = make_uncertain_space(design_space, model, unit)
    x = np.array([[1.2, 0.5, 25.0, -3.0], [2.0, 0.6, 60.0, -4.0]])
    vectors = uspace.design_vectors(x, np.arange(4))
    assert vectors.shape == (8, 5)
    assert np.array_equal(vectors[:4, :4], np.tile(x[0], (4, 1)))
    assert np.array_equal(vectors[:4, 4], np.arange(4))
    assert np.array_equal(vectors[4:, 4], np.arange(4))


def test_the_same_design_and_draw_is_a_cache_hit(tmp_path, design_space, model):
    unit = common_random_numbers(model.n_inputs, 3, seed=6)
    uspace = make_uncertain_space(design_space, model, unit)
    store = CandidateStore(tmp_path / "c.csv")
    evaluator = BudgetedEvaluator(uspace, 20, store, run_id="T", method="m", seed=1)
    reference = np.array([[design_space.variable(n).reference
                           for n in design_space.active]])
    first = evaluate_under_uncertainty(evaluator, uspace, reference, np.arange(3))
    second = evaluate_under_uncertainty(evaluator, uspace, reference, np.arange(3))
    assert len(first) == len(second) == 3
    assert evaluator.used == 3           # common random numbers are free the second time
    assert evaluator.n_cache_hits == 3


# =======================================================================================
# 8. the end-to-end chain on the real evaluator (small N)
# =======================================================================================

@pytest.fixture(scope="module")
def propagated(design_space, model, tmp_path_factory):
    draws = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                       model.indices_of_kind("epistemic"), mode="nested", seed=17,
                       n_aleatory=4, n_epistemic_branches=3)
    uspace = make_uncertain_space(design_space, model, draws.unit)
    store = CandidateStore(tmp_path_factory.mktemp("prop") / "c.csv")
    evaluator = BudgetedEvaluator(uspace, len(draws), store, run_id="T",
                                  method="propagate", seed=17)
    reference = np.array([[design_space.variable(n).reference
                           for n in design_space.active]])
    frame = evaluate_under_uncertainty(evaluator, uspace, reference, np.arange(len(draws)))
    result = analyse("reference", frame, draws,
                     design_values={n: design_space.variable(n).reference
                                    for n in design_space.active},
                     outputs=("peak_heat_flux_w_m2", "peak_bondline_temperature_k"),
                     convergence_checkpoints=(4, 8, 12))
    return result, draws


def test_propagation_produces_a_spread_and_separates_its_two_sources(propagated):
    result, _ = propagated
    for name in ("peak_heat_flux_w_m2", "peak_bondline_temperature_k"):
        combined = result.combined[name]
        assert combined["n_finite"] == 12
        assert combined["std"] > 0.0
        assert combined["percentiles"]["p5"] < combined["percentiles"]["p95"]
        decomposition = result.decomposition[name]
        assert decomposition["separable"]
        assert decomposition["std_aleatory"] > 0.0
        assert decomposition["std_epistemic"] > 0.0
        assert "QUADRATURE" in decomposition["note"]


def test_a_mixed_sample_says_its_two_sources_are_not_separable(design_space, model,
                                                              tmp_path):
    draws = make_draws(model.n_inputs, model.indices_of_kind("aleatory"),
                       model.indices_of_kind("epistemic"), mode="mixed", seed=19,
                       n_aleatory=8)
    uspace = make_uncertain_space(design_space, model, draws.unit)
    store = CandidateStore(tmp_path / "c.csv")
    evaluator = BudgetedEvaluator(uspace, len(draws), store, run_id="T", method="m",
                                  seed=19)
    reference = np.array([[design_space.variable(n).reference
                           for n in design_space.active]])
    frame = evaluate_under_uncertainty(evaluator, uspace, reference, np.arange(len(draws)))
    result = analyse("reference", frame, draws, design_values={},
                     outputs=("peak_bondline_temperature_k",))
    decomposition = result.decomposition["peak_bondline_temperature_k"]
    assert not decomposition["separable"]
    assert math.isnan(decomposition["std_epistemic"])
    assert "pooled by construction" in decomposition["note"]


def test_analyse_refuses_a_frame_that_is_out_of_step_with_its_draws(propagated):
    result, draws = propagated
    with pytest.raises(ValueError, match="out of step"):
        analyse("x", result.rows.iloc[:5], draws, design_values={},
                outputs=("max_g",))


def test_every_constraint_violation_probability_carries_an_interval(propagated):
    result, _ = propagated
    assert "any" in result.violations
    for name, value in result.violations.items():
        assert value.n_samples == 12
        assert 0.0 <= value.wilson[0] <= value.wilson[1] <= 1.0
        assert value.name == name


# =======================================================================================
# 9. the section 39 comparison table and the report generator
# =======================================================================================

def test_a_missing_source_becomes_NOT_AVAILABLE_and_never_a_substituted_design(
        design_space):
    from src.aether.uncertainty.comparison import resolve_design

    values, run, reason = resolve_design({"source": "m4_selected", "key": "joint_knee"},
                                         design_space, m4_summary=None, m4_run_id="",
                                         robust_front=None, robust_run_id="")
    assert values is None
    assert "no M4 optimisation run" in reason

    values, run, reason = resolve_design({"source": "m7_robust", "key": "knee"},
                                         design_space, m4_summary={}, m4_run_id="X",
                                         robust_front=None, robust_run_id="")
    assert values is None
    assert "no robust optimisation front" in reason

    values, run, reason = resolve_design({"source": "design_space_reference"},
                                         design_space, m4_summary=None, m4_run_id="",
                                         robust_front=None, robust_run_id="")
    assert reason == ""
    assert values["diameter_m"] == design_space.variable("diameter_m").reference


def test_comparison_row_reports_tpi_and_flags_it_as_discarded(design_space):
    from src.aether.scoring.tpi import TPIConfig
    from src.aether.uncertainty.comparison import TPI_FOOTNOTE, evaluate_row

    reference = {v.name: v.reference for v in design_space.variables}
    row = evaluate_row("Baseline", "design_space_reference", reference, design_space,
                       TPIConfig(t_reference_k=400.0, depth_limit_m=0.015),
                       "configs/design_space.yaml")
    assert row.available
    assert row.metrics["tpi_k_m_s"] > 0.0
    assert row.metrics["peak_bondline_temperature_k"] > 0.0
    assert "DISCARD" in TPI_FOOTNOTE
    assert "rank-regression" in TPI_FOOTNOTE or "reconstructible" in TPI_FOOTNOTE


def test_comparison_row_quotes_the_stored_value_and_the_difference(design_space):
    from src.aether.scoring.tpi import TPIConfig
    from src.aether.uncertainty.comparison import evaluate_row

    reference = {v.name: v.reference for v in design_space.variables}
    stored = {"peak_heat_flux_w_m2": 1.0e6}
    row = evaluate_row("x", "m4_selected", reference, design_space,
                       TPIConfig(t_reference_k=400.0, depth_limit_m=0.015), "M4-OPT-X",
                       stored)
    assert row.stored_metrics["peak_heat_flux_w_m2"] == 1.0e6
    assert row.deltas["peak_heat_flux_w_m2"] == pytest.approx(
        row.metrics["peak_heat_flux_w_m2"] - 1.0e6)


def test_the_stale_banner_names_every_reason_and_says_what_was_done():
    from src.aether.uncertainty.guards import m4_front_is_current, stale_banner

    snapshot = {"study": {"variables": {}, "base_overrides": {}, "objectives": []},
                "base": {"vehicle": {"geometry": {"effective_nose_radius_model":
                                                  "cap_radius"}},
                         "limits": {"max_bluntness_ratio": 1.2}}}
    study = {"variables": {}, "base_overrides": {}, "objectives": []}
    base = {"vehicle": {"geometry": {"effective_nose_radius_model": "velocity_gradient"}},
            "limits": {"max_bluntness_ratio": None}}
    reasons = m4_front_is_current(snapshot, study, base)
    assert any("effective-nose-radius" in r for r in reasons)
    assert any("max_bluntness_ratio" in r for r in reasons)
    banner = stale_banner(reasons, "M4-OPT-X")
    assert "STALE SOURCE" in banner
    assert "RE-EVALUATED" in banner
    assert stale_banner([], "M4-OPT-X") == ""


def test_the_report_generates_offline_from_a_summary_alone(tmp_path, design_space, model):
    """Spec section 50: a stranger with the result files and no compute rebuilds the report."""
    from src.aether.uncertainty.report import write_m7_report

    summary = {
        "run_id": "M7-TEST", "git_commit": "abc1234", "git_dirty": False,
        "source_hash": "deadbeef", "workers": 6, "wall_s": 61.0, "n_evaluations": 12,
        "aero_model": "constant", "fidelity": 0,
        "objectives": ["peak_heat_flux_w_m2", "peak_bondline_temperature_k"],
        "units": {"peak_heat_flux_w_m2": "W m^-2",
                  "peak_bondline_temperature_k": "K"},
        "allowables": {"peak_bondline_temperature_k": 450.0},
        "uncertainty_model": {**model.to_dict(), "density_profile": None},
        "draws": {"mode": "nested", "seed": 1, "n_samples": 12, "n_inputs": 9,
                  "n_epistemic_branches": 3, "n_aleatory": 4},
        "stale_warnings": [], "sizing": {}, "propagation": {}, "figures": [],
    }
    path = write_m7_report(REPO_ROOT, summary, tmp_path / "M7.md")
    text = path.read_text()
    assert "# M7 — Uncertainty propagation and robust design" in text
    assert "M7-TEST" in text
    assert "lower bound on the real uncertainty" in text
    # sections with no result say so rather than printing a table of blanks
    assert "Not run in this run" in text
    assert "engineering judgment" in text
