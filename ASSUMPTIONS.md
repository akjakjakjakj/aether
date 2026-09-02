# Assumptions

Every assumption that could change a conclusion, with its justification and the
direction of the error it introduces. An assumption that is not written here is a
defect, not a simplification.

Legend for **Effect**: which way the assumption biases the headline result
(the anti-correlation between peak heat flux and bondline temperature).

---

## Atmosphere

| ID | Assumption | Justification | Effect |
|---|---|---|---|
| A-ATM-1 | US Standard Atmosphere 1976, 0–86 km, computed exactly from the standard's defined layer profile. | It is the reference standard for this class of study and is reproducible by anyone. | None on the mechanism. Real density varies by tens of percent with solar activity, season and latitude — quantified later under uncertainty propagation, not ignored. |
| A-ATM-2 | Above 86 km, values are **log-interpolated from a transcribed table** rather than computed. USSA-76 above 86 km requires a species-diffusion model with varying mean molar mass, which is out of scope. | Density above 86 km is ~10⁻⁶ kg/m³; it contributes negligibly to both drag and heating. | Negligible. Flagged `extrapolated=True` at runtime and **LIMITED** in the validation matrix. The transcribed table has not yet been checked against a primary copy of the standard — open item. |
| A-ATM-3 | Model refuses to return values above 150 km. | Silent extrapolation is a worse failure than an exception. | None. |
| A-ATM-4 | Calorically perfect air (γ = 1.4) for speed of sound. | Valid for freestream in the homosphere. | Mach is used only as a bookkeeping quantity here. It is **not** valid behind the bow shock and must not be reused there. |

## Trajectory

| ID | Assumption | Justification | Effect |
|---|---|---|---|
| A-TRAJ-1 | Point-mass 3-DOF, planar, **non-rotating** spherical Earth. | Standard for entry corridor and aerothermal sizing studies. | Earth rotation changes relative velocity by up to ~0.46 km/s at the equator, i.e. up to ~6% on V and therefore ~19% on q'' (V³). This shifts magnitudes; it does not reverse the ordering between a steep and a shallow entry. |
| A-TRAJ-2 | Constant C_D, no angle-of-attack dependence, no lift, no bank. | This is the Fidelity-0 baseline. Replacing it with a CFD-derived response surface is precisely what Fidelity 1 exists to do. | Real C_D falls through the transonic regime. The affected phase is below peak heating, so the peak-flux ordering is robust; the integrated load and hence the bondline result is more sensitive. |
| A-TRAJ-3 | Constant mass — no ablative mass loss. | Ablation chemistry is explicitly out of scope (spec §5). | An ablator carries energy away as mass loss, disproportionately in the long shallow case. This would **reduce** the size of the burn-vs-bake effect. It does not reverse it, because the mechanism is diffusive timescale, not magnitude. |
| A-TRAJ-4 | Integration stops at 20 km altitude. | Below this the aerothermal problem is over and descent/parachute phases (out of scope) take over. | The thermal solve continues past this point via the soak-out phase (A-TPS-5), so no bondline heating is lost. |

## Aeroheating

| ID | Assumption | Justification | Effect |
|---|---|---|---|
| A-HEAT-1 | Sutton–Graves stagnation-point correlation, Earth-air constant k = 1.7415×10⁻⁴ SI. | Standard engineering correlation with a documented source (NASA TR R-376). | Scaling verified; absolute value **LIMITED** pending re-derivation from the primary reference. |
| A-HEAT-2 | **Convective heating only.** Shock-layer radiative heating neglected. | Defensible for Earth entry at ~7.4 km/s with a metre-scale nose radius. | Would be indefensible at lunar-return speeds. Under-predicts total heating, more so for the steep/hot case — which makes the reported effect **conservative**. |
| A-HEAT-3 | **Cold-wall** correlation; no hot-wall or blowing correction. | Standard conservative practice. | Over-predicts flux into a hot surface. Conservative. |
| A-HEAT-4 | Stagnation point only; the whole TPS is analysed at the stagnation-point condition. | Worst-case point on the vehicle. | Real vehicles are frequently damaged at the shoulder or afterbody, which this model says nothing about. A genuine limitation, not a conservatism. |

## TPS

| ID | Assumption | Justification | Effect |
|---|---|---|---|
| A-TPS-1 | 1-D conduction normal to the surface. | TPS is thin relative to its lateral extent; lateral gradients are second-order. | Small. |
| A-TPS-2 | **Temperature-independent** k, ρ, c_p. | Fidelity-0 baseline; temperature-dependent properties are a documented later refinement. | Real insulator conductivity rises with temperature, which would **increase** bondline temperature in the long shallow case — i.e. strengthen the reported effect. |
| A-TPS-3 | **Adiabatic back face.** | Conservative: no heat is allowed to escape behind the structure. | Over-predicts bondline temperature for both cases. Does not change the ordering. |
| A-TPS-4 | Surface re-radiates to a 4 K sink with ε = 0.85, no radiation exchange between surfaces. | Near-vacuum entry environment. | Small. Radiation is the dominant surface cooling term and is modelled implicitly and nonlinearly, not linearised away. |
| A-TPS-5 | The conduction solve continues for **1200 s after the trajectory ends**, at zero incident flux. | The bondline peak *lags* the heat pulse. Truncating at the trajectory's end under-predicted the bondline peak by ~50 K in this study. | Essential. Without it the headline result is understated. Verified by `test_bondline_peak_lags_the_heat_pulse`. |
| A-TPS-6 | No contact resistance between layers; perfect thermal bonding. | Simplification. | Real contact resistance would lower bondline temperature. Affects both cases similarly. |
| A-TPS-7 | Material properties are **engineering placeholders** of the right order for a low-density insulator over an aluminium-like structure. They are not the properties of any specific qualified TPS material. | The result is about a *mechanism*, not about a product. | Absolute temperatures are indicative only. Any claim about a real material requires real property data. |

## Constraints and limits

| ID | Assumption | Justification | Effect |
|---|---|---|---|
| A-LIM-1 | Bondline allowable 450 K, deceleration limit 12 g, both declared in `configs/baseline.yaml`. | Order-of-magnitude representative. **Not sourced from a standard.** | These set where the feasibility boundary falls. The *existence* of the anti-correlation does not depend on them; the feasible region does. |
| A-LIM-2 | An unsourced limit is stored as `null` and **skipped**, never treated as satisfied. | An unknown constraint is an open question, not a pass. | Prevents false feasibility claims. |
| A-LIM-3 | Diameter bounded at 3.0 m in the M1b sweep. | Arbitrary bound for a first sweep. | **Both optima sit on this bound**, so it is active — the physics is not what stops the optimiser there. Flagged as an open item; must be justified from packaging/launch constraints or widened. |
