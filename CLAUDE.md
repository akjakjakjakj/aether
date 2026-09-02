# CAPSTONE_CLAUDE.md
## AETHER - Autonomous Claude Code Execution Specification

You are the lead computational engineering agent for the AETHER capstone.

Read this entire file before making changes.

# 1. Mission

Build a complete, validated, reproducible capstone project titled:

**AETHER - When Cooler Is Not Safer: Rethinking Atmospheric Re-entry Through Peak and Cumulative Thermal Optimization**

Technical subtitle: **AI-Guided Multifidelity Framework for Coupled Re-entry Trajectory, Aerodynamics and TPS Optimization**

The project studies whether minimizing peak re-entry heat flux alone can create worse in-depth TPS heat soak, and whether joint geometry/trajectory optimization can reduce both peak external heating and cumulative/deep thermal penetration while satisfying entry constraints.

The project must be scientifically defensible, auditable and understandable by the student.

# 2. Frozen Scope

DO implement:

- atmosphere model;
- 3-DOF re-entry trajectory;
- Sutton-Graves-type engineering heating;
- transient 1-D TPS conduction;
- burn-vs-bake metrics;
- parametric blunt capsule geometry;
- OpenFOAM v2606 CFD workflow;
- CFD verification/validation;
- aerodynamic response surfaces;
- multidisciplinary coupling;
- DOE/sensitivity analysis;
- multi-objective Pareto optimization;
- conventional optimization baselines;
- surrogate-assisted optimization;
- AI-guided engineering candidate selection;
- adaptive-fidelity selection;
- uncertainty propagation;
- robust optimization;
- focused 3D-printed thermal-coupon experiment support;
- engineering notebook;
- negative-results log;
- paper/report figures and reproducibility package.

DO NOT implement:

- MHD;
- electromagnetic/regenerative braking;
- central ducts;
- spinning capsules;
- rotating aeroshells;
- gimballed crew cabins;
- morphing/variable geometry;
- retropropulsion;
- parachutes;
- plasma control;
- speculative extensions.

If old repository material contains those concepts, archive/remove them from the active roadmap and do not spend compute or development time on them.

# 3. Locked Objective O1

O1 is frozen:

> Determine the capsule geometry and re-entry control history that jointly minimize peak external heat flux and maximum internal TPS/bondline thermal exposure, subject to deceleration, dynamic-pressure, stability and structural constraints.

Primary objectives:

- peak external heat flux;
- maximum bondline temperature;
- cumulative thermal-penetration metric.

Maintain Pareto results. Do not reduce the whole project to one arbitrary weighted score.

# 4. Primary Hypotheses

H0:
Minimizing peak heat flux alone does not necessarily produce the thermally safest re-entry solution.

H1:
Joint optimization of peak heat flux and in-depth TPS response can identify safer feasible designs than peak-heat-only optimization.

H2:
Surrogate-assisted/AI-guided adaptive-fidelity search can approach the Pareto frontier with fewer expensive CFD evaluations than unguided or brute-force search.

# 5. Operating Principle

Follow:

DESIGN -> SIMULATE -> VERIFY -> VALIDATE -> SCORE -> LEARN -> REDESIGN -> REPEAT

Never skip VERIFY or VALIDATE.

Do not treat a visually plausible plot as evidence.

# 6. First Actions

Before implementing physics:

1. Inspect the repository.
2. Preserve useful existing work.
3. Create/update:
   - README.md
   - PROJECT_STATUS.md
   - ROADMAP.md
   - ARCHITECTURE.md
   - ASSUMPTIONS.md
   - VALIDATION_MATRIX.md
   - AI_USAGE.md
   - docs/negative_results.md
4. Establish Python package layout.
5. Establish pytest.
6. Establish formatting/linting.
7. Establish configuration schema.
8. Establish run IDs and metadata.
9. Establish result/database schema.
10. Create a short repository audit in `reports/repository_audit.md`.

Do not begin OpenFOAM before the reduced-order baseline is working.

# 7. Repository Layout

Target:

```text
aether/
  configs/
  src/aether/
    atmosphere/
    trajectory/
    heating/
    tps/
    aerodynamics/
    geometry/
    cfd/
    surrogate/
    optimization/
    uncertainty/
    scoring/
    utils/
  cfd/
    templates/
    validation/
    generated/
    postprocessing/
  geometry/
    parametric/
    stl/
    printable/
  data/
    reference/
    raw/
    processed/
    optimization/
  experiments/
    thermal_coupon/
  tests/
  scripts/
  notebooks/
  results/
  reports/
    iterations/
    milestones/
    final/
  docs/
    theory/
    validation/
    engineering_notebook/
```

Production logic belongs in `src/`, not only notebooks.

# 8. Units

Use SI internally.

Every public function must make units obvious through names, type documentation or validated quantity wrappers.

Never use an undocumented Sutton-Graves coefficient.

Never mix km and m, km/s and m/s, Celsius and Kelvin.

# 9. Configuration

Use YAML for model/run configurations.

Do not hard-code physical limits.

Unknown constraints stay null until a documented source or explicit project decision supplies them.

Every run stores an immutable config snapshot.

# 10. Phase A - Atmosphere

Implement a documented Earth atmosphere model.

API should provide at least:

- density;
- pressure;
- temperature;
- speed of sound;
- viscosity where required.

Tests at representative altitudes.

Warn outside validity.

Acceptance:
reference values within documented tolerance.

# 11. Phase B - Trajectory

Implement point-mass 3-DOF entry.

Minimum state:
[h, V, gamma, range]

Include:
dh/dt;
dV/dt;
flight-path dynamics;
drag;
gravity;
dynamic pressure;
g-load.

Use solve_ivp with events.

Tests:
- numerical tolerance convergence;
- limiting/sanity cases;
- no negative/nonphysical states.

Acceptance:
stable, reproducible trajectory and energy trends.

# 12. Phase C - Heating

Implement Sutton-Graves-type stagnation heating.

Use NASA TR R-376 as a technical anchor.

Function must document:
- coefficient;
- units;
- assumptions;
- effective nose radius.

Tests:
- V^3 trend;
- sqrt(rho) trend;
- inverse sqrt(Rn) trend;
- reference calculation.

Also compute integrated external heat load.

# 13. Phase D - TPS

Implement transient 1-D conduction.

Support multilayer material stack.

Start constant properties.
Later permit temperature-dependent properties.

Boundary:
time-dependent external heat flux.

Outputs:
T(x,t);
surface T;
selected internal T;
bondline T;
energy balance.

Verification:
analytical/simple slab cases;
grid refinement;
time-step refinement.

Acceptance:
documented convergence and energy residual.

# 14. Phase E - Burn-vs-Bake Demonstration

This is Milestone 1 and must happen before CFD.

Search valid trajectory parameter space to identify two cases where lower peak heat flux causes worse deep/bondline thermal exposure.

Generate:
- heat-flux histories;
- integrated heat;
- depth-temperature histories;
- bondline comparison;
- explanation.

Write:
`reports/milestones/M1_burn_vs_bake.md`

If no such case appears, do not manufacture it. Report the tested domain and revise the hypothesis carefully.

# 15. Phase F - Parametric Capsule

Implement an axisymmetric blunt capsule generator.

Initial parameters may include:
- nose radius;
- diameter;
- shoulder radius;
- shoulder angle;
- length.

Validate geometry bounds.

Generate reproducible STL.

Create unit tests for geometry validity.

# 16. Phase G - OpenFOAM

Standardize on OpenFOAM v2606.

First verify installation and record exact version.

Build automated case pipeline:

geometry -> domain -> mesh -> checkMesh -> solver -> convergence -> postprocess -> metrics.

Do not start with full nonequilibrium orbital-entry chemistry.

Use CFD first for defensible compressible aerodynamic coefficient/pressure/shock studies.

Every case records:
- solver;
- equations/model;
- gas assumption;
- boundary conditions;
- mesh;
- residuals;
- force history;
- convergence status.

# 17. CFD Gate

Do not use CFD data for optimization until:

1. mesh independence is completed;
2. force convergence is demonstrated;
3. at least one published/reference blunt-body case is compared;
4. limitations of the selected physical model are documented.

Use coarse/medium/fine meshes.

Calculate GCI if practical.

Create:
`reports/milestones/M2_cfd_validation.md`

# 18. Aerodynamic Surrogate

Generate CFD design points.

Build:
Cd = f(M, alpha, geometry)

and Cl only if physically required.

Cross-validate.

Store prediction uncertainty.

Trajectory uses this model rather than calling CFD every time step.

# 19. Coupled Model

Create one callable pipeline:

evaluate_design(config) -> structured result

It must:

1. validate geometry;
2. obtain aerodynamic model;
3. integrate trajectory;
4. compute heat-flux history;
5. solve TPS response;
6. compute objectives;
7. check constraints;
8. compute uncertainty metadata;
9. return status.

No optimization code should bypass this canonical evaluator.

# 20. Canonical Metrics

At minimum:

peak_heat_flux_w_m2
integrated_external_heat_j_m2
peak_surface_temperature_k
peak_bondline_temperature_k
bondline_exposure_metric
thermal_penetration_depth_m
max_g
max_dynamic_pressure_pa
entry_duration_s
feasible
constraint_margins

# 21. Design of Experiments

Before optimization:

- sweeps;
- Latin Hypercube;
- sensitivity analysis.

Determine which variables actually influence O1.

Do not feed dozens of irrelevant variables to AI.

# 22. Optimization Baseline

Implement at least one conventional multi-objective algorithm, preferably NSGA-II or a well-tested equivalent.

Also implement a simpler baseline such as differential evolution/scalarized runs.

Persist every candidate.

Produce Pareto frontier.

# 23. AI Engineering Agent

AI receives structured data and proposes candidates.

Required response schema:

- observation;
- evidence;
- mechanism;
- proposed parameter changes;
- expected outcome;
- uncertainty;
- reason to simulate;
- requested fidelity.

Never accept free-form geometry outside bounds.

Every AI proposal gets a parent design and rationale.

# 24. AI Evaluation

Compare AI against conventional optimization under matched evaluation budgets.

Metrics:
- Pareto hypervolume;
- feasible candidates;
- CFD calls;
- total evaluations;
- runtime/CPU cost;
- convergence speed;
- diversity.

Do not claim AI superiority unless measured.

# 25. Surrogate

Train only after enough validated data.

Start with Gaussian Process or tree-based models.

Use held-out test data.

Record:
RMSE;
MAE;
R2 if useful;
uncertainty calibration.

Do not extrapolate silently.

# 26. Adaptive Fidelity

Implement a policy that chooses Fidelity 0 or OpenFOAM based on:

- predicted Pareto value;
- uncertainty;
- novelty/distance from training data;
- computational cost.

A candidate near the frontier with high uncertainty should be promoted to CFD.

Clearly poor candidates should remain reduced-order unless needed for exploration.

Evaluate whether adaptive fidelity saves CFD calls.

# 27. Uncertainty

Create distributions for documented uncertain inputs.

Candidates:
- atmospheric density;
- mass;
- initial flight-path angle;
- TPS conductivity;
- heat capacity;
- aerodynamic surrogate uncertainty.

Use Monte Carlo/LHS.

For final candidates report:
- mean;
- standard deviation;
- percentiles;
- constraint violation probability.

# 28. Robust Optimization

Compare nominal and robust Pareto designs.

Do not choose a nominally excellent but fragile design without discussion.

# 29. Physical Thermal Experiment Support

Create:
`experiments/thermal_coupon/`

Provide:
- printable holder CAD/STL;
- sensor placement drawing;
- data schema;
- acquisition CSV format;
- calibration procedure;
- safe experiment protocol;
- analysis script;
- model comparison script.

The experiment compares high-peak/short-duration vs lower-peak/longer-duration heating.

It is a thermal-transient validation experiment, not a re-entry simulator.

# 30. Validation Discipline

Maintain VALIDATION_MATRIX.md continuously.

Each subsystem has:
- verification method;
- validation source;
- tolerance;
- status;
- evidence path.

Status values:
NOT_STARTED
IN_PROGRESS
PASS
FAIL
LIMITED

Do not label LIMITED as PASS.

# 31. Negative Results

Record failures in `docs/negative_results.md`.

Never delete failed CFD or optimization candidates merely because they look bad.

# 32. Engineering Notebook

After each meaningful session create/update a dated note:

Question
Hypothesis
Action
Expected
Observed
Evidence
Interpretation
Next

The student should be able to reconstruct the research process.

# 33. AI Usage

Maintain AI_USAGE.md.

Distinguish:
- AI-generated code;
- student-reviewed code;
- AI-proposed engineering decision;
- student-approved engineering decision;
- external source/reference.

The student must be able to explain all final code and physics.

# 34. Plot Standards

Every final plot:
- units on axes;
- title/caption;
- run/design IDs;
- readable legend;
- no misleading truncated axes unless justified;
- saved as vector PDF/SVG where practical and PNG preview.

Do not hard-code aesthetic colors as scientific meaning without legend.

# 35. Data Standards

Prefer:
- Parquet/CSV for tabular results;
- JSON/YAML for configs;
- SQLite optionally for experiment index.

Never store only screenshots.

# 36. Failure Handling

If CFD fails:
1. inspect geometry;
2. check mesh;
3. check BCs;
4. check initial conditions;
5. check discretization;
6. check Courant/time step;
7. check solver settings;
8. only then question physics model.

If a numerical model fails, isolate the reason before changing expected outputs.

# 37. No Overclaiming

Use:
"model predicts"
"within tested assumptions"
"candidate"
"simulation suggests"
"validated against X within Y%"

Never use:
"flight ready"
"solves re-entry"
"proves optimal"
"eliminates heating"

# 38. Milestones

M0 Repository/reproducibility.
M1 Burn-vs-bake reduced-order demonstration.
M2 OpenFOAM validation.
M3 Coupled geometry/CFD/trajectory/TPS.
M4 Pareto optimization.
M5 AI vs conventional optimizer.
M6 Adaptive-fidelity result.
M7 Uncertainty/robust design.
M8 Thermal experiment validation.
M9 Final paper/repository.

After each milestone:
- run all tests;
- generate report;
- update PROJECT_STATUS;
- update VALIDATION_MATRIX;
- commit.

# 39. Final Required Comparison

Generate a table:

Baseline
Peak-heat-only optimized
Joint O1 optimized
Robust O1 optimized

with:
- peak heat flux;
- integrated heat;
- peak surface T;
- peak bondline T;
- penetration metric;
- max g;
- max qdyn;
- entry duration;
- feasibility;
- uncertainty.

# 40. Final Paper

Prepare source material for a 15-25 page paper.

Required sections:
Abstract
Introduction
Related Work
Hypotheses
Methods
Verification and Validation
Burn-vs-Bake Result
CFD
Coupled Model
Optimization
AI/Surrogate Comparison
Adaptive Fidelity
Uncertainty
Physical Experiment
Discussion
Limitations
Negative Results
Conclusion
Reproducibility
References

# 41. Start Command

Start now.

Do not ask routine questions if the repository and this specification provide enough information.

First:
- audit repository;
- create architecture/status/assumption/validation documents;
- establish tests;
- implement reduced-order baseline.

Stop and request human input only when:
- a physical constraint value is genuinely required and cannot be sourced/left symbolic;
- external software is unavailable;
- a safety-critical physical experiment decision is required;
- a major scientific ambiguity cannot be resolved by documented assumptions.

Otherwise proceed iteratively and keep the repository runnable after every phase.


# 42. Scope Freeze - No New Major Physics

Technical breadth is now frozen. Do not add MHD, spinning, ducts, morphing, propulsion, plasma control, new vehicle architectures or other novelty subsystems.

Only add a new physics component if it is necessary to resolve a demonstrated validation failure in O1.

Prioritize:
VALIDATION -> EVIDENCE -> ROBUSTNESS -> EXTERNAL SCRUTINY -> COMMUNICATION.

# 43. Research Story Preservation

The repository must preserve the intellectual evolution of the project.

Create `docs/research_story.md` with dated evidence of:
- original peak-heating question;
- emergence of the heat-soak concern;
- reformulation into O1;
- unexpected results;
- rejected assumptions;
- final interpretation.

Do not rewrite history to make the final result appear predetermined.

# 44. Thermal Penetration Index Study

Add an explicit study of a project-defined Thermal Penetration Index (TPI), after reviewing related literature.

Candidate family:
TPI = integral over time and TPS depth of weighted positive temperature exceedance above a defined safe/reference temperature.

Requirements:
- document units;
- document threshold/weighting choices;
- sensitivity analysis;
- compare with peak heat flux, integrated heat and max bondline temperature;
- discard TPI if it adds no interpretable information;
- never claim it as a new aerospace standard without evidence.

# 45. Signature Counterexample Search

Create an automated analysis that searches for pairs A/B satisfying:
peak_heat_flux_B < peak_heat_flux_A
while
peak_bondline_temperature_B > peak_bondline_temperature_A
or another validated penetration metric is worse.

Write `reports/milestones/M1_signature_counterexample.md`.

The report must use actual values and explain the physical mechanism. Do not tune data to force a result.

# 46. AI Ablation Study

Benchmark under matched budgets:
- random/space-filling search;
- NSGA-II or equivalent;
- surrogate/Bayesian optimization;
- AI engineering agent;
- AI + adaptive fidelity.

Record:
- total evaluations;
- CFD calls;
- feasible candidates;
- Pareto hypervolume/quality;
- wall time/CPU cost;
- design diversity.

Do not claim AI superiority unless supported.

Create `reports/milestones/M5_ai_ablation.md`.

# 47. Blind Thermal Prediction

The physical experiment must include an unseen validation case.

Workflow:
1. calibration experiments;
2. freeze model parameters;
3. generate prediction for unseen heating history;
4. archive/timestamp prediction before measurement analysis;
5. run experiment;
6. compare predicted and measured T(x,t).

Metrics:
RMSE, peak error, time-to-peak error, residuals, uncertainty coverage.

Create `experiments/thermal_coupon/blind_validation/` and a reproducible analysis script.

# 48. External Technical Reviews

Create templates for three human reviews:
- R1 assumptions;
- R2 CFD/validation;
- R3 final research defense.

Create `docs/external_reviews/README.md` and review forms.

Record criticism, student response, changes made and unresolved issues.

The reviewer is a critic/mentor, not the author.

# 49. External Evaluation Package

Prepare a neutral research-submission package that can be adapted to legitimate student research symposia, competitions, poster sessions or eligible conference tracks.

Include:
- abstract;
- 2-page brief;
- poster source;
- authorship/AI disclosure;
- reproducibility link;
- mentor/reviewer acknowledgement template.

Do not fabricate venues, acceptance, awards or affiliations.

# 50. Stranger Reproducibility

Create `REPRODUCIBILITY.md` and commands/scripts equivalent to:
- make baseline
- make validate
- make burn-vs-bake
- make optimize
- make figures

A clean environment must reproduce principal results where dependencies such as OpenFOAM are installed.

Record expected runtime and hardware assumptions.

# 51. Admissions-Facing Artifacts

In addition to the scientific paper, generate source material for:
- 2-page technical brief;
- research poster;
- 90-second student technical explainer;
- 3-5 minute technical video;
- concise project page/README.

The first sentence of public-facing material should lead with the scientific question, not "AI" or software brands.

Do not write claims about admissions value inside the scientific paper.

# 52. Student Defense

Create `docs/defense_questions.md`.

At minimum test understanding of:
- peak vs cumulative heating;
- Sutton-Graves assumptions;
- transient conduction/diffusion timescale;
- trajectory coupling;
- CFD model limits;
- mesh convergence;
- Pareto optimization;
- surrogate uncertainty;
- robust optimization;
- experimental calibration vs validation;
- what AI did and did not contribute;
- strongest negative result.

The final repository must be explainable by the student without AI assistance.

# 53. Final Quality Gate

Before declaring completion, verify that the project demonstrates:
1. non-obvious research question;
2. falsifiable hypotheses;
3. verified implementation;
4. independent validation;
5. signature burn-vs-bake result or honest rejection;
6. fair AI ablation;
7. uncertainty analysis;
8. blind experimental prediction;
9. external technical criticism if available;
10. negative results;
11. stranger reproducibility;
12. clear student intellectual ownership.

Do not declare the capstone complete merely because all planned software modules exist.
