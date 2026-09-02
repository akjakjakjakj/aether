# Negative results and things that broke

Kept deliberately. A repository that only shows what worked is a marketing document.

---

### NR-01 — The radiating boundary condition diverged

**What happened.** The first TPS implementation solved the surface energy balance
`q_net = q_conv − εσ(T_s⁴ − T_sink⁴)` by damped fixed-point iteration. At realistic
entry heat fluxes (~2 MW/m²) the surface temperature overflowed to infinity and the
linear solve failed with `array must not contain infs or NaNs`.

**Why.** Fixed-point iteration on a T⁴ law has a local gain of `4εσT³ · R_half`. At
T ≈ 2000 K that gain exceeds 1, so the iteration is divergent, and damping only slows
the divergence.

**Fix.** Newton-linearise the radiation term about the current surface estimate,
`q_rad ≈ q_rad(T*) + h_rad(T_s − T*)` with `h_rad = 4εσT*³`, which makes the surface
flux affine in the unknown and folds it directly into the tridiagonal system. `h_rad`
only ever *adds* to the diagonal, so the scheme is unconditionally stable.

**Kept because** the failure mode is instructive: an explicit-looking treatment of a
strongly nonlinear boundary condition is not merely inaccurate, it is unstable.

---

### NR-02 — Truncating the thermal solve hid ~50 K of bondline heating

**What happened.** The first version ended the conduction solve when the trajectory
reached its terminal altitude. The bondline peak came out ~50 K too low for a 20 mm
stack.

**Why.** The bondline peak *lags* the heat pulse. Heat already inside the TPS keeps
diffusing inward after aeroheating has stopped, so the peak occurs minutes after the
vehicle has finished decelerating.

**Fix.** The evaluator now continues the conduction solve at zero incident flux for a
configurable soak period (default 1200 s), with re-radiation still active. It is inside
`evaluate_design`, not in a study script, so it cannot be forgotten.

**Kept because** this would have systematically understated the project's own headline
result. It is now a regression test: `test_bondline_peak_lags_the_heat_pulse`.

---

### NR-03 — The first TPS stack was too thick to show anything

**What happened.** With a 40 mm insulator the bondline rose from 300 K to 308.8 K over
the whole entry. The burn-vs-bake effect was invisible.

**Why.** The diffusion length √(αt) for α ≈ 8.9×10⁻⁷ m²/s over a 245 s entry is about
15 mm. Behind 40 mm of insulator the bondline simply never hears about the entry.

**Fix.** The stack was sized to 15 mm, where the bondline is a live constraint. This is
also the realistic design point: nobody flies a heat shield with 2.5× more thickness
than the thermal problem requires, because it is all mass.

**Kept because** it is worth stating plainly that the effect *can* be designed away by
brute-force insulation, at a mass cost. The result is about where the interesting
trade lives, not a claim that every vehicle is at risk.

---

### NR-04 — The Pareto front implementation was wrong

**What happened.** The first `pareto_front` returned all 21 feasible designs as
non-dominated, and the plotted "front" zigzagged.

**Why.** The dominance test had inverted control flow: when it found a point that
dominated candidate *i*, it `continue`d — keeping *i* — instead of marking it dominated.

**How it was caught.** By looking at the rendered figure. A two-objective Pareto front
is necessarily monotone; a zigzag is geometrically impossible, so the plot falsified the
code. The test suite had not caught it because no test asserted monotonicity.

**Fix.** Rewritten as a direct dominance check, plus a monotonicity assertion.

**Kept because** it is the clearest example in this project of a figure functioning as a
test. It is also why the plotting standard requires real axes and real units — a
prettier, less quantitative chart would have hidden it.
