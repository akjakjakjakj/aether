#!/usr/bin/env python3
"""How much of each method's final hypervolume is bought within a hair of a constraint?
Recompute per-seed hypervolume from the persisted candidates after DROPPING every feasible
design whose smallest constraint margin is below a threshold. Read-only; uses the project's
own hypervolume function and the run's config snapshot. Writes audit/fence_counterfactual.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, yaml
RUN = Path(__file__).resolve().parents[1]; ROOT = RUN.parents[2]
sys.path.insert(0, str(ROOT))
from src.aether.optimization.pareto import normalised_hypervolume  # noqa: E402
snap = yaml.safe_load((RUN / "config_snapshot.yaml").read_text())["config"]["study"]
obj = list(snap["objectives"]); hv = snap["optimize"]["hypervolume"]
ideal = np.array([float(hv["ideal_point"][n]) for n in obj]); ref = np.array([float(hv["reference_point"][n]) for n in obj])
f = pd.read_csv(RUN / "candidates.csv"); f = f[(~f.cache_hit.astype(bool)) & f.feasible.astype(bool)]
margins = [c for c in f.columns if c.startswith("margin__")]
f["min_margin"] = f[margins].min(axis=1, skipna=True)
out = {}
for thr in (0.0, 1e-4, 1e-3, 1e-2):
    for method, sub in f.groupby("method"):
        vals = []
        for seed, s in sub.groupby("seed"):
            s = s[s.min_margin >= thr]
            vals.append(normalised_hypervolume(s[obj].to_numpy(float), ideal, ref) if len(s) else 0.0)
        out.setdefault(method, {})[f"min_margin>={thr:g}"] = {"hv_mean": float(np.mean(vals)), "per_seed": [round(v, 6) for v in vals]}
(RUN / "audit" / "fence_counterfactual.json").write_text(json.dumps(out, indent=1))
for m, d in out.items():
    print(m, {k: round(v["hv_mean"], 4) for k, v in d.items()})
