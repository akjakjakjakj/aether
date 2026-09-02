# Roadmap

Scope is frozen (spec §2, §42). This roadmap sequences the frozen scope; it does not
extend it. No new physics subsystem is added unless it is needed to resolve a
demonstrated validation failure in O1.

## Done

- **M0** Repository, provenance, config schema, test harness, plotting standards.
- **M1** Burn-vs-bake reduced-order demonstration. H0 supported (ρ = −1.000).
- **M1b** Geometry axis; peak-only vs joint optimiser comparison. H1 supported.

## Next

**M2 — OpenFOAM validation.** Verify the v2606 installation and record the exact
version. Build the automated case pipeline: geometry → domain → mesh → checkMesh →
solver → convergence → postprocess → metrics. Coarse/medium/fine meshes, GCI where
practical, one published blunt-body benchmark, and a written statement of model-form
limits. Produces `reports/milestones/M2_cfd_validation.md`. **Gates everything below.**

**M3 — Coupled model.** Parametric axisymmetric capsule generator with validity bounds
and reproducible STL. C_D response surface from CFD design points with cross-validation
and stored prediction uncertainty, wired in through the existing `cd_model` hook.

**M4 — Pareto optimisation.** NSGA-II plus a simpler baseline (differential evolution /
scalarised runs). Every candidate persisted. Precede with sweeps, Latin Hypercube and
sensitivity analysis so that irrelevant variables are removed before the optimiser sees
them.

**M5 — AI ablation.** Matched-budget benchmark: random search, NSGA-II, surrogate /
Bayesian optimisation, AI engineering agent, AI + adaptive fidelity. Report evaluations,
CFD calls, feasible count, hypervolume, wall time and diversity. No superiority claim
without measurement.

**M6 — Adaptive fidelity.** Promotion policy based on predicted Pareto value,
uncertainty, novelty and cost. Measure whether it actually saves CFD calls.

**M7 — Uncertainty and robustness.** Monte Carlo / LHS over atmospheric density, mass,
entry angle, TPS conductivity and heat capacity, plus surrogate uncertainty. Report
mean, standard deviation, percentiles and constraint-violation probability. Compare
nominal and robust Pareto designs.

**M8 — Thermal coupon.** Calibrate, freeze the model, archive a timestamped blind
prediction, then run the experiment. Compare high-peak/short against lower-peak/long
heating. RMSE, peak error, time-to-peak error, residuals, uncertainty coverage.

**M9 — Paper and package.** 15–25 page paper, poster, 2-page brief, reproducibility
package, external review record.

## Immediate open items

Carried from `PROJECT_STATUS.md`: justify or widen the active diameter bound; re-derive
the Sutton–Graves constant from TR R-376; check the >86 km atmosphere table against a
primary source; reproduce an external trajectory reference case; source the constraint
limits; consider Crank–Nicolson before evaluation count starts to matter.
