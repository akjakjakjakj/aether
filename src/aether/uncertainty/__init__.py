"""M7: uncertainty propagation and robust design (spec sections 27, 28, 39).

Nothing in this package integrates a trajectory or a TPS stack. Every sample reaches the
physics through `optimization.BudgetedEvaluator` -> `evaluate_design`, exactly as every
DOE, sweep and optimiser does, so an uncertainty sample and an optimisation candidate are
the same kind of thing and are logged in the same store.
"""

from .attribution import Attribution, attribute, saltelli_unit_points
from .distributions import (
    Discrete,
    Distribution,
    LogNormal,
    Normal,
    Triangular,
    Uniform,
    build_distribution,
)
from .inputs import (
    ALEATORY,
    EPISTEMIC,
    InputUnavailable,
    UncertainInput,
    UncertaintyModel,
)
from .propagate import (
    DesignPropagation,
    analyse,
    evaluate_under_uncertainty,
    robust_objective_values,
)
from .robust import (
    RobustScore,
    RobustSettings,
    ShortcutVerification,
    robust_front,
    run_robust_nsga2,
    score_sample,
    verify_shortcut,
)
from .sampling import DrawSet, common_random_numbers, make_draws
from .space import UncertainDesignSpace, design_only, make_uncertain_space
from .statistics import (
    SampleSummary,
    ViolationProbability,
    bootstrap_ci,
    clopper_pearson_interval,
    converged,
    convergence_table,
    quantile,
    summarise,
    violation_probability,
    wilson_interval,
)

__all__ = [
    "ALEATORY",
    "EPISTEMIC",
    "Attribution",
    "DesignPropagation",
    "Discrete",
    "Distribution",
    "DrawSet",
    "InputUnavailable",
    "LogNormal",
    "Normal",
    "RobustScore",
    "RobustSettings",
    "SampleSummary",
    "ShortcutVerification",
    "Triangular",
    "UncertainDesignSpace",
    "UncertainInput",
    "UncertaintyModel",
    "Uniform",
    "ViolationProbability",
    "analyse",
    "attribute",
    "bootstrap_ci",
    "build_distribution",
    "clopper_pearson_interval",
    "common_random_numbers",
    "convergence_table",
    "converged",
    "design_only",
    "evaluate_under_uncertainty",
    "make_draws",
    "make_uncertain_space",
    "quantile",
    "robust_front",
    "robust_objective_values",
    "run_robust_nsga2",
    "saltelli_unit_points",
    "score_sample",
    "summarise",
    "verify_shortcut",
    "violation_probability",
    "wilson_interval",
]
