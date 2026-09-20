# Fidelity-1 CFD: what the model is, and what it may and may not be used for

Gate G4, condition 4 (spec §17): *limitations of the selected physical model are documented.*
This file is that document. It is prose about the model, not about results; the numbers live
in `reports/milestones/M2_cfd_validation.md`, which is generated from result files.

## The model

| Item | Choice |
|---|---|
| Solver | OpenFOAM `rhoCentralFoam` (density-based, Kurganov–Tadmor central-upwind fluxes, van Leer reconstruction) |
| Equations | Axisymmetric compressible **Euler** equations (dynamic viscosity set to zero) |
| Gas | Single-species **calorically perfect** air, γ = 1.4, R = 287.053 J kg⁻¹ K⁻¹ (USSA-76 value, `utils/constants.py`) |
| Time integration | Local time stepping (pseudo-time) to a steady state |
| Geometry | 5° wedge, zero angle of attack, body of revolution |
| Domain | **Forebody only**: nose to the maximum-radius station, closed by a supersonic outflow plane |
| Walls | Slip (no boundary layer) |

## What is NOT modelled, and what that costs

1. **No high-temperature gas physics.** No vibrational excitation, dissociation, ionisation or
   finite-rate chemistry. Behind a real entry bow shock at 7 km/s air does not behave as a
   γ = 1.4 gas: energy goes into vibration and dissociation, the density ratio across the shock
   rises well above the perfect-gas limit of 6, and the shock layer thins accordingly (standard
   textbook result, e.g. Anderson, *Hypersonic and High-Temperature Gas Dynamics*, ch. 14 —
   cited from the textbook, **not re-derived or checked in this project**). A perfect-gas
   stand-off distance is therefore wrong for flight, in a known direction (too large).
2. **No viscosity.** No boundary layer, no skin friction, no separation physics. Skin friction
   on a blunt forebody is expected to be small next to pressure drag, but this project has not
   quantified it; separation matters behind the shoulder, which this domain does not contain.
3. **No wake and no base pressure.** The domain stops at the maximum-radius station. The
   pressure on everything aft of it is not computed. An attempt to compute it with the Euler
   equations did not reach a steady state and is recorded as negative result NR-06; an inviscid
   wake has no physical mechanism fixing its base pressure, so that attempt would not have been
   trustworthy even if it had converged.
4. **No radiation**, no ablation, no surface catalysis, no blowing.
5. **No turbulence, no transition.**
6. **Zero angle of attack only.** Axisymmetric by construction.
7. **Steady flow only.**
8. **Mach range.** Validated at Mach 3 and 6. The perfect-gas assumption is *defensible for
   wind-tunnel-like conditions* across that range. It is **not** a statement about flight at the
   same Mach numbers at high enthalpy.

## Permitted uses in this project

- **Forebody pressure-drag coefficient** C_D,fore(M, geometry) at zero incidence, for blunt
  axisymmetric bodies whose shoulder flow is supersonic at the maximum-radius station (the
  pipeline measures the minimum outflow Mach number on every case and reports it).
- **Surface pressure distribution** on the forebody.
- **Bow-shock shape and stand-off distance *as perfect-gas quantities***, e.g. for comparing
  geometries with each other under one consistent model.
- **Relative comparisons between geometries** — the intended use in M3/M4. A modelling error
  that is common to all candidates largely cancels in a ranking; it does not cancel in an
  absolute number.

Why C_D survives the perfect-gas assumption when the stand-off distance does not: blunt-body
surface pressure is set mainly by the normal momentum flux ρ∞V∞², and the stagnation pressure
coefficient moves only from ≈1.84 (γ = 1.4) to ≈2.0 (the Newtonian limit γ → 1). Hypersonic
pressure-drag coefficients are therefore insensitive to the gas model at the level of several
percent — the Mach-number-independence principle. That is an argument from theory, **not**
something this project has validated; the several-percent figure is carried forward as an
uncertainty, not as a result.

## Forbidden uses

- **Heating. Any heating.** No wall heat flux, no stagnation-point heating, no heating
  distribution, no recovery temperature. An inviscid solver has no thermal boundary layer, so it
  has no heat flux to report, and the perfect-gas shock-layer temperature at entry speed is far too
  high because none of the energy is allowed to go into dissociation. **Heating stays with Sutton–Graves (gate G2).** Nothing computed
  by this CFD may be used to modify, calibrate or "correct" the heating model.
- **Shock-layer temperature, density or species** as flight quantities.
- **Flight shock stand-off distance.**
- **Total drag including the base**, as a CFD result. The trajectory model needs a total C_D;
  the base contribution has to come from a separately stated assumption with its own
  uncertainty (see ASSUMPTIONS A-CFD-5), and the report must say which part is computed and
  which part is assumed.
- **Angle-of-attack effects, lift, pitching moment, static or dynamic stability.**
- **Subsonic, transonic or low-supersonic flight** (below the validated range), where the
  wake and the base dominate the drag of a capsule.
- **Rarefied flow.** The continuum assumption fails at the top of the entry corridor, where
  the Knudsen number is not small.
- **Anything about a real vehicle or a real TPS material.**

## Wording

Results from this model are described as "the inviscid perfect-gas model predicts …", "validated
against X within Y %", "within tested assumptions". Never "flight C_D", "flight-ready",
"proves", or any equivalent (spec §37).
