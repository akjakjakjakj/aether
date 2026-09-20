"""Candidate persistence: every evaluated design, feasible or not, written down once.

Spec sections 22 and 31: persist every candidate; never delete a failed one because it
looks bad. The store is an append-only CSV (so a run that dies half-way still leaves
every evaluation it paid for on disk) with a Parquet export for analysis. One row per
SUBMITTED candidate - including cache hits and refused geometries - carrying its run ID,
method, seed, generation, parent IDs, objectives, constraint margins and failure reason.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

# Fixed leading columns. Design variables, metrics, margins and diagnostics follow in the
# order the first row supplies them; the header is written once and then enforced.
ID_COLUMNS = (
    "run_id", "method", "seed", "fidelity", "eval_index", "budget_index", "generation",
    "candidate_id", "parent_ids", "cache_hit", "feasible", "failure_reason",
    "violated_constraints", "wall_time_s",
)
_JSON_COLUMNS = ("parent_ids", "violated_constraints")


class CandidateStore:
    """Append-only candidate log. Not safe for concurrent writers - the parent process of
    a run is the only writer; worker processes return rows, they never write."""

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._columns: list[str] | None = None
        if self.csv_path.exists() and self.csv_path.stat().st_size > 0:
            with open(self.csv_path, newline="") as fh:
                self._columns = next(csv.reader(fh))

    def append(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        if self._columns is None:
            extra = [k for k in rows[0] if k not in ID_COLUMNS]
            self._columns = [*ID_COLUMNS, *extra]
            with open(self.csv_path, "w", newline="") as fh:
                csv.writer(fh).writerow(self._columns)
        with open(self.csv_path, "a", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=self._columns, restval="")
            for row in rows:
                unknown = set(row) - set(self._columns)
                if unknown:
                    raise KeyError(f"candidate row has columns not in the store header: "
                                   f"{sorted(unknown)}")
                flat = dict(row)
                for key in _JSON_COLUMNS:
                    flat[key] = json.dumps(list(flat.get(key) or []))
                writer.writerow(flat)

    def load(self) -> pd.DataFrame:
        return load_candidates(self.csv_path)

    def export_parquet(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else self.csv_path.with_suffix(".parquet")
        frame = self.load()
        for key in _JSON_COLUMNS:  # Parquet wants a homogeneous column: keep the JSON text
            frame[key] = frame[key].map(json.dumps)
        frame.to_parquet(target, index=False)
        return target


def load_candidates(path: str | Path) -> pd.DataFrame:
    """Read a candidate log (CSV or Parquet) back with its list columns decoded."""
    path = Path(path)
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path)
    else:
        frame = pd.read_csv(path, keep_default_na=True,
                            dtype={"failure_reason": "string", "method": "string",
                                   "candidate_id": "string", "run_id": "string"})
    for key in _JSON_COLUMNS:
        frame[key] = frame[key].map(lambda s: json.loads(s) if isinstance(s, str) else [])
    frame["failure_reason"] = frame["failure_reason"].fillna("")
    for key in ("feasible", "cache_hit"):
        frame[key] = frame[key].astype(bool)
    return frame
