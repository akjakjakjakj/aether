"""Dominance, hypervolume, spacing and knee - against HAND-WORKED cases.

NR-04 recorded an inverted dominance test in an earlier `pareto_front`. Every expected
value below was worked out on paper, not produced by the code under test.
"""

import numpy as np
import pytest

from src.aether.optimization.pareto import (
    dominates,
    hypervolume_2d,
    knee_point,
    normalise,
    normalised_hypervolume,
    pareto_front,
    spacing_metric,
)
from src.aether.studies import pareto_front as studies_pareto_front


def test_dominance_direction_is_minimisation():
    assert dominates([1.0, 1.0], [2.0, 2.0])
    assert not dominates([2.0, 2.0], [1.0, 1.0])


def test_better_in_one_equal_in_other_dominates():
    assert dominates([1.0, 2.0], [1.0, 3.0])
    assert not dominates([1.0, 3.0], [1.0, 2.0])


def test_trade_off_points_do_not_dominate_each_other():
    assert not dominates([1.0, 3.0], [2.0, 2.0])
    assert not dominates([2.0, 2.0], [1.0, 3.0])


def test_equal_points_do_not_dominate():
    assert not dominates([1.0, 1.0], [1.0, 1.0])


def test_nan_neither_dominates_nor_is_dominated():
    assert not dominates([np.nan, 0.0], [1.0, 1.0])
    assert not dominates([0.0, 0.0], [np.nan, 1.0])


def test_front_of_a_hand_worked_set():
    # A(1,5) B(2,3) C(4,1) are mutually non-dominated. D(3,4) is dominated by B,
    # E(5,5) by everything, F(2,6) by A and B.
    pts = np.array([[1, 5], [2, 3], [4, 1], [3, 4], [5, 5], [2, 6]], dtype=float)
    assert pareto_front(pts).tolist() == [0, 1, 2]


def test_front_is_monotone_for_random_clouds():
    rng = np.random.default_rng(3)
    pts = rng.random((400, 2))
    front = pts[pareto_front(pts)]
    front = front[np.argsort(front[:, 0])]
    assert np.all(np.diff(front[:, 0]) > 0)
    assert np.all(np.diff(front[:, 1]) < 0)
    for p in pts:  # nothing in the cloud dominates a front member
        assert not any(dominates(p, f) for f in front)


def test_front_ignores_nan_rows_and_keeps_duplicates():
    pts = np.array([[1.0, 1.0], [np.nan, 0.0], [1.0, 1.0], [2.0, 2.0]])
    assert pareto_front(pts).tolist() == [0, 2]


def test_studies_reexport_is_the_same_function():
    assert studies_pareto_front is pareto_front


def test_hypervolume_single_point_is_a_rectangle():
    assert hypervolume_2d(np.array([[1.0, 2.0]]), np.array([4.0, 5.0])) == pytest.approx(9.0)


def test_hypervolume_staircase_hand_calculation():
    # Front (1,3) (2,2) (3,1), reference (4,4). Sweep left to right:
    #   x in [1,2): height 4-3 = 1 -> 1
    #   x in [2,3): height 4-2 = 2 -> 2
    #   x in [3,4): height 4-1 = 3 -> 3        total = 6
    front = np.array([[1, 3], [2, 2], [3, 1]], dtype=float)
    assert hypervolume_2d(front, np.array([4.0, 4.0])) == pytest.approx(6.0)


def test_hypervolume_is_unchanged_by_dominated_and_duplicate_points():
    front = np.array([[1, 3], [2, 2], [3, 1]], dtype=float)
    noisy = np.vstack([front, [[2.5, 2.5], [3.5, 3.5], [2, 2]]])
    assert hypervolume_2d(noisy, np.array([4.0, 4.0])) == pytest.approx(6.0)


def test_hypervolume_is_order_invariant():
    front = np.array([[3, 1], [1, 3], [2, 2]], dtype=float)
    assert hypervolume_2d(front, np.array([4.0, 4.0])) == pytest.approx(6.0)


def test_points_outside_the_reference_box_contribute_nothing():
    pts = np.array([[5.0, 0.5], [0.5, 5.0], [4.0, 1.0]])  # last one sits ON the boundary
    assert hypervolume_2d(pts, np.array([4.0, 4.0])) == 0.0
    assert hypervolume_2d(np.empty((0, 2)), np.array([4.0, 4.0])) == 0.0


def test_hypervolume_grows_monotonically_as_points_are_added():
    rng = np.random.default_rng(0)
    pts = rng.random((60, 2))
    ref = np.array([1.0, 1.0])
    values = [hypervolume_2d(pts[:n], ref) for n in range(1, 61)]
    assert np.all(np.diff(values) >= -1e-15)


def test_normalised_hypervolume_of_the_ideal_point_is_one():
    ideal, ref = np.array([0.0, 300.0]), np.array([2.0e6, 450.0])
    assert normalised_hypervolume(np.array([[0.0, 300.0]]), ideal, ref) == pytest.approx(1.0)
    # (1e6, 375 K) is the centre of the rectangle -> one quarter
    assert normalised_hypervolume(np.array([[1.0e6, 375.0]]), ideal, ref) == pytest.approx(0.25)


def test_normalise_rejects_a_degenerate_box():
    with pytest.raises(ValueError):
        normalise(np.zeros((1, 2)), np.array([0.0, 1.0]), np.array([1.0, 1.0]))


def test_spacing_is_zero_for_an_evenly_spaced_front():
    front = np.array([[0.0, 1.0], [0.25, 0.75], [0.5, 0.5], [0.75, 0.25], [1.0, 0.0]])
    assert spacing_metric(front) == pytest.approx(0.0, abs=1e-15)


def test_spacing_hand_calculation():
    # nearest-neighbour L1 distances: 0.2, 0.2, 1.6 -> mean 2/3
    # S = sqrt(((0.2-2/3)^2 * 2 + (1.6-2/3)^2) / 2)
    front = np.array([[0.0, 1.0], [0.1, 0.9], [0.9, 0.1]])
    d = np.array([0.2, 0.2, 1.6])
    expected = np.sqrt(np.sum((d - d.mean()) ** 2) / 2)
    assert spacing_metric(front) == pytest.approx(expected)
    assert np.isnan(spacing_metric(front[:2]))


def test_knee_is_the_point_bulging_towards_the_ideal():
    front = np.array([[0.0, 1.0], [0.2, 0.2], [0.6, 0.15], [1.0, 0.0]])
    assert knee_point(front) == 1


def test_knee_ignores_a_point_on_the_far_side_of_the_chord():
    front = np.array([[0.0, 1.0], [0.8, 0.8], [0.45, 0.45], [1.0, 0.0]])
    assert knee_point(front) == 2
