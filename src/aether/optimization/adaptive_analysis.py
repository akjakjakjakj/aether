"""M6 scoring: every arm is judged on TRUTH-AS-BEST-KNOWN, never on its own surface.

Conceptual anchor
-----------------
Each arm of the M6 study ends with a different drag surface, so each arm's own hypervolume is
measured with a different ruler - and the arm with the most wrong surface may well have the
most flattering one. Scoring therefore happens after the fact, on one common ruler:

  pooled truth      ONE surface fitted through the starting CFD points plus every usable CFD
                    point bought by ANY arm on ANY seed. It is the best drag model the project
                    has at the end of the study; it is not the truth, and the report measures
                    how far off it is where each arm makes its claims (hold-out CFD cases that
                    no surface was fitted to).
  belief            what an arm thought when it stopped: the LATEST logged value of every
                    design it submitted, under whatever surface version it had then.
  recommended set   the arm's deliverable: the designs it BELIEVES are feasible and
                    non-dominated. Chosen by the arm's belief, scored by pooled truth.

  primary metric    truth hypervolume of the recommended set (members that are infeasible
                    under pooled truth are dropped - a false claim earns nothing).

Why the recommended set and not "everything the arm evaluated": re-scoring every submitted
design under truth would pay an arm for designs it thought were bad and would never have
delivered (luck), and would hide the cost of a wrong surface, which is precisely a wrong
CHOICE. That number is still reported, as the `oracle` hypervolume; the difference is the
arm's selection regret.

Metric-gaming routes considered, and what closes each (the report prints the evidence):

  1. flattering surrogate     belief is never scored. `optimism_gap` = belief HV - truth HV of
                              the same designs, per arm.
  2. never promoting looks    "converged" is not a metric here. The target is a fraction of
     cheap and converged      the POOLED-TRUTH reference hypervolume, which contains designs
                              only reachable by extending the hull. An arm that reaches it
                              with zero calls has honestly shown the CFD was not needed, and
                              the verdict then says H2 is NOT TESTABLE at that target.
  3. hull rejection shrinks   every hull-rejected design is re-evaluated under pooled truth
     the space silently       (whose hull contains every arm's hull). Reported per arm: how
                              many it lost, how many of those are truly feasible, how many sit
                              on the reference front.
  4. luck / selection         recommended set, not all designs (above); `oracle` reported.
  5. false claims             recommended designs infeasible under truth: dropped and counted.
  6. free information         probes are counted and capped and never enter a hypervolume;
                              re-evaluations after a refit are charged; cache hits cannot
                              move a curve (curves are functions of what was PAID).
  7. CFD accounting           failed cases cost a call; a repeat is free only within the arm
                              that paid; a case another arm already ran is still charged;
                              near-duplicate requests are refused by the Mach rule.
  8. truth favours whoever    pooled truth is most accurate where promoting arms sampled, and
     bought CFD               equals the starting surface where nobody did - so a no-CFD arm
                              has a zero optimism gap BY CONSTRUCTION in untouched regions.
                              Hold-out CFD at each arm's recommended designs measures the
                              truth surface's error there; the truth sigma at each arm's
                              recommended set is reported beside its score.
  9. the ruler moves          hypervolume reference and ideal points are M4's, read from the
                              design-space config (A-OPT-4); the reference FRONT includes a
                              dedicated large-budget search on the truth surface, so it does
                              not depend on how well the arms happened to cover it.
 10. who-vs-how confound      all promoting arms share one Mach rule, one refit, one
                              re-evaluation rule; they differ only in WHO is promoted.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..aerodynamics.cfd_surface import SHAPE_INPUTS, CfdDragSurface
from .ablation import compare, permutation_rank_test
from .adaptive import HULL_REJECT_PREFIX
from .budget import evaluate_candidate
from .design_space import DesignSpace
from .pareto import normalised_hypervolume, pareto_front

CENSORED = "not reached"


def hv_points(hv_cfg: dict[str, Any], objectives: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
    ideal = np.array([hv_cfg["ideal_point"][n] for n in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][n] for n in objectives], dtype=float)
    return ideal, ref


def _hv(values: np.ndarray, ideal: np.ndarray, ref: np.ndarray) -> float:
    values = np.asarray(values, dtype=float).reshape(-1, len(ideal))
    return float(normalised_hypervolume(values, ideal, ref)) if len(values) else 0.0


# ---------------------------------------------------------------------------------------
# pooled truth
# ---------------------------------------------------------------------------------------
def pooled_training_table(base_table: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    """Starting CFD points + every USABLE promotion case of the run. Hold-out cases are
    excluded: they exist to test this surface, so it must never see them."""
    if cases.empty:
        return base_table.reset_index(drop=True)
    keep = cases[(cases["usable"].astype(bool)) & (cases["purpose"] != "holdout")]
    keep = keep.drop_duplicates("point_id")
    keep = keep[~keep["point_id"].isin(set(base_table["point_id"].astype(str)))]
    rows = pd.DataFrame({"point_id": keep["point_id"], "role": "promotion", "split": "train",
                         "mach": keep["mach"], **{k: keep[k] for k in SHAPE_INPUTS},
                         "cd_fore": keep["cd_fore"], "verdict": keep["verdict"],
                         "label": "m6:pooled"})
    return pd.concat([base_table, rows], ignore_index=True)


def build_truth_surface(base: CfdDragSurface, cases: pd.DataFrame, directory: Path
                        ) -> CfdDragSurface:
    table = pooled_training_table(base.table, cases)
    meta = {k: v for k, v in base.meta.items()
            if k not in ("kernel_theta", "training_hash", "n_train")}
    meta.update(adaptive_arm="POOLED-TRUTH", adaptive_base_hash=base.meta["training_hash"],
                n_promotion_points=int((table["role"] == "promotion").sum()))
    if len(table) == len(base.table):       # nobody bought anything: truth IS the base surface
        surface = CfdDragSurface(table, meta, theta=np.array(base.meta["kernel_theta"]))
    else:
        surface = CfdDragSurface(table, meta)
    surface.save(Path(directory))
    return surface


def distinct_designs(frame: pd.DataFrame) -> pd.DataFrame:
    cols = ["candidate_id", *[c for c in frame.columns if c.startswith("x__")]]
    return frame[cols].drop_duplicates("candidate_id").reset_index(drop=True)


def truth_evaluate(designs: pd.DataFrame, space: DesignSpace, aero_block: dict[str, Any],
                   objectives: tuple[str, ...], *, executor=None,
                   evaluate_fn=evaluate_candidate) -> pd.DataFrame:
    """Every distinct design of the study under the pooled-truth surface. Scoring, not search:
    it spends no arm's budget and no arm ever sees it."""
    payloads = []
    for rec in designs.to_dict("records"):
        values = {k.removeprefix("x__"): float(v) for k, v in rec.items() if k.startswith("x__")}
        cfg = space.config_for(values)
        cfg["vehicle"]["aero"] = {**(cfg["vehicle"].get("aero") or {}), **aero_block}
        payloads.append((cfg, rec["candidate_id"]))
    mapper = map if executor is None else executor.map
    rows = []
    for (_, cid), result in zip(payloads, mapper(evaluate_fn, payloads), strict=True):
        rows.append({"candidate_id": cid, "truth__status": result["status"],
                     "truth__feasible": bool(result["feasible"]),
                     "truth__hull_rejected": str(result["status"]).startswith(
                         HULL_REJECT_PREFIX),
                     **{f"truth__{n}": float(result[n]) for n in objectives}})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------
# belief, recommended set, curves
# ---------------------------------------------------------------------------------------
def belief_at(run: pd.DataFrame, n_evaluations: int) -> pd.DataFrame:
    """Latest logged row of every design the arm had PAID for after `n_evaluations`."""
    seen = run[run["budget_index"] <= n_evaluations].sort_values("eval_index")
    return seen.drop_duplicates("candidate_id", keep="last")


def recommended(belief: pd.DataFrame, objectives: tuple[str, ...]) -> pd.DataFrame:
    feas = belief[belief["feasible"]]
    if feas.empty:
        return feas
    idx = pareto_front(feas[list(objectives)].to_numpy(dtype=float))
    return feas.iloc[idx]


def _truth_values(ids: pd.Series, truth: pd.DataFrame, objectives: tuple[str, ...]
                  ) -> tuple[np.ndarray, int]:
    """(truth objective rows of the truly feasible members, number of FALSE claims)."""
    sub = truth[truth["candidate_id"].isin(set(ids))]
    ok = sub[sub["truth__feasible"]]
    return ok[[f"truth__{n}" for n in objectives]].to_numpy(dtype=float), int(len(sub) - len(ok))


def arm_seed_curve(run: pd.DataFrame, calls: pd.DataFrame, truth: pd.DataFrame,
                   objectives: tuple[str, ...], hv_cfg: dict[str, Any],
                   checkpoints: np.ndarray) -> pd.DataFrame:
    ideal, ref = hv_points(hv_cfg, objectives)
    rows = []
    for n in checkpoints:
        belief = belief_at(run, int(n))
        rec = recommended(belief, objectives)
        rec_truth, false_claims = _truth_values(rec["candidate_id"], truth, objectives)
        all_truth, _ = _truth_values(belief["candidate_id"], truth, objectives)
        rows.append({
            "n_evaluations": int(n),
            "cfd_calls": int((calls["evaluations_used"] <= n).sum()) if len(calls) else 0,
            "hv_belief": _hv(rec[list(objectives)].to_numpy(dtype=float), ideal, ref),
            "hv_truth": _hv(rec_truth, ideal, ref),
            "hv_truth_oracle": _hv(all_truth, ideal, ref),
            "n_recommended": int(len(rec)), "n_false_claims": false_claims})
    return pd.DataFrame(rows)


def calls_to_target(curve: pd.DataFrame, target_hv: float) -> dict[str, Any]:
    hit = curve[curve["hv_truth"] >= target_hv]
    if hit.empty:
        return {"reached": False, "cfd_calls": None, "n_evaluations": None}
    first = hit.iloc[0]
    return {"reached": True, "cfd_calls": int(first["cfd_calls"]),
            "n_evaluations": int(first["n_evaluations"])}


# ---------------------------------------------------------------------------------------
# the pre-declared H2 rule
# ---------------------------------------------------------------------------------------
def h2_verdict(reach: dict[str, list[dict[str, Any]]], criteria: dict[str, Any],
               cfd_budget: int) -> dict[str, Any]:
    """Apply the rule of configs/adaptive_fidelity.yaml. `reach[arm]` is one
    `calls_to_target` record per seed. An arm that never reached the target is CENSORED at
    `cfd_budget + 1` calls for ranking: worse than any arm that reached it, by any margin."""
    subject, no_cfd = criteria["subject"], criteria["no_cfd_arm"]
    need = int(criteria["min_seeds_reaching"])
    alpha = float(criteria["alpha"])

    def censored(arm: str) -> np.ndarray:
        return np.array([r["cfd_calls"] if r["reached"] else cfd_budget + 1
                         for r in reach[arm]], dtype=float)

    n_reached = {arm: int(sum(r["reached"] for r in recs)) for arm, recs in reach.items()}
    out: dict[str, Any] = {"subject": subject, "n_seeds_reaching": n_reached,
                           "median_calls_censored": {arm: float(np.median(censored(arm)))
                                                     for arm in reach},
                           "censored_at": cfd_budget + 1}
    if subject not in reach:
        return {**out, "verdict": "subject arm was not run", "status": "NOT_RUN"}
    comparators = [a for a in criteria["comparators"] if a in reach]
    if no_cfd in reach and n_reached[no_cfd] >= need:
        return {**out, "status": "NOT_TESTABLE",
                "verdict": f"target reached by '{no_cfd}' with no new CFD in "
                           f"{n_reached[no_cfd]} seeds: CFD calls cannot be 'saved' at this "
                           "target, so H2 is not testable here"}
    if n_reached[subject] < need:
        others = [a for a in comparators if n_reached[a] >= need]
        return {**out, "status": "NOT_SUPPORTED",
                "verdict": (f"'{subject}' reached the target in {n_reached[subject]} seeds "
                            f"(needs {need}); " + (f"{others} did reach it" if others else
                                                   "no arm reached it"))}
    if not comparators:
        return {**out, "status": "NOT_TESTABLE", "verdict": "no comparator arm was run"}
    med = out["median_calls_censored"]
    best = min(comparators, key=lambda a: (med[a], float(np.mean(censored(a)))))
    test = permutation_rank_test(censored(subject), censored(best))
    out.update(best_comparator=best, rank_test=test,
               pairwise={a: {"median_calls_censored": med[a],
                             "rank_test": permutation_rank_test(censored(subject),
                                                                censored(a))}
                         for a in comparators})
    if med[subject] < med[best] and test["p_less"] < alpha:
        out.update(status="SUPPORTED", verdict=f"'{subject}' reached the target with fewer CFD "
                                               f"calls than the best comparator '{best}'")
    elif med[subject] > med[best] and test["p_greater"] < alpha:
        out.update(status="CONTRADICTED", verdict=f"the comparator '{best}' reached the target "
                                                  f"with fewer CFD calls than '{subject}'")
    else:
        out.update(status="NO_MEASURED_DIFFERENCE",
                   verdict=f"no measured difference in CFD calls between '{subject}' and the "
                           f"best comparator '{best}'")
    return out


# ---------------------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------------------
def arm_table(frame: pd.DataFrame, calls: pd.DataFrame, truth: pd.DataFrame,
              curves: dict[tuple[str, int], pd.DataFrame], counters: dict[str, Any],
              reference_front_ids: set[str], arms: list[str]) -> dict[str, Any]:
    """Per arm, over its seeds: the score, and everything needed to audit the score."""
    table: dict[str, Any] = {}
    for arm in arms:
        sub = frame[frame["method"] == arm]
        seeds = sorted(int(s) for s in sub["seed"].unique())
        per_seed: dict[str, list[float]] = {}

        def put(key: str, value: float, store=per_seed) -> None:
            store.setdefault(key, []).append(float(value))

        for seed in seeds:
            run = sub[sub["seed"] == seed]
            paid = run[~run["cache_hit"]]
            last = curves[(arm, seed)].iloc[-1]
            mine = calls[(calls["arm"] == arm) & (calls["seed"] == seed)] if len(calls) \
                else calls
            lost = paid[paid["hull_rejected"]].drop_duplicates("candidate_id")
            # a design rejected early and evaluable after a hull extension is not lost
            final = belief_at(run, int(paid["budget_index"].max()))
            lost = lost[lost["candidate_id"].isin(
                set(final[final["hull_rejected"]]["candidate_id"]))]
            lost_truth = truth[truth["candidate_id"].isin(set(lost["candidate_id"]))]
            c = counters.get(f"{arm}|{seed}", {})
            put("hv_truth", last["hv_truth"])
            put("hv_belief", last["hv_belief"])
            put("hv_truth_oracle", last["hv_truth_oracle"])
            put("optimism_gap", last["hv_belief"] - last["hv_truth"])
            put("selection_regret", last["hv_truth_oracle"] - last["hv_truth"])
            put("n_recommended", last["n_recommended"])
            put("n_false_claims", last["n_false_claims"])
            put("evaluations_used", paid["budget_index"].max())
            put("reevaluations", (paid["eval_kind"] == "reeval").sum())
            put("probes", c.get("n_probes", 0))
            put("cache_hits", run["cache_hit"].sum())
            put("cfd_budget", c.get("cfd_budget", 0))
            put("cfd_calls", len(mine))
            put("cfd_failed", int((~mine["usable"].astype(bool)).sum()) if len(mine) else 0)
            put("cfd_repeat_requests_free", c.get("n_repeat_requests", 0))
            put("cfd_wall_s", float(mine["wall_time_s"].sum()) if len(mine) else 0.0)
            put("surface_versions", c.get("surface_version", 0))
            put("hull_lost", len(lost))
            put("hull_lost_share_of_budget", len(lost) / max(len(paid), 1))
            put("hull_lost_truly_feasible", lost_truth["truth__feasible"].sum())
            put("hull_lost_on_reference_front",
                lost_truth["candidate_id"].isin(reference_front_ids).sum())
        table[arm] = {
            "seeds": seeds, "n_seeds": len(seeds), "per_seed": per_seed,
            **{f"{k}_mean": float(np.mean(v)) for k, v in per_seed.items()},
            "hv_truth_std": (float(np.std(per_seed["hv_truth"], ddof=1))
                             if len(seeds) > 1 else float("nan")),
            "hv_truth_min": float(np.min(per_seed["hv_truth"])),
            "hv_truth_max": float(np.max(per_seed["hv_truth"])),
        }
    return table


def surface_error_table(finals: dict[tuple[str, int], CfdDragSurface], truth: CfdDragSurface,
                        shapes: list[dict[str, float]], machs: list[float]) -> pd.DataFrame:
    """Each arm's FINAL surface against pooled truth on one common probe set: the shapes of
    the reference front x the declared Mach nodes. GP predictions only - no evaluation."""
    rows = []
    mach = np.clip(np.array(machs, dtype=float), truth.mach_min, truth.mach_max)
    for (arm, seed), surface in finals.items():
        err, outside, n = [], 0, 0
        for shape in shapes:
            mine = surface.predict_fore(mach, shape, on_extrapolation="flag")
            ref = truth.predict_fore(mach, shape, on_extrapolation="flag")
            err.extend((mine.central - ref.central).tolist())
            outside += int(np.sum(mine.extrapolated))
            n += len(mach)
        err_a = np.array(err, dtype=float)
        rows.append({"arm": arm, "seed": seed, "n_probe_points": n,
                     "n_train": int(len(surface.table)),
                     "cd_fore_rmse_vs_truth": float(np.sqrt(np.mean(err_a ** 2))) if n else
                     float("nan"),
                     "cd_fore_max_abs_vs_truth": float(np.max(np.abs(err_a))) if n else
                     float("nan"),
                     "share_outside_own_hull": outside / n if n else float("nan")})
    return pd.DataFrame(rows)


def truth_sigma_at(truth: CfdDragSurface, shapes: list[dict[str, float]], mach: float) -> float:
    if not shapes:
        return float("nan")
    inflation = float(truth.meta.get("sigma_inflation", 1.0))
    m = np.array([min(max(mach, truth.mach_min), truth.mach_max)])
    return float(np.mean([truth.predict_fore(m, s, on_extrapolation="flag").std[0] * inflation
                          for s in shapes]))


def holdout_table(cases: pd.DataFrame, truth: CfdDragSurface, picks: list[dict[str, Any]]
                  ) -> pd.DataFrame:
    """Hold-out CFD cases (never fitted by any surface) against the pooled-truth prediction."""
    rows = []
    for pick in picks:
        case = cases[cases["key"] == pick["key"]]
        rec = {"arm": pick["arm"], "key": pick["key"], "mach": pick["mach"],
               **{k: pick[k] for k in SHAPE_INPUTS}, "usable": False}
        if len(case):
            c = case.iloc[-1]
            pred = truth.predict_fore(np.array([float(c["mach"])]),
                                      {k: float(c[k]) for k in SHAPE_INPUTS},
                                      on_extrapolation="flag")
            sigma = float(pred.std[0]) * float(truth.meta.get("sigma_inflation", 1.0))
            rec.update(usable=bool(c["usable"]), verdict=str(c["verdict"]),
                       cd_fore_truth_surface=float(pred.central[0]),
                       cd_fore_truth_sigma=sigma,
                       truth_surface_extrapolated=bool(pred.extrapolated[0]))
            if bool(c["usable"]):
                error = float(pred.central[0]) - float(c["cd_fore"])
                rec.update(cd_fore_cfd=float(c["cd_fore"]), error=error,
                           rel_error=error / float(c["cd_fore"]),
                           z=error / sigma if sigma > 0 else math.nan)
        rows.append(rec)
    return pd.DataFrame(rows)


def compare_final(table: dict[str, Any], subject: str, others: list[str]) -> dict[str, Any]:
    """Final truth hypervolume, subject against each comparator run on the same seeds."""
    out = {}
    for arm in others:
        if arm in table and subject in table and table[arm]["seeds"] == table[subject]["seeds"]:
            out[arm] = compare(np.array(table[subject]["per_seed"]["hv_truth"]),
                               np.array(table[arm]["per_seed"]["hv_truth"]), paired=True)
    return out
