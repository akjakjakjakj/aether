"""Design-space definition: the map between an optimiser's vector and an evaluator config.

Conceptual anchor
-----------------
An optimiser thinks in a box of numbers; `evaluate_design` thinks in a nested config.
This module is the only translator between the two, so a variable's range, role, units
and the config key it writes to are declared once (in `configs/design_space.yaml`) and
every DOE, sweep and optimiser sees the same thing.

Geometry is parametrised by SIZE (diameter) and SHAPE RATIOS (nose radius / D, shoulder
radius / D, length / D) rather than by four lengths. The ratios are what make a capsule
blunt or slender regardless of scale, and a box in ratio space contains far fewer
geometrically impossible capsules than a box in raw lengths does. The translation to the
raw `CapsuleGeometry` fields happens here; validity is still decided by
`CapsuleGeometry.validate()` inside the evaluator, never here.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from ..utils.run import REPO_ROOT, load_config

ROLES = ("design", "given", "deferred")
KINDS = ("direct", "times_diameter")
_DIAMETER = "diameter_m"


@dataclass(frozen=True)
class DesignVariable:
    """One axis of the design space. Bounds are in the variable's own units."""

    name: str
    kind: str
    path: str
    units: str
    role: str
    lower: float
    upper: float
    reference: float

    @property
    def span(self) -> float:
        return self.upper - self.lower


def _set_path(config: dict[str, Any], path: str, value: float) -> None:
    """Write `value` at a dotted path. Integer components index into lists."""
    node: Any = config
    parts = path.split(".")
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node.setdefault(part, {})
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


def _deep_update(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


@dataclass(frozen=True)
class DesignSpace:
    """An ordered set of variables, the ones currently ACTIVE, and the base config."""

    variables: tuple[DesignVariable, ...]
    active: tuple[str, ...]
    base_config: dict[str, Any]

    # -- construction ------------------------------------------------------------------

    @classmethod
    def from_config(cls, space_cfg: dict[str, Any], root: Path = REPO_ROOT) -> DesignSpace:
        """Build from a parsed `design_space.yaml`. All variables start active."""
        meta = space_cfg["meta"]
        base = load_config(root / meta["base_config"])
        _deep_update(base, space_cfg.get("base_overrides") or {})
        geometry_bounds = load_config(root / meta["geometry_bounds"])

        variables: list[DesignVariable] = []
        for name, spec in space_cfg["variables"].items():
            kind, role = str(spec["kind"]), str(spec["role"])
            if kind not in KINDS:
                raise ValueError(f"variable '{name}': unknown kind '{kind}', expected {KINDS}")
            if role not in ROLES:
                raise ValueError(f"variable '{name}': unknown role '{role}', expected {ROLES}")
            lower, upper = float(spec["min"]), float(spec["max"])
            reference = float(spec["reference"])
            if not lower < upper:
                raise ValueError(f"variable '{name}': min {lower} must be below max {upper}")
            if not lower <= reference <= upper:
                raise ValueError(f"variable '{name}': reference {reference} is outside "
                                 f"[{lower}, {upper}]")
            ref_name = spec.get("bounds_ref")
            if ref_name is not None:
                outer = geometry_bounds.get(ref_name)
                if outer is None:
                    raise KeyError(f"variable '{name}': bounds_ref '{ref_name}' is not in "
                                   f"{meta['geometry_bounds']}")
                lo, hi = outer.get("min"), outer.get("max")
                if (lo is not None and lower < lo) or (hi is not None and upper > hi):
                    raise ValueError(
                        f"variable '{name}': range [{lower}, {upper}] leaves the geometry "
                        f"bound '{ref_name}' [{lo}, {hi}] ({meta['geometry_bounds']})")
            variables.append(DesignVariable(name, kind, str(spec["path"]),
                                            str(spec.get("units", "")), role,
                                            lower, upper, reference))

        names = [v.name for v in variables]
        if any(v.kind == "times_diameter" for v in variables) and _DIAMETER not in names:
            raise ValueError("a times_diameter variable needs a 'diameter_m' variable")
        return cls(tuple(variables), tuple(names), base)

    # -- views -------------------------------------------------------------------------

    def variable(self, name: str) -> DesignVariable:
        for var in self.variables:
            if var.name == name:
                return var
        raise KeyError(name)

    @property
    def active_variables(self) -> tuple[DesignVariable, ...]:
        return tuple(self.variable(name) for name in self.active)

    @property
    def n_active(self) -> int:
        return len(self.active)

    @property
    def lower(self) -> np.ndarray:
        return np.array([v.lower for v in self.active_variables])

    @property
    def upper(self) -> np.ndarray:
        return np.array([v.upper for v in self.active_variables])

    def with_active(self, names: list[str] | tuple[str, ...]) -> DesignSpace:
        """Same space with only `names` free; every other variable sits at its reference."""
        for name in names:
            self.variable(name)
        ordered = tuple(v.name for v in self.variables if v.name in set(names))
        return replace(self, active=ordered)

    def with_bounds(self, overrides: dict[str, dict[str, float]]) -> DesignSpace:
        """Same space with narrowed ranges (the Sobol all-valid sub-box)."""
        new_vars = []
        for var in self.variables:
            spec = overrides.get(var.name)
            if spec is None:
                new_vars.append(var)
                continue
            lower, upper = float(spec["min"]), float(spec["max"])
            if lower < var.lower or upper > var.upper or not lower < upper:
                raise ValueError(f"sub-box for '{var.name}' [{lower}, {upper}] must lie "
                                 f"inside [{var.lower}, {var.upper}]")
            reference = min(max(var.reference, lower), upper)
            new_vars.append(replace(var, lower=lower, upper=upper, reference=reference))
        return replace(self, variables=tuple(new_vars))

    # -- vector <-> values <-> config --------------------------------------------------

    def from_unit(self, unit_x: np.ndarray) -> np.ndarray:
        """Map points of the unit hypercube [0, 1]^k onto the active box."""
        unit_x = np.asarray(unit_x, dtype=float)
        return self.lower + unit_x * (self.upper - self.lower)

    def to_unit(self, x: np.ndarray) -> np.ndarray:
        return (np.asarray(x, dtype=float) - self.lower) / (self.upper - self.lower)

    def values(self, x: np.ndarray) -> dict[str, float]:
        """Full name -> value mapping for an ACTIVE-variable vector (frozen ones filled in)."""
        x = np.asarray(x, dtype=float)
        if x.shape != (self.n_active,):
            raise ValueError(f"expected a vector of length {self.n_active}, got {x.shape}")
        out = {v.name: v.reference for v in self.variables}
        out.update({name: float(val) for name, val in zip(self.active, x, strict=True)})
        return out

    def config_for(self, values: dict[str, float]) -> dict[str, Any]:
        """Evaluator config for one design. Does NOT validate geometry - the evaluator does."""
        cfg = copy.deepcopy(self.base_config)
        diameter = float(values[_DIAMETER]) if _DIAMETER in values else float(
            cfg["vehicle"]["geometry"]["diameter_m"])
        for var in self.variables:
            value = float(values[var.name])
            if var.kind == "times_diameter":
                value *= diameter
            _set_path(cfg, var.path, value)
        return cfg

    def clip(self, x: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(x, dtype=float), self.lower, self.upper)


def load_design_space(path: str | Path, root: Path = REPO_ROOT) -> tuple[DesignSpace, dict]:
    """(DesignSpace, raw study config) from a `design_space.yaml`."""
    cfg = load_config(path)
    return DesignSpace.from_config(cfg, root), cfg
