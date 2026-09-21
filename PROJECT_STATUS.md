# Project status

Updated 2026-09-21, at commit `de2a834`. Written by the AI assistant from the repository's
files; every number below names the file it was read from.

**One-line state:** every simulation study has run and the paper is drafted. The project is
**not complete** by spec §53: the blind thermal experiment has not been run, no external
review has happened, and the student has not yet read the code or revised the paper
(`docs/final_quality_gate.md`: 6 MET, 3 PARTIAL, 3 NOT MET).

## Milestones

| ID | Milestone | Status | Evidence |
|---|---|---|---|
| M0 | Repository, reproducibility, provenance, test harness | Complete | `REPRODUCIBILITY.md`; 497 tests passed, 1 skipped at the 2026-09-21 regeneration |
| M1 | Burn-vs-bake reduced-order demonstration | Complete. **H0 supported** in the tested domain. Fidelity 0, legacy-model numbers | `reports/milestones/M1_burn_vs_bake.md`, `M1_signature_counterexample.md` |
| M1b | Geometry axis opened; peak-only against joint optimum | Complete. H1 supported at Fidelity 0 (32.5 K); superseded as the headline by M4 | M1 report §M1b |
| §44 | Thermal Penetration Index | Complete. Verdict **DISCARD** (rank-redundant with bondline peak) | `reports/milestones/TPI_study.md`; NR-10 |
| M2 | OpenFOAM validation, gate G4 | Complete. **G4 PASS, and it first read LIMITED**; the restart rule that turned it was written after the original results were seen (NR-25) | `reports/milestones/M2_cfd_validation.md` |
| M3 | Coupled model, CFD drag surface `cfd_surface_v2` | Complete. G5 PASS (software gate only); the surface itself is **LIMITED** (coarse mesh, perfect gas, no capsule validation data) | `reports/milestones/M3_coupled_model.md` |
| M4 | DOE and Pareto optimisation, Fidelity 1 | Complete. **H1 supported, narrowly**; matrix row LIMITED | `reports/milestones/M4_pareto_optimisation.md` |
| M5 | AI against conventional optimisers | Complete. Mixed: AI helped at 50 and 100 evaluations, no measured difference at 200; n = 5, one model; matrix row LIMITED | `reports/milestones/M5_ai_ablation.md`, `M5_qualitative_audit.md` |
| M6 | Adaptive fidelity | Complete. **H2 NOT SUPPORTED**; target unreachable at the budget (sizing flaw); AI-guided arm not run; matrix row LIMITED | `reports/milestones/M6_adaptive_fidelity.md`, `M6_addendum_posthoc.md` |
| M7 | Uncertainty and robust design | Complete. Shortcut verification PASSED; every spread is a lower bound; matrix row LIMITED | `reports/milestones/M7_uncertainty_robust.md`, `M7_addendum_posthoc.md` |
| M8 | Thermal coupon blind validation | **Support package only. The experiment has NOT been run.** No measurement exists. Matrix row IN_PROGRESS | `experiments/thermal_coupon/` |
| M9 | Final paper and package | **Paper drafted (AI draft, unrevised by the student). Package pending student items:** experiment results, external review, public location, review counts | `reports/final/AETHER_paper.md`, `reports/final/HANDOFF.md`, `docs/submission_package/` |

## Headline results

**H0: supported, within the model.** Over a 41-point sweep of entry angle from −8.0° to
−1.5°, peak heat flux and peak bondline temperature are strictly monotone with opposite
signs. The ends differ by 38.3% in peak flux and 114.1 K at the bondline, and 818 of 1640
ordered pairs are counterexamples under thresholds declared in advance. The Spearman
ρ = −1.000 over that sweep is tautological for a one-parameter family and is not evidence.
With geometry frozen, 0 of 41 candidates were feasible. (M1 reports; Fidelity 0.)

**H1: supported, narrowly.** On the final physics (CFD-derived drag, corrected nose-radius
heating), the knee of the 78-design front runs **14.9 K cooler** at the bondline than the
peak-flux-only optimum for **+21.5 kW/m²** of peak flux (403.5 K against 418.4 K). Under the
declared uncertainties, paired on shared draws, the difference is **−14.31 K, s.d. 1.45 K,
negative in 3000 of 3000 draws and 24 of 24 epistemic branches**. (M4 report §10; M7
addendum §1.)

It is a statement about entry steepness at a fenced geometry, not about capsule shape (M4
report §11–§11a; NR-29, NR-30):

- C_D at peak heating varies by about 0.1% across the front (1.363–1.364);
- 50 of 78 front designs are within 1% of a heat-shield mass-fraction limit of 1.0 that is a
  logical fence, not a sourced mass budget. The knee's TPS is **346 kg of a 350 kg vehicle**.
  That is not a vehicle;
- 28 of 78 sit on the edge of the CFD hull, which is where CFD happened to be run;
- the shoulder ratio was frozen by the screening rule, and probes show the frozen lever is
  worth about 7% of peak flux at the front, a lever a stagnation-point-only heating model
  rewards for the wrong reason;
- every front design accrues more than 5% of its heat load above 86 km, up to 20.9%.

**Fragility and the robust design.** The three nominal optima violate at least one
constraint in 29.6%, 34.4% and 46.6% of draws. None of the violations is thermal (bondline 0
of 3000 for each). The chance-constrained robust knee reads **3.20% [2.63, 3.89]** on the
same 3000 draws (like-for-like run `M7-LFL-20260921T011854Z`) for +3.1% nominal peak flux.
The cell as first generated, 2.80% [1.68, 4.64] on 500 mixed draws, is kept on record. (M7
report §3.2, §6; NR-33.)

**H2: NOT supported.** Adaptive fidelity reached the pre-declared target in 0 of 5 seeds; no
arm did. 109 extra CFD points moved the no-CFD arm's score by 0.0001. The target was also
unreachable at the budget: all 25 arm-seeds pooled reach 94.1% of the reference against a 95%
target, a sizing flaw (NR-35). The LLM-guided adaptive arm was never run, so the hypothesis's
"AI-guided" clause is untested. The criterion was left as written.

**AI ablation: mixed.** The LLM agent beat the best conventional optimiser (the Bayesian
optimiser) at 50 and 100 evaluations and showed no measured difference at 200 under the
pre-declared rule. Its lever directions came from aerospace priors, which it usually stated,
so the early lead cannot be separated from contamination; a little under half its final lead
is precision on placeholder limits. n = 5 seeds, one model. (M5 report §4; audit; NR-32.)

**What dominates the uncertainty.** At the front, peak flux is dominated by the disagreement
between two NASA sources for effective nose radius (S_T 0.706; they differ by about 20% at
K = 0.417). Bondline temperature is dominated by TPS conductivity (0.638) and the multiplier
on heating above 86 km (0.262), both engineering judgment. Epistemic share of variance:
84–94% for flux, 97–99% for bondline. (M7 report §4; addendum §5.)

## What is NOT established

- Anything about a real vehicle, a real TPS material or a flight condition.
- Anything experimental. The coupon experiment has not been run; only a synthetic software
  check exists.
- Any external view. No review has been requested or received.
- The heating model form (gate G2′: catalycity, hot wall, radiation). Not attempted;
  catalycity alone is worth about a factor of two. Every uncertainty figure is therefore a
  lower bound.
- Heating above 86 km, which is outside Sutton–Graves' continuum regime and rests on an
  interpolated atmosphere table checked at five altitudes only.
- The perfect-gas CFD's ±5% model-form band, which is declared and has not been validated.
- The drag on capsule shapes against any measurement. The CFD is validated on a sphere at
  Mach 3 and 6.

## Verification state

497 tests passed, 1 skipped (`reports/milestones/REPORT_REGENERATION_2026-09-21.md`). Gate
summary: G1A, G1B, G2, G3 `PASS`; G1A′ `PASS` at five altitudes and `LIMITED` elsewhere;
G2′ `LIMITED`, not attempted; G-GEO2 `PASS` implementation / `LIMITED` physics; G4 `PASS`
with the NR-25 history; G5 `PASS` as a software gate; M3 to M7 rows `LIMITED`; M8
`IN_PROGRESS`. Full table: `VALIDATION_MATRIX.md`.

`VALIDATION_MATRIX.md` was swept for stale text on 2026-09-21 (same day, after this file was
first written): the M1 row now reads `LIMITED` (mechanism confirmed at Fidelity 1 and under
uncertainty; not validated against a measurement); the closing "Supported / Not supported"
paragraphs now describe `cfd_surface_v2` and its unvalidated ±5% band instead of a constant
coefficient; the M6 and M7 harness rows now read as historical ("harness built 2026-09-20;
study since run"); and the §44 row now cites NR-10. See `VALIDATION_MATRIX.md`'s own "Last
updated" line.

## Open student decisions

1. **The deceleration limit.** Flat 12 g appears in no NASA document found. Option A: keep it
   and relabel it an emergency envelope; "feasible" then means survivable in a contingency.
   Option B: adopt the NASA-STD-3001 deconditioned duration curve; measured on the M1b grid
   that leaves 4 of 140 designs at 10 g and none at 8 g, and it needs a pulse-duration metric
   the evaluator does not compute. (`ASSUMPTIONS.md`, open decision under A-LIM-1b.)
2. **The twenty-two AI-proposed decisions** awaiting approval in `AI_USAGE.md`, several of
   which change a physical model (the effective-nose-radius model; the unchanged
   Sutton–Graves constant; the forebody-only CFD domain; the mass-closure constraint; the
   whole M7 input inventory) or decide what happens in the laboratory.
3. **Whether to accept a drag surface built on the coarse mesh.** Six coarse-to-medium pairs
   differ by at most 0.411% and the discretisation band is 0.628% from a sphere's GCI; the
   all-medium design is estimated at about 8 h and was not run. Related: whether to accept
   G4's `PASS` given that its restart rule was written after the fact (NR-25).

Also his: the coupon's polymer, heater, sensors and declared tolerance; the public location
of the repository; whether to authorise the live LLM calls the `ai_adaptive` arm would need.

## What would change the conclusions

- A catalycity or hot-wall treatment: levels and margins move, possibly by a factor near two,
  mostly in common mode across designs.
- An ablating TPS or a much thicker stack: the effect shrinks; at 40 mm it vanished (NR-03).
- A sourced mass budget or a mass model that grows with size: the front moves to smaller
  diameters and higher heating, and shape may start to matter.
- A heating model that sees the shoulder: the frozen 7% lever becomes a real trade or a real
  cost.
- Adopting the documented deceleration curve: the Fidelity-0 feasible region empties; the
  effect on the Fidelity-1 front has not been measured.
- A coupon result that the conduction model mispredicts: the one `PASS` the headline rests on
  would be in question.
- Resolving the 20% disagreement between the two nose-radius sources: removes most of the
  peak-flux uncertainty at the front. The paper that would do it (DOI 10.2514/1.T7458) is
  paywalled and unread.

## Next action

The student's, in the order given in `reports/final/HANDOFF.md`: read the Tier 1 code, decide
the g-limit, run the coupon experiment, ask for one review.
