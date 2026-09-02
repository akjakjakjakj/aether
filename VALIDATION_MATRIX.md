# Validation matrix

Status values are exactly as defined in the specification (§30):
`NOT_STARTED` · `IN_PROGRESS` · `PASS` · `FAIL` · `LIMITED`.

**`LIMITED` is never reported as `PASS`.** A row is `PASS` only when it has been checked
against an independent reference, not merely when the code runs.

Last updated: 2026-09-02 · after M1.

| Gate | Subsystem | Verification method | Validation source | Tolerance | Status | Evidence |
|---|---|---|---|---|---|---|
| G1A | Atmosphere, 0–86 km | Exact integration of the defined USSA-76 layer profile; ideal-gas closure; monotonic density | Published USSA-76 layer-base T and p values | 0.01% on T, 0.1% on p | **PASS** | `tests/test_atmosphere.py::test_layer_boundaries_against_published_table` |
| G1A′ | Atmosphere, 86–150 km | Log-interpolation of a transcribed table; runtime `extrapolated` flag; refusal above 150 km | Transcribed USSA-76 table, **not yet checked against a primary copy** | — | **LIMITED** | `src/aether/atmosphere/us76.py` `_UPPER_TABLE`; see ASSUMPTIONS A-ATM-2 |
| G1B | Trajectory | Integrator tolerance convergence; physical-ordering tests (steeper ⇒ shorter and higher g); ballistic-coefficient ordering; no nonphysical states | No independent flight or published trajectory comparison yet | 0.01% on max-g between rtol 1e-8 and 1e-10 | **LIMITED** | `tests/test_trajectory.py` (7 tests). Verified, not validated — no external reference case has been reproduced. |
| G2 | Aeroheating | Exact V³, √ρ and 1/√R_n scaling; direct reference evaluation; input-domain rejection | NASA TR R-376 cited as the source of the correlation, but the constant has **not** been re-derived from the primary document | 1e-12 on scaling ratios | **LIMITED** | `tests/test_heating.py` (7 tests); see ASSUMPTIONS A-HEAT-1 |
| G3 | TPS conduction | Analytical benchmark at four depths and at the surface; grid-refinement convergence; timestep-refinement convergence; energy-balance closure; null test; physical-ordering tests | Carslaw & Jaeger, *Conduction of Heat in Solids* 2nd ed. §2.9, semi-infinite solid under constant surface flux | 0.2% against analytical; energy residual < 1e-6 | **PASS** | `tests/test_tps.py` (11 tests). Measured: 0.002% surface error, energy residual ~1e-14. |
| M1 | Burn-vs-bake result | Full-domain sweep; automated signature-pair search with pre-declared thresholds; rank correlation | Self-consistent within the model. No external validation exists for this claim. | — | **IN_PROGRESS** | `reports/milestones/M1_burn_vs_bake.md`. The *mechanism* is verified; the *magnitude* is model-dependent and awaits Fidelity 1 and the physical coupon experiment. |
| G4 | OpenFOAM CFD | Mesh independence, force convergence, published blunt-body benchmark, model-form limitations | Not begun | — | **NOT_STARTED** | Gated: no CFD data may enter the optimisation loop until this row is PASS. |
| G5 | Coupled model | End-to-end evaluator determinism and provenance | Not begun | — | **IN_PROGRESS** | `src/aether/evaluate.py` exists and is the sole evaluation path; formal gate not yet run. |
| M8 | Physical thermal coupon | Blind prediction, frozen before measurement | Not begun | — | **NOT_STARTED** | `experiments/thermal_coupon/` scaffolded only. |

## What the current evidence does and does not support

**Supported.** Within this model, over the tested domain, peak external heat flux and
peak bondline temperature are perfectly anti-ordered (Spearman ρ = −1.0), and a joint
objective selects a design with materially more bondline margin than a peak-flux-only
objective does. The conduction solver underlying that claim agrees with an analytical
benchmark to 0.002% and closes its energy balance to ~10⁻¹⁴.

**Not supported.** Any statement about a real vehicle, a real TPS material, or a flight
condition. The aerodynamics are a constant coefficient, the heating correlation has not
been re-derived from its primary source, and no CFD or experimental validation exists
yet. Three of the six active rows above are `LIMITED`, and that is the honest state of
the project.
