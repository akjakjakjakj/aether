"""M6 report generator. EVERY interpretive sentence is emitted by code from `summary.json`,
or not at all (NR-18, point 3): this file contains the description of the method and the
wording of each possible outcome, never a finding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _f(value: Any, fmt: str = ".4f") -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "n/a"
    return format(value, fmt)


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def _h2_sentences(cell: dict[str, Any], budget: int) -> list[str]:
    out = [f"**Verdict at {100 * cell['fraction']:.0f}% of the reference hypervolume "
           f"(target {cell['target_hv']:.4f}): {cell['status']}** - {cell['verdict']}."]
    reached = cell["n_seeds_reaching"]
    out.append("Seeds reaching the target: " + ", ".join(
        f"`{arm}` {n} of {len(cell['reach'][arm])}" for arm, n in reached.items()) + ".")
    med = cell["median_calls_censored"]
    out.append("Median CFD calls charged when the target was first reached (an arm-seed that "
               f"never reached it counts as {budget + 1}): "
               + ", ".join(f"`{arm}` {_f(v, '.1f')}" for arm, v in med.items()) + ".")
    test = cell.get("rank_test")
    if test:
        out.append(f"Exact one-sided permutation rank test, `{cell['subject']}` fewer calls than "
                   f"`{cell['best_comparator']}`: p = {test['p_less']:.4f} (the reverse: p = "
                   f"{test['p_greater']:.4f}; smallest attainable p with these sample sizes: "
                   f"{test['min_attainable_p_one_sided']:.4f}).")
    return out


def _read_first(summary: dict[str, Any], snapshot: dict[str, Any] | None) -> list[str]:
    """The opening paragraph: verdict, what was NOT run, and whether the target was reachable
    at all. Every clause is computed from `summary` (and the run's config snapshot for the
    declared-but-not-run arms and the reference search's budget); NR-35."""
    truth, arms = summary["truth"], summary["arms"]
    cell = summary["h2"][next(iter(summary["h2"]))]
    out = [f"**Read this first. H2 verdict, as pre-declared: {cell['status']}** at "
           f"{100 * cell['fraction']:.0f}% of the reference hypervolume (target "
           f"{cell['target_hv']:.4f}) - {cell['verdict']}."]
    af = (snapshot or {}).get("adaptive_fidelity") or {}
    declared = [a for a, s in (af.get("arms") or {}).items() if s.get("enabled", False)]
    not_run = [a for a in declared if a not in arms]
    llm_not_run = [a for a in not_run if af["arms"][a].get("search") == "ai_agent"]
    if not_run:
        out.append("Declared in the config and NOT run in this invocation: "
                   + ", ".join(f"`{a}`" for a in not_run)
                   + f" (LLM calls made: {summary['llm_calls_total']}).")
    if llm_not_run:
        out.append("That is the LLM-guided arm, so **H2's \"AI-guided\" clause is untested by "
                   "this study**; the arm is exploratory and outside the declared criterion, "
                   "so the verdict above does not depend on it.")
    union, ref = float(truth["hv_union_of_arms"]), float(truth["hv_reference"])
    n_evals = sum(a["evaluations_used_mean"] * a["n_seeds"] for a in arms.values())
    n_runs = sum(a["n_seeds"] for a in arms.values())
    best_arm, best = max(((arm, max(a["per_seed"]["hv_truth"])) for arm, a in arms.items()),
                         key=lambda item: item[1])
    reference = af.get("reference") or {}
    ref_text = (f" by {len(reference['seeds'])} x {reference['budget_evaluations']}-evaluation "
                "searches on the truth surface" if reference else "")
    if union < cell["target_hv"]:
        out.append(
            f"**Reachability (a sizing flaw of this study, NR-35).** Every truly feasible "
            f"design of all {n_runs} arm-seeds pooled - {n_evals:.0f} F0 evaluations - reaches "
            f"{union:.4f} = {100 * union / ref:.1f}% of the reference ({ref:.4f}, set{ref_text}"
            f"), which is below the {100 * cell['fraction']:.0f}% target; the best single "
            f"arm-seed (`{best_arm}`) reached {best:.4f} = {100 * best / ref:.1f}%. At "
            f"{summary['budget_evaluations']} F0 evaluations per arm-seed the target was "
            "therefore beyond what the searches as run could reach, singly or pooled, so a "
            "saving in CFD calls could not have shown up in this criterion. The config's "
            "sizing checked statistical power and "
            "machine time, not reachability. The criterion is applied as written and is not "
            "re-scored.")
    else:
        out.append(f"Reachability: all arm-seeds pooled reach {100 * union / ref:.1f}% of the "
                   f"reference, at or above the {100 * cell['fraction']:.0f}% target.")
    return out


def write_m6_report(summary: dict[str, Any], path: Path, figure_prefix: str = "../figures",
                    snapshot: dict[str, Any] | None = None,
                    addendum: str | None = None) -> Path:
    arms = summary["arms"]
    crit = summary["criteria_declared"]
    subject = crit["subject"]
    budget = int(summary["cfd_budget_calls"])
    truth, cfd, gate = summary["truth"], summary["cfd"], summary["gate"]
    lines: list[str] = []
    add = lines.append

    add("# M6 - Adaptive-fidelity optimisation: who should get the next CFD case?\n")
    add(f"*Generated by `scripts/run_adaptive_fidelity.py` from `results/M6/{summary['run_id']}/`. "
        "Every number and every interpretive sentence below is computed from that run's "
        "files; the generator contains no pre-written finding.*\n")
    if summary.get("banner"):
        add(f"> **{summary['banner']}**\n")
    add(" ".join(_read_first(summary, snapshot)) + "\n")
    if addendum:
        add(f"*Hand-written companion for this run (what the verdict means, where each arm "
            f"spent its CFD, failed cases, figure check): `{addendum}`. It is not generated "
            "and nothing in it overrides a number here.*\n")
    if gate["provisional"]:
        add(f"> **PROVISIONAL.** Gate G4 was `{gate['gate_G4_status_at_build']}` when the "
            f"starting surface was built and `{gate['gate_G4_status_now']}` when this run "
            "started; the run was allowed only because its config set `allow_provisional: "
            "true`. Spec section 17: nothing here may be used as an optimisation result.\n")
    add(f"Run `{summary['run_id']}` · git `{summary['git_commit']}`"
        f"{' (dirty tree)' if summary['git_dirty'] else ''} · evaluator source hash "
        f"`{summary['source_hash']}` (re-checked after every logged batch, NR-18) · F1 backend "
        f"`{cfd['backend']}` · mesh level `{summary['mesh_level']}` · active variables "
        f"{summary['active']} ({summary['active_source']}).\n")

    add("## 1. What was compared\n")
    add("F0 is `evaluate_design` with the arm's current GP drag surface. F1 is an OpenFOAM case "
        "for the candidate's forebody shape through M3's design-point runner, unchanged; a "
        "usable case joins the arm's training set, the surface is refitted and the candidate is "
        "re-evaluated; a case that fails M2's convergence criterion is kept, costs a call and "
        "yields no training point. Every arm starts every seed from the same surface "
        f"(`{truth['base_training_hash']}`, {truth['n_base']} CFD points) and the same seeded "
        f"initial population, with {summary['budget_evaluations']} F0 evaluations and "
        f"{budget} CFD calls.\n")
    add(_table(["arm", "promotion strategy", "search", "seeds", "CFD budget"], [
        [f"`{arm}`", str(s["strategy"]), str(s["search"]), str(arms[arm]["seeds"]),
         _f(arms[arm]["cfd_budget_mean"], ".0f")]
        for arm, s in summary["arm_settings"].items()]) + "\n")

    add("## 2. How every arm was scored\n")
    add(f"On POOLED TRUTH: one surface through the {truth['n_base']} starting points plus the "
        f"{truth['n_promotion_points']} usable CFD points bought by any arm on any seed "
        f"(`{truth['training_hash']}`). An arm's score is the truth hypervolume of its "
        "RECOMMENDED set - the designs its own final belief calls feasible and non-dominated - "
        "with recommended designs that are infeasible under truth dropped. The reference "
        f"hypervolume is **{truth['hv_reference']:.4f}**: every truly feasible design of "
        f"every arm ({truth['hv_union_of_arms']:.4f} on their own) plus a dedicated NSGA-II "
        f"search on the truth surface ({truth['hv_reference_search_alone']:.4f} on its own); "
        f"{truth['n_distinct_designs_scored']} distinct designs were re-scored. The reasoning, "
        "and the metric-gaming routes this closes, are in the docstring of "
        "`src/aether/optimization/adaptive_analysis.py` and in ASSUMPTIONS A-AF-7..A-AF-9.\n")

    add("## 3. Result against the pre-declared H2 criterion\n")
    keys = list(summary["h2"])
    add(f"Declared before the run (`configs/adaptive_fidelity.yaml`): subject `{subject}`, "
        f"comparators {crit['comparators']}, no-CFD arm `{crit['no_cfd_arm']}`, target "
        f"{100 * float(crit['target_fraction_of_reference_hv']):.0f}% of the reference, at least "
        f"{crit['min_seeds_reaching']} seeds reaching it, alpha = {crit['alpha']}.\n")
    for sentence in _h2_sentences(summary["h2"][keys[0]], budget):
        add(sentence + "\n")
    if len(keys) > 1:
        add("Sensitivity to the target (reported, NOT the criterion): " + "; ".join(
            f"{100 * summary['h2'][k]['fraction']:.0f}% -> {summary['h2'][k]['status']}"
            for k in keys[1:]) + ".\n")
    n_seeds = arms[subject]["n_seeds"] if subject in arms else 0
    if n_seeds:
        add(f"Power: {n_seeds} seeds per arm. CFD-call counts are small integers with many ties, "
            "so the rank test rejects only when the samples barely overlap; a 'no measured "
            "difference' here is weak evidence of equivalence.\n")
    add(f"![hv vs cfd calls]({figure_prefix}/M6_hv_vs_cfd_calls.png)\n")

    add("## 4. Scores, and what is needed to audit them\n")
    add(_table(["arm", "truth HV (mean ± sd)", "min-max", "belief HV", "optimism gap",
                "oracle HV", "selection regret", "false claims", "CFD calls", "failed calls"], [
        [f"`{arm}`", f"{_f(a['hv_truth_mean'])} ± {_f(a['hv_truth_std'])}",
         f"{_f(a['hv_truth_min'])}-{_f(a['hv_truth_max'])}", _f(a["hv_belief_mean"]),
         _f(a["optimism_gap_mean"], "+.4f"), _f(a["hv_truth_oracle_mean"]),
         _f(a["selection_regret_mean"], "+.4f"), _f(a["n_false_claims_mean"], ".1f"),
         _f(a["cfd_calls_mean"], ".1f"), _f(a["cfd_failed_mean"], ".1f")]
        for arm, a in arms.items()]) + "\n")
    add("`belief HV` is what the arm's own surface says about its recommended set; `optimism "
        "gap` = belief - truth for the same designs; `oracle HV` scores EVERY design the arm "
        "paid for under truth (what perfect selection would have delivered); `false claims` are "
        "recommended designs that pooled truth calls infeasible.\n")
    gaps = {arm: a["optimism_gap_mean"] for arm, a in arms.items()}
    worst = max(gaps, key=lambda k: abs(gaps[k]))
    add(f"Largest mean optimism gap in magnitude: `{worst}` ({gaps[worst]:+.4f}). "
        + ("A positive gap means the arm's own surface flattered it." if gaps[worst] > 0 else
           "A non-positive gap means the arm's own surface did not flatter it.") + "\n")
    final = summary["final_hv_comparison"]
    if final:
        add("Final truth hypervolume, `" + subject + "` against each other arm on the same "
            "seeds (paired):\n")
        add(_table(["comparator", "mean difference", "A12", "seeds where subject is better",
                    "rank test p (subject greater)"], [
            [f"`{arm}`", _f(c["mean_difference"], "+.4f"), _f(c["a12"], ".2f"),
             f"{c.get('seeds_a_better', 'n/a')} of {len(c.get('paired_differences', []))}",
             _f(c["rank_test"]["p_greater"])] for arm, c in final.items()]) + "\n")

    add("## 5. The hull: designs an arm could not see\n")
    add(_table(["arm", "hull-rejected at the end (mean/seed)", "share of F0 budget",
                "of those truly feasible", "of those on the reference front",
                "surface versions"], [
        [f"`{arm}`", _f(a["hull_lost_mean"], ".1f"), _f(a["hull_lost_share_of_budget_mean"], ".3f"),
         _f(a["hull_lost_truly_feasible_mean"], ".1f"),
         _f(a["hull_lost_on_reference_front_mean"], ".1f"),
         _f(a["surface_versions_mean"], ".1f")] for arm, a in arms.items()]) + "\n")
    add("A design refused by an arm's hull and later made evaluable by a hull extension is not "
        "counted as lost. Pooled truth's hull contains every arm's hull, so these designs were "
        "scored; an arm simply never learnt their value.\n")

    add("## 6. Budgets, exactly\n")
    add(_table(["arm", "F0 evaluations", "of which re-evaluations", "probes (uncharged)",
                "cache hits", "CFD calls / budget", "free repeat requests", "CFD wall [s]"], [
        [f"`{arm}`", _f(a["evaluations_used_mean"], ".0f"), _f(a["reevaluations_mean"], ".1f"),
         _f(a["probes_mean"], ".1f"), _f(a["cache_hits_mean"], ".1f"),
         f"{_f(a['cfd_calls_mean'], '.1f')} / {_f(a['cfd_budget_mean'], '.0f')}",
         _f(a["cfd_repeat_requests_free_mean"], ".1f"), _f(a["cfd_wall_s_mean"], ".0f")]
        for arm, a in arms.items()]) + "\n")
    add(f"CFD cases: {cfd['n_calls_charged']} calls charged across all arms, "
        f"{cfd['n_cases_run']} cases actually run in this invocation "
        f"({cfd['n_cases_imported']} imported from an earlier run, {cfd['n_cases_usable']} of "
        f"{cfd['n_cases_in_store']} in the store usable); at most {cfd['max_concurrent']} serial "
        f"solvers side by side (peak observed: {cfd['peak_concurrency_observed']}); median case "
        f"wall time {_f(cfd['case_wall_s_median'], '.0f')} s, sum "
        f"{cfd['case_wall_s_sum'] / 3600.0:.2f} core-hours. LLM calls: "
        f"{summary['llm_calls_total']}.\n")
    add(f"![cfd spend map]({figure_prefix}/M6_cfd_spend_map.png)\n")

    add("## 7. How good is 'truth'?\n")
    add(_table(["arm", "final-surface RMSE vs truth (C_D,fore)",
                "truth sigma at the arm's recommended shapes, Mach max"], [
        [f"`{arm}`", _f(a.get("surface_rmse_vs_truth_mean")),
         _f(a.get("truth_sigma_cd_at_recommended_mach_max"))] for arm, a in arms.items()]) + "\n")
    hold = summary["holdout"]
    if hold:
        add("Hold-out CFD cases - fitted by NO surface, charged to nobody - at the recommended "
            "design of each arm that lies farthest from every truth training point:\n")
        add(_table(["arm", "case", "usable", "C_D,fore CFD", "truth surface", "error",
                    "rel. error [%]", "z"], [
            [f"`{h['arm']}`", h["key"], str(h["usable"]), _f(h.get("cd_fore_cfd")),
             _f(h.get("cd_fore_truth_surface")), _f(h.get("error"), "+.4f"),
             _f(100 * h["rel_error"] if h.get("rel_error") is not None else None, "+.2f"),
             _f(h.get("z"), "+.2f")] for h in hold]) + "\n")
        errs = [abs(h["rel_error"]) for h in hold if h.get("rel_error") is not None
                and np.isfinite(h["rel_error"])]
        if errs:
            add(f"Largest hold-out error of the truth surface: {100 * max(errs):.2f}% of "
                f"C_D,fore over {len(errs)} usable cases. That is the measured size of the "
                "gap between 'pooled truth' and CFD where the arms make their claims; it is "
                "not a bound.\n")
    else:
        add("No hold-out CFD case was run in this invocation, so the error of the pooled-truth "
            "surface at the arms' recommended designs is NOT measured here.\n")
    add(f"![surface error]({figure_prefix}/M6_surface_error_vs_truth.png)\n")

    add("## 8. Limits\n")
    add("- Pooled truth is a GP through CFD, not CFD, and the CFD is inviscid perfect-gas at "
        "zero angle of attack on the surface's mesh level (M3 report section 11). 'Truth' means "
        "best-known drag model, nothing more.\n"
        "- Belief is the latest LOGGED value of each design. Designs an arm evaluated early and "
        "never revisited keep the value of an older surface; only the promoted design and the "
        "believed front are refreshed (and charged) after a refit. This penalises promoting "
        "arms, the subject included.\n"
        "- NSGA-II's internal population is not re-scored after a refit.\n"
        "- Probes are `evaluate_design` calls that are counted but not charged (A-AF-5).\n"
        "- The sigma inflation factor is M3's and is not re-measured after a refit (A-AF-6).\n"
        + ("- `ai_adaptive` uses a different search from the other arms and fewer seeds; it is "
           "exploratory and is not part of the criterion.\n" if "ai_adaptive" in arms else
           "- `ai_adaptive` (LLM-guided search, exploratory, outside the criterion) was NOT run "
           "in this invocation: nothing in this report is evidence about it.\n"))

    add("## 9. Reproduce\n")
    add("```\nmake adaptive                          # the study: hours, OpenFOAM, gate G4 PASS\n"
        f"make adaptive-report RUN_ID={summary['run_id']}   # rebuild figures + report only\n```\n")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path
