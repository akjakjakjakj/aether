# 5. Methods, part 1: the reduced-order model (Fidelity 0)

*Draft. Does not depend on any pending run. The Fidelity-1 half of Methods is specified in
`reports/final/paper_outline.md` §5 and is not drafted, because it is conditional on gate
G4.*

Everything below is the chain that produced the results in §7. It is called Fidelity 0
throughout, and the label is on every number it produces. Its defining property is that the
drag coefficient is a constant, so the capsule's forebody *shape* has no aerodynamic
consequence at all and only its diameter acts, through the reference area.

---

## 5.1 The canonical evaluator

One function, `evaluate_design(config)`, performs the whole chain: validate the geometry,
obtain the aerodynamic model, integrate the trajectory, compute the heat-flux history, solve
the TPS response, compute the objectives, check the constraints, attach uncertainty metadata,
and return a status. **No study bypasses it**, including the uncertainty propagation, which
would naturally have looped over draws outside the optimiser and was instead implemented by
appending the draw index to the design space as one synthetic variable, so that each
design-and-draw pair is an ordinary design vector that is charged and logged like any other.

The reason for the rule is that a study which builds its own evaluation shortcut produces
numbers that cannot be compared with any other study's. It also makes certain classes of
error impossible to reintroduce: the post-entry soak-out phase, which was once omitted and
understated the bondline peak by about 50 K, lives inside the evaluator rather than in a
study script.

Determinism and provenance are verified rather than assumed. Three runs of the evaluator on
one configuration produce identical result fingerprints covering every metric, every
constraint margin, every diagnostic, the provenance block and the entire velocity history,
bit for bit.

---

## 5.2 Atmosphere

**0 to 86 km** is computed exactly from the U.S. Standard Atmosphere 1976's defined layer
profile, with an ideal-gas closure, using geopotential altitude so that the hydrostatic
integration can be carried out at constant gravity, which is what makes the standard's layer
profiles closed forms.

**86 to 150 km** is log-interpolated from a transcribed table. USSA-76 above 86 km uses
individual per-species barometric equations with diffusion coefficients and a varying mean
molar mass, which is out of scope, so the table is a stand-in for that model and every value
returned from this region is flagged `extrapolated` at runtime.

**Above 150 km** the model refuses to return values and raises, because silent extrapolation
is a worse failure than an exception.

The assumption originally attached to the 86 to 150 km region was that its density
contribution is negligible. **That is true for peak heat flux and false for the bondline**,
and the correction is quantified in §17: over a 3000-point Latin Hypercube the share of
integrated external heat load accruing above 86 km has a median of 9.5% and a maximum of 27%,
and among feasible designs it is never below 5.0%. The share is now a per-candidate
diagnostic.

Real density varies by tens of percent with solar activity, season and latitude. That is
handled as an uncertainty input rather than ignored.

---

## 5.3 Trajectory

A point-mass three-degree-of-freedom planar entry over a non-rotating spherical Earth, with
state [altitude, velocity, flight-path angle, range], integrated with an adaptive Runge–Kutta
scheme and terminal events. Gravity is inverse-square, g = μ/r², with the mean volumetric
Earth radius of 6371 km. Integration stops at 20 km altitude, below which the aerothermal
problem is over and descent phases that are out of scope take over; the thermal solve
continues past that point.

Assumptions and their directions:

- **Non-rotating Earth.** Earth rotation changes relative velocity by up to about 0.46 km/s
  at the equator, which is up to about 6% on V and therefore up to about 19% on q″ because
  heating goes as V³. That shifts magnitudes and does not reverse the ordering between a
  steep and a shallow entry.
- **Constant drag coefficient, no angle of attack, no lift, no bank.** This is the defining
  Fidelity-0 assumption. Real C_D falls through the transonic regime, but that phase is below
  peak heating, so the peak-flux ordering is robust to it while the integrated load, and
  therefore the bondline result, is more sensitive.
- **Constant mass**, no ablative mass loss, because ablation chemistry is out of scope. An
  ablator would carry energy away as mass loss, disproportionately in the long shallow case,
  which would **reduce** the size of the reported effect without reversing it, because the
  mechanism is a diffusive timescale rather than a magnitude.

Two optional hooks, `gravity_m_s2` and `planet_radius_m`, exist solely so that a published
reference case computed with constant gravity can be reproduced under its own assumptions.
Both default to the production behaviour, and a test asserts that the default path is
bit-identical with them present.

---

## 5.4 Aeroheating

Stagnation-point convective heating from a Sutton–Graves-form correlation,

    q̇″ = k √(ρ_∞ / R_eff) V_∞³,   k = 1.7415×10⁻⁴ kg^½ m⁻¹,

with the integrated external heat load computed as its time integral.

Four assumptions, all of which bias the result in a stated direction:

- **Convective only.** Shock-layer radiative heating is neglected, which is defensible at
  about 7.4 km/s with a metre-scale nose radius and would be indefensible at lunar-return
  speeds. It under-predicts total heating, more so for the steep hot case, which makes the
  reported effect conservative.
- **Cold wall.** No hot-wall or blowing correction. Over-predicts flux into a hot surface;
  conservative.
- **Stagnation point only.** The whole TPS is analysed at the stagnation-point condition,
  which is the worst point on the vehicle for this quantity. Real vehicles are frequently
  damaged at the shoulder or the afterbody, about which this model says nothing. **This is a
  genuine limitation, not a conservatism**, and it becomes important in §10, where the
  corrected heating model gives an optimiser a reason to prefer a sharp shoulder.
- **The constant is uncertain at the several-percent level.** Its re-derivation from the
  primary source is §6's business; the operational conclusion is to treat this correlation as
  ±4% at best and to propagate that rather than assume it away.

### 5.4.1 The effective nose radius

The radius fed to the correlation is **not** the nose cap radius in general, and getting this
right was a correction to the model rather than a refinement of it.

`1/√R_n` is a statement about the stagnation-point velocity gradient (dU/dS)_s, the rate at
which flow accelerates sideways away from the stagnation point. Heating follows it because
the stagnation boundary layer is continuously swept away by that accelerating flow, giving a
thickness δ ~ √(ν / (dU/dS)_s) and therefore q̇″ ∝ √((dU/dS)_s). For a sphere the only
available length is its radius, so the gradient must go as 1/R and the familiar 1/√R follows.
**That is a property of spheres.** For a shallow spherical cap the flow reaches the shoulder
within about a fifth of a quarter-circle from the tip, and the distance over which pressure
falls from its stagnation value is set by the body radius and the corner, so the benefit of
flattening the nose saturates.

The standard repair, used by both primary sources, is to keep the sphere formula and feed it
the radius of the hemisphere that would produce the body's actual gradient,

    R_b / R_eff = (dU/dS)_s,BB / (dU/dS)_s,hemi.

The implementation interpolates nine measured values of R_b/R_eff over K = R_b/R_n and
R_c/R_b from Ellison's Table I, with an exact hemisphere anchor at K = 1 that follows
identically from the defining relation. **Neither primary publishes a formula, so the
interpolation, shape-preserving cubic in K and linear in R, is this project's own
construction** and is labelled as such wherever it appears. Outside K ≤ 1 the model falls
back to R_eff = R_n and flags the result, because a nose radius smaller than the body radius
is a sphere-cone rather than a spherical segment and neither source covers it.

Validity, from the primaries: zero angle of attack, K in [0, 1], R_c/R_b ≤ 0.4, and Mach
above about 3.5, the last resting on the finding that the stagnation-region pressure
distribution is invariant above that Mach number, which is what licenses using Mach 8 tunnel
data at 7.4 km/s.

The uncertainty is larger than the heating constant's. Ellison states that his data disagree
with the other primary by about 20% at K = 0.417, which is where this project's shallow-cap
designs sit, and 20% on R_eff is about ±10% on heat flux. Ellison is used because it is
tabulated rather than read off a graph, is an experiment rather than a computation from
another study's pressure data, and is the conservative of the two.

**Which results use which model.** The legacy setting, R_eff = R_n, remains the dataclass
default so that every pre-existing configuration and stored result is untouched. The
velocity-gradient model is the default in the design-space configuration. The two agree
identically at K = 1, which is why the baseline and the §7 results, all of which use a
hemisphere-nosed body with R_n = D/2, are bit-for-bit unchanged by the correction, while the
shallow-cap optimisation fronts move by about 20% in peak heat flux.

---

## 5.5 Thermal protection system

A one-dimensional transient conduction solve normal to the surface through a multilayer
stack, discretised by finite volumes with harmonic interface conductivities and advanced by
backward Euler.

**Why harmonic interfaces.** At a layer boundary the conserved quantity is the heat flux, and
two slabs in series add thermal resistances. The harmonic mean of the conductivities,
weighted by the half-cell widths, is what that addition gives. An arithmetic mean would let
the conductive layer dominate and pass too much heat across a strong conductivity contrast,
which for an insulator-on-aluminium stack is precisely the interface that sets the bondline
temperature.

**Why backward Euler.** Unconditional stability for diffusion. The explicit limit
Δt ≤ Δx²/(2α) is of order 0.018 s for this mesh, which over an entry plus soak-out would
force of order 10⁵ timesteps for stability alone, against roughly 2800 implicit steps taken.
The scheme is first order in time, which is convergent and adequate but costs steps that
Crank–Nicolson would not; that trade is recorded as an open item rather than presented as a
choice with no downside.

**The surface boundary condition is nonlinear and is handled by Newton linearisation.** The
balance is q_net = q_conv − εσ(T_s⁴ − T_sink⁴), with ε = 0.85 and a 4 K sink. Solving it by
damped fixed-point iteration diverges, because the local gain of an iteration on a T⁴ law is
4εσT³·R_half and exceeds 1 at entry surface temperatures, so damping only slows the
divergence. Linearising the radiation term about the current surface estimate,
q_rad ≈ q_rad(T*) + h_rad(T_s − T*) with h_rad = 4εσT*³, makes the surface flux affine in the
unknown and folds it into the tridiagonal system, and because h_rad only adds to the diagonal
the scheme is unconditionally stable.

**The back face is adiabatic**, which is conservative: no heat is allowed to escape behind
the structure, so bondline temperature is over-predicted for every case, which does not change
the ordering between cases.

**The solve continues past the end of the trajectory.** A soak-out phase runs for a
configurable period, 1200 s by default, at zero incident flux with re-radiation still active,
because the bondline peak lags the heat pulse. Omitting it under-predicted the bondline peak
by about 50 K for a 20 mm stack. Every candidate carries a diagnostic of its bondline warming
rate at the end of the window, so a truncated solve is visible rather than silent.

**Material properties are engineering placeholders** of the right order for a low-density
insulator over an aluminium-like structure. They are not the properties of any qualified TPS
material, and the consequence is that absolute temperatures are indicative only. The result
is about a mechanism, not about a product.

**Stack sizing is a modelling decision with consequences**, and it is stated as one. At 40 mm
of insulator the bondline moved 8.8 K across an entire entry, because the diffusion length
√(αt) with α ≈ 8.9×10⁻⁷ m²/s over a 245 s entry is about 15 mm and the bondline behind 40 mm
never learns about the entry. The stack was sized to 15 mm, where the bondline is a live
design constraint, which is also where a real design would sit, because insulation is mass.
The effect being studied *can* be designed away by brute-force insulation at a mass cost, and
saying so is what makes the result a statement about where the trade lives rather than a
claim that every vehicle is exposed to it.

Additional bench boundary terms exist for the coupon experiment: front- and back-face
convective loss, back-face re-radiation, and a series contact resistance at the
flux-application plane. **Every one defaults to zero**, which reproduces the adiabatic
radiating entry model exactly, and a test asserts that the defaults leave the entry model
bit-identical.

---

## 5.6 Geometry

The forebody is parametrised as sphere, cone, torus, cone, flat base. A pure spherical
segment of the Apollo type is represented as the limiting case where the straight fore-cone
segment has numerically zero length, rather than through a discrete shape flag, so that one
parametrisation covers both flown families without a mode switch that downstream code would
have to branch on.

Validity is decided by one method, `CapsuleGeometry.validate()`, which is called inside the
evaluator. An invalid capsule is returned as an infeasible candidate carrying the validator's
own message, with NaN metrics and no physics run, and it stays in the candidate log. That
matters more than it sounds: it means the boundary of the valid region is data rather than a
silent absence.

Volumes are computed from exact closed forms for the spherical cap and both conical frusta
with an adaptively quadratured contribution from the toroidal shoulder, and are cross-checked
against an independent numerical integration of the profile and against the exported mesh's
own volume by the divergence theorem. STL export is deterministic byte for byte, and
watertightness and outward normal orientation are verified by reading the written file back
rather than inferred from the construction being closed by design.

---

## 5.7 Constraints, metrics and what is reported

Every evaluation returns: peak external heat flux, integrated external heat load, peak surface
temperature, peak bondline temperature, a bondline exposure metric, thermal penetration depth,
maximum deceleration, maximum dynamic pressure, entry duration, feasibility, and the margin on
every constraint.

**An unsourced constraint limit is stored as `null` and skipped, never treated as satisfied.**
An unknown constraint is an open question, and a large placeholder would be silently satisfied
by every design and would produce false feasibility claims indistinguishable from real ones.

Two limits are active and their status differs:

- **Bondline allowable, 450 K.** Sourced. It is 449.8 K, the 350 °F design temperature limit
  of the Space Shuttle Orbiter's aluminium primary structure. It is a *substrate* limit rather
  than a universal bondline constant, so it is the right number only because this project's
  structure layer is aluminium-like; against a stainless or composite substrate it would be 83
  to 140 K higher and much of the currently infeasible space would open.
- **Deceleration limit, 12 g.** Not sourceable as written. No document states a flat 12 g;
  the applicable standard gives a duration-dependent curve, and for a deconditioned crew 12 g
  exceeds it beyond about one to two seconds. The number has deliberately not been changed,
  because the two available readings decide what kind of vehicle this is and that is an
  engineering choice rather than an audit's. The full decision, with its measured effect on the
  feasible region, is in §16.

Every candidate also carries artefact diagnostics: the share of external heat load accrued
above 86 km, the bondline warming rate at the end of the soak-out window, the bluntness ratio,
and the heat-shield mass fraction. These exist because an optimiser finds whatever the model
gets wrong before a reader does, and they are per design so that a winning design can be
inspected physically rather than trusted.

---

## Notes for revision

- Every assumption referenced here has an ID in `ASSUMPTIONS.md` and the final text should
  carry the IDs, so a reader can go from a sentence to the signed assumption without
  searching. They are omitted in this draft to keep it readable.
- §5.4.1 is the longest subsection and should stay that way. It is the one place in the
  methods where the project changed its own physics, and a reader who does not follow it
  cannot evaluate §10.
- The Fidelity-1 half of Methods attaches after §5.7 and is conditional on gate G4.
