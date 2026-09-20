"""Verification of the Thermal Penetration Index against closed-form cases.

TPI is a double integral, so every one of these builds a temperature field whose double
integral can be written down by hand and checks the code reproduces it. Nothing here
checks the solver; these tests would pass if the conduction model were nonsense, which
is the point - they isolate the metric.
"""

import numpy as np
import pytest

from src.aether.scoring import TPIConfig, thermal_penetration_index, weight_profile


class _FakeTPSResult:
    """Minimal stand-in carrying exactly what `thermal_penetration_index` reads.

    A hand-built field is the only way to have an exact expected value: any field taken
    from the real solver would have to be checked against the same quadrature the code
    under test uses, which proves nothing.
    """

    def __init__(self, time_s, depth_m, cell_width_m, temperature_k):
        self.time_s = np.asarray(time_s, dtype=float)
        self.depth_m = np.asarray(depth_m, dtype=float)
        self.cell_width_m = np.asarray(cell_width_m, dtype=float)
        self.temperature_k = np.asarray(temperature_k, dtype=float)


def _uniform_field(n_cells=20, length_m=0.020, duration_s=100.0, n_t=201,
                   t_field_k=500.0):
    """Spatially and temporally constant temperature field."""
    dx = length_m / n_cells
    depth = (np.arange(n_cells) + 0.5) * dx
    widths = np.full(n_cells, dx)
    time = np.linspace(0.0, duration_s, n_t)
    temps = np.full((n_t, n_cells), t_field_k)
    return _FakeTPSResult(time, depth, widths, temps)


def test_constant_field_gives_exactly_delta_t_times_length_times_duration():
    """TPI = (T - T_ref) * L * tau for a uniform field and uniform unit weighting."""
    res = _uniform_field(t_field_k=500.0, length_m=0.020, duration_s=100.0)
    cfg = TPIConfig(t_reference_k=400.0, weighting="uniform", normalise_weights=False)
    out = thermal_penetration_index(res, cfg)
    assert out.tpi_k_m_s == pytest.approx(100.0 * 0.020 * 100.0)
    assert out.domain_length_m == pytest.approx(0.020)


def test_field_below_reference_contributes_nothing():
    """max(T - T_ref, 0) means a cold stack scores exactly zero, not a small number."""
    res = _uniform_field(t_field_k=350.0)
    out = thermal_penetration_index(res, TPIConfig(t_reference_k=400.0))
    assert out.tpi_k_m_s == 0.0
    assert out.deepest_exceeded_m == 0.0


def test_linear_ramp_in_time_integrates_to_half_a_tau_squared():
    """T(t) = T_ref + a t over [0, tau]  =>  INT dt = a tau^2 / 2 at every depth."""
    n_cells, length_m, tau, a = 10, 0.010, 60.0, 2.0
    dx = length_m / n_cells
    time = np.linspace(0.0, tau, 6001)
    temps = np.tile((400.0 + a * time)[:, None], (1, n_cells))
    res = _FakeTPSResult(time, (np.arange(n_cells) + 0.5) * dx,
                         np.full(n_cells, dx), temps)
    cfg = TPIConfig(t_reference_k=400.0, weighting="uniform", normalise_weights=False)
    out = thermal_penetration_index(res, cfg)
    assert out.tpi_k_m_s == pytest.approx(a * tau**2 / 2.0 * length_m, rel=1e-6)


def test_depth_limit_truncates_the_domain_proportionally():
    """Half the depth of a uniform field is exactly half the index."""
    res = _uniform_field(n_cells=20, length_m=0.020)
    full = thermal_penetration_index(
        res, TPIConfig(t_reference_k=400.0, normalise_weights=False))
    half = thermal_penetration_index(
        res, TPIConfig(t_reference_k=400.0, normalise_weights=False, depth_limit_m=0.010))
    assert half.tpi_k_m_s == pytest.approx(0.5 * full.tpi_k_m_s, rel=1e-12)
    assert half.n_cells_in_domain == 10


def test_normalised_weights_agree_across_every_family_on_a_uniform_field():
    """The invariant that makes cross-family comparison meaningful.

    If the depth-average of w is 1 then a field with no depth structure must score the
    same under every family. Any difference between families on a REAL field is then
    attributable to the field's shape, not to the arbitrary scale of w.
    """
    res = _uniform_field(n_cells=60, length_m=0.015)
    values = []
    for weighting, params in (
        ("uniform", {}),
        ("linear_depth", {}),
        ("exponential_depth", {"decay": 4.0}),
        ("bondline_gaussian", {"sigma_m": 0.003}),
    ):
        cfg = TPIConfig(t_reference_k=400.0, weighting=weighting, weight_params=params,
                        normalise_weights=True)
        values.append(thermal_penetration_index(res, cfg).tpi_k_m_s)
    assert np.allclose(values, values[0], rtol=1e-10)


def test_depth_weighting_prefers_a_hot_interior_over_a_hot_surface():
    """The whole reason a weighting family exists.

    Two fields with the SAME total exceedance, one hot at the surface and one hot at the
    back. A uniform weighting cannot tell them apart; a depth weighting must.
    """
    n_cells, length_m = 20, 0.020
    dx = length_m / n_cells
    depth = (np.arange(n_cells) + 0.5) * dx
    time = np.linspace(0.0, 100.0, 201)

    hot_front = np.full((len(time), n_cells), 400.0)
    hot_front[:, :5] = 500.0
    hot_back = np.full((len(time), n_cells), 400.0)
    hot_back[:, -5:] = 500.0

    front = _FakeTPSResult(time, depth, np.full(n_cells, dx), hot_front)
    back = _FakeTPSResult(time, depth, np.full(n_cells, dx), hot_back)

    flat = TPIConfig(t_reference_k=400.0, weighting="uniform", normalise_weights=True)
    assert (thermal_penetration_index(front, flat).tpi_k_m_s
            == pytest.approx(thermal_penetration_index(back, flat).tpi_k_m_s))

    deep = TPIConfig(t_reference_k=400.0, weighting="exponential_depth",
                     weight_params={"decay": 4.0}, normalise_weights=True)
    assert (thermal_penetration_index(back, deep).tpi_k_m_s
            > 3.0 * thermal_penetration_index(front, deep).tpi_k_m_s)


def test_index_falls_monotonically_as_the_reference_temperature_rises():
    res = _uniform_field(t_field_k=520.0)
    values = [
        thermal_penetration_index(res, TPIConfig(t_reference_k=tref)).tpi_k_m_s
        for tref in (350.0, 400.0, 450.0, 500.0, 550.0)
    ]
    assert all(values[i] > values[i + 1] or values[i + 1] == 0.0
               for i in range(len(values) - 1)), values
    assert values[-1] == 0.0


def test_index_is_linear_in_exceedance_and_in_duration():
    """Doubling either the exceedance or the duration doubles the index."""
    base = thermal_penetration_index(
        _uniform_field(t_field_k=500.0, duration_s=100.0),
        TPIConfig(t_reference_k=400.0, normalise_weights=False)).tpi_k_m_s
    hotter = thermal_penetration_index(
        _uniform_field(t_field_k=600.0, duration_s=100.0),
        TPIConfig(t_reference_k=400.0, normalise_weights=False)).tpi_k_m_s
    longer = thermal_penetration_index(
        _uniform_field(t_field_k=500.0, duration_s=200.0),
        TPIConfig(t_reference_k=400.0, normalise_weights=False)).tpi_k_m_s
    assert hotter == pytest.approx(2.0 * base, rel=1e-9)
    assert longer == pytest.approx(2.0 * base, rel=1e-9)


def test_exponential_decay_zero_recovers_the_uniform_family():
    """A one-parameter generalisation must actually contain the thing it generalises."""
    depth = np.linspace(0.0005, 0.0195, 20)
    cfg = TPIConfig(t_reference_k=400.0, weighting="exponential_depth",
                    weight_params={"decay": 0.0})
    assert np.allclose(weight_profile(depth, 0.020, cfg), 1.0)


def test_peak_exceedance_depth_reports_where_the_index_came_from():
    n_cells, length_m = 20, 0.020
    dx = length_m / n_cells
    depth = (np.arange(n_cells) + 0.5) * dx
    time = np.linspace(0.0, 50.0, 101)
    temps = np.full((len(time), n_cells), 400.0)
    temps[:, 12] = 700.0
    res = _FakeTPSResult(time, depth, np.full(n_cells, dx), temps)
    out = thermal_penetration_index(res, TPIConfig(t_reference_k=400.0))
    assert out.peak_exceedance_depth_m == pytest.approx(depth[12])
    assert out.deepest_exceeded_m == pytest.approx(depth[12])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"t_reference_k": 400.0, "weighting": "made_up_family"},
        {"t_reference_k": -1.0},
        {"t_reference_k": 400.0, "depth_limit_m": -0.01},
        {"t_reference_k": 400.0, "weighting": "bondline_gaussian"},
        {"t_reference_k": 400.0, "weighting": "bondline_gaussian",
         "weight_params": {"sigma_m": 0.0}},
        {"t_reference_k": 400.0, "weighting": "exponential_depth",
         "weight_params": {"decay": -2.0}},
    ],
)
def test_rejects_undeclarable_configurations(kwargs):
    """A TPI number without a declared family, datum and domain is meaningless, so the
    config refuses to exist rather than silently defaulting."""
    with pytest.raises(ValueError):
        TPIConfig(**kwargs)


def test_config_round_trips_through_yaml_shaped_dicts():
    cfg = TPIConfig(t_reference_k=420.0, weighting="bondline_gaussian",
                    weight_params={"sigma_m": 0.004}, normalise_weights=False,
                    depth_limit_m=0.015)
    assert TPIConfig.from_dict(cfg.to_dict()) == cfg


def test_depth_limit_that_excludes_everything_raises_rather_than_returning_zero():
    res = _uniform_field()
    with pytest.raises(ValueError, match="excludes every cell"):
        thermal_penetration_index(res, TPIConfig(t_reference_k=400.0, depth_limit_m=1e-9))


def test_tpi_on_a_real_solver_result_is_bounded_by_its_trivial_bounds():
    """Sanity coupling to the actual solver: 0 <= TPI <= (T_max - T_ref) * L * tau."""
    from src.aether.tps import Layer, TPSStack, solve_tps

    t = np.linspace(0.0, 600.0, 1201)
    q = np.where(t < 120.0, 1.0e6, 0.0)
    stack = TPSStack([Layer("ins", 0.015, 0.30, 280.0, 1200.0, 120),
                      Layer("str", 0.010, 150.0, 2700.0, 900.0, 20)],
                     emissivity=0.85, bondline_after_layer=0, t_initial_k=300.0)
    res = solve_tps(stack, t, q)
    cfg = TPIConfig(t_reference_k=400.0, weighting="uniform", normalise_weights=False,
                    depth_limit_m=0.015)
    out = thermal_penetration_index(res, cfg)
    ceiling = (res.temperature_k.max() - 400.0) * out.domain_length_m * (t[-1] - t[0])
    assert 0.0 < out.tpi_k_m_s < ceiling
