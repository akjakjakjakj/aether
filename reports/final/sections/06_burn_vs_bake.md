# 7. The burn-versus-bake result

*Draft. Does not depend on any pending run. These are the project's only final results.*

**Fidelity and model version, stated first.** Everything in this section is a Fidelity-0
result: the drag coefficient is a constant, so the capsule's forebody shape has no
aerodynamic consequence and only its diameter acts. The heating uses the **legacy**
effective-nose-radius setting, R_eff = R_n. §7.5 states exactly what that does and does not
mean for these numbers, and the short answer is that for these particular geometries it means
nothing at all, while for the optimisation fronts of §10 it means about 20% in peak heat
flux.

---

## 7.1 The question, and how it was asked

Does minimising peak external heat flux also minimise the temperature reached at the TPS
bondline?

Entry flight-path angle was swept from −8.00° to −1.50° in 41 steps. Every other design
variable was held at the baseline configuration, so any difference between candidates is
attributable to trajectory shape alone. Each candidate ran the full chain through the
canonical evaluator. No candidate was discarded.

The answer is that the two metrics are optimised by different trajectories. The angle
minimising peak heat flux is −1.50°, the shallowest tested; the angle minimising bondline
temperature is −8.00°, the steepest. They are at opposite ends of the tested range.

---

## 7.2 The result

| | A: steep, γ₀ = −8.00° | B: shallow, γ₀ = −1.50° |
|---|---|---|
| Peak heat flux | 230.64 W/cm² | **142.38 W/cm²** |
| Integrated external load | 79.3 MJ/m² | 128.3 MJ/m² |
| Entry duration | 134.8 s | 324.1 s |
| **Peak bondline temperature** | **423.7 K** | 537.8 K |

Candidate B reduces peak heat flux by **38.3%**, a large win by the conventional metric,
while running the bondline **114.1 K hotter**.

An automated search over all 1640 ordered candidate pairs, with detection thresholds declared
in advance so that discretisation noise could not be reported as physics (at least a 1.0%
flux reduction and at least a 1.0 K bondline penalty), found **818 counterexample pairs**.
Every value is read from the stored candidate file; nothing was hand-selected or adjusted.

**The honest statement of what this establishes** is the monotonicity, not a correlation.
Over the full range tested, every step that lowers peak heat flux raises bondline
temperature, and there is no interior entry angle at which both improve. That is enough for
H0.

The rank correlation over this sweep is Spearman ρ = −1.000, and **that number is close to
tautological and must not be quoted as independent evidence.** Only one parameter was varied;
both metrics turn out to be strictly monotone in that parameter; and two strictly monotone
functions of a single variable can only ever give ±1, whatever the physics. The correlation
restates "both are monotone in γ, with opposite signs". It does not measure the strength of a
relationship across a design space, because this domain is a line segment rather than a
space. A claim about a design space needs §7.4's grid and, properly, the design of
experiments.

The same trap was checked for elsewhere rather than assumed to be unique. In the
thermal-penetration-index study, 10 of 10 fixed-diameter lines of a two-dimensional grid give
|ρ| ≥ 0.999 between that index and bondline temperature; those line correlations are reported
there purely to show why only the two-dimensional number counts.

---

## 7.3 The mechanism

The shallower entry decelerates in thinner air over a longer time. Peak flux falls because
q̇″ ∝ √ρ·V³, but the pulse lengthens from 135 s to 324 s and the integrated external load
rises from 79.3 to 128.3 MJ/m².

The TPS is a diffusive low-pass filter. Its characteristic time L²/α is long compared with a
steep entry but *comparable* to a shallow one: with α ≈ 8.9×10⁻⁷ m²/s, the diffusion length
√(αt) over a 245 s entry is about 15 mm, which is the insulator thickness. A short intense
pulse is absorbed near the surface and re-radiated away at T⁴ before it can diffuse inward. A
long mild pulse has time to reach the bondline.

Peak flux is a **surface** quantity. Bondline temperature is an **integrated and delayed**
one. Optimising the first does not constrain the second.

The comparability of the two timescales is what makes the effect exist, and it is also what
bounds the claim. Behind 40 mm of insulator the bondline rose 8.8 K across an entire entry:
the effect can be designed away by brute-force insulation, at a mass cost. The result
identifies where the interesting trade lives; it is not a claim that every vehicle is exposed
to it.

---

## 7.4 The feasibility squeeze, and the geometry axis

Of the 41 candidates, **zero satisfy every hard constraint**. Steep entries violate the
deceleration limit; shallow entries violate the bondline limit; nothing in between satisfies
both.

**This was not anticipated.** With the geometry frozen, trajectory shape alone cannot produce
a valid design. It is not a modelling failure; it is the result that motivates optimising
geometry and trajectory *jointly* rather than sequentially, and it is what caused the
geometry axis to be opened immediately rather than deferred.

A full-factorial grid over entry angle and capsule diameter, 140 coupled evaluations with
mass held constant so that diameter sets the ballistic coefficient and bluntness ratio held
constant so that an optimiser cannot exploit the heating correlation, recovers a feasible
region: **21 of 140 designs satisfy every constraint**.

Two optimisers were then run over that feasible set. One minimises peak heat flux, as
conventional practice does. One treats bondline temperature as an objective in its own right.

| | Baseline | Peak-flux-only optimum | Joint optimum |
|---|---|---|---|
| Entry angle γ₀ | −3.00° | −1.50° | −3.50° |
| Diameter | 1.20 m | 3.00 m | 3.00 m |
| Ballistic coefficient β | 257.9 | 41.3 | 41.3 kg m⁻² |
| Peak heat flux | 160.28 | **37.01** | 44.27 W cm⁻² |
| Integrated load | 112.5 | 32.1 | 26.5 MJ m⁻² |
| Peak surface temperature | 2381 | 1626 | 1699 K |
| **Peak bondline temperature** | 494.8 | 444.1 | **411.6 K** |
| Bondline margin to limit | −10.0% | +1.3% | +8.5% |
| Maximum deceleration | 11.89 | 9.13 | 11.69 g |
| Feasible | no | yes | yes |

The joint optimum runs its bondline **32.5 K cooler** than the design a peak-flux-only search
selects, at a cost of +19.6% on peak heat flux. **H1 is supported.**

### Two things that must be said with that table

**Do not quote the margin as a ratio.** It is tempting to report that the joint design has
several times the thermal margin of the peak-only design. That ratio is measured against the
bondline allowable and is violently sensitive to it:

| Assumed bondline allowable | Margin ratio, joint vs peak-only |
|---|---|
| 445 K | 37.5× |
| 450 K | 6.5× |
| 460 K | 3.0× |
| 500 K | 1.6× |

The robust quantity is the **absolute** difference, 32.5 K, which does not depend on the
allowable at all. That is what is reported. The allowable has since been sourced, which makes
the ratio meaningful in principle, but it is a structural-substrate limit rather than a
universal constant, and against a stainless or composite substrate it would be 83 to 140 K
higher. The absolute difference remains the right thing to quote.

**The diameter bound is active, and that is a defect in the result.** Both optima choose the
largest available diameter, which is the lowest ballistic coefficient. That is the expected
physics, since a lower β decelerates higher in thinner air, and it means **the bound rather
than the physics is selecting them**. A design stopped by a box bound is an optimum of the
box, and should be read as "at least this far in this direction", not as a located minimum.
Justifying that bound from packaging or launch-vehicle constraints, or widening it, is an
open item. Widening it without a mass model produces an optimiser that walks straight out of
the physically possible, which is what happened later and is reported in §17.

---

## 7.5 Which model these numbers came from

The heating in this section used `effective_nose_radius_m = nose_radius_m`, the legacy
setting. That setting was subsequently found to be wrong for shallow spherical caps, because
Sutton–Graves' 1/√R_n is really a statement about the stagnation-point velocity gradient and
only for a sphere is that gradient set by the nose radius. It was replaced with a model that
takes the effective radius from measured stagnation-point velocity gradients. The full story
is §17.

**For the results in this section the replacement changes nothing, and the reason is
geometric rather than fortunate.** M1 and M1b both use a hemisphere-nosed body, R_n = D/2,
which gives K = R_b/R_n = 1. At K = 1 the forebody *is* a hemisphere, and the two models
agree identically by the defining relation. Every number in §7.2 and §7.4 is therefore
unchanged by the correction, and that is verified rather than asserted: the persisted results
reproduce bit-for-bit under the legacy default, and a test pins it.

**For the optimisation fronts of §10 the replacement changes a great deal.** Those designs
are shallow caps at K ≈ 0.42, where the effective radius is 0.685 to 0.693 of the cap radius,
peak heat flux rises by 20.2 to 20.8%, and peak bondline temperature by 6.7 to 9.1 K. The
fronts on disk were computed under the legacy model behind a bluntness cap that has since
been removed, which is why they are superseded rather than reinterpreted.

The distinction matters enough to be stated in one sentence a reader can carry: **the
results in this section are legacy-model results whose geometry makes the legacy and
corrected models identical; the optimisation results are legacy-model results whose geometry
does not.**

---

## 7.6 Figures

| Figure | File | Shows |
|---|---|---|
| Anti-correlation | `reports/figures/M1_anticorrelation.png` | Peak flux and bondline temperature against entry angle |
| Trade space | `reports/figures/M1_trade_space.png` | The two objectives against each other across the sweep |
| Mechanism | `reports/figures/M1_mechanism.png` | Heat-flux history and in-depth response, steep against shallow |
| Temperature field | `reports/figures/M1_temperature_field.png` | Depth against time, showing the bondline peak lagging |
| Integrated load | `reports/figures/M1_integrated_vs_bondline.png` | Integrated external load against bondline temperature |
| Feasible region | `reports/figures/M1b_feasible_region.png` | The 2-D grid with both constraints |
| Optimiser comparison | `reports/figures/M1b_optimiser_comparison.png` | Peak-flux-only against joint selection |

---

## 7.7 Limitations of this result

This is a Fidelity-0 result and is only as good as its assumptions.

- **Constant drag coefficient.** A real capsule's C_D varies with Mach number and angle of
  attack. The *direction* of the effect is robust to this; the magnitudes are not. Replacing
  it is what Fidelity 1 exists to do, and the measured consequence of doing so is that the
  substitution is not a uniform shift: it penalises slender-to-moderate shapes and mildly
  rewards blunt ones.
- **Cold-wall, convective-only, stagnation-point heating.** Radiative heating and a hot-wall
  correction are absent; catalycity is unquantified and is worth roughly a factor of two;
  nothing is known about shoulder or afterbody heating.
- **No ablation.** A real ablator would carry energy away as mass loss, disproportionately in
  the long shallow case, reducing the effect without reversing it.
- **Adiabatic back face, constant material properties, no contact resistance**, and material
  properties that are engineering placeholders rather than those of a qualified material.
  Absolute temperatures are indicative only.
- **The deceleration limit is unsourced as a flat number**, and it decides the feasible
  region. The documented alternative for a deconditioned crew would reduce the feasible count
  from 21 of 140 to 4 of 140 at 10 g and to **zero** at 8 g. That is an open decision,
  reported in §16, and it is the single assumption with the most leverage over the feasible
  region in the project.
- **One parameter was swept for the counterexample search**, and two for the optimiser
  comparison. Both are small design spaces.

The claim supported by this section is narrow, deliberately. *Within this model, peak heat
flux and bondline temperature are optimised by different trajectories, and a joint objective
selects a design with materially more bondline margin than a peak-flux-only objective does.*
No claim is made about any flight vehicle.
