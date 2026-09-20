"""Gate G4 - Richardson extrapolation / GCI (Celik et al. 2008)."""

import math

import pytest

from src.aether.cfd.gci import grid_convergence_index, observed_order


def test_hand_worked_constant_ratio_example():
    """Worked by hand. phi = 1 + 0.5 h^2 on h = 1, 2, 4:
    fine 1.5, medium 3.0, coarse 9.0;  eps21 = 1.5, eps32 = 6.0;
    p = ln(6/1.5)/ln 2 = 2;  phi_ext = (4*1.5 - 3)/(4 - 1) = 1.0;
    e_a21 = 1.5/1.5 = 1.0;  GCI_fine = 1.25*1.0/(4 - 1) = 0.41667;
    e_a32 = 6/3 = 2;  GCI_32 = 1.25*2/(4 - 1) = 0.83333;
    asymptotic ratio = 0.83333/(4*0.41667) = 0.5, which equals phi_fine/phi_medium because
    the two GCIs are normalised by different solutions (it tends to 1 as they converge)."""
    r = grid_convergence_index("phi", 1.5, 3.0, 9.0, 1.0, 2.0, 4.0)
    assert r.convergence_type == "monotone"
    assert r.observed_order == pytest.approx(2.0, abs=1e-10)
    assert r.phi_extrapolated == pytest.approx(1.0, abs=1e-10)
    assert r.rel_error_fine_medium == pytest.approx(1.0, abs=1e-12)
    assert r.gci_fine == pytest.approx(1.25 / 3.0, abs=1e-10)
    assert r.gci_medium == pytest.approx(1.25 * 2.0 / 3.0, abs=1e-10)
    assert r.asymptotic_ratio == pytest.approx(0.5, abs=1e-10)


def test_celik_2008_published_example():
    """Celik et al. (2008), Table 1, first column: N = 18000/8000/4500 so r21 = 1.5,
    r32 = 1.333; phi = 6.063, 5.972, 5.863. Published: p = 1.53, phi_ext = 6.1685,
    e_a21 = 1.5%, e_ext21 = 1.7%, GCI_fine = 2.2%."""
    h1, h2, h3 = (1 / 18000) ** 0.5, (1 / 8000) ** 0.5, (1 / 4500) ** 0.5
    r = grid_convergence_index("phi", 6.063, 5.972, 5.863, h1, h2, h3)
    assert r.r21 == pytest.approx(1.5, abs=1e-9)
    assert r.r32 == pytest.approx(1.3333, abs=1e-4)
    assert r.observed_order == pytest.approx(1.53, abs=0.01)
    assert r.phi_extrapolated == pytest.approx(6.1685, abs=2e-3)
    assert 100 * r.rel_error_fine_medium == pytest.approx(1.5, abs=0.05)
    assert 100 * r.rel_error_extrapolated == pytest.approx(1.7, abs=0.05)
    assert 100 * r.gci_fine == pytest.approx(2.2, abs=0.05)


@pytest.mark.parametrize("p_true", [1.0, 1.7, 2.0])
def test_recovers_manufactured_order_with_unequal_ratios(p_true):
    exact, c = 0.9, 0.3
    h = (0.01, 0.015, 0.027)   # r21 = 1.5, r32 = 1.8
    phi = [exact + c * hi**p_true for hi in h]
    r = grid_convergence_index("phi", *phi, *h)
    assert r.observed_order == pytest.approx(p_true, abs=1e-8)
    assert r.phi_extrapolated == pytest.approx(exact, abs=1e-10)
    # exactly phi_fine/phi_medium for exact power-law data (different normalisations)
    assert r.asymptotic_ratio == pytest.approx(phi[0] / phi[1], rel=1e-8)


def test_oscillatory_convergence_is_flagged_not_hidden():
    r = grid_convergence_index("phi", 1.00, 1.02, 0.99, 1.0, 2.0, 4.0)
    assert r.convergence_type == "oscillatory"
    assert "oscillatory" in r.note


def test_divergence_is_flagged():
    r = grid_convergence_index("phi", 1.00, 1.10, 1.12, 1.0, 2.0, 4.0)
    assert r.convergence_type == "divergent"


def test_identical_solutions_report_zero_uncertainty():
    r = grid_convergence_index("phi", 2.0, 2.0, 2.0, 1.0, 2.0, 4.0)
    assert r.convergence_type == "converged_to_tolerance"
    assert r.gci_fine == 0.0


def test_stalled_pair_does_not_invent_an_order():
    r = grid_convergence_index("phi", 2.0, 2.0, 2.1, 1.0, 2.0, 4.0)
    assert math.isnan(r.observed_order) and math.isnan(r.gci_fine)


def test_grid_order_is_validated():
    with pytest.raises(ValueError):
        grid_convergence_index("phi", 1.0, 1.1, 1.2, 4.0, 2.0, 1.0)


def test_observed_order_constant_ratio_closed_form():
    assert observed_order(0.01, 0.04, 2.0, 2.0) == pytest.approx(2.0, abs=1e-12)
