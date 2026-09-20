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

**Closed 2026-09-20** by the sourcing report and its follow-through — struck, not deleted,
so the sequence stays legible:

- ~~re-derive the Sutton–Graves constant from TR R-376~~ — done,
  `docs/theory/sutton_graves_constant.md`. Constant deliberately unchanged (NR-12);
  gate G2 → PASS.
- ~~check the >86 km atmosphere table against a primary source~~ — done at five
  altitudes, exact agreement, nothing changed; gate G1A′ → PASS/LIMITED split.
- ~~reproduce an external trajectory reference case~~ — done, Allen–Eggers (NACA 1381)
  against the Putnam & Braun 2015 benchmark; gate G1B → PASS.
- ~~source the constraint limits~~ — both sourced, neither changed. The bondline
  allowable now cites the Shuttle aluminium-structure limit (A-LIM-1a); the 12 g figure
  matches no documented sustained-g curve and is now an explicit open **student
  decision** in `ASSUMPTIONS.md`, with its measured effect on the feasible region.

**Still open:**

- justify or widen the active diameter bound (A-LIM-3; partially superseded by the
  mass-closure constraint A-OPT-6, not closed by it);
- **decide the deceleration limit** — Option A (relabel 12 g as an emergency envelope) or
  Option B (adopt the NASA-STD-3001 duration-dependent deconditioned curve, which empties
  the M1b feasible region). Option B additionally requires a *pulse-duration* metric; the
  evaluator currently stores `max_g` only;
- close the rest of G1A′: the 86/95/130 km rows, the pressure column, and the
  interpolation between rows — promoted from housekeeping by NR-14;
- read Tauber (NASA TP-2914, 1989) and Tauber & Sutton (1991) and quantify the
  Sutton–Graves model-form limits (gate G2′), catalycity first;
- consider Crank–Nicolson before evaluation count starts to matter.
