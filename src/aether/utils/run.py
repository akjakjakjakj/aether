"""Run identity, config loading and immutable config snapshots.

Every result in this repository must be traceable to (a) a run ID, (b) the exact
config that produced it, and (c) the git commit of the code that ran.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "UNTRACKED"
    except Exception:
        return "UNKNOWN"


def _git_dirty() -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        return bool(out.stdout.strip())
    except Exception:
        return True


def config_hash(config: dict[str, Any]) -> str:
    """Stable 12-hex-char hash of a config dict. Two identical configs hash identically."""
    blob = json.dumps(config, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:12]


def new_run_id(prefix: str = "run") -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


@dataclass
class RunMeta:
    """Provenance record attached to every persisted result."""

    run_id: str
    config_hash: str
    git_commit: str = field(default_factory=_git_commit)
    git_dirty: bool = field(default_factory=_git_dirty)
    created_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    aether_version: str = "0.1.0"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config. Physical limits live here, never hard-coded in source."""
    with open(path) as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise TypeError(f"config {path} did not parse to a mapping")
    return cfg


def snapshot_config(config: dict[str, Any], out_dir: str | Path, meta: RunMeta) -> Path:
    """Write an immutable copy of the config plus its provenance beside the results."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "config_snapshot.yaml"
    payload = {"_meta": meta.to_dict(), "config": config}
    with open(target, "w") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False)
    return target


_CREATED = re.compile(r"^\s*created_utc:\s*'?([0-9T:+\-.]+)'?\s*$", flags=re.MULTILINE)


def run_window(run_dir: str | Path) -> tuple[datetime, datetime] | None:
    """(start, end) of a run, UTC, from what the run itself recorded.

    start = `_meta.created_utc` of its config snapshot (written once, at launch);
    end   = modification time of its append-only `candidates.csv`, i.e. the moment of its
            last evaluation. Report-only rebuilds rewrite `summary.json`, never that log.
    None if either record is missing. A file time is weaker evidence than a logged
    timestamp (copying a results tree resets it) - callers that publish a window should
    store it the first time it is computed and reuse the stored value afterwards.
    """
    run_dir = Path(run_dir)
    snap, log = run_dir / "config_snapshot.yaml", run_dir / "candidates.csv"
    if not (snap.exists() and log.exists()):
        return None
    with open(snap) as fh:
        match = _CREATED.search(fh.read(2000))
    if match is None:
        return None
    start = datetime.fromisoformat(match.group(1))
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return start, datetime.fromtimestamp(log.stat().st_mtime, tz=UTC)


def overlapping_runs(results_root: str | Path, run_dir: str | Path) -> dict[str, Any] | None:
    """Every other run under `results_root` whose recorded window overlaps `run_dir`'s.

    Used to caveat wall-time figures: a wall time measured while other studies held the
    machine is not a clean cost comparison. Reads timestamps only; evaluates nothing.
    """
    run_dir = Path(run_dir)
    mine = run_window(run_dir)
    if mine is None:
        return None
    others = []
    for snap in sorted(Path(results_root).glob("*/*/config_snapshot.yaml")):
        if snap.parent.resolve() == run_dir.resolve():
            continue
        window = run_window(snap.parent)
        if window is None or window[1] <= mine[0] or window[0] >= mine[1]:
            continue
        overlap = (min(window[1], mine[1]) - max(window[0], mine[0])).total_seconds()
        others.append({"run_id": snap.parent.name,
                       "start_utc": window[0].isoformat(timespec="seconds"),
                       "last_evaluation_utc": window[1].isoformat(timespec="seconds"),
                       "overlap_s": float(overlap),
                       "overlap_fraction_of_this_run":
                           float(overlap / max((mine[1] - mine[0]).total_seconds(), 1e-9))})
    return {"start_utc": mine[0].isoformat(timespec="seconds"),
            "last_evaluation_utc": mine[1].isoformat(timespec="seconds"),
            "basis": "config_snapshot.yaml _meta.created_utc -> candidates.csv mtime",
            "overlapping_runs": others}
