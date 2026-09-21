# Two-page technical brief

Spec §51. Source for a two-page PDF: one page of argument, one page of evidence. Written
for a technically literate reader who is not an aerothermodynamicist.

**Status: simulation slots filled 2026-09-21 from the result files at commit `de2a834`;
AI-drafted, to be revised and owned by the student.** Prose that is final is marked *final*.
Slots that depend on the physical experiment or on external review are marked
`[PENDING — STUDENT]`.

---

## Page 1

### Title

**When cooler is not safer: peak versus in-depth thermal optimisation of atmospheric
re-entry**

Author line: name, "independent capstone", year. No institution, no venue, no award. If a
submission form requires a school affiliation, it goes in the form, not on the brief.

### Opening (final, ~120 words)

> A re-entry vehicle is normally designed against peak heat flux: the single worst instant
> of heating on the outer surface of its heat shield. That is the number that selects the
> material. But the heat shield does not fail at the surface. It fails at the bondline,
> where the thermal protection meets the structure underneath, and the bondline does not
> respond to the peak. It responds to how much heat got past the surface, and for how long.
>
> Those are different quantities, and there is no reason they should be minimised by the
> same entry. A steep entry burns hard and briefly. A shallow entry runs cooler at the
> surface for much longer, and heat has time to diffuse inward. This project asks whether
> designing against the peak can therefore select the wrong trajectory, and what it costs to
> optimise both at once.

### The mechanism, with the figure (final)

Half a page. Figure: `reports/figures/M1_mechanism.png`, which shows the heat-flux history
and the in-depth temperature history side by side for a steep and a shallow entry.

Content, in this order:

1. Sutton–Graves: q̇″ = k√(ρ/R_n)V³. Velocity cubed, density rooted. Heating is dominated
   by speed; deceleration (ρV²) is relatively more sensitive to density. So heating peaks
   earlier and higher, where the vehicle is fast and the air is thin.
2. The TPS is a diffusive low-pass filter. Its characteristic time is L²/α; equivalently the
   depth heat reaches in time t is √(αt). For this stack, α ≈ 8.9×10⁻⁷ m²/s, so over a 245 s
   entry √(αt) ≈ 15 mm, which is the stack thickness. **The two timescales are comparable,
   and that is the whole point**: if the stack were much thicker the bondline would never
   hear about the entry, and if it were much thinner it would just track the surface.
3. Therefore a short intense pulse is absorbed near the surface and re-radiated away at T⁴
   before it can diffuse inward, while a long mild pulse has time to reach the bondline.
4. One sentence naming the consequence: peak flux is a surface quantity, bondline
   temperature is an integrated and delayed one, and optimising the first does not constrain
   the second.

### The result that exists (final numbers, from `reports/milestones/M1_burn_vs_bake.md`)

| | Steep (γ₀ = −8.00°) | Shallow (γ₀ = −1.50°) |
|---|---|---|
| Peak heat flux | 230.64 W/cm² | **142.38 W/cm²** (−38.3%) |
| Integrated external load | 79.3 MJ/m² | 128.3 MJ/m² |
| Entry duration | 134.8 s | 324.1 s |
| **Peak bondline temperature** | **423.7 K** | 537.8 K (+114.1 K) |

Both metrics are strictly monotone in entry angle with opposite signs across the whole range
tested, so there is no intermediate angle at which both improve. An automated search over
all 1640 ordered candidate pairs, with thresholds declared in advance (at least 1.0% flux
reduction and at least 1.0 K bondline penalty, so discretisation noise cannot be reported as
physics), found 818 counterexample pairs.

**Three things the brief must say here and not quietly drop:**

- The rank correlation over that sweep is Spearman ρ = −1.000, and **that number is close to
  tautological**: over a one-parameter sweep, two strictly monotone functions can only give
  ±1. The monotonicity is the finding.
- With geometry frozen, **zero of 41 candidates satisfied both hard constraints**. Steep
  entries violate the deceleration limit, shallow ones the bondline limit. Trajectory
  shaping alone cannot produce a valid design, which is the reason the objective optimises
  geometry and trajectory jointly.
- Opening the diameter axis (140-design grid) recovers 21 feasible designs, and a joint
  optimiser selects a design whose bondline runs **32.5 K cooler** (411.6 K against 444.1 K)
  than the peak-flux-only optimum, at a cost of +19.6% on peak heat flux. Quote the absolute
  32.5 K, never a margin ratio: the ratio is measured against the bondline allowable and
  swings from 37.5× at 445 K to 1.6× at 500 K.

**Legacy-model note, required.** M1 and M1b were computed with `effective_nose_radius_m =
nose_radius_m`. That model was later found to be wrong for shallow spherical caps and was
replaced. For M1 and M1b specifically the replacement changes nothing: both use a
hemisphere-nosed body (R_n = D/2, so K = R_b/R_n = 1), where the two models agree
identically by construction. The numbers above are unaffected by that correction. They are
still constant-drag-coefficient numbers: with the CFD-derived drag surface the same baseline
capsule's peak flux is 16.52% higher and its bondline 9.56 K hotter
(`reports/milestones/M3_coupled_model.md` §10). The Fidelity-1 result is on page 2.

### What is not claimed (updated 2026-09-21)

Five lines, in the brief itself, not in a footnote:

- The Fidelity-1 result is a statement about entry steepness at a geometry set by
  placeholder constraints. The knee design's heat shield is 346 kg of a 350 kg vehicle; it
  is not a capsule.
- The CFD gate G4 reads `PASS` under a restart rule written after the first results were
  seen; on the original runs it read `LIMITED`. The CFD is inviscid perfect gas on a coarse
  mesh, validated on a sphere at Mach 3 and 6 only, with a declared ±5% band that this
  project has not validated.
- H2 (adaptive use of CFD saves CFD runs) was **not supported**.
- No physical measurement exists and no external review has taken place.
  `[PENDING — STUDENT]`
- Nothing here is a statement about a flight vehicle or a real thermal protection material.

---

## Page 2

### Method, one column

The chain, each with its verification status:

| Layer | Model | Status |
|---|---|---|
| Atmosphere | USSA-76, exact 0–86 km; transcribed and log-interpolated table 86–150 km | G1A `PASS`; G1A′ `PASS` at five primary-checked altitudes, `LIMITED` elsewhere |
| Trajectory | Point-mass 3-DOF planar, non-rotating spherical Earth, inverse-square gravity | G1B `PASS` |
| Heating | Sutton–Graves stagnation-point convective, with R_eff from measured stagnation-point velocity gradients | G2 `PASS` (the constant); G2′ `LIMITED` (the model form, *not attempted*) |
| TPS | 1-D transient multilayer conduction, implicit, radiating surface, post-entry soak-out | G3 `PASS` |
| Aerodynamics (Fidelity 1) | OpenFOAM v2512 inviscid axisymmetric forebody; GP drag surface `cfd_surface_v2` through 69 usable coarse-mesh cases, Mach 3–27; base drag assumed | G4 `PASS` (first read `LIMITED`; restart rule written after the fact, NR-25); surface `LIMITED`; G5 `PASS` (software gate only) |

One paragraph on the canonical evaluator: every study calls one function, so no study can
build its own shortcut, and gate G5 fingerprints every metric, margin, diagnostic and the
whole velocity history bit for bit.

### Verification, one column (final numbers)

- Conduction solver against Carslaw & Jaeger's semi-infinite constant-flux solution: **0.002%**
  at the surface, checked at four depths, with demonstrated grid and timestep convergence and
  an energy-balance residual around **10⁻¹⁴**.
- Trajectory integrator against a published Allen–Eggers-versus-numerical comparison
  (Putnam & Braun 2015, Table 2): all nine published figures reproduced to within **0.92
  percentage points** against a declared allowance of 1.0. The point is subtle and worth one
  sentence: the closed form neglects gravity, so a correct integrator *must* disagree with
  it, increasingly as entry flattens. What is validated is the reproduction of a published
  disagreement, not agreement.
- Heating constant re-derived from the primary source: **0.39%** from the value in the code,
  against the primary's own stated 3.3% average correlation error for air. The constant was
  deliberately **not changed**; see the negative-results panel.

### Figures for page 2

| Figure | File | What it shows |
|---|---|---|
| Trade space | `reports/figures/M1_trade_space.png` | Peak flux against bondline temperature across the sweep |
| Feasible region | `reports/figures/M1b_feasible_region.png` | Where both constraints are satisfied on the 2-D grid |
| Optimiser comparison | `reports/figures/M1b_optimiser_comparison.png` | Peak-flux-only against joint selection |
| Pareto front | `reports/figures/M4_pareto_front.png` (run `M4-OPT-20260920T205252Z`, Fidelity 1) | The front under the corrected heating model and the CFD drag surface, with the peak-flux-only optimum, the knee and the bondline-only optimum marked |
| Nominal against robust | `reports/figures/M7_robust_vs_nominal.png` (runs `M4-OPT-20260920T205252Z`, `M7-ROBUST-20260920T211216Z`) | The 78-design nominal front, the chance-constrained front, and each nominal design's 95th percentile |

### Negative results panel (final, this is a selling point rather than a confession)

Pick three of the 35 entries. Recommended (a fourth candidate since the studies ran is
NR-35: H2 not supported, and the study's target was beyond its own search budget):

- **NR-15.** The optimiser was exploiting the heating model. With the nose radius taken as
  the cap radius, `1/√R_n` sends heating to zero as the nose flattens, so an infinitely flat
  nose removed **98.90%** of the stagnation heat flux and 54 of 64 front designs were pressed
  against a placeholder cap. Two 1960s NASA reports supply a measured effective radius from
  stagnation-point velocity gradients; with it, the same change is worth 21.31%, peak flux on
  those designs rises 20.2–20.8%, and the placeholder fence is replaced by a geometric bound.
  The honest coda is that the fix **moved** the exploit: a rounder shoulder now raises
  stagnation heating, so an optimiser will want a sharp shoulder, which is exactly where real
  vehicles are damaged and exactly where this stagnation-point-only model is silent.
- **NR-12.** The heating constant was re-derived from the primary and deliberately **not
  changed**. The derivation lands 0.39% away, but each substitution needed to reach the
  familiar form carries more error than that (−4.10%, −1.10%, +0.81%), and applying all three
  gives −4.01% in the opposite direction. Adopting the fresh number would have shifted every
  heat flux in the repository for worse justification, while looking like the conscientious
  outcome of a validation exercise.
- **NR-04.** The first Pareto front implementation was wrong, and it was caught **by looking
  at the figure**: a two-objective front must be monotone, so a zigzag is geometrically
  impossible. The test suite had not caught it because no test asserted monotonicity.

### Results panel

The §39 comparison table, copied from `reports/milestones/M7_uncertainty_robust.md` §6
(run `M7-UQ-20260920T233048Z`; Fidelity 1, `cfd_surface_v2`; every row re-evaluated under one
source hash; uncertainty from 3000 nested draws, seed 20260921). For the brief, cut to the
rows below; the full table is in the paper.

| Metric | Baseline | Peak-heat-only | Joint O1 (knee) | Robust O1 (knee) |
|---|---|---|---|---|
| Peak heat flux [W/m²] | 1.868e+06 | 2.295e+05 | 2.51e+05 | 2.588e+05 |
| Integrated heat [J/m²] | 1.306e+08 | 1.975e+07 | 1.781e+07 | 1.801e+07 |
| Peak bondline T [K] | 504.3 | 418.4 | 403.5 | 403 |
| Max g | 12.25 | 9.216 | 10.35 | 10.48 |
| Feasible at nominal | no | yes | yes | yes |
| p95 peak bondline T [K] | 523.1 | 426.2 | 410.4 | 410 † |
| P(any constraint violated) | 100.00% [99.87, 100.00] | 34.40% [32.72, 36.12] | 29.60% [27.99, 31.26] | 3.20% [2.63, 3.89] † |

† Like-for-like cell, run `M7-LFL-20260921T011854Z`. The cell as first generated was 500
mixed draws on another seed: p95 bondline 414.1 K, P(violation) 2.80% [1.68, 4.64].

Three sentences that must travel with the table:

- Paired on the same draws, the knee is 14.31 K cooler at the bondline than the
  peak-flux-only design (s.d. 1.45 K), in 3000 of 3000 draws and 24 of 24 epistemic branches
  (`M7_addendum_posthoc.md` §1). That holds within the declared uncertainty model only.
- None of the violations is thermal (bondline 0 of 3000 for every optimised design). The
  constraint crossed is a heat-shield mass fraction of 1.0, which is a logical fence, not a
  mass budget, and for the bondline-only design also a 12 g limit that matches no document.
- Along the front only the entry angle trades the objectives; C_D at peak heating varies by
  about 0.1% across it (M4 report §11a; NR-30).

Method results, one line each: a language-model agent beat the best conventional optimiser at
50 and 100 evaluations and showed no measured difference at 200 under the pre-declared rule
(n = 5, one model; its early lead cannot be separated from prior knowledge). Adaptive
fidelity: H2 `NOT_SUPPORTED`, 0 of 5 seeds reached a target that was itself unreachable at
the budget, and the AI-guided arm was not run.

Physical experiment result: `[PENDING — STUDENT]`. Not run.

### Footer (final)

One line each:

- **Reproducibility.** `make test && make burn-vs-bake` reproduces the result on the
  committed configuration; runtimes and hardware assumptions in `REPRODUCIBILITY.md`.
- **AI disclosure.** Most of the code was written with AI assistance; what was generated,
  what was reviewed and what was student-authored is recorded in `AI_USAGE.md`.
- **Repository.** `[link]`

---

## Layout notes

- Two pages means two pages. If it does not fit, cut the method column before cutting the
  limitations, and cut the negative-results panel to two entries before cutting the
  verification numbers.
- The mechanism figure is the one thing a reader will look at. Give it space.
- Do not put the AI disclosure in six-point type at the bottom. It goes at the same size as
  the reproducibility line.
