"""Study guards shared by every long-running study runner (M5 ablation, M6 adaptive fidelity).

Conceptual anchor
-----------------
A matched-budget comparison is one experiment only if one evaluator, on one design space,
produced every row of it. Two things broke that once (NR-18) and are now refused by code:

  source guard     the evaluator's SOURCE changed while the study ran. Worker processes import
                   the package when they are spawned, so an edit during a long run silently
                   splits the candidate log between two physics models. `SourceGuard` hashes
                   `src/aether` at launch and re-checks on demand; on a mismatch it writes
                   `ABORTED.md` into the run directory and raises `SourceChanged`.
  screening guard  the DOE screening the active-variable list comes from was made on a
                   different design space or base config. `screening_is_current` lists the
                   reasons; `load_current_screening` refuses to return a stale one.

`GuardedStore` is the candidate log both runners write through: one writer at a time (seeds
run in threads), and the source guard is re-checked after every logged batch - what was paid
for is on disk FIRST, then the run stops.

These lived in `ablation.py` / `scripts/run_ai_ablation.py` until M6 needed them too; both
import them from here now (`ablation.py` re-exports the old names).
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .persistence import CandidateStore


class SourceChanged(RuntimeError):
    """The evaluator's source tree changed while a study was running (NR-18)."""


class StaleScreening(RuntimeError):
    """The DOE screening does not apply to the design space the study would run on."""


def source_tree_hash(package_dir: Path, exclude: tuple[str, ...] = ()) -> str:
    """SHA-256 over every .py file under `package_dir` (relative path + bytes, sorted).
    `exclude` names top-level sub-packages left out - see `SourceGuard`.

    A study's candidates are only comparable if one evaluator produced all of them. Worker
    processes import the package when they are spawned, so an edit to the source during a
    long run silently splits the candidate log between two physics models. The runner
    records this hash at launch and refuses to continue when it changes.
    """
    digest = hashlib.sha256()
    for path in sorted(Path(package_dir).rglob("*.py")):
        if path.relative_to(package_dir).parts[0] in exclude:
            continue
        digest.update(str(path.relative_to(package_dir)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def screening_is_current(doe_snapshot: dict[str, Any], study: dict[str, Any],
                         base_config: dict[str, Any]) -> list[str]:
    """Reasons the DOE screening no longer applies to today's design space ([] == current).

    The active-variable list is only valid for the model and ranges it was screened on: a
    physics default that makes a frozen variable matter voids it.
    """
    reasons = []
    old = doe_snapshot["study"]
    for key in ("variables", "base_overrides", "objectives"):
        if old.get(key) != study.get(key):
            reasons.append(f"`{key}` in the design-space config differs from the DOE run's")
    if doe_snapshot["base"] != base_config:
        reasons.append("the base evaluator config (after overrides) differs from the DOE run's")
    return reasons


class SourceGuard:
    """Hash of `package_dir` at launch + a `check(where)` that aborts the run on a change.

    `exclude`: top-level sub-packages left out of the hash. Default none, and a STUDY uses
    none. It exists for smoke tests run while another work-stream is editing a sub-package
    the run never imports; `check` then also REFUSES to continue if any excluded sub-package
    has been imported into this process, so the exclusion cannot hide a real dependency.
    """

    def __init__(self, package_dir: Path, run_dir: Path, exclude: tuple[str, ...] = ()):
        self.package_dir, self.run_dir = Path(package_dir), Path(run_dir)
        self.exclude = tuple(exclude)
        self.hash_at_launch = source_tree_hash(self.package_dir, self.exclude)
        self._lock = threading.Lock()

    def check(self, where: str) -> None:
        import sys
        loaded = sorted(name for name in sys.modules for sub in self.exclude
                        if f".{self.package_dir.name}.{sub}" in f".{name}.")
        if loaded:
            raise SourceChanged(f"{where}: {loaded} were imported although excluded from the "
                                "source guard - the exclusion is not valid for this run")
        now = source_tree_hash(self.package_dir, self.exclude)
        if now == self.hash_at_launch:
            return
        message = (f"ABORTED {where}: {self.package_dir.name} changed while the study was "
                   f"running (hash {self.hash_at_launch} at launch, {now} now). Worker "
                   "processes may already hold either version, so this run's candidates are "
                   "not one experiment. Do not analyse this directory. See NR-18.")
        with self._lock:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            (self.run_dir / "ABORTED.md").write_text(
                "# ABORTED RUN - DO NOT ANALYSE\n\n" + message + "\n")
        raise SourceChanged(message)


class GuardedStore(CandidateStore):
    """Append-only candidate log with one writer at a time and an after-append hook."""

    def __init__(self, csv_path: str | Path):
        super().__init__(csv_path)
        self._lock = threading.Lock()
        self.after_append: Callable[[str], None] | None = None

    def append(self, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            super().append(rows)     # what was paid for is logged first, THEN the guard
        if self.after_append is not None:
            self.after_append("after a batch was logged")


def latest_run(results: Path, pattern: str, marker: str) -> Path:
    runs = sorted(p for p in Path(results).glob(pattern) if (p / marker).exists())
    if not runs:
        raise FileNotFoundError(f"no run matching {pattern} with a {marker} under {results}")
    return runs[-1]


def load_current_screening(doe_dir: Path, study: dict[str, Any],
                           base_config: dict[str, Any]) -> dict[str, Any]:
    """`screening.json` of `doe_dir`, or `StaleScreening` naming why it is void.

    The ONLY source of a study's active-variable list."""
    doe_dir = Path(doe_dir)
    screening = json.loads((doe_dir / "screening.json").read_text())
    snapshot = yaml.safe_load((doe_dir / "config_snapshot.yaml").read_text())["config"]
    stale = screening_is_current(snapshot, study, base_config)
    if stale:
        raise StaleScreening(
            f"REFUSING TO RUN: the screening of DOE run {doe_dir.name} is void for the "
            "current design space:\n  - " + "\n  - ".join(stale) + "\nThe active-variable "
            "list is a property of the model it was screened on. Re-run `make doe` (and "
            "`make optimize`) first, or pin a current DOE run with DOE_RUN=...")
    return screening
