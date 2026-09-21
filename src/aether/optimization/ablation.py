"""M5 analysis: matched-budget method table, exact small-sample tests, surrogate scoring,
agent scoring and the per-method metric-gaming audit. Works on persisted logs only - it
never evaluates anything and never calls an LLM, so `--report-only` reproduces a report.

Conceptual anchor (the statistics)
----------------------------------
Five seeds per method is a small sample, so no normality is assumed anywhere:

  permutation test   Under "the two methods are the same", which 5 of the 10 hypervolumes
                     were labelled A is arbitrary. All C(10,5) = 252 relabellings are
                     enumerated and the rank-sum recomputed; the p-value is the share at
                     least as extreme as observed. This IS the exact Mann-Whitney test,
                     and it stays exact with ties. Smallest possible p: 1/252 one-sided.
  signed-rank test   When two methods share their initial design seed for seed, the
                     seed-wise differences are paired; all 2^5 = 32 sign patterns are
                     enumerated. Smallest possible p: 1/32 one-sided, 2/32 TWO-sided - a
                     two-sided paired test at n = 5 can never reach 0.05.
  A12                Vargha-Delaney effect size: probability a random run of A beats a
                     random run of B (0.5 = no difference, 1.0 = A always wins). Reported
                     because a p-value at n = 5 mostly measures n.
"""

from __future__ import annotations

import math
from itertools import combinations, product
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from ..surrogate.gp import GPSurrogate
from ..surrogate.model import DesignSurrogate
from ..surrogate.validation import holdout_validation, regression_metrics
from .analysis import feasible_front, hypervolume_curve
from .budget import MARGIN_NAMES
from .design_space import DesignSpace
from .guards import (  # noqa: F401  (moved to guards.py at M6; old import path kept)
    SourceChanged,
    screening_is_current,
    source_tree_hash,
)
from .pareto import normalise, spacing_metric

LLM_KINDS = ("ai_agent", "ai_adaptive")


# ---------------------------------------------------------------------------------------
# exact small-sample statistics
# ---------------------------------------------------------------------------------------
def a12(a: np.ndarray, b: np.ndarray) -> float:
    """Vargha-Delaney A: P(A > B) + 0.5 P(A == B). Larger hypervolume is better."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    greater = np.sum(a[:, None] > b[None, :])
    equal = np.sum(a[:, None] == b[None, :])
    return float((greater + 0.5 * equal) / (a.size * b.size))


def permutation_rank_test(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    """Exact two-sample rank-sum permutation test (Mann-Whitney with midranks)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    ranks = rankdata(np.concatenate([a, b]))
    n_a, n = a.size, a.size + b.size
    observed = float(ranks[:n_a].sum())
    sums = np.array([ranks[list(idx)].sum() for idx in combinations(range(n), n_a)])
    centre = n_a * (n + 1) / 2.0
    eps = 1e-12
    return {
        "p_greater": float(np.mean(sums >= observed - eps)),
        "p_less": float(np.mean(sums <= observed + eps)),
        "p_two_sided": float(np.mean(np.abs(sums - centre) >= abs(observed - centre) - eps)),
        "min_attainable_p_one_sided": 1.0 / len(sums),
    }


def signed_rank_test(diff: np.ndarray) -> dict[str, float]:
    """Exact Wilcoxon signed-rank test on paired differences; zero differences dropped."""
    diff = np.asarray(diff, dtype=float)
    diff = diff[diff != 0.0]
    n = diff.size
    if n == 0:
        return {"n_nonzero": 0, "p_greater": 1.0, "p_less": 1.0, "p_two_sided": 1.0,
                "min_attainable_p_two_sided": 1.0}
    ranks = rankdata(np.abs(diff))
    observed = float(ranks[diff > 0].sum())
    sums = np.array([ranks[np.array(signs, dtype=bool)].sum()
                     for signs in product((False, True), repeat=n)])
    centre = ranks.sum() / 2.0
    eps = 1e-12
    return {
        "n_nonzero": int(n),
        "p_greater": float(np.mean(sums >= observed - eps)),
        "p_less": float(np.mean(sums <= observed + eps)),
        "p_two_sided": float(np.mean(np.abs(sums - centre) >= abs(observed - centre) - eps)),
        "min_attainable_p_two_sided": 2.0 / len(sums),
    }


def holm(p_values: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order."""
    m = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * p_values[idx])
        adjusted[idx] = min(1.0, running)
    return adjusted.tolist()


def compare(a: np.ndarray, b: np.ndarray, *, paired: bool) -> dict[str, Any]:
    """A versus B on per-seed hypervolumes (same seed order in both when `paired`)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    out: dict[str, Any] = {
        "mean_a": float(a.mean()), "mean_b": float(b.mean()),
        "mean_difference": float(a.mean() - b.mean()),
        "a12": a12(a, b), "rank_test": permutation_rank_test(a, b), "paired": paired,
    }
    if paired and a.size == b.size:
        diff = a - b
        out["paired_differences"] = diff.tolist()
        out["seeds_a_better"] = int(np.sum(diff > 0))
        out["signed_rank_test"] = signed_rank_test(diff)
    return out


# ---------------------------------------------------------------------------------------
# method table
# ---------------------------------------------------------------------------------------
def _mean_pairwise_distance(x_unit: np.ndarray) -> float:
    if len(x_unit) < 2:
        return float("nan")
    dist = np.linalg.norm(x_unit[:, None, :] - x_unit[None, :, :], axis=2)
    return float(dist[np.triu_indices(len(x_unit), 1)].mean())


def _unit(frame: pd.DataFrame, space: DesignSpace) -> np.ndarray:
    return space.to_unit(frame[[f"x__{n}" for n in space.active]].to_numpy(dtype=float))


def method_table(frame: pd.DataFrame, space: DesignSpace, objectives: tuple[str, ...],
                 hv_cfg: dict[str, Any], checkpoints: np.ndarray, methods: list[str]
                 ) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    ideal = np.array([hv_cfg["ideal_point"][n] for n in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][n] for n in objectives], dtype=float)
    table: dict[str, Any] = {}
    curves: dict[str, np.ndarray] = {}
    for method in methods:
        sub = frame[frame["method"] == method]
        seeds = sorted(int(s) for s in sub["seed"].unique())
        per_seed: dict[str, list[float]] = {key: [] for key in (
            "budget_used", "n_feasible", "n_no_physics", "cache_hits", "front_size",
            "spacing", "diversity_all", "diversity_feasible", "inert_repeats",
            "surface_evaluations")}
        seed_curves = []
        for seed in seeds:
            run = sub[sub["seed"] == seed]
            paid = run[~run["cache_hit"]]
            seed_curves.append(hypervolume_curve(run, objectives, hv_cfg, checkpoints))
            front = feasible_front(run, objectives)
            feas = paid[paid["feasible"]]
            per_seed["budget_used"].append(int(paid["budget_index"].max()))
            per_seed["n_feasible"].append(int(len(feas)))
            per_seed["n_no_physics"].append(int((paid["status"] != "OK").sum()))
            per_seed["cache_hits"].append(int(run["cache_hit"].sum()))
            per_seed["front_size"].append(int(len(front)))
            per_seed["spacing"].append(spacing_metric(normalise(
                front[list(objectives)].to_numpy(dtype=float), ideal, ref))
                if len(front) else float("nan"))
            per_seed["diversity_all"].append(_mean_pairwise_distance(_unit(paid, space)))
            per_seed["diversity_feasible"].append(_mean_pairwise_distance(_unit(feas, space)))
            physics = paid[paid["status"] == "OK"]
            per_seed["inert_repeats"].append(
                int(physics.duplicated(list(objectives), keep="first").sum()))
            # NR-31: this is NOT a count of CFD solver runs. It counts paid evaluations the
            # evaluator labelled fidelity > 0, i.e. that returned physics through a
            # CFD-DERIVED drag surface. It was called "cfd_calls" until 2026-09-21; solver
            # calls are counted separately (`cfd_solver_calls`, run_ai_ablation.summarise).
            per_seed["surface_evaluations"].append(int((paid["fidelity"] > 0).sum()))
        curve = np.array(seed_curves)
        curves[method] = curve
        final = curve[:, -1]
        table[method] = {
            "seeds": seeds, "n_seeds": len(seeds),
            "hv_final_per_seed": final.tolist(),
            "hv_mean": float(final.mean()),
            "hv_std": float(final.std(ddof=1)) if len(final) > 1 else float("nan"),
            "hv_min": float(final.min()), "hv_max": float(final.max()),
            "hv_curve_mean": curve.mean(axis=0).tolist(),
            "hv_curve_min": curve.min(axis=0).tolist(),
            "hv_curve_max": curve.max(axis=0).tolist(),
            "per_seed": per_seed,
            **{f"{key}_mean": float(np.nanmean(values)) if np.any(np.isfinite(values))
               else float("nan") for key, values in per_seed.items()},
        }
    return table, curves


def hv_at(curves: dict[str, np.ndarray], checkpoints: np.ndarray, method: str,
          n_evaluations: int) -> np.ndarray:
    idx = int(np.flatnonzero(checkpoints == n_evaluations)[0])
    return curves[method][:, idx]


def evaluate_success_criteria(curves: dict[str, np.ndarray], checkpoints: np.ndarray,
                              table: dict[str, Any], kinds: dict[str, str],
                              criteria: dict[str, Any], paired_with: tuple[str, ...]
                              ) -> dict[str, Any]:
    """Apply the PRE-DECLARED rule of configs/ai_ablation.yaml. Only methods run on the
    full seed list enter; `ai_adaptive` never does."""
    subject = criteria["subject"]
    if subject not in curves:
        return {"subject": subject, "status": "subject method was not run"}
    n_full = table[subject]["n_seeds"]
    conventional = [m for m in curves if kinds[m] not in LLM_KINDS
                    and table[m]["n_seeds"] == n_full]
    if not conventional:
        return {"subject": subject, "status": "no non-LLM method was run on the same seeds"}
    out: dict[str, Any] = {"subject": subject, "conventional": conventional,
                           "checkpoints": {}, "pairwise": {}}
    primary_p_help, primary_p_hurt = [], []
    for n_eval in criteria["checkpoints"]:
        ai = hv_at(curves, checkpoints, subject, int(n_eval))
        means = {m: float(hv_at(curves, checkpoints, m, int(n_eval)).mean())
                 for m in conventional}
        best = max(means, key=means.get)
        result = compare(ai, hv_at(curves, checkpoints, best, int(n_eval)),
                         paired=best in paired_with)
        out["checkpoints"][str(n_eval)] = {"comparator": best, "conventional_means": means,
                                           **result}
        primary_p_help.append(result["rank_test"]["p_greater"])
        primary_p_hurt.append(result["rank_test"]["p_less"])
        out["pairwise"][str(n_eval)] = {
            m: compare(ai, hv_at(curves, checkpoints, m, int(n_eval)),
                       paired=m in paired_with) for m in conventional}
    help_adj, hurt_adj = holm(primary_p_help), holm(primary_p_hurt)
    gain, alpha = float(criteria["min_hv_gain"]), float(criteria["alpha"])
    for i, n_eval in enumerate(criteria["checkpoints"]):
        cell = out["checkpoints"][str(n_eval)]
        cell["p_helped_holm"], cell["p_hurt_holm"] = help_adj[i], hurt_adj[i]
        # the two legs of the rule AS EVALUATED, recorded so the report can say which one
        # decided a verdict (NR-31). Descriptive only: the verdict below does not read them.
        cell["rule_legs"] = {
            "helped": {"effect_size_met": bool(cell["mean_difference"] >= gain),
                       "significance_met": bool(help_adj[i] < alpha)},
            "hurt": {"effect_size_met": bool(cell["mean_difference"] <= -gain),
                     "significance_met": bool(hurt_adj[i] < alpha)}}
        if cell["mean_difference"] >= gain and help_adj[i] < alpha:
            cell["verdict"] = "AI helped"
        elif cell["mean_difference"] <= -gain and hurt_adj[i] < alpha:
            cell["verdict"] = "AI hurt"
        else:
            cell["verdict"] = "no measured difference"
    return out


# ---------------------------------------------------------------------------------------
# surrogate scoring (spec section 25)
# ---------------------------------------------------------------------------------------
def static_surrogate_validation(frame: pd.DataFrame, space: DesignSpace,
                                objectives: tuple[str, ...], cfg: dict[str, Any]
                                ) -> dict[str, Any]:
    """Train on one seed's space-filling candidates, test on the next seed's."""
    sub = frame[(frame["method"] == cfg["train_method"]) & ~frame["cache_hit"]]
    seeds = sorted(int(s) for s in sub["seed"].unique())
    if len(seeds) < 2:
        return {"status": f"needs >= 2 seeds of '{cfg['train_method']}'"}
    transforms = cfg.get("transforms") or {}
    outputs = [*objectives, *[f"margin__{n}" for n in MARGIN_NAMES]]
    splits: list[dict[str, Any]] = []
    validity: list[dict[str, Any]] = []
    for i, seed in enumerate(seeds):
        test_seed = seeds[(i + 1) % len(seeds)]
        train, test = sub[sub["seed"] == seed], sub[sub["seed"] == test_seed]
        tr_ok, te_ok = train[train["status"] == "OK"], test[test["status"] == "OK"]
        for name in outputs:
            y_tr, y_te = tr_ok[name].to_numpy(dtype=float), te_ok[name].to_numpy(dtype=float)
            if np.any(~np.isfinite(y_tr)) or np.ptp(y_tr) == 0.0:
                continue
            model = GPSurrogate(name, transform=transforms.get(name, "identity"), seed=seed)
            splits.append({"train_seed": seed, "test_seed": test_seed,
                           **holdout_validation(model, _unit(tr_ok, space), y_tr,
                                                _unit(te_ok, space), y_te)})
        bundle = DesignSurrogate(space, objectives, seed=seed, transforms=transforms)
        bundle.fit(train.to_dict("records"))
        p_valid = bundle.probability_valid(_unit(test, space))
        truth = (test["status"] == "OK").to_numpy()
        validity.append({"train_seed": seed, "test_seed": test_seed, "n_test": int(len(test)),
                         "accuracy": float(np.mean((p_valid >= 0.5) == truth)),
                         "brier": float(np.mean((p_valid - truth) ** 2)),
                         "base_rate_valid": float(truth.mean())})

    pooled: dict[str, Any] = {}
    for name in outputs:
        mine = [s for s in splits if s["output"] == name]
        if not mine:
            continue
        pooled[name] = {"transform": mine[0]["transform"], "n_splits": len(mine)}
        for region in ("inside_hull", "outside_hull"):
            cells = [s[region] for s in mine if s[region].get("n", 0) > 0]
            if not cells:
                pooled[name][region] = {"n": 0}
                continue
            weights = np.array([c["n"] for c in cells], dtype=float)
            agg = {"n": int(weights.sum()),
                   "rmse": float(np.sqrt(np.average([c["rmse"] ** 2 for c in cells],
                                                    weights=weights))),
                   "mae": float(np.average([c["mae"] for c in cells], weights=weights)),
                   "r2_median": float(np.nanmedian([c["r2"] for c in cells])),
                   "z_std_median": float(np.nanmedian([c["z_std"] for c in cells])),
                   "coverage": {level: float(np.average([c["coverage"][level] for c in cells],
                                                        weights=weights))
                                for level in cells[0]["coverage"]}}
            pooled[name][region] = agg
    return {"train_method": cfg["train_method"], "splits": splits, "pooled": pooled,
            "validity_classifier": validity}


def score_prediction_log(records: list[dict[str, Any]], frame: pd.DataFrame
                         ) -> dict[str, Any]:
    """Prospective test: predictions logged BEFORE evaluation against what came back."""
    if not records:
        return {"n_records": 0}
    truth = (frame[~frame["cache_hit"]].drop_duplicates(["method", "seed", "candidate_id"])
             .set_index(["method", "seed", "candidate_id"]))
    collected: dict[str, dict[str, list[float]]] = {}
    n_extrapolated, valid_probs, valid_truth = 0, [], []
    for rec in records:
        key = (rec["method"], rec["seed"], rec["candidate_id"])
        if key not in truth.index:
            continue
        row = truth.loc[key]
        n_extrapolated += int(rec["extrapolated"])
        valid_probs.append(rec["p_valid"])
        valid_truth.append(row["status"] == "OK")
        if row["status"] != "OK":
            continue
        for name, pred in rec["outputs"].items():
            value = float(row[name])
            if pred["transform"] == "log10":
                value = math.log10(value)
            bucket = collected.setdefault(name, {"truth": [], "mean": [], "std": [],
                                                 "outside": [],
                                                 "transform": pred["transform"]})
            bucket["truth"].append(value)
            bucket["mean"].append(pred["mean"])
            bucket["std"].append(pred["std"])
            bucket["outside"].append(bool(rec["extrapolated"]))
    outputs = {}
    for name, b in collected.items():
        t, m, s = (np.array(b[k], dtype=float) for k in ("truth", "mean", "std"))
        outside = np.array(b["outside"], dtype=bool)
        outputs[name] = {"transform": b["transform"],
                         "all": regression_metrics(t, m, s),
                         "inside_hull": regression_metrics(t[~outside], m[~outside],
                                                           s[~outside]),
                         "outside_hull": regression_metrics(t[outside], m[outside],
                                                            s[outside])}
    probs, labels = np.array(valid_probs), np.array(valid_truth, dtype=float)
    return {"n_records": len(valid_probs), "n_extrapolated": n_extrapolated,
            "fraction_extrapolated": n_extrapolated / max(len(valid_probs), 1),
            "validity": {"accuracy": float(np.mean((probs >= 0.5) == (labels > 0.5))),
                         "brier": float(np.mean((probs - labels) ** 2)),
                         "base_rate_valid": float(labels.mean())},
            "outputs": outputs}


# ---------------------------------------------------------------------------------------
# agent scoring
# ---------------------------------------------------------------------------------------
def score_agent(agent_logs: dict[str, dict[str, Any]], frame: pd.DataFrame,
                objectives: tuple[str, ...]) -> dict[str, Any]:
    """Per LLM method: calls, tokens, rejections by reason, and how good the agent's own
    numeric `expected_outcome` predictions were."""
    truth = (frame[~frame["cache_hit"]].drop_duplicates(["method", "seed", "candidate_id"])
             .set_index(["method", "seed", "candidate_id"]))
    out: dict[str, Any] = {}
    for method, log in agent_logs.items():
        rounds = log["rounds"]
        reasons: dict[str, int] = {}
        for item in log["rejections"]:
            reasons[item["reason"]] = reasons.get(item["reason"], 0) + 1
        outcomes: dict[str, int] = {}
        for entry in rounds:
            outcomes[entry["outcome"]] = outcomes.get(entry["outcome"], 0) + 1
        errors: dict[str, list[float]] = {name: [] for name in objectives}
        feasibility_hits, n_scored, n_said_feasible, n_was_feasible = 0, 0, 0, 0
        for prop in log["proposals"]:
            key = (prop["method"], prop["seed"], prop["candidate_id"])
            if key not in truth.index:
                continue
            row = truth.loc[key]
            n_scored += 1
            said = bool(prop["expected_outcome"]["feasible"])
            n_said_feasible += int(said)
            n_was_feasible += int(bool(row["feasible"]))
            feasibility_hits += int(said == bool(row["feasible"]))
            if row["status"] == "OK":
                for name in objectives:
                    errors[name].append(float(prop["expected_outcome"][name])
                                        - float(row[name]))
        fidelity = log.get("fidelity_decisions", [])
        out[method] = {
            "llm_calls": len(rounds), "call_outcomes": outcomes,
            "models": sorted({m for e in rounds for m in e.get("models", [])}),
            "input_tokens": int(sum(e.get("input_tokens", 0) for e in rounds)),
            "output_tokens": int(sum(e.get("output_tokens", 0) for e in rounds)),
            "llm_wall_s": float(sum(e.get("wall_s", 0.0) for e in rounds)),
            "cost_usd_list_price": float(sum(e.get("cost_usd_list_price", 0.0)
                                             for e in rounds)),
            "replayed": bool(rounds) and all(e.get("replayed", False) for e in rounds),
            "n_proposals_received": int(sum(e.get("n_proposed", 0) for e in rounds)),
            "n_proposals_accepted": len(log["proposals"]),
            "n_proposals_rejected": len(log["rejections"]),
            "rejections_by_reason": dict(sorted(reasons.items())),
            "n_malformed_responses": outcomes.get("malformed_response", 0),
            "n_failed_calls": outcomes.get("call_failed", 0),
            "fallback_evaluations": int(log.get("fallback_evaluations", 0)),
            "expected_outcome": {
                "n_scored": n_scored,
                "feasibility_accuracy": feasibility_hits / n_scored if n_scored else math.nan,
                "n_predicted_feasible": n_said_feasible, "n_actually_feasible": n_was_feasible,
                **{name: {"n": len(err), "mae": float(np.mean(np.abs(err))) if err
                          else math.nan, "bias": float(np.mean(err)) if err else math.nan}
                   for name, err in errors.items()}},
            "fidelity": {
                "n_decisions": len(fidelity),
                "n_agent_requested_high": sum(d["agent_requested_fidelity"] >= 1
                                              for d in fidelity),
                "n_policy_promotions": sum(d["policy_fidelity"] >= 1 for d in fidelity),
                "n_granted": sum(d["granted_fidelity"] >= 1 for d in fidelity)},
        }
    return out


# ---------------------------------------------------------------------------------------
# metric-gaming audit, per method
# ---------------------------------------------------------------------------------------
def gaming_audit(frame: pd.DataFrame, space: DesignSpace, objectives: tuple[str, ...],
                 audit_cfg: dict[str, Any], methods: list[str]) -> dict[str, Any]:
    """Is a method's hypervolume coming from somewhere it should not?

    Per method, over all its seeds:
      fences        share of its front designs within 1% of each constraint, and parked
                    on each box bound - hypervolume bought by leaning on a placeholder
      free lunches  cache hits (cost 0) and whether any of them could have moved the
                    hypervolume (they cannot: the curve counts paid rows only - checked)
      waste         budget spent on designs with no physics; on designs whose objectives
                    are bit-identical to an earlier one (an inert variable was moved)
      near-repeats  paid designs within 1e-3 (unit cube) of an earlier paid design - a
                    way to dodge the 12-significant-digit cache without learning anything
    """
    tol = float(audit_cfg["bound_tolerance_fraction"])
    out: dict[str, Any] = {}
    for method in methods:
        sub = frame[frame["method"] == method]
        paid = sub[~sub["cache_hit"]]
        fronts = pd.concat([feasible_front(sub[sub["seed"] == s], objectives)
                            for s in sorted(sub["seed"].unique())], ignore_index=True)
        n_front = int(len(fronts))
        fences = {}
        for name in MARGIN_NAMES:
            col = fronts[f"margin__{name}"].to_numpy(dtype=float) if n_front else np.array([])
            if col.size and np.any(np.isfinite(col)):
                fences[name] = float(np.mean(col < 0.01))
        parked = {}
        for var in space.active_variables:
            col = fronts[f"x__{var.name}"].to_numpy(dtype=float) if n_front else np.array([])
            if col.size:
                parked[var.name] = {
                    "at_lower": float(np.mean(col <= var.lower + tol * var.span)),
                    "at_upper": float(np.mean(col >= var.upper - tol * var.span))}
        near = 0
        for seed in sorted(paid["seed"].unique()):
            x = _unit(paid[paid["seed"] == seed].sort_values("budget_index"), space)
            if len(x) > 1:
                dist = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2)
                dist[np.triu_indices(len(x))] = np.inf      # compare with EARLIER designs
                near += int(np.sum(dist.min(axis=1) < 1e-3))
        physics = paid[paid["status"] == "OK"]
        hits = sub[sub["cache_hit"]]
        out[method] = {
            "n_front_designs": n_front,
            "front_share_within_1pct_of_constraint": fences,
            "front_share_parked_on_bound": parked,
            "cache_hits": int(len(hits)),
            "cache_hits_counted_in_hypervolume": 0,   # by construction; see hypervolume_curve
            "budget_share_no_physics": float(np.mean(paid["status"] != "OK")),
            "budget_share_inert_repeat": float(
                physics.duplicated(["seed", *objectives], keep="first").sum() / len(paid)),
            "near_repeats": near,
            "max_heat_load_fraction_above_86km_on_front": float(
                fronts["diag__heat_load_fraction_above_86km"].max()) if n_front
            else float("nan"),
        }
    return out
