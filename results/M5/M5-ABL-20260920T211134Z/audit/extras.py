#!/usr/bin/env python3
"""More audit numbers from persisted logs only: per-call no-physics share and numeric
prediction error of the agent; C_D at peak heating on each method's per-seed fronts; how
C_D moves with shape in the space-filling (lhs_search) data. Writes audit/extras.json."""
import json
from pathlib import Path
import numpy as np, pandas as pd
RUN = Path(__file__).resolve().parents[1]
OBJ = ["peak_heat_flux_w_m2", "peak_bondline_temperature_k"]
f = pd.read_csv(RUN / "candidates.csv"); f = f[~f["cache_hit"].astype(bool)]
logs = json.loads((RUN / "agent_log.json").read_text())
out = {}
for method, log in logs.items():
    rows = {(int(r.seed), r.candidate_id): r for r in f[f.method == method].itertuples(index=False)}
    per = {}
    for p in log["proposals"]:
        c = rows[(int(p["seed"]), p["candidate_id"])]
        d = per.setdefault(int(p["call"]), {"n": 0, "no_physics": 0, "infeasible_physics": 0,
                                            "feasible": 0, "q_err": [], "t_err": []})
        d["n"] += 1
        if c.status != "OK": d["no_physics"] += 1; continue
        d["feasible" if c.feasible else "infeasible_physics"] += 1
        d["q_err"].append(abs(p["expected_outcome"][OBJ[0]] - c.peak_heat_flux_w_m2) / c.peak_heat_flux_w_m2)
        d["t_err"].append(abs(p["expected_outcome"][OBJ[1]] - c.peak_bondline_temperature_k))
    out[method] = {"by_call": {str(k): {"n": v["n"], "no_physics": v["no_physics"],
        "infeasible_physics": v["infeasible_physics"], "feasible": v["feasible"],
        "median_abs_rel_err_flux": float(np.median(v["q_err"])) if v["q_err"] else None,
        "median_abs_err_bondline_k": float(np.median(v["t_err"])) if v["t_err"] else None}
        for k, v in sorted(per.items())}}
    out[method]["no_physics_by_seed_call"] = {}
    for p in log["proposals"]:
        c = rows[(int(p["seed"]), p["candidate_id"])]
        if c.status != "OK":
            key = f"seed {p['seed']} call {p['call']}"
            out[method]["no_physics_by_seed_call"][key] = out[method]["no_physics_by_seed_call"].get(key, 0) + 1
    out[method]["hv_by_round"] = {f"seed {r['seed']}": [] for r in log["rounds"]}
    for r in log["rounds"]:
        out[method]["hv_by_round"][f"seed {r['seed']}"].append(round(r.get("hv_after", float("nan")), 5))

def front(sub):
    v = sub[OBJ].to_numpy(float); keep = []
    for i in range(len(v)):
        if not np.any(np.all(v <= v[i], axis=1) & np.any(v < v[i], axis=1)): keep.append(i)
    return sub.iloc[keep]
fr = {}
for method, sub in f[f.feasible.astype(bool)].groupby("method"):
    fronts = pd.concat([front(s) for _, s in sub.groupby("seed")])
    fr[method] = {"n": int(len(fronts)),
                  "cd_at_peak_heating": [float(fronts.diag__aero_cd_at_peak_heating.min()), float(fronts.diag__aero_cd_at_peak_heating.max())],
                  **{n: [float(fronts[f"x__{n}"].min()), float(fronts[f"x__{n}"].max())] for n in
                     ("diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg")},
                  "min_margin_mass_fraction": float(fronts.margin__heatshield_mass_fraction.min()),
                  "min_margin_max_g": float(fronts.margin__max_g.min()),
                  "share_margin_mass_below_1e-3": float((fronts.margin__heatshield_mass_fraction < 1e-3).mean()),
                  "share_margin_mass_below_1e-4": float((fronts.margin__heatshield_mass_fraction < 1e-4).mean())}
out["per_seed_fronts_pooled"] = fr
lhs = f[(f.method == "lhs_search") & (f.status == "OK")]
out["lhs_cd_spearman"] = {n: float(lhs[[f"x__{n}", "diag__aero_cd_at_peak_heating"]].corr(method="spearman").iloc[0, 1])
                          for n in ("diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg")}
out["lhs_cd_range"] = [float(lhs.diag__aero_cd_at_peak_heating.min()), float(lhs.diag__aero_cd_at_peak_heating.max())]
out["failure_reasons_agent"] = (f[(f.method == "ai_agent") & (f.status != "OK")].failure_reason.str.slice(0, 60)
                                .str.replace(r"[-\d.]+", "#", regex=True).value_counts().to_dict())
(RUN / "audit" / "extras.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
