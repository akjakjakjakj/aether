"""Render `reports/milestones/M5_ai_ablation.md` from an M5 `summary.json`.

Every number is read from the summary; nothing is typed by hand, so a re-run (corrected
nose-radius physics, CFD surrogate) rewrites the whole report consistently.

RULE FOR THIS FILE: prose may describe what the harness DOES (design, declared before the
run) and may state general statistical facts. It may not assert a FINDING - which method
won, where a front sits, why a number is what it is - unless that sentence is generated
from a value in `summary.json`. The first version of this file carried pre-written
interpretation ("every method's front leans on the same two fences"); the physics then
changed and the sentences would have been false. Findings are now conditional code. The one
hand-written part is the qualitative audit of the agent's stated mechanisms: it lives in
`reports/milestones/M5_qualitative_audit.md`, names the run it was written against, and is
included ONLY if that run is the one being reported - a stale audit cannot survive a re-run.
"""

from __future__ import annotations

import re
from math import comb
from pathlib import Path
from typing import Any

from .ablation import LLM_KINDS

NOT_MEANINGFUL = "NOT YET MEANINGFUL — no second fidelity available"
_AUDIT_FILE = "M5_qualitative_audit.md"


def _fmt(value: Any, spec: str = ".4f") -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "n/a"
    return format(value, spec)


def _header(s: dict[str, Any]) -> list[str]:
    lines = [
        "# M5 — AI vs conventional optimiser ablation",
        "",
        f"> **fidelity: {s['fidelity']}** · aerodynamic model: `{s['aero_model']}` · "
        "generated file, do not edit by hand",
        ">",
        f"> ablation run `{s['run_id']}` (git `{s['git_commit']}`"
        f"{', dirty tree' if s['git_dirty'] else ''}, evaluator source hash "
        f"`{s.get('source_hash') or 'not recorded'}`) · active variables from DOE run "
        f"`{s['doe_run_id']}`"
        + (f" · **replay of `{s['replay_of']}`**" if s.get("replay_of") else ""),
        "",
    ]
    if s["git_dirty"]:
        lines += ["*Produced from an uncommitted working tree; the config snapshot beside the "
                  "result is the authoritative record of what ran.*", ""]
    cfd = sum(sum(m["per_seed"]["cfd_calls"]) for m in s["methods"].values())
    lines += [
        f"**Read this first.** Fidelity {s['fidelity']}, aerodynamic model "
        f"`{s['aero_model']}`, {len(s['active'])} active design variables "
        f"({', '.join(f'`{n}`' for n in s['active'])}) taken from the DOE screening named "
        f"above. **Evaluations at a fidelity above 0 (CFD-backed), all methods and seeds: "
        f"{cfd}.** "
        + ("No CFD-derived number enters any result below. " if cfd == 0 and s["fidelity"] == 0
           else "")
        + "An optimiser comparison is a statement about the methods ON THIS MODEL, under the "
        "limits and variable ranges in the config snapshot; it is not evidence about how the "
        "methods would rank on a different model, and nothing here is a statement about a "
        "real vehicle.",
        "",
    ]
    return lines


def _setup(s: dict[str, Any]) -> list[str]:
    crit = s["criteria_declared"]
    llm = s["llm"]
    kinds = s["method_kinds"]
    lines = [
        "## 1. What was asked, and what was declared before the run",
        "",
        "Spec §24/§46: compare an LLM engineering agent against conventional optimisers under "
        "matched evaluation budgets, and do not claim AI superiority unless it is measured. "
        "The rule for \"measured\" was written into `configs/ai_ablation.yaml` before any "
        "method ran:",
        "",
        f"- **metric:** normalised hypervolume of the feasible set after "
        f"{', '.join(str(c) for c in crit['checkpoints'])} evaluations;",
        "- **comparator:** at each checkpoint, the non-LLM method with the highest mean "
        "hypervolume (\"best conventional\") — beating only the LHS floor does not count;",
        f"- **\"AI helped\"** iff mean HV(`{crit['subject']}`) − mean HV(comparator) ≥ "
        f"{crit['min_hv_gain']} **and** the one-sided exact permutation test gives "
        f"p < {crit['alpha']} after Holm correction across the checkpoints; **\"AI hurt\"** is "
        "the mirror image; anything else is **\"no measured difference\"**.",
        "",
        "## 2. Set-up",
        "",
        f"Every method received exactly **{s['budget']} evaluations per seed**, seeds "
        f"{', '.join(str(x) for x in s['seeds'])}, through the same `BudgetedEvaluator` as M4 "
        "(A-OPT-3: every distinct design costs 1, including geometrically invalid ones; a "
        "repeat is served from cache, logged, and costs 0). Active variables: "
        + ", ".join(f"`{n}`" for n in s["active"]) + ". Hypervolume reference point "
        f"({s['hypervolume']['reference_point'][s['objectives'][0]]:.3g} W/m², "
        f"{s['hypervolume']['reference_point'][s['objectives'][1]]:.0f} K) — M4's, read from "
        "the same config file, not copied.",
        "",
        f"**Why {s['budget']} × {len(s['seeds'])} and not M4's 1000 × 7.** The LLM is the "
        f"scarce resource: the study is hard-capped in code at {llm['max_llm_calls_study']} "
        f"LLM calls ({llm['max_llm_calls']} per seed). M4's 1000-evaluation runs remain the "
        "conventional reference for what a large budget reaches.",
        "",
        "| method | kind | what it is |",
        "|---|---|---|",
    ]
    describe = {
        "lhs_search": "one seeded Latin Hypercube of the whole budget; no learning. M4 code, "
                      "unchanged.",
        "nsga2": "pymoo NSGA-II, constraint-domination. M4 code, unchanged; population from "
                 "the settings column.",
        "bo_parego": "GP per objective and per constraint margin plus a GP validity "
                     "classifier, trained only on evaluated candidates; ParEGO random "
                     "Tchebycheff scalarisation, Monte-Carlo EI × probability of "
                     "feasibility, batched.",
        "ai_agent": "LLM proposes batches from a structured table; strict schema; every "
                    "proposal has a parent and a rationale.",
        "ai_adaptive": f"the same agent plus the fidelity-promotion hook. **{NOT_MEANINGFUL}.**",
    }
    for method, kind in kinds.items():
        settings = {k: v for k, v in s["method_settings"][method].items()
                    if k in ("population_size", "n_initial", "n_initial_per_variable",
                             "batch_size", "rounds", "seeds")}
        lines.append(f"| `{method}` | {kind} | {describe.get(kind, '')} "
                     f"Settings: {settings or '—'} |")
    lines += [
        "",
        *[f"`{m}` runs a population of {st['population_size']}: "
          f"{s['budget'] // int(st['population_size'])} full generations in {s['budget']} "
          "evaluations." for m, st in s["method_settings"].items()
          if st["kind"] == "nsga2"],
        "Where two NSGA-II populations are listed, both were declared before the run so that "
        "NSGA-II is not judged only on a setting chosen for M4's larger budget. `bo_parego` "
        "and the agent start from the **same** seeded initial Latin Hypercube, seed for "
        "seed (size = `n_initial_per_variable` × the number of active variables), which is "
        "what makes their comparison paired.",
        "",
        "**Why ParEGO and not expected hypervolume improvement** (a design choice, made "
        "before the run). Batched EHVI in a constrained box with unevaluable regions needs a "
        "greedy fantasy loop or a joint batch integral; random Tchebycheff weights give batch "
        "diversity at one GP fit per iteration, and the GPs model the objectives themselves, "
        "so the models that drive the search are the ones validated in §5.",
        "",
        "**Invalid geometry — no method gets it for free.** The analytic "
        "`CapsuleGeometry.validate()` rule is not given to any optimiser as a pre-filter or "
        "repair step: an invalid design costs 1 for everyone (A-OPT-3), the Bayesian "
        "optimiser learns the valid region from the designs that came back invalid, and an "
        "LLM proposal that turns out invalid is charged like any other.",
        "",
        "**What the LLM saw, and the asymmetries that remain.** Structured JSON only: the "
        "active variables' names, units and bounds; the frozen parameters; objective and "
        "constraint *names*; the hypervolume reference point; the budget left; a table of "
        "the feasible non-dominated designs, the nearest misses, the most recent evaluations "
        "and recent geometry failures, each with metrics, constraint margins and the "
        "evaluator's failure message; and a digest of its own earlier rounds. It was told "
        "neither the equations of the model nor anything M4 found. The CLI was run in an "
        "empty temporary directory with tools, MCP servers, hooks, skills and CLAUDE.md "
        "discovery disabled, so it could not read this repository. Three asymmetries are "
        "part of what is being measured and are stated rather than removed: (1) **prior "
        "knowledge** — the variable and metric names alone tell an LLM trained on the "
        "aerospace literature that blunter and larger means cooler; the other optimisers "
        "see numbers without names; (2) **failure messages** — the geometry validator's "
        "text says which variable to move (\"increase cone_half_angle_deg …\"), which the "
        "LLM can read and the numeric optimisers cannot; (3) **contamination** — the model "
        "may have seen blunt-body entry optimisation problems like this one in training. A "
        "win by the agent is therefore a win for *priors plus data*, not for data alone.",
        "",
    ]
    return lines


def _results(s: dict[str, Any], fig: str) -> list[str]:
    lines = [
        "## 3. Results (spec §46 table)",
        "",
        "| method | seeds | total evaluations / seed | CFD calls | feasible found (mean) | "
        "HV @ final, mean ± s.d. | min – max | front size (mean) | design diversity, all / "
        "feasible | wall s / seed (mean) | LLM calls | LLM tokens in / out | proposals "
        "rejected |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for method, m in s["methods"].items():
        kind = s["method_kinds"][method]
        agent = s["agent"].get(method)
        wall = s["wall_s"].get(method) or [float("nan")]
        hv = (f"**{m['hv_mean']:.4f} ± {_fmt(m['hv_std'])}**"
              if kind != "ai_adaptive" else f"{NOT_MEANINGFUL} ({m['hv_mean']:.4f}, F0 only)")
        lines.append(
            f"| `{method}` | {m['n_seeds']} | {_fmt(m['budget_used_mean'], '.0f')} | "
            f"{_fmt(m['cfd_calls_mean'], '.0f')} | {_fmt(m['n_feasible_mean'], '.1f')} | {hv} | "
            f"{m['hv_min']:.4f} – {m['hv_max']:.4f} | {_fmt(m['front_size_mean'], '.1f')} | "
            f"{_fmt(m['diversity_all_mean'], '.3f')} / {_fmt(m['diversity_feasible_mean'], '.3f')}"
            f" | {sum(wall) / len(wall):.0f} | "
            + (f"{agent['llm_calls']} | {agent['input_tokens']} / {agent['output_tokens']} | "
               f"{agent['n_proposals_rejected']} of {agent['n_proposals_received']} |"
               if agent else "0 | — | — |"))
    lines += [
        "",
        "s.d. is the sample standard deviation over seeds. *Design diversity* is the mean "
        "pairwise Euclidean distance between a run's evaluated designs in the unit cube of "
        "the active variables (all paid designs / feasible ones only), averaged over seeds: "
        "large = explored widely, small = concentrated. Wall time for the LLM methods is "
        "dominated by model latency and was measured with several seeds running "
        "concurrently, so it is an upper bound per seed, not a CPU cost; the conventional "
        "methods ran one seed at a time on the same 6-process pool. "
        f"All methods and seeds pooled: {s['combined']['n_front']} front designs, normalised "
        f"hypervolume {s['combined']['hv']:.4f}.",
        "",
    ]
    m4 = s.get("m4_reference") or {}
    if m4:
        lines += [
            f"**Against the large-budget reference.** M4's NSGA-II (run `{m4['run_id']}`) "
            f"reached {m4['nsga2_hv_mean_at_full_budget']:.4f} ± "
            f"{m4['nsga2_hv_std_at_full_budget']:.4f} after {m4['budget']} evaluations "
            f"({m4['n_seeds']} seeds). "
            + (f"Determinism check: M5's `nsga2` runs reproduce the first {s['budget']} "
               "evaluations of M4's runs on the shared seeds to within "
               f"{m4['max_abs_hv_difference_vs_m5_nsga2']:.1e} in hypervolume."
               if m4.get("max_abs_hv_difference_vs_m5_nsga2") is not None else ""),
            "",
        ]
    lines += [f"![hypervolume vs evaluations]({fig}/M5_hypervolume.png)", "",
              f"![per-seed hypervolume]({fig}/M5_hypervolume_per_seed.png)", "",
              f"![fronts]({fig}/M5_fronts.png)", "",
              f"![budget use]({fig}/M5_budget_use.png)", ""]
    return lines


def _statistics(s: dict[str, Any]) -> list[str]:
    crit = s["criteria"]
    lines = ["## 4. Statistical comparison", ""]
    if "checkpoints" not in crit:
        return lines + [f"Not evaluated: {crit.get('status', 'unknown')}.", ""]
    n = s["methods"][crit["subject"]]["n_seeds"]
    lines += [
        f"Samples are the per-seed hypervolumes (n = {n} per method). No normality is "
        "assumed. **Rank test:** exact two-sample permutation test on rank sums (the exact "
        "Mann–Whitney test, valid with ties), all C(2n, n) relabellings enumerated. "
        "**Signed-rank:** exact Wilcoxon on seed-wise differences, reported only against "
        "`bo_parego`, the one method that shares the agent's initial design seed for seed. "
        "**A12:** Vargha–Delaney probability that a random agent run beats a random "
        "comparator run (0.5 = none, 1 = always).",
        "",
        f"**Power, stated plainly.** With n = {n} per method the smallest attainable "
        f"one-sided rank-test p is 1/{comb(2 * n, n)} = {1 / comb(2 * n, n):.4f} — reachable "
        "only when every run of one method beats every run of the other — and the smallest "
        f"attainable *two-sided* signed-rank p is 2/{2 ** n} = {2 / 2 ** n:.4f}"
        + (", which can never reach 0.05" if 2 / 2 ** n > 0.05 else "")
        + ". A \"no measured difference\" below therefore means *this study could not tell "
        "them apart*, not *they are equivalent*. Effect sizes and the raw per-seed values "
        "are given so the reader is not left with a p-value alone.",
        "",
        "### Pre-declared comparison: agent vs best conventional",
        "",
        "| evaluations | best conventional (mean HV) | agent mean HV | difference | A12 | "
        "rank test p (agent better) | Holm | p (agent worse) | Holm | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n_eval, cell in crit["checkpoints"].items():
        lines.append(
            f"| {n_eval} | `{cell['comparator']}` ({cell['mean_b']:.4f}) | {cell['mean_a']:.4f} "
            f"| {cell['mean_difference']:+.4f} | {cell['a12']:.2f} | "
            f"{cell['rank_test']['p_greater']:.4f} | {cell['p_helped_holm']:.4f} | "
            f"{cell['rank_test']['p_less']:.4f} | {cell['p_hurt_holm']:.4f} | "
            f"**{cell['verdict']}** |")
    lines += ["", "### Agent vs every non-LLM method (descriptive; not the declared test)", "",
              "| evaluations | comparator | comparator mean HV | agent − comparator | A12 | "
              "rank test p, two-sided | seeds agent better | signed-rank p, two-sided |",
              "|---|---|---|---|---|---|---|---|"]
    for n_eval, row in crit["pairwise"].items():
        for method, cell in row.items():
            paired = cell.get("signed_rank_test")
            lines.append(
                f"| {n_eval} | `{method}` | {cell['mean_b']:.4f} | "
                f"{cell['mean_difference']:+.4f} | {cell['a12']:.2f} | "
                f"{cell['rank_test']['p_two_sided']:.4f} | "
                + (f"{cell['seeds_a_better']} of {len(cell['paired_differences'])} | "
                   f"{paired['p_two_sided']:.4f} |" if paired else "— | — |"))
    lines += ["", "These rows are not corrected for multiplicity and are not the basis of any "
              "claim; they are here so that a reader can see every comparison, not only the "
              "one the rule selected.", ""]
    return lines


def _surrogate(s: dict[str, Any], fig: str) -> list[str]:
    sur = s["surrogate"]
    lines = [
        "## 5. Surrogate validation (spec §25)",
        "",
        "Two held-out tests, both on designs the model had never seen, both in the modelled "
        "space (log₁₀ for heat flux, where the GP's Gaussian assumption is made).",
        "",
    ]
    static = sur.get("static", {})
    if static.get("pooled"):
        lines += [
            f"**(a) Static.** For each seed, GPs were trained on that seed's "
            f"`{static['train_method']}` designs that returned physics and scored on the "
            "next seed's — evaluations the ablation had already paid for. Test points are "
            "split by whether they lie inside the convex hull of the training inputs.",
            "",
            "| output | region | n | RMSE | MAE | R² (median over splits) | z s.d. (1 = "
            "calibrated) | coverage of the 50 / 68 / 90 / 95 % interval |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for name, cell in static["pooled"].items():
            for region in ("inside_hull", "outside_hull"):
                r = cell[region]
                if not r.get("n"):
                    continue
                cov = " / ".join(f"{r['coverage'][k]:.2f}" for k in sorted(r["coverage"]))
                lines.append(
                    f"| `{name}`{' (log₁₀)' if cell['transform'] == 'log10' else ''} | "
                    f"{region.replace('_', ' ')} | {r['n']} | {r['rmse']:.3g} | {r['mae']:.3g} "
                    f"| {_fmt(r['r2_median'], '.3f')} | {_fmt(r['z_std_median'], '.2f')} | "
                    f"{cov} |")
        val = static.get("validity_classifier") or []
        if val:
            acc = sum(v["accuracy"] for v in val) / len(val)
            brier = sum(v["brier"] for v in val) / len(val)
            base = sum(v["base_rate_valid"] for v in val) / len(val)
            lines += ["", f"Validity classifier (does the design return physics at all), mean "
                      f"over {len(val)} splits: accuracy {acc:.3f}, Brier score {brier:.3f}, "
                      f"against a base rate of {base:.2f} valid — always guessing the "
                      f"majority class would score {max(base, 1 - base):.3f}.", ""]
    pro = sur.get("prospective", {})
    if pro.get("n_records"):
        lines += [
            f"**(b) Prospective.** Inside `bo_parego`, every design's prediction was logged "
            f"*before* it was evaluated ({pro['n_records']} designs over all seeds). This is "
            "the test scored where the optimiser actually went. "
            f"**{pro['n_extrapolated']} of {pro['n_records']} "
            f"({100 * pro['fraction_extrapolated']:.0f}%) of those picks lay outside the "
            "convex hull of the training data** and were flagged as extrapolations at the "
            "time they were made.",
            "",
            "| output | region | n | RMSE | MAE | R² | z s.d. | coverage 50 / 68 / 90 / 95 % |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for name, cell in pro["outputs"].items():
            for region in ("inside_hull", "outside_hull"):
                r = cell[region]
                if not r.get("n"):
                    continue
                cov = " / ".join(f"{r['coverage'][k]:.2f}" for k in sorted(r["coverage"]))
                lines.append(f"| `{name}` | {region.replace('_', ' ')} | {r['n']} | "
                             f"{r['rmse']:.3g} | {r['mae']:.3g} | {_fmt(r['r2'], '.3f')} | "
                             f"{_fmt(r['z_std'], '.2f')} | {cov} |")
        v = pro["validity"]
        lines += ["", f"Validity probability on the same picks: accuracy {v['accuracy']:.3f}, "
                  f"Brier {v['brier']:.3f}, base rate valid {v['base_rate_valid']:.2f}.", ""]
    lines += [
        "**Extrapolation policy.** `GPSurrogate.predict` *refuses* (raises) outside the "
        "training hull by default; a number of record cannot be produced there. The "
        "acquisition function is the one caller allowed to pass `on_extrapolation=\"flag\"`: "
        "it is buying an evaluation at that point, not trusting the prediction, and every "
        "such pick is flagged and counted above. R² is unstable when a held-out set has "
        "little variance (a general property of R², not a finding about this run), so RMSE "
        "and interval coverage are given beside it.",
        "",
        f"![surrogate calibration]({fig}/M5_surrogate_calibration.png)",
        "",
    ]
    return lines


def _agent(s: dict[str, Any]) -> list[str]:
    objectives = s["objectives"]
    lines = ["## 6. The agent's behaviour", ""]
    for method, a in s["agent"].items():
        kind = s["method_kinds"][method]
        exp = a["expected_outcome"]
        lines += [
            f"### `{method}`" + (f" — {NOT_MEANINGFUL}" if kind == "ai_adaptive" else ""),
            "",
            f"- model: {', '.join(f'`{m}`' for m in a['models']) or 'n/a'}"
            + (" (responses **replayed** from disk, no live call)" if a["replayed"] else ""),
            f"- LLM calls: **{a['llm_calls']}** ({a['call_outcomes']}); tokens in / out "
            f"{a['input_tokens']} / {a['output_tokens']}; summed call wall time "
            f"{a['llm_wall_s']:.0f} s; list-price cost as reported by the CLI "
            f"${a['cost_usd_list_price']:.2f} (a subscription login was used; no API key)",
            f"- proposals: {a['n_proposals_received']} received, {a['n_proposals_accepted']} "
            f"accepted, **{a['n_proposals_rejected']} rejected** "
            f"({a['rejections_by_reason'] or 'none'}); malformed responses "
            f"{a['n_malformed_responses']}; failed calls {a['n_failed_calls']}; budget spent on "
            f"the LHS fallback because the agent could not fill it: "
            f"{a['fallback_evaluations']} evaluations",
            f"- the agent's own numeric predictions ({exp['n_scored']} scored): feasibility "
            f"called correctly {100 * exp['feasibility_accuracy']:.0f}% of the time "
            f"(it predicted feasible {exp['n_predicted_feasible']}×, "
            f"{exp['n_actually_feasible']} were); "
            + "; ".join(f"`{n}` MAE {exp[n]['mae']:.3g}, bias {exp[n]['bias']:+.3g}"
                        for n in objectives),
            "",
        ]
        if kind == "ai_adaptive":
            f = a["fidelity"]
            lines += [
                f"**Adaptive-fidelity hook — {NOT_MEANINGFUL}.** The promotion policy "
                "(`src/aether/optimization/fidelity.py`; spec §26: predicted Pareto value, "
                "uncertainty, novelty, cost) was called on every accepted proposal: "
                f"{f['n_decisions']} decisions, the agent asked for Fidelity 1 on "
                f"{f['n_agent_requested_high']}, the policy wanted to promote "
                f"{f['n_policy_promotions']}, and **{f['n_granted']} were granted**. "
                + ("No Fidelity-1 evaluator was available to this run, so every candidate "
                   "was evaluated at Fidelity 0 and this method's search is, by construction, "
                   "the plain agent's with different LLM samples. Its hypervolume is printed "
                   "only to show the plumbing ran; it is excluded from every comparison and "
                   "says nothing about adaptive fidelity. "
                   if f["n_granted"] == 0 else
                   "Promotions WERE granted in this run: the label on this section is stale "
                   "and the report generator must be updated for M6 before this is read. ")
                + "The policy thresholds are placeholders until they are set against real "
                "CFD cost data.",
                "",
            ]
    return lines


def _audit(root: Path, s: dict[str, Any]) -> list[str]:
    lines = ["## 7. Qualitative audit of the agent's stated mechanisms", ""]
    path = root / "reports" / "milestones" / _AUDIT_FILE
    target = s.get("replay_of") or s["run_id"]
    if path.exists():
        text = path.read_text()
        match = re.search(r"^audited_run:\s*(\S+)\s*$", text, flags=re.MULTILINE)
        if match and match.group(1) == target:
            body = text.split("---", 2)[-1].strip() if text.startswith("---") else text
            return lines + [f"*Hand-written after reading every round of run `{target}` "
                            f"(`results/M5/{target}/agent_log.json` and the raw responses "
                            "beside it); the only part of this report not generated from "
                            "`summary.json`.*", "", body, ""]
    return lines + [
        f"**Not yet written for run `{target}`.** The audit is a human/agent reading of the "
        f"mechanisms in `results/M5/{target}/agent_log.json`; an audit written against an "
        f"earlier run is deliberately not shown. Write `reports/milestones/{_AUDIT_FILE}` "
        f"with front-matter `audited_run: {target}` and re-run "
        f"`make ablation-report RUN_ID={s['run_id']}`.", ""]


def _gaming(s: dict[str, Any]) -> list[str]:
    gaming = s["gaming"]
    constraints = sorted({c for g in gaming.values()
                          for c in g["front_share_within_1pct_of_constraint"]})
    variables = list(s["active"])
    lines = [
        "## 8. Metric-gaming audit, per method",
        "",
        "The question for every method: is its hypervolume coming from physics, or from "
        "something the model or the meter gets wrong? Every sentence below the tables is "
        "generated from the tables; a check that found nothing says so.",
        "",
        "Share of each method's front designs (seeds pooled) within 1% of a constraint:",
        "",
        "| method | front designs | " + " | ".join(f"`{c}`" for c in constraints) + " |",
        "|---|---|" + "---|" * len(constraints),
    ]
    for method, g in gaming.items():
        fence = g["front_share_within_1pct_of_constraint"]
        lines.append(f"| `{method}` | {g['n_front_designs']} | "
                     + " | ".join(_fmt(fence.get(c), ".0%") for c in constraints) + " |")
    lines += ["", "Share of front designs parked within 1% of a box bound (lower / upper):", "",
              "| method | " + " | ".join(f"`{v}`" for v in variables) + " |",
              "|---|" + "---|" * len(variables)]
    for method, g in gaming.items():
        parked = g["front_share_parked_on_bound"]
        lines.append(f"| `{method}` | " + " | ".join(
            f"{parked[v]['at_lower']:.0%} / {parked[v]['at_upper']:.0%}" if v in parked
            else "n/a" for v in variables) + " |")
    lines += ["", "Where the budget went, and free evaluations:", "",
              "| method | budget spent on no-physics designs | on inert repeats | "
              "near-repeats (< 1e-3 in the unit cube) | cache hits | of which counted in "
              "hypervolume |", "|---|---|---|---|---|---|"]
    for method, g in gaming.items():
        lines.append(f"| `{method}` | {g['budget_share_no_physics']:.0%} | "
                     f"{g['budget_share_inert_repeat']:.1%} | {g['near_repeats']} | "
                     f"{g['cache_hits']} | {g['cache_hits_counted_in_hypervolume']} |")
    lines.append("")

    half = 0.5
    for c in constraints:
        leaning = [m for m, g in gaming.items()
                   if (g["front_share_within_1pct_of_constraint"].get(c) or 0.0) > half]
        if leaning:
            lines.append(f"- **Fence `{c}`:** more than half of the front designs of "
                         + ", ".join(f"`{m}`" for m in leaning) + " sit within 1% of it. "
                         "Hypervolume from these methods partly measures how precisely they "
                         "park on that limit; if the limit is a placeholder, so is that part "
                         "of the score.")
    for v in variables:
        for side in ("at_lower", "at_upper"):
            parked = [m for m, g in gaming.items()
                      if g["front_share_parked_on_bound"].get(v, {}).get(side, 0.0) > half]
            if parked:
                lines.append(f"- **Box bound, `{v}` {side.replace('at_', '')}:** more than "
                             "half of the front designs of "
                             + ", ".join(f"`{m}`" for m in parked) + " are parked on it — an "
                             "optimum of the box, not of the physics.")
    if len(lines) and lines[-1] == "":
        lines.append("- No method has more than half of its front within 1% of any "
                     "constraint or box bound.")
    hits = {m: g["cache_hits"] for m, g in gaming.items() if g["cache_hits"]}
    lines.append("- **Cache = free evaluations.** Cache hits cost 0 by design (A-OPT-3) and "
                 "the hypervolume curve is computed from paid rows only. "
                 + (f"Cache hits occurred: {hits}." if hits else
                    "No method produced a cache hit in this run."))
    repeats = {m: g["near_repeats"] for m, g in gaming.items() if g["near_repeats"]}
    lines.append("- **Near-repeats** (a paid design within 1e-3 of an earlier one — a way "
                 "round the 12-significant-digit cache that buys no information): "
                 + (f"{repeats}." if repeats else "none in this run."))
    inert = {m: f"{g['budget_share_inert_repeat']:.1%}" for m, g in gaming.items()
             if g["budget_share_inert_repeat"] > 0.0}
    lines.append("- **Inert repeats** (paid evaluations whose objective vector is "
                 "bit-identical to an earlier one: a variable the model cannot see was "
                 "moved; `feasible_front` keeps one representative, so they are waste, not "
                 "gain): " + (f"{inert}." if inert else "none in this run."))
    lines += ["- Anything found here that needed a write-up is in "
              "`docs/negative_results.md`.", ""]
    return lines


def _limitations(s: dict[str, Any]) -> list[str]:
    n = len(s["seeds"])
    cost = s.get("cost") or {}
    lines = [
        "## 9. Limitations",
        "",
        f"1. **Fidelity {s['fidelity']}, aerodynamic model `{s['aero_model']}`, "
        f"{len(s['active'])} active variables.** The comparison holds for this model and "
        "this design space only; it must be re-run, not reused, when either changes.",
        f"2. **n = {n} seeds**, set by the LLM call cap, not by a power analysis. The exact "
        "tests are valid at this n but weak (§4).",
        "3. **The LLM is not a fixed algorithm.** Its responses are sampled; a re-run issues "
        "new calls and will give different numbers. The *recorded* run is reproducible "
        "through replay mode, which is a statement about the pipeline, not about the model. "
        "The model identifier is recorded per call.",
        "4. **Prior knowledge and contamination** cannot be separated from reasoning-from-"
        "data in this design (§2). The qualitative audit is the only handle on it.",
        "5. **Budget is counted in evaluations, not in cost.** "
        + (f"In this run one evaluation took a median of {cost['eval_wall_s_median']:.2f} s "
           "of worker time"
           + (f", and one LLM round a mean of {cost['llm_round_wall_s_mean']:.0f} s"
              if cost.get("llm_round_wall_s_mean") is not None else "")
           + ". " if cost.get("eval_wall_s_median") is not None else "")
        + "Hypervolume per evaluation and hypervolume per second are different questions; "
        "this report answers the first.",
        "6. **Development history.** `bo_parego` was changed twice after a single-seed smoke "
        "test and before any study run (NR-17); that seed is excluded from the study seeds. "
        "An earlier study run was aborted when the physics changed under it (NR-18) and no "
        "number from it was inspected.",
        "7. Hypervolume inherits M4's fixed reference point and whatever placeholder limits "
        "the design-space config carries (see the config snapshot and ASSUMPTIONS A-LIM-*, "
        "A-OPT-4).",
        "",
    ]
    return lines


def _reproduce(s: dict[str, Any]) -> list[str]:
    target = s.get("replay_of") or s["run_id"]
    return [
        "## Reproduce",
        "",
        "```",
        "make ablation                          # LIVE: new LLM calls, new run ID, new numbers",
        f"make ablation-replay RUN_ID={target}   # no LLM access needed",
        f"make ablation-report RUN_ID={target}   # rebuild summary, figures, report from logs",
        "```",
        "",
        "`make ablation` needs the Claude Code CLI installed and signed in (no API key is read "
        "or accepted). `make ablation-replay` re-runs EVERY evaluation from the recorded "
        "responses, checks that each method's per-seed hypervolumes match the original run, "
        "and writes to its own run directory without touching this report. "
        f"Prompts and raw responses: `results/M5/{target}/llm/<method>/seed_<n>/`. Replay uses "
        "that run's `config_snapshot.yaml`, not today's config files, so it stays "
        "reproducible after the design-space config or the physics defaults change — "
        "provided the legacy behaviour it ran with remains selectable.",
        "",
    ]


def write_m5_report(root: Path, summary: dict[str, Any], path: Path, *,
                    figure_prefix: str = "../figures") -> Path:
    lines = [*_header(summary), *_setup(summary), *_results(summary, figure_prefix),
             *_statistics(summary), *_surrogate(summary, figure_prefix), *_agent(summary),
             *_audit(root, summary), *_gaming(summary), *_limitations(summary),
             *_reproduce(summary)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


__all__ = ["LLM_KINDS", "NOT_MEANINGFUL", "write_m5_report"]
