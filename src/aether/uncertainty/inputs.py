"""The declared uncertain inputs: what varies, by how much, on whose authority.

Conceptual anchor
-----------------
An uncertainty study is only as good as its inventory. This module is the inventory's
loader and its gatekeeper: it reads `configs/uncertainty.yaml`, refuses anything that is
not fully declared, and turns one unit-cube point into one patched evaluator config.

Three rules it enforces, because each was a way of quietly cheating:

1. **Every input carries a SOURCE and a TIER** (`T1` primary opened and read, `T2`
   reputable secondary, `T3` engineering judgment). A `T3` input must *say* it is
   judgment in its own source line; the loader refuses it otherwise. An unsourced spread
   is allowed here - what is not allowed is an unsourced spread that reads as though it
   were sourced.

2. **Every input is labelled ALEATORY or EPISTEMIC** and the two never merge.
   *Aleatory* is mission-to-mission variability: fly it again and you get another draw
   (the day's atmosphere, the as-built mass). *Epistemic* is ignorance about a fixed
   truth: which of two NASA reports is right about the effective nose radius does not
   change between flights, and averaging over it produces a number that describes no
   vehicle. They are carried separately all the way to the outputs.

3. **An input whose evidence does not exist yet REFUSES, it does not silently vanish.**
   The C_D discretisation band is read from M2's GCI study, which has not produced one.
   That input declares `when_unavailable: refuse`, so a run that would have dropped the
   term stops instead. Dropping it would understate the C_D uncertainty and nothing in
   the output would show it.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..aerodynamics.cfd_surface import discretisation_band
from ..utils.run import REPO_ROOT, load_config
from .distributions import Discrete, Distribution, build_distribution

ALEATORY = "aleatory"
EPISTEMIC = "epistemic"
KINDS = (ALEATORY, EPISTEMIC)

TIERS = ("T1", "T2", "T3")
TIER_LABEL = {"T1": "✅ T1 primary", "T2": "🟡 T2 secondary",
              "T3": "❌ T3 engineering judgment"}

APPLY_TYPES = ("multiply", "multiply_one_plus", "offset", "set", "density_profile",
               "select")

WHEN_UNAVAILABLE = ("refuse", "skip")


class InputUnavailable(RuntimeError):
    """A declared uncertain input cannot be evaluated and said to refuse rather than skip."""


# ---------------------------------------------------------------------------------------
# config plumbing
# ---------------------------------------------------------------------------------------

def _get_path(config: dict[str, Any], path: str) -> Any:
    node: Any = config
    for part in path.split("."):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def _set_path(config: dict[str, Any], path: str, value: Any) -> None:
    """Write `value` at a dotted path, creating intermediate mappings. Ints index lists.

    Same semantics as `optimization.design_space._set_path`; duplicated rather than
    imported so that the uncertainty package does not depend on the optimisation package
    for something this small.
    """
    node: Any = config
    parts = path.split(".")
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node.setdefault(part, {})
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


# ---------------------------------------------------------------------------------------
# one input
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class UncertainInput:
    """One declared uncertain quantity."""

    name: str
    kind: str
    distribution: Distribution
    apply: dict[str, Any]
    source: str
    tier: str
    units: str = ""
    notes: str = ""
    requires: dict[str, Any] | None = None
    when_unavailable: Any = "refuse"
    """`'refuse'`, `'skip'`, or a mapping from requirement name to one of those.

    Per-requirement, because the two failure modes are not the same thing. An input that
    only exists at Fidelity 1 should quietly SKIP at Fidelity 0 - there is no CFD surface
    for it to be about. The same input's dependence on M2's GCI study must REFUSE, because
    there the surface exists, the term is real, and dropping it would understate the C_D
    uncertainty with nothing in the output to show it (A-CFD-9).
    """
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"input '{self.name}': kind must be one of {KINDS}, "
                             f"got {self.kind!r}")
        if self.tier not in TIERS:
            raise ValueError(f"input '{self.name}': tier must be one of {TIERS}, "
                             f"got {self.tier!r}")
        if not self.source.strip():
            raise ValueError(f"input '{self.name}': every input needs a `source` line")
        if self.tier == "T3" and "judgment" not in self.source.lower():
            raise ValueError(
                f"input '{self.name}' is tier T3 but its source line does not say so. An "
                "unsourced spread is allowed ONLY if it is labelled engineering judgment "
                "in its own source line - write it there.")
        apply_type = str(self.apply.get("type", ""))
        if apply_type not in APPLY_TYPES:
            raise ValueError(f"input '{self.name}': apply.type must be one of "
                             f"{APPLY_TYPES}, got {apply_type!r}")
        if apply_type == "select" and not isinstance(self.distribution, Discrete):
            raise ValueError(f"input '{self.name}': apply.type 'select' needs a discrete "
                             "distribution")
        policies = (self.when_unavailable.values()
                    if isinstance(self.when_unavailable, dict) else [self.when_unavailable])
        for policy in policies:
            if policy not in WHEN_UNAVAILABLE:
                raise ValueError(f"input '{self.name}': when_unavailable must be one of "
                                 f"{WHEN_UNAVAILABLE} (or a mapping to those), got "
                                 f"{policy!r}")
        if isinstance(self.when_unavailable, dict):
            unknown = set(self.when_unavailable) - set(self.requires or {})
            if unknown:
                raise ValueError(f"input '{self.name}': when_unavailable names "
                                 f"requirements it does not declare: {sorted(unknown)}")

    def policy_for(self, requirement: str) -> str:
        if isinstance(self.when_unavailable, dict):
            return str(self.when_unavailable.get(requirement, "refuse"))
        return str(self.when_unavailable)

    # -- availability ------------------------------------------------------------------
    def unavailable_because(self, base_config: dict[str, Any]) -> tuple[str, str] | None:
        """(requirement, why) this input cannot be used, or None if it can.

        Requirements are checked IN DECLARATION ORDER, and the first failure wins, so a
        config can say "at Fidelity 0 skip me, but if the surface IS in use and its GCI is
        missing, refuse" simply by listing `aero_model` first.

        Checked, never assumed:
          `aero_model`           the evaluator's `vehicle.aero.model` must be this
          `discretisation_band`  M2's GCI study must have produced a band at this mesh
                                 level (`results/M2/<run>/gci.csv`), read at call time
        """
        for key, want in (self.requires or {}).items():
            if key == "aero_model":
                have = str((base_config.get("vehicle", {}).get("aero") or {})
                           .get("model", "constant"))
                if have != str(want):
                    return (key, f"needs vehicle.aero.model == {want!r}, but the base "
                                 f"config uses {have!r}")
            elif key == "discretisation_band":
                band = discretisation_band(str(want))
                if not band["available"]:
                    return (key, "the CFD discretisation band is not available: M2 has "
                                 f"produced no {want}-mesh GCI "
                                 "(results/M2/<run>/gci.csv). A-CFD-9 says this term "
                                 "RAISES rather than silently becoming zero")
            else:
                raise ValueError(f"input '{self.name}': unknown requirement {key!r}")
        return None

    # -- sampling ----------------------------------------------------------------------
    def value(self, u: float) -> Any:
        """The physical draw for a unit-cube coordinate `u`."""
        raw = float(np.atleast_1d(self.distribution.ppf(np.atleast_1d(u)))[0])
        if str(self.apply["type"]) == "select":
            return self.distribution.select(raw)  # type: ignore[union-attr]
        return raw

    def patch(self, config: dict[str, Any], value: Any) -> None:
        """Apply one draw to `config`, in place."""
        spec = self.apply
        kind = str(spec["type"])
        if kind == "density_profile":
            _apply_density_profile(config, spec, float(value))
            return
        path = str(spec["path"])
        if kind == "set" or kind == "select":
            _set_path(config, path, value)
        elif kind == "multiply":
            _set_path(config, path, float(_get_path(config, path)) * float(value))
        elif kind == "multiply_one_plus":
            _set_path(config, path, float(_get_path(config, path)) * (1.0 + float(value)))
        elif kind == "offset":
            _set_path(config, path, float(_get_path(config, path)) + float(value))

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "units": self.units,
                "distribution": self.distribution.to_dict(),
                "describe": self.distribution.describe(),
                "apply": dict(self.apply), "source": self.source, "tier": self.tier,
                "tier_label": TIER_LABEL[self.tier], "notes": self.notes,
                "requires": dict(self.requires or {}),
                "when_unavailable": self.when_unavailable}


def _apply_density_profile(config: dict[str, Any], spec: dict[str, Any], z: float) -> None:
    """Turn a standard-normal draw into an altitude-dependent density multiplier.

        multiplier(h) = 1 + z * sigma(h)

    ONE z for the whole trajectory (see `atmosphere.perturbed` for why), with sigma(h)
    the declared 1-sigma dispersion table. The multiplier is floored at
    `min_multiplier` so a large negative draw cannot produce a non-positive density; the
    floor is recorded in the config snapshot and the propagation reports how often it bit.
    """
    altitudes = [float(z_km) for z_km in spec["sigma_vs_altitude_km"]["altitude_km"]]
    sigmas = [float(s) for s in spec["sigma_vs_altitude_km"]["sigma_relative"]]
    if len(altitudes) != len(sigmas):
        raise ValueError("density_profile: altitude_km and sigma_relative differ in length")
    floor = float(spec.get("min_multiplier", 0.05))
    multiplier = [max(floor, 1.0 + z * s) for s in sigmas]
    _set_path(config, "atmosphere.density_multiplier_profile",
              {"altitude_km": altitudes, "multiplier": multiplier})


# ---------------------------------------------------------------------------------------
# the whole inventory
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class UncertaintyModel:
    """The ordered, filtered list of uncertain inputs plus the raw study config."""

    inputs: tuple[UncertainInput, ...]
    config: dict[str, Any]
    skipped: tuple[tuple[str, str], ...] = ()
    """(name, reason) for inputs that declared `when_unavailable: skip` and were."""

    # -- construction ------------------------------------------------------------------
    @classmethod
    def from_config(cls, cfg: dict[str, Any], base_config: dict[str, Any]
                    ) -> UncertaintyModel:
        """Build from a parsed `uncertainty.yaml` and the evaluator config it runs on.

        Raises `InputUnavailable` if an input that declared `refuse` cannot be evaluated.
        """
        built: list[UncertainInput] = []
        skipped: list[tuple[str, str]] = []
        for name, spec in (cfg.get("inputs") or {}).items():
            spec = dict(spec)
            if not bool(spec.pop("enabled", True)):
                skipped.append((name, "disabled in config"))
                continue
            item = UncertainInput(
                name=name,
                kind=str(spec["kind"]),
                distribution=build_distribution(spec["distribution"]),
                apply=dict(spec["apply"]),
                source=str(spec["source"]),
                tier=str(spec["tier"]),
                units=str(spec.get("units", "")),
                notes=str(spec.get("notes", "")),
                requires=dict(spec["requires"]) if spec.get("requires") else None,
                when_unavailable=(dict(spec["when_unavailable"])
                                  if isinstance(spec.get("when_unavailable"), dict)
                                  else str(spec.get("when_unavailable", "refuse"))),
            )
            failure = item.unavailable_because(base_config)
            if failure is None:
                built.append(item)
                continue
            requirement, reason = failure
            if item.policy_for(requirement) == "refuse":
                raise InputUnavailable(
                    f"REFUSING TO RUN: uncertain input '{name}' {reason}.\n"
                    "Its requirement `" + requirement + "` is declared "
                    "`when_unavailable: refuse` precisely so that the term cannot be "
                    "dropped without anyone noticing. Either produce the evidence it "
                    "needs, or change its declaration in configs/uncertainty.yaml "
                    "deliberately and say so in the report.")
            skipped.append((name, reason))
        if not built:
            raise ValueError("no uncertain inputs are active; there is nothing to propagate")
        return cls(tuple(built), cfg, tuple(skipped))

    @classmethod
    def load(cls, path: str | Path, base_config: dict[str, Any] | None = None,
             root: Path = REPO_ROOT) -> tuple[UncertaintyModel, dict[str, Any]]:
        """(model, raw config) from a `uncertainty.yaml`. Loads the base config if needed."""
        cfg = load_config(path)
        if base_config is None:
            base_config = load_config(root / cfg["meta"]["base_config"])
        return cls.from_config(cfg, base_config), cfg

    # -- views -------------------------------------------------------------------------
    @property
    def names(self) -> tuple[str, ...]:
        return tuple(i.name for i in self.inputs)

    @property
    def n_inputs(self) -> int:
        return len(self.inputs)

    def of_kind(self, kind: str) -> tuple[UncertainInput, ...]:
        return tuple(i for i in self.inputs if i.kind == kind)

    def indices_of_kind(self, kind: str) -> tuple[int, ...]:
        return tuple(i for i, item in enumerate(self.inputs) if item.kind == kind)

    @property
    def tier_counts(self) -> dict[str, int]:
        return {t: sum(1 for i in self.inputs if i.tier == t) for t in TIERS}

    # -- sampling ----------------------------------------------------------------------
    def draw(self, unit_point: np.ndarray) -> dict[str, Any]:
        """Physical values for one unit-cube point, keyed by input name."""
        unit_point = np.asarray(unit_point, dtype=float)
        if unit_point.shape != (self.n_inputs,):
            raise ValueError(f"expected a unit point of length {self.n_inputs}, "
                             f"got {unit_point.shape}")
        return {item.name: item.value(u)
                for item, u in zip(self.inputs, unit_point, strict=True)}

    def patch(self, config: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        """A DEEP COPY of `config` with every draw applied. The original is untouched."""
        patched = copy.deepcopy(config)
        for item in self.inputs:
            if item.name in values:
                item.patch(patched, values[item.name])
        return patched

    def config_for_unit(self, config: dict[str, Any], unit_point: np.ndarray
                        ) -> dict[str, Any]:
        return self.patch(config, self.draw(unit_point))

    # -- reporting ---------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "n_inputs": self.n_inputs,
            "n_aleatory": len(self.of_kind(ALEATORY)),
            "n_epistemic": len(self.of_kind(EPISTEMIC)),
            "tier_counts": self.tier_counts,
            "inputs": [i.to_dict() for i in self.inputs],
            "skipped": [{"name": n, "reason": r} for n, r in self.skipped],
        }
