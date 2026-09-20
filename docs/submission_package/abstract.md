# Abstract

Target 200–250 words. One paragraph in the final version; the structure below is scaffolding
and is removed before use.

**Status: skeleton.** Every result slot is `[PENDING FINAL RUN]`. The framing sentences are
final and are written to be reusable verbatim.

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
> Opening the geometry axis recovers a feasible region in which a jointly optimised design
> runs its bondline 32.5 K cooler than one selected on peak flux alone.
>
> [PENDING FINAL RUN — one sentence on the Fidelity-1 Pareto result and its uncertainty.]
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

**Paragraph 4.** `[PENDING FINAL RUN]`. When M4 is re-run under the corrected heating model
and the CFD drag surface, one sentence: the front, the joint-versus-peak-only comparison,
and the uncertainty band from M7. If M5 or M6 produce a measured difference, that is a
*second* abstract about optimisation methods and does not belong in this one.

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
> entry cuts peak flux 38.3% while running the bondline 114.1 K hotter. A jointly optimised
> design runs 32.5 K cooler at the bondline than one chosen on peak flux alone.
> [PENDING FINAL RUN — uncertainty.] All results are model predictions within documented
> assumptions.
