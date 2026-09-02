# AETHER

### When Cooler Is Not Safer: Rethinking Atmospheric Re-entry Through Peak and Cumulative Thermal Optimization

*AI-guided multifidelity framework for coupled re-entry trajectory, aerodynamics and TPS optimization.*

---

## The question

A re-entry vehicle is usually designed against **peak heat flux** — the single worst
instant of heating on the outer surface. The heat shield, however, does not fail at the
surface. It fails at the **bondline**, where the thermal protection system meets the
structure it is protecting, and the bondline responds not to the peak but to the *time
integral* of what got past the surface.

Those two quantities are not optimized by the same trajectory. A steep entry burns hard
and briefly. A shallow entry runs cooler at the surface for much longer, and heat has
time to diffuse inward.

> **H0 — the central hypothesis:** minimizing peak heat flux alone does not necessarily
> produce the thermally safest re-entry solution.

This repository tries to falsify that, quantitatively, with a verified reduced-order
model first and CFD afterwards.

So far it survives: over a 41-point sweep of entry angle, the two metrics are strictly
monotone in opposite directions — the shallowest entry cuts peak heat flux 38% while
running the bondline 114 K hotter, and no interior angle improves both. That is a result
about a one-parameter family, not yet about a design space; see
[`PROJECT_STATUS.md`](PROJECT_STATUS.md) for exactly how far the claim extends and where
it stops.

## Status

**Milestone M1 complete** (reduced-order burn-vs-bake demonstration). See
[`PROJECT_STATUS.md`](PROJECT_STATUS.md) for the live gate table and
[`reports/milestones/`](reports/milestones/) for results.

Nothing in this repository is flight-relevant. Every result is a model prediction inside
a documented set of assumptions — see [`ASSUMPTIONS.md`](ASSUMPTIONS.md) and
[`VALIDATION_MATRIX.md`](VALIDATION_MATRIX.md), which records what has actually been
verified against a reference and what has not.

## Quick start

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"

make test            # verification suite (analytical benchmarks, convergence)
make baseline        # single nominal entry: trajectory -> heating -> TPS
make burn-vs-bake    # M1: search for the signature counterexample
make figures         # regenerate every figure in reports/
```

Full instructions, expected runtimes and hardware assumptions:
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

## What is modelled

| Layer | Model | Verified against |
|---|---|---|
| Atmosphere | US Standard Atmosphere 1976, 0–86 km geopotential | published USSA-76 table values |
| Trajectory | point-mass 3-DOF planar entry, spherical non-rotating Earth | tolerance convergence + limiting cases |
| Aeroheating | Sutton–Graves stagnation-point convective flux | scaling laws + published worked value |
| TPS | 1-D multilayer transient conduction, implicit, radiating surface | analytical semi-infinite constant-flux solution |

Fidelity 1 (OpenFOAM v2606 compressible aerodynamics) is scaffolded but **gated** — CFD
data may not enter the optimization loop until mesh independence, force convergence and
a published blunt-body benchmark comparison are all documented. See
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## What this is not

No MHD, no plasma braking, no morphing geometry, no retropropulsion, no spinning
capsules, no ablation chemistry as a primary model, no flight-qualified structural
design. Scope is frozen — see [`CLAUDE.md`](CLAUDE.md) §2 and §42.

## Honesty

- [`AI_USAGE.md`](AI_USAGE.md) — line between AI-generated, student-reviewed, and
  student-authored work.
- [`docs/negative_results.md`](docs/negative_results.md) — things that did not work,
  kept on purpose.
- [`docs/research_story.md`](docs/research_story.md) — how the question actually
  changed, not a story rewritten to look predetermined.

Adithya Kesan Jayakanth · independent capstone · 2026
