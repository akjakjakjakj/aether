# The Thermal Penetration Index: definition, prior art, and what would make it fail

> Spec §44. Written **before** the study in `reports/milestones/TPI_study.md` was run, so
> that the failure mode predicted below can be judged as a prediction rather than as a
> post-hoc explanation. Literature check performed 2026-09-20.

---

## 1. The definition

    TPI = ∫₀^t_end ∫₀^L  w(x) · max( T(x,t) − T_ref , 0 )  dx dt

| Symbol | Meaning | Unit |
|---|---|---|
| `x` | depth into the stack, measured from the heated surface | m |
| `L` | depth of the integration domain — the TPS layers, **not** the structure behind them | m |
| `t` | time from entry interface, including the post-entry soak-out | s |
| `T_ref` | exceedance datum; temperature below which nothing is counted | K |
| `w(x)` | depth weighting, normalised so its depth-average over `[0, L]` is 1 | – |
| **TPI** | | **K·m·s** |

A Kelvin-metre-second is not a standard engineering unit. It is what falls out of the
definition, and this project does not dress it up as anything else.

Three choices change the number and must always be quoted with it: `T_ref`, the
weighting family, and `L`. They live in `configs/tpi_study.yaml`; the implementation in
`src/aether/scoring/tpi.py` hard-codes none of them.

**Why normalise `w`.** With the depth-average of `w` fixed at 1, a temperature field
with no depth structure scores identically under every weighting family. Any difference
between families on a real field is then attributable to the *shape* of that field, not
to the arbitrary scale of the weight function. Without normalisation, "family A gives a
bigger number" is a statement about A's units.

**Why the depth limit matters.** The baseline stack is 15 mm of insulator on 10 mm of
aluminium. The aluminium is not thermal protection; it is the thing being protected. Its
volumetric heat capacity is ~7× the insulator's, so including it would let the structure
dominate an index whose whole purpose is to describe the insulator. The reference
configuration integrates over the insulator only.

---

## 2. What already exists

The honest framing for §44 is that cumulative thermal-exposure metrics are an old idea
with at least four independent literatures. TPI is a member of that family, not a
departure from it.

### 2.1 Integrated heat load — the metric this project already reports

The standard aerothermal quantity is the time integral of surface heat flux,
`Q = ∫ q″ dt` [J/m²]. NASA's TFAWS aerothermodynamics course defines the pair directly:

> "Heat Rate (q) — Instantaneous heat flux at a point on the vehicle (W/cm2)"
> "Heat Load (Q) — Integration of heat rate with time over a trajectory (J/cm2)"

and states the division of labour that motivates this whole project:

> "Heat flux (with pressure & shear) used to select TPS material
> Heat load determines TPS thickness"

with the stagnation-point form

> "Stagnation point heat load is just the time integration of the heat flux:
> Qs = (k/√Rn) ∫ ½ρV³ dt"

The same document states the entry-angle trade as an exercise, and gives the answer
this project's M1 rediscovered numerically:

> "The selection of γ becomes a trade between peak heat rate (TPS material selection),
> and total heat load (TPS thickness and mass)"
> — with a figure captioned **steep → "Higher Peak Heat Flux"**, **shallow → "Higher
> Peak Heat Load"**.

*Source, opened and read in full: NASA TFAWS 2012, Aerothermodynamics Course,
"Lecture #1: Stagnation Point Heating", slides 4, 9, 46–50.
`https://tfaws.nasa.gov/TFAWS12/Proceedings/Aerothermodynamics%20Course.pdf`*

**This matters for the verdict.** Integrated heat load is a *time* integral of a
*surface* quantity. TPI is a depth-and-time integral of an *in-depth* quantity. If the
two turn out to order designs the same way, that is a finding about this stack, not a
definition.

### 2.2 The bondline criterion is a peak, with a deadline — not an integral

Same source, on TPS sizing:

> "Baseline (zero-margin) sizing computed assuming nominal environments and response
> model to hit given bondline temperature limit"
> "Primary (thermal) margin is applied directly to the TPS design criterion (e.g.
> maximum bondline temperature)"
> "Adhesive failure accounted for by maintaining conservative bondline temperature limit"

So the accepted in-depth criterion in TPS design is a **maximum** at a **single plane**.
That is precisely the thing TPI proposes to generalise: the peak throws away how much of
the stack got hot and for how long. Whether that discarded information is worth
recovering is the empirical question §44 asks.

### 2.3 Thermal dose — CEM43, from hyperthermia

The oncology literature has carried an accepted cumulative thermal-exposure metric since
1984. Sapareto and Dewey's thermal isoeffective dose converts any temperature–time
history into an equivalent number of minutes at 43 °C:

> "Sapareto and Dewey [27] defined a 'thermal isoeffective dose' in terms of cumulative
> equivalent minutes (CEM) at 43°C which allows conversion of any temperature-time (T-t)
> combination to the equivalent time for which the reference temperature of 43°C must be
> applied to obtain the same level of thermal damage, given by
>
>     CEM = ∫₀^t_final R^(43−T) dt          (5)
>
> where R = 0.5 for T ≥ 43° and R = 0.25 for T < 43°."

with the primary reference given in that paper's list as:

> "[27] S. A. Sapareto and W. C. Dewey, 'Thermal dose determination in cancer therapy,'
> International Journal of Radiation Oncology, Biology, Physics, vol. 10, no. 6,
> pp. 787–800, 1984."

*Source, opened and read: Martin, Aubry, Schafer, Verhagen, Treeby, Butts Pauly et al.
(ITRUSST), "ITRUSST Consensus on Standardised Reporting for Transcranial Ultrasound
Stimulation", arXiv:2402.10027 (2024), §4.3, eq. (5).
`https://arxiv.org/pdf/2402.10027`. The Sapareto & Dewey original is paywalled and was
**not** opened; the formula and citation above are one level removed from the primary.*

**What CEM43 does that TPI does not.** CEM43 is *exponentially* weighted in temperature,
with a physically-motivated breakpoint, and it is dimensioned in minutes — a unit a
practitioner already has intuition for. TPI as defined in §44 is *linear* in exceedance
and dimensioned in K·m·s. Linear weighting is the weaker choice: it says 10 K over 100 s
is worth the same as 100 K over 10 s, which is true of no damage mechanism. It is kept
here because §44 specifies it and because a linear index is the simplest thing that
could possibly work; if it fails, a nonlinear variant is the obvious next candidate and
CEM43 is the template for it.

### 2.4 Arrhenius damage integrals — burns and pyrolysis

The other established cumulative form is the Arrhenius damage integral, from Henriques
and Moritz's burn work:

> "∂Ω/∂t = A exp(−ΔE/RT)" — "Ω is the damage integral, A is the frequency factor,
> ΔE is activation energy, R is the universal gas constant, and T is transient
> temperature."
> "It is reported that an Ω value of 0.53, 1.0 and 10⁴ corresponds to first, second and
> third degree burns, respectively"

*Source, opened and read: Hanglin Ye and Suvranu De, "Thermal injury of skin and
subcutaneous tissues: A review of experimental approaches and numerical models" (2016),
PMC5459687. `https://pmc.ncbi.nlm.nih.gov/articles/PMC5459687/`. The review attributes
the formulation to Henriques but does not state units for Ω or A, and the Henriques
originals were **not** opened.*

The same mathematical form is what charring-ablator response models use for resin
decomposition. The TFAWS course above describes the pyrolysis source term as

> "Determined experimentally and modeled with an Arrhenius fit"

and the material-characterisation procedure as

> "Conduct Thermogravimetric Analysis (TGA experiments) in inert gas... Data fits provide
> decomposition kinetic constants for the Arrhenius equation."

So for a *real* charring TPS, the cumulative in-depth exposure metric already exists and
is physically grounded: it is the decomposition state, integrated by the material itself.
TPI is only interesting for a **non-decomposing** stack — which is exactly what this
project models (ASSUMPTIONS A-TRAJ-3, no ablation) and exactly what the 3-D-printed M8
coupon will be.

---

## 3. Does a depth-and-time double integral already have a name?

A delegated literature search, run with instructions to report failure honestly, ran
targeted queries for a named metric that integrates temperature exceedance over **both**
depth and time inside a TPS, and **found none**. The NASA TPS-margin literature it
surfaced treats bondline temperature, in-depth thermocouple response and recession as
separate design responses rather than fusing them.

Stated as carefully as the evidence allows: **no named prior metric of this exact shape
was found in the sources searched.** That is a negative search result, not a proof of
absence. Paywalled AIAA and Elsevier content, industry-internal TPS design standards and
any export-controlled material were not reachable, and none of this is a claim of
novelty. §44 forbids claiming TPI as a new aerospace standard, and this document makes
no such claim.

### Sources not opened by the author of this document

The following were reported by the delegated search with URLs, and are recorded as
**leads, not citations**. Nothing in this document rests on them. Anyone using them must
open them first: Mars 2020 TPS sizing (NTRS 20220006688) · Beck, "Ablative Thermal
Protection Systems Fundamentals", TFAWS 2017 (NTRS 20170011453) · Kolodziej, "Strategies
and Approaches to TPS Design", RTO-EN-AVT-116-13 · Rickman et al., "Ablative TPS Margin
Study" (NTRS 20200005815) · "Ablative Thermal Response Analysis Using the Finite Element
Method" (NTRS 20090007598) · Liu & Chen, ICCM2024, on CEM43 for pulse-heated tissue.

---

## 4. Weighting families

All are defined on `x ∈ [0, L]` and normalised to unit depth-average before use.

| Family | `w(x)` before normalisation | What it assumes about the failure mode |
|---|---|---|
| `uniform` | 1 | Every millimetre of TPS matters equally. The null hypothesis. |
| `linear_depth` | `x / L` | Surface exposure is not the point; discount it smoothly. |
| `exponential_depth` | `exp(decay · (x/L − 1))` | Interior strongly favoured. `decay → 0` recovers `uniform`, so it is a genuine one-parameter generalisation, not a separate model. |
| `bondline_gaussian` | `exp(−½((x − x_c)/σ)²)`, `x_c = L` | The failure is one adhesive at one depth. Closest in spirit to the accepted bondline criterion in §2.2. |

---

## 5. The prediction: how this is expected to fail

Written before the run.

The integrand is `max(T − T_ref, 0)`. In an entry TPS the surface reaches ~2000–3000 K
while a plausible `T_ref` is 350–500 K, so the exceedance near the surface is **an order
of magnitude larger** than anywhere else in the stack, and it persists for the whole
entry. The depth integral is therefore expected to be dominated by the outer millimetre
or two, no matter what happens at the bondline.

The weighting is the only defence against that, and normalisation caps how strong the
defence can be: a weight with unit depth-average cannot suppress the surface by more than
a bounded factor without starving the rest of the domain.

If that is what happens, TPI will behave like a slightly smeared version of
surface-exposure-integrated-over-time, which is itself close to integrated heat load —
and integrated heat load is already what drives bondline temperature in this stack (M1's
figure `M1_integrated_vs_bondline`). The consequence would be a near-perfect rank
correlation between TPI and peak bondline temperature, and no new information.

**The falsifiable, pre-declared test** is therefore: regress TPI's *ranks* on the ranks
of (peak bondline temperature, integrated heat load) over the 2-D M1b grid. If the R²
exceeds 0.98, TPI's ordering of designs is reconstructible from metrics the project
already reports, and §44's own instruction applies — *"discard TPI if it adds no
interpretable information"*.

Two diagnostics are recorded alongside the verdict so this prediction can be checked
rather than assumed:

1. the depth at which the unweighted time-integrated exceedance peaks, for every design;
2. the residual of the rank regression, plotted — structure there would be TPI's
   independent content.

**Where TPI could still be the right metric, and this study would not know.** A stack
with an interior bondline behind a second insulator, a temperature-dependent
conductivity, or a charring layer that decouples surface temperature from in-depth
temperature could break the correlation. That is a prediction about future work, not a
defence of the metric, and it is not evidence for anything today.

---

## 6. Result, and how §5 scored as a prediction

**The section above is left exactly as it was written before the run.** It is a
pre-registration; editing it after seeing the answer would destroy the only thing it was
for. What follows is the addendum.

The verdict is **DISCARD** (`reports/milestones/TPI_study.md`): over the 140-design M1b
grid, TPI's ranking is 99.94% reconstructible from peak bondline temperature and
integrated heat load, Spearman ρ against peak bondline temperature alone is +0.9992, and
a TPI-minimising optimiser picks the same design as a bondline-minimising one. All 16
declared combinations of T_ref and weighting fail the pre-declared criterion together.

**§5 predicted the outcome but got the mechanism half wrong, and the wrong half is the
interesting one.**

- *Right:* the unweighted time-integrated exceedance peaks at the surface — in the
  shallowest cell of the mesh, 0.06 mm deep, for every one of the 140 designs.
- *Wrong:* it does not **dominate**. The outermost 20% of the TPS depth carries only
  27.6–40.6% of the integral, against the 20% a uniform profile would give. The profile
  declines smoothly and by a factor of only a few across 15 mm. It is not a surface
  spike, and the prediction that "the depth integral is expected to be dominated by the
  outer millimetre or two" is not supported.

The real mechanism is **shape invariance**. Normalised to unit length, the exceedance
profiles of all 140 designs have a minimum pairwise cosine similarity of 0.9366 (mean
0.9891): every design produces very nearly the *same* depth profile, scaled. A weighted
integral of a profile whose shape does not change between designs is that scale factor
and nothing else, which is why no weighting family can rescue the metric — there is no
dimension of variation for a weighting to select.

That distinction matters for what happens next. Had §5's mechanism been right, a
sufficiently aggressive depth weighting would have been worth trying. Because the
profiles are shape-invariant on this stack, the thing to change is the *stack* — an
interior bondline behind a second insulator, a temperature-dependent conductivity, a
charring layer — not the weighting. That is a prediction about future work, not a defence
of the metric, and nothing in the current evidence supports it.

Recorded in `docs/negative_results.md` NR-10.
