"""Aerodynamic model selection - the one place a drag model is chosen.

Conceptual anchor
-----------------
The trajectory integrator does not care where C_D comes from; it takes an optional
callable `cd_model(mach, altitude_m) -> C_D` (see `trajectory.integrate_entry`). This
module turns the `vehicle.aero` block of a config into that callable, and reports the
FIDELITY LEVEL of what it built, so every result can be labelled with the fidelity of the
aerodynamics that produced it.

    vehicle:
      aero:
        model: constant        # Fidelity 0 - uses vehicle.cd, ASSUMPTIONS A-TRAJ-2

Swapping in the M3 CFD response surface is meant to be a config change plus a re-run:
register a builder under a new model name here, point `vehicle.aero.model` at it, and no
study, DOE or optimiser changes.

M3 registered `cfd_surface_v1`, built while gate G4 was IN_PROGRESS; it stays registered for
provenance and stays PROVISIONAL. `cfd_surface_v2` (see `cfd_surface.py`) is the current
surface. Whether a surface is provisional is READ - from the gate status its own
`surface.json` recorded at build time and from M2's `gate_assessment.json` now - and a
provisional surface is REFUSED (`GateNotPassedError`) unless the config carries
`allow_provisional: true`, which labels every result it produces (spec section 17).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

CdModel = Callable[[float, float], float]
"""(mach, altitude_m) -> C_D, dimensionless."""

_Builder = Callable[[dict[str, Any], Any], "tuple[CdModel | None, int]"]
_REGISTRY: dict[str, _Builder] = {}


def register_aero_model(name: str, builder: _Builder) -> None:
    """Register `builder(aero_cfg, geometry) -> (cd_model | None, fidelity)` under `name`."""
    _REGISTRY[name] = builder


def _build_constant(aero_cfg: dict[str, Any], geometry: Any) -> tuple[CdModel | None, int]:
    """Fidelity 0: constant `vehicle.cd`. Returning None makes the integrator use it.

    The capsule SHAPE therefore has no aerodynamic consequence at this fidelity - only
    the diameter acts, through the reference area. That is a property of the model, not
    of the physics, and the M4 report says so.
    """
    return None, 0


register_aero_model("constant", _build_constant)


def _cfd_surface_builder(model_name: str) -> _Builder:
    """Fidelity 1: CFD-derived C_D(Mach, forebody shape). Imported lazily - the surrogate
    package imports the evaluator, which imports this module."""
    def build(aero_cfg: dict[str, Any], geometry: Any) -> tuple[CdModel | None, int]:
        from .cfd_surface import build_cfd_surface_model

        return build_cfd_surface_model(aero_cfg, geometry, model_name=model_name)
    return build


# v1 was built while gate G4 was IN_PROGRESS: kept for provenance, provisional for ever (its
# own surface.json says so, and the builder reads it). v2 is the current surface.
register_aero_model("cfd_surface_v1", _cfd_surface_builder("cfd_surface_v1"))
register_aero_model("cfd_surface_v2", _cfd_surface_builder("cfd_surface_v2"))


def build_cd_model(aero_cfg: dict[str, Any] | None, geometry: Any) -> tuple[CdModel | None, int]:
    """Build the drag model named by a `vehicle.aero` config block.

    Parameters
    ----------
    aero_cfg:
        The `vehicle.aero` mapping, or None for the Fidelity-0 default.
    geometry:
        The validated `CapsuleGeometry` (or None on the legacy two-parameter path). A
        geometry-dependent model - the future CFD response surface - reads its shape
        parameters from here.

    Returns
    -------
    (cd_model, fidelity): the callable to hand to `integrate_entry` (None == constant
    `vehicle.cd`) and the integer fidelity level to label the evaluation with.
    """
    name = str((aero_cfg or {}).get("model", "constant"))
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown vehicle.aero.model '{name}'. Registered: {sorted(_REGISTRY)}. A "
            "CFD-derived model may only be USED once validation gate G4 is PASS "
            "(spec section 17)."
        )
    return _REGISTRY[name](aero_cfg or {}, geometry)


__all__ = ["CdModel", "build_cd_model", "register_aero_model"]
