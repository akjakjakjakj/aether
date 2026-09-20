"""M7's run guards: the shared ones, plus the M4-staleness check M7 needs on top.

WHERE THESE LIVE
----------------
`SourceGuard`, `GuardedStore`, `source_tree_hash` and `screening_is_current` were factored
out of `ablation.py` into `optimization/guards.py` while M7 was being built, so M5, M6 and
M7 now run behind one implementation. This module imports them from there and adds nothing
to them.

What the shared ones are for
----------------------------
`SourceGuard`
    NR-18: worker processes import `src/aether` when they are spawned, so an edit to the
    physics DURING a long run silently splits the candidate log between two models. The
    runner records the hash at launch and refuses to continue when it moves, writing an
    `ABORTED.md` into the run directory so the half-run cannot be mistaken for a result.

`GuardedStore`
    The candidate log a study writes through: one writer at a time, and the source guard
    re-checked after every logged batch. The ORDER matters and is deliberate - what was
    paid for reaches disk first, and only then does the run stop.

`screening_is_current`
    The active-variable list is a property of the model it was screened on. M7 inherits
    M4's screening, so if the design space or the base physics config has changed since
    that DOE ran, the list is void and the run must stop.

What M7 adds
------------
`m4_front_is_current`
    M7 reads M4's SELECTED DESIGNS - the peak-flux-only and joint-knee points §39 compares
    against. Those are stored metrics from a run that may have been computed under
    different physics; ASSUMPTIONS A-OPT-5 records that the current M4 front was produced
    under the legacy `cap_radius` heating model behind a bluntness cap that has since been
    removed, and must be regenerated rather than reinterpreted. M7 must not quietly
    present those numbers as today's, so this returns the reasons they are stale and the
    report prints them above any table that quotes them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..optimization.guards import (
    GuardedStore as _SharedGuardedStore,
)
from ..optimization.guards import (
    SourceChanged,
    SourceGuard,
    screening_is_current,
    source_tree_hash,
)

__all__ = ["GuardedStore", "SourceChanged", "SourceGuard", "m4_front_is_current",
           "screening_is_current", "source_tree_hash", "stale_banner"]


class GuardedStore(_SharedGuardedStore):
    """The shared guarded store with its `SourceGuard` already wired to its run directory.

    M5 and M6 build the guard and the store separately and connect them in their runners;
    M7's two scripts each need exactly one of each, so they are assembled here instead of
    being reassembled identically in both scripts.
    """

    def __init__(self, csv_path: str | Path, package_dir: Path, out_dir: Path):
        super().__init__(csv_path)
        self.guard = SourceGuard(Path(package_dir), Path(out_dir))
        self.after_append = self.guard.check

    @property
    def launch_hash(self) -> str:
        return self.guard.hash_at_launch

    def check(self, where: str) -> None:
        self.guard.check(where)


def m4_front_is_current(m4_snapshot: dict[str, Any], study: dict[str, Any],
                        base_config: dict[str, Any]) -> list[str]:
    """Reasons an M4 optimisation run's stored designs no longer describe today's model.

    [] means the stored metrics and today's evaluator agree about what they are; it does
    NOT promise the numbers are bit-identical, which is why the comparison table
    re-evaluates every design anyway and prints both.
    """
    reasons = list(screening_is_current(m4_snapshot, study, base_config))
    old_geometry = (m4_snapshot.get("base", {}).get("vehicle", {}) or {}).get("geometry", {})
    new_geometry = (base_config.get("vehicle", {}) or {}).get("geometry", {})
    old_model = str(old_geometry.get("effective_nose_radius_model", "cap_radius"))
    new_model = str(new_geometry.get("effective_nose_radius_model", "cap_radius"))
    if old_model != new_model:
        reasons.append(
            f"the effective-nose-radius model was {old_model!r} when that front was "
            f"computed and is {new_model!r} now (A-GEO-3, NR-15)")
    old_limits = m4_snapshot.get("base", {}).get("limits", {}) or {}
    new_limits = base_config.get("limits", {}) or {}
    for key in sorted(set(old_limits) | set(new_limits)):
        if old_limits.get(key) != new_limits.get(key):
            reasons.append(f"limit '{key}' was {old_limits.get(key)!r} and is now "
                           f"{new_limits.get(key)!r}")
    return reasons


def stale_banner(reasons: list[str], run_id: str) -> str:
    """The warning a report prints above any table quoting a stale run's numbers."""
    if not reasons:
        return ""
    bullets = "\n".join(f"  - {r}" for r in reasons)
    return (f"STALE SOURCE: the stored designs of M4 run {run_id} were produced under a "
            f"different model from today's:\n{bullets}\n"
            "Their design VECTORS are still usable - a set of geometry and trajectory "
            "numbers is model-independent - so every design below is RE-EVALUATED under "
            "the current source and both values are shown. The stored metrics are "
            "reported for traceability and must not be quoted as current results. "
            "Regenerate with `make doe && make optimize` (ASSUMPTIONS A-OPT-5).")
