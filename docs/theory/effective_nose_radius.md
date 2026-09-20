# The effective nose radius — why a flat face is not an infinitely blunt sphere

**Status.** This closes the model-validity failure recorded as NR-15 and the placeholder
it forced (`ASSUMPTIONS.md` A-GEO-3, A-OPT-5). Written 2026-09-20.

**Result in one line.** Sutton–Graves' `1/√R_n` is really a statement about the
stagnation-point *velocity gradient*, and for a shallow spherical cap that gradient stops
following the cap's curvature — so the benefit of flattening the nose **saturates**. For
AETHER's M4 front the radius that belongs in the heating equation is **0.69 × the cap
radius**, not the cap radius, and peak heat flux is **20.5% higher** than the M4 report
states.

---

## 1. What the heating equation is actually asking for

AETHER computes stagnation heating as

$$\dot q'' = k\,\sqrt{\frac{\rho_\infty}{R_n}}\,V_\infty^{3}$$

and the temptation is to read `R_n` as "the radius of the round thing at the front". It is
not. It is a stand-in for a flow quantity, and it is worth seeing exactly which one.

### The stagnation-point velocity gradient

At the stagnation point the oncoming air is brought completely to rest. Just off that
point, flow begins to slide sideways around the body, and it speeds up as it goes. Call
the distance measured along the surface from the stagnation point $S$, and the speed of
the flow just outside the boundary layer $U_e$. Right at the stagnation point $U_e = 0$;
a little way round, $U_e$ has grown roughly in proportion to $S$. The constant of
proportionality,

$$\left(\frac{dU}{dS}\right)_s ,$$

is the **stagnation-point velocity gradient**. Units: $\mathrm{s^{-1}}$. It measures how
violently the flow is made to turn and accelerate as it escapes the stagnation point.

### Why heating follows it

Heat crosses into the wall by conduction through the boundary layer, so the flux goes as
the temperature difference divided by the layer's thickness $\delta$:

$$\dot q'' \sim k_{\text{air}}\,\frac{T_{\text{shock layer}} - T_{\text{wall}}}{\delta}.$$

A stagnation boundary layer does not have time to thicken along the surface — it is
continuously *swept away* sideways by the accelerating flow and continuously rebuilt. The
faster the sweeping, the thinner the layer that survives. Balancing the rate at which
viscosity diffuses momentum outward against the rate at which the flow carries it away
gives the standard stagnation-layer thickness

$$\delta \sim \sqrt{\frac{\nu}{(dU/dS)_s}} .$$

Put the two together:

$$\boxed{\ \dot q'' \;\propto\; \sqrt{\left(\frac{dU}{dS}\right)_s\ }\ }$$

**This is the real law.** A steeper velocity gradient means a thinner boundary layer means
more heat into the wall — and because thickness goes as the square root of the gradient,
so does the flux. Everything else here is a question of how to get that gradient for a
given shape.

### Where `1/√R_n` comes from, and what it assumes

For a **sphere**, Newtonian flow gives the gradient in closed form:

$$\left(\frac{dU}{dS}\right)_{s,\text{hemi}} \;\approx\; \frac{1}{R}\sqrt{\frac{2 p_s}{\rho_s}}$$

(Zoby & Sullivan eq. 3). Dimensionally this is forced: the only length available is the
sphere's own radius, so the gradient *must* go as $1/R$. Substituting into
$\dot q'' \propto \sqrt{(dU/dS)_s}$ gives $\dot q'' \propto 1/\sqrt{R}$ — the familiar
form.

> [!important]
> The `1/√R_n` scaling is **a property of spheres**, not a general law of blunt bodies. It
> is correct exactly when the only length scale the flow can feel at the stagnation point
> is the nose radius. The moment that stops being true, so does the scaling.

---

## 2. Why it stops being true, and why a flat face is not "infinitely blunt"

Take AETHER's own front designs. They are 3.38 m across, so the body radius is
$R_b = 1.69$ m — but the nose cap radius is $R_n = 4.02$ m, nearly **two and a half times
the body radius**. That cap is very gently curved. Sweeping from the tip, the sphere
covers only about 21° before the shape has to turn and become the shoulder.

Now ask what the air does. It is brought to rest at the tip and starts sliding outward.
Under the `1/√R_n` picture it should feel a 4 m radius of curvature all the way and
accelerate very gently indeed. **It does not get the chance.** Within a fifth of the way
round a quarter-circle it has reached the shoulder, where the surface turns hard through
the corner radius and the flow is dumped down the side of the vehicle. The pressure
gradient that drives the acceleration is set by the distance over which the pressure must
fall from its stagnation value to something much lower — and *that* distance is fixed by
the **body radius**, not by the cap's curvature.

So the flow accelerates faster than the cap radius alone would suggest. Steeper gradient,
thinner boundary layer, more heating than `1/√R_n` predicts.

Push it to the limit. A genuinely **flat face** has $R_n = \infty$. Taken literally,
`1/√R_n` says the velocity gradient is zero, the boundary layer is infinitely thick, and
**the stagnation heating is zero**. That is not a small error; it is the wrong answer by
an infinite factor, and it is exactly the direction an optimiser will happily run in. The
real flat-faced cylinder has a perfectly finite gradient: the flow still has to get from
rest at the centre to the rim in a distance $R_b$, and the corner still turns it. Tauber
makes the same point from the other side — modified Newtonian theory gives *zero* gradient
for a flat face while measurement gives a clearly non-zero one.

### The fix: an effective radius

The standard repair, and the one both primaries use, is to keep the sphere formula and
change the radius you feed it. Define $R_{\text{eff}}$ as the radius of the hemisphere
that *would* produce the blunt body's actual gradient:

$$\left(\frac{dU}{dS}\right)_{s,\text{BB}} \;\approx\; \frac{1}{R_{\text{eff}}}\sqrt{\frac{2 p_s}{\rho_s}}
\qquad\Longrightarrow\qquad
\frac{R_b}{R_{\text{eff}}} \;=\; \frac{(dU/dS)_{s,\text{BB}}}{(dU/dS)_{s,\text{hemi}}}$$

(Zoby & Sullivan eqs. 4 and 5, where the reference hemisphere has the **body** radius
$R_b$). Then feed $R_{\text{eff}}$ to Sutton–Graves and everything downstream is unchanged.

> [!note]
> That last step is not this project improvising. Zoby went on to publish a
> Sutton–Graves-form correlation written with $R_{\text{eff}}$ substituted for the nose
> radius, citing his own TM X-1067 for it (NASA TN D-4799, eq. 1). The substitution is
> the original author's.

**For a sharp-cornered flat face the measured answer is $R_{\text{eff}} \approx 3.2$ to
$3.5\,R_b$.** So a flat face heats like a sphere about three times the body radius — blunt,
certainly, but *finite*, and nothing like the infinitely-blunt zero-heating body that
`1/√R_n` promises. This is the origin of the "3.3–3.4 × body radius" rule of thumb that
circulates in hypersonics teaching. It is supported by the primaries; it is **not** a
universal constant (see §5).

---

## 3. The two dimensionless groups, and the data

Everything above collapses into two ratios, written here in the sources' own notation:

| symbol | meaning | AETHER's M4 front |
|---|---|---|
| $K = R_b/R_n$ | body radius over nose radius. $K=0$ is a flat face, $K=1$ is a hemisphere | **0.417 – 0.425** |
| $R = R_c/R_b$ | corner radius over body radius. $R=0$ is a sharp corner | **0.200** |

Note $K$ is the **reciprocal** of the "bluntness ratio" the rest of AETHER talks in
(bluntness $= R_n/D$, so $K = 1/(2\times\text{bluntness})$). A *large* bluntness is a
*small* $K$.

**Neither primary publishes a formula.** Zoby & Sullivan print faired curves; Ellison
prints a table and two charts; a third report of the same era tells the reader in as many
words to interpolate from the charts. The numbers AETHER uses are Ellison's table:

**NASA TN D-5121, Table I, α = 0° rows — $R_b/R_{\text{eff}}$**

| $K = R_b/R_n$ | $R=0$ (sharp) | $R=0.2$ | $R=0.4$ |
|---|---|---|---|
| 0 (flat face) | 0.317 | 0.377 | 0.455 |
| 0.417 | 0.587 | **0.609** | 0.640 |
| 0.707 | 0.738 | 0.772 | 0.817 |
| 1 (hemisphere) | 1.000 | 1.000 | 1.000 |

The last row is not measured — Ellison's experiment stops at $K = 0.707$ — and it is not
read off anything either. When $R_n = R_b$ the segment *is* a hemisphere, eq. (5) gives
$R_{\text{eff}} = R_b = R_n$ identically, and a corner radius has nothing left to blend.
Zoby & Sullivan's figure 4 shows all five of their curves meeting at exactly 1.0 there.

Two behaviours in this table are worth reading off directly:

- **It saturates.** Going down the first column, $R_b/R_{\text{eff}}$ does not head for
  zero as the nose flattens; it heads for 0.317. So $R_{\text{eff}}$ heads for
  $3.155\,R_b$ and stops.
- **A rounder corner makes things worse.** Along each row, $R_b/R_{\text{eff}}$ *rises*
  with corner radius, so $R_{\text{eff}}$ falls and heating goes up. Rounding the shoulder
  gives the flow an easier path around, it accelerates harder, the layer thins. Zoby &
  Sullivan quantify the same effect: at $K=0$, going from a sharp corner to $R=0.3$ raises
  the heating ratio by about 11%.

The interpolation between these points — shape-preserving cubic in $K$, linear in $R$ —
is **this project's construction**, not the literature's, and is documented as such in
`src/aether/geometry/stagnation_gradient.py`.

---

## 4. The worked number for AETHER

Take the M4 knee design: $D = 3.377$ m, bluntness $= 1.188$, shoulder ratio $= 0.10$.

1. Body radius $R_b = D/2 = 1.689$ m.
2. Nose cap radius $R_n = 1.188 \times 3.377 = 4.012$ m.
3. $K = R_b/R_n = 1.689/4.012 = 0.421$.
4. Corner radius $R_c = 0.10 \times 3.377 = 0.338$ m, so $R = R_c/R_b = 0.200$.
5. The table at $K = 0.417$, $R = 0.2$ reads $R_b/R_{\text{eff}} = 0.609$ — and $K=0.421$
   is so close to the tabulated point that interpolation barely moves it.
6. $R_{\text{eff}} = 1.689/0.609 = 2.77$ m.

Compare: the old model fed Sutton–Graves $R_n = 4.01$ m. The correct value is 2.77 m —
**31% smaller**. Since $\dot q'' \propto 1/\sqrt{R_{\text{eff}}}$:

$$\frac{\dot q''_{\text{corrected}}}{\dot q''_{\text{old}}} = \sqrt{\frac{4.01}{2.77}} = 1.20$$

**Peak heating is 20% higher than M4 reported.** Not because the design changed, but
because the old model was reading the wrong length off the geometry.

> [!tip] The sanity check to remember
> $R_{\text{eff}} = 2.77$ m sits **between** the body radius (1.69 m) and the cap radius
> (4.01 m). That is where it must sit for a shallow cap: the flow feels something blunter
> than the body itself, but nothing like as blunt as the cap pretends to be. If a
> calculation ever puts $R_{\text{eff}}$ above $R_n$ for $K \le 1$, it is wrong.

---

## 5. How wrong this can be, and where it must not be used

**The uncertainty is the two primaries' disagreement, and it is not small.** Ellison
compared his measurements directly against Zoby & Sullivan (his p. 5, verbatim):

> "The data of the present investigation agree with the results of Zoby and Sullivan
> (ref. 6) within 10 percent for K = 0 and K = 0.707; however, for K = 0.417 and R = 0,
> the disagreement is about 20 percent."

$K = 0.417$ is, awkwardly, exactly where AETHER's front sits. Twenty percent on
$R_{\text{eff}}$ is about **10% on heat flux** — larger than the Sutton–Graves constant's
own ±4% (A-HEAT-1), and it must be propagated in M7 rather than assumed away. AETHER uses
Ellison, which is the **conservative** of the two: smaller $R_{\text{eff}}$, hence more
heating.

**Four places this must not be used:**

1. **$K > 1$** — a nose radius *smaller* than the body radius. That is a sphere-cone
   (Viking, Pathfinder, MSL), not a spherical segment, and neither source covers it. The
   code falls back to $R_{\text{eff}} = R_n$ there and flags it. The one hint available
   says a conical flank *raises* $R_{\text{eff}}$, so the fallback is probably
   conservative — but that is a hint, not a source.
2. **Angle of attack.** Every number used here is α = 0°. AETHER's trajectory is
   ballistic and non-lifting (A-TRAJ-2), so this costs nothing today and blocks any future
   lifting entry.
3. **M < 3.5.** Ellison measured at M = 8 in a perfect-gas wind tunnel; AETHER flies at
   7.4 km/s in real air. The transfer rests entirely on Zoby & Sullivan's finding that the
   stagnation-region pressure distribution — and therefore this *ratio*, though not the
   gradient itself — is invariant above about M = 3.5. Below that it is unsupported.
4. **A long straight fore-cone.** The measured bodies blend a spherical cap straight into
   the corner. AETHER's capsule can put a conical segment between them; on the M4 front
   that segment spans under 6% of the body radius, which is close enough to the measured
   shape, but the code reports the number rather than assuming it.

**And one thing this correction creates.** A rounder corner now *raises* stagnation
heating, so an optimiser will want to make the shoulder sharp. A sharp shoulder is exactly
where real vehicles are damaged, and this model — stagnation point only, A-HEAT-4 — says
nothing whatsoever about shoulder heating. That is a new metric-gaming surface, recorded
here and in `configs/design_space.yaml` before the next optimisation run rather than after.

---

## Sources

| Document | Used for | Tier |
|---|---|---|
| Zoby, E. V. & Sullivan, E. M., *Effects of Corner Radius on Stagnation-Point Velocity Gradients on Blunt Axisymmetric Bodies*, NASA TM X-1067, 1965 (NTRS 19660017753) | eqs. (3)–(5) defining $R_{\text{eff}}$; the 11%/22% corner-effect statements; Mach-invariance above 3.5; the hemisphere anchor; the ~2% agreement with measured heating | ✅ T1 — opened, figures and text read at 600 dpi |
| Ellison, J. C., *Experimental Stagnation-Point Velocity Gradients and Heat-Transfer Coefficients for a Family of Blunt Bodies at Mach 8 and Angles of Attack*, NASA TN D-5121, 1969 (NTRS 19690013192) | **Table I** — the nine numbers the model is built on; the stated 10%/20% disagreement with Zoby & Sullivan; the validity range | ✅ T1 — opened, Table I transcribed from a 400 dpi page render |
| Zoby, E. V., *Empirical Stagnation-Point Heat-Transfer Relation in Several Gas Mixtures at High Enthalpy Levels*, NASA TN D-4799, 1968 (NTRS 19680025996) | precedent for substituting $R_{\text{eff}}$ into a Sutton–Graves-form correlation | ✅ T1 — opened |
| Zoby & Sullivan figure 4, digitised | independent cross-check only; never a model coefficient | 🟡 T2 — figure read, ±0.010, one reader |
| Any hypersonics **textbook** stating "3.3–3.4 × body radius" | — | ❌ T3 — no textbook was opened. The rule is supported by the primaries above; cite them, not a textbook |
| Boison & Curtiss (ARS J. 1959); Trimmer (AEDC, DTIC AD0669378) | — | ❌ T3 — citations confirmed real, documents not obtainable |
| Rodrigues, *Closed-Form Reconstruction of Zoby–Sullivan Stagnation-Point Heat-Flux Scaling*, JTHT 2026, DOI 10.2514/1.T7458 | would likely replace this project's own interpolation with a published fit | ❌ T3 — paywalled, not opened. **The single highest-value follow-up on this topic.** |

Full provenance, verbatim quotations and the digitised cross-check data:
`data/reference/stagnation_velocity_gradient.yaml`.
