# 2026-09-20 — Closing the three LIMITED rows: what the primaries actually say

## Question

`VALIDATION_MATRIX.md` carried three rows as `LIMITED` for the same reason: a number in the
code had a citation attached but nobody had opened the cited document. G1A′ (the >86 km
atmosphere table), G2 (the Sutton–Graves constant) and G1B (the trajectory integrator,
which had no external reference at all). A sourcing report arrived with the documents read
and tiered. Can the rows be closed — and, the question that actually matters, **does
closing them change any number the project has already published?**

## Hypothesis

Written before opening anything, so the record shows what was expected:

1. The atmosphere table is probably fine. It was transcribed from *somewhere*; the risk
   flagged in the sourcing report is that the source was `braeunig.us`, whose >84.852 km
   table is MSISE-90, not USSA-76. If that happened, densities would be off by percent-level
   amounts and the >86 km heat load would move.
2. The Sutton–Graves constant probably re-derives to something close to 1.7415×10⁻⁴, and
   the interesting outcome is not the number but the size of the assumption chain's own
   error.
3. The trajectory integrator should disagree with Allen–Eggers by a lot at shallow entry
   angles. If it agrees to a few percent everywhere, something is wrong — with the
   integrator, or with the comparison being unwittingly circular.

Expected difficulty, written down in advance: the Allen–Eggers comparison is only
meaningful under matched assumptions, and "matched" is doing a lot of work. The closed form
needs an exponential atmosphere, which the integrator does not have.

## Action

1. **Read the primaries, not the citations.** Two documents were downloaded and read from
   300 dpi page renders rather than from OCR text: NASA TR R-376 (Sutton & Graves 1971) and
   Putnam & Braun, JGCD 38(3) 2015. The USSA-76 values came from the sourcing report's own
   direct read of Table I, pp. 68–69.
2. **G1A′.** Diffed `_UPPER_TABLE` against the primary at 90/100/110/120/150 km. Added
   `test_upper_table_against_primary_ussa76`, with the tolerance set to half the primary's
   own printed resolution (0.005 K, 2.5×10⁻⁴ rel.) because that is the tightest claim the
   document can support. Added a second test that *fails* if the three unchecked rows
   (86, 95, 130 km) are ever quietly forgotten.
3. **G2.** Carried the algebra from eq. (33) to the V³ form explicitly, in the report's own
   declared units, and wrote it up step by step in `docs/theory/sutton_graves_constant.md`.
   Quantified each substitution's own error separately.
4. **G1B.** Implemented the Allen–Eggers closed form from NACA 1381's equations
   (`src/aether/trajectory/allen_eggers.py`), added an `ExponentialAtmosphere` and a
   USSA-76 exponential fit, and added `gravity_m_s2` / `planet_radius_m` hooks to
   `integrate_entry` so the reference's constant-gravity model can be matched. All three
   default to the production behaviour.
5. **Constraint limits.** Rewrote A-LIM-1 as A-LIM-1a/1b, and measured what a
   NASA-STD-3001 deconditioned g-curve would do to the feasible region using the stored
   M1b grid rather than re-running anything.

## Expected

See Hypothesis. Also expected and worth stating: that at least one of the three numbers
would turn out wrong and have to be changed, with a documented effect on the baseline.

## Observed

**Not one number changed.** `scripts/run_baseline.py` produces a bit-identical result
before and after: peak heat flux 160.28 W/cm², peak bondline 494.8 K, max 11.89 g. That was
not the expected outcome and it is the single most useful thing in this entry.

**G1A′ — the table is exactly right, at the altitudes checked.** T and ρ agree with the
primary to *every printed digit* at 90, 100, 110, 120 and 150 km; the largest relative
difference is 1.6×10⁻¹⁵, i.e. floating-point round-trip noise. Whatever the table was
transcribed from, it was not the MSISE-90 table the sourcing report warned about. Three
rows (86, 95, 130 km), the entire pressure column, and the log-interpolation between rows
remain unchecked, so the row is `PASS` at five altitudes and `LIMITED` everywhere else.

A side observation worth keeping: the exactly-integrated homosphere and the transcribed
table do not meet at the 86 km seam — T steps by 0.078 K (0.042%) and ρ by 0.032%. Two
different constructions of the same standard, so a small step is expected; it is now
pinned by a test so it cannot grow unnoticed.

**G2 — the report does not contain the equation this project uses.** TR R-376 is written
entirely in stagnation pressure and enthalpy. Its units are `MW/m²`, `atm`, `m`, `MJ/kg` —
verbatim from the SYMBOLS list, and *not* the W/cm² that several secondary restatements
imply. `K(air) = 0.1113` is confirmed exactly at Table II, p. 39.

Carrying the algebra through gives **k = 1.74826×10⁻⁴, +0.39%** from the code's value. The
temptation was to adopt it. The reason not to is that the substitution chain is worse than
the gap it measures: replacing the Newtonian stagnation pressure with the exact
perfect-gas value is −4.10%, the cold-wall assumption −1.10%, the dropped freestream
enthalpy +0.81%; all three applied gives 1.6717×10⁻⁴, i.e. −4.01% in the *opposite*
direction. The primary's own fit carries 3.3% average error for air. The constant stays.

**G1B — the integrator reproduces a published benchmark to under one percentage point.**
Putnam & Braun's Table 2 (p. 419) publishes the disagreement between the Allen–Eggers
closed form and their own numerical integration for three cases. Under their stated
assumptions (ρ = 1.215 e^(−h/8500), g = 9.81 constant, R = 6378 km, L/D = 0, non-rotating):

| case (γ₀) | quantity | AETHER vs. AE | published | residual |
|---|---|---|---|---|
| strategic (−30°) | peak deceleration | −5.89% | −5.1% | 0.79 |
| sample return (−8.2°) | peak deceleration | +35.82% | +34.9% | 0.92 |
| LEO return (−1.35°) | peak deceleration | −58.18% | −57.3% | 0.88 |
| strategic | velocity at peak | −1.78% | −1.8% | 0.02 |
| sample return | velocity at peak | −2.29% | −2.1% | 0.19 |
| LEO return | velocity at peak | +35.25% | +34.9% | 0.35 |
| strategic | altitude at peak | +3.56% | +3.6% | 0.04 |
| sample return | altitude at peak | −4.73% | −4.6% | 0.13 |
| LEO return | altitude at peak | +27.30% | +27.0% | 0.30 |

The gravity model mattered: with AETHER's default inverse-square field and 6371 km radius
the residuals were up to 2.3 points, and matching the reference's constant g = 9.81 and
6378 km brought every one under 1.0.

**Three things found along the way that are not in any plan:**

- *An artefact that looked like physics.* The strategic case peaks at ~6 km altitude while
  travelling at 4.4 km/s, so consecutive solver output samples are ~440 m apart and the raw
  `argmax` altitude is quantised at the several-percent level. The first version of the test
  reported a +5.16% altitude disagreement against a published +3.6% and looked like a real
  discrepancy. It was the output grid. Parabolic refinement through the three samples around
  the peak reproduces a ten-times-finer run to better than 0.01% at a tenth of the cost.
- *An inconsistency in the reference.* Putnam & Braun's Table 2 prints velocity at peak
  deceleration as 7.64 km/s for the sample-return case, but Allen–Eggers requires
  V₁ = V₀·e^(−1/2) = 7.764 km/s for V₀ = 12.8 km/s, and their other two cases match that
  identity (to within their own eq. 13 correction factor, which is +0.4% for the LEO case
  and negligible for the others). Their published *errors* are consistent internally and are
  what this project compares against; the 7.64 is noted and not used.
- *The paper is internally inconsistent about ρ₀* — 1.215 kg/m³ in the case setup (p. 416,
  citing Fegley 1995) against 1.225 in descriptive text on p. 415. 1.215 was used, because
  that is the number attached to the cases.

**Constraint limits — the bondline allowable is real, the g limit is not.** 450 K is
449.8 K = 350 °F, the Space Shuttle Orbiter's aluminium primary-structure design limit
(NASA CR-159900 p. 1). It is a *substrate* limit, not a universal bondline constant —
Apollo's stainless interface is 589 K, Orion's composite-over-titanium 533 K — and it is
the right one only because this project's structure layer is aluminium-like. The residual
gap is that no primary sentence ties 350 °F to the RTV-560 adhesive line specifically.

The 12 g is a different situation. **No document states it.** NASA-STD-3001's sustained
+Ax limit is a duration-dependent curve, and for a deconditioned (post-microgravity) crew
it reads 10.0 g at 10 s, 8.0 g at 30 s, 5.0 g at 90 s, 4.0 g at ≥150 s. The baseline spends
25.5 s above 10 g and 40.0 s above 8 g, so it violates that curve comfortably while
"passing" the flat 12 g with +0.9% margin. Measured on the stored M1b grid (140 designs):

| g limit | passes | passes with bondline ≤ 450 K |
|---|---|---|
| 12.0 (current) | 48 (34.3%) | 21 (15.0%) |
| 10.0 | 18 (12.9%) | 4 (2.9%) |
| 8.0 | **0** | **0** |

**At 8 g the design space is empty.** That is not a tuning question, so the number was not
touched; it is written into `ASSUMPTIONS.md` as an open student decision with both options
and this table.

## Evidence

- `tests/test_atmosphere.py` (+4 tests), `tests/test_heating.py` (+3),
  `tests/test_trajectory_allen_eggers.py` (10, 1 skipped). Full suite: 266 passed,
  1 skipped, ruff clean.
- `docs/theory/sutton_graves_constant.md` — the derivation, step by step with units.
- `docs/negative_results.md` NR-12 — why the constant was not changed.
- `src/aether/trajectory/allen_eggers.py`, `src/aether/atmosphere/exponential.py`.
- `ASSUMPTIONS.md` A-ATM-2, A-ATM-5, A-TRAJ-5, A-HEAT-1, A-LIM-1a/1b + open decision.
- `VALIDATION_MATRIX.md` G1A′, G1B, G2, G2′.
- Baseline runs before and after: `results/baseline/baseline-20260920T131400Z` and
  `.../baseline-20260920T133102Z` — identical.
- Primaries: NASA TR R-376 (NTRS 19720003329); NACA Report 1381 (NTRS 19930091020);
  Putnam & Braun, DOI 10.2514/1.G000846; USSA-76 Table I pp. 68–69; NASA-STD-3001 Vol 2
  Rev F Table 6.5-1; NASA CR-159900 (NTRS 19790012947); NASA TM-104753 (NTRS 19930020462).

## Interpretation

The honest summary is that **the citations were load-bearing and they held** — but not in
the way the rows claimed. Each upgrade is narrower than its row title:

- G1A′ validates a transcription at five altitudes. It does not validate the
  log-interpolation, which is a stand-in for the species-diffusion model USSA-76 actually
  defines, and NR-14 (found concurrently) shows the bondline objective draws 5–20% of its
  heat load from precisely that region. The row was written as `PASS`/`LIMITED` rather than
  rounded up for exactly this reason.
- G1B validates the *integration*, under an exponential atmosphere and constant gravity,
  because that is where a closed form exists. It is not a flight-trajectory validation and
  the production configuration is still unreproduced against anything external.
- G2 validates the *constant*, not the correlation. Catalycity alone is worth roughly a
  factor of two and is untouched (G2′). The useful output of the derivation was not a
  better number but a bound: **treat Sutton–Graves as ±4% at best**, which now belongs in
  M7's uncertainty propagation instead of being assumed away.

The most interesting result is the one that produced no code change at all. A validation
exercise that ends in "the number was right" is easy to under-value, and the pressure to
adopt the freshly-derived 1.74826×10⁻⁴ — because it *feels* like the more rigorous number —
was real. It would have shifted every heat flux in the repository by 0.4% in exchange for
worse justification. Deriving the thing was worth it; changing it would not have been.

The g limit is the opposite case: a number nobody questioned, which turns out to
correspond to no document, and whose defensible replacement would invalidate the feasible
region of the headline study. That is now visible instead of buried.

## Next

1. **Decide the deceleration limit** (student). Option B additionally needs a pulse-duration
   metric in the evaluator — `max_g` alone cannot be read onto NASA-STD-3001's axis.
2. Finish G1A′: the 86/95/130 km rows, the pressure column, and an error bound on the
   log-interpolation between rows. Promoted from housekeeping by NR-14.
3. Open Tauber (NASA TP-2914, 1989) and Tauber & Sutton (1991) and put a number on the
   catalycity term. That is the largest unquantified uncertainty in the heating chain, and
   it is a bigger lever on the result than anything closed today.
4. Carry the ±4% heating-correlation uncertainty and the ±(unquantified) upper-atmosphere
   density uncertainty into M7 as distributions rather than as prose.
5. The Stardust reconstruction (Desai & Qualls, AIAA 2008-1198) remains the best available
   *flight* comparison for G1B, and is blocked on one number: a C_D for the flown SRC.
   Worth one targeted search before M7.
