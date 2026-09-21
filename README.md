# AETHER

### When Cooler Is Not Safer: Rethinking Atmospheric Re-entry Through Peak and Cumulative Thermal Optimization

---

## The question

A re-entry vehicle is usually designed against **peak heat flux**, the single worst instant
of heating on the outer surface. The heat shield does not fail at the surface. It fails at
the **bondline**, where the thermal protection system meets the structure it is protecting,
and the bondline responds to the heat that got past the surface over the whole entry, not to
the peak.

Those two quantities need not be minimised by the same entry. A steep entry burns hard and
briefly. A shallow entry runs cooler at the surface for much longer, and heat has time to
diffuse inward.

> **H0:** minimising peak heat flux alone does not necessarily produce the thermally safest
> re-entry solution.
>
> **H1:** joint optimisation of peak heat flux and in-depth TPS response can identify safer
> feasible designs than peak-heat-only optimisation.
>
> **H2:** surrogate-assisted and AI-guided adaptive-fidelity search can approach the Pareto
> frontier with fewer expensive CFD evaluations than unguided or brute-force search.

This repository tries to falsify those, with a reduced-order model checked against published
references first and a CFD-derived drag model afterwards.

## The result, in one paragraph

Within the model, H0 holds: over a 41-point sweep of entry angle, peak heat flux and peak
bondline temperature are strictly monotone in opposite directions, and the shallowest entry
cuts peak flux 38.3% while running the bondline 114.1 K hotter. H1 holds narrowly: on the
final physics the knee of the Pareto front runs 14.9 K cooler at the bondline than the
peak-flux-only optimum for 21.5 kW/m² more peak flux, and under the declared uncertainties
that difference (−14.31 K, s.d. 1.45 K) is negative in all 3000 draws. But it is a statement
about how steeply to enter, at a geometry fixed by placeholder constraints: the knee design's
heat shield is 346 kg of a 350 kg vehicle, which is not a vehicle, and capsule shape does not
vary along the front. **H2 was not supported:** adaptive use of CFD reached its pre-declared
target in none of five seeds, the target turned out to be unreachable at the study's budget,
extra CFD changed the no-CFD arm's score by 0.0001, and the AI-guided arm was never run. A
language-model agent beat the best conventional optimiser at 50 and 100 evaluations and
showed no measured difference at 200; its early lead cannot be separated from prior
knowledge. **The physical experiment has not been run and no external review has happened.**

Nothing in this repository is flight-relevant. Every result is a model prediction inside a
documented set of assumptions.

- The paper: [`reports/final/AETHER_paper.md`](reports/final/AETHER_paper.md) (AI-drafted;
  to be revised by the author)
- Exactly how far each claim extends: [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
- What has been checked against a reference and what has not:
  [`VALIDATION_MATRIX.md`](VALIDATION_MATRIX.md), [`ASSUMPTIONS.md`](ASSUMPTIONS.md)
- Why the project is not complete: [`docs/final_quality_gate.md`](docs/final_quality_gate.md)

## Status

Simulation milestones M0 to M7 are complete. **M8 (the thermal coupon experiment) is a
support package only; nothing has been measured.** M9: the paper is drafted and the
submission package is filled except for the items only the author can supply. By the
specification's own final quality gate the project is **not complete**: blind experimental
prediction, external criticism and student intellectual ownership are unmet.

## How to reproduce

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"

make test            # verification suite (analytical benchmarks, convergence, guards)
make baseline        # single nominal entry: trajectory -> heating -> TPS
make burn-vs-bake    # M1 + M1b: the Fidelity-0 result, reports and figures (~4 min)
make doe && make optimize                                # M4 at Fidelity 1 (~11 min, 6 workers)
make ablation-replay RUN_ID=M5-ABL-20260920T211134Z      # M5, no LLM access needed
make robust && make uncertainty                          # M7 (hours, then ~25 min)
```

The CFD stages (`make cfd-validate`, `make cfd-design-points`, `make adaptive`) need OpenFOAM
and take hours; the version used was v2512. The drag surface they produced is persisted in
`data/aero/cfd_surface_v2/` and reloads bit for bit, and the evaluator serves it only while
the stored gate file `results/M2/M2-20260920T123901Z/gate_assessment.json` reads PASS, so the
commands above are intended to run without OpenFOAM. That has not been tried on a clean
machine by anyone yet. Full instructions,
measured runtimes and hardware assumptions: [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md). Every
number in every milestone report is read from a result file; reports are generated, and a
hand edit is overwritten by the next run.

## What is modelled

| Layer | Model | Checked against | Status |
|---|---|---|---|
| Atmosphere | US Standard Atmosphere 1976; exact 0–86 km, transcribed table 86–150 km | published layer-base values; a primary copy at five altitudes | `PASS` / `LIMITED` above 86 km outside those five |
| Trajectory | point-mass 3-DOF planar entry, non-rotating spherical Earth | a published closed-form-versus-numerical comparison, within 0.92 points | `PASS` |
| Aeroheating | Sutton–Graves stagnation-point convective flux, effective nose radius from measured stagnation velocity gradients | the constant re-derived from NASA TR R-376 to 0.39% | constant `PASS`; model form `LIMITED`, not attempted |
| TPS | 1-D multilayer transient conduction, implicit, radiating surface, post-entry soak-out | analytical semi-infinite constant-flux solution, 0.002% | `PASS` |
| Aerodynamics | Gaussian-process drag surface through 69 inviscid perfect-gas OpenFOAM cases, Mach 3–27, coarse mesh; base drag assumed | sphere at Mach 3 and 6 (gate G4, which first read `LIMITED`) | gate `PASS`; surface `LIMITED` |

## What this is not

No MHD, no plasma braking, no morphing geometry, no retropropulsion, no spinning capsules, no
ablation chemistry, no flight-qualified structural design. Scope is frozen: see
[`CLAUDE.md`](CLAUDE.md) §2 and §42.

## Honesty

- [`AI_USAGE.md`](AI_USAGE.md): **most of the code, the study runs, the milestone reports and
  the first draft of the paper were produced by an AI assistant.** This file records what was
  generated, what has been reviewed by the author (so far, very little), and which modelling
  decisions await his approval.
- [`docs/negative_results.md`](docs/negative_results.md): thirty-five things that did not
  work, kept on purpose.
- [`docs/research_story.md`](docs/research_story.md): how the question actually changed, not
  a story rewritten to look predetermined.
- [`reports/final/HANDOFF.md`](reports/final/HANDOFF.md): what is done and what only the
  author can do.

Adithya Kesan Jayakanth · independent capstone · 2026
