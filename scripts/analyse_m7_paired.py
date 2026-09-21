"""M7 post-hoc: is the joint knee's bondline advantage over the peak-flux-only design larger
than the propagated uncertainty ON THAT DIFFERENCE?

Reads ONLY result files of a finished `make uncertainty` run - `candidates.csv` and
`draws.csv` - and evaluates nothing. Every propagated design in one run shares one draw set
(same seed, same `x___uq_draw` index: common random numbers), so the per-draw difference

    delta_i = output(design_a, draw i) - output(design_b, draw i)

compares the two designs IN THE SAME WORLD. That tests the difference itself, instead of
asking whether two independently-read clouds overlap.

The draw set is NESTED (epistemic branches x shared aleatory draws), so the rows are not
independent: confidence intervals on the mean resample whole epistemic BRANCHES (cluster
bootstrap), never single rows.

    python scripts/analyse_m7_paired.py M7-UQ-<run id>

Writes results/M7/<run>/paired_difference.json and prints a summary. Nothing is tuned and
nothing here feeds back into any study.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [("joint_knee", "peak_flux_only"), ("bondline_only", "peak_flux_only"),
         ("bondline_only", "joint_knee")]
OUTPUTS = ["peak_bondline_temperature_k", "peak_heat_flux_w_m2"]
N_BOOT = 4000
BOOT_SEED = 20260926


def _series(frame: pd.DataFrame, label: str, output: str) -> pd.Series:
    rows = frame[frame["method"] == f"propagate:{label}"]
    s = rows.set_index(rows["x___uq_draw"].astype(int))[output].astype(float)
    if s.index.duplicated().any():
        raise SystemExit(f"{label}: duplicated draw indices - cannot pair")
    return s.sort_index()


def _pair(frame: pd.DataFrame, draws: pd.DataFrame, a: str, b: str, output: str) -> dict:
    sa, sb = _series(frame, a, output), _series(frame, b, output)
    if not sa.index.equals(sb.index):
        raise SystemExit(f"{a} and {b} do not share a draw set - not paired")
    ok = np.isfinite(sa.values) & np.isfinite(sb.values)
    delta = (sa - sb)[ok]
    branch = draws.set_index("draw_index").loc[delta.index, "epistemic_branch"].astype(int)

    by_branch = delta.groupby(branch.values)
    branch_mean = by_branch.mean()
    rng = np.random.default_rng(BOOT_SEED)
    ids = branch_mean.index.to_numpy()
    groups = {k: v.to_numpy() for k, v in by_branch}
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        pick = rng.choice(ids, size=len(ids), replace=True)
        boot[i] = np.concatenate([groups[k] for k in pick]).mean()

    sd_a, sd_b = float(sa[ok].std(ddof=1)), float(sb[ok].std(ddof=1))
    sd_delta = float(delta.std(ddof=1))
    n_neg, n = int((delta < 0).sum()), int(len(delta))
    return {
        "a": a, "b": b, "output": output, "n_pairs": n, "n_dropped_nonfinite": int((~ok).sum()),
        "delta_definition": f"{output}({a}) - {output}({b}), same draw",
        "mean": float(delta.mean()), "sd": sd_delta,
        "percentiles": {f"p{p:g}": float(np.percentile(delta, p)) for p in (1, 5, 50, 95, 99)},
        "min": float(delta.min()), "max": float(delta.max()),
        "n_draws_a_below_b": n_neg, "fraction_a_below_b": n_neg / n,
        "mean_ci95_cluster_bootstrap": [float(np.percentile(boot, 2.5)),
                                        float(np.percentile(boot, 97.5))],
        "epistemic_branches": {
            "n": int(len(branch_mean)),
            "branch_mean_min": float(branch_mean.min()),
            "branch_mean_max": float(branch_mean.max()),
            "n_branches_with_mean_below_zero": int((branch_mean < 0).sum()),
            "largest_within_branch_sd": float(by_branch.std(ddof=1).max()),
        },
        "for_contrast": {
            "sd_a": sd_a, "sd_b": sd_b,
            "sd_of_difference_if_clouds_were_independent": float(np.hypot(sd_a, sd_b)),
            "sd_of_difference_paired": sd_delta,
            "correlation_between_designs": float(np.corrcoef(sa[ok], sb[ok])[0, 1]),
            "abs_mean_over_paired_sd": abs(float(delta.mean())) / sd_delta if sd_delta else None,
        },
    }


def _violation_drivers(frame: pd.DataFrame, draws: pd.DataFrame, label: str) -> dict:
    """Which declared input separates violating from non-violating draws (description only)."""
    rows = frame[frame["method"] == f"propagate:{label}"].copy()
    rows["draw_index"] = rows["x___uq_draw"].astype(int)
    merged = rows.merge(draws, on="draw_index")
    out: dict = {}
    for constraint in ("heatshield_mass_fraction", "max_g"):
        hit = merged["violated_constraints"].fillna("").astype(str).str.contains(constraint)
        if hit.sum() == 0 or hit.sum() == len(merged):
            out[constraint] = {"n_violating": int(hit.sum()), "n": int(len(merged))}
            continue
        corr = {}
        for col in [c for c in merged.columns if c.startswith("u__")]:
            corr[col[3:]] = float(np.corrcoef(merged[col].astype(float), hit.astype(float))[0, 1])
        top = sorted(corr.items(), key=lambda kv: -abs(kv[1]))[:3]
        out[constraint] = {"n_violating": int(hit.sum()), "n": int(len(merged)),
                           "largest_point_biserial_correlations": dict(top)}
    if "diag__heatshield_mass_fraction" in merged:
        m = merged["diag__heatshield_mass_fraction"].astype(float)
        out["heatshield_mass_fraction_values"] = {
            "min": float(m.min()), "p50": float(m.median()), "max": float(m.max())}
    return out


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    run_dir = ROOT / "results" / "M7" / sys.argv[1]
    frame = pd.read_csv(run_dir / "candidates.csv", low_memory=False)
    draws = pd.read_csv(run_dir / "draws.csv")
    summary = json.loads((run_dir / "summary.json").read_text())

    result = {
        "run_id": sys.argv[1], "source_hash": summary.get("source_hash"),
        "method": "paired per-draw differences under common random numbers; "
                  f"cluster bootstrap over epistemic branches, {N_BOOT} resamples, "
                  f"seed {BOOT_SEED}",
        "pairs": [_pair(frame, draws, a, b, o) for a, b in PAIRS for o in OUTPUTS],
        "violation_drivers": {d: _violation_drivers(frame, draws, d)
                              for d in ("peak_flux_only", "joint_knee", "bondline_only")},
    }
    (run_dir / "paired_difference.json").write_text(json.dumps(result, indent=2))
    for p in result["pairs"]:
        c = p["for_contrast"]
        print(f"{p['a']} - {p['b']}  {p['output']}: mean {p['mean']:.4g}  sd {p['sd']:.4g}  "
              f"p5..p95 [{p['percentiles']['p5']:.4g}, {p['percentiles']['p95']:.4g}]  "
              f"range [{p['min']:.4g}, {p['max']:.4g}]  "
              f"a<b in {p['n_draws_a_below_b']}/{p['n_pairs']}  "
              f"(independent-cloud sd would be {c['sd_of_difference_if_clouds_were_independent']:.4g}, "
              f"rho {c['correlation_between_designs']:.4f})")
    print(json.dumps(result["violation_drivers"], indent=1))


if __name__ == "__main__":
    main()
