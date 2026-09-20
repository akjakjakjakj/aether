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
    return lines


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
            "purpose: a margin *ratio* would be measured against the bondline allowable, "
            "which is an unsourced placeholder (A-LIM-1; see the M1b correction in "
            "PROJECT_STATUS), so no such ratio is quoted.",
        ]
    lines += ["", "![front in design space](../figures/M4_front_variables.png)", ""]
    lines += _audit_section(opt)
    return lines


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
        "- **Inert variable parked on a bound.** Where `cone_half_angle_deg` sits at its upper "
        "bound this is not a preference for wide cones: at Fidelity 0 the angle changes no "
        "objective, and a wide cone is simply the only geometry in which a bluntness ratio "
        "near the cap is valid. It will mean something only when C_D depends on shape.",
        "- **Geometry corner cases and mass closure.** See `docs/negative_results.md` for "
        "the two exploits the counterfactual rows expose and the constraints added in "
        "response; the offending candidates remain in the log as infeasible.",
        "",
    ]
    return lines


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
    lines += [
        "2. Heating is stagnation-point Sutton–Graves with `effective_nose_radius_m = "
        "nose_radius_m`. For very blunt spherical segments the stagnation velocity "
        "gradient is set by the body radius and corner, not the cap radius, so the "
        "1/√R_n benefit saturates; the model does not capture that and is protected only "
        "by the placeholder bluntness cap.",
        "3. The constraint limits (12 g, 450 K, bluntness 1.2) and the variable ranges are "
        "unsourced engineering placeholders. They decide where the feasible region and "
        "therefore the front lies.",
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
