# Project status

Updated 2026-09-02.

## Milestones

| ID | Milestone | Status |
|---|---|---|
| M0 | Repository, reproducibility, provenance, test harness | **Complete** |
| M1 | Burn-vs-bake reduced-order demonstration | **Complete** — H0 supported, ρ = −1.0 |
| M1b | Geometry axis opened; peak-only vs joint optimiser comparison | **Complete** — H1 supported |
| M2 | OpenFOAM validation (mesh independence, benchmark, GCI) | Not started — **gates all CFD-derived optimisation** |
| M3 | Coupled geometry / CFD / trajectory / TPS | Not started |
| M4 | Pareto optimisation (NSGA-II + baseline) | Not started |
| M5 | AI vs conventional optimiser ablation | Not started |
| M6 | Adaptive-fidelity result | Not started |
| M7 | Uncertainty propagation and robust design | Not started |
| M8 | Thermal coupon blind validation | Not started |
| M9 | Final paper and reproducibility package | Not started |

## Headline results so far

**H0 — supported.** Across a 41-point sweep of entry flight-path angle from −8.0° to
−1.5°, peak heat flux and peak bondline temperature are both **strictly monotone in
entry angle, with opposite signs**: there is no interior angle at which both improve.
The endpoints differ by **38.3% lower peak flux and a 114 K hotter bondline**.

The rank correlation over this sweep is Spearman ρ = −1.000, but that number is close to
tautological — two strictly monotone functions of one swept variable can only give ±1 —
and must not be quoted as independent evidence. The monotonicity is the finding; the
correlation coefficient adds nothing to it. A claim about the *design space* rather than
this one-parameter family requires M1b and, properly, the DOE at M4.

**The feasibility squeeze.** With geometry frozen, **zero of 41** candidates satisfy
both the 12 g deceleration limit and the 450 K bondline limit. Steep entries fail on
deceleration; shallow entries fail on bondline. Trajectory shaping alone cannot produce
a valid design — which is the reason O1 optimises geometry and trajectory jointly.

**H1 — supported.** Opening the diameter axis (140-point grid) recovers 21 feasible
designs. A peak-flux-only optimiser selects a design with a bondline at 444.1 K; a joint
optimiser selects one at 411.6 K. The joint design therefore runs **32.5 K cooler at the
bondline** for 19.6% higher peak heat flux.

Quote that absolute figure, not a margin *ratio*. The ratio is measured against the
bondline allowable, which A-LIM-1 declares an unsourced placeholder, and it swings from
37× to 1.6× as the allowable moves from 445 K to 500 K. The 32.5 K does not depend on
the allowable at all.

## Verification state

38 tests pass. The TPS solver — the component the headline claim rests on — matches the
Carslaw & Jaeger analytical solution to 0.002% at the surface and closes its energy
balance to ~10⁻¹⁴, with demonstrated grid and timestep convergence.

Three validation rows are `LIMITED`, not `PASS`. See `VALIDATION_MATRIX.md`.

## Open items

1. **The diameter bound is active.** Both M1b optima sit on the 3.0 m upper bound, so the
   bound rather than the physics is selecting them. Justify it from packaging or
   launch-vehicle constraints, or widen it and re-run.
2. **Sutton–Graves constant not re-derived** from NASA TR R-376 directly. Currently
   `LIMITED`.
3. **Upper-atmosphere table not checked** against a primary copy of USSA-76.
4. **No external trajectory reference case** has been reproduced. G1B is verified but not
   validated.
5. **Constraint limits are unsourced** engineering placeholders (`A-LIM-1`). They set
   where the feasible region falls, though not whether the anti-correlation exists.
6. **Only one parameter was swept in M1.** The monotonicity result is a statement about a
   one-parameter family, not a design space. M4's DOE is what upgrades it.
7. **Backward Euler is first-order in time.** Adequate and convergent, but Crank–Nicolson
   would cut timestep cost for the same accuracy — worth doing before the optimisation
   loop makes evaluation count matter.

## Next action

M2: verify the OpenFOAM v2606 installation, record the exact version, and build the
automated case pipeline. **No CFD result may enter the optimisation loop until mesh
independence, force convergence and a published blunt-body benchmark comparison are all
documented** (spec §17).
