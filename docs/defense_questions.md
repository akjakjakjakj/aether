# Defence questions

The final repository must be explainable by the student without AI assistance. These are the
questions to be able to answer cold. Answering "the model said so" is a fail.

**How to use this file.** Each entry has four parts:

- **Q** — the question, in the form an examiner would actually ask it.
- **A** — a model answer at the level this project is pitched: the idea first, then the
  maths. Answering in the examiner's own words is better than reciting this one.
- **Evidence** — where the claim lives. File paths plus the section heading or test name,
  rather than line numbers, because line numbers go stale and a wrong pointer in a defence
  is worse than no pointer.
- **Push** — the follow-up a good examiner asks next, and how to meet it.

**Updated 2026-09-21.** M4 (re-run at Fidelity 1), M5, M6 and M7 have run, and the answers
that were marked `[PENDING FINAL RUN]` have been filled from the generated milestone reports
and their hand-written addenda, with the file named beside each number. The filling was done
by the AI assistant; say these answers in your own words and check each against its file
before relying on it. **`[PENDING — STUDENT]`** marks what still has no answer because it
depends on the physical experiment (M8) or on external review. For those, the correct answer
is "the support package is built and checked on synthetic data, the criterion will be
declared before the run, and the run has not happened."

Several *main* answers below were written on 2026-09-20 and still describe the Fidelity-0
state (for example Q30's indices, and any answer that says the drag surface is provisional or
that M5, M6 or M7 has not run). The filled *Push* answers are current. Bringing the main
answers up to date is part of reading the code, and is the student's.

---

## 1. Peak versus cumulative heating

### Q1. Why does stagnation heating scale as V³ but only as √ρ? What does that imply about *when* during an entry peak heating occurs relative to peak deceleration?

**A.** Sutton–Graves is `q̇″ = k √(ρ/R_n) V³`. The velocity cube comes from the energy the
flow carries: the mass flux into the shock layer goes as ρV, and the energy per unit mass
goes as V²/2, so the energy flux goes as ρV³; the boundary layer passes a fraction of it to
the wall. The half-power on density comes from the boundary layer's thickness, which goes
as 1/√(velocity gradient) and therefore brings a √ρ rather than a ρ.

Because V is cubed and ρ only rooted, heating is dominated by velocity. Drag deceleration
goes as ρV², one power of V lower and one power of ρ higher, so it is relatively more
sensitive to density. Descending, velocity falls slowly at first while density climbs
exponentially. Heating therefore peaks **earlier and higher** than deceleration, where the
vehicle is still fast and the air is still thin. For the baseline capsule, peak heating is
at Mach 19.4 and peak deceleration at Mach 12.2.

**Evidence.** `src/aether/heating/sutton_graves.py`;
`tests/test_heating.py` (V³, √ρ and 1/√R_n scaling tests);
`reports/milestones/M3_coupled_model.md` §7 for the two Mach numbers.

**Push.** *"Show me that the exponents in your code are the exponents you just claimed."*
The tests assert the ratios to 1e-12 by evaluating the function at scaled inputs, not by
inspecting the source. That is the right way to test an exponent.

---

### Q2. Explain in one sentence why a *lower* peak heat flux can produce a *hotter* bondline.

**A.** Peak heat flux is a surface quantity at one instant; bondline temperature is what is
left after the whole heat pulse has been low-pass filtered by conduction through the stack,
so a longer, gentler pulse can deliver more total energy deep into the material even though
its maximum is smaller.

The mechanism in full: a shallower entry decelerates in thinner air over a longer time.
Peak flux falls because q̇″ ∝ √ρ·V³, but the pulse lengthens and the integrated external
load rises. A short intense pulse is absorbed near the surface and re-radiated away at T⁴
before it can diffuse inward. A long mild pulse has time to reach the bondline. In M1,
going from −8.00° to −1.50° entry angle cut peak flux by 38.3% (230.64 to 142.38 W/cm²)
while raising integrated load from 79.3 to 128.3 MJ/m² and the bondline from 423.7 K to
537.8 K, 114.1 K hotter.

**Evidence.** `reports/milestones/M1_burn_vs_bake.md` §"Mechanism" and §"Strongest
counterexample"; `reports/figures/M1_mechanism.png`.

**Push.** *"Is that a general result or a result about your stack?"* It is about this
stack. NR-03 shows the effect can be designed away by brute-force insulation: at 40 mm the
bondline moved 9 K across the entire entry, because the diffusion length √(αt) over a 245 s
entry is about 15 mm. The claim is about where the interesting trade lives, not that every
vehicle is at risk.

---

### Q3. Why does the bondline temperature peak *after* aeroheating has stopped?

**A.** Heat already inside the TPS keeps diffusing inward once the surface stops receiving
flux, and the surface is simultaneously re-radiating, so the interior is being fed from
stored energy rather than from the flow. The bondline peak therefore lags the heat pulse by
minutes.

This is not a subtlety that was reasoned out in advance; it was a bug. The first version of
the evaluator ended the conduction solve when the trajectory reached terminal altitude and
under-reported the bondline peak by about 50 K for a 20 mm stack. The evaluator now
continues the solve at zero incident flux for a configurable soak period, default 1200 s,
with re-radiation still active, and it lives inside `evaluate_design` so it cannot be
forgotten in a study script.

**Evidence.** `docs/negative_results.md` NR-02; `ASSUMPTIONS.md` A-TPS-5;
`tests/test_tps.py::test_bondline_peak_lags_the_heat_pulse`.

**Push.** *"How do you know 1200 s is enough?"* Every candidate carries a diagnostic for
the bondline warming rate at the end of the window. In the M4 DOE the largest was
−2.13×10⁻² K/s, i.e. every design was already cooling when the window closed, and zero
designs were truncated. `reports/milestones/M4_pareto_optimisation.md` §11.

---

### Q4. What is the ballistic coefficient, and why does lowering it move peak deceleration to higher altitude?

**A.** β = m/(C_D·A), mass over drag area. It measures how hard the vehicle is to stop. A
low-β vehicle is light for its frontal area, so it feels a given deceleration at a lower
dynamic pressure, which it reaches higher up where the air is thinner. A high-β vehicle
punches deeper before the air can stop it.

Consequences for this project: lowering β raises the altitude of the whole event, which
lowers peak heat flux (less density at peak heating) and lengthens the entry (more
integrated load). That is why both M1b optima ran to the largest available diameter, and why
that was a problem rather than a result: the diameter *bound*, not the physics, was
selecting them.

**Evidence.** `reports/milestones/M1_burn_vs_bake.md` §M1b table (β = 257.9 baseline
against 41.3 for both optima) and its closing paragraph; `ASSUMPTIONS.md` A-LIM-3.

**Push.** *"So the answer to everything is a bigger capsule?"* Only because nothing charged
for it. Once the heat-shield mass-closure constraint was added, the optimiser's preference
for diameter ran into a shield weighing as much as the vehicle (NR-13). A sourced mass
budget, or a mass model where vehicle mass grows with size, is the open item.

---

## 2. Sutton–Graves and the heating model

### Q5. State three assumptions built into Sutton–Graves that would be violated at lunar-return speed.

**A.** (i) **Convective heating only.** Shock-layer radiative heating is neglected, which
is defensible at about 7.4 km/s with a metre-scale nose and indefensible at lunar-return
speeds where radiation becomes a major term. (ii) **Cold wall.** The V³ form assumes the
wall enthalpy is negligible against stagnation enthalpy; the surface here reaches about
2400 K, and the correction grows as velocity falls. (iii) **Equilibrium boundary layer,
i.e. effectively a fully catalytic wall.** A non-catalytic surface is reported at roughly
half the catalytic heat flux for comparable conditions, and this is the largest
unquantified term in the whole heating chain. A fourth, if asked: the fitted domain is
2.3–116.2 MJ/kg stagnation enthalpy and 0.001–100 atm, and the code does not currently
reject inputs outside it.

**Evidence.** `ASSUMPTIONS.md` A-HEAT-2, A-HEAT-3, A-HEAT-4;
`VALIDATION_MATRIX.md` row G2′ (`LIMITED`, *not attempted*);
`docs/theory/sutton_graves_constant.md` §6.

**Push.** *"Which way do those biases push your headline result?"* Neglecting radiation
under-predicts total heating, more so for the steep hot case, which makes the reported
anti-correlation **conservative**. Cold wall over-predicts flux into a hot surface, also
conservative. Catalycity is not signed, which is why it is `LIMITED` and not "small".

---

### Q6. Your code uses k = 1.7415×10⁻⁴ and cites NASA TR R-376. Is that citation correct?

**A.** Not as it was originally written. TR R-376 contains neither the constant nor the
equation form. It gives `q̇ = K√(p_s/R)(h_s − h_w)` with K(air) = 0.1113 in
kg·s⁻¹·m⁻³ᐟ²·atm⁻¹ᐟ², and the V³ form is a later simplification that needs three
substitutions the report does not make: Newtonian stagnation pressure p_s ≈ ρV², total
enthalpy h_s ≈ V²/2, and a cold wall. Carrying those through in the report's own units
gives k = K/(2√101325) = 1.74826×10⁻⁴, which is +0.39% from the code's value.

**The constant was not changed**, and the reason matters more than the number: each
substitution carries more error than 0.39%. The exact perfect-gas stagnation-pressure
coefficient is 1.83937 rather than the Newtonian 2, worth −4.10% on k; the cold-wall
assumption −1.10%; the dropped freestream enthalpy +0.81%. Applying all three gives
1.6717×10⁻⁴, −4.01% in the opposite direction. And the primary's own fit carries 3.3%
average error for air. So the code's value sits between two defensible derivations and the
evidence cannot pick between them. The honest output of the exercise is a bound: treat this
correlation as ±4% at best, and propagate it.

**Evidence.** `docs/theory/sutton_graves_constant.md` (the full derivation, step by step,
with the unit check on K); `docs/negative_results.md` NR-12;
`docs/validation/sourcing_report.md` §1;
`tests/test_heating.py::test_constant_is_exactly_the_value_every_result_was_computed_with`
and `::test_constant_matches_rederivation_from_tr_r376`.

**Push.** *"Then where do the digits 1.7415 come from?"* Unknown. They could not be
reconstructed from the primary by any route tried: eq. (42)'s leading 0.1106 gives
1.73728×10⁻⁴ and eq. (41) at a wall Prandtl number of 0.71 gives 1.71805×10⁻⁴. The
earliest located statement of the V³ form with this constant is NASA TFAWS 2012 training
material, which is a 🟡 T2 source. The provenance of the fifth significant figure is an
open item and is listed as one.

---

### Q7. Your capsule's nose radius is 4 m and its body radius is 1.7 m. Which of those belongs in `1/√R_n`, and why?

**A.** Neither, exactly. `1/√R_n` is not a statement about the radius of the round thing at
the front; it is a statement about the **stagnation-point velocity gradient**, (dU/dS)_s,
the rate at which flow accelerates sideways as it escapes the stagnation point. Heating
follows it because the stagnation boundary layer is continuously swept away by that
accelerating flow and continuously rebuilt, so its thickness is δ ~ √(ν/(dU/dS)_s), and
conduction across it gives q̇″ ∝ √((dU/dS)_s).

For a sphere the only available length is its radius, so dimensionally the gradient *must*
go as 1/R, and substituting gives the familiar 1/√R. **That is a property of spheres.** For
a shallow cap the flow reaches the shoulder within about a fifth of a quarter-circle from
the tip, and the distance over which pressure falls from its stagnation value is set by the
**body** radius and the corner, not by the cap's curvature. So the flow accelerates faster
than the cap radius suggests, and the benefit of flattening saturates.

The repair, which both primaries use, is to keep the sphere formula and change the radius
fed to it: define R_eff as the radius of the hemisphere that would produce the actual
gradient. For this project's front designs R_eff ≈ 0.69 × the cap radius, i.e. about 2.77 m
against a cap radius of 4.01 m, and peak heating is about 20% higher than the legacy model
said. The sanity check to remember: R_eff must sit **between** the body radius and the cap
radius for a shallow cap. If a calculation puts R_eff above R_n for K ≤ 1, it is wrong.

**Evidence.** `docs/theory/effective_nose_radius.md` §§1–4 (derivation and the worked
number); `src/aether/geometry/stagnation_gradient.py`;
`data/reference/stagnation_velocity_gradient.yaml` (provenance and verbatim quotations);
`tests/test_stagnation_gradient.py` (49 tests).

**Push.** *"Where did the numbers in that interpolation come from, and is the interpolation
yours?"* The nine values are Ellison, NASA TN D-5121 (1969), Table I, α = 0 rows,
transcribed from a 400 dpi page render: measured R_b/R_eff at Mach 8 over K = R_b/R_n ∈
{0, 0.417, 0.707} and R_c/R_b ∈ {0, 0.2, 0.4}, plus an exact hemisphere anchor at K = 1
which is not measured but follows identically from Zoby & Sullivan's eq. (5). **Neither
source publishes a formula**, so the interpolation, shape-preserving cubic in K and linear
in R, is this project's construction and is labelled as such everywhere. The saving grace
is that all 64 front designs land at K = 0.417–0.425 and R_c/R_b = 0.200, essentially on a
tabulated point, so almost nothing is being interpolated.

---

### Q8. What is the uncertainty on that correction?

**A.** Larger than the Sutton–Graves constant's. Ellison p. 5, verbatim: "The data of the
present investigation agree with the results of Zoby and Sullivan (ref. 6) within 10
percent for K = 0 and K = 0.707; however, for K = 0.417 and R = 0, the disagreement is
about 20 percent." K = 0.417 is exactly where this project's front sits. Twenty percent on
R_eff is about ±10% on heat flux, against ±4% on the constant (A-HEAT-1). It is a real
disagreement between two primary sources and is carried as an uncertainty rather than
resolved by preferring one. Ellison is used because it is tabulated rather than read off a
graph, is an experiment rather than a computation from someone else's pressure data, and is
the conservative of the two (smaller R_eff, more heating).

**Evidence.** `docs/theory/effective_nose_radius.md` §5; `ASSUMPTIONS.md` A-GEO-3a;
`VALIDATION_MATRIX.md` row G-GEO2 (`PASS` implementation / `LIMITED` physics);
`ASSUMPTIONS.md` A-UQ-NOSE-1 for how it is sampled.

**Push.** *"Why is it a discrete switch in your uncertainty model and not a Gaussian?"*
Because that is what the evidence is. Two reports disagree, one is closer to right, there
is no continuum between them and no frequency to be normal about. The 50/50 split is
declared indifference between two primaries, not a measured frequency, and the entry lists
three ways the alternative state is wider than the source strictly licenses.

---

## 3. Conduction and numerics

### Q9. Write down the diffusion timescale of the TPS stack. Why does it matter that it is comparable to, not much shorter than, the entry duration?

**A.** The relevant group is t_diff ~ L²/α, with α = k/(ρc_p) the thermal diffusivity.
Equivalently, the depth heat reaches in time t is the diffusion length √(αt). For this
stack α ≈ 8.9×10⁻⁷ m²/s, so over a 245 s entry √(αt) ≈ 15 mm.

If t_diff ≫ t_entry the bondline never hears about the entry and there is no trade to study;
if t_diff ≪ t_entry the stack is effectively in quasi-steady state and the bondline just
tracks the surface, so again nothing interesting happens. The burn-vs-bake effect lives
exactly where the two are comparable, because that is where "how long the pulse lasted"
changes the answer and not just "how big it was". That is why the stack was sized to 15 mm.

**Evidence.** `docs/negative_results.md` NR-03; `ASSUMPTIONS.md` A-TPS-7.

**Push.** *"So you chose the thickness to make your effect appear."* The thickness was
chosen to be the design point where the bondline is a live constraint, which is also the
realistic one: nobody flies 2.5× more insulation than the thermal problem requires, because
it is all mass. NR-03 states plainly that the effect *can* be insulated away at a mass cost.
The honest framing is that the result identifies where the trade lives, not that every
vehicle is exposed to it.

---

### Q10. Why backward Euler rather than forward Euler? What is the explicit stability limit for this mesh?

**A.** Backward Euler is unconditionally stable for diffusion; forward Euler is not. The
explicit limit is Δt ≤ Δx²/(2α). With 140 cells over a 25 mm stack, Δx ≈ 1.8×10⁻⁴ m, so
Δx² ≈ 3.2×10⁻⁸ m², and with α ≈ 8.9×10⁻⁷ m²/s the limit is of order 0.018 s. Over a 245 s
entry plus a 1200 s soak that is roughly 10⁵ timesteps for stability reasons alone, against
the ~2800 implicit steps actually taken. Backward Euler is first-order in time, which is
paid for with more steps than Crank–Nicolson would need, and that trade is an open item
recorded in `PROJECT_STATUS.md`.

**Evidence.** `src/aether/tps/` solver module; `tests/test_tps.py` (timestep-refinement
convergence); `PROJECT_STATUS.md` open item 7.

**Push.** *"First order in time, and you claim 0.002% accuracy?"* The 0.002% is against the
Carslaw & Jaeger analytical solution at the converged timestep, and it is a statement about
the converged answer, not about the order of the scheme. The timestep-refinement test is
the separate claim.

---

### Q11. Why must interface conductivity be a harmonic and not an arithmetic mean?

**A.** At a layer interface the physically conserved quantity is the heat *flux*, and two
slabs in series add **thermal resistances**, not conductivities. The resistance of each
half-cell is Δx/(2k), so the combined conductance is the reciprocal of the sum of the
resistances, which is the harmonic mean weighted by the half-cell widths. An arithmetic
mean would let a highly conductive layer dominate the interface and would pass too much
heat across a strong conductivity contrast, which for an insulator-on-aluminium stack is
exactly the interface that decides the bondline temperature. The scheme is conservative
because each face flux appears once with each sign in the two cells it separates.

**Evidence.** `src/aether/tps/` (interface conductivity); `tests/test_tps.py` (energy
balance closes to ~1e-14; multilayer ordering tests).

**Push.** *"Prove the scheme is conservative."* The energy-balance residual measures
exactly that: the difference between energy entering through the boundaries and the change
in stored energy, as a fraction of the energy in. It closes to about 1e-14, which is
floating-point round-off over the number of operations, not a physical tolerance. If the
scheme were not conservative the residual would be at the discretisation error level, about
1e-3, not at machine precision.

---

### Q12. The radiating boundary condition is nonlinear. How is it handled, and why did the first approach diverge?

**A.** The surface energy balance is `q_net = q_conv − εσ(T_s⁴ − T_sink⁴)`. The first
implementation solved it by damped fixed-point iteration, and at realistic entry fluxes of
about 2 MW/m² the surface temperature overflowed to infinity. The reason is that
fixed-point iteration on a T⁴ law has local gain 4εσT³·R_half; at T ≈ 2000 K that gain
exceeds 1, so the iteration is divergent and damping only slows the divergence.

The fix is to Newton-linearise the radiation term about the current surface estimate:
`q_rad ≈ q_rad(T*) + h_rad(T_s − T*)` with `h_rad = 4εσT*³`. That makes the surface flux
affine in the unknown so it folds directly into the tridiagonal system, and because h_rad
only ever *adds* to the diagonal the scheme is unconditionally stable.

**Evidence.** `docs/negative_results.md` NR-01; `AI_USAGE.md` (row: Newton linearisation,
AI-proposed / student-approved, proposed in response to an actual divergence).

**Push.** *"Is an explicit treatment merely less accurate, or actually wrong?"* Actually
unstable, which is the instructive part. The failure was not a slightly wrong number; it
was `array must not contain infs or NaNs`.

---

### Q13. Grid convergence was demonstrated. What is the observed order of accuracy in space, and does it match theory?

**A.** The spatial scheme is second-order finite volume with harmonic interface
conductivities, so the expected observed order is 2 in smooth regions. The grid-refinement
test measures it by comparing successive refinements rather than assuming it.

The important distinction, which an examiner will probe: **the TPS grid convergence (G3) is
demonstrated and the CFD grid convergence (G4) is not.** Those are two different questions
and only the first is closed.

**Evidence.** `tests/test_tps.py` (grid-refinement convergence); `VALIDATION_MATRIX.md`
row G3 (`PASS`, 0.002% against Carslaw & Jaeger §2.9, energy residual ~1e-14) against row
G4 (`NOT_STARTED`/gated).

**Push.** *"Show me the analytical solution you validated against."* Carslaw & Jaeger,
*Conduction of Heat in Solids*, 2nd ed. §2.9: a semi-infinite solid under constant surface
flux. It is an external published result, checked at four depths and at the surface, which
is what makes G3 a `PASS` rather than an internal consistency check.

---

### Q14. What does geopotential altitude mean and why does USSA-76 use it?

**A.** Geopotential altitude is the altitude you would need at constant surface gravity to
have the same gravitational potential energy as the real altitude in a gravity field that
weakens with height. Using it lets the hydrostatic equation be integrated with g held
constant, which is what makes USSA-76's layer profiles exact closed forms rather than
numerical integrations. The conversion is H = R_e·Z/(R_e + Z). This project computes the
0–86 km region exactly from the standard's defined layer profile, and the 86–150 km region
is a different matter entirely (see Q17).

**Evidence.** `src/aether/atmosphere/`; `tests/test_atmosphere.py::test_layer_boundaries_against_published_table`;
`VALIDATION_MATRIX.md` row G1A (`PASS`, 0.01% on T and 0.1% on p).

**Push.** *"Is your atmosphere validated everywhere you fly?"* No. See Q17.

---

## 4. Trajectory and coupling

### Q15. In the 3-DOF equations, where does the term V²cos γ / r come from and what would happen if it were dropped?

**A.** It is the centrifugal term in the flight-path-angle equation. Working in a frame
following the vehicle around a spherical Earth, the path must curve to stay at constant
radius, and V²cos γ / r is the angular rate that curvature demands. The γ equation is
roughly dγ/dt = (1/V)[L/m − g cos γ] + (V cos γ)/r, where the last term expresses that a
vehicle moving fast enough near the surface needs less gravity turning to hold its path.

Dropping it makes every trajectory turn downward too fast: the entry would appear steeper
than it is, giving too high a peak deceleration and too short a duration. For a near-orbital
entry at 7.4 km/s the term is not small, because V²/r is of the same order as g.

**Evidence.** `src/aether/trajectory/` equations of motion; `AI_USAGE.md` lists the 3-DOF
equations as **External** with the note that the student must be able to derive dγ/dt
including this term; `tests/test_trajectory.py` (physical-ordering tests).

**Push.** *"Then why is your integrator's peak-g allowed to disagree with a published
closed form by 58%?"* Because the closed form neglects gravity entirely. See Q16.

---

### Q16. You validated the trajectory integrator against Allen–Eggers and the disagreement is up to 58%. Explain why that is a pass.

**A.** Allen–Eggers (NACA Report 1381, 1958) is a closed-form ballistic entry solution that
assumes a straight flight path, gravity negligible against drag, an exponential isothermal
atmosphere and constant C_D. Those assumptions are good for steep entry and get worse as
entry flattens, because a shallow entry spends a long time with gravity doing real work. So
a **correct** numerical integrator must disagree with the closed form, and increasingly so
at shallow angles. Agreement to a few percent everywhere would be evidence of a bug or of a
circular comparison.

The validation therefore does not compare against the closed form; it reproduces a
**published disagreement**. Putnam & Braun (JGCD 38(3), 2015, Table 2, p. 419) run three
entry cases through both the closed form and their own full numerical integration and
publish the gap. This project reproduces all nine published figures to within 0.92
percentage points, with the tolerance declared as 1.0 point:

| case (γ₀) | quantity | AETHER vs AE | published | residual |
|---|---|---|---|---|
| −30.0° | peak deceleration | −5.89% | −5.1% | 0.79 |
| −8.2° | peak deceleration | +35.82% | +34.9% | 0.92 |
| −1.35° | peak deceleration | −58.18% | −57.3% | 0.88 |

**Evidence.** `VALIDATION_MATRIX.md` row G1B (`PASS`) with the full nine-figure table;
`tests/test_trajectory_allen_eggers.py` (10 tests);
`src/aether/trajectory/allen_eggers.py`; `src/aether/atmosphere/exponential.py`;
`docs/engineering_notebook/2026-09-20_validation_closeout.md`.

**Push.** *"What did you have to change to get that agreement, and does it contaminate your
production results?"* Three things, all opt-in and all defaulting off: an
`ExponentialAtmosphere` (a validation instrument, not a model of the air, A-ATM-5), and
`gravity_m_s2` / `planet_radius_m` overrides so the reference's constant g = 9.81 and
R = 6378 km can be matched (A-TRAJ-5). Matching the gravity model moved the agreement by up
to 1.3 percentage points, which is the size of the effect.
`test_production_default_is_unchanged_by_the_validation_hooks` asserts the default path is
bit-identical. Two further honest notes: the raw `argmax` altitude was quantised by the
solver's output grid and initially looked like a real +5.16% discrepancy until parabolic
refinement through the three samples around the peak fixed it, and the reference paper is
internally inconsistent about ρ₀ (1.215 vs 1.225 kg/m³) and about one velocity figure; the
value attached to the cases was used and the inconsistency is recorded rather than smoothed
over.

---

### Q17. Which validation rows are `LIMITED` rather than `PASS`, and what specifically is missing from each?

**A.** As of the last update:

- **G1A′ (atmosphere 86–150 km)** — split. `PASS` for the *transcription* at 90, 100, 110,
  120 and 150 km, which agree with a primary copy of USSA-76 Table I to every printed digit.
  `LIMITED` for the 86, 95 and 130 km rows, the entire pressure column, and the
  log-interpolation *between* rows, which is a stand-in for the species-diffusion model
  USSA-76 actually defines above 86 km.
- **G2′ (heating model form)** — *not attempted*. Catalycity, hot wall, radiation, and no
  domain checking against the primary's fitted range.
- **G-GEO (capsule geometry)** — `PASS` internally, `LIMITED` because every check is
  against another computation this project derived; no published capsule moldline has been
  reproduced.
- **G-GEO2 (effective nose radius)** — `PASS` implementation, `LIMITED` physics: α = 0,
  Mach 8 cold-wall perfect-gas data transferred to a 7.4 km/s real-air condition, and this
  project's own interpolation between nine points.
- **G4 (CFD)** — `NOT_STARTED` as a gate: mesh independence and the published benchmark are
  both incomplete.
- **G5 (coupled model)** and **M3 (drag surface)** — `LIMITED`, and G5 cannot be better than
  the surface it stands on, which is PROVISIONAL.
- **§44 (TPI)** — `LIMITED` with verdict DISCARD, because it is a result about one stack and
  one two-variable design space.
- **M8 (coupon)** — `IN_PROGRESS`; no measurement exists.

**Evidence.** `VALIDATION_MATRIX.md` in full, and its closing section "The three 2026-09-20
upgrades, and what they did *not* buy".

**Push.** *"Which `LIMITED` row most threatens your headline claim?"* G1A′, and not for the
reason it looks. NR-14 measured that 5–20% of a *feasible* design's integrated heat load
accrues above 86 km, and the bondline objective responds to the integrated load. So the
second of the two objectives draws up to a fifth of its driver from a log-interpolated table
and from a continuum correlation applied where the flow is transitional. That promotes
finishing G1A′ from housekeeping to a prerequisite for trusting bondline differences of a
few kelvin between front designs.

---

## 5. CFD

### Q18. Why is your CFD forebody-only, and what does that cost you?

**A.** Because an inviscid wake never settles. With the full sphere in the domain, forebody
drag converged to within about ±0.1% while the **afterbody** contribution kept climbing
through 20 000 iterations (roughly 0.09 at 3000, 0.12 at 20 000, still rising), and the
density residual stalled at about a quarter of its starting value. The reason is physical,
not numerical: in the Euler equations nothing fixes the base pressure of a bluff body. The
recirculation behind it exists only through numerical dissipation, so its pressure is a
property of the mesh and the scheme. Even a converged value would not have been
trustworthy.

The production domain therefore runs from the nose to the maximum-radius station and closes
with an outflow plane where the flow is supersonic, so nothing downstream can influence the
solution. The pipeline measures the minimum outflow Mach number on every case, because the
zero-gradient outflow condition is only well posed if it exceeds 1.

The cost, accepted and written down: **base drag is not computed.** The trajectory needs a
total C_D, so M3 adds a separately stated base-pressure assumption with its own band, and
the sphere's measured *total* drag cannot be compared like for like, which is why that part
of the benchmark is `LIMITED`.

**Evidence.** `docs/negative_results.md` NR-06; `ASSUMPTIONS.md` A-CFD-4, A-CFD-5 and its
M3 update; `docs/validation/M2_model_form_limits.md`;
`reports/milestones/M3_coupled_model.md` §8.

**Push.** *"So where does base drag come from?"*
`C_D,base = (1 − p_b/p∞)·2/(γM²)·(A_base/A_ref)`, which is algebra. All the uncertainty is
in the base-pressure ratio, which is **bounded, not predicted**: 0 at the exact vacuum limit
up to 1 for M ≤ 6 and up to 3 for M ≥ 10, the upper end read off figure 11(b) of NASA TN
D-4800 (Miller 1968) by eye on a log scale, ±30%. The 1/M² factor makes the term small
exactly where the heating happens: the nominal base share is 5.4–8.4% of total C_D at Mach 3
and essentially zero above Mach 10. The thing expected to be the weak point turned out to
matter least.

---

### Q19. Why inviscid rather than laminar Navier–Stokes?

**A.** Three reasons. Blunt-forebody drag is pressure drag, so the quantity of interest
survives. A laminar boundary layer at flight Reynolds number would need wall-normal
resolution the design-point budget cannot afford, and it would still not be turbulent, so it
would not be right either. And an inviscid solver has exact, like-for-like references
available: the Rayleigh-pitot stagnation-pressure relation, and Van Dyke & Gordon's inviscid
stand-off data.

There is a fourth reason that is really a safety property: **an inviscid solver has no
thermal boundary layer, so it has no heat flux to report.** That removes the temptation to
read a wall heat flux off a solution that could not support one. Heating stays with
Sutton–Graves, and nothing computed by the CFD may be used to modify or calibrate the
heating model.

**Evidence.** `ASSUMPTIONS.md` A-CFD-1, A-CFD-2; `docs/validation/M2_model_form_limits.md`
§"Forbidden uses" (first bullet: "Heating. Any heating.").

**Push.** *"Name three things you are forbidden to use this CFD for."* Heating of any kind;
shock-layer temperature, density or species as flight quantities; total drag including the
base as a CFD result. Also flight shock stand-off, lift, moments, stability, angle of attack,
subsonic and transonic flight, and rarefied flow.

---

### Q20. What is mesh independence, why does it need three meshes, and what is a GCI?

**A.** Mesh independence is the demonstration that the answer has stopped changing as the
mesh is refined, so what is left is physics rather than discretisation. Two meshes only tell
you the answer *moved*; they cannot tell you whether it is converging, and at what rate, or
let you extrapolate to zero cell size.

With three geometrically similar meshes at a constant refinement ratio r you can do
Richardson extrapolation. If φ is the quantity and φ₁, φ₂, φ₃ are fine, medium and coarse,
the observed order is p = ln|(φ₃−φ₂)/(φ₂−φ₁)| / ln r, and the extrapolated value is
φ_ext = φ₁ + (φ₁−φ₂)/(rᵖ−1). The **Grid Convergence Index** turns that into a reported
uncertainty band: GCI = F_s·|(φ₁−φ₂)/φ₁|/(rᵖ−1) with a safety factor F_s = 1.25, following
Celik et al. (2008). It is an error *estimate* with a margin, not an error bound.

**This project does not have one yet.** The M2 report prints "GCI not available: fewer than
three successful mesh levels at any Mach." The declared rule, written before the runs, is
that forebody C_D must converge monotonically with GCI_fine ≤ 2% and a fine-to-medium
change ≤ 1%.

**Evidence.** `reports/milestones/M2_cfd_validation.md` §"Condition 1 — mesh independence";
`configs/cfd_validation.yaml`; `ASSUMPTIONS.md` A-CFD-9.

**Push.** *"What breaks downstream because you have no GCI?"* Three things, and they are
all wired to refuse rather than to guess. The M3 drag surface's discretisation band reads
`results/M2/<run>/gci.csv` through a hook that currently returns `available = False`, and no
number has been typed in its place. M7's `cd_discretisation` input declares
`when_unavailable: refuse` for that requirement, so selecting the CFD surface **stops the
run**, naming the input and the file, rather than propagating one fewer C_D term. And gate
G5 is `LIMITED` partly for this reason. In place of a GCI, M3 reports a measured
two-level coarse-to-medium change on six paired capsule cases, largest 0.411%, and says
explicitly that this shows the size of the effect and does not bound the error.

---

### Q21. What is force convergence, and why is it your criterion of record instead of residuals?

**A.** The criterion, declared before the runs: over the final 2000 iterations, forebody C_D
must have peak-to-peak variation ≤ 0.1% of its mean **and** drift between the two halves of
that window ≤ 0.02%. The reported C_D is the mean over that window.

Residuals are not the criterion because with a TVD limiter the density residual of this
solver stalls about one decade down and never reaches machine zero: the captured shock keeps
flickering between neighbouring cells, which keeps the residual alive while the integrated
force has long since stopped moving. The report shows the residual plot anyway, uncropped,
and says a reader wanting machine-zero residuals will not find them here.

**Evidence.** `reports/milestones/M2_cfd_validation.md` §"Condition 2";
`docs/negative_results.md` NR-07 (max Courant 0.5 left a 0.157% limit cycle; 0.2 gave
0.029%, and the mean C_D moved by under 0.1% between them, so the oscillation was noise
about the right answer).

**Push.** *"A case missed your criterion. What did you do?"* Did not move the criterion.
NR-09: `sphere_M3_coarse` finished its planned 10 000 iterations with drift 0.0219% against
a limit of 0.02%. The limit was declared before the run, and a criterion relaxed the first
time it bites is not a criterion. The pipeline was changed instead to run until converged,
extending in blocks up to three times, and the number of extensions each case needed is
printed so the cost of convergence is visible. Later, NR-21: five M3 design points still
missed after up to 55 000 iterations. They are REJECTED, they are listed in the report, and
they are not in the surface. A separate, labelled INCLUSIVE surface containing them exists
only to measure what the strict rule costs, and on the designs compared it costs very
little.

---

### Q22. What is Mach-number independence, and what does the perfect-gas assumption get wrong?

**A.** Above roughly Mach 8–10, blunt-body pressure coefficients stop depending on Mach
number and depend only on shape and γ. Physically, the surface pressure is set by the normal
momentum flux ρ∞V∞², and once the shock is strong the pressure *coefficient* stops changing.
That is what licenses running a Mach-20 case and holding its value above Mach 20, which
matters because 55% of the baseline capsule's heat load accrues above Mach 20.

It is an approximation, not an identity, and this project measured the size of it rather than
asserting it: the largest change in C_D,fore between Mach 10 and Mach 20 among the named
shapes inside the hull is **1.80%**. So holding the value is an approximation of about that
size.

What the perfect gas gets wrong is everything about the shock layer. Behind a real entry bow
shock at 7 km/s, air does not behave as a γ = 1.4 gas: energy goes into vibration and
dissociation, the density ratio across the shock rises well above the perfect-gas limit of 6,
and the shock layer thins accordingly. So a perfect-gas stand-off distance is wrong for
flight in a known direction (too large), and perfect-gas shock-layer temperatures are far too
high. What survives is the pressure field, because the stagnation pressure coefficient moves
only from about 1.84 at γ = 1.4 to 2.0 in the Newtonian limit. That is an argument from
theory, **not validated here**, and it is carried as a declared ±5% model-form half-band on
C_D,fore for M7 to sample.

**Evidence.** `reports/milestones/M3_coupled_model.md` §7 (the Mach-band heat-load table and
the 1.80% measurement); `ASSUMPTIONS.md` A-CFD-12;
`docs/validation/M2_model_form_limits.md`.

**Push.** *"You cite Anderson for Mach-number independence. Did you read it?"* No, and the
repository says so: the chapter and section titles were verified against the Library of
Congress table of contents, and the book's text itself was not opened. The principle is
cited, not quoted, and the project's own measurement of 1.80% is what the claim actually
rests on.

---

## 6. Optimisation

### Q23. Why is `evaluate_design` the only permitted evaluation path?

**A.** Because a study that builds its own evaluation shortcut is a study whose numbers
cannot be compared with anyone else's. Every objective, constraint, diagnostic, provenance
field and uncertainty hook lives inside one function, so a change to the physics reaches
every study at once and a per-study variation is impossible by construction. It is also what
makes the soak-out phase (NR-02) impossible to forget.

It is enforced even where it was inconvenient. M7's uncertainty propagation would naturally
loop over draws *outside* the optimiser, which would bypass the budget meter. Instead the
draw index is appended to the design space as one synthetic variable, so `(design, draw)` is
an ordinary design vector; nothing in the budget, persistence or evaluator code had to
change, each pair gets a candidate ID and is charged and logged, and common random numbers
become visible cache hits rather than an untracked saving.

**Evidence.** `src/aether/evaluate.py`; `ASSUMPTIONS.md` A-UQ-* preamble and
`docs/engineering_notebook/2026-09-20_M7_uncertainty_robust.md` §Action ("Uncertainty is a
coordinate of the design space").

**Push.** *"How do you know two runs of it agree?"* Gate G5 fingerprints every metric,
margin, diagnostic, provenance block and the whole velocity history, bit for bit. Three runs
on the same config gave `c05015c9da0f11b3` three times.

---

### Q24. What is a Pareto front? Why must a two-objective front be monotone, and how did that fact catch a bug?

**A.** A design dominates another if it is at least as good on every objective and strictly
better on at least one. The Pareto front is the set of non-dominated designs: those you
cannot improve on one objective without losing on another. With two objectives both
minimised, the front must be monotone decreasing, because if two front points had one
better on both axes the other would be dominated and would not be on the front.

That geometric fact caught a real bug. The first `pareto_front` returned all 21 feasible
designs as non-dominated and the plotted front zigzagged. A zigzag is geometrically
impossible, so the **figure falsified the code**. The dominance test had inverted control
flow: on finding a point that dominated candidate *i*, it `continue`d, keeping *i*, instead
of marking it dominated. The test suite had not caught it because no test asserted
monotonicity. It was rewritten as a direct dominance check plus a monotonicity assertion.

**Evidence.** `docs/negative_results.md` NR-04; `tests/test_pareto.py`.

**Push.** *"What does that tell you about your plotting standards?"* That a chart with real
axes and real units is a test, and a prettier, less quantitative chart would have hidden it.
That is the reason for the plotting rules in spec §34, and it is the clearest example in
this project of a figure functioning as a test.

---

### Q25. What is hypervolume, and why did you fix its reference point before running anything?

**A.** Hypervolume is the area (in two objectives) of the region dominated by a front and
bounded by a chosen reference point, usually the worst acceptable value on each axis. It is
one number that rewards a front for being close to the ideal corner **and** for being spread
out, which is why it is the standard scalar summary of multi-objective performance.

Its weakness is that it depends entirely on where the reference point is put. A reference
point that moves with the data makes hypervolumes from different runs incomparable, and it
lets a method look better by finding one very bad design that stretches the rectangle. So
this project fixed both corners in config before any optimiser ran: reference point
(2.5×10⁶ W/m², 450 K), ideal point (0 W/m², 300 K), with hypervolume reported normalised to
that rectangle. 450 K is the bondline allowable, 300 K the TPS initial temperature, and
2.5 MW/m² sits above every feasible design of the DOE's Latin Hypercube (the largest was
2.05 MW/m²). The report counts feasible designs falling outside the rectangle, which was 0.

**Evidence.** `ASSUMPTIONS.md` A-OPT-4; `configs/design_space.yaml`;
`reports/milestones/M4_pareto_optimisation.md` §7; `tests/test_pareto.py` (hypervolume
against hand-worked cases to 1e-12).

**Push.** *"You said you fixed it before any optimiser ran. Is that the whole truth?"* No,
and the notebook discloses it: the reference flux was written into the config before any
optimiser ran but *after* the evaluator had been timed on four hand-picked designs, so the
order of magnitude of the flux was already known. It was checked afterwards against the DOE
and not changed. A second disclosure of the same kind: M2's benchmark tolerances were
written into the config after a coarse prototype had already produced numbers on screen, so
"pre-declared" there means before the validation runs, not before any CFD number had ever
been seen.

---

### Q26. The M1 sweep reports Spearman ρ = −1.000. Why is that number close to worthless as independent evidence, and what *is* the defensible claim?

**A.** Only one parameter was varied. Both metrics turn out to be strictly monotone in that
parameter, and two strictly monotone functions of a single variable can only ever give
ρ = +1 or −1, whatever the physics. The correlation restates "both are monotone in γ, with
opposite signs"; it does not measure the strength of a relationship across a design space,
because the domain is a line segment rather than a space.

The defensible claim is the **monotonicity itself**: over the full range of entry angle
tested, every step that lowers peak heat flux raises bondline temperature, and there is no
interior angle at which both improve. That is enough for H0, and it is a statement about a
one-parameter family. A claim about the design space needs M1b's grid and, properly, the
DOE.

**Evidence.** `reports/milestones/M1_burn_vs_bake.md` §"How much this rank correlation is
actually worth"; `PROJECT_STATUS.md` §"Headline results so far"; commit `202fa00`
("docs: stop overclaiming the rank correlation and the margin ratio").

**Push.** *"Did the same trap appear anywhere else?"* Yes, and it was checked for. In the
TPI study, along each fixed-diameter line of the grid, 10 of 10 lines give |ρ| ≥ 0.999
between TPI and peak bondline temperature. Those line correlations are reported purely to
show why only the 2-D number counts, and every correlation the verdict rests on is over the
full 2-D grid.

---

### Q27. Both M1b optima sit on the diameter bound. Why is that a problem, and what would you do about it?

**A.** Because a design stopped by a box bound is an optimum **of the box**, not of the
physics. The right way to read it is "at least this far in this direction", not "a located
minimum". Both M1b optima ran to the 3.0 m upper bound, so the bound was selecting them.

Two things have happened since. The bound was replaced by something physical, a heat-shield
mass-closure constraint at 1.0 (shield must not outweigh the vehicle), which is a logical
necessity rather than a judgment. But that only excludes the impossible: the M4 front then
sat *on* the mass-closure constraint at a shield about 99% of vehicle mass, which no real
vehicle could be. So the open item is not closed. What would close it is a sourced mass
budget, or a mass model in which vehicle mass grows with size.

**Evidence.** `ASSUMPTIONS.md` A-LIM-3 and A-OPT-6; `docs/negative_results.md` NR-13;
`reports/milestones/M4_pareto_optimisation.md` §10 (the "what stops each selected design"
list) and §11 (the counterfactual table).

**Push.** *"How do you know which constraints are doing the work?"* The metric-gaming audit
computes, from the same candidate log, the front each constraint would have produced if it
were ignored, and how many of those designs violate it. Removing mass closure leaves a front
of 4 designs, all 4 violating it, worst margin −0.776. That is measured from stored data,
not argued.

---

### Q28. Why is "six times the thermal margin" a bad way to report the M1b comparison?

**A.** Because a margin *ratio* is measured against the bondline allowable, and the ratio is
violently sensitive to it: at a 445 K allowable the ratio is 37.5×, at 450 K it is 6.5×, at
460 K it is 3.0×, at 500 K it is 1.6×. When that was written the allowable was an unsourced
placeholder, so the ratio was an artefact of a number nobody had justified.

The robust quantity is the **absolute** difference, 32.5 K, which does not depend on the
allowable at all. That is what gets reported. The allowable has since been sourced (450 K is
the Shuttle's aluminium-structure limit), which makes the ratio meaningful in principle, but
it is a *substrate* limit rather than a universal constant, and against Apollo's stainless
interface (589 K) or Orion's composite-over-titanium (533 K) it would be 83–140 K higher.
The absolute difference stays the right thing to quote.

**Evidence.** `reports/milestones/M1_burn_vs_bake.md` §"Do not quote the margin as a ratio"
(with the four-row sensitivity table); `ASSUMPTIONS.md` A-LIM-1a; commit `202fa00`.

**Push.** *"Then is your feasible region real?"* Partly. The 450 K side is now sourced. The
12 g side is not, and that is the open student decision: see Q40.

---

### Q29. What are Sobol' indices, and what is the difference between first-order and total-order?

**A.** They are a variance decomposition. Take the output variance and ask how much of it
would disappear if you learned the true value of one input. The **first-order** index S₁ is
the share of variance explained by that input alone, averaged over everything else. The
**total-order** index S_T is the share that would remain if you fixed *everything except*
that input, so it includes every interaction the input takes part in. Always S_T ≥ S₁, and a
large gap between them means the variable matters mainly through interactions.

This project's screening rule uses **total order**, declared before the run: freeze a design
variable only if its total-order upper confidence bound is below 0.01 for every screened
output **and** its validity-index upper bound is below 0.03. Total order, because a variable
can matter only through interactions; validity as well, because a variable that moves no
objective can still decide which designs exist. That second half turned out to matter: cone
half-angle moves no objective at Fidelity 0 (index exactly 0.0000) but was kept active
because it decides which bluntness ratios are geometrically valid. Freezing it at the
baseline 25° would silently have capped bluntness near 0.54.

**Evidence.** `ASSUMPTIONS.md` A-OPT-7, A-OPT-8;
`reports/milestones/M4_pareto_optimisation.md` §§5–6;
`tests/test_optimization.py::test_sobol_indices_recover_the_ishigami_analytical_values`.

**Push.** *"Your first-order confidence intervals were once [−0.41, 1.15]. A variance share
cannot be negative or above one. What happened?"* The Saltelli-2010 first-order estimator
multiplies by f(B). For an output with a ~400 K mean and only a few tens of K of spread, the
estimator's variance is dominated by the mean rather than by the signal. Sobol' indices are
invariant to a constant shift, so the output is now mean-centred before estimation. Same
6144 evaluations, re-analysed: the interval on the leading variable became [0.30, 0.45].
Total-order indices are differences and were unaffected, so **no screening decision
changed** (NR-16). The estimator is now pinned against the Ishigami function's analytical
indices, which is a test case with a known answer.

---

### Q30. What does your DOE actually say drives each objective?

**A.** At Fidelity 0, on the all-valid sub-box:

- **Peak heat flux**: diameter dominates (S_T = 0.886), then bluntness (0.081), then entry
  angle (0.054).
- **Peak bondline temperature**: diameter (0.419), insulator thickness (0.379), entry angle
  (0.242).
- **Max g**: entry angle almost entirely (0.972).
- **Heat-shield mass fraction**: diameter (0.945), then vehicle mass (0.082).

The honest reading is that at Fidelity 0 the problem is nearly one-dimensional: diameter and
bluntness are free improvements that run until a constraint stops them, and only entry angle
genuinely trades the two objectives against each other. Four shape variables produce a range
of **exactly zero** in both objectives, which is not a small effect but a structural
statement: at constant C_D the drag model cannot see shape at all. A shape variable frozen
here is frozen because the model is blind to it, not because shape is unimportant.

**Evidence.** `reports/milestones/M4_pareto_optimisation.md` §§3–6;
`docs/engineering_notebook/2026-09-20_M4_doe_pareto_fidelity0.md` §Observed.

**Push.** *"Then your screening is worthless once you add CFD."* Correct, and it is stated
in the report and enforced in code. The M4 screening is already **void**, for a second
reason: the effective-nose-radius correction made `shoulder_ratio` non-inert (worth 1.45% of
peak flux across its box) after it had been frozen on a total-order index of exactly zero.
M7's runner refuses to start on a stale screening and prints why.

*Filled 2026-09-21 from `reports/milestones/M4_pareto_optimisation.md` §5–§6, §11 (vi) and
NR-29.* The screening was re-derived from scratch at Fidelity 1 (run
`M4-DOE-20260920T204844Z`). Total-order indices inside the Saltelli sub-box: peak flux is
diameter 0.896, bluntness 0.063, entry angle 0.054; bondline is diameter 0.429, insulator
thickness 0.377, entry angle 0.239; max g is entry angle 0.979. Active variables: diameter,
bluntness, cone half-angle (it moves no objective but decides validity) and entry angle.
**The rule froze the shoulder ratio again**, on an upper bound of 0.0048 against a threshold
of 0.01, and that is the part to be ready for. Probes on the three selected front designs
show the frozen lever is worth 16.6–19.9 kW/m², about 7% of peak flux, and 3.1–3.9 K at the
front. A Sobol' index is a share of variance over the sub-box, where diameter carries about
0.90 of the flux variance, so a 7% lever rounds to zero. The rule answers "which variables
explain the spread of the box", not "which would an optimiser exploit at the optimum". And
the lever is one the stagnation-point-only heating model rewards for the wrong reason. The
freeze was left in place and labelled a fence that happens to stand in the right place;
re-running the screening with a rule chosen after seeing this would have been tuning.

---

## 7. Surrogates

### Q31. What is a Gaussian process surrogate, and why use one here?

**A.** A GP is a model that, instead of fitting one curve, puts a probability distribution
over functions. Given training points it returns, at any new input, both a predicted mean
and a predicted standard deviation, and the standard deviation grows as you move away from
the data. That is exactly what is needed when each training point costs an OpenFOAM run:
you need the prediction *and* an honest statement of how much to trust it, so the optimiser
can decide whether to spend a CFD call.

Here it models C_D,fore over log(Mach) and three forebody shape ratios, with a Matérn-5/2
kernel, one length scale per input, and a white-noise term, fitted on 56 usable CFD cases.
Measured on a held-out test set drawn *before any case ran*: RMSE 0.0270 in C_D units,
R² 0.9942, over a C_D,fore range of 0.352–1.551.

**Evidence.** `reports/milestones/M3_coupled_model.md` §6;
`src/aether/surrogate/gp.py`; `tests/test_surrogate.py`.

**Push.** *"Is a held-out R² of 0.994 on seven points impressive?"* Not on its own, and the
report says the coverage figures are themselves uncertain by roughly ±1/√n. Seven points is
seven points.

---

### Q32. Your GP's error bars had to be inflated. Explain.

**A.** Accuracy and calibration are different properties. A model can predict the mean well
and still be **overconfident**, meaning its stated intervals are too narrow, so the truth
falls outside them more often than the nominal rate. The diagnostic is the z-score spread:
for each held-out point, (truth − prediction)/σ_predicted. If the GP is calibrated that
spread has standard deviation 1. Here it was 1.65 over all usable points in k-fold, and
predicted 68% intervals covered only 59% of held-out truths.

The immediate cause was identified: after three late anchors were added to enclose the M4
front (NR-22), six near-duplicate points sat in one corner, and near-duplicates make a GP
more confident than it should be, because the kernel reads repeated agreement as evidence of
low noise. The k-fold z-score spread rose from about 1.1 to about 1.65 when they went in.

The response was a **sigma inflation factor**, measured rather than assumed, stored with the
surface and applied to the GP term before M7 samples it: **1.65 on `cfd_surface_v1`**; the
surface was rebuilt as `cfd_surface_v2` on 2026-09-20 (extended to Mach 27 under gate G4
PASS) with a recomputed factor of **1.21**, which is what M7's propagation and robust runs
actually sampled. The report calls it what it is: a one-number recalibration, not a cure.
The held-out points show a **bias** as well as a spread, and a single multiplier cannot fix
a bias.

**Evidence.** `reports/milestones/M3_coupled_model.md` §6 (the coverage table and
§"Calibration"); `docs/negative_results.md` NR-22;
`docs/engineering_notebook/2026-09-20_M3_cfd_drag_surface.md` §Observed.

**Push.** *"You tried a better input parametrisation and did not adopt it. Why?"* Replacing
the cone-angle input with sin²θ, the Newtonian variable, moved k-fold RMSE from 0.0326 to
0.0313. That is a real improvement, and it was **not adopted**, because by then the held-out
test set had been seen. Changing a declared model input after looking at the test set turns
a held-out set into a training set. The measurement is recorded and the change is not made.

---

### Q33. What happens when the optimiser asks your surrogate about a shape it has never seen?

**A.** It refuses. `GPSurrogate.predict` raises outside the convex hull of its training
inputs unless the caller explicitly passes `on_extrapolation="flag"`, and `evaluate_design`
returns such a design as a **rejected candidate** with `status: aero surface extrapolation`
and NaN metrics, which stays in the candidate log. A GP outside its hull does not fail
loudly on its own: it reverts smoothly to its prior mean with a wide interval, which looks
like a prediction and is not one.

The cost is real and is stated: failed CFD cases shrink the design space the optimiser can
use. NR-21's rejected hulls removed the slender small-shoulder corner at Mach 20 and the
validity-boundary point at R_n/D = 0.8.

**Evidence.** `ASSUMPTIONS.md` A-AERO-1, A-AI-4; `reports/milestones/M3_coupled_model.md`
§6 §"Extrapolation guard"; `docs/negative_results.md` NR-21.

**Push.** *"Did that guard ever misfire?"* Yes, and finding out why is one of the better
results in the repository. In an M6 dry run, an arm that had bought **one** new CFD point
suddenly had 6 of its next 20 designs rejected as extrapolations, while the arm that bought
nothing had none in 100 evaluations. A convex hull cannot shrink when a point is added. The
cause: `shoulder_ratio` frozen at 0.10 is written as a length and divided back to
0.10000000000000002, a unit coordinate of 1 + 2.2×10⁻¹⁶, sitting exactly **on** a hull
facet. `Delaunay.find_simplex` at Qhull's default tolerance then decided membership by
triangulation luck: 48/48 query points inside the 56-point hull, 1/48 inside the 57-point
hull, 48/48 inside both at a tolerance of 1e-12 or larger. Fixed with an explicit
`HULL_TOLERANCE = 1e-9` in unit-cube edge lengths, which is physically nothing and makes
boundary membership independent of the triangulation. The consequence had it gone unnoticed
is the point: in M6 this would have **punished promotion**, biasing an adaptive-fidelity
study against every arm that buys CFD, in a study whose whole question is whether buying CFD
pays (NR-23).

---

## 8. Uncertainty and robustness

### Q34. What is the difference between aleatory and epistemic uncertainty, and why does this project carry them separately?

**A.** Aleatory uncertainty is genuine variability: the atmosphere on the day, the as-built
mass, the delivered flight-path angle. It does not go away with more study, and you absorb
it with margin. Epistemic uncertainty is ignorance about something that does not vary at
all: which of two NASA reports is right about R_eff, what the placeholder TPS material
actually is. It *does* go away, with evidence, and buying margin to cover it is the
expensive way to handle it.

They demand different responses, so pooling them destroys exactly the information that says
which to buy. The sampling shape enforces the distinction rather than a post-hoc split:
nested sampling of E epistemic branches × A aleatory draws sharing common random numbers,
so each branch yields a complete output distribution and the primary result is a **p-box**
rather than one curve. Reading the figure: the width of one curve is variability, the gap
between curves is ignorance.

The pooled mean and standard deviation are still printed, combined by the law of total
variance, i.e. **in quadrature**, and the code says so in those words together with the
caveat that the identity is only *meaningful* if an epistemic band is read as a probability
distribution, which it is not.

**Evidence.** `ASSUMPTIONS.md` A-UQ-1; `docs/theory/uncertainty.md`;
`tests/test_uncertainty.py` (nested draws proven to share common random numbers across
epistemic branches and to hold the epistemic block fixed within one).

**Push.** *"Which dominates, in your problem?"* *Filled 2026-09-21 from
`reports/milestones/M7_uncertainty_robust.md` §3.1, §4 and `M7_addendum_posthoc.md` §5 (run
`M7-UQ-20260920T233048Z`).* Epistemic, for both thermal objectives: 84.4–93.9% of peak-flux
variance and 97.2–98.7% of bondline variance across the four designs. Max g is the opposite
(12–38% epistemic; it is driven by delivered entry angle and density). At the knee
(K = 0.417), peak flux is dominated by the choice between the two NASA nose-radius sources,
S_T 0.706 [0.599, 0.819], then the Sutton–Graves constant 0.181; on the hemispherical
baseline that same term is exactly 0.000, because the two sources agree identically at
K = 1, and the constant leads at 0.609. The bondline is dominated by TPS conductivity (0.638
at the knee, 0.883 at the baseline) and by the multiplier on heating above 86 km (0.262 at
the knee), **both engineering judgment**. So the second objective is governed by the two
numbers the project has least evidence for. The GP surrogate (≤ 0.020) and the mesh term
(≤ 0.003) are negligible everywhere. There are 12 active inputs, 7 of them judgment (T3),
4 primary (T1), 1 secondary. An index on an epistemic input is a sensitivity to which model
is believed, not a share of real variability. And every spread is a lower bound, because gate
G2′ (catalycity above all) has no distribution attached.

What follows is the text written before the study ran, kept for the record. The declared
hypothesis, written before building, is that epistemic terms dominate,
because the aleatory inputs are a few percent while the epistemic ones are a ±15% band on a
placeholder conductivity and a ~20% disagreement about R_eff. The smoke runs put the
epistemic share of the bondline variance at 98–99%, but on 12 draws with a stale
active-variable list, so that is an indication of where the answer may land and not the
answer. If it holds, M7's headline output is a **shopping list of measurements to buy**
rather than a margin. Of nine active inputs, 7 are engineering judgment (T3) and 2 are T1,
and the two T1 inputs are the ones this project measured about itself.

---

### Q35. What is a chance constraint, and what is the trap in yours?

**A.** A deterministic constraint asks "is this design feasible?". A chance constraint asks
"is this design feasible with at least probability 1 − α?", here P(violation) ≤ 0.05 per
constraint. It is the right question once the inputs are uncertain, because a design sitting
at +0.9% margin on a hard limit is not really feasible.

The trap is **resolution**. With S inner draws the estimated violation probability can only
take values that are multiples of 1/S. So α = 0.05 with S = 32 really means "at most 1 of
32 draws may violate", and at S = 8, the smoke setting, it means **zero violations**, which
is far harsher than 5% sounds. The first smoke run returned an empty front for exactly that
reason and it initially looked like a bug. `RobustSettings.effective_chance_rule` now
computes and prints that translation, and it is tested.

Two further declared rules: a draw that produced no physics at all counts as a violation of
**every** chance constraint and is reported separately, because a vehicle that does not
complete an entry has satisfied nothing. And the robust objective is the 95th percentile of
each O1 objective, an empirical order statistic: a design is judged on a bad day, not an
average one.

**Evidence.** `ASSUMPTIONS.md` A-UQ-ROB-1; `docs/theory/uncertainty.md` §on the chance
rule; `configs/uncertainty.yaml`; `tests/test_robust.py`.

**Push.** *"Do the M4 front designs survive a chance constraint?"* *Filled 2026-09-21 from
the M7 report §3.2, §5–§6, the addendum §2–§3 and NR-33.* No. P(any constraint violated) is
34.40% [32.72, 36.12] for the peak-flux-only optimum, 29.60% [27.99, 31.26] for the knee and
46.60% [44.82, 48.39] for the bondline-only optimum, against the declared 5%. **None of it is
thermal:** the bondline limit is violated in 0 of 3000 draws for each, which is below 0.13%
at 95% confidence and is not zero. What is crossed is the heat-shield mass-fraction fence,
pushed over by a ±2% mass dispersion on a 350 kg placeholder, plus the 12 g limit for the
bondline-only design (36.00%). The designs sat 0.84%, 1.09% and 0.19% from their binding
constraint at nominal. So the fragility is about two placeholders and a fence, not evidence
that anything overheats. The robust knee, propagated on the same 3000 draws, reads 3.20%
[2.63, 3.89], all of it mass fraction, for +7.8 kW/m² (+3.1%) of nominal peak flux and a
bondline lower by 0.42 K. Be ready for the follow-up: all 46 robust-front designs sit at
exactly 1/32 on the mass-fraction chance constraint, the optimiser having used its allowance
to the last of 32 fixed draws, and on 1000 fresh draws one of 8 checked designs reads 5.7%
against the 5% limit.

Written before the study ran, kept for the record: the declared hypothesis is that they do
not, because an optimiser with no reason to leave
margin parks on its binding constraint and A-LIM-1b records the baseline at +0.9% on the g
limit. It is untestable until the front is regenerated, because the designs in question came
from a superseded run.

---

### Q36. Zero of your draws violated the constraint. Is the violation probability zero?

**A.** No, and this is the single most common way to over-claim from a Monte Carlo. Observing
0 events in n trials does not mean the rate is 0; it means the rate is small, and how small
depends on n. The exact Clopper–Pearson upper limit at k = 0 is 1 − α^(1/n), which for 95%
confidence is approximately the **rule of three**: the rate is below roughly 3/n.

So the correct sentence is the one the report generates: *"0 of 500 draws violated it, i.e.
below 0.57% at 95% confidence, not zero."* Wilson score intervals are the default rather
than the textbook-first Wald interval, precisely because Wald gives a zero-width interval at
k = 0, which is the failure mode this is there to prevent.

**Evidence.** `docs/theory/uncertainty.md` §on interval estimators (Wilson, Clopper–Pearson
at k = 0, the rule of three, and the verbatim reporting sentence);
`tests/test_uncertainty.py` (Wilson against its own algebra; Clopper–Pearson at k = 0
against the closed form 1 − α^(1/n)).

**Push.** *"How many draws would you need to claim 10⁻³?"* By the rule of three, about 3000
for the *upper bound* to reach 10⁻³ with no observed events, and far more to estimate a rate
of that size rather than bound it. That is the honest reason a Monte Carlo of a few thousand
draws cannot support a reliability claim, only a bound.

---

### Q37. Your robust optimisation uses 32 inner draws. Full Monte Carlo would take hours. How do you know the shortcut is safe?

**A.** By measuring it, not by asserting it. The shortcut is S = 32 inner draws under
**common random numbers**: the same draws for every candidate in every generation. CRN makes
the estimator of the *difference* between two designs far better than the estimator of either
value, and an optimiser only ever needs the comparison. Without it the search would chase
sampling noise.

Both halves of that trade are stated: a 95th percentile from 32 draws is noisy and biased
inward, and CRN buys precision on the comparison at the price of correlated error on the
level. So `verify_shortcut` re-scores a subset of the finished front under **full
independent Monte Carlo**, 1000 draws, a different seed and no CRN, and reports the measured
bias, the rank correlation and the violation-probability error against tolerances declared
before the run. If any is missed, the report says the front is the output of an unverified
shortcut.

The verification has tests proving it **fails** on an injected bias, a reversed ranking and
a wrong violation probability. A verification that cannot fail is a rubber stamp.

**Evidence.** `ASSUMPTIONS.md` A-UQ-ROB-2; `src/aether/uncertainty/`;
`tests/test_robust.py` (the three injected-failure tests).

**Push.** *"What did the verification say?"* *Filled 2026-09-21 from the M7 report §5.2 and
the addendum §3 (run `M7-ROBUST-20260920T211216Z`).* PASSED, applied exactly as declared.
Eight designs along the robust front were re-scored with 1000 fresh independent draws:
relative bias −1.61% on p95 peak flux and +0.32% on p95 bondline (tolerance 5%); Spearman
1.000 on both (tolerance ≥ 0.80); largest violation-probability error 2.60% (tolerance 5%).
The bias has a consistent sign: the 32-draw p95 under-reads peak flux on all 8. One
feasibility verdict flipped: design `C-22b67c409bf2` at the low-bondline end reads
P(any) = 5.7% on fresh draws, 2.6% of it from max g, which the 32 inner draws had seen as
zero. A flipped verdict is not one of the three declared tolerances, so the check passes and
the flip is reported beside it, not absorbed into it. The criterion was not re-tuned either
way. Also true and slightly embarrassing: common random numbers produced 0 cache hits in
90,000 inner evaluations, so the free re-evaluations the harness anticipated never happened.

Written before the study ran, kept for the record: smoke runs at S = 8
passed on three designs with biases of −1.51% and −0.69% and Spearman 1.000 on both
objectives, which means the plumbing works and nothing more. The instruction written into
the notebook is to **read the shortcut verification first** when the study runs, before
reading the front.

---

### Q38. Why does your uncertainty run *refuse to start* in some configurations?

**A.** Because dropping a term you cannot quantify understates the uncertainty, and nothing
in the output would show it. Each uncertain input carries its own policy for what to do when
its evidence does not exist. `cd_discretisation` requires the M2 GCI and declares `refuse`,
so selecting the CFD drag surface stops the run and names the input, the requirement and
`gci.csv`. The same input's `aero_model` requirement declares `skip`, because at Fidelity 0
there is no surface for the term to be about.

There is a second refusal of the same character: the source-tier loader rejects any input
tiered T3 unless its own source line contains the word "judgment". An unsourced spread is
allowed; an unsourced spread that *reads as though it were sourced* is not.

And a third: the runner refuses to start when the DOE screening is void for the current
design space, which is the state it is in now.

**Evidence.** `ASSUMPTIONS.md` A-UQ-2, A-UQ-3;
`tests/test_uncertainty.py::test_the_run_refuses_when_the_gci_term_is_unavailable`;
`ASSUMPTIONS.md` A-CFD-9 ("sampling it raises rather than returning zero").

**Push.** *"Is your uncertainty estimate complete, then?"* No, and the notebook says so
plainly: every output distribution it produces is a **lower bound** on the real uncertainty,
because gate G2′ (catalycity, hot wall, radiation) has no distribution attached and is not in
the inventory at all, and catalycity alone is worth roughly a factor of two.

---

## 9. Constraints, feasibility and the open decision

### Q39. Why does an unsourced constraint limit get stored as `null` rather than as a large number?

**A.** Because an unknown constraint is an open question, not a satisfied one. A large
placeholder would be silently treated as satisfied by every design and would produce false
feasibility claims that look identical to real ones. `null` is skipped, and the skip is
visible.

**Evidence.** `ASSUMPTIONS.md` A-LIM-2; spec §9.

**Push.** *"Where did that actually bite?"* `max_bluntness_ratio` is now `null` after the
nose-radius correction removed the model failure it was fencing off, and `max_heatshield_mass_fraction`
is `null` in `configs/baseline.yaml` so no M1, M1b or TPI number changed when it was added
to the design-space config.

---

### Q40. Your deceleration limit is 12 g. Defend it.

**A.** I cannot defend it as a nominal design limit, and the repository says so. No document
states a flat 12 g. NASA-STD-3001 Vol 2 Rev F Table 6.5-1 gives a duration-dependent
sustained +Ax curve, and for a **deconditioned** crew, which is the entry-relevant case
after time in microgravity, it reads 14.0 g at 0.5 s, 10.0 g at 10 s, 8.0 g at 30 s, 6.3 g
at 50 s, 5.0 g at 90 s, 4.3 g at 120 s and 4.0 g beyond 150 s. Twelve g exceeds that curve
beyond about 1–2 seconds. It sits inside the *emergency-conditions* envelope instead, and it
matches NASA TM-104753's deconditioned 5-second plateau (12 G / 5 s) almost exactly. It also
exceeds every published nominal crewed entry: Mercury 7.6–11.1 g, Gemini 4.3–7.7 g, Apollo
3.3–6.8 g, Soyuz nominal 3–4 g.

What it would cost to fix, measured on the stored M1b grid of 140 designs rather than
estimated:

| g limit | deconditioned duration | passes g | passes g **and** bondline ≤ 450 K |
|---|---|---|---|
| 12.0 (current) | not on the curve | 48 (34.3%) | 21 (15.0%) |
| 10.0 | 10 s | 18 (12.9%) | 4 (2.9%) |
| 8.0 | 30 s | **0** | **0** |

And the pulse it would be keyed against: the baseline peaks at 11.89 g with 25.5 s above
10 g, 40.0 s above 8 g and 52.6 s above 6.3 g. Read onto the deconditioned curve, the
baseline exceeds it at every level, not marginally.

So there are two honest options, and they are not a tuning choice. **Option A**: keep 12 g
and relabel it as an emergency/off-nominal envelope value, which it defensibly is; every
stored result stays valid, and the honesty cost is that "feasible" then means *survivable in
a contingency*, not *acceptable for a nominal crewed entry*, and the §39 comparison table
must say so. **Option B**: adopt the duration-dependent curve, which empties the M1b design
space entirely and restates the burn-vs-bake result as being about an uncrewed or
contingency-entry vehicle, or reopens the design space. Option B additionally needs a new
metric, because the evaluator stores `max_g` only and the standard's axis is duration of
sustained acceleration.

**This is the student's decision and it has not been made.** Until it is, 12 g stands and
A-LIM-1b says what it is and is not.

**Evidence.** `ASSUMPTIONS.md` A-LIM-1b and §"OPEN STUDENT DECISION — the deceleration
limit"; `docs/validation/sourcing_report.md` §2;
`docs/engineering_notebook/2026-09-20_validation_closeout.md`.

**Push.** *"So is your headline result about a crewed vehicle?"* Not established. The
mechanism (peak versus cumulative) does not depend on the g limit at all. The *feasible
region*, and therefore which designs the optimisers select, depends on it completely.

---

## 10. Experiment

### Q41. What is the difference between calibration and validation, and how does your coupon experiment keep them apart?

**A.** Calibration fits model parameters to data. Validation tests the model against data it
has never seen. If you calibrate and validate on the same data you have measured how well
you can fit, which is not a measure of the model.

The coupon protocol is built as a chain that makes the separation structural: (1) run
calibration experiments; (2) **freeze** the model parameters; (3) generate a prediction for
an unseen heating history; (4) archive and timestamp that prediction **before** any
measurement of the unseen case is analysed; (5) run the experiment; (6) compare predicted
and measured T(x,t) on RMSE, peak error, time-to-peak error, residuals and uncertainty
coverage. Step 4 is the one that makes it a blind prediction rather than a fit.

The experiment compares high-peak/short-duration against lower-peak/longer-duration heating
on the same coupon. It is a thermal-transient validation experiment, not a re-entry
simulator.

**Evidence.** `experiments/thermal_coupon/protocol.md`;
`experiments/thermal_coupon/blind_validation/` (`make_prediction.py`, README);
spec §47; `VALIDATION_MATRIX.md` row M8 (`IN_PROGRESS`).

**Push.** *"Has any of this been run?"* `[PENDING — STUDENT]` — as of 2026-09-21 **no coupon
has been printed, no heater has been switched on, and no measurement exists.** What has been done is
the whole chain against a **synthetic twin**: data generated by this project's own solver
with known parameters. That is a check on the software and nothing else, and the matrix row
says so.

---

### Q42. What did the synthetic twin find, before you spent any money?

**A.** Four traps, each of which would have been invisible in the real experiment because
the calibration would have fitted beautifully and the parameters would still have been
wrong.

1. **Contact resistance is weakly identifiable under a prescribed flux.** Fitting all five
   parameters freely, heater-to-coupon contact resistance came back +186% to +531% wrong and
   dragged conductivity and specific heat 5–12% low with it. The cause is structural: with
   the flux *prescribed*, contact resistance does not change how much heat enters the solid
   at all. It only raises the temperature of the flux-application plane. A least-squares fit
   given a parameter that barely affects the residual will use it to absorb everything else.
   Fix: measure it in a dedicated steady-state run and fix it during the calibration.
2. **A short calibration step leaves k and c_p degenerate.** With a step of about one
   diffusion time, both came back ~12% low while their *ratio*, the diffusivity, was
   recovered to 0.4%. A transient shorter than the diffusion time only ever sees α;
   separating k from ρc_p needs the steady depth gradient dT/dx = q″/k, which needs the step
   held long enough to establish it. Fix: at least 2–3 diffusion times, about an hour for a
   10 mm coupon, which is the single biggest time cost in the protocol.
3. **Peak metrics are estimator-dependent, and the obvious fix does not work.** The maximum
   of a noisy record is biased high by roughly σ√(2 ln N), over a kelvin at 0.4 K sensor
   noise, in the direction that makes a *correct* model look like it under-predicts. The
   obvious remedy, averaging the near-peak plateau, barely helped (+1.36 K residual bias),
   because the plateau window is *selected by the noisy maximum* and the selection bias
   survives the average. Smoothing the record first, identically for prediction and
   measurement so any rounding cancels in the difference, cut it to +0.08 K.
4. **The "seeded" synthetic data was not reproducible between processes.** The per-run seed
   used `abs(hash(name))`, and Python salts string hashes per interpreter. So the twin
   generated different data in every process while looking deterministic within one. It
   surfaced only because trap 3's marginal assertion passed on one salt and failed on the
   next: a test that should have been catching a bug was itself the bug.

With the first two fixes in, the twin recovers conductivity, specific heat and both loss
coefficients to better than 0.5%, fitting at a coarser mesh than generated the data, and
predicts an unseen triangular pulse to better than 0.1 K against the noise-free truth.

**Evidence.** `docs/negative_results.md` NR-11;
`experiments/thermal_coupon/protocol.md` §§7–9;
`tests/test_thermal_coupon.py::test_contact_resistance_is_weakly_identified_and_the_fit_says_so`.

**Push.** *"Why does the test assert the weak identifiability rather than the fix?"* So the
finding cannot be silently forgotten. The test checks that the fit's own reported
uncertainty flags the parameter, which is a property of the method; a test of the fix would
pass even if someone later removed the protocol step that makes the fix work.

---

## 11. What AI did and did not contribute

### Q43. What did AI contribute to this project, and what did it not?

**A.** Most of the code was written by Claude via Claude Code, and `AI_USAGE.md` records
this row by row in four categories: AI-generated/student-reviewed, AI-proposed/student-
approved, student-authored, and external. Rows still marked **review pending** are exactly
that, and they change only when the code has actually been read and understood, not when a
milestone is declared done.

What AI did **not** contribute: the research question, the choice of hypotheses, the frozen
scope, and the decision that the bondline rather than the surface is the interesting failure
mode. Those came from the project specification, which the student received and accepted.
That is stated plainly in `docs/research_story.md`'s first entry, which says the framing
"came from the specification, not from an observation made here", because stating it plainly
matters for the authorship question.

AI also introduced several of the project's recorded defects: the divergent radiation
boundary condition (NR-01), the truncated thermal solve (NR-02), the inverted Pareto
dominance test (NR-04), the uncentred Sobol' estimator (NR-16), and the NaN-returning GP
classifier (NR-17). Those are kept rather than quietly fixed, because the debugging is part
of the research record and because they are the honest measure of what unreviewed generated
code is worth.

**Evidence.** `AI_USAGE.md` (categories, table and standing rules);
`docs/ai_usage_proposed_update.md` (the components added most recently, all unreviewed);
`docs/research_story.md` entry 2026-08-29.

**Push.** *"Can you explain the code you did not write?"* That is the actual gate, and it is
`docs/final_quality_gate.md` item 12. The reading order and honest time estimate are in
`docs/ai_usage_proposed_update.md` §"Reading order".

---

### Q44. In the M5 ablation, the LLM agent is one of the optimisers. What exactly does it see, and why does that matter?

**A.** Structured JSON only: variable bounds, frozen parameters, objective and constraint
names, the hypervolume reference, the remaining budget, tables of evaluated designs with
their metrics, margins and failure messages, and a digest of its own earlier rounds. It is
told neither the model's equations nor any M4 finding. The CLI runs in an empty temporary
directory with tools, MCP, hooks, skills and project-file discovery switched off,
specifically so it cannot read `reports/milestones/M4_pareto_optimisation.md`, which states
the answer.

Why it matters: the variable and metric *names* still carry aerospace meaning, so prior
knowledge and training-set contamination cannot be separated from reasoning-from-data. That
is stated as part of what is being measured rather than claimed away. In one development
call the agent back-computed the constraint limits from the reported margins and said it was
using "ballistic-entry scaling from prior knowledge, checked against the rows", which is
recorded as an anecdote from a single call on a model that has since changed, not as a
finding.

There is a second asymmetry, also stated rather than removed: no optimiser is given the free
analytic geometry-validity check, but the LLM still reads the *failure message* for designs
it paid for, which names the variable to move, while the numeric optimisers see only a fixed
constraint violation. That is real, it is part of what "an agent that reads" means, and it is
in the report.

**Evidence.** `ASSUMPTIONS.md` A-AI-2, A-AI-5, A-AI-6;
`src/aether/optimization/ai_agent.py`;
`docs/engineering_notebook/2026-09-20_M5_ai_ablation_fidelity0.md`.

**Push.** *"Did the AI beat the conventional optimisers?"* *Filled 2026-09-21 from
`reports/milestones/M5_ai_ablation.md` §3–§4, `M5_qualitative_audit.md` and NR-32 (run
`M5-ABL-20260920T211134Z`, Fidelity 1, 200 evaluations × 5 seeds, model `claude-sonnet-5`).*
Early, yes; at the end, not by an amount I had agreed in advance to count. Against the best
conventional method, which was the Bayesian optimiser at every checkpoint: +0.0283 in
hypervolume at 50 evaluations (Holm p 0.0278) and +0.0085 at 100 (0.0119), both "AI helped";
+0.0036 at 200, "no measured difference". Be precise about that last cell: the test
*rejected* there (every agent seed beat every `bo_parego` seed, p = 1/252), and the verdict
comes from the effect-size leg, because 0.0036 is under the 0.005 threshold declared
beforehand. Three things to say with it. One: the agent stated the direction of every lever
in round 1, before it had data, 35 of 47 rounds say it is using prior knowledge, and its
first-round directions were right on 88 of 95 flux calls, so the early lead measures priors
plus data and cannot be separated from contamination. Two: dropping designs within 0.1% of a
constraint cuts the final lead from 0.0036 to 0.0020, so a little under half of it is
precision in parking on a mass fence and an unsourceable 12 g; a fifth of its budget went on
near-repeats that bought 0.0004. Three: n = 5, one model, one easy problem with monotone
free improvements, which is the most favourable case for a textbook prior. Nothing shows it
found a design that NSGA-II with five times the budget did not. It arrived sooner and parked
closer. The separate claim that AI-guided *adaptive fidelity* would save CFD runs (H2) was
not supported, and its AI-guided arm was never run (`M6_adaptive_fidelity.md`, NR-35).

Written before the study ran, kept for the record. The criterion, declared before any run,
was: "AI helped"
at 50/100/200 evaluations only if mean hypervolume exceeds the best non-LLM method's by
≥ 0.005 **and** a one-sided exact permutation test gives p < 0.05 after Holm correction;
mirror image for "AI hurt"; otherwise "no measured difference". With n = 5 seeds only
near-complete separation of the two samples can reject, and a null result is weak evidence
of equivalence. That is written into the config, not decided afterwards.

---

### Q45. How can anyone reproduce a study that calls a language model?

**A.** They cannot reproduce the model; they can reproduce the **run**. Every prompt and
every raw response is persisted verbatim, and `make ablation-replay` re-runs every evaluation
from them using the recorded run's config snapshot and checks the hypervolumes match. A
strict replay of a live development run gave 0 prompt mismatches and an identical candidate
log and hypervolume.

The distinction is stated rather than blurred: what is reproducible is the recorded run.
`make ablation` issues new calls and will give different numbers. A stranger with no LLM
access can still reproduce the principal result, which is what spec §50 asks for.

Model output is also treated as **untrusted data**: parsed with `json.loads` only, validated
field by field against the §23 schema, and unknown fields, unknown parents, non-finite or
out-of-bounds values are rejected and logged, never clipped or repaired. The rejection count
is itself a reported metric, because a model that is sloppy about bounds loses evaluations,
which is the correct price.

**Evidence.** `ASSUMPTIONS.md` A-AI-9, A-AI-6; `make ablation-replay`;
`REPRODUCIBILITY.md` (replay row); `tests/test_ai_agent.py` (fake CLI; no test makes a live
call).

**Push.** *"What stops a long run from silently mixing two physics models?"* The source-tree
hash guard, which exists because that happened. See Q47.

---

## 12. Negative results and honesty

### Q46. Name the strongest negative result in this project and why it was kept.

**A.** The candidate answers are different in kind, and an examiner will want the reasoning
for the choice rather than a name.

**NR-15 is the strongest as *physics*.** The optimiser was exploiting the heating model: with
`effective_nose_radius_m = nose_radius_m`, `1/√R_n` sends heating to zero as R_n → ∞, so an
infinitely flat nose removed **98.90%** of stagnation heat flux. That is not a small
extrapolation error; it is the wrong answer by construction, and it was holding open a lever
that 54 of 64 front designs were pressed against. Under the corrected velocity-gradient
model the same change is worth 21.31%. Keeping it recorded is what made the eventual fix
legible as a *repair of a demonstrated validation failure*, which is the only ground spec §42
permits new physics on. And the entry's honest coda is that the fix **moved** the exploit
rather than removing it: a sharp shoulder now lowers stagnation heating, and shoulder heating
is precisely what this stagnation-point-only model cannot see.

**NR-12 is the strongest as *discipline*.** The tempting move was the wrong one in a way
invisible from the result. Deriving k = 1.74826×10⁻⁴ from the primary and adopting it would
have shifted every heat flux, surface temperature and bondline temperature in the repository
by 0.4%, invalidated every stored result, and produced a number with **worse** justification
than the one it replaced, all while looking like the conscientious outcome of a validation
exercise.

**NR-10 is the strongest as *method*.** A project-defined metric was defined, given a
falsification threshold in a config file **before** the run, and then discarded when the
threshold fired. The pre-registered mechanism was also half wrong, and the diagnostic that
refuted it (shape invariance, minimum pairwise cosine similarity 0.9366) turned out to be
worth more than the verdict, because it changes what future work should try.

If forced to one: **NR-15**, because it is the only one that was actively corrupting an
optimisation result at the time it was found.

**Evidence.** `docs/negative_results.md` NR-10, NR-12, NR-15 (including the 2026-09-20
follow-up), and the other 21 entries.

**Push.** *"Which assumptions, if corrected, would weaken your headline result? Which would
strengthen it?"* **Weaken**: ablation, because an ablator carries energy away as mass loss
disproportionately in the long shallow case (A-TRAJ-3); it reduces the size of the effect
without reversing it, because the mechanism is a diffusive timescale rather than a
magnitude. **Strengthen**: temperature-dependent conductivity, because real insulator
conductivity rises with temperature and would raise the bondline in the long shallow case
(A-TPS-2). **Neutral on direction, large on magnitude**: catalycity, radiation, and the
effective-nose-radius disagreement.

---

### Q47. What is the strongest *process* failure in this project?

**A.** NR-18. A two-hour M5 run was launched detached, and while it ran a concurrent
work-stream changed `src/aether/evaluate.py` to the velocity-gradient nose radius. The runner
had snapshotted its config at launch, so the config edit could not reach it, but worker
processes import `src/aether` when they are spawned, so a **source** edit can split one
candidate log between two physics models with nothing in the log to say which row is which.
The run header said only "dirty tree". A matched-budget comparison whose methods were
evaluated by different physics is not a comparison.

The run was killed part-way through, no `summary.json` was written and no number from it was
inspected; the directory is kept with a README saying it must not be analysed. The failure
was organisational, not numerical, and it would have produced a complete, plausible,
well-formatted report, which is why it is the worst kind.

What changed: a whole-tree source hash recorded at launch and re-checked before and after
every (method, seed) and after every logged batch, writing `ABORTED.md` and stopping on a
mismatch *after* the batch already paid for is on disk; a refusal to start on a stale DOE
screening; and the removal of every pre-written interpretive sentence from the generated
report, because its first version stated as prose that every front leans on the bluntness and
mass fences, which was true of M4's model and false of the one that replaced it an hour
later.

**Evidence.** `docs/negative_results.md` NR-18, NR-24;
`src/aether/optimization/guards.py`; `REPRODUCIBILITY.md` §"What is deterministic".

**Push.** *"Did the guard then get in your way?"* Yes, twice, correctly: it aborted two M6
dry runs because another work-stream was editing `src/aether/uncertainty` (NR-24). The
response was a *verified* exclusion, which lets a sub-package be left out of the hash but
refuses to continue if that sub-package has actually been imported into the process, so the
exclusion cannot hide a real dependency. It is rejected outright in `mode: study`.

---

### Q48. What would falsify H0? What experiment or simulation would you run to try?

**A.** H0 says minimising peak heat flux alone does not necessarily produce the thermally
safest re-entry solution. It is falsified by demonstrating that, over a domain where the
model is valid, the design minimising peak heat flux **also** minimises the in-depth thermal
response, with no counterexample pair.

Three ways to try, in increasing cost:

1. **Change the stack so the timescales separate.** Make the insulator thick enough that
   t_diff ≫ t_entry and the bondline stops responding. NR-03 already did this accidentally at
   40 mm, where the bondline moved 9 K over an entire entry. That is a genuine falsification
   of the claim *for that stack*, and it is why the result is stated as being about where the
   trade lives.
2. **Put the two objectives on the same side of the trade.** The anti-correlation is carried
   by entry angle through the pulse duration. A design space where the dominant variable
   moves both metrics the same way (for example, one where only ballistic coefficient varies
   and duration barely changes) would break it.
3. **Measure it.** The M8 coupon compares high-peak/short against lower-peak/long heating on a
   real specimen with a blind prediction archived before measurement. If the measured in-depth
   response contradicts the model's ordering, the mechanism itself is in question rather than
   the magnitudes.

**Evidence.** `docs/negative_results.md` NR-03; `experiments/thermal_coupon/protocol.md`;
`CLAUDE.md` §4 (hypotheses as written).

**Push.** *"Your M1 result was stronger than H0 required. Does that worry you?"* It should,
and it is recorded that way. H0 asks for the existence of *one* counterexample pair; the
sweep returned a perfectly anti-ordered domain. The reporting was changed to lead with the
monotonicity rather than with the single strongest pair, because quoting the two endpoints of
a monotone sweep as a dramatic pair overstates how special they are. A result that arrives
stronger than the hypothesis asked for is usually a sign that the hypothesis was easy, and
saying so is cheaper than being told.

---

### Q49. What is the single biggest thing this project has not done?

**A.** Validated anything against a physical measurement. Every `PASS` in the matrix is
against a published number, an analytical solution, or an independently implemented closed
form. There is no experiment behind any of it. M8 is the row that would change that, and it
is `IN_PROGRESS` with no coupon printed.

Second biggest: **gate G4 is not PASS**, so no CFD result may enter the optimisation loop,
and every optimisation number in the repository is Fidelity 0 with a constant drag
coefficient. M3's drag surface exists, is registered, and is switched off.

Third: the largest unquantified uncertainty in the heating chain, catalycity, has no number
attached and is not in M7's inventory, so every uncertainty figure the project produces is a
lower bound.

**Evidence.** `VALIDATION_MATRIX.md` rows M8, G4, G2′; `docs/final_quality_gate.md`.

**Push.** *"So what is the defensible claim, in one sentence?"* Within a verified
reduced-order model and a documented set of assumptions, peak external heat flux and peak
bondline temperature are optimised by different entry trajectories, and a joint objective
selects a design with measurably more bondline margin than a peak-flux-only objective does.
Nothing in the repository is a statement about a flight vehicle or a real TPS material.

---

## Appendix — questions that cannot be answered yet

Listed so that nobody is tempted to answer them from a smoke run or a superseded report.

| Question | Blocked on | Criterion, already declared |
|---|---|---|
| Where does the Pareto front lie under the corrected heating model and the CFD drag surface? | `make doe && make optimize` after G4 = PASS | A-OPT-4 hypervolume points, fixed before any run |
| Does the LLM agent beat NSGA-II or Bayesian optimisation at a matched budget? | `make ablation` | A-AI-7: ΔHV ≥ 0.005 **and** exact permutation p < 0.05 after Holm |
| Does adaptive fidelity save CFD calls (H2)? | `make adaptive` | A-AF-9, including the `NOT_TESTABLE` verdict if the no-CFD arm reaches the target |
| How wide are the answers, and which ignorance dominates? | `make uncertainty` | A-UQ-1 p-box; Sobol' attribution over the uncertain inputs |
| Do the front designs survive chance constraints? | `make robust` | A-UQ-ROB-1: P(violation) ≤ 0.05 per constraint, 95th-percentile objectives |
| Does the measured coupon match the frozen prediction? | M8 experiment | `protocol.md` §9, tolerance to be declared **before** the runs |
| What is the §39 four-row comparison table? | all of the above | A-UQ-39-1: every row re-evaluated under one source hash |
