# 6. Verification and Validation, part 1: gates G1 to G3

*Draft. Does not depend on any pending run. Gates G4 (CFD) and G5 (coupled model) are §8's
business and are not drafted, because G4 is `IN_PROGRESS`.*

Verification asks whether the equations are being solved correctly. Validation asks whether
they are the right equations. The two are kept apart throughout, and the status vocabulary is
fixed: `NOT_STARTED`, `IN_PROGRESS`, `PASS`, `FAIL`, `LIMITED`. **A row is `PASS` only when
it has been checked against an independent reference, not merely when the code runs, and
`LIMITED` is never reported as `PASS`.**

---

## 6.1 Atmosphere

### G1A, 0 to 86 km: `PASS`

The layer profile is integrated exactly and the result is compared with published layer-base
temperatures and pressures, to 0.01% on temperature and 0.1% on pressure. Monotonicity of
density and the ideal-gas closure are checked as well.

### G1A′, 86 to 150 km: `PASS` at five altitudes, `LIMITED` everywhere else

This row was opened deliberately. The concern was specific: a widely used online table labels
its data above 84.852 km as MSISE-90 rather than USSA-76 in a section that is easy to miss,
so if the project's table had been transcribed from there, densities would have been wrong by
percent-level amounts and the upper-atmosphere heat load with them.

The transcribed values at 90, 100, 110, 120 and 150 km were diffed against a primary copy of
the standard's Table I, read off 300 dpi page renders, with the tolerance set to half the
primary's own printed resolution, 0.005 K on temperature and 2.5×10⁻⁴ relative on density,
because that is the tightest claim the document can support.

**They agree to every printed digit**, temperature and density, at all five altitudes. The
largest relative difference is 1.6×10⁻¹⁵, which is floating-point round-trip noise. No table
value was changed.

What that does **not** establish, and the row says so:

- the 86, 95 and 130 km rows, for which no primary value was obtained;
- the entire pressure column, at every altitude;
- the log-interpolation *between* rows, which is a stand-in for the species-diffusion model
  the standard actually defines above 86 km.

A second test fails if the three unchecked rows are ever quietly forgotten.

One side observation is kept because it is the kind of thing that grows unnoticed: the
exactly integrated homosphere and the transcribed table do not meet perfectly at the 86 km
seam, with temperature stepping by 0.078 K and density by 0.032%. Two different constructions
of the same standard, so a small step is expected, and it is now pinned by a test.

**Why the `LIMITED` half is material rather than housekeeping.** Between 5% and 20% of a
feasible design's integrated external heat load accrues above 86 km, and the bondline
objective responds to the integrated load. So up to a fifth of what drives the second
objective comes from the interpolated region, and from a continuum stagnation-heating
correlation applied where the flow is transitional to rarefied. Finishing this row is a
prerequisite for trusting bondline differences of a few kelvin between front designs, not a
tidying task.

---

## 6.2 Trajectory: G1B, `PASS`

The integrator's verification is ordinary: tolerance convergence, physical-ordering tests
(steeper entries are shorter and produce higher peak deceleration; higher ballistic
coefficient penetrates deeper), and checks that no nonphysical state is produced.

The validation is the interesting part, and it turns on a point worth making carefully.

The classical closed-form entry solution neglects gravity relative to drag and holds the
flight-path angle constant. Those assumptions are good for a steep entry and get worse as
entry flattens, because a shallow entry spends a long time in a regime where gravity does
real work. **A correct numerical integrator must therefore disagree with the closed form**,
and increasingly so at shallow angles. Agreement to a few percent everywhere would be
evidence of a bug, or of a comparison that had become circular.

So the validation does not compare against the closed form. It reproduces a **published
disagreement**. Putnam and Braun run three entry cases through both the closed form and their
own full numerical integration and publish the gap for each. Matching their stated
assumptions (an exponential atmosphere with ρ₀ = 1.215 kg/m³ and a scale height of 8500 m,
constant gravity at 9.81 m/s², a planet radius of 6378 km, zero lift, non-rotating), this
project reproduces all nine published figures:

| Case (γ₀) | Quantity | This work vs closed form | Published | Residual (points) |
|---|---|---|---|---|
| Strategic, −30.0° | peak deceleration | −5.89% | −5.1% | 0.79 |
| Sample return, −8.2° | peak deceleration | +35.82% | +34.9% | 0.92 |
| LEO return, −1.35° | peak deceleration | −58.18% | −57.3% | 0.88 |
| Strategic | velocity at peak | −1.78% | −1.8% | 0.02 |
| Sample return | velocity at peak | −2.29% | −2.1% | 0.19 |
| LEO return | velocity at peak | +35.25% | +34.9% | 0.35 |
| Strategic | altitude at peak | +3.56% | +3.6% | 0.04 |
| Sample return | altitude at peak | −4.73% | −4.6% | 0.13 |
| LEO return | altitude at peak | +27.30% | +27.0% | 0.30 |

Maximum residual 0.92 percentage points, against a declared allowance of 1.0, which was set
as the largest residual measured once every published assumption was matched rather than as a
physics tolerance.

**Three things found on the way**, all recorded because they each looked like something they
were not:

- *An artefact that looked like physics.* The strategic case peaks at about 6 km altitude at
  4.4 km/s, so consecutive solver output samples are about 440 m apart and the raw `argmax`
  altitude is quantised at the several-percent level. The first version of the test reported a
  +5.16% altitude disagreement against a published +3.6% and looked like a real discrepancy.
  It was the output grid. Parabolic refinement through the three samples around the peak
  reproduces a ten-times-finer run to better than 0.01% at a tenth of the cost.
- *An inconsistency in the reference.* The published table gives a velocity at peak
  deceleration for one case that does not satisfy the closed form's own identity
  V₁ = V₀ e^(−1/2), which the other two cases do satisfy. The published *errors* are
  internally consistent and are what this work compares against; the anomalous figure is
  noted and not used.
- *An inconsistency in the reference's atmosphere.* The paper gives ρ₀ as 1.215 kg/m³ in the
  case setup and 1.225 in descriptive text. The value attached to the cases was used.

**What G1B does and does not validate.** It validates the *integration*, under an exponential
atmosphere with constant gravity and a constant drag coefficient, because those are the
assumptions under which a closed form exists. It does not validate the production
configuration, and no flight trajectory has been reproduced. The exponential atmosphere added
for this purpose is a validation instrument, not a model of the air, and reports its own
worst-case residual against the standard atmosphere precisely so it cannot be mistaken for an
improvement on it. The gravity and planet-radius overrides default to the production
behaviour and a test asserts the default path is bit-identical. Matching the reference's
gravity model moved the agreement by up to 1.3 percentage points, which is the scale of the
effect.

---

## 6.3 Aeroheating: G2 `PASS` on the constant, G2′ `LIMITED` on the model form

### G2: the constant

Verification is the scaling behaviour: exact V³, √ρ and 1/√R_n ratios to 1e-12, checked by
evaluating the function at scaled inputs rather than by inspecting the source, plus a direct
reference evaluation and input-domain rejection.

Validation is a re-derivation from the primary. The result and the decision that followed are
reported here because the decision is the more useful output.

The primary contains neither the equation form this project uses nor its constant. It gives
q̇_w = K √(p_s/R)(h_s − h_w) with K = 0.1113 for air, in units read verbatim from its own
symbol list, and with a stated average correlation error for air of 3.3% and a maximum of
9.8%. Reaching the V³ form requires three substitutions the report does not make: a Newtonian
stagnation pressure p_s ≈ ρV², a total enthalpy h_s ≈ V²/2, and a cold wall. Carrying those
through, with the unit conversion done explicitly and the two factors of 10⁶ cancelling while
a single √101325 from the atmosphere unit on pressure does not,

    k = K_air / (2√101325) = 0.1113 / 636.632 = 1.74826×10⁻⁴,

which is **+0.39%** from the 1.74150×10⁻⁴ in the code. The declared tolerance for this row is
the primary's own 3.3%, which is the source's number rather than this project's, and 0.39%
passes it.

**The constant was not changed**, and the reason is that the derivation is less accurate than
the gap it measures. Quantifying each substitution at the baseline condition: the exact
perfect-gas stagnation-pressure coefficient is 1.83937 rather than the Newtonian 2, worth
−4.10% on k; the cold-wall assumption is worth −1.10%; the dropped freestream static enthalpy
+0.81%. Applying all three gives 1.6717×10⁻⁴, which is −4.01% in the *opposite* direction. So
the code's value sits between two defensible derivations, the evidence cannot discriminate
between them, and adopting the fresh number would have shifted every heat flux, surface
temperature and bondline temperature in the repository by 0.4% in exchange for worse
justification.

The exact digits 1.7415 could not be reconstructed from the primary by any route tried, and
their provenance in the secondary literature remains an open item. A test pins the value so
the decision cannot be quietly reversed.

**The useful output was not a number but a bound: treat this correlation as ±4% at best, and
propagate that.**

### G2′: the model form, `LIMITED`, not attempted

G2 being `PASS` says nothing about whether Sutton–Graves is the right correlation for this
problem. Four things are untouched:

- **Catalycity**, which is by far the largest unquantified term. The correlation's basis is an
  equilibrium boundary layer, characterised by secondary sources as equivalent to a fully
  catalytic wall, and catalytic heat flux is reported at roughly twice non-catalytic values at
  comparable conditions. That dwarfs everything settled above.
- **Wall temperature.** The V³ form assumes a cold wall; the surface here reaches about
  2400 K. The bias is conservative.
- **Radiation.** Neglected, which the primary also states of its own study.
- **Domain checking.** The code does not currently reject inputs outside the primary's fitted
  domain. The baseline sits inside it, at ½V² = 27.4 MJ/kg against a fitted range of 2.3 to
  116.2 MJ/kg, but nothing enforces that.

**Every uncertainty figure this project produces is therefore a lower bound**, because this
row has no distribution attached and is not in the uncertainty inventory at all.

---

## 6.4 Effective nose radius: G-GEO2, `PASS` implementation, `LIMITED` physics

Verification covers exactness at all nine tabulated points, both analytic limits (the
hemisphere returning R_eff = R_n to 1e-12, the flat face saturating at 3.155 R_b),
monotonicity in both radii, continuity across the K = 1 seam where the model hands back to
the cap radius, the module's table pinned against its provenance file, and bit-for-bit
reproduction of persisted earlier results under the legacy default.

**The tolerance is the sources' own disagreement rather than this project's**: about 10% at
K = 0 and K = 0.707, and about 20% at K = 0.417, which is about ±10% on heat flux and larger
than the heating constant's own ±4%.

`LIMITED` because every number is zero angle of attack and Mach 8 cold-wall perfect-gas data
transferred to a 7.4 km/s real-air flight condition on the strength of a
pressure-distribution-invariance argument; because the interpolation between the nine points
is this project's construction rather than a published fit; because K > 1 falls back to the
cap radius and is flagged; and because no geometry in this project has been compared against a
measured velocity gradient of its own.

---

## 6.5 TPS conduction: G3 `PASS`, G3b `PASS` (internal)

### G3

Validated against the semi-infinite solid under constant surface flux, checked at four depths
and at the surface, against a declared tolerance of 0.2% and an energy residual below 1e-6.

**Measured: 0.002% surface error and an energy residual of about 1e-14.** Grid refinement and
timestep refinement convergence are both demonstrated, a null test is included, and physical
ordering tests are in place.

The energy residual is worth one sentence of interpretation, because a small number is easy to
quote and easy to misread. It measures the difference between energy entering through the
boundaries and the change in stored energy, as a fraction of the energy in. At 1e-14 it is
floating-point round-off over the number of operations, not a physical tolerance. That is the
expected signature of a conservative finite-volume scheme, where each face flux appears once
with each sign in the two cells it separates. A scheme that was not conservative would show a
residual at the discretisation error level, around 1e-3, and would still look convergent.

**This is the strongest `PASS` in the project, and it is the one the headline claim rests
on**, because the claim is about what happens inside the stack.

### G3b

The bench boundary options added for the coupon experiment (convective loss at both faces,
back-face re-radiation, a series contact resistance) are each verified against closed-form
cases: a steady state with a convective back face and a contact resistance to 1e-4 relative, a
lumped Newton-cooling decay to 2e-3, and energy closure with all four sinks active to 1e-4.
A regression test asserts that the defaults leave the entry model bit-identical.

`PASS` is marked **(internal)** because these are closed-form checks of this project's own
implementation rather than comparisons against an external measurement.

---

## 6.6 What these gates do not buy

Three upgrades moved off `LIMITED` on the strength of opening the cited documents, and each
is narrower than its row title. Stating the narrowing is the point of this subsection.

- **G1A′** validates a *transcription*, at five altitudes, and nothing else. The
  interpolation between them is still a log-linear stand-in for a species-diffusion model, and
  that region supplies 5 to 20% of the second objective's driver.
- **G1B** validates the *integration*, under an exponential atmosphere and constant gravity,
  because that is where a closed form exists. The production configuration remains unreproduced
  against anything external.
- **G2** validates the *constant*, not the correlation. G2′ is untouched and catalycity alone
  is worth about a factor of two.

Two constraint limits were also sourced without being changed. The bondline allowable turned
out to be a real flown limit, the Shuttle's aluminium-structure design temperature. The
deceleration limit turned out to correspond to no documented sustained-g curve at all, and is
carried as an explicit open decision with its measured effect on the feasible region, because
adopting the documented alternative would empty that region entirely, which is a result rather
than a setting.

**The most useful outcome of the whole verification exercise produced no code change.** The
baseline was re-run before and after and is bit-identical: peak heat flux 160.28 W/cm², peak
bondline 494.8 K, maximum 11.89 g. The expectation written down beforehand was that at least
one of the three numbers would be wrong and would have to change. A validation exercise that
ends in "the value was right" is easy to under-value, and the pressure to adopt the freshly
derived constant because it felt like the more rigorous number was real.

---

## Notes for revision

- The status table from `VALIDATION_MATRIX.md` should be reproduced in the paper in full,
  including the `NOT_STARTED` and `LIMITED` rows, rather than filtered to the passing ones.
- §6.6 is the section a hostile reader will look for. It should not be moved to an appendix.
- §6.3's decision not to change the constant reads as a strength only if the arithmetic is
  shown. Keep the three substitution errors with their signs.
