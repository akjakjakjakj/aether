"""M4: design space, budgeted evaluation, candidate persistence, Pareto tools, optimisers.

Nothing in this package integrates a trajectory or a TPS stack. Physics is reached only
through `BudgetedEvaluator`, which calls the canonical `evaluate_design` (spec section 19).
"""

from .analysis import (
    audit_exploits,
    feasible_front,
    hypervolume_curve,
    select_designs,
)
from .budget import (
    BudgetedEvaluator,
    BudgetExhausted,
    constraint_violation,
    evaluate_candidate,
    objective_matrix,
)
from .design_space import DesignSpace, DesignVariable, load_design_space
from .optimizers import METHODS, run_lhs_search, run_nsga2, run_scalarised_de
from .pareto import (
    dominates,
    hypervolume_2d,
    knee_point,
    normalise,
    normalised_hypervolume,
    pareto_front,
    spacing_metric,
)
from .persistence import CandidateStore, load_candidates
from .sampling import (
    SobolResult,
    given_data_first_order,
    latin_hypercube,
    one_at_a_time,
    saltelli_sample,
    sobol_indices,
)

__all__ = [
    "METHODS",
    "BudgetExhausted",
    "BudgetedEvaluator",
    "CandidateStore",
    "DesignSpace",
    "DesignVariable",
    "SobolResult",
    "audit_exploits",
    "constraint_violation",
    "dominates",
    "evaluate_candidate",
    "feasible_front",
    "given_data_first_order",
    "hypervolume_2d",
    "hypervolume_curve",
    "knee_point",
    "latin_hypercube",
    "load_candidates",
    "load_design_space",
    "normalise",
    "normalised_hypervolume",
    "objective_matrix",
    "one_at_a_time",
    "pareto_front",
    "run_lhs_search",
    "run_nsga2",
    "run_scalarised_de",
    "saltelli_sample",
    "select_designs",
    "sobol_indices",
    "spacing_metric",
]
