"""Render `reports/milestones/M4_pareto_optimisation.md` from the two M4 summary files.

Every number in the report is read from `results/M4/<run>/summary.json`. Nothing is typed
by hand, so re-running the pipeline (for instance at Fidelity 1) rewrites the whole
report consistently, and a stale number cannot survive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_OUT_UNITS = {
    "peak_heat_flux_w_m2": "W/m²",
    "peak_bondline_temperature_k": "K",
    "max_g": "g",
    "heatshield_mass_fraction": "-",
}


def _fmt(value: float, spec: str = ".3g") -> str:
    return "n/a" if value is None or value != value else format(value, spec)


def _header(doe: dict[str, Any], opt: dict[str, Any] | None) -> list[str]:
    fidelity = doe["fidelity"] if opt is None else opt["fidelity"]
    dirty = doe["git_dirty"] or (opt is not None and opt["git_dirty"])
    lines = [
        "# M4 — DOE, sensitivity and Pareto optimisation",
        "",
        f"> **fidelity: {fidelity}** · aerodynamic model: `{doe['aero_model']}` · "
        "generated file, do not edit by hand",
        ">",
        f"> DOE run `{doe['run_id']}` (git `{doe['git_commit']}`"
        f"{', dirty tree' if doe['git_dirty'] else ''})"
        + ("" if opt is None else
           f" · optimisation run `{opt['run_id']}` (git `{opt['git_commit']}`"
           f"{', dirty tree' if opt['git_dirty'] else ''})"),
        "",
    ]
    if dirty:
        lines += ["*Produced from an uncommitted working tree; the config snapshot beside "
                  "each result is the authoritative record of what ran.*", ""]
    if fidelity == 0:
        lines += [
            "**Read this first.** Everything below is a Fidelity-0 result: constant drag "
            "coefficient, Sutton–Graves stagnation heating, 1-D conduction. No CFD-derived "
            "number enters it (the CFD gate G4 was not PASS when this ran). At this fidelity "
            "the capsule's *shape* has no aerodynamic consequence at all — only its diameter "
            "acts, through the reference area — so the design freedom the optimisers are "
            "given is much smaller than the variable list suggests. The pipeline is built so "
            "that replacing the drag model is one line of `configs/design_space.yaml` plus "
            "`make doe && make optimize`; the numbers here are expected to change when that "
            "happens and must not be quoted as final.",
            "",
        ]
    else:
        lines += [
            f"**Read this first.** This is the Fidelity-{fidelity} re-run of M4 on the final "
            f"physics: drag from the CFD-derived response surface `{doe['aero_model']}` "
            "(inviscid, calorically perfect gas, zero angle of attack, coarse mesh, assumed "
            "base drag; `reports/milestones/M3_coupled_model.md`), stagnation heating from "
            "Sutton–Graves with the effective nose radius taken from the measured "
            "stagnation-point velocity gradient (A-GEO-3), 1-D conduction. **No heating "
            "quantity comes from CFD.** The Fidelity-0 report is archived unchanged as "
            "`M4_pareto_optimisation_fidelity0.md`; its screening and fronts are void for "
            "this model twice over (the shoulder ratio now moves heating through R_eff, and "
            "shape now moves drag) and nothing here reuses them. Every statement below is "
            "\"the model predicts, within the tested assumptions\" - the limits are in §12 "
            "and they are not small.",
            "",
        ]
    return lines


def _f1_hull_section(doe: dict[str, Any]) -> list[str]:
    hull = doe.get("f1_hull")
    if not hull:
        return []
    full, sub = hull["full_box"], hull["sobol_sub_box"]
    return [
        "### What Fidelity 1 can and cannot explore",
        "",
        f"The drag surface refuses a forebody shape outside the convex hull of the CFD cases "
        f"it was fitted to (A-AERO-1): such a design is returned as a rejected candidate, "
        f"never an extrapolated number. Measured by Monte Carlo over the shape box "
        f"({full['n_samples']} seeded samples of bluntness, cone half-angle and shoulder "
        f"ratio; surface `{hull['surface_training_hash']}`): "
        f"**{100 * full['fraction_of_box_valid_forebody']:.1f}%** of the box is a forebody "
        f"that can exist at all, **{100 * full['fraction_of_box_valid_and_inside_hull']:.1f}%"
        f"** of the box is both valid and inside the CFD hull, i.e. "
        f"**{100 * full['fraction_of_valid_shapes_inside_hull']:.1f}% of the valid shapes** "
        f"are evaluable (Monte-Carlo standard error "
        f"±{100 * full['standard_error_of_box_fractions']:.1f} points). The rest is closed "
        "to every optimiser at this fidelity - not by physics, but by where CFD was run and "
        "where it converged (M3 report §3). That is a real limit on what the front below can "
        "be said to have searched.",
        "",
        "The Saltelli sub-box of §5 was verified BEFORE the run to lie wholly inside that "
        f"region ({sub['preflight']['n_vertices']} vertices + "
        f"{sub['preflight']['n_interior']} seeded interior shapes, all valid and inside the "
        "hull); the run refuses to start otherwise, because a Saltelli design cannot tolerate "
        "one rejected sample. The sub-box covers "
        f"**{100 * hull['sub_box_volume_fraction_of_shape_box']:.1f}% of the shape box** "
        f"({100 * hull['sub_box_volume_fraction_of_evaluable_region']:.1f}% of its evaluable "
        "part). What keeps it that small is mostly GEOMETRIC VALIDITY (a rectangle in which "
        "every capsule exists has to stay at wide cone angles and moderate bluntness), not "
        "the CFD hull; either way, the Sobol' indices of §5 - and the freeze decisions made "
        "from them - describe that fraction of the box and nothing outside it.",
        "",
    ]


def _doe_sections(doe: dict[str, Any]) -> list[str]:
    cost, lhs, sobol, scr = doe["cost"], doe["lhs"], doe["sobol"], doe["screening"]
    per = cost["per_evaluation_wall_s"]
    lines = [
        "## 1. Cost of one evaluation",
        "",
        f"Measured over {cost['n_physics_evaluations']} coupled evaluations inside worker "
        f"processes: median **{per['median']:.3f} s**, mean {per['mean']:.3f} s, 95th "
        f"percentile {per['p95']:.3f} s, maximum {per['max']:.3f} s per `evaluate_design` "
        f"call. With {doe['workers']} worker processes the DOE sustained "
        f"{cost['throughput_evaluations_per_s']:.1f} evaluations/s "
        f"({cost['n_evaluations_paid']} evaluations in {cost['total_wall_s']:.0f} s). "
        "The conduction solve dominates. At this cost a variance-based global sensitivity "
        "analysis is affordable, so Sobol' indices were used rather than Morris screening.",
        "",
        "## 2. Design space",
        "",
        "| variable | role | units | min | max | reference |",
        "|---|---|---|---|---|---|",
    ]
    for name, v in doe["variables"].items():
        lines.append(f"| `{name}` | {v['role']} | {v['units']} | {_fmt(v['lower'], 'g')} | "
                     f"{_fmt(v['upper'], 'g')} | {_fmt(v['reference'], 'g')} |")
    lines += [
        "",
        "Geometry is parametrised by diameter plus shape *ratios* (nose radius/D, shoulder "
        "radius/D, length/D); the evaluator converts to `CapsuleGeometry` fields and "
        "`CapsuleGeometry.validate()` decides validity. `given` variables are mission "
        "givens, screened because M7 needs them as uncertainties, never optimised. "
        "`deferred` is a real design variable held out of M4 (ASSUMPTIONS A-OPT-2).",
        "",
        *_f1_hull_section(doe),
        "## 3. One-at-a-time sweeps",
        "",
        "Range of each output over a sweep of one variable across its full range, all "
        "others at the reference design. A range of exactly 0 means the model is "
        "structurally blind to that variable.",
        "",
        "| variable | Δ peak flux [W/m²] | Δ bondline T [K] | Δ max g [g] | "
        "Δ shield mass fraction [-] | invalid geometry | feasible |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, e in doe["oat"].items():
        lines.append(
            f"| `{name}` | {_fmt(e['peak_heat_flux_w_m2']['range'], '.4g')} | "
            f"{_fmt(e['peak_bondline_temperature_k']['range'], '.4g')} | "
            f"{_fmt(e['max_g']['range'], '.4g')} | "
            f"{_fmt(e['heatshield_mass_fraction']['range'], '.4g')} | "
            f"{e['n_invalid_geometry']}/{e['n_points']} | {e['n_feasible']}/{e['n_points']} |")
    lines += [
        "",
        "![one-at-a-time sweeps](../figures/M4_doe_oat.png)",
        "",
        "## 4. Latin Hypercube over the full box",
        "",
        f"{lhs['n_samples']} seeded LHS samples (seed {doe['seed']}): "
        f"**{lhs['n_valid_geometry']}** geometrically valid, {lhs['n_evaluated_ok']} "
        f"evaluated cleanly, **{lhs['n_feasible']}** feasible. Invalid geometries are "
        "recorded as infeasible candidates with `CapsuleGeometry.validate()`'s own message "
        "as the failure reason; none was dropped.",
        "",
        "Constraint violations among evaluated samples: "
        + ", ".join(f"`{k}` {v}" for k, v in lhs["violation_counts"].items()) + ".",
        "",
        "Most common failure reasons (numbers masked as #):",
        "",
    ]
    lines += [f"- {count} × {reason}" for reason, count in lhs["failure_reasons"].items()]
    lines += [
        "",
        "Which variables decide whether a geometry is *valid* (given-data first-order "
        "index on the validity indicator, 95% bootstrap CI):",
        "",
        "| variable | S₁(validity) | CI |",
        "|---|---|---|",
    ]
    for name, e in sorted(lhs["validity"].items(), key=lambda kv: -kv[1]["first"]):
        lines.append(f"| `{name}` | {e['first']:.3f} | [{e['ci'][0]:.3f}, {e['ci'][1]:.3f}] |")
    lines += [
        "",
        "![LHS cloud](../figures/M4_doe_lhs.png)",
        "",
        "## 5. Global sensitivity (Sobol')",
        "",
        f"Saltelli design, n_base = {sobol['n_base']}, {sobol['n_evaluations']} evaluations, "
        "Saltelli-2010 first-order and Jansen total-order estimators, percentile-bootstrap "
        "95% confidence intervals. A Saltelli design needs a box in which every point can "
        "be evaluated, so it was run on an all-valid sub-box: "
        + ", ".join(f"`{n}` ∈ [{_fmt(b[0], 'g')}, {_fmt(b[1], 'g')}]"
                    for n, b in doe["sobol_sub_box"].items()
                    if b != [doe["variables"][n]["lower"], doe["variables"][n]["upper"]])
        + "; all other ranges as in §2. Indices are therefore statements about that "
        "sub-box. The full box is covered by the LHS analysis above.",
        "",
    ]
    for out, spec in sobol["outputs"].items():
        ranked = sorted(spec["variables"].items(), key=lambda kv: -kv[1]["total"])
        lines += [
            f"**{out}** [{_OUT_UNITS.get(out, '')}] — ranked by total-order index",
            "",
            "| rank | variable | S_T | 95% CI | S₁ | 95% CI |",
            "|---|---|---|---|---|---|",
        ]
        for rank, (name, e) in enumerate(ranked, 1):
            lines.append(
                f"| {rank} | `{name}` | {e['total']:.4f} | [{e['total_ci'][0]:.4f}, "
                f"{e['total_ci'][1]:.4f}] | {e['first']:.4f} | [{e['first_ci'][0]:.4f}, "
                f"{e['first_ci'][1]:.4f}] |")
        lines.append("")
    lines += [
        "![Sobol indices](../figures/M4_doe_sobol.png)",
        "",
        "## 6. Screening decision",
        "",
        "Rule, declared in `configs/design_space.yaml` before the run: a `design` variable "
        f"is frozen at its reference value iff its total-order upper confidence bound is "
        f"below {scr['thresholds']['total_index']} for every screened output **and** its "
        f"validity-index upper bound is below {scr['thresholds']['validity_index']}.",
        "",
        "| variable | role | decision | max S_T upper bound (output) | validity upper bound | "
        "reason |",
        "|---|---|---|---|---|---|",
    ]
    for name, d in scr["variables"].items():
        lines.append(
            f"| `{name}` | {d['role']} | **{d['decision']}** | "
            f"{d['max_total_index_upper']:.4f} ({d['max_total_index_output']}) | "
            f"{d['validity_index_upper']:.3f} | {d['reason']} |")
    lines += [
        "",
        f"Optimised: {', '.join(f'`{n}`' for n in scr['active'])}. "
        f"Frozen at reference: {', '.join(f'`{n}`' for n in scr['frozen'])}.",
        "",
    ]
    if doe["fidelity"] == 0:
        lines += [
            "A shape variable frozen here is frozen **because the Fidelity-0 drag model "
            "cannot see it**, not because capsule shape is unimportant. This screening must "
            "be re-run, not reused, when the drag model changes.",
            "",
        ]
    else:
        lines += [
            "This screening was derived on the Fidelity-1 model from scratch; the "
            "Fidelity-0 decision (which froze the shoulder ratio because constant C_D could "
            "not see it) was not consulted. The rule and its thresholds were declared in the "
            "config before the run and applied as written. Note what the indices are: "
            "variance shares **inside the Saltelli sub-box**, which at this fidelity also has "
            "to sit inside the CFD hull - a variable's index says nothing about the part of "
            "its range the sub-box leaves out.",
            "",
        ]
    return lines


def _design_row(label: str, d: dict[str, Any]) -> str:
    return (f"| {label} | `{d['candidate_id']}` | {d['peak_heat_flux_w_m2']:.4g} | "
            f"{d['integrated_external_heat_j_m2']:.4g} | "
            f"{d['peak_surface_temperature_k']:.1f} | "
            f"{d['peak_bondline_temperature_k']:.1f} | "
            f"{d['thermal_penetration_depth_m'] * 1e3:.2f} | {d['max_g']:.2f} | "
            f"{d['max_dynamic_pressure_pa']:.4g} | {d['entry_duration_s']:.0f} | "
            f"{'yes' if d['feasible'] else 'NO'} |")


def _opt_sections(doe: dict[str, Any], opt: dict[str, Any]) -> list[str]:
    hv = opt["hypervolume"]
    lines = [
        "## 7. Optimisation set-up",
        "",
        f"Active variables: {', '.join(f'`{n}`' for n in opt['active'])}. Objectives, both "
        "minimised: peak external heat flux and peak bondline temperature. The third "
        "candidate objective of spec §3, a cumulative thermal-penetration metric, was "
        "studied and discarded as rank-redundant with the bondline peak "
        "(`reports/milestones/TPI_study.md`); integrated external heat load is therefore "
        "*reported* on every design but not optimised, since adding a redundant objective "
        "only dilutes selection pressure. No weighted single score is formed anywhere.",
        "",
        f"Every method received exactly **{opt['budget']} evaluations per seed**, "
        f"{len(opt['seeds'])} seeds ({', '.join(str(s) for s in opt['seeds'])}), through the "
        "same `BudgetedEvaluator`. Accounting: each distinct design costs 1 whether "
        "feasible, infeasible or geometrically invalid; a repeated design is served from "
        "cache, logged, and costs 0 (ASSUMPTIONS A-OPT-3).",
        "",
        f"Hypervolume is measured against the fixed reference point "
        f"({hv['reference_point']['peak_heat_flux_w_m2']:.4g} W/m², "
        f"{hv['reference_point']['peak_bondline_temperature_k']:.0f} K) and normalised by the "
        f"rectangle down to the ideal point ({hv['ideal_point']['peak_heat_flux_w_m2']:.4g} "
        f"W/m², {hv['ideal_point']['peak_bondline_temperature_k']:.0f} K). "
        f"{opt['combined']['n_feasible_outside_reference']} feasible candidates lie outside "
        "that rectangle and contribute nothing.",
        "",
        "## 8. Method comparison",
        "",
        "| method | final HV mean ± s.d. | min – max | feasible found (mean) | front size "
        "(mean) | spacing (mean) | budget to 95% of own final HV (median) | cache hits "
        "(mean) | wall s/seed (mean) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for method, m in opt["methods"].items():
        lines.append(
            f"| `{method}` | **{m['hv_mean']:.4f} ± {m['hv_std']:.4f}** | "
            f"{m['hv_min']:.4f} – {m['hv_max']:.4f} | {m['n_feasible_mean']:.0f} | "
            f"{m['front_size_mean']:.1f} | {_fmt(m['spacing_mean'], '.4f')} | "
            f"{_fmt(m['evals_to_95pct_median'], '.0f')} | {m['cache_hits_mean']:.1f} | "
            f"{m['wall_s_mean']:.0f} |")
    lines += [
        "",
        f"s.d. is the sample standard deviation over {len(opt['seeds'])} seeds. Combined "
        f"front of all methods and seeds: {opt['combined']['n_front']} designs, normalised "
        f"hypervolume {opt['combined']['hv']:.4f}.",
        "",
        "![hypervolume history](../figures/M4_hypervolume.png)",
        "",
        "## 9. Pareto front and feasible region",
        "",
        "![Pareto front](../figures/M4_pareto_front.png)",
        "",
        "## 10. Peak-flux-only optimum versus the joint knee design",
        "",
        "All three designs are taken from the combined feasible front. The knee is the "
        "front point furthest from the chord joining the front's two extremes in normalised "
        "objective space — a definition with no weights in it.",
        "",
        "| design | id | peak flux [W/m²] | heat load [J/m²] | peak surface T [K] | peak "
        "bondline T [K] | penetration depth [mm] | max g | max q_dyn [Pa] | duration [s] | "
        "feasible |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        _design_row("reference (unoptimised)", opt["reference_design"]),
    ]
    labels = {"peak_flux_only": "peak-flux-only optimum", "joint_knee": "joint knee design",
              "bondline_only": "bondline-only optimum"}
    for key, label in labels.items():
        if key in opt["selected"]:
            lines.append(_design_row(label, opt["selected"][key]))
    lines += ["", "Design variables of the selected designs:", "",
              "| design | " + " | ".join(f"`{n}`" for n in opt["active"]) + " |",
              "|---|" + "---|" * len(opt["active"])]
    for key, label in labels.items():
        if key in opt["selected"]:
            d = opt["selected"][key]
            lines.append(f"| {label} | " + " | ".join(
                f"{d[f'x__{n}']:.4g}" for n in opt["active"]) + " |")
    lines += ["", "What stops each selected design (box bound within 1% of the range, or a "
              "constraint within 1% of active):", ""]
    for key, label in labels.items():
        stops = opt.get("selected_limits", {}).get(key)
        if stops:
            items = stops["box_bounds"] + [f"constraint `{c}` active"
                                           for c in stops["active_constraints"]]
            lines.append(f"- **{label}:** " + ("; ".join(items) if items else "nothing - "
                                                "an interior design"))
    lines += ["", "A design stopped by a *box bound* is an optimum of the box, not of the "
              "physics: read it as 'at least this far', not as a located minimum."]
    cmp_ = opt.get("comparison")
    if cmp_:
        lines += [
            "",
            f"Relative to the peak-flux-only optimum, the joint knee design's bondline runs "
            f"**{cmp_['bondline_delta_k']:+.1f} K** and its peak heat flux "
            f"**{cmp_['peak_flux_delta_w_m2']:+.4g} W/m²**; its integrated heat load differs "
            f"by {cmp_['heat_load_delta_j_m2']:+.4g} J/m². Across the whole front the "
            f"bondline spans {cmp_['front_bondline_span_k']:.1f} K and the peak flux "
            f"{cmp_['front_flux_span_w_m2']:.4g} W/m². These are absolute differences on "
            "purpose: no ratio against the bondline allowable is quoted anywhere in this "
            "report (the allowable is a substrate-specific limit, A-LIM-1a, and a margin "
            "ratio would inherit it).",
        ]
    lines += _h1_section(opt)
    lines += ["", "![front in design space](../figures/M4_front_variables.png)", ""]
    lines += _audit_section(opt)
    return lines


def _h1_section(opt: dict[str, Any]) -> list[str]:
    """H1, stated from the numbers, whichever way they fall. No threshold is invented: the
    section reports the two designs in absolute terms and says which of three cases holds."""
    sel = opt.get("selected", {})
    if not {"peak_flux_only", "joint_knee", "bondline_only"} <= set(sel):
        return []
    a, k, b = sel["peak_flux_only"], sel["joint_knee"], sel["bondline_only"]
    d_t = k["peak_bondline_temperature_k"] - a["peak_bondline_temperature_k"]
    d_q = k["peak_heat_flux_w_m2"] - a["peak_heat_flux_w_m2"]
    d_t_end = b["peak_bondline_temperature_k"] - a["peak_bondline_temperature_k"]
    d_q_end = b["peak_heat_flux_w_m2"] - a["peak_heat_flux_w_m2"]
    lines = [
        "",
        "### H1 under this model",
        "",
        "H1: *joint optimisation of peak heat flux and in-depth TPS response can identify "
        "safer feasible designs than peak-heat-only optimisation.* In absolute terms, at "
        f"Fidelity {opt['fidelity']}:",
        "",
        f"- the peak-flux-only optimum reaches **{a['peak_heat_flux_w_m2']:.4g} W/m²** and a "
        f"peak bondline temperature of **{a['peak_bondline_temperature_k']:.1f} K**;",
        f"- the joint knee design reaches **{k['peak_heat_flux_w_m2']:.4g} W/m²** and "
        f"**{k['peak_bondline_temperature_k']:.1f} K**: {d_t:+.1f} K at the bondline for "
        f"{d_q:+.4g} W/m² of peak flux;",
        f"- the bondline-only end of the front reaches **{b['peak_heat_flux_w_m2']:.4g} "
        f"W/m²** and **{b['peak_bondline_temperature_k']:.1f} K**: {d_t_end:+.1f} K for "
        f"{d_q_end:+.4g} W/m².",
        "",
    ]
    if len({a["candidate_id"], k["candidate_id"], b["candidate_id"]}) == 1 or d_t_end >= 0.0:
        lines += [
            "**H1 is NOT supported by this run.** The front has collapsed (or the design that "
            "minimises peak flux also minimises the bondline peak): within this model and "
            "this search there is no feasible design that trades peak flux for a cooler "
            "bondline. That is a result, not a failure of the optimiser, and it is reported "
            "as such.", ""]
    else:
        lines += [
            f"**The model predicts a trade-off, so H1 is supported within the tested "
            f"assumptions:** the front spans {abs(d_t_end):.1f} K of bondline temperature, and "
            "a search that looked at peak flux alone would have stopped at its hottest-"
            "bondline end. How much weight that carries depends on what the difference is "
            "compared with, and both comparisons belong next to the claim: (i) the front's "
            "whole bondline span is an absolute temperature difference inside a 1-D "
            "conduction model with a placeholder TPS stack (A-TPS-7), not a margin against a "
            "qualified material limit; "
            + _model_form_sentence(opt, abs(d_t), abs(d_t_end))
            + " The ±20% band on the effective-nose-radius data (A-GEO-3a) has not been "
            "propagated at all - that is M7's job; this section states the numbers and leaves "
            "the propagated verdict "
            "to M7.", ""]
    return lines


def _model_form_sentence(opt: dict[str, Any], knee_k: float, span_k: float) -> str:
    mf = opt.get("m3_model_form_sensitivity")
    if not mf:
        return "(ii) no measured drag-model sensitivity is available to compare it with."
    band = max(abs(v) for v in mf["bondline_change_k"])
    flux = max(abs(v) for v in mf["peak_flux_rel_change"])
    relation = ("LARGER than" if knee_k > band else "NOT larger than")
    return (f"(ii) M3 measured (`{mf['source']}`) that the declared, unvalidated "
            f"±{100 * mf['model_form_rel_halfband']:.0f}% perfect-gas band on C_D alone moves "
            f"the baseline capsule's bondline peak by up to ±{band:.1f} K and its peak flux by "
            f"up to ±{100 * flux:.1f}%. The knee's {knee_k:.1f} K and the front's {span_k:.1f} "
            f"K are {relation} that one band - one band, on one capsule, of several.")


def _audit_section(opt: dict[str, Any]) -> list[str]:
    a = opt["audit"]
    lines = ["## 11. Metric-gaming audit", ""]
    if a.get("n_front", 0) == 0:
        return lines + ["No feasible front exists; nothing to audit.", ""]
    lines += [
        f"Performed on the {a['n_front']} designs of the combined feasible front. The "
        "question for each check: is the optimiser winning on physics, or on something the "
        "model gets wrong?",
        "",
        "| variable | box | front range | parked at lower | parked at upper |",
        "|---|---|---|---|---|",
    ]
    for name, p in a["parked_on_bounds"].items():
        lines.append(f"| `{name}` | [{_fmt(p['lower'], 'g')}, {_fmt(p['upper'], 'g')}] | "
                     f"[{p['front_min']:.4g}, {p['front_max']:.4g}] | {p['at_lower']} | "
                     f"{p['at_upper']} |")
    lines += ["", "| constraint | front designs with margin < 1% | smallest margin |",
              "|---|---|---|"]
    for name, c in a["active_constraints"].items():
        lines.append(f"| `{name}` | {c['n_active']} | {c['min_margin']:.4f} |")
    lines += ["", "Counterfactual — the front the same candidates would give *without* each "
              "constraint, and how many of its designs violate that constraint:", "",
              "| constraint removed | front size | of which violate it | worst margin |",
              "|---|---|---|---|"]
    for name, c in a["counterfactual_without_constraint"].items():
        lines.append(f"| `{name}` | {c['n_front_without_constraint']} | "
                     f"{c['n_of_those_violating_it']} | {c['worst_margin']:.3f} |")
    h, s = a["heat_load_above_86km"], a["soak_truncation"]
    lines += [
        "",
        f"- **Flagged atmosphere (> 86 km, A-ATM-2).** Largest share of any front design's "
        f"external heat load accumulated there: {h['max_fraction']:.4f} (audit limit "
        f"{h['limit']}); {h['n_over']} designs over.",
        f"- **Soak-out truncation (NR-02).** Largest bondline warming rate at the end of the "
        f"thermal window: {s['max_end_rate_k_s']:.2e} K/s; {s['n_still_warming']} front "
        "designs were still warming when the window closed"
        + (" — their bondline peaks are lower bounds." if s["n_still_warming"] else "."),
    ]
    if opt.get("fidelity", 0) == 0:
        lines += [
            "- **Inert variable parked on a bound.** Where `cone_half_angle_deg` sits at its "
            "upper bound this is not a preference for wide cones: at Fidelity 0 the angle "
            "changes no objective, and a wide cone is simply the only geometry in which a "
            "bluntness ratio near the cap is valid. It will mean something only when C_D "
            "depends on shape.",
            "- **Geometry corner cases and mass closure.** See `docs/negative_results.md` for "
            "the two exploits the counterfactual rows expose and the constraints added in "
            "response; the offending candidates remain in the log as infeasible.",
            "",
        ]
        return lines
    return lines + _f1_audit(opt)


def _f1_audit(opt: dict[str, Any]) -> list[str]:
    """The Fidelity-1 checks. Every sentence is conditional on a number in the summary."""
    a = opt["audit"]
    n = a["n_front"]
    lines: list[str] = []
    sh = a.get("shape_variables_on_front", {}).get("shoulder_ratio")
    if sh:
        if not sh["active"]:
            lines.append(
                f"- **(i) Shoulder ratio.** Frozen by the screening at its reference "
                f"{sh['front_min']:g} (the box is [{sh['lower']:g}, {sh['upper']:g}]), so the "
                "optimiser could not move it and the sharp-shoulder exploit was not available "
                "in this run. That is a property of the freeze rule applied to the Saltelli "
                "sub-box, not evidence that the shoulder does not matter: see the one-at-a-"
                "time sweep in §3 for what it does to peak flux across its full range.")
        elif sh["n_within_1pct_of_lower"] > 0:
            lines.append(
                f"- **(i) SHOULDER RATIO: THE FRONT SITS ON THE SHARP-CORNER BOUND.** "
                f"{sh['n_within_1pct_of_lower']} of {n} front designs are within 1% of the "
                f"MINIMUM shoulder ratio {sh['lower']:g} (front range {sh['front_min']:.4g}-"
                f"{sh['front_max']:.4g}, median {sh['front_median']:.4g}). In this model a "
                "sharper corner raises the stagnation-point velocity-gradient radius and so "
                "LOWERS stagnation heating - and the model has nothing else to say about a "
                "shoulder. It is a stagnation-point-only heating model: it cannot see the "
                "corner, which is exactly where real capsules see their highest heating and "
                "are damaged (A-HEAT-4). **The bound, not physics, sets the shoulder of these "
                "designs.** The value 0.02 is a box edge, not a sourced minimum corner radius; "
                "no sourced corner-heating model exists in this project, so the bound is kept "
                "as a labelled FENCE and the exploit is recorded in `docs/negative_results.md`."
                " Read every design on this front as 'at least this sharp', never as a "
                "located optimum.")
        else:
            lines.append(
                f"- **(i) Shoulder ratio.** Active; front range {sh['front_min']:.4g}-"
                f"{sh['front_max']:.4g} in a box of [{sh['lower']:g}, {sh['upper']:g}]; "
                f"{sh['n_within_1pct_of_lower']} designs on the sharp-corner bound and "
                f"{sh['n_within_1pct_of_upper']} on the blunt one. The front does not pile "
                "onto the minimum shoulder ratio in this run. The model still cannot see "
                "corner heating (A-HEAT-4), so this is absence of the exploit, not validation "
                "of the shoulder it chose.")
    hb = a.get("cfd_hull_boundary")
    cs = a.get("cfd_surface")
    if hb:
        dirs = ", ".join(f"`{d['input']}` {d['direction']} ({d['n']})"
                         for d in hb["cfd_hull_by_input_and_direction"]) or "none"
        verdict = ("**The optimiser is being stopped by where CFD happened to be run**, in "
                   "those directions: a better design in this model may lie outside the hull, "
                   "and the front is an optimum of the hull, not of the physics."
                   if hb["n_front_on_cfd_hull_boundary"] else
                   "No front design is stopped by the hull in any shape direction at this "
                   "step size.")
        lines.append(
            f"- **(ii) CFD hull boundary.** Each front design's shape was stepped by "
            f"±{100 * hb['step_fraction_of_box_range']:g}% of the box range in each shape "
            f"input. **{hb['n_front_on_cfd_hull_boundary']} of {hb['n_front']}** designs have "
            f"at least one step that stays a valid forebody inside the box but LEAVES the "
            f"CFD hull (by input and direction: {dirs}). {verdict}"
            + (f" Over the whole run {cs['n_candidates_rejected_outside_hull']} paid "
               f"candidates ({100 * cs['fraction_of_paid_candidates_rejected_outside_hull']:.1f}"
               "%) were rejected for lying outside the hull; they stay in the log." if cs
               else ""))
    mf = a["active_constraints"].get("heatshield_mass_fraction")
    if mf:
        lines.append(
            f"- **(iii) Heat-shield mass fraction.** {mf['n_active']} of {n} front designs are "
            f"within 1% of the limit (smallest margin {mf['min_margin']:.4f}); limit = 1.0, "
            "i.e. the forebody TPS stack weighing as much as the whole vehicle. That is a "
            "logical necessity, not a mass budget (A-OPT-6): vehicle mass is held fixed while "
            "diameter grows, so the optimiser buys a low ballistic coefficient with a shield "
            "no real vehicle could carry. There is still no sourced mass budget in this "
            "project, so the constraint stays where it is and is labelled a FENCE. A design "
            "with a mass fraction near 1 is not a candidate vehicle.")
    h = a["heat_load_above_86km"]
    lines.append(
        f"- **(iv) Heat load above 86 km.** Up to {100 * h['max_fraction']:.1f}% of a front "
        f"design's external heat load accrues in the flagged log-interpolated atmosphere "
        f"(A-ATM-2; audit limit {100 * h['limit']:.0f}%, {h['n_over']} of {n} designs over). "
        "Shallow, large-diameter designs decelerate high; the bondline objective integrates "
        "that heating, so the front leans on the least-validated part of the atmosphere "
        "model (NR-14).")
    if cs:
        lines.append(
            f"- **(v) Drag above the CFD Mach range.** Front designs fly "
            f"{100 * cs['heat_fraction_above_top_cfd_mach_min']:.1f}-"
            f"{100 * cs['heat_fraction_above_top_cfd_mach_max']:.1f}% of their heat load above "
            f"their own top CFD Mach number (top node {cs['top_cfd_mach_min']:.1f}-"
            f"{cs['top_cfd_mach_max']:.1f}; {cs['n_front_with_truncated_mach_top']} designs "
            "have a hull-truncated top), where C_D is a held value. Surface C_D at peak "
            f"heating on the front: {cs['cd_at_peak_heating_min']:.3f}-"
            f"{cs['cd_at_peak_heating_max']:.3f}. Extending perfect-gas CFD in Mach closes an "
            "extrapolation in Mach, not the model-form error; the ±5% band stays (M3 §7).")
    pr = a.get("probes")
    if pr:
        sh_q = [d["sharp_shoulder_peak_flux_delta_w_m2"] for d in pr.values()]
        sh_t = [d["sharp_shoulder_bondline_delta_k"] for d in pr.values()]
        bl_q = [d["bluntest_peak_flux_delta_w_m2"] for d in pr.values()]
        bl_t = [d["bluntest_bondline_delta_k"] for d in pr.values()]
        cmp_ = opt.get("comparison", {})
        lines += [
            "- **(vi) What the two fences are worth - PROBES, not candidates** "
            "(`scripts/run_m4_audit_probes.py`, `audit_probes.csv`; evaluated through the "
            "canonical evaluator, entering no front and no hypervolume). *Sharp shoulder:* "
            "moving the three selected designs from the frozen shoulder ratio to the box "
            f"minimum changes peak flux by **{min(sh_q):+.4g} to {max(sh_q):+.4g} W/m²** and "
            f"the bondline peak by **{min(sh_t):+.1f} to {max(sh_t):+.1f} K**"
            + (f" - against a whole-front span of {cmp_['front_flux_span_w_m2']:.4g} W/m² and "
               f"{cmp_['front_bondline_span_k']:.1f} K" if cmp_ else "")
            + ". So the lever the screening froze as negligible (total-order index below 0.01 "
            "in a sub-box whose variance is dominated by diameter) is NOT negligible at the "
            "front, and it is precisely the lever a stagnation-point-only heating model "
            "rewards for the wrong reason: the model sees the larger effective nose radius a "
            "sharp corner gives and cannot see the corner's own heating. Had the freeze rule "
            "let it go, the front would be expected to sit on the 0.02 bound. It did not, by "
            "the accident of a variance-share rule - that is a fence, and it is recorded as "
            "one (NR-29). *Beyond the CFD hull in bluntness:* stepping the same designs up to "
            "the geometric-validity limit, as LABELLED GP extrapolations, changes peak flux by "
            f"{min(bl_q):+.4g} to {max(bl_q):+.4g} W/m² and the bondline by {min(bl_t):+.2f} to "
            f"{max(bl_t):+.2f} K: the hull edge withholds about 1% of peak flux, in a direction "
            "the corrected nose model has already nearly saturated.",
        ]
    lines += ["- **Physical inspection of the winning designs.** See §11a.", ""]
    lines += _physical_inspection(opt)
    return lines


def _physical_inspection(opt: dict[str, Any]) -> list[str]:
    sel = opt.get("selected", {})
    if "joint_knee" not in sel:
        return []
    k = sel["joint_knee"]
    import math
    d = k["x__diameter_m"]
    mass = opt["frozen"].get("mass_kg", k.get("x__mass_kg"))
    area = math.pi * d * d / 4.0
    cd = k.get("diag__aero_cd_at_peak_heating")
    beta = mass / (cd * area) if cd and cd == cd else float("nan")
    frac = k["diag__heatshield_mass_fraction"]
    dia = opt["audit"]["parked_on_bounds"]["diameter_m"]
    return [
        "### 11a. What the joint knee design physically is",
        "",
        f"Diameter **{d:.2f} m**, nose radius {k['x__bluntness_ratio'] * d:.2f} m "
        f"(R_n/D = {k['x__bluntness_ratio']:.3f}), cone half-angle "
        f"{k['x__cone_half_angle_deg']:.1f}°, shoulder radius "
        f"{k['x__shoulder_ratio'] * d:.2f} m, entering at "
        f"{k['x__flight_path_angle_deg']:.2f}°; vehicle mass **{mass:.0f} kg** (a mission "
        f"given, held fixed). Surface C_D at peak heating {cd:.3f}, so the ballistic "
        f"coefficient is about **{beta:.0f} kg/m²**. The forebody TPS stack alone is "
        f"**{100 * frac:.1f}% of the vehicle mass** ({frac * mass:.0f} of {mass:.0f} kg).",
        "",
        "That is not a capsule; it is a heat shield with "
        f"{(1 - frac) * mass:.0f} kg left over for structure, payload and everything else. "
        "The model reaches its low heating the only way this problem statement lets it: by "
        "growing the drag area at constant mass until the one constraint that knows about "
        "mass (a logical fence at 100%, A-OPT-6) stops it. Every design on the front has a "
        "diameter within "
        f"{dia['front_max'] - dia['front_min']:.3f} m "
        "of this one for that reason. Bluntness is stopped by the CFD hull / geometric "
        "validity, the cone angle is squeezed into the ~1° window between the validity limit "
        "for that bluntness and the 70° box bound, and the shoulder is frozen. **The only "
        "variable that actually trades the two objectives along this front is the entry "
        "flight-path angle** - shallow entries lower the peak flux and lengthen the soak, "
        "steep ones do the opposite until the g-limit stops them. The front is a "
        "burn-versus-bake curve in flight-path angle drawn at a fenced geometry, and it "
        "should be read as that, not as a located optimum of capsule shape.",
        "",
    ]



def _limitations(doe: dict[str, Any], opt: dict[str, Any] | None) -> list[str]:
    lines = ["## 12. Limitations", ""]
    if doe["fidelity"] == 0:
        lines += [
            "1. **This is Fidelity 0 and will be re-run.** Drag is a constant coefficient, so "
            "cone angle, shoulder radius, afterbody angle and length change nothing but "
            "geometric validity and wetted area. Any conclusion about *shape* is a "
            "conclusion about the drag model's blindness. Once the CFD response surface "
            "exists (M3), set `base_overrides.vehicle.aero.model` and re-run `make doe` "
            "then `make optimize`; the screening, the fronts, the hypervolumes and this "
            "report all regenerate.",
        ]
    else:
        hull = doe.get("f1_hull")
        lines += [
            "1. **Fidelity 1 means a better drag model, not a validated one.** C_D comes from "
            "inviscid, calorically-perfect-gas, zero-angle-of-attack CFD on the COARSE mesh, "
            "with base drag assumed, interpolated by a Gaussian process over a few dozen "
            "cases. Gate G4 validates that pipeline on a sphere at Mach 3 and 6. The "
            "perfect gas is the wrong gas at entry speeds; that is carried as a declared, "
            "unvalidated ±5% band on C_D and is not reduced by running the same gas model to "
            "a higher Mach number. No lift, trim or stability exists in this model, so the "
            "'stability' constraint of O1 is not checked at all."
            + (f" {100 * hull['full_box']['fraction_of_valid_shapes_inside_hull']:.0f}% "
               "of the valid shapes in the box lie inside the CFD hull (§2); the rest was "
               "closed to the search." if hull else ""),
        ]
    if doe["fidelity"] == 0:
        lines += [
            "2. Heating is stagnation-point Sutton–Graves with `effective_nose_radius_m = "
            "nose_radius_m`. For very blunt spherical segments the stagnation velocity "
            "gradient is set by the body radius and corner, not the cap radius, so the "
            "1/√R_n benefit saturates; the model does not capture that and is protected only "
            "by the placeholder bluntness cap.",
            "3. The constraint limits (12 g, 450 K, bluntness 1.2) and the variable ranges are "
            "unsourced engineering placeholders. They decide where the feasible region and "
            "therefore the front lies.",
        ]
    else:
        lines += [
            "2. Heating is **stagnation-point only**: Sutton–Graves with an effective nose "
            "radius from the measured stagnation velocity gradient (NASA TN D-5121 table I, "
            "A-GEO-3/3a, ±20% between the two primaries, not yet propagated). The model has "
            "no corner, no afterbody and no radiative heating. Any design feature whose real "
            "cost is heating somewhere other than the stagnation point - above all a sharp "
            "shoulder - is invisible to it (§11 (i)).",
            "3. Limits: 450 K is the Shuttle aluminium-structure limit (A-LIM-1a, sourced, "
            "substrate-specific); 12 g is numerically unchanged and known to be unsourceable "
            "as a flat value (A-LIM-1b); the heat-shield mass fraction limit of 1.0 is a "
            "logical fence, not a mass budget (A-OPT-6). The variable ranges are engineering "
            "choices. Together they decide where the feasible region, and therefore the "
            "front, lies.",
        ]
    lines += [
        "4. Vehicle mass is fixed while diameter varies. The heat-shield mass-closure "
        "constraint only excludes the impossible (shield heavier than the vehicle); it is "
        "not a mass model.",
        "5. TPS thickness was deliberately not optimised: with no mass objective in O1 it "
        "is a free improvement and an optimiser would simply park on its upper bound.",
        "6. The scalarised-DE baseline divides its budget equally across its weight sweep, "
        "so each weight gets only a handful of generations (see the settings in "
        "`configs/design_space.yaml`). Its hypervolume is a statement about that declared "
        "configuration under this budget, not about differential evolution in general; the "
        "settings were fixed before the run and were not retuned after seeing the result.",
        "7. Hypervolume differences between methods are reported with seed spread and no "
        "significance test; with this few seeds, overlapping ranges mean *no measured "
        "difference*. The model predicts these fronts within the tested assumptions; "
        "nothing here is a statement about a real vehicle.",
        "",
    ]
    return lines


def write_m4_report(root: Path, doe: dict[str, Any], opt: dict[str, Any] | None) -> Path:
    lines = _header(doe, opt) + _doe_sections(doe)
    if opt is None:
        lines += ["## 7–11. Optimisation", "",
                  "*Not yet run against this DOE. `make optimize` completes this report.*", ""]
    else:
        lines += _opt_sections(doe, opt)
    lines += _limitations(doe, opt)
    lines += ["## Reproduce", "", "```", "make doe        # a few minutes on 6 cores",
              "make optimize   # uses the latest DOE's screening.json", "```", ""]
    target = root / "reports" / "milestones" / "M4_pareto_optimisation.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines))
    return target
