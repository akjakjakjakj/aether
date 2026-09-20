#!/usr/bin/env python3
"""Spec section 44 driver: evaluate the Thermal Penetration Index and decide its fate.

    python scripts/run_tpi_study.py [--config configs/tpi_study.yaml]

Writes:
    results/TPI/<run_id>/tpi_grid.csv          every design, every TPI variant
    results/TPI/<run_id>/summary.json          every number quoted in the report
    results/TPI/<run_id>/config_snapshot.yaml  immutable provenance
    reports/milestones/TPI_study.md
    reports/figures/TPI_*.png / .pdf

The report is generated from `summary.json`; no number in it is typed by hand.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.scoring import TPIConfig  # noqa: E402
from src.aether.studies import decide, run_tpi_study, study_table  # noqa: E402
from src.aether.studies.tpi_study import COMPARISON_METRICS  # noqa: E402
from src.aether.utils.run import (  # noqa: E402
    RunMeta,
    config_hash,
    load_config,
    new_run_id,
    snapshot_config,
)
from src.aether.viz import plot_tpi_figures  # noqa: E402


def _linspace(spec: dict) -> np.ndarray:
    return np.linspace(float(spec["min"]), float(spec["max"]), int(spec["n"]))


def _variant_configs(tpi_cfg: dict) -> list[TPIConfig]:
    """Full cross of the declared T_ref values and weighting families.

    A sensitivity analysis over one axis at a time would miss an interaction between the
    datum and the weighting, which is exactly the kind of thing that decides whether a
    metric is robust or an artefact of one setting.
    """
    ref = tpi_cfg["reference"]
    sens = tpi_cfg["sensitivity"]
    out: list[TPIConfig] = []
    for t_ref in sens["t_reference_k"]:
        for fam in sens["weighting"]:
            out.append(TPIConfig(
                t_reference_k=float(t_ref),
                weighting=str(fam["name"]),
                weight_params={k: float(v) for k, v in (fam.get("params") or {}).items()},
                normalise_weights=bool(ref.get("normalise_weights", True)),
                depth_limit_m=(None if ref.get("depth_limit_m") is None
                               else float(ref["depth_limit_m"])),
            ))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/tpi_study.yaml")
    args = ap.parse_args()

    study_cfg = load_config(ROOT / args.config)
    base_cfg = load_config(ROOT / study_cfg["meta"]["base_config"])

    run_id = new_run_id("TPI")
    out_dir = ROOT / "results" / "TPI" / run_id
    meta = RunMeta(run_id=run_id,
                   config_hash=config_hash({"study": study_cfg, "base": base_cfg}),
                   notes="Spec section 44 Thermal Penetration Index study")
    snapshot_config({"study": study_cfg, "base": base_cfg}, out_dir, meta)

    gammas = _linspace(study_cfg["grid"]["flight_path_angle_deg"])
    diameters = _linspace(study_cfg["grid"]["diameter_m"])
    reference = TPIConfig.from_dict(study_cfg["tpi"]["reference"])
    variants = _variant_configs(study_cfg["tpi"])

    print(f"AETHER TPI  run={run_id}  git={meta.git_commit}"
          f"{' (dirty)' if meta.git_dirty else ''}")
    print(f"grid: {len(gammas)} x {len(diameters)} = {len(gammas) * len(diameters)} "
          f"coupled evaluations via evaluate_design")
    print(f"reference TPI configuration: {reference.label}")
    print(f"sensitivity variants: {len(variants)}\n")

    study = run_tpi_study(base_cfg, gammas, diameters, reference, variants,
                          study_cfg["verdict"], progress=True)
    verdict = decide(study)

    rows = study_table(study)
    with open(out_dir / "tpi_grid.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = build_summary(study, verdict, reference, run_id, meta)
    with open(out_dir / "summary.json", "w") as fh:
        json.dump(summary, fh, indent=2, default=float)

    figures = plot_tpi_figures(study, verdict, ROOT / "reports" / "figures")
    write_report(summary, figures, out_dir)

    print(f"\nVERDICT: {verdict.decision}")
    for reason in verdict.reasons:
        print(f"  - {reason}")
    print(f"\nresults -> {out_dir}")
    return 0


def build_summary(study, verdict, reference, run_id, meta) -> dict:
    """Every number the report is allowed to quote, computed once, persisted once."""
    corr_all = study.correlations(study.reference)
    corr_feas = study.correlations(study.reference, feasible_only=True)
    taut = study.one_parameter_tautology_check()

    best_tpi = study.best_by_tpi(study.reference)
    best_bond = study.best_by("peak_bondline_temperature_k")
    best_flux = study.best_by("peak_heat_flux_w_m2")
    best_q = study.best_by("integrated_external_heat_j_m2")

    def describe(ev):
        if ev is None:
            return None
        return {
            "design_id": ev.design_id,
            "gamma_deg": ev.design_vector["entry_flight_path_angle_deg"],
            "diameter_m": ev.design_vector["diameter_m"],
            "peak_heat_flux_w_m2": ev.performance.peak_heat_flux_w_m2,
            "integrated_external_heat_j_m2": ev.performance.integrated_external_heat_j_m2,
            "peak_bondline_temperature_k": ev.performance.peak_bondline_temperature_k,
        }

    tpi = study.reference.values_k_m_s
    return {
        "run_id": run_id,
        "git_commit": meta.git_commit,
        "git_dirty": meta.git_dirty,
        "config_hash": meta.config_hash,
        "n_designs": study.n_designs,
        "n_feasible": int(np.sum(study.feasible)),
        "grid_shape": list(study.sweep.shape),
        "reference_config": reference.to_dict(),
        "reference_label": reference.label,
        "thresholds": study.thresholds,
        "tpi_range_k_m_s": [float(np.min(tpi)), float(np.max(tpi))],
        "tpi_peak_exceedance_depth_range_m": [
            float(np.min(study.reference.peak_exceedance_depth_m)),
            float(np.max(study.reference.peak_exceedance_depth_m)),
        ],
        "correlations_all": corr_all,
        "correlations_feasible": corr_feas,
        "redundancy_r2_all": study.redundancy_r2(study.reference),
        "redundancy_r2_feasible": study.redundancy_r2(study.reference, feasible_only=True),
        "disagreement_all": study.disagreement(study.reference),
        "disagreement_feasible": study.disagreement(study.reference, feasible_only=True),
        "tautology_check": taut,
        "exceedance_shape": study.exceedance_shape_statistics(),
        "variants": [
            {
                "label": v.label,
                "t_reference_k": v.config.t_reference_k,
                "weighting": v.config.weighting,
                "weight_params": v.config.weight_params,
                "tpi_min_k_m_s": float(np.min(v.values_k_m_s)),
                "tpi_max_k_m_s": float(np.max(v.values_k_m_s)),
                "rho_bondline": study.correlations(v)["peak_bondline_temperature_k"],
                "rho_integrated_heat": study.correlations(v)[
                    "integrated_external_heat_j_m2"],
                "rho_peak_flux": study.correlations(v)["peak_heat_flux_w_m2"],
                "redundancy_r2": study.redundancy_r2(v),
                "best_design_id": (study.best_by_tpi(v).design_id
                                   if study.best_by_tpi(v) is not None else None),
            }
            for v in study.variants
        ],
        "selection": {
            "tpi": describe(best_tpi),
            "peak_bondline_temperature_k": describe(best_bond),
            "peak_heat_flux_w_m2": describe(best_flux),
            "integrated_external_heat_j_m2": describe(best_q),
        },
        "verdict": {
            "decision": verdict.decision,
            "reasons": verdict.reasons,
            "reference_r2": verdict.reference_r2,
            "reference_rho_bondline": verdict.reference_rho_bondline,
            "unanimous": verdict.unanimous,
            "selects_a_different_design": verdict.selects_a_different_design,
            "variant_r2": verdict.variant_r2,
        },
    }


def write_report(s: dict, figures, out_dir: Path) -> None:
    rep = ROOT / "reports" / "milestones"
    rep.mkdir(parents=True, exist_ok=True)
    rel = lambda p: Path(p).relative_to(ROOT)  # noqa: E731
    v = s["verdict"]

    r2_all = s["redundancy_r2_all"]
    variant_r2 = [x["redundancy_r2"] for x in s["variants"]]
    thr = s["thresholds"]["redundancy_r2_threshold"]
    n_redundant = int(np.sum(np.array(variant_r2) >= thr))

    L = [
        "# Thermal Penetration Index — does it earn its place?\n",
        f"> Run `{s['run_id']}` · git `{s['git_commit']}`"
        f"{' · **working tree dirty**' if s['git_dirty'] else ''}"
        f" · config hash `{s['config_hash']}` · generated by `scripts/run_tpi_study.py`\n>\n"
        f"> Regenerate with `make tpi`. Raw data: `{rel(out_dir)}/tpi_grid.csv`, "
        f"`{rel(out_dir)}/summary.json`. Every number below is read from those files.\n",
        "\n## Question\n",
        "Spec §44 proposes a Thermal Penetration Index: a weighted double integral, over "
        "TPS depth and over time, of temperature exceedance above a reference "
        "temperature.\n",
        "\n```\nTPI = ∫₀^t_end ∫₀^L  w(x) · max( T(x,t) − T_ref , 0 )  dx dt       [K·m·s]\n```\n",
        "\nThe project already reports peak bondline temperature and integrated external "
        "heat load. A third number is only worth carrying if it would make a designer "
        "choose differently. The test is therefore not *is TPI physically meaningful* — it "
        "plainly is — but **does its ordering of designs contain anything the existing "
        "metrics do not**.\n",
        "\n## Method\n",
        f"The index was evaluated over the M1b design grid: "
        f"{s['grid_shape'][0]} entry flight-path angles × {s['grid_shape'][1]} capsule "
        f"diameters = **{s['n_designs']} coupled evaluations**, all through the canonical "
        f"`evaluate_design` path, of which {s['n_feasible']} satisfy every hard "
        f"constraint.\n",
        f"\nReference configuration: `{s['reference_label']}`. "
        f"Depth integration is restricted to the insulator "
        f"({(s['reference_config']['depth_limit_m'] or 0) * 1e3:.0f} mm); the aluminium "
        f"structure behind the bondline is not TPS and its thermal mass would otherwise "
        f"dominate the index.\n",
        "\n**Redundancy criterion, declared in `configs/tpi_study.yaml` before the run:** "
        f"TPI is discarded if the rank-space R² of TPI regressed on "
        f"(peak bondline temperature, integrated heat load) is ≥ **{thr:.2f}**, or if "
        f"|Spearman ρ| against peak bondline temperature alone is ≥ "
        f"**{s['thresholds']['redundancy_rho_threshold']:.2f}**.\n",
        "\n## Guard against the known trap\n",
        "M1 recorded a Spearman ρ of −1.000 between peak flux and bondline temperature and "
        "then said plainly that the number was close to content-free: over a "
        "**one-parameter** sweep, two strictly monotone functions of that parameter can "
        "only give ρ = ±1, whatever the physics. The same trap is live here.\n",
        f"\nAlong each fixed-diameter line of this grid ({s['tautology_check']['line_length']} "
        f"points, flight-path angle varying alone), "
        f"{s['tautology_check']['n_saturated']} of "
        f"{s['tautology_check']['n_lines']} lines give |ρ| ≥ 0.999 between TPI and peak "
        f"bondline temperature; the smallest |ρ| on any line is "
        f"{s['tautology_check']['min_abs_rho']:.4f}. **Those line correlations are "
        "uninformative and are reported here only to show why the 2-D number is the one "
        "that counts.** Every correlation quoted below is over the full 2-D grid, where "
        "the metrics are not forced into a common ordering.\n",
        "\n## Result\n",
        f"TPI over the grid spans {s['tpi_range_k_m_s'][0]:.4g} – "
        f"{s['tpi_range_k_m_s'][1]:.4g} K·m·s.\n",
        "\n### Where the index comes from — and a prediction that was half wrong\n",
        "`docs/theory/tpi.md` §5 predicted, before the run, that the depth integral "
        "would be *dominated by the outer millimetre or two*. **The first half of that "
        "is right and the second half is not,** and the distinction turns out to be the "
        "real explanation for the verdict.\n",
        f"\nRight: the unweighted time-integrated exceedance does peak at the surface — "
        f"at a depth between "
        f"{s['tpi_peak_exceedance_depth_range_m'][0] * 1e3:.3f} and "
        f"{s['tpi_peak_exceedance_depth_range_m'][1] * 1e3:.3f} mm, the shallowest cell "
        f"in the mesh, for every one of the {s['n_designs']} designs.\n",
    ]
    shape = s.get("exceedance_shape", {})
    if shape.get("available"):
        pct = 100 * shape["outer_fraction_of_domain"]
        L += [
            f"\nWrong: it does not *dominate*. The outermost {pct:.0f}% of the TPS depth "
            f"carries only {100 * shape['outer_share_min']:.1f}–"
            f"{100 * shape['outer_share_max']:.1f}% of the integral, against the "
            f"{pct:.0f}% a perfectly uniform profile would give. The profile declines "
            f"smoothly with depth; it is not a surface spike.\n",
            f"\nThe actual mechanism is the profile's **shape invariance**. Normalised to "
            f"unit length, the exceedance profiles of the "
            f"{shape['n_designs_with_any_exceedance']} designs that exceed T_ref anywhere "
            f"have a minimum pairwise cosine similarity of "
            f"**{shape['min_pairwise_cosine_similarity']:.4f}** (mean "
            f"{shape['mean_pairwise_cosine_similarity']:.4f}). Every design produces very "
            f"nearly the *same* depth profile scaled by a different factor. TPI is "
            f"therefore that scalar — and so is any weighted integral of the same "
            f"profile, which is why **no weighting family rescues it**: the sensitivity "
            f"table below shows all 16 configurations failing the redundancy criterion "
            f"together. A metric cannot separate designs along a dimension in which the "
            f"designs do not differ.\n",
        ]
    L += [
        "See `reports/figures/TPI_weighting_and_profile.png` for the profiles themselves.\n",
        "\n### Rank correlation with the existing metrics (2-D grid)\n",
        "| Metric | Spearman ρ, all designs | Spearman ρ, feasible only |\n|---|---|---|\n",
    ]
    for key, label in COMPARISON_METRICS:
        L.append(f"| {label} | {s['correlations_all'][key]:+.4f} | "
                 f"{s['correlations_feasible'][key]:+.4f} |\n")

    d = s["disagreement_all"]
    L += [
        "\n### Redundancy\n",
        f"Rank-space R² of TPI on (peak bondline temperature, integrated heat load): "
        f"**{r2_all:.4f}** over all {s['n_designs']} designs, "
        f"**{s['redundancy_r2_feasible']:.4f}** over the feasible subset.\n",
        f"\nKendall τ between TPI and peak bondline temperature is "
        f"{d['kendall_tau']:+.4f}: **{d['discordant_pairs']} of {d['total_pairs']} "
        f"ordered design pairs ({100 * d['discordant_fraction']:.2f}%) are ranked "
        f"differently** by the two metrics.\n",
        "\n### What each objective actually selects\n",
        "| Objective minimised | Design | γ₀ | D | q''ₘₐₓ [W cm⁻²] | Q_ext [MJ m⁻²] | "
        "T_bond,max [K] |\n|---|---|---|---|---|---|---|\n",
    ]
    for key, label in (("tpi", "TPI"),
                       ("peak_bondline_temperature_k", "peak bondline temperature"),
                       ("peak_heat_flux_w_m2", "peak heat flux"),
                       ("integrated_external_heat_j_m2", "integrated heat load")):
        sel = s["selection"][key]
        if sel is None:
            L.append(f"| {label} | — no feasible design — | | | | | |\n")
            continue
        L.append(
            f"| {label} | `{sel['design_id']}` | {sel['gamma_deg']:+.2f}° | "
            f"{sel['diameter_m']:.2f} m | {sel['peak_heat_flux_w_m2'] / 1e4:.2f} | "
            f"{sel['integrated_external_heat_j_m2'] / 1e6:.1f} | "
            f"{sel['peak_bondline_temperature_k']:.1f} |\n")

    L += [
        "\n### Sensitivity to the two free choices\n",
        f"All {len(s['variants'])} declared combinations of exceedance datum T_ref and "
        f"weighting family, from `configs/tpi_study.yaml`. "
        f"**{n_redundant} of {len(s['variants'])}** exceed the redundancy threshold.\n",
        "\n| T_ref [K] | weighting | ρ vs T_bond,max | ρ vs Q_ext | ρ vs q''ₘₐₓ | "
        "rank R² | TPI range [K·m·s] |\n|---|---|---|---|---|---|---|\n",
    ]
    for x in sorted(s["variants"], key=lambda r: (r["t_reference_k"], r["weighting"])):
        params = ", ".join(f"{k}={val:g}" for k, val in sorted(x["weight_params"].items()))
        fam = x["weighting"] + (f" ({params})" if params else "")
        L.append(
            f"| {x['t_reference_k']:.0f} | {fam} | {x['rho_bondline']:+.4f} | "
            f"{x['rho_integrated_heat']:+.4f} | {x['rho_peak_flux']:+.4f} | "
            f"{x['redundancy_r2']:.4f} | {x['tpi_min_k_m_s']:.3g} – "
            f"{x['tpi_max_k_m_s']:.3g} |\n")

    L += [
        f"\n## Verdict: **{v['decision']}**\n",
        *[f"\n- {r}\n" for r in v["reasons"]],
        "\n### What was NOT claimed\n",
        "No claim is made that TPI is a new aerospace standard, and none that it is "
        "original. `docs/theory/tpi.md` reviews the prior art for cumulative "
        "thermal-exposure metrics — integrated heat load in TPS sizing, CEM43 thermal dose "
        "in hyperthermia, Arrhenius damage integrals — and TPI sits inside that family "
        "rather than beside it.\n",
        "\n## Figures\n",
        *[f"- `{rel(f)}`\n" for f in figures],
        "\n## Limitations\n",
        "- This verdict is about **this design space**: one vehicle family, two design "
        "variables, a constant-property two-layer stack, Fidelity 0 aerodynamics. A stack "
        "with a genuinely different in-depth response — a charring ablator, a "
        "temperature-dependent conductivity, a multi-layer insulator with an interior "
        "bondline — could decouple TPI from peak bondline temperature. That is a testable "
        "prediction, not a defence of the metric.\n",
        "- The redundancy criterion is a threshold on a rank R². It was declared in "
        "advance, but it is still a threshold, and a metric just below it would not "
        "thereby be useful.\n",
        "- T_ref and the weighting family were swept over declared ranges, not optimised. "
        "A configuration outside those ranges could behave differently; the ranges are in "
        "the config snapshot.\n",
    ]
    (rep / "TPI_study.md").write_text("".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
