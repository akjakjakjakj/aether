# AETHER
## When Cooler Is Not Safer: Rethinking Atmospheric Re-entry Through Peak and Cumulative Thermal Optimization

**Technical subtitle:** AI-Guided Multifidelity Framework for Coupled Re-entry Trajectory, Aerodynamics and TPS Optimization

**Capstone Project Specification**  
**Domain:** Aerospace Engineering / Computational Aerothermodynamics / Multidisciplinary Design Optimization  
**Primary tools:** Python, OpenFOAM v2606, ParaView, parametric CAD, 3D printing, thermocouples, optimization and surrogate modeling  
**Project type:** Independent student capstone with computational research, validation, optimization and focused physical experimentation

---

# 1. Executive Summary

AETHER is a computational aerospace engineering capstone investigating a deceptively simple question:

> **Is the re-entry trajectory or capsule design that minimizes peak heating necessarily the thermally safest design?**

Atmospheric re-entry exposes a spacecraft to intense but transient aerodynamic heating. A design strategy that minimizes only the maximum surface heat flux can unintentionally prolong exposure and allow more heat to conduct through the Thermal Protection System (TPS). This creates a "slow-bake" or heat-soak problem: the surface may experience a lower peak while the TPS bondline or underlying structure reaches a higher temperature.

AETHER will build a validated, reproducible engineering framework that couples:

1. atmospheric modeling;
2. re-entry trajectory integration;
3. engineering aerothermal heating correlations;
4. transient through-thickness TPS heat conduction;
5. parametric capsule geometry;
6. OpenFOAM CFD;
7. multifidelity surrogate models;
8. multi-objective optimization;
9. an AI-guided iterative engineering agent;
10. uncertainty and robustness analysis; and
11. a focused 3D-printed, instrumented thermal experiment.

The project deliberately does **not** attempt to solve every possible re-entry technology. It excludes MHD braking, regenerative electromagnetic braking, central flow-through ducts, spinning/rotating capsules, gimballed crew cores, morphing/variable geometry and other speculative extensions. The strength of the capstone is depth, validation and a clear research contribution.

The final product will compare conventional peak-heating optimization against joint peak-and-penetration optimization, quantify the trade space through a Pareto frontier, and test whether an AI-guided adaptive-fidelity search can discover high-quality designs with fewer expensive CFD evaluations than conventional search.

---

# 2. Research Motivation

A spacecraft entering Earth's atmosphere must dissipate enormous kinetic energy. For a vehicle entering at approximately 7.8 km/s, the specific kinetic energy is roughly:

\[
E_k/m = \frac{1}{2}V^2 \approx 30.4\ \mathrm{MJ/kg}
\]

The thermal protection problem is therefore not simply about lowering temperature. The engineering problem is to manage where, when and how thermal energy is transferred to the vehicle while simultaneously satisfying trajectory, structural and deceleration constraints.

Peak convective heating is strongly dependent on velocity. A Sutton-Graves-type engineering relation has the form:

\[
\dot q_{stag} = K\sqrt{\frac{\rho}{R_n}}V^3
\]

where:

- \(\dot q_{stag}\) is stagnation-point convective heat flux;
- \(\rho\) is freestream density;
- \(R_n\) is effective nose radius;
- \(V\) is freestream velocity;
- \(K\) is a gas/unit-dependent coefficient.

This immediately shows why trajectory and geometry are coupled to heating.

But peak heat flux alone is incomplete. The TPS responds over time according to transient conduction:

\[
\rho_m c_p \frac{\partial T}{\partial t}
=
\frac{\partial}{\partial x}
\left(k\frac{\partial T}{\partial x}\right)
\]

A lower external heat-flux peak can still result in a higher internal temperature if heating persists for longer. NASA thermal-protection design practice explicitly evaluates both maximum heat flux and maximum heat-load trajectories and predicts in-depth temperature histories.

AETHER therefore treats the re-entry problem as a **coupled transient optimization problem**, not a single-point temperature problem.

---

# 3. Locked Research Objective O1

## O1 - Joint Aerothermal-Trajectory Optimization

> **Determine the capsule geometry and re-entry control history that jointly minimize peak external heat flux and maximum internal TPS/bondline thermal exposure, subject to deceleration, dynamic-pressure, stability and structural constraints.**

The primary multi-objective formulation is:

\[
\min_{X,u(t)}
\left[
q''_{\max},
T_{\mathrm{bond,max}},
Q_{\mathrm{penetration}}
\right]
\]

where:

- \(X\) represents geometric/design variables;
- \(u(t)\) represents trajectory/control variables;
- \(q''_{\max}\) is maximum external convective heat flux;
- \(T_{\mathrm{bond,max}}\) is maximum TPS bondline temperature;
- \(Q_{\mathrm{penetration}}\) is a cumulative thermal-penetration metric.

The project must preserve the multi-objective nature of O1. A weighted scalar objective may be used for particular algorithms, but the final analysis must show the Pareto trade space.

### Hard constraints

At minimum:

\[
g(t) \leq g_{\max}
\]

\[
q_{dyn}(t) \leq q_{dyn,\max}
\]

\[
T_{\mathrm{bond}}(t) \leq T_{\mathrm{bond,allow}}
\]

\[
S_{\mathrm{struct}}(t) \leq S_{\mathrm{allow}}
\]

and the trajectory must satisfy valid terminal conditions.

Constraint violations may not be hidden by objective weights.

---

# 4. Primary Hypotheses

## H0 - The central scientific hypothesis

> **Minimizing peak heat flux alone does not necessarily produce the thermally safest re-entry solution.**

A lower \(q''_{\max}\) trajectory may have longer heat exposure and therefore a larger \(T_{\mathrm{bond,max}}\) or cumulative penetration.

This is the core "burn versus bake" question.

## H1 - Joint optimization hypothesis

> **Joint optimization of peak heat flux and in-depth thermal response can identify designs/trajectories that are safer than designs obtained by optimizing peak heat flux alone.**

"Safer" is defined quantitatively by O1 and its constraints.

## H2 - Computational methodology hypothesis

> **A surrogate-assisted or AI-guided adaptive-fidelity design loop can approach the Pareto frontier with fewer expensive CFD evaluations than brute-force or unguided search.**

This makes the capstone both an aerospace project and a computational-engineering project.

---

# 5. What AETHER Is Not

To preserve depth and credibility, the following are outside the capstone scope:

- MHD or plasma braking;
- regenerative electromagnetic braking;
- central flow-through ducts;
- spinning or continuously rotating re-entry capsules;
- stabilized inner crew cores or gimballed cabins;
- morphing or variable-geometry re-entry vehicles;
- propulsion or retropropulsion;
- parachute design;
- ablative chemistry as a primary model;
- flight-qualified structural design;
- home-built hypersonic or plasma testing.

These may be mentioned only as possible future research directions, not implemented as AETHER modules.

---

# 6. Research Contribution

The intended contribution is not a claim to have invented re-entry optimization.

The capstone will investigate and demonstrate a specific framework:

> **An AI-guided, multifidelity multidisciplinary design framework that jointly optimizes capsule geometry and re-entry trajectory using both peak external heating and transient in-depth TPS thermal response, with explicit validation and uncertainty analysis.**

The differentiators are:

- joint peak-heating and heat-soak treatment;
- direct coupling of trajectory and TPS response;
- comparison of single-objective and multi-objective optimization;
- adaptive use of low-, medium- and higher-fidelity models;
- quantitative comparison of numerical optimization and AI-guided candidate selection;
- physical thermal validation of the heat-penetration concept.

---

# 7. Overall System Architecture

The engineering discovery loop is:

```text
Initial Design Space
       |
       v
Parametric Capsule Geometry
       |
       v
Low-Fidelity Aerodynamics/Heating
       |
       v
Trajectory Solver
       |
       v
Transient TPS Solver
       |
       v
O1 Metrics + Constraints
       |
       v
Optimizer / AI Engineering Agent
       |
       +------> next candidate
       |
       v
Selected candidates
       |
       v
OpenFOAM CFD
       |
       v
Model correction / surrogate update
       |
       v
Pareto Frontier + Robustness Analysis
```

The loop is iterative. Every simulation must produce machine-readable data and become part of an auditable design history.

---

# 8. Fidelity Hierarchy

AETHER must not run expensive CFD for every candidate.

## Fidelity 0 - Reduced-order

Used for thousands of evaluations.

Includes:

- atmospheric model;
- 3-DOF trajectory;
- analytical/empirical aerodynamic approximation;
- Sutton-Graves-type stagnation heating;
- 1-D transient TPS conduction;
- simple structural proxies.

Typical runtime target: milliseconds to seconds per trajectory/design.

## Fidelity 1 - OpenFOAM CFD

Used for selected geometries and operating points.

Purposes:

- estimate aerodynamic coefficients;
- pressure distribution;
- shock structure;
- validate/correct reduced-order aerodynamic assumptions;
- create aerodynamic response surfaces.

The project should standardize on **OpenFOAM v2606** for reproducibility.

OpenFOAM must not be treated as a magical "hypersonic truth machine." Solver physics, thermochemistry and validity must be stated.

## Fidelity 2 - Selected higher-fidelity validation

Only if schedule and computational resources permit, use a more physically appropriate high-temperature model or published benchmark for a small number of final cases.

This is a validation layer, not a new research branch.

AETHER succeeds without Fidelity 2 if Fidelity 0 and Fidelity 1 are rigorously validated and limitations are explicit.

---

# 9. Phase 0 - Reproducible Research Environment

Before physics development:

- initialize Git repository;
- define Python package structure;
- pin dependencies;
- establish tests with pytest;
- establish linting/formatting;
- establish structured logging;
- define configuration files in YAML;
- define run metadata;
- create deterministic random seeds;
- define units policy;
- create experiment database;
- create automatic plots/reports.

Every run must record:

- run ID;
- Git commit;
- date/time;
- configuration;
- solver/model version;
- mesh ID if CFD;
- convergence status;
- input vector;
- output metrics;
- warnings;
- constraint status.

### Gate G0

The repository installs cleanly, tests run, and a sample experiment is reproducible.

---

# 10. Phase 1 - Atmospheric Model

Implement:

\[
\rho(h),\ T(h),\ p(h),\ a(h),\ \mu(h)
\]

Use a documented standard-atmosphere model in its valid range.

Required tests:

- sea-level values;
- 10 km;
- 30 km;
- 50 km;
- 80 km;
- upper-atmosphere behavior;
- monotonicity where appropriate.

The software must warn when extrapolating outside a model's reliable range.

### Output

A reusable atmosphere API and plots of density, pressure, temperature and speed of sound versus altitude.

### Gate G1A

Atmospheric values agree with reference data within documented tolerances.

---

# 11. Phase 2 - Re-entry Trajectory Solver

Build a baseline point-mass 3-DOF entry solver.

Minimum state:

\[
X=[h,V,\gamma,s]
\]

with equations including:

\[
\dot h=V\sin\gamma
\]

\[
\dot V=-\frac{D}{m}-g\sin\gamma
\]

\[
D=\frac{1}{2}\rho V^2 C_DA
\]

and appropriate flight-path-angle/range dynamics.

Use a robust ODE integrator such as SciPy `solve_ivp`.

### Required outputs

- altitude vs time;
- velocity vs time;
- Mach vs time;
- flight-path angle;
- dynamic pressure;
- drag;
- deceleration/g-load;
- kinetic energy;
- downrange if modeled.

### Event handling

Terminate or flag:

- ground intersection;
- invalid atmospheric state;
- numerical divergence;
- excessive g;
- excessive dynamic pressure;
- terminal-condition achievement.

### Verification

Use simplified limiting cases where analytical behavior is available.

### Gate G1B

Trajectory integration is stable, convergent with time-step/tolerance refinement, and physically plausible.

---

# 12. Phase 3 - Engineering Aerothermal Heating

Implement a Sutton-Graves-type stagnation heating model.

Canonical interface:

```python
heat_flux_sutton_graves(
    density,
    velocity,
    nose_radius,
    coefficient,
    units=...
)
```

The implementation must document units and coefficient source.

### Physics sanity tests

Within the model:

\[
V\uparrow \Rightarrow q''\uparrow
\]

\[
\rho\uparrow \Rightarrow q''\uparrow
\]

\[
R_n\uparrow \Rightarrow q''\downarrow
\]

### Integrated heat load

Compute:

\[
Q_{ext}=\int q''(t)\,dt
\]

This is not the same as TPS penetration but is an important diagnostic.

### Gate G2

The implementation reproduces selected published/reference calculations to a documented tolerance.

---

# 13. Phase 4 - Transient TPS Solver

Build a 1-D finite-difference or finite-volume transient conduction model.

General equation:

\[
\rho c_p \frac{\partial T}{\partial t}
=
\frac{\partial}{\partial x}
\left(k\frac{\partial T}{\partial x}\right)
\]

Support:

- one or more material layers;
- material density;
- heat capacity;
- conductivity;
- layer thickness;
- surface heat-flux boundary condition;
- inner boundary condition;
- temperature-dependent properties as a later refinement.

### Required outputs

\[
T(x,t)
\]

including:

- surface temperature;
- shallow TPS temperature;
- mid-depth temperature;
- deep TPS temperature;
- bondline temperature.

### Verification cases

- semi-infinite solid where applicable;
- constant heat-flux slab;
- steady-state conduction limit;
- mesh refinement;
- time-step refinement;
- energy balance.

### Gate G3

TPS solver passes analytical/numerical benchmark tests and demonstrates grid/time-step convergence.

---

# 14. Formalizing the Burn-vs-Bake Problem

AETHER must quantify at least the following:

## Metric M1 - Peak external heat flux

\[
M_1=q''_{\max}
\]

## Metric M2 - Integrated external heat load

\[
M_2=\int_0^{t_f}q''(t)\,dt
\]

## Metric M3 - Maximum bondline temperature

\[
M_3=T_{\mathrm{bond,max}}
\]

## Metric M4 - Bondline thermal exposure

One candidate:

\[
M_4=
\int_0^{t_f}
\max(0,T_{\mathrm{bond}}-T_{ref})\,dt
\]

## Metric M5 - Thermal penetration depth

Maximum depth at which temperature exceeds a selected engineering threshold.

The project must investigate which penetration metric is most stable and physically interpretable.

### Milestone 1 experiment

Find two valid trajectories A and B such that:

\[
q''_{\max,B}<q''_{\max,A}
\]

but:

\[
T_{\mathrm{bond,max,B}}>T_{\mathrm{bond,max,A}}
\]

or B has a worse cumulative penetration metric.

This is the first major capstone result.

---

# 15. Phase 5 - Baseline Capsule Geometry

Build a parameterized blunt-body/capsule geometry.

Candidate design variables:

\[
X_g=[
R_n,
D,
R_s,
\theta_s,
L
]
\]

where appropriate.

Start axisymmetric.

Requirements:

- geometry reproducible from parameters;
- exportable to STL;
- watertight mesh;
- design bounds;
- geometry validity checks;
- automatic naming/versioning.

Do not allow the optimizer to create physically invalid geometries.

---

# 16. Phase 6 - OpenFOAM CFD Workflow

Standardize on OpenFOAM v2606.

Build a reproducible case-generation pipeline:

```text
parameter vector
 -> geometry
 -> computational domain
 -> mesh
 -> checkMesh
 -> solver setup
 -> run
 -> convergence checks
 -> post-process
 -> extract metrics
 -> archive
```

### Initial CFD objective

Do not begin by attempting complete nonequilibrium re-entry chemistry.

First establish a defensible compressible aerodynamic baseline for selected conditions.

Extract:

- drag coefficient;
- lift coefficient if relevant;
- pressure coefficient;
- surface pressure;
- shock location/structure;
- residual history;
- force convergence.

### Solver validity

Every CFD report must state:

- governing equations;
- gas model;
- turbulence/laminar assumption;
- thermophysical model;
- Mach number;
- Reynolds number if meaningful;
- boundary conditions;
- mesh statistics;
- convergence criteria;
- known limitations.

---

# 17. CFD Validation

## V1 - Mesh independence

At minimum:

- coarse;
- medium;
- fine.

Compare:

\[
C_D
\]

shock stand-off distance if measurable, and selected surface quantities.

Use Grid Convergence Index if practical.

## V2 - Reference benchmark

Choose a published sphere/blunt-body/capsule benchmark with comparable conditions.

Compare numerical outputs with reference values.

## V3 - Numerical convergence

Require:

- bounded residual behavior;
- stabilized integrated forces;
- absence of nonphysical fields;
- repeatability.

## V4 - Model-form limitation

Explicitly document where ideal/perfect-gas CFD becomes insufficient for actual orbital-entry aerothermodynamics.

### Gate G4

OpenFOAM results are not admitted to the optimization database until validation criteria are met.

---

# 18. Phase 7 - Aerodynamic Response Surface

CFD is too expensive to run inside every trajectory time step.

Create response surfaces such as:

\[
C_D=f(M,\alpha,X_g)
\]

and, if justified:

\[
C_L=f(M,\alpha,X_g)
\]

Use selected CFD design points.

Possible interpolation/surrogate methods:

- multilinear interpolation;
- radial basis functions;
- Gaussian Process;
- polynomial response surface.

Use cross-validation.

Record uncertainty.

The trajectory solver queries the response surface during integration.

---

# 19. Phase 8 - Coupled Multidisciplinary Model

The full low/medium-fidelity chain becomes:

```text
Geometry
  |
  v
Aerodynamic model / CFD surrogate
  |
  v
Trajectory
  |
  v
rho(t), V(t), Rn
  |
  v
Aerothermal heating
  |
  v
q''(t)
  |
  v
TPS transient conduction
  |
  v
T(x,t)
  |
  v
O1 metrics + constraints
```

This coupled model is the computational heart of AETHER.

### Gate G5

A change in geometry must propagate consistently through aerodynamics, trajectory, heating and TPS response.

---

# 20. Design and Performance Vectors

## Design vector

A canonical design vector may be:

\[
X=[
R_n,D,R_s,\theta_s,L,\gamma_0,\alpha
]
\]

Only include variables that are actually modeled and justified.

## Performance vector

\[
Y=[
C_D,
C_L,
q''_{\max},
Q_{ext},
T_{\mathrm{surface,max}},
T_{\mathrm{bond,max}},
Q_{\mathrm{penetration}},
g_{\max},
q_{dyn,\max},
t_{entry}
]
\]

Every candidate must have a unique design ID and machine-readable \(X,Y\) record.

---

# 21. Phase 9 - Sensitivity and Design-of-Experiments

Before AI optimization, understand the design space.

Use:

- one-at-a-time sweeps for intuition;
- Latin Hypercube Sampling;
- Sobol or Morris analysis if practical.

Investigate sensitivity to:

- nose radius;
- diameter/reference area;
- entry flight-path angle;
- angle of attack if modeled;
- ballistic coefficient;
- TPS thickness;
- TPS conductivity;
- vehicle mass.

Produce ranked sensitivity results.

This prevents the AI agent from operating as an opaque trial-and-error system.

---

# 22. Phase 10 - Multi-objective Optimization

The primary final output is a Pareto frontier.

At minimum compare:

\[
q''_{\max}
\]

against:

\[
T_{\mathrm{bond,max}}
\]

with other constraints encoded.

A useful 3-objective formulation is:

\[
\min
[
q''_{\max},
T_{\mathrm{bond,max}},
Q_{\mathrm{penetration}}
]
\]

subject to hard constraints.

Candidate algorithms:

- NSGA-II;
- differential evolution;
- Bayesian multi-objective optimization.

The project must not call one point "the optimum" without explaining the engineering trade.

---

# 23. Phase 11 - AI-Guided Engineering Loop

The AI component must be rigorous and auditable.

The AI agent receives structured results, not screenshots.

Example input:

```json
{
  "design_id": "D0042",
  "geometry": {},
  "trajectory": {},
  "thermal": {},
  "constraints": {},
  "uncertainty": {},
  "comparison_to_parent": {}
}
```

The agent returns:

1. observation;
2. numerical evidence;
3. likely physical mechanism;
4. trade-off;
5. next candidate;
6. reason for candidate;
7. expected effect;
8. uncertainty/risk.

Example:

> Increasing nose radius reduced peak heating by 9.1%, but entry duration increased and bondline maximum fell only 1.3%. Test a modestly steeper entry flight-path angle while retaining the larger radius to determine whether the peak-flux benefit can be preserved while shortening thermal exposure.

Every proposal must be traceable to prior data.

---

# 24. Compare AI Against Conventional Optimization

AETHER should not assume AI is superior.

Run comparable optimization budgets.

For example:

- 100 candidate evaluations by differential evolution;
- 100 by Bayesian optimization;
- 100 proposed by the AI engineering agent;
- hybrid adaptive-fidelity strategy.

Compare:

- best feasible Pareto hypervolume;
- number of CFD calls;
- number of failed candidates;
- wall-clock/CPU cost;
- convergence speed;
- diversity of designs.

This converts "AI-assisted" from marketing language into a testable computational research question.

---

# 25. Phase 12 - Surrogate-Assisted Optimization

After sufficient validated data:

\[
\hat Y=f(X)
\]

Candidate surrogate models:

- Gaussian Process;
- Random Forest;
- Gradient Boosting.

Neural networks are unnecessary unless the dataset justifies them.

Report:

- training error;
- validation error;
- test error;
- RMSE;
- MAE;
- uncertainty/calibration where available.

Never use a surrogate outside its training domain without a warning.

---

# 26. Adaptive-Fidelity Agent

A major refinement is allowing the system to choose not only the next design but the required fidelity.

Concept:

```text
candidate
   |
   +-- clearly poor/uncertain-low-value --> Fidelity 0
   |
   +-- promising --> OpenFOAM CFD
   |
   +-- Pareto candidate --> repeated/refined validation
```

The decision policy should use:

- predicted performance;
- model uncertainty;
- distance from known data;
- proximity to Pareto frontier;
- computational cost.

Research question:

> Can adaptive fidelity achieve comparable design quality with fewer CFD evaluations?

---

# 27. Phase 13 - Uncertainty Quantification

Nominal optimization is insufficient.

Represent uncertainties such as:

\[
\rho(h)(1+\delta_\rho)
\]

\[
m+\delta_m
\]

\[
\gamma_0+\delta_\gamma
\]

\[
k_{TPS}+\delta_k
\]

and numerical/model uncertainties.

Use Monte Carlo or Latin Hypercube uncertainty propagation.

For final designs report distributions:

\[
P(T_{\mathrm{bond,max}}>T_{\mathrm{allow}})
\]

\[
P(g_{\max}>g_{\mathrm{allow}})
\]

and confidence/credible intervals.

---

# 28. Robust Optimization

A final design should perform well under uncertainty.

A possible robust objective is:

\[
J_{robust}=E[J]+\lambda\sigma_J
\]

while retaining hard probability-of-failure constraints.

Compare:

- nominal optimum;
- robust optimum.

A nominally superior design that is extremely sensitive to atmosphere or entry-angle errors may be a worse engineering choice.

---

# 29. Structural and Stability Proxies

The capstone is not a flight structural-certification project.

Use defensible proxy constraints:

- maximum dynamic pressure;
- maximum deceleration;
- surface pressure;
- center-of-pressure/center-of-mass stability proxy if geometry permits;
- geometric manufacturability;
- TPS temperature limits.

Any structural-stress estimate must be labeled preliminary unless supported by a dedicated validated FEA model.

---

# 30. Physical Experiment - Focused Thermal Validation

Use the 3D printer for one high-quality experiment directly tied to the research question.

## Objective

Demonstrate and validate transient thermal penetration through an instrumented TPS-like stack under controlled, repeatable heating.

## Test article

A 3D-printed holder containing interchangeable thermal coupons/layers.

Embed thermocouples at:

- exposed surface or near-surface;
- shallow depth;
- mid depth;
- deep layer;
- bondline/back face.

Record:

\[
T(x,t)
\]

## Experiment matrix

Vary controlled heating histories with approximately equal or deliberately different:

- peak heat flux;
- duration;
- integrated energy.

Create at least one pair where:

- Test A has a higher peak and shorter duration;
- Test B has a lower peak and longer duration.

Determine whether Test B can produce greater deep/bondline heating.

This directly demonstrates the burn-vs-bake concept without pretending to reproduce hypersonic entry.

---

# 31. Experimental Instrumentation

Minimum:

- suitable thermocouples for safe bench temperatures;
- multichannel thermocouple interface/data logger;
- cold-junction compensation;
- timestamped acquisition;
- calibrated/characterized heat source;
- known coupon geometry;
- repeatable sensor locations.

Perform:

- sensor sanity checks;
- repeatability runs;
- uncertainty estimates;
- energy/input characterization where possible.

Do not use dangerous temperatures or equipment beyond appropriate supervised laboratory practice.

---

# 32. Experiment-to-Model Comparison

Use the same imposed heat-flux/time history as TPS solver input.

Compare measured:

\[
T_i(t)
\]

with predicted:

\[
\hat T_i(t)
\]

at each thermocouple depth.

Report:

- RMSE;
- peak-temperature error;
- time-to-peak error;
- residual plots.

Adjust uncertain material properties only through a documented calibration procedure.

Keep a separate validation dataset that is not used for calibration.

---

# 33. Validation Matrix

Maintain `VALIDATION_MATRIX.md`.

Minimum rows:

| Model | Verification | Validation | Acceptance |
|---|---|---|---|
| Atmosphere | unit/reference checks | standard atmosphere | tolerance documented |
| Trajectory | convergence/limiting cases | published/simple entry case | stable and plausible |
| Sutton-Graves | dimensional/trend tests | NASA reference calculations | documented error |
| TPS | analytical slab cases | thermal coupon experiment | error bounds |
| CFD | residual/mesh convergence | published blunt-body benchmark | documented error |
| Surrogate | cross-validation | held-out CFD cases | RMSE threshold |
| Optimization | deterministic tests | repeated runs | repeatable frontier |

No subsystem is considered "done" merely because it runs.

---

# 34. Required Negative-Results Log

Maintain `docs/negative_results.md`.

Record:

- hypotheses that fail;
- numerical approaches that fail;
- parameter regions that are infeasible;
- surrogate failures;
- CFD convergence failures;
- assumptions shown to be inadequate.

A negative result is scientifically useful.

The project must not be engineered to make every hypothesis succeed.

---

# 35. Engineering Notebook

Maintain dated entries containing:

1. question;
2. hypothesis;
3. model/design change;
4. expected result;
5. actual result;
6. evidence;
7. interpretation;
8. next action.

This creates an auditable record of student reasoning and AI assistance.

---

# 36. Student Ownership and AI Transparency

AI can assist with:

- code generation;
- debugging;
- simulation automation;
- literature organization;
- optimization proposals;
- data analysis;
- documentation.

But the student must understand and be able to defend:

- governing equations;
- boundary conditions;
- numerical methods;
- solver choices;
- mesh convergence;
- heating correlation;
- TPS model;
- optimization objectives;
- uncertainty analysis;
- every major conclusion.

Maintain an `AI_USAGE.md` file describing where AI was used.

The project should demonstrate engineering judgment, not prompt-writing ability.

---

# 37. Connection to Prior F1 STEM Racing Work

The capstone intentionally extends an established workflow.

## F1 workflow

\[
Geometry
\rightarrow
CFD
\rightarrow
performance
\rightarrow
AI-assisted analysis
\rightarrow
redesign
\rightarrow
validation
\]

## AETHER workflow

\[
Capsule\ Geometry
\rightarrow
CFD
\rightarrow
Trajectory
\rightarrow
Aerothermal\ Heating
\rightarrow
TPS
\rightarrow
Multi-objective\ Optimization
\rightarrow
AI-guided\ Redesign
\rightarrow
Validation
\]

The intellectual continuity is **closed-loop computational engineering optimization**.

The capstone should describe this continuity without overstating that F1 and hypersonic re-entry are physically equivalent.

---

# 38. Repository Structure

```text
aether/
├── README.md
├── LICENSE
├── CITATION.cff
├── PROJECT_STATUS.md
├── ROADMAP.md
├── ARCHITECTURE.md
├── ASSUMPTIONS.md
├── VALIDATION_MATRIX.md
├── AI_USAGE.md
├── pyproject.toml
├── requirements.txt
├── configs/
│   ├── atmosphere/
│   ├── vehicle/
│   ├── trajectory/
│   ├── tps/
│   ├── cfd/
│   └── optimization/
├── src/aether/
│   ├── atmosphere/
│   ├── trajectory/
│   ├── heating/
│   ├── tps/
│   ├── aerodynamics/
│   ├── geometry/
│   ├── cfd/
│   ├── surrogate/
│   ├── optimization/
│   ├── uncertainty/
│   ├── scoring/
│   └── utils/
├── cfd/
│   ├── templates/
│   ├── validation/
│   ├── generated/
│   └── postprocessing/
├── geometry/
│   ├── parametric/
│   ├── stl/
│   └── printable/
├── data/
│   ├── reference/
│   ├── raw/
│   ├── processed/
│   └── optimization/
├── experiments/
│   └── thermal_coupon/
├── tests/
├── notebooks/
├── scripts/
├── results/
├── reports/
│   ├── iterations/
│   ├── milestones/
│   └── final/
└── docs/
    ├── theory/
    ├── validation/
    ├── engineering_notebook/
    ├── negative_results.md
    └── paper/
```

---

# 39. Canonical Configuration

Use YAML, not hard-coded constants.

Example:

```yaml
vehicle:
  mass_kg: 5000.0
  diameter_m: 4.0
  nose_radius_m: 2.0
  reference_area_m2: null

entry:
  initial_altitude_m: 120000.0
  initial_velocity_m_s: 7800.0
  flight_path_angle_deg: -6.0

tps:
  layers:
    - name: layer_1
      thickness_m: 0.05
      density_kg_m3: null
      conductivity_w_mk: null
      heat_capacity_j_kgk: null

constraints:
  max_g: null
  max_dynamic_pressure_pa: null
  max_bondline_temperature_k: null

numerics:
  rtol: 1.0e-8
  atol: 1.0e-10
```

Unknown values must remain explicit `null` until justified.

Never invent engineering limits.

---

# 40. Data Integrity

Every run gets:

- immutable run ID;
- parent design ID;
- configuration snapshot;
- Git commit;
- model versions;
- status;
- metrics;
- warnings.

Failed runs remain in the database but are flagged.

Never silently discard inconvenient data.

---

# 41. Computational Acceptance Gates

## G0 - software foundation
All tests pass and experiment metadata is reproducible.

## G1 - trajectory
Trajectory solver verified.

## G2 - heating
Heating correlation validated against reference calculations.

## G3 - TPS
Thermal solver verified and validated.

## G4 - CFD
OpenFOAM mesh/convergence/reference validation complete.

## G5 - coupled model
Geometry changes propagate through full model.

## G6 - baseline optimization
A reproducible Pareto frontier exists.

## G7 - AI/surrogate
AI/surrogate predictions are benchmarked against conventional methods.

## G8 - uncertainty
Finalists evaluated under uncertainty.

## G9 - physical experiment
Thermal coupon model-to-experiment comparison complete.

## G10 - final capstone
Paper, code, data and presentation are reproducible.

Do not skip failed gates.

---

# 42. Suggested Project Timeline

## Weeks 1-2
Repository, atmosphere, trajectory, tests.

## Weeks 3-4
Heating model, TPS solver, verification.

## Week 5
Burn-vs-bake demonstration.

## Weeks 6-8
Parametric capsule and OpenFOAM baseline.

## Weeks 9-10
CFD validation and response surfaces.

## Weeks 11-12
Coupled multidisciplinary model.

## Weeks 13-15
DOE, sensitivity and conventional optimization.

## Weeks 16-18
Surrogate and AI-guided optimization.

## Weeks 19-20
Adaptive fidelity and comparison of optimizers.

## Weeks 21-22
Uncertainty and robust optimization.

## Weeks 23-24
3D-printed thermal experiment.

## Weeks 25-26
Final validation, paper, poster, video and repository cleanup.

The schedule can be compressed by completing a strong validated core before optional sophistication.

---

# 43. Minimum Viable Capstone

If application deadlines arrive early, the minimum high-quality version is:

1. validated trajectory model;
2. Sutton-Graves heating;
3. validated transient TPS model;
4. quantitative burn-vs-bake result;
5. parametric geometry;
6. at least one validated OpenFOAM CFD family;
7. Pareto optimization;
8. public/reproducible repository;
9. concise technical paper.

This is preferable to a larger unfinished system.

---

# 44. Stretch Capstone

If time permits:

- surrogate-assisted optimization;
- adaptive-fidelity agent;
- robust optimization;
- thermal physical experiment;
- automated report generation;
- interactive results explorer.

These deepen the core question without changing project scope.

---

# 45. Key Figures for Final Paper

Automatically produce:

1. capsule geometry and parameter definitions;
2. atmospheric profiles;
3. baseline trajectory \(V(h)\);
4. dynamic pressure vs time;
5. heat flux vs time;
6. TPS temperature-depth/time contour;
7. bondline temperature vs time;
8. burn-vs-bake comparison;
9. CFD pressure/Mach field;
10. mesh-convergence plot;
11. aerodynamic response surface;
12. sensitivity ranking;
13. Pareto frontier;
14. optimizer convergence comparison;
15. surrogate predicted-vs-actual plot;
16. uncertainty distributions;
17. nominal vs robust design;
18. experimental thermocouple traces;
19. experiment-vs-model residuals;
20. final baseline-vs-optimized comparison.

---

# 46. Final Comparison

The final result must include at least:

| Metric | Baseline | Peak-Heat Optimized | Joint O1 Optimized | Robust O1 |
|---|---:|---:|---:|---:|
| Peak heat flux | | | | |
| Integrated external heat load | | | | |
| Peak surface temperature | | | | |
| Peak bondline temperature | | | | |
| Penetration metric | | | | |
| Maximum g | | | | |
| Maximum dynamic pressure | | | | |
| Entry duration | | | | |
| Feasible? | | | | |

The most important comparison is between **Peak-Heat Optimized** and **Joint O1 Optimized**.

---

# 47. Final Research Paper Structure

1. Abstract  
2. Introduction  
3. Background and related work  
4. Research question and hypotheses  
5. Governing equations  
6. Atmospheric and trajectory model  
7. Aerothermal heating model  
8. TPS transient thermal model  
9. Parametric geometry and CFD  
10. Verification and validation  
11. Multidisciplinary coupling  
12. Design-of-experiments and sensitivity  
13. Multi-objective optimization  
14. Surrogate and AI-guided design methodology  
15. Adaptive-fidelity strategy  
16. Uncertainty and robust optimization  
17. Physical thermal experiment  
18. Results  
19. Discussion  
20. Limitations  
21. Negative results  
22. Conclusions  
23. Future work  
24. References  
25. Reproducibility appendix

---

# 48. Deliverables

## D1 - Public/reproducible code repository
All source, configs, tests and documentation.

## D2 - Validated trajectory solver

## D3 - Aerothermal heating module

## D4 - Transient TPS solver

## D5 - Parametric capsule generator

## D6 - Validated OpenFOAM workflow

## D7 - Coupled multidisciplinary simulator

## D8 - Multi-objective optimizer and Pareto analysis

## D9 - AI-guided/adaptive-fidelity engineering loop

## D10 - Uncertainty/robustness analysis

## D11 - 3D-printable thermal test fixture and experiment dataset

## D12 - 15-25 page technical paper

## D13 - 2-page technical poster

## D14 - 3-5 minute technical visualization/video

## D15 - Engineering notebook and negative-results log

## D16 - Reproducibility package

---

# 49. Scientific Language Rules

Use:

- "the model predicts";
- "within the assumptions tested";
- "simulation suggests";
- "the candidate reduced";
- "the hypothesis was supported/not supported";
- "the result is sensitive to";
- "higher-fidelity validation is required."

Avoid:

- "solves re-entry";
- "eliminates heating";
- "proves the safest capsule";
- "AI invented the optimal spacecraft";
- "flight ready."

---

# 50. Success Criteria

AETHER succeeds if it can defensibly answer:

> **Does optimizing only peak heat flux risk selecting a trajectory/design with worse in-depth TPS thermal exposure?**

and:

> **Can joint geometry-trajectory optimization reduce both peak heating and deep thermal penetration while satisfying entry constraints?**

and, if the AI methodology is completed:

> **Can an AI-guided adaptive-fidelity search reach comparable or better Pareto solutions with fewer expensive CFD evaluations than conventional optimization?**

The capstone succeeds even if the answer to any hypothesis is "no," provided the result is validated and reproducible.

---


# 51. Research Narrative and Signature Question

The capstone must be presented as a scientific discovery process, not as a predetermined demonstration.

The narrative is:

```text
Can peak re-entry heating be reduced?
        |
        v
Would a lower peak require longer thermal exposure?
        |
        v
Could a cooler surface trajectory heat the protected structure more deeply?
        |
        v
What should "thermally optimal re-entry" actually mean?
        |
        v
O1: jointly optimize peak heating and in-depth TPS response
        |
        v
AETHER: validated multifidelity design + trajectory optimization
```

The memorable research hook is:

> **Could a re-entry trajectory that looks cooler at the surface actually be thermally worse inside the spacecraft?**

The project must preserve evidence of how the question evolved. The engineering notebook should document changes in assumptions, failed hypotheses, unexpected results and subsequent reformulation.

---

# 52. Project-Defined Thermal Penetration Index

In addition to standard metrics, investigate whether a project-defined **Thermal Penetration Index (TPI)** provides a useful summary of in-depth thermal exposure.

A candidate family is:

\[
TPI = \int_0^{t_f}\int_0^L w(x)\max[T(x,t)-T_{safe}(x),0] \, dx\,dt
\]

This is **not** to be claimed as a new aerospace standard. The project must:

1. review literature for existing equivalent or related thermal-dose/penetration metrics;
2. define the purpose and units of each candidate TPI formulation;
3. test sensitivity to threshold and depth weighting;
4. compare TPI with peak heat flux, integrated heat load and maximum bondline temperature;
5. retain TPI only if it adds interpretable information.

If it does not add value, report that negative result.

---

# 53. Signature Counterexample

AETHER should actively search for a **validated counterexample** to the assumption that lower peak heat flux always means a thermally safer entry.

The desired form is:

\[
q''_{max,B} < q''_{max,A}
\]

while:

\[
T_{bond,max,B} > T_{bond,max,A}
\]

or B has demonstrably worse cumulative/deep thermal penetration.

The final report should express the result in a single understandable sentence, using only actual computed and validated values, for example:

> "Trajectory B reduced peak heat flux by X%, yet increased maximum bondline temperature by Y K because thermal exposure persisted for Z% longer."

Never select or tune results merely to obtain this headline. If the counterexample does not exist within the tested design space, that is itself a valid research result.

---

# 54. AI Ablation and Fair Benchmarking

The AI component must undergo an ablation study. Compare, under matched evaluation budgets where practical:

| Search method | Total evaluations | CFD calls | Feasible designs | Pareto quality/hypervolume | Compute cost |
|---|---:|---:|---:|---:|---:|
| Random or space-filling baseline | | | | | |
| NSGA-II / conventional optimizer | | | | | |
| Surrogate/Bayesian optimization | | | | | |
| AI engineering agent | | | | | |
| AI + adaptive fidelity | | | | | |

The project must not assume AI is superior. A result showing that a conventional method outperforms the AI agent is acceptable and should be reported plainly.

The research question is not "Can AI design a spacecraft?" It is:

> **Does AI-guided engineering reasoning improve search efficiency, design diversity or computational allocation relative to established optimization methods?**

---

# 55. Blind Experimental Prediction

The physical thermal experiment should culminate in a **blind prediction test**.

Procedure:

1. use initial thermal-coupon runs for instrumentation checks and model calibration;
2. reserve one or more heating histories as unseen validation cases;
3. freeze model parameters before revealing the measured validation traces;
4. generate predicted temperature histories at every thermocouple depth;
5. timestamp/archive the predictions;
6. perform the unseen experiment;
7. compare prediction with measurement.

Report:

- RMSE at each depth;
- peak-temperature error;
- time-to-peak error;
- confidence/uncertainty interval coverage;
- residuals versus time.

This separates **calibration** from **prediction** and makes the physical validation substantially stronger.

---

# 56. External Technical Review and Research Defense

Seek a qualified aerospace/thermal researcher or engineer to act as a **technical reviewer**, not as the author of the project.

Recommended reviews:

### Review R1 - Model assumptions

Challenge atmosphere, trajectory, heating and TPS assumptions.

### Review R2 - CFD and validation

Challenge solver physics, boundary conditions, mesh convergence, continuum/perfect-gas assumptions and benchmark selection.

### Review R3 - Final research defense

Challenge optimization, uncertainty, conclusions and limitations.

For every review, preserve:

- date;
- reviewer role/affiliation if permission is given;
- questions/criticisms;
- student response;
- changes made;
- unresolved limitations.

The reviewer must not write the project. The value is in demonstrating the student's ability to defend, revise and improve technical work under expert scrutiny.

---

# 57. External Scientific Evaluation

After the validated core is complete, seek appropriate external evaluation through one or more legitimate channels such as:

- student research symposium;
- engineering/science competition;
- research poster event;
- eligible aerospace/student conference track;
- appropriate preprint or student research venue.

Do not optimize the science to win an award. External evaluation is useful because independent reviewers can test whether the work is understandable, technically defensible and genuinely student-owned.

Any submission must clearly disclose AI assistance and mentorship according to the venue's rules.

---

# 58. Reproducibility by a Stranger

A clean environment should be able to reproduce the principal results from documented commands.

Target interface:

```text
make baseline
make validate
make burn-vs-bake
make optimize
make figures
```

or equivalent scripts if `make` is not portable.

At minimum a new user should be able to reproduce:

1. baseline trajectory;
2. heating validation;
3. TPS validation;
4. burn-vs-bake result;
5. CFD benchmark where OpenFOAM is installed;
6. Pareto frontier;
7. final comparison figures.

Create `REPRODUCIBILITY.md` with environment requirements, expected runtime and exact commands.

---

# 59. Admissions-Facing Research Artifacts

The research remains primary. Communication artifacts should make the work accessible without oversimplifying it.

Produce:

1. **15-25 page technical research paper** - complete scientific record;
2. **2-page technical brief** - question, method, result, validation and limitations;
3. **public/reproducible code repository** - code, data, tests and run instructions;
4. **research poster** - suitable for technical review;
5. **90-second technical explainer** - student explains the question, one key result and validation;
6. **3-5 minute technical video** - deeper method/result explanation;
7. **instrumented thermal demonstrator** - physical validation artifact.

The 90-second explanation should begin with the research question, not with software names or AI.

A strong opening is conceptually:

> "I began by asking how to reduce peak re-entry heating. But that led to a harder question: could reducing the peak keep the spacecraft hot for longer and actually increase the temperature deeper inside the heat shield?"

The exact wording should remain the student's own.

---

# 60. Student Intellectual Ownership

The central evidence of quality is the student's reasoning.

The final project must make clear that:

- AI is a tool, not the scientific author;
- OpenFOAM is a tool, not the contribution;
- optimization is a method, not the conclusion;
- the 3D printer is a validation tool, not a display prop.

The student should be able to answer, without AI assistance during a defense:

- Why is peak heat flux insufficient?
- Why does velocity appear cubed in the engineering heating correlation?
- What does the TPS diffusion timescale imply?
- What assumptions limit Sutton-Graves?
- What assumptions limit the OpenFOAM model?
- Why is mesh convergence necessary?
- What makes a Pareto solution different from a single optimum?
- How was uncertainty propagated?
- What did AI contribute, and where did it fail?
- Which result most changed the student's original intuition?

Create `docs/defense_questions.md` and periodically conduct mock defenses.

---

# 61. Continuity With Prior Computational Engineering

AETHER should be framed as a progression in engineering methodology rather than an isolated admissions project.

The continuity is:

```text
prior aerodynamic design
    -> parameterized geometry
    -> simulation
    -> quantitative comparison
    -> iterative redesign
    -> validation

AETHER
    -> coupled geometry + trajectory
    -> aerodynamics
    -> transient thermal response
    -> multi-objective optimization
    -> uncertainty
    -> physical validation
```

The scientific leap is from optimizing a relatively localized aerodynamic performance problem to managing a coupled transient aerospace system with competing objectives.

Do not overstate physical equivalence between different applications. The continuity is the **engineering method**.

---

# 62. Scope Freeze Rule

From this revision onward, technical breadth is frozen unless a new component is required to resolve a validation failure in O1.

Do **not** add new major physics subsystems for novelty.

Future effort should preferentially improve:

\[
\boxed{Validation \rightarrow Evidence \rightarrow Robustness \rightarrow External\ Scrutiny \rightarrow Communication}
\]

rather than scope.

A smaller project with defensible results is superior to a larger unfinished project.

---

# 63. Final Evaluation Standard

The strongest possible outcome is not "a high-school student ran a sophisticated re-entry simulation."

It is evidence that the student:

1. identified a non-obvious engineering question;
2. formulated falsifiable hypotheses;
3. built coupled models from first principles and documented correlations;
4. verified numerical implementation;
5. validated against independent references and physical data;
6. discovered or rejected a counterintuitive burn-vs-bake effect;
7. compared AI with established optimization rather than assuming superiority;
8. quantified uncertainty;
9. subjected the work to external technical criticism;
10. communicated limitations and negative results honestly;
11. made the work reproducible by others.

That is the standard against which every remaining project decision should be judged.

---

# 64. References and Technical Anchors

1. Sutton, K. and Graves, R. A., Jr., **A General Stagnation-Point Convective-Heating Equation for Arbitrary Gas Mixtures**, NASA TR R-376, 1971.  
   https://ntrs.nasa.gov/citations/19720003329

2. NASA Thermal Protection Materials Branch, **Design and Analysis** - description of coupled thermal/structural analysis, in-depth TPS response, thermocouple validation, thermal soak, and sizing for maximum heat-load and maximum heat-flux trajectories.  
   https://www.nasa.gov/general/thermal-protection-materials-branch-design-and-analysis/

3. OpenFOAM, **v2606 release**, June 26, 2026.  
   https://www.openfoam.com/news/main-news/openfoam-v2606

4. OpenFOAM, **current release/download documentation**.  
   https://www.openfoam.com/current-release

5. Sutton, K. and Hartung, L. C., **Equilibrium Radiative Heating Tables for Earth Entry**, NASA TM-102652, 1990.  
   https://ntrs.nasa.gov/citations/19900014359

These are starting anchors, not a complete literature review. The final capstone must add current peer-reviewed work on re-entry trajectory optimization, multidisciplinary design optimization, surrogate modeling, TPS response and uncertainty quantification.

---

# 65. Final Project Identity

**Project:** AETHER  
**Research title:** When Cooler Is Not Safer: Rethinking Atmospheric Re-entry Through Peak and Cumulative Thermal Optimization

**Technical subtitle:** AI-Guided Multifidelity Framework for Coupled Re-entry Trajectory, Aerodynamics and TPS Optimization

**One-sentence description:**

> AETHER develops and validates an AI-guided computational framework that couples capsule geometry, CFD, re-entry trajectory and transient TPS response to investigate the trade between peak atmospheric-entry heating and cumulative in-depth thermal penetration.

**Core idea:**

\[
\boxed{
\text{Do not optimize only how hot re-entry gets. Optimize how heat moves through the vehicle over the entire entry.}
}
\]

