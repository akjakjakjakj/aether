# Abstract

Target 200–250 words. One paragraph in the final version; the structure below is scaffolding
and is removed before use.

**Status: filled 2026-09-21 from the result files at commit `de2a834`; AI-drafted, to be
revised and owned by the student before use.** The simulation slots are filled. Nothing in
an abstract depends on the physical experiment except the closing sentence, which already
says no experimental validation is claimed; if the coupon experiment is run, that sentence
and one result sentence change, and that change is `[PENDING — STUDENT]`.

---

## Draft

> A re-entry heat shield is normally designed against peak heat flux, the single worst
> instant of heating on its outer surface, but it does not fail there: it fails at the
> bondline, where the thermal protection meets the structure it protects, and the bondline
> responds to the time integral of the heat that gets past the surface rather than to the
> peak. This work asks whether those two quantities are minimised by the same entry, and
> whether optimising both together finds designs that optimising the peak alone would miss.
>
> A reduced-order chain (US Standard Atmosphere 1976, point-mass three-degree-of-freedom
> entry, Sutton–Graves stagnation heating with an effective nose radius taken from measured
> stagnation-point velocity gradients, and a one-dimensional transient multilayer conduction
> solver with a radiating surface) was verified against published references before being
> used: the conduction solver agrees with an analytical semi-infinite solution to 0.002% and
> closes its energy balance to about 10⁻¹⁴, and the trajectory integrator reproduces a
> published closed-form-versus-numerical comparison to within 0.92 percentage points.
>
> Over a sweep of entry flight-path angle, peak heat flux and peak bondline temperature are
> strictly monotone with opposite signs: the shallowest entry tested cuts peak heat flux by
> 38.3% while running the bondline 114.1 K hotter, and no intermediate angle improves both.
> With drag taken from a response surface fitted to 69 inviscid perfect-gas CFD cases, the
> knee of the two-objective Pareto front runs 14.9 K cooler at the bondline than the
> peak-flux-only optimum for 21.5 kW/m² more peak flux; under the declared uncertainties the
> paired difference is −14.31 K (s.d. 1.45 K) and is negative in all 3000 draws. That is a
> statement about entry steepness at a geometry fixed by placeholder constraints, not about a
> located capsule shape. The hypothesis that adaptive use of CFD would reduce the number of
> CFD runs needed was not supported, and the physical coupon experiment has not been run.
>
> All results are model predictions within a documented set of assumptions; no flight or
> experimental validation is claimed.

---

## Notes on each part, for whoever fills this in

**Sentence 1 (the question).** Final. It leads with the physics, names the failure mode, and
gives the reason the question is non-obvious in the same breath. It does not mention AI,
optimisation, software or the framework, per spec §51. Do not replace "bondline" with
something vaguer; the specificity is the point.

**Sentence 2 (what was asked).** Final.

**Paragraph 2 (method and verification).** The numbers are real and final:

| Claim | Source file |
|---|---|
| 0.002% against the analytical solution, energy residual ~1e-14 | `VALIDATION_MATRIX.md` row G3 |
| 0.92 percentage points against Putnam & Braun (2015) Table 2 | `VALIDATION_MATRIX.md` row G1B |
| effective nose radius from measured velocity gradients | `docs/theory/effective_nose_radius.md` |

Mentioning verification in an abstract is unusual and is done deliberately: it is the
strongest true thing about the work, and it is what separates it from a plausible-looking
simulation.

**Paragraph 3 (the result that exists).** Numbers from
`reports/milestones/M1_burn_vs_bake.md`. Three cautions, all of which the milestone report
already carries and none of which may be dropped in compression:

- Say **"strictly monotone with opposite signs"**, not "perfectly anti-correlated". The
  Spearman ρ = −1.000 is close to tautological over a one-parameter sweep and must not be
  quoted as independent evidence.
- Quote the **absolute** 32.5 K, never a margin ratio, which swings from 37× to 1.6× as the
  bondline allowable moves from 445 K to 500 K.
- These are **legacy-heating-model** numbers, and for M1 and M1b specifically that label
  costs nothing: both use a hemisphere-nosed body (R_n = D/2, i.e. K = 1), where the legacy
  and corrected effective-nose-radius models agree identically. Say so in the brief; there
  is no room in an abstract, which is why the abstract states the physical result rather
  than a heating magnitude.

**Paragraph 4.** Filled 2026-09-21. Sources:

| Claim | Source file |
|---|---|
| 69 usable CFD cases | `reports/milestones/M3_coupled_model.md` §3, §6 |
| knee −14.9 K, +2.146e+04 W/m² against the peak-flux-only optimum | `reports/milestones/M4_pareto_optimisation.md` §10 |
| paired difference −14.31 K, s.d. 1.45 K, 3000 of 3000 draws | `reports/milestones/M7_addendum_posthoc.md` §1; `results/M7/M7-UQ-20260920T233048Z/paired_difference.json` |
| geometry fixed by fences | M4 report §11, §11a; `docs/negative_results.md` NR-29, NR-30 |
| H2 `NOT_SUPPORTED` | `reports/milestones/M6_adaptive_fidelity.md` |

The 32.5 K Fidelity-0 figure was dropped from the full abstract to make room: it is a
constant-drag-coefficient number and the Fidelity-1 figure supersedes it as the headline. It
stays in the brief, labelled. The M5 result is not in the abstract, because it is a result
about optimisation methods and the abstract is about the physics; H2 is in, because it is one
of the three frozen hypotheses and it was not supported.

**Final sentence.** Final, and not negotiable. Spec §37.

---

## Shorter variants

Some forms cap at 100 or 150 words. Compress by dropping paragraph 2 entirely rather than by
thinning every paragraph, because the verification detail is the first thing that becomes
meaningless when abbreviated. Never compress by dropping the final sentence.

**100-word version, skeleton:**

> A re-entry heat shield is normally designed against peak heat flux, but it fails at the
> bondline, which responds to the integrated heat that gets past the surface rather than to
> the peak. This work asks whether the two are minimised by the same entry. In a verified
> reduced-order model, they are not: over the range of entry angle tested, peak heat flux
> and peak bondline temperature are strictly monotone with opposite signs, and the shallowest
> entry cuts peak flux 38.3% while running the bondline 114.1 K hotter. With CFD-derived
> drag, the knee of the Pareto front runs 14.9 K cooler at the bondline than the
> peak-flux-only optimum, and the paired difference under the declared uncertainties
> (−14.31 K, s.d. 1.45 K) is negative in all 3000 draws. All results are model predictions
> within documented assumptions; no experiment has been run.
