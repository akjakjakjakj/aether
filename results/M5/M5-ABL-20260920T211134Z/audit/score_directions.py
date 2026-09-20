#!/usr/bin/env python3
"""Quantitative half of the M5 qualitative audit. Reads ONLY persisted logs of this run
(agent_log.json, candidates.csv); evaluates nothing, calls no LLM, edits nothing outside
this directory. Writes direction_scores.json beside itself.

For every ACCEPTED proposal whose parent and child both returned physics:
  stated direction  = sign(expected_outcome[obj] - parent's simulated value)
  actual direction  = sign(child's simulated value - parent's simulated value)
A direction counts as "stated" only if the predicted change exceeds a dead band
(0.5 % of the parent's peak flux; 0.5 K of bondline temperature); inside it the agent is
read as predicting "about the same" and the proposal is not scored for that objective.

    .venv/bin/python results/M5/<run>/audit/score_directions.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
OBJ = ("peak_heat_flux_w_m2", "peak_bondline_temperature_k")
ACTIVE = ("diameter_m", "bluntness_ratio", "cone_half_angle_deg", "flight_path_angle_deg")


def dead_band(obj: str, parent_value: float) -> float:
    return 0.005 * abs(parent_value) if obj == OBJ[0] else 0.5


def main() -> None:
    logs = json.loads((RUN / "agent_log.json").read_text())
    frame = pd.read_csv(RUN / "candidates.csv")
    frame = frame[~frame["cache_hit"].astype(bool)]
    out: dict = {}
    for method, log in logs.items():
        rows = {(int(r.seed), r.candidate_id): r for r in
                frame[frame["method"] == method].itertuples(index=False)}
        per_obj = {o: Counter() for o in OBJ}
        per_round = defaultdict(lambda: {o: Counter() for o in OBJ})
        per_seed = defaultdict(lambda: {o: Counter() for o in OBJ})
        both = Counter()
        feas = Counter()
        child_status = Counter()
        changed = Counter()
        n_changed = Counter()
        fidelity = Counter()
        uncertainty = Counter()
        unc_both = defaultdict(Counter)
        improvement_claims = {o: Counter() for o in OBJ}
        for p in log["proposals"]:
            seed = int(p["seed"])
            child = rows.get((seed, p["candidate_id"]))
            parent = rows.get((seed, p["parent_id"]))
            if child is None or parent is None:
                child_status["not_in_log"] += 1
                continue
            for name in p["parameter_changes"]:
                pv = getattr(parent, f"x__{name}")
                if not np.isclose(pv, p["parameter_changes"][name], rtol=0, atol=1e-12):
                    changed[name] += 1
            n_changed[sum(not np.isclose(getattr(parent, f"x__{n}"), v, rtol=0, atol=1e-12)
                          for n, v in p["parameter_changes"].items())] += 1
            fidelity[int(p["requested_fidelity"])] += 1
            uncertainty[p["uncertainty"]] += 1
            ok_child, ok_parent = child.status == "OK", parent.status == "OK"
            child_status["physics" if ok_child else "no_physics"] += 1
            said = bool(p["expected_outcome"]["feasible"])
            feas[("said_feasible" if said else "said_infeasible") + "__"
                 + ("was_feasible" if bool(child.feasible) else
                    ("was_infeasible" if ok_child else "was_no_geometry"))] += 1
            if not (ok_child and ok_parent):
                continue
            verdicts = []
            for o in OBJ:
                pv, cv = float(getattr(parent, o)), float(getattr(child, o))
                ev = float(p["expected_outcome"][o])
                band = dead_band(o, pv)
                if abs(ev - pv) <= band:
                    per_obj[o]["no_direction_stated"] += 1
                    continue
                if abs(cv - pv) <= 1e-9 * max(abs(pv), 1.0):
                    per_obj[o]["actual_unchanged"] += 1
                    verdicts.append(False)
                    continue
                right = np.sign(ev - pv) == np.sign(cv - pv)
                key = "right" if right else "wrong"
                per_obj[o][key] += 1
                per_round[int(p["call"])][o][key] += 1
                per_seed[seed][o][key] += 1
                improvement_claims[o][("claimed_decrease" if ev < pv else "claimed_increase")
                                      + "__" + ("decreased" if cv < pv else "increased")] += 1
                verdicts.append(bool(right))
            if len(verdicts) == 2:
                k = "both_right" if all(verdicts) else ("one_right" if any(verdicts)
                                                        else "both_wrong")
                both[k] += 1
                unc_both[p["uncertainty"]][k] += 1

        def rate(c: Counter) -> float | None:
            n = c["right"] + c["wrong"] + c["actual_unchanged"]
            return c["right"] / n if n else None

        rej = Counter(r["reason"] for r in log["rejections"])
        out[method] = {
            "n_accepted_proposals": len(log["proposals"]),
            "n_rejected_proposals": len(log["rejections"]),
            "rejections_by_reason": dict(rej),
            "rejections_by_seed": dict(Counter(int(r["seed"]) for r in log["rejections"])),
            "round_outcomes": dict(Counter(r["outcome"] for r in log["rounds"])),
            "child_status": dict(child_status),
            "direction": {o: {**dict(per_obj[o]), "rate_right": rate(per_obj[o])} for o in OBJ},
            "direction_joint": {**dict(both),
                                "rate_both_right": (both["both_right"] / sum(both.values())
                                                    if sum(both.values()) else None)},
            "direction_joint_by_stated_uncertainty": {u: dict(c) for u, c in unc_both.items()},
            "direction_by_call": {str(k): {o: {**dict(v[o]), "rate_right": rate(v[o])}
                                           for o in OBJ} for k, v in sorted(per_round.items())},
            "direction_by_seed": {str(k): {o: {**dict(v[o]), "rate_right": rate(v[o])}
                                           for o in OBJ} for k, v in sorted(per_seed.items())},
            "claim_vs_actual": {o: dict(improvement_claims[o]) for o in OBJ},
            "feasibility_confusion": dict(feas),
            "variables_changed": dict(changed),
            "n_variables_changed_per_proposal": {str(k): v for k, v in sorted(n_changed.items())},
            "requested_fidelity": {str(k): v for k, v in fidelity.items()},
            "stated_uncertainty": dict(uncertainty),
        }

        # where the proposals went, call by call (medians over all seeds)
        traj = defaultdict(list)
        for p in log["proposals"]:
            traj[int(p["call"])].append([p["values"][n] for n in ACTIVE])
        out[method]["proposal_medians_by_call"] = {
            str(k): dict(zip(ACTIVE, np.median(np.array(v), axis=0).round(4).tolist(), strict=True))
            for k, v in sorted(traj.items())}
        out[method]["proposal_fpa_range_by_call"] = {
            str(k): [float(np.min(np.array(v)[:, 3])), float(np.max(np.array(v)[:, 3]))]
            for k, v in sorted(traj.items())}

    # C_D at peak heating on each method's pooled feasible set, and front variable ranges
    full = pd.read_csv(RUN / "candidates.csv")
    cd = {}
    for method, sub in full[full["feasible"].astype(bool)].groupby("method"):
        col = sub["diag__aero_cd_at_peak_heating"].astype(float)
        cd[method] = {"n_feasible": int(len(sub)), "cd_min": float(col.min()),
                      "cd_max": float(col.max()),
                      **{f"{n}_range": [float(sub[f'x__{n}'].min()), float(sub[f'x__{n}'].max())]
                         for n in ACTIVE}}
    out["feasible_set_by_method"] = cd
    (HERE / "direction_scores.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({m: {k: out[m][k] for k in ("direction", "direction_joint",
                                                  "feasibility_confusion",
                                                  "rejections_by_reason")}
                      for m in logs}, indent=1))


if __name__ == "__main__":
    main()
