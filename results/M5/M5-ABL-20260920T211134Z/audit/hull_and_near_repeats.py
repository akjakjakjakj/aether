#!/usr/bin/env python3
"""Two gaming checks the generated report does not make. Read-only, persisted logs only.
 (a) CFD-hull edge, per method: paid designs refused by the drag surface ('aero surface
     extrapolation'), and how close each method's per-seed fronts sit to the largest
     bluntness this run ever saw evaluated at cone >= 69.9 deg (an empirical hull edge).
 (b) near-repeats: per-seed hypervolume with every paid design lying within 1e-3 (unit
     cube) of an EARLIER paid design removed - what those evaluations bought.
Writes audit/hull_and_near_repeats.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, yaml
RUN = Path(__file__).resolve().parents[1]; ROOT = RUN.parents[2]
sys.path.insert(0, str(ROOT))
from src.aether.optimization.pareto import normalised_hypervolume  # noqa: E402
snap = yaml.safe_load((RUN / "config_snapshot.yaml").read_text())["config"]
study = snap["study"]; obj = list(study["objectives"]); hv = study["optimize"]["hypervolume"]
ideal = np.array([float(hv["ideal_point"][n]) for n in obj]); ref = np.array([float(hv["reference_point"][n]) for n in obj])
active = snap["screening"]["active"]
bounds = {v["name"]: (float(v["min"]), float(v["max"])) for v in study["variables"] if v["name"] in active} \
    if isinstance(study["variables"], list) else {n: (float(study["variables"][n]["min"]), float(study["variables"][n]["max"])) for n in active}
f = pd.read_csv(RUN / "candidates.csv"); f = f[~f.cache_hit.astype(bool)].copy()
f["reason"] = f.failure_reason.fillna("")
ok = f[f.status == "OK"]
edge = float(ok[ok.x__cone_half_angle_deg >= 69.9].x__bluntness_ratio.max())
refused_min = float(f[f.reason.str.startswith("aero surface") & (f.x__cone_half_angle_deg >= 69.9)].x__bluntness_ratio.min())
def front(s):
    v = s[obj].to_numpy(float)
    keep = [i for i in range(len(v)) if not np.any(np.all(v <= v[i], axis=1) & np.any(v < v[i], axis=1))]
    return s.iloc[keep]
out = {"largest_bluntness_evaluated_at_cone>=69.9": edge, "smallest_bluntness_refused_by_surface_at_cone>=69.9": refused_min, "methods": {}}
for method, sub in f.groupby("method"):
    fr = pd.concat([front(s[s.feasible.astype(bool)]) for _, s in sub.groupby("seed")])
    hv_all, hv_drop, n_near = [], [], 0
    for seed, s in sub.groupby("seed"):
        s = s.sort_values("budget_index")
        x = np.column_stack([(s[f"x__{n}"].to_numpy(float) - bounds[n][0]) / (bounds[n][1] - bounds[n][0]) for n in active])
        d = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=2); d[np.triu_indices(len(x))] = np.inf
        near = d.min(axis=1) < 1e-3; n_near += int(near.sum())
        fe = s.feasible.astype(bool).to_numpy()
        hv_all.append(normalised_hypervolume(s[fe][obj].to_numpy(float), ideal, ref) if fe.any() else 0.0)
        keep = fe & ~near
        hv_drop.append(normalised_hypervolume(s[keep][obj].to_numpy(float), ideal, ref) if keep.any() else 0.0)
    out["methods"][method] = {
        "paid": int(len(sub)),
        "refused_outside_cfd_hull": int(sub.reason.str.startswith("aero surface").sum()),
        "invalid_geometry": int(sub.reason.str.startswith("invalid geometry").sum()),
        "front_designs": int(len(fr)),
        "front_share_within_0.01_bluntness_of_edge": float((fr.x__bluntness_ratio >= edge - 0.01).mean()),
        "front_bluntness_max": float(fr.x__bluntness_ratio.max()),
        "near_repeats": n_near,
        "hv_mean": float(np.mean(hv_all)), "hv_mean_without_near_repeats": float(np.mean(hv_drop)),
    }
(RUN / "audit" / "hull_and_near_repeats.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
