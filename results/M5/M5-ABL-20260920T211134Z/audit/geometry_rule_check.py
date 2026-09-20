#!/usr/bin/env python3
"""Does the validity rule the agent stated in its FIRST round (seeds 37, 41, 67:
(bluntness - 0.1) * cos(cone_half_angle) <= 0.4) agree with the evaluator on every design
logged in this run, all methods? Read-only."""
from pathlib import Path
import numpy as np, pandas as pd
RUN = Path(__file__).resolve().parents[1]
f = pd.read_csv(RUN / "candidates.csv"); f = f[~f.cache_hit.astype(bool)]
bad = f.failure_reason.fillna("").str.startswith("invalid geometry")
pred = (f.x__bluntness_ratio - 0.1) * np.cos(np.radians(f.x__cone_half_angle_deg)) > 0.4
print(f"paid designs {len(f)}, invalid geometry {int(bad.sum())}, rule agrees on "
      f"{int((pred == bad).sum())}, false alarms {int((pred & ~bad).sum())}, misses {int((~pred & bad).sum())}")
