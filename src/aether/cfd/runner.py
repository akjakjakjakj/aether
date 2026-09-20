"""Thin, logged wrapper around the OpenFOAM command line.

The native macOS build is entered through the ``openfoam -c '<command>'`` launcher. Every
call is logged to ``log.<name>`` inside the case, timed, run with stdin closed and given a
hard timeout - a crashed solver must produce a failed step, never a hung pipeline.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

LAUNCHER = "openfoam"


def openfoam_available() -> bool:
    return shutil.which(LAUNCHER) is not None


def openfoam_version() -> str:
    """Exact version string of the installed build, e.g. 'v2512'. 'ABSENT' if not found."""
    if not openfoam_available():
        return "ABSENT"
    out = subprocess.run([LAUNCHER, "-c", "echo $WM_PROJECT_VERSION"], capture_output=True,
                         text=True, stdin=subprocess.DEVNULL, timeout=60)
    return out.stdout.strip() or "UNKNOWN"


@dataclass(frozen=True)
class StepResult:
    name: str
    command: str
    returncode: int
    wall_time_s: float
    timed_out: bool

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict:
        return asdict(self)


def run_foam(case_dir: Path, name: str, command: str, timeout_s: float = 3600.0) -> StepResult:
    """Run one OpenFOAM command inside ``case_dir``, logging to ``log.<name>``."""
    case_dir = Path(case_dir)
    shell_cmd = f"cd {shlex.quote(str(case_dir))} && {command}"
    t0 = time.perf_counter()
    timed_out = False
    with open(case_dir / f"log.{name}", "w") as log:
        try:
            proc = subprocess.run([LAUNCHER, "-c", shell_cmd], stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT, timeout=timeout_s)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc, timed_out = -9, True
    return StepResult(name, command, rc, time.perf_counter() - t0, timed_out)


def set_patch_type(case_dir: Path, patch: str, new_type: str) -> None:
    """Rewrite one patch's type in constant/polyMesh/boundary.

    extrudeMesh leaves the collapsed axis patch as a zero-face 'patch'; OpenFOAM's
    convention for an axisymmetric case is type 'empty'.
    """
    path = Path(case_dir) / "constant" / "polyMesh" / "boundary"
    text = path.read_text()
    new, n = re.subn(rf"(\b{re.escape(patch)}\s*\{{\s*type\s+)\w+;", rf"\g<1>{new_type};", text)
    if n != 1:
        raise RuntimeError(f"patch {patch!r} not found exactly once in {path}")
    path.write_text(new)


def parse_check_mesh(log_text: str) -> dict:
    """Pull the quality numbers and the verdict out of a checkMesh log."""
    def grab(pattern: str) -> float | None:
        m = re.search(pattern, log_text)
        return float(m.group(1)) if m else None

    failed = re.search(r"Failed (\d+) mesh checks", log_text)
    return {
        "mesh_ok": "Mesh OK." in log_text,
        "n_failed_checks": int(failed.group(1)) if failed else 0,
        "n_cells": grab(r"(?m)^\s*cells:\s+(\d+)"),
        "max_non_orthogonality_deg": grab(r"Mesh non-orthogonality Max:\s*([\d.eE+-]+)"),
        "avg_non_orthogonality_deg": grab(r"non-orthogonality Max:\s*[\d.eE+-]+\s*average:\s*"
                                          r"([\d.eE+-]+)"),
        "n_severely_non_orthogonal_faces": grab(r"severely non-orthogonal[^\n]*faces:\s*(\d+)"),
        "max_skewness": grab(r"Max skewness = ([\d.eE+-]+)"),
        "max_aspect_ratio": grab(r"Max aspect ratio = ([\d.eE+-]+)"),
    }
