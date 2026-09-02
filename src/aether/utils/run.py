"""Run identity, config loading and immutable config snapshots.

Every result in this repository must be traceable to (a) a run ID, (b) the exact
config that produced it, and (c) the git commit of the code that ran.
"""

from __future__ import annotations

import hashlib
import json
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
