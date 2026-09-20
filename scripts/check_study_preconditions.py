#!/usr/bin/env python3
"""Would M5 / M6 / M7 start today? Runs ONLY the precondition checks their runners run.

Starts no study, evaluates no design, launches no OpenFOAM case and makes NO LLM call. It calls
the same guard functions the runners call, against the same configs and the latest DOE run:

  M5  make ablation      screening of the latest DOE is current for today's design space
  M6  make adaptive      mode: study; design space selects the required drag surface; screening
                         current; base surface built AND read under gate G4 = PASS; no
                         allow_provisional; F1 mesh level matches the surface
  M7  make robust /      screening current; every uncertainty input available for today's
      make uncertainty   evaluator (in particular the GCI discretisation term, which REFUSES
                         when M2's gci.csv is missing)

Exit status 0 only if all three would start. Prints the source-tree hash the study runners
would record at launch.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.aether.optimization.design_space import DesignSpace  # noqa: E402
from src.aether.optimization.guards import (  # noqa: E402
    StaleScreening,
    latest_run,
    load_current_screening,
    source_tree_hash,
)
from src.aether.utils.run import load_config  # noqa: E402


def main() -> int:
    study = load_config(ROOT / "configs" / "design_space.yaml")
    full = DesignSpace.from_config(study, ROOT)
    model = str(full.base_config["vehicle"].get("aero", {}).get("model", "constant"))
    doe_dir = latest_run(ROOT / "results" / "M4", "M4-DOE-*", "screening.json")
    results: dict[str, tuple[bool, str]] = {}

    try:
        screening = load_current_screening(doe_dir, study, full.base_config)
        screening_msg = (f"screening of {doe_dir.name} is current; active = "
                         f"{screening['active']}")
        screening_ok = True
    except StaleScreening as exc:
        screening, screening_ok, screening_msg = None, False, str(exc)

    results["M5 ablation"] = (screening_ok, screening_msg)

    # -- M6 --------------------------------------------------------------------------------
    try:
        from src.aether.optimization.adaptive import load_base_surface, require_f1_gate
        af = load_config(ROOT / "configs" / "adaptive_fidelity.yaml")["adaptive_fidelity"]
        problems = []
        if af["mode"] != "study":
            problems.append(f"mode is '{af['mode']}', not 'study'")
        if af["allow_provisional"]:
            problems.append("allow_provisional is true")
        if model != af["require_aero_model"]:
            problems.append(f"design space selects '{model}', M6 needs "
                            f"'{af['require_aero_model']}'")
        base = load_base_surface(ROOT / af["initial_surface"]["directory"])
        gate = require_f1_gate(base.meta, bool(af["allow_provisional"]))
        if gate["provisional"]:
            problems.append(f"base surface is provisional: {gate}")
        if af["f1"]["mesh_level"] not in ("from_surface", base.meta["mesh_level"]):
            problems.append("F1 mesh level differs from the surface's")
        if not screening_ok:
            problems.append("stale screening")
        results["M6 adaptive"] = (not problems, "; ".join(problems) or (
            f"surface {base.meta['model']} ({base.meta['training_hash']}), G4 at build "
            f"{gate['gate_G4_status_at_build']}, now {gate['gate_G4_status_now']}; "
            + screening_msg))
    except Exception as exc:  # noqa: BLE001 - a refusal of any kind is the answer here
        results["M6 adaptive"] = (False, f"{type(exc).__name__}: {exc}")

    # -- M7 --------------------------------------------------------------------------------
    try:
        from src.aether.uncertainty.inputs import UncertaintyModel
        built, _ = UncertaintyModel.load(ROOT / "configs" / "uncertainty.yaml",
                                         full.base_config)
        results["M7 robust / uncertainty"] = (screening_ok, (
            f"{len(built.names)} uncertain inputs active ({', '.join(built.names)}); skipped: "
            f"{[n for n, _ in built.skipped]}; " + screening_msg))
    except Exception as exc:  # noqa: BLE001
        results["M7 robust / uncertainty"] = (False, f"{type(exc).__name__}: {exc}")

    print(f"design space aero model: {model}")
    print(f"src/aether source-tree hash (what a study records at launch): "
          f"{source_tree_hash(ROOT / 'src' / 'aether')}")
    for name, (ok, msg) in results.items():
        print(f"[{'WOULD START' if ok else 'REFUSES'}] {name}: {msg}")
    return 0 if all(ok for ok, _ in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
