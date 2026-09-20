# 2. Related Work

*Draft. Does not depend on any pending run.*

**Sourcing rule for this section.** Every citation below is one that was opened and read
during this project and recorded in `docs/validation/sourcing_report.md` or in
`docs/theory/*`, or is explicitly marked as a secondary source. Nothing is cited from
memory. Sources that could not be obtained are listed as gaps rather than omitted, because a
gap that is named is a different thing from a gap that is hidden. Tiers follow the project's
own scale: **✅ T1** opened and read in the primary document, **🟡 T2** reputable secondary
only, **❌ T3** could not be sourced.

---

## 2.1 Stagnation-point convective heating correlations

The correlation this project uses originates with Sutton and Graves, who fitted a
stagnation-point heating coefficient to chemical-equilibrium boundary-layer computer
solutions across nine base gases and twenty-two mixtures [1]. Their equation is written in
stagnation pressure and enthalpy,

    q̇_w = K √(p_s / R) (h_s − h_w),

with K = 0.1113 kg·s⁻¹·m⁻³ᐟ²·atm⁻¹ᐟ² for air, an average correlation error of 3.3% and a
maximum of 9.8%, fitted over stagnation enthalpies of 2.3 to 116.2 MJ/kg, pressures of 0.001
to 100 atm, and two discrete wall temperatures of 300 K and 1111 K. The report states
explicitly that radiative heating was neglected.

The familiar form used throughout the entry literature,

    q̇″ = k √(ρ_∞ / R_n) V_∞³,

**does not appear in that report**, and neither does the constant usually attributed to it.
Reaching the V³ form requires three further substitutions: a Newtonian stagnation pressure
p_s ≈ ρV², a total enthalpy h_s ≈ V²/2, and a cold wall. The chain is stated in NASA training
material [2] and in Carroll and Brandis [3], both secondary. This project carried the algebra
through from the primary's own coefficient and units and reports the outcome in §6, together
with the reason the code's constant was not changed.

The standard critical assessment of this class of correlation is Tauber's review work [4].
**The provenance of that citation is unresolved in this repository and must be settled before
submission.** The engineering notebook for the effective-nose-radius work lists NASA TP-2914
among four primaries obtained and read at 400 to 600 dpi, and the effective-nose-radius
derivation uses one qualitative point attributed to Tauber. The sourcing report and the
validation closeout both record the same document as ❌ T3, cited by secondary sources but
not opened. Those two records cannot both be right. Until the conflict is resolved, no
quantitative claim in this paper rests on Tauber, and the citation appears only where the
text says so.

The largest unquantified term in this correlation class is surface catalycity. The
equilibrium-boundary-layer basis is characterised by secondary sources as equivalent to a
fully catalytic wall, and catalytic heat flux is reported at roughly twice non-catalytic
values for comparable conditions [5]. This project does not quantify it, and says so.

---

## 2.2 Stagnation-point velocity gradients on blunt bodies

The `1/√R_n` scaling above is really a statement about the stagnation-point velocity
gradient, and it is exact only for a sphere, where dimensional analysis forces the gradient
to go as 1/R because the nose radius is the only available length. Zoby and Sullivan address
the general blunt body directly: they define an effective radius by declaring the body's
stagnation velocity gradient to be that of a hemisphere of some other radius,

    R_b / R_eff = (dU/dS)_s,BB / (dU/dS)_s,hemi,

their equation (5), and they report the effect of corner radius on the heating ratio, about
11% and about 22% at zero bluntness as the corner ratio goes from 0 to 0.3 [6]. Their method
rests on the stagnation-region pressure distribution being invariant above about Mach 3.5.

Ellison measured the same quantity experimentally on nine models at Mach 8 and a Reynolds
number of 1.37×10⁶, tabulating R_b/R_eff over K = R_b/R_n in {0, 0.417, 0.707} and R_c/R_b in
{0, 0.2, 0.4} [7]. Two features of that table matter for design. The effective radius
**saturates**: for a flat face with a sharp corner it reaches 3.155 R_b rather than heading
for infinity. And a **rounder corner makes heating worse**, because it gives the flow an
easier path around the shoulder, which steepens the acceleration and thins the boundary
layer.

Ellison also states the disagreement between the two sources in his own words: agreement
within 10 percent at K = 0 and K = 0.707, and about 20 percent at K = 0.417 with a sharp
corner [7]. That is a real disagreement in the literature at the geometry this project's
designs occupy, and it is carried as an uncertainty rather than resolved by preferring a
source.

The precedent for substituting an effective radius into a Sutton–Graves-form correlation is
not this project's improvisation: Zoby published exactly that, citing his own earlier work
for the effective radius [8].

**Neither source publishes a formula.** Zoby and Sullivan print faired curves, Ellison prints
a table and two interpolation charts, and a third report of the era instructs the reader to
interpolate from charts. The interpolation used here is therefore this project's own
construction over the primaries' data points and is labelled as such wherever it appears. A
2026 paper whose title describes precisely the published closed-form reconstruction that
would replace it exists and is paywalled [9]; it is the single highest-value follow-up on
this topic and it has not been read.

---

## 2.3 Ballistic entry trajectory solutions

The classical closed-form treatment is Allen and Eggers [10], who derive velocity against
altitude, the altitude and velocity of peak deceleration, and the peak deceleration itself
under a straight flight path, negligible gravity relative to drag, an exponential isothermal
atmosphere, constant drag coefficient and a flat non-rotating Earth. Their peak-deceleration
result,

    (−dV/dt / g)_max = β V_E² sin θ_E / (2ge),

with β the inverse atmospheric scale height, is the standard sanity check for an entry
integrator.

It is also a trap, in two ways. The first is notational: a widely used modern restatement
writes β for the *ballistic coefficient* m/(C_D A), a different physical quantity from the
primary's inverse scale height [11]. The second is more important. Because the closed form
neglects gravity, a correct numerical integrator must **disagree** with it, and increasingly
as entry flattens. Putnam and Braun quantify that disagreement by running three entry cases
through both the closed form and a full numerical integration, publishing peak-deceleration
errors of +34.9%, −5.1% and −57.3% for sample-return, steep-strategic and shallow LEO-return
cases respectively [12]. That published disagreement, rather than agreement with the closed
form, is what an integrator should be validated against, and it is what this project uses in
§6.

For a flight comparison rather than an analytical one, the Stardust entry reconstruction
gives a radar-tracked peak deceleration of 32.89 Earth g against a pre-entry prediction of
32.86 g, with a published 3σ Monte Carlo dispersion of ±3.64 g [13]. That comparison is not
made here, because it needs a drag coefficient for the flown sample-return capsule that could
not be sourced.

Two standard textbook treatments of entry flight mechanics could not be obtained in any
accessible form and are recorded as gaps (❌ T3): Vinh, Busemann and Culp; and Regan and
Anandakrishnan.

---

## 2.4 TPS sizing criteria and bondline allowables

The accepted in-depth criterion in TPS design is a maximum temperature at a single plane.
NASA training material states baseline zero-margin sizing as computed to hit a given bondline
temperature limit, with primary thermal margin applied directly to that criterion and
adhesive failure accounted for by maintaining a conservative bondline limit [2].

The limit itself is a property of the structure, not of the insulator, and flown vehicles
differ accordingly:

| Vehicle | Stated limit | Material system | Tier |
|---|---|---|---|
| Apollo CM (Block II) | 600 °F / 588.7 K | Avcoat on stainless-steel honeycomb | ✅ T1 [14] |
| Space Shuttle Orbiter | 350 °F / 449.8 K | fused-silica tile, Nomex SIP, RTV-560 on aluminium airframe | ✅ T1 [15] |
| Orion (EFT-1) | 500 °F / 533.2 K | Avcoat on composite over titanium | ✅ T1 [16] |

One limitation of that table is recorded rather than smoothed over: CR-159900 states 350 °F
as the *aluminium airframe's* design limit and rates RTV-560 itself to 500 °F, and no primary
sentence was found tying 350 °F specifically to the adhesive line. The often-cited "Shuttle
Tile Story" has no accessible full text and was not verified (❌ T3).

For deceleration limits, no document states a flat scalar. NASA-STD-3001 gives a
duration-dependent sustained acceleration curve, and for a deconditioned crew the applicable
values run from 14.0 g at 0.5 s to 4.0 g beyond 150 s [17]. Published peak decelerations from
crewed entries are 7.6 to 11.1 g for Mercury, 4.3 to 7.7 g for Gemini, 3.3 to 6.8 g for
Apollo and 3 to 4 g for nominal Soyuz [18].

---

## 2.5 Cumulative thermal-exposure metrics

The project defines and then tests a Thermal Penetration Index, a weighted double integral of
temperature exceedance over depth and time. The honest framing is that cumulative
thermal-exposure metrics are an old idea with several independent literatures, and any such
index is a member of that family rather than a departure from it.

The aerothermal member is integrated heat load, Q = ∫ q″ dt, already discussed [2]. The
oncology member is the thermal isoeffective dose of Sapareto and Dewey, CEM43, which converts
any temperature-time history into cumulative equivalent minutes at 43 °C with an exponential
temperature weighting and a physically motivated breakpoint. The original is paywalled and
was not opened; the formula and its citation were read in a consensus paper that reproduces
them [19]. The burn-injury and pyrolysis member is the Arrhenius damage integral originating
with Henriques and Moritz, again read through a review rather than in the original [20]. The
same mathematical form is what charring-ablator response models use for resin decomposition,
with kinetic constants from thermogravimetric analysis [2], which means that for a *real*
charring TPS the cumulative in-depth metric already exists and is integrated by the material
itself. An index of this kind is therefore only interesting for a non-decomposing stack,
which is what this project models.

On whether an index of this exact shape, a depth-and-time double integral of temperature
exceedance inside a TPS, already has a name: a targeted literature search found none in the
sources it could reach, and the NASA TPS-margin literature it surfaced treats bondline
temperature, in-depth thermocouple response and recession as separate design responses rather
than fusing them. **That is a negative search result, not a proof of absence**, and it is not
a novelty claim. Paywalled publisher content, industry-internal TPS design standards and any
export-controlled material were not reachable. The project specification explicitly forbids
claiming such a metric as a new aerospace standard, and no such claim is made.

---

## 2.6 Base drag on blunt bodies

Because the CFD in this project computes forebody drag only, the base contribution has to
come from a stated assumption. The foundational semi-empirical treatment is Chapman [21],
which requires boundary-layer-state input and is not a closed-form Cp(M) relation, and Love
[22], whose method is restricted to turbulent boundary layers at roughly Mach 1 to 4. The
directly useful measurement is Miller's wind-tunnel study of blunted 9° cones from Mach 10.5
to 20, which reports base drag below about 2% of total drag for bluntness ratios of 0.55 to
0.8 across that Mach range [23]. Hoerner gives the qualitative direction, that base drag
falls monotonically with Mach in the supersonic regime and that turbulent boundary layers give
less base suction than laminar [24].

Every quantitative dataset found is low-Reynolds-number wind-tunnel data. Flight-measured
backshell pressure from the Mars 2020 entry exists and would close that gap but is paywalled
and was reached only at abstract level [25]. This is recorded as an unresolved gap.

---

## 2.7 Flown capsule geometries

Nine vehicles were checked in primary sources to establish where a realistic design box sits.
The result is a pattern the project uses and did not assume: shallow spherical-cap capsules
cluster at R_n/D ≈ 1.0 to 1.2 (Apollo 1.20, Mercury 1.07), while blunted sphere-cones cluster
at R_n/D ≈ 0.25 to 0.5 (Viking, Pathfinder, MER and MSL at 0.25 with 70° half-angles;
Stardust 0.281; Hayabusa about 0.50) [26]. Two corrections that came out of checking rather
than assuming are worth recording: Apollo's commonly quoted 32.5° half-angle could not be
confirmed in any primary document, whose baseline configuration gives 33.0°; and Stardust's
R_n/D is 0.281, not the 0.5-plus that had been assumed when the search was scoped, which
belongs to Hayabusa instead.

---

## 2.8 Method citations with no recorded provenance

Four methods are used by the code and cited in generated reports, and none has a provenance
record in this project's sourcing report. They are listed here rather than cited silently,
and **each must be verified against the primary before submission**:

| Method | Used for | Cited as |
|---|---|---|
| Richardson extrapolation and the Grid Convergence Index | CFD mesh independence, safety factor 1.25 | Celik et al. (2008) |
| Saltelli first-order and Jansen total-order estimators | Sobol' sensitivity indices | Saltelli (2010); Jansen |
| Semi-infinite solid under constant surface flux | the conduction solver's analytical benchmark | Carslaw and Jaeger, *Conduction of Heat in Solids*, 2nd ed. §2.9 |
| Billig's shock-shape correlation | CFD inflow boundary placement only, never to adjust a result | Billig; the original is paywalled and the formula was confirmed from three secondary sources, one of which prints a different exponent (3.2 against 3.24) |

The third is the most consequential, because gate G3, the strongest `PASS` in the project,
is measured against it. The solution itself is standard and the agreement is 0.002%, but the
edition, section and printed form should be checked against a copy rather than inherited.

---

## References for this section

Numbering is local and is reconciled at assembly. Full details and how each was read are in
`docs/validation/sourcing_report.md` and `docs/theory/*`.

1. ✅ T1 Sutton, K. and Graves, R. A. Jr., *A General Stagnation-Point Convective-Heating
   Equation for Arbitrary Gas Mixtures*, NASA TR R-376, 1971. NTRS 19720003329. Eq. (33)
   p. 13; SYMBOLS pp. 2–3; Table II p. 39; domain pp. 1–2. Read from 300 dpi page renders.
2. 🟡 T2 NASA TFAWS 2012, *Aerothermodynamics Course*, Lecture 1. Opened and read.
   NASA-authored training material, not peer reviewed.
3. 🟡 T2 Carroll, B. and Brandis, A., "Stagnation Point Convective Heating Correlations for
   Entry into H₂/He Atmospheres", AIAA Aviation 2022. NTRS 20220018610.
4. **Provenance unresolved** Tauber, M., NASA TP-2914, 1989; Tauber and Sutton, 1991. See
   §2.1.
5. 🟡 T2 ONERA/CNES, "Noncatalytic and Finite Catalytic Heating Models for Atmospheric
   Re-entry Codes", 1st International Orbital Debris Conference, 2019.
6. ✅ T1 Zoby, E. V. and Sullivan, E. M., *Effects of Corner Radius on Stagnation-Point
   Velocity Gradients on Blunt Axisymmetric Bodies*, NASA TM X-1067, 1965. NTRS 19660017753.
7. ✅ T1 Ellison, J. C., *Experimental Stagnation-Point Velocity Gradients and Heat-Transfer
   Coefficients for a Family of Blunt Bodies at Mach 8 and Angles of Attack*, NASA TN D-5121,
   1969. NTRS 19690013192. Table I transcribed from a 400 dpi page render.
8. ✅ T1 Zoby, E. V., *Empirical Stagnation-Point Heat-Transfer Relation in Several Gas
   Mixtures at High Enthalpy Levels*, NASA TN D-4799, 1968. NTRS 19680025996.
9. ❌ T3 Rodrigues, "Closed-Form Reconstruction of Zoby–Sullivan Stagnation-Point Heat-Flux
   Scaling", JTHT, 2026. DOI 10.2514/1.T7458. Paywalled, not opened.
10. ✅ T1 Allen, H. J. and Eggers, A. J. Jr., NACA Report 1381, 1958. NTRS 19930091020.
11. 🟡 T2 Wikipedia, "Planar reentry equations". Used for an equation cross-check only,
    checked by hand against [10].
12. ✅ T1 Putnam, Z. R. and Braun, R. D., "Extension and Enhancement of the Allen–Eggers
    Analytical Ballistic Entry Trajectory Solution", JGCD 38(3), 2015. DOI 10.2514/1.G000846.
    Table 2, p. 419.
13. ✅ T1 Desai, P. N. and Qualls, G. D., "Stardust Entry Reconstruction", AIAA 2008-1198.
    NTRS 20080008567.
14. ✅ T1 Pavlosky, J. E. and St. Leger, L. G., *Apollo Experience Report: Thermal Protection
    Subsystem*, NASA TN D-7564, 1974. NTRS 19740007423, p. 2.
15. ✅ T1 Smith, Hamermesh and Hogenson, NASA CR-159900, 1979. NTRS 19790012947, p. 1.
16. ✅ T1 Vander Kam and Gage, "Estimating Orion Heat Shield Failure Due to Ablator Cracking
    During the EFT-1 Mission", JSR. DOI 10.2514/1.A35003, NTRS 20160007549.
17. ✅ T1 NASA-STD-3001 Vol 2 Rev F, Table 6.5-1.
18. ✅ T1 NASA TM-104753, 1992. NTRS 19930020462.
19. 🟡 T2 Martin et al. (ITRUSST), "ITRUSST Consensus on Standardised Reporting for
    Transcranial Ultrasound Stimulation", arXiv:2402.10027, 2024, §4.3 eq. (5). Opened; the
    Sapareto and Dewey 1984 original is paywalled and was not opened.
20. 🟡 T2 Ye, H. and De, S., "Thermal injury of skin and subcutaneous tissues", 2016,
    PMC5459687. Opened; the Henriques originals were not.
21. ✅ T1 Chapman, D. R., NACA Report 1051, 1951. NTRS 19930090963.
22. ✅ T1 Love, E. S., NACA TN 3819, 1957. NTRS 19930084517.
23. ✅ T1 Miller, C. G. III, NASA TN D-4800, 1968. NTRS 19680026196.
24. ✅ T1 Hoerner, S. F., *Fluid-Dynamic Drag*, 1965, Ch. XVI.
25. 🟡 T2 Karlgaard, Schoenenberger and Van Norman, "Base Drag Model Derived from Mars 2020
    Backshell Pressure Measurements", JSR 60(6), 2023. DOI 10.2514/1.A35774. Paywalled,
    abstract level only.
26. ✅ T1 NASA/TM-2005-213457 (Apollo, NTRS 20060008942); Erb and Jacobs (Mercury);
    Wilmoth, Mitcheltree and Moss, AIAA 97-2510 (Stardust); NTRS 20060017066 (Viking);
    Spencer et al., AAS 98-146 and NTRS 20040090463 (Pathfinder); NTRS 20120011936 and
    NTRS 20090024218 (MSL); Passamaneck, JPL TR 32-1327, NTRS 19690003885; NTRS 20160000307
    (Hayabusa). Soyuz geometry: ❌ T3, no primary numeric source found.
27. ✅ T1 *U.S. Standard Atmosphere, 1976*, NOAA-S/T 76-1562 / NASA-TM-X-74335, Table I
    pp. 68–69. Read from 300 dpi page renders.

---

## Notes for revision

- The four unverified method citations in §2.8 are a real defect and are written as one.
  Resolving them is on the assembly checklist.
- The Tauber provenance conflict is the other one. It is stated in the body rather than
  hidden in a note because it is a conflict between two of this project's own records.
- Do not add a paragraph on multi-objective optimisation literature or on machine learning
  for surrogate modelling unless sources for it are actually opened. There is no verified
  sourcing for either in this repository, and a related-work section that cites from memory
  in one subsection undermines the seven that do not.
