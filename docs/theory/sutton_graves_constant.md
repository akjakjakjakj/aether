# Where k = 1.7415×10⁻⁴ comes from — a re-derivation from NASA TR R-376

**Status of this document.** This closes the open item "re-derive the Sutton–Graves
constant from TR R-376" (`ROADMAP.md`, `VALIDATION_MATRIX.md` G2, `ASSUMPTIONS.md`
A-HEAT-1). Written 2026-09-20.

**Result in one line.** Starting from the primary report's own coefficient and its own
declared units, the project's SI form reduces to **k = 1.74826×10⁻⁴**, which is **+0.39%**
relative to the 1.7415×10⁻⁴ the code uses — well inside the primary's own stated
correlation error for air (average 3.3%, maximum 9.8%). **The constant in the code was
not changed**, and the sections below explain why the derivation cannot justify changing
it in either direction.

---

## 1. What the primary document actually contains

Sutton, K. & Graves, R. A., Jr., *A General Stagnation-Point Convective-Heating Equation
for Arbitrary Gas Mixtures*, NASA TR R-376, NASA Langley, November 1971
(NTRS 19720003329). The PDF was downloaded and read; every fact below was checked
against 300 dpi renders of the printed pages, not against the PDF's unreliable OCR text
layer.

**The report does NOT contain the equation this project uses.** A full-text search for
`1.74`, `17415` and for any freestream-velocity form of the heating equation returns
nothing. TR R-376 is written entirely in terms of stagnation pressure and enthalpy
difference. Its defining equation, printed p. 13 as eq. (33), is

$$K \;=\; \frac{\dot q_w \sqrt{R/p_s}}{h_s - h_w}
\qquad\Longleftrightarrow\qquad
\dot q_w \;=\; K \sqrt{\frac{p_s}{R}}\,\bigl(h_s - h_w\bigr)$$

The report also gives two closed forms for $K$ itself (pp. 16–17):

$$K = \frac{0.0885}{N_{Pr,w}^{0.6}} \Bigl(\textstyle\sum_i \frac{c_{O,i}}{M_{O,i}\gamma_{O,i}}\Bigr)^{-1/2}
\quad\text{(eq. 41)};\qquad
K = 0.1106 \Bigl(\textstyle\sum_i \frac{c_{O,i}}{M_{O,i}\gamma_{O,i}}\Bigr)^{-1/2}
\quad\text{(eq. 42, for } N_{Pr,w}=0.69\text{)}$$

**Units, quoted verbatim from the report's SYMBOLS list (pp. 2–3).** This is the
load-bearing part of the whole derivation and it is where most secondary restatements
go wrong:

| Symbol | Report's own words | Unit used below |
|---|---|---|
| $\dot q$ | "convective heating rate, MW/m²" | MW·m⁻² |
| $K$ | "heat-transfer coefficient defined by equation (33), kg/s-m^3/2-atm^1/2" | kg·s⁻¹·m⁻³ᐟ²·atm⁻¹ᐟ² |
| $p$ | "pressure, atm (1 atmosphere equals 101.325 kN/m²)" | atm |
| $R$ | "equivalent body radius, m" | m |
| $h$ | "enthalpy, MJ/kg" | MJ·kg⁻¹ |

Note in particular that $\dot q$ is in **MW/m²**, not W/cm², and $h$ is in **MJ/kg**, not
J/kg. Several widely-circulated restatements of "Sutton–Graves" imply W/cm²; that reading
is off by a factor of 100 against the document.

**The air coefficient.** Table II ("Heat-Transfer Coefficients From Correlation of Present
Computer Results", p. 39), row `0.2320 O₂ – 0.7680 N₂ (air)`:

$$\boxed{K_{\text{air}} = 0.1113\ \mathrm{kg\,s^{-1}\,m^{-3/2}\,atm^{-1/2}}}$$

with **average error 3.3% and maximum error 9.8%** against the chemical-equilibrium
boundary-layer computer solutions it was fitted to.

**Domain of the fit**, quoted from the Summary and Introduction (pp. 1–2): stagnation
enthalpies 2.3–116.2 MJ/kg, stagnation pressures 0.001–100 atm, wall temperatures 300 K
and 1111 K (two discrete values, not a range), wall Prandtl number 0.67–0.71 for the
planetary-entry gas mixtures.

### 1.1 Dimensional self-check on K

Before using $K$, confirm the report's stated units are the ones eq. (33) actually
implies:

$$[K] = \frac{[\dot q]\,[R]^{1/2}}{[p]^{1/2}\,[h]}
= \frac{\mathrm{MW\,m^{-2}} \cdot \mathrm{m^{1/2}}}{\mathrm{atm^{1/2}} \cdot \mathrm{MJ\,kg^{-1}}}
= \frac{\mathrm{MJ\,s^{-1}\,m^{-3/2}}}{\mathrm{atm^{1/2}\,MJ\,kg^{-1}}}
= \mathrm{kg\,s^{-1}\,m^{-3/2}\,atm^{-1/2}}$$

which is exactly the report's printed "kg/s-m^3/2-atm^1/2". The unit system is
self-consistent, so the conversion below rests on a verified reading and not on an
inference about what the authors meant.

---

## 2. The three substitutions that turn eq. (33) into the project's form

The project uses

$$\dot q'' = k \sqrt{\frac{\rho_\infty}{R_n}}\, V_\infty^3
\qquad [\mathrm{W\,m^{-2}}],\quad \rho\ [\mathrm{kg\,m^{-3}}],\ R_n\ [\mathrm{m}],\ V\ [\mathrm{m\,s^{-1}}]$$

Getting from eq. (33) to this requires three physical substitutions, **none of which is in
TR R-376**. They are the "later derived simplification" the sourcing report identifies;
the chain is stated (not derived) in NASA TFAWS 2012 training material and in
Carroll & Brandis, AIAA Aviation 2022 (both 🟡 T2).

**(S1) Stagnation pressure from freestream momentum — Newtonian limit.**
Define the stagnation-pressure coefficient $C_{p,\max} = (p_s - p_\infty)/(\tfrac12\rho V^2)$.
In the Newtonian limit $C_{p,\max} \to 2$, and at hypersonic speed $p_\infty \ll p_s$, so

$$p_s \approx \rho_\infty V_\infty^2 \qquad [\mathrm{Pa}]$$

**(S2) Total enthalpy from kinetic energy.**
$h_s = h_\infty + \tfrac12 V_\infty^2$; dropping the freestream static enthalpy,

$$h_s \approx \tfrac12 V_\infty^2 \qquad [\mathrm{J\,kg^{-1}}]$$

**(S3) Cold wall.** $h_w \ll h_s$, so $h_s - h_w \approx h_s$.

Substituting all three into eq. (33), with every quantity in the report's units:

$$\dot q_w\,[\mathrm{MW/m^2}] = K \sqrt{\frac{p_s[\mathrm{atm}]}{R[\mathrm{m}]}} \cdot \frac{V^2}{2}\,[\mathrm{MJ/kg}]$$

---

## 3. The unit conversion, carried explicitly

Let SI quantities carry no bracket. The report's variables relate to SI by

$$\dot q[\mathrm{MW/m^2}] = \frac{\dot q''}{10^6},\qquad
p[\mathrm{atm}] = \frac{p_s^{\mathrm{SI}}}{101325},\qquad
R[\mathrm{m}] = R_n,\qquad
h[\mathrm{MJ/kg}] = \frac{h^{\mathrm{SI}}}{10^6}$$

Substituting into eq. (33):

$$\frac{\dot q''}{10^6} = K \sqrt{\frac{p_s^{\mathrm{SI}}}{101325\,R_n}}\cdot\frac{h^{\mathrm{SI}}_s}{10^6}$$

$$\dot q'' = \frac{K}{\sqrt{101325}} \sqrt{\frac{p_s^{\mathrm{SI}}}{R_n}}\; h_s^{\mathrm{SI}}
\qquad [\mathrm{W\,m^{-2}}]$$

The two factors of $10^6$ cancel exactly — a useful check, because it means the result is
insensitive to whether one reads the report's $\dot q$/$h$ as MW/MJ or as W/J, provided
*both* are read the same way. What does **not** cancel, and what every mis-derivation gets
wrong, is the single $\sqrt{101325}$ from the atmosphere unit on pressure.

Now apply (S1) and (S2)–(S3):

$$\dot q'' = \frac{K}{\sqrt{101325}} \sqrt{\frac{\rho_\infty V_\infty^2}{R_n}}\cdot\frac{V_\infty^2}{2}
= \frac{K}{2\sqrt{101325}} \sqrt{\frac{\rho_\infty}{R_n}}\, V_\infty^3$$

which is exactly the project's form, with

$$\boxed{\;k = \frac{K_{\text{air}}}{2\sqrt{101325}} = \frac{0.1113}{2 \times 318.3159} = 1.74826\times10^{-4}\;}$$

**Units of $k$:** $\mathrm{kg^{1/2}\,m^{-1}}$ — check: $\sqrt{\rho/R_n}\,V^3$ carries
$\mathrm{kg^{1/2}\,m^{-2}} \cdot \mathrm{m^3\,s^{-3}} = \mathrm{kg^{1/2}\,m\,s^{-3}}$, and
$\mathrm{W\,m^{-2}} = \mathrm{kg\,s^{-3}}$, so $[k]=\mathrm{kg^{1/2}\,m^{-1}}$, matching
the docstring in `src/aether/heating/sutton_graves.py`.

---

## 4. What the derivation yields versus what the code uses

| Quantity | Value | Relative to the code |
|---|---|---|
| Derived here from the primary, substitutions S1–S3 | 1.74826×10⁻⁴ | **+0.39%** |
| In `src/aether/heating/sutton_graves.py` | 1.74150×10⁻⁴ | — |
| $K$ implied by the code's constant, back-substituted | 0.110869 | vs. the primary's 0.1113 |

**The exact digits 1.7415 could not be reconstructed from the primary.** Two candidate
explanations were tested and both fail:

- using eq. (42)'s leading coefficient 0.1106 in place of the fitted $K_{\text{air}}$
  gives 1.73728×10⁻⁴ (−0.24% against the code, still not a match);
- evaluating eq. (41) at $N_{Pr,w} = 0.71$ instead of 0.69 gives 1.71805×10⁻⁴ (−1.35%).

So the provenance of the fifth significant figure in the literature's 1.7415×10⁻⁴ remains
**unsourced** (sourcing report, open item 1). What *is* now sourced is the constant's
origin, its form, its units and its magnitude to better than half a percent.

---

## 5. Why 0.39% is not evidence that the code is wrong

The substitution chain S1–S3 is itself accurate only to a few percent, and its errors are
**larger than the discrepancy it is being used to assess**. Quantifying each, at the
project's baseline condition ($V = 7400\ \mathrm{m\,s^{-1}}$, $T_\infty = 220$ K,
$T_w = 300$ K, $\gamma = 1.4$):

**S1 is the crudest step.** The Newtonian $C_{p,\max}=2$ overstates the real stagnation
pressure. The exact Rayleigh-pitot value for a calorically perfect gas as $M\to\infty$ is

$$C_{p,\max} = \frac{1}{\tfrac12\gamma}\left[\left(\frac{(\gamma+1)^2}{4\gamma}\right)^{\frac{\gamma}{\gamma-1}}\frac{2\gamma}{\gamma+1}\right] = 1.83937$$

so $p_s = 0.9197\,\rho V^2$, and since $k \propto \sqrt{p_s}$ this scales $k$ by
$\sqrt{1.83937/2} = 0.95900$, i.e. **−4.10%**.

**S2 and S3 partially cancel.** Restoring both the freestream static enthalpy
($h_\infty = c_p T_\infty = 2.21\times10^5$ J/kg) and the wall enthalpy
($h_w = c_p T_w = 3.01\times10^5$ J/kg) multiplies $k$ by
$1 + 2(h_\infty - h_w)/V^2 = 0.99706$, i.e. **−0.29%** net. Individually they are +0.81%
and −1.10%; at a hot wall (the primary's other tabulated case, 1111 K) the wall term alone
is −4.1%, and it grows as $V$ falls.

Applying both corrections gives $k = 1.6717\times10^{-4}$, which is **−4.01%** against the
code's value — a larger disagreement, in the opposite direction, than the crude chain's
+0.39%.

**And the primary's own fit carries 3.3% average / 9.8% maximum error for air** before any
of this. The honest reading:

> The derivation confirms the equation's form, its units and the magnitude of its constant.
> It cannot resolve the constant to better than about ±4%, because the substitutions needed
> to reach the V³ form are individually worse than that and partially cancel. The code's
> 1.7415×10⁻⁴ sits between the crude-chain value (+0.39%) and the corrected-chain value
> (−4.01%), and no result in this project is sensitive at that level in a way that would be
> decidable by this argument.

**Decision: `SUTTON_GRAVES_K_EARTH` is unchanged at 1.7415×10⁻⁴.** Changing it to 1.74826
or 1.6717 would move every heat-flux number in the repository for a reason the evidence
does not support. Recorded in `docs/negative_results.md` NR-12.

---

## 6. What this does and does not validate

**Validated (gate G2 → PASS).** The constant's provenance and magnitude, against an
independent re-derivation from a ✅ T1 primary-source coefficient with primary-source
units. Declared tolerance: the primary's own average correlation error for air, 3.3%.
Measured: 0.39%. Pinned by
`tests/test_heating.py::test_constant_matches_rederivation_from_tr_r376`.

**Not validated, and out of scope rather than outstanding.** Everything about the *model
form*, which is carried as assumptions A-HEAT-2 … A-HEAT-4, not as validation debt:

- **Catalycity.** TR R-376's basis is an equilibrium boundary layer, characterised by
  secondary sources as equivalent to a fully catalytic wall; catalytic heat flux is
  reported to be roughly 2× non-catalytic at comparable conditions (🟡 T2, ONERA/CNES 2019).
  This is by far the largest unquantified model-form uncertainty in the heating chain and
  it dwarfs the 0.39% above.
- **Wall temperature.** The V³ form assumes a cold wall; the surface in this project
  reaches ~2400 K. The bias is conservative (over-predicts flux) and is stated in A-HEAT-3.
- **Radiation.** "Radiative heating was neglected in the present study" — verbatim, primary
  source, consistent with A-HEAT-2.
- **Domain checking.** The code does not currently reject inputs outside the primary's
  fitted domain (2.3–116.2 MJ/kg, 0.001–100 atm). The project's baseline sits inside it
  ($\tfrac12V^2 = 27.4$ MJ/kg at entry), but nothing enforces that.
- **Tauber's review papers** (NASA TP-2914, 1989; Tauber & Sutton 1991), the standard
  critical assessment of this correlation class, remain unread (❌ T3, sourcing report
  open item 2).

---

## Sources

- ✅ **T1** Sutton, K. & Graves, R. A., Jr., *A General Stagnation-Point Convective-Heating
  Equation for Arbitrary Gas Mixtures*, NASA TR R-376, November 1971. NTRS 19720003329,
  <https://ntrs.nasa.gov/citations/19720003329>. Eq. (33) p. 13; eqs. (41)–(42) pp. 16–17;
  SYMBOLS list pp. 2–3; Table II p. 39; domain statement pp. 1–2. Read from 300 dpi page
  renders.
- 🟡 **T2** NASA TFAWS 2012, *Aerothermodynamics Course*, Lecture 1 — the earliest located
  statement of the V³ form with k = 1.7415×10⁻⁴.
- 🟡 **T2** Carroll, B. & Brandis, A., "Stagnation Point Convective Heating Correlations for
  Entry into H₂/He Atmospheres", AIAA Aviation 2022, NTRS 20220018610 — states the
  three-substitution chain.
- 🟡 **T2** ONERA/CNES, "Noncatalytic and Finite Catalytic Heating Models for Atmospheric
  Re-entry Codes", 1st Int'l Orbital Debris Conf., 2019 — catalytic/non-catalytic ratio.
- Project sourcing pass: `docs/validation/sourcing_report.md` §1.
