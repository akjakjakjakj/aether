# Sourcing report — ASSUMPTIONS.md open items

Purpose: find primary or clearly reputable sources for the seven values flagged as
unsourced placeholders in `ASSUMPTIONS.md`, `VALIDATION_MATRIX.md`, and the "Immediate
open items" line of `ROADMAP.md`. Tiering:

- **✅ T1** — verified directly in the primary document (opened and read, not just cited by a secondary source).
- **🟡 T2** — from a reputable secondary source only (NASA training material, a textbook citation, a paywalled paper verified only at abstract/snippet level, etc.).
- **❌ T3** — could not source. Reported as a gap, not filled with an unsourced number.

Every number below was retrieved by a research pass against NASA NTRS, NACA reports,
AIAA papers, and named textbooks — none is quoted from model memory. Where a source
disagreed with another, or with the project's own placeholder, that disagreement is
stated rather than resolved by picking a side.

Research date: 2026-09-20.

---

## 1. Sutton-Graves stagnation-point heating constant (A-HEAT-1, G2)

**Project placeholder:** k = 1.7415×10⁻⁴ SI, in `q = k·√(ρ/Rn)·V³`.

**Finding: the primary 1971 report does not contain this equation form or this constant.** NASA-TR-R-376 (Sutton, K. &amp; Graves, R. A., Jr., *A General Stagnation-Point Convective-Heating Equation for Arbitrary Gas Mixtures*, NASA Langley, 1 Nov 1971; NTRS 19720003329, https://ntrs.nasa.gov/citations/19720003329) was located and its full text opened and grepped. It derives a heat-transfer coefficient **K** (not k) via `q = K·√(p_stag/R)·(h_e−h_w)`, fit to chemical-equilibrium boundary-layer computer solutions across 9 base gases + 22 mixtures, for air specifically (0.2320 O₂ – 0.7680 N₂ by mass): **K(air) = 0.1113** (units inferred as kg·s⁻¹·m^1.5·atm^-0.5 from context, OCR-uncertain), average correlation error 3.3%, max 9.8% (Table II, p. 38). A full-text search of the document for "1.74", "17415", and "1.7623" returned nothing.

The popular `q = k·√(ρ/Rn)·V³` SI form is a **later, derived simplification** of the actual Sutton-Graves equation, obtained (per a 2022 NASA Ames/AIAA paper, below) by substituting three further approximations: `h_e ∝ h_∞ ≈ V²/2`, a **cold-wall assumption** `h_w ≪ h_∞`, and `p_stag ∝ ρV²`.

| Value | Form | Source | Tier |
|---|---|---|---|
| K(air) = 0.1113 | `q = K·√(p_stag/R)·(h_e−h_w)` | NASA-TR-R-376, Table II, p. 38 | ✅ T1 |
| k = 1.7415×10⁻⁴ (Earth, SI) | `q̇s = k·√(ρ/Rn)·V³` | NASA TFAWS 2012 *Aerothermodynamics Course*, Lecture 1, slides 17–18, 29 (worked example reproduces the constant: q=1.7415e-4·√(3.1459e-4/1)·3535³=13.6 W/cm² for a Shuttle-like case). https://tfaws.nasa.gov/TFAWS12/Proceedings/Aerothermodynamics%20Course.pdf | 🟡 T2 (NASA-authored training material, not peer-reviewed; cites TR-R-376 as origin but the constant itself is not verified inside TR-R-376) |
| k = 1.74153×10⁻⁴ | same form | Wikipedia, "Planar reentry equations" (correctly attributes to TR-R-376) | 🟡 T2, corroborating only |
| k = 1.7623×10⁻⁴ | — | **No source found for this value anywhere**, despite targeted searches. Possible typo/mistranscription of 1.7415, or a value computed at a different wall Prandtl number (the primary report's K is derived for N_Pr,w = 0.69 specifically — a source using 0.71 could legitimately differ). | ❌ T3 — do not use without locating a source |

**Validity conditions (as stated in the primary source or a reputable secondary):**
- Fit domain: stagnation enthalpy 2.3–116.2 MJ/kg, pressure 0.001–100 atm, wall temperature 300 K and 1111 K (✅ T1, primary). No velocity range is stated directly; converting the enthalpy bound via h≈V²/2 gives ~15.2 km/s at the top of the envelope — **this conversion is the researcher's own inference, not a number in any source**.
- **"Radiative heating was neglected in the present study"** — verbatim, primary source (✅ T1). Consistent with the project's own A-HEAT-2.
- Cold-wall / fully-catalytic: the primary report itself uses discrete wall temperatures (300 K/1111 K), not literally a cold-wall limit; the popular V³-form derivation explicitly assumes a cold wall (🟡 T2, Carroll &amp; Brandis, NASA Ames, "Stagnation Point Convective Heating Correlations for Entry into H₂/He Atmospheres," AIAA Aviation 2022, NTRS 20220018610). The equilibrium-boundary-layer basis is characterized by secondary sources as equivalent to a fully catalytic wall (🟡 T2), with catalytic-wall heat flux reported roughly 2× non-catalytic for the same conditions (ONERA/CNES, "Noncatalytic and Finite Catalytic Heating Models for Atmospheric Re-entry Codes," 1st Int'l Orbital Debris Conf. 2019, https://www.hou.usra.edu/meetings/orbitaldebris2019/orbital2019paper/pdf/6112.pdf).
- Tauber's review papers (NASA TP-2914, 1989; Tauber &amp; Sutton 1991) are the standard critical assessment of this correlation class and are cited by the AIAA 2022 paper but were **not opened** in this pass — flagged as a real gap (❌ T3).

  > **Note, 2026-09-21.** `docs/engineering_notebook/2026-09-20_effective_nose_radius.md`
  > §Action item 1 records NASA TP-2914 as one of four primaries "obtained and read." This
  > report says the opposite. This project cannot tell which record is correct from the
  > files alone — the contradiction is left standing rather than silently resolved in
  > either direction. No claim in the paper rests on TP-2914
  > (`reports/final/AETHER_paper.md`). The student should open the document and settle
  > which record was wrong.

**Recommendation for ASSUMPTIONS.md:** downgrade A-HEAT-1's citation. "NASA TR R-376" is the correct origin of the underlying physics but the project's exact numeric constant and equation form should be attributed to a **derived simplification** (best available cite: NASA TFAWS 2012 training material), not read as verbatim content of TR-R-376. If precision matters, the next step is to algebraically re-derive k from K(air)=0.1113 via the three-assumption chain and check it lands on 1.7415×10⁻⁴ — not yet done.

---

## 2. Crew deceleration limits (A-LIM-1)

**Project placeholder:** "deceleration limit 12 g," unsourced, in `configs/baseline.yaml`.

**Finding: no document states a flat "12 g" limit.** NASA-STD-3001's actual limit is a **duration-and-conditioning-dependent curve**, not a scalar, and 12 g is not a clean point on any of its curves.

### NASA-STD-3001 Vol 2 (Rev F), Table 6.5-1 — "Ax Sustained Translational Acceleration Limits (Seated)" (✅ T1, opened directly)

| Crew state | Duration | +Ax (chest-to-back) upper limit |
|---|---|---|
| Emergency conditions | 0.5 s / 120 s / 300 s / 1200 s | 38.0 g / 8.8 g / 7.5 g / 5.0 g |
| Non-deconditioned | 0.5 s / 5 s / 300 s | 19.0 g / 16.0 g / 7.5 g |
| **Deconditioned (post-microgravity — the entry-relevant case)** | 0.5 s / 10 s / 30 s / 50 s / 90 s / 120 s / 150 s→∞ | 14.0 g / 10.0 g / 8.0 g / 6.3 g / 5.0 g / 4.3 g / 4.0 g |

A returning crew is medically deconditioned, so the third row is the applicable curve. **12 g exceeds this curve for any duration beyond ~1–2 seconds.** It sits inside the emergency-conditions envelope for durations under ~2 minutes.

### OCHMO-TB-024 Rev D Technical Brief (✅ T1, 2025-03-13, NASA official)
Descriptive table (sourced to Human Integration Design Handbook Table 6.5-3) places 9–12 g as "increased severity of symptoms; severe breathing difficulty, increased chest pain, marked fatigue, loss of peripheral vision, diminution of central acuity, lacrimation" — significant distress, not incapacitation, but a real physiological cost.

### NASA TM-104753 (1992), Vasantha Kumar &amp; Norfleet, "Issues on Human Acceleration Tolerance After Long-Duration Space Flights" (✅ T1, NTRS 19930020462), Table 3, p. 24

| Category | Normal conditioning | Deconditioned (post-hypokinesia) |
|---|---|---|
| Plateau | 16 G / 5 s; 20 G / 0.2 s | 12 G / 5 s; 15 G / 0.2 s |
| Sustained | 8 G / 5 min | 8 G / &lt;2.5 min |

(The "8 G/5 min" sustained figure traces to Bondurant et al. 1958, USAF Armed Forces J. 9:1093 — cited by the TM, not independently retrieved — 🟡 T2 for that sub-citation.)

### Published peak-g from real crewed entries (same TM, §IV.B, pp. 9–10, citing Harding 1989 "Survival in Space" for Soviet figures — ✅ T1 for the TM's own text)

| Program | Peak +Gx, re-entry |
|---|---|
| Mercury | 7.6–11.1 g |
| Gemini | 4.3–7.7 g |
| Apollo | 3.3–6.8 g (higher on lunar-return trajectories) |
| Vostok | 8–10 g |
| Soyuz (nominal) | 3–4 g |

**Soyuz TMA-11, 19 Apr 2008 (ballistic-contingency descent):** 🟡 T2, IEEE Spectrum reporting on an internal NASA document ("ISS Ballistic Entry Outbrief," G. Kafka), not independently opened. Reported 8–9 g for the ballistic descent, with "some reports" of 11 g for a few seconds and astronaut Peggy Whitson recalling 8.4 g on the onboard meter. The article is internally inconsistent about the nominal (lifting) descent figure (3–4 g in body text vs. 4–5 g in a caption) — flagged, not resolved.

**Note on a rejected number:** a WebSearch AI-summary claimed Mercury-Atlas 6 hit "74 g" on re-entry, attributed to the Friendship 7 mission report. This is inconsistent with every primary/secondary source found (Mercury re-entry consistently 7.6–11.1 g) and was **not used** — treated as a likely AI-summary fabrication.

**Read on the placeholder:** 12 g is plausible as a **contingency/off-nominal ceiling** (it sits within NASA-STD-3001's emergency envelope and matches TM-104753's deconditioned 5-second plateau almost exactly) but is **not defensible as a nominal design limit**, and it exceeds every published nominal crewed-entry peak-g on record. Recommend replacing the flat number with a duration-tagged value from Table 6.5-1 above, keyed to expected entry-pulse duration, and stating explicitly whether the design targets nominal or emergency conditions.

**Sources:**
- ✅ T1 NASA-STD-3001 Vol 2 Rev F, Table 6.5-1, §6.5.1 [V2 6064] — https://www.nasa.gov (downloaded PDF, standards.nasa.gov origin)
- ✅ T1 OCHMO-TB-024 Rev D, 2025-03-13
- ✅ T1 NASA TM-104753 (1992), NTRS 19930020462
- ✅ T1 Eiband, A. M., "Human Tolerance to Rapidly Applied Accelerations," NASA Memo 5-19-59E (1959), NTRS 19980228043 — confirmed this is a **transient/impact** chart (sub-second, trapezoidal-pulse), not the sustained-plateau source it's sometimes cited as.
- ✅ T1 (context) / 🟡 T2 (exact curve digits, OCR-unreadable scan) NASA Bioastronautics Data Book, NASA SP-3006 (2nd ed., 1973), NTRS 19730006364, Fig. 4-24 (sustained tolerance) and Ch. 6 Table 6-2 (impact tolerance, distinct from sustained).
- 🟡 T2 IEEE Spectrum, "Internal NASA Documents Give Clues to Scary Soyuz Return Flight," 7 May 2008.

---

## 3. Bondline temperature allowables (A-LIM-1)

**Project placeholder:** "bondline allowable 450 K" (~177°C), unsourced.

**Finding: 450 K matches the Space Shuttle Orbiter's aluminum-airframe design limit specifically — not a generic TPS-bondline constant.** Three different flown vehicles give three different, all independently-sourced, allowables, each tied to a different structural material:

| Vehicle | Value stated in source | °C / K | Material system | Tier | Source |
|---|---|---|---|---|---|
| Apollo CM (Block II, flown config) | 600°F, "at any time before main parachute deployment" | 315.6°C / 588.7 K | Avcoat 5026-39 ablator / **stainless-steel honeycomb**, bonded with HT-424 tape adhesive | ✅ T1 | NASA TN D-7564, *Apollo Experience Report — Thermal Protection Subsystem*, Pavlosky &amp; St. Leger, JSC, Jan 1974, p. 2. NTRS 19740007423 |
| Apollo CM (Block I, separate aluminum pressure vessel limit) | 200°F | 366.5 K | Aluminum-honeycomb pressure-vessel structure (a stricter, separate limit from the ablator/stainless interface above) | ✅ T1 | Same, p. 2 |
| **Space Shuttle Orbiter** | "Design temperature limit of 350°F (177°C)" for the aluminum-alloy primary structure; RTV-560 adhesive itself is rated to 500°F (260°C) | 176.7°C / **449.8 K** — matches the project's placeholder | Fused-silica tile + Nomex SIP + RTV-560 silicone adhesive on aluminum airframe skin | ✅ T1 (airframe limit) / 🟡 T2 (exact linkage of "350°F" specifically to the RTV-560 bondline, as opposed to the airframe generally) | NASA CR-159900, *Adhesives for Bonding RSI Tile to Gr/Pl Structure...*, Smith, Hamermesh &amp; Hogenson (Rockwell Intl./NASA Langley, NAS1-15152), Apr 1979, p. 1. NTRS 19790012947 |
| Orion (MPCV), EFT-1 heat shield | "Allowable temperature of 500°F... 99.95%, or 3.3-sigma, likelihood" of the bondline-temperature distribution; nominal bondline ~238°F (3σ-high ~246°F) | 260°C / 533.2 K (allowable); ~114°C / 387 K (nominal) | Avcoat (block-bonded, "HC/G") on **composite skin over titanium skeleton** — not aluminum | ✅ T1 | Vander Kam &amp; Gage, *Estimating Orion Heat Shield Failure Due to Ablator Cracking During the EFT-1 Mission*, AIAA/JSR, DOI 10.2514/1.A35003, NTRS 20160007549, pp. 9–10 |

**The allowable is set by the substrate material's own temperature limit, not by a universal "bondline" constant** — stainless steel (Apollo, 589 K), aluminum (Shuttle, 450 K), composite-over-titanium (Orion, 533 K). AETHER's 450 K placeholder is a real, precedented number **if and only if the project's structural substrate is aluminum-like** (matches Shuttle exactly); it would understate Apollo's stainless-steel allowable by ~140 K and Orion's by ~83 K.

**What could not be verified:** a primary NASA document stating in one sentence "the RTV-560/tile bondline limit is 350°F" — CR-159900 states it as the aluminum airframe's design limit, from which the tile-bond system's operating point follows; the often-cited "Shuttle Tile Story" paper (Cooper &amp; Holloway, 1981, NTRS 19810036013) has no full text on NTRS and was not verified.

**Sources:**
- ✅ T1 NASA TN D-7564, NTRS 19740007423, https://ntrs.nasa.gov/citations/19740007423
- ✅ T1 / 🟡 T2 NASA CR-159900, NTRS 19790012947, https://ntrs.nasa.gov/citations/19790012947
- ✅ T1 Vander Kam &amp; Gage, NTRS 20160007549, https://ntrs.nasa.gov/citations/20160007549
- 🟡 T2 Day, D. A., "Shuttle Thermal Protection System (TPS)," U.S. Centennial of Flight Commission (corroborates 350°F/175°C aluminum limit; not independently opened as a NASA primary)
- ❌ T3 Cooper &amp; Holloway, "The Shuttle Tile Story," *Astronautics and Aeronautics* 19, Jan 1981, NTRS 19810036013 — no full text available, not verified

---

## 4. Base drag / afterbody pressure for blunt capsules (A-CFD-5)

**Project's own internal data point** (already in ASSUMPTIONS.md): sphere measured total C_D 0.940–0.944 at Mach 3.2–5.9 (Bailey &amp; Hiatt, Re≈10⁴) against Clark's forebody-only pressure drag at the same Mach numbers, 0.855–0.888 → base+friction ≈ 5.5–9.4% of total, shrinking with Mach.

**Corroborating/extending sources found:**

| Source | What it gives | Tier |
|---|---|---|
| Chapman, D. R., "An Analysis of Base Pressure at Supersonic Velocities and Comparison with Experiment," NACA Report 1051 (1951), NTRS 19930090963 | Foundational semi-empirical base-pressure theory. **Not a closed-form Cp(M) equation** — requires boundary-layer-state input, case-by-case evaluation. | ✅ T1, opened |
| Love, E. S., "Base Pressure at Supersonic Speeds on Two-Dimensional Airfoils and on Bodies of Revolution... Turbulent Boundary Layers," NACA TN 3819 (1957), NTRS 19930084517 | Semi-empirical method via a boundary-layer-separation analogy; **restricted to turbulent BL, M ≈ 1–4** — not directly applicable to hypersonic capsule Mach numbers. | ✅ T1, opened |
| **Miller, C. G. III, "Experimental Base Pressures on 9° Spherically Blunted Cones at Mach Numbers From 10.5 to 20," NASA TN D-4800 (1968), NTRS 19680026196** | Direct wind-tunnel base-drag-fraction-of-total-drag data across bluntness ratios 0/0.3/0.55/0.8, M=10.6–19.6, Re≈0.02–2×10⁶ (laminar assumed). **Quoted result:** base drag &lt;2% of total for bluntness 0.55–0.8 across the whole Mach range; ~15%→2-4% for the pointed cone as M rises 10.6→19.6; ~5%→&lt;2.5% for bluntness 0.3. | ✅ T1, opened and grepped directly |
| Zarin, N. A., BRL Memo Report 1709 (1965), reproduced inside the Miller report | Same 9° cone family at M=3.5–9.2: pointed-cone base drag 57%→19% of total as M rises; bluntness-0.286 case 41%→7%. | ✅ T1 (numbers reproduced verbatim inside a primary source) |
| Karlgaard, Schoenenberger, Van Norman, "Base Drag Model Derived from Mars 2020 Backshell Pressure Measurements," JSR 60(6), 2023, DOI 10.2514/1.A35774 | **Real flight-measured** backshell pressure data (MEDLI2 instrumentation) — exactly the flight-Reynolds-number data this problem needs, but paywalled; only abstract/snippet level accessible. | 🟡 T2 |
| Kumar &amp; Reddy, "Numerical Simulation of Base Pressure and Drag of Space Reentry Capsules at High Speed," IntechOpen 2017 | Cp_base ≥ −2/(γM∞²) vacuum-limit bound (asymptotic upper bound, not a typical value); CFD-only, explicitly unvalidated by its own authors; also tabulates CDB for named capsules (Apollo, Soyuz, MUSES-C, etc.) at values that don't reconcile with the wind-tunnel fractions above — flagged as an open contradiction, not resolved. | 🟡 T2 |
| Hoerner, S. F., *Fluid-Dynamic Drag* (1965), Ch. XVI, https://archive.org/details/FluidDynamicDragHoerner1965 | Qualitative: base drag coefficient falls monotonically with Mach in the supersonic regime; **turbulent boundary layers give less base suction than laminar**, for equal wetted-area ratio. | ✅ T1, opened |

**Combined picture (base+friction as % of total drag, by bluntness ratio and Mach):**

| Bluntness | Mach 3.2–5.9 | Mach 3.5–9.2 | Mach 10.6–19.6 |
|---|---|---|---|
| Sphere (project's own) | 5.5–9.4% | — | — |
| 9° cone, blunt 0.8 | — | — | &lt;2% |
| 9° cone, blunt 0.55 | — | — | &lt;2% |
| 9° cone, blunt 0.3/0.286 | — | 7–41% | 2.5–5% |
| 9° cone, pointed | — | 19–57% | 2–15% |

**Direction is consistent everywhere: base-drag fraction shrinks with increasing Mach and shrinks with increasing bluntness.** A defensible engineering bound for a genuinely blunt capsule at supersonic-hypersonic Mach: **~2–10% of total drag, trending toward ~2% above M≈10 for bluntness ratio ≥0.5.**

**Unresolved gap:** every quantitative dataset found (project's own Bailey &amp; Hiatt, Re≈10⁴; Miller, Re≈0.02–2×10⁶, laminar-assumed) is low-Reynolds-number wind-tunnel data, not flight-representative turbulent-afterbody Re. Hoerner's qualitative note (turbulent → less base drag than laminar) suggests the available data is a conservative (over-)estimate of the missing term, but no source quantifies this. The Mars 2020 flight-pressure paper could close this gap but was inaccessible beyond snippet level.

**Sources:** see table above; all URLs are NTRS citation pages (`https://ntrs.nasa.gov/citations/<id>`) unless noted.

---

## 5. Published trajectory reference case for 3-DOF ballistic entry validation

**The Allen-Eggers closed-form solution — found, opened, and equations verified directly.**

Citation: Allen, H. J. &amp; Eggers, A. J. Jr., "A Study of the Motion and Aerodynamic Heating of Ballistic Missiles Entering the Earth's Atmosphere at High Supersonic Speeds," **NACA Report 1381** (1958), which supersedes the classified **NACA TN 4047** (confirmed by the report's own footnote). NTRS 19930091020, https://ntrs.nasa.gov/citations/19930091020.

Both an official NASA scan and an independent transcription were opened and cross-checked equation-by-equation (✅ T1). Notation: β = inverse atmospheric scale height (ρ=ρ₀e^(−βy)), θ_E = entry flight-path angle, straight-line flight path, gravity neglected relative to drag:

- Velocity vs. altitude (eq. 13): `V = V_E · exp[ −(C_D ρ₀ A)/(2βm sinθ_E) · e^(−βy) ]`
- Altitude of peak deceleration (eq. 15): `y₁ = (1/β)·ln[ C_D ρ₀ A / (β m sinθ_E) ]`
- Velocity at peak deceleration (eq. 16): `V₁ = V_E·e^(−1/2) ≈ 0.61 V_E`
- **Peak deceleration** (eq. 17): `(−dV/dt / g)_max = β V_E² sinθ_E / (2ge)`
- If y₁ &lt; 0, peak deceleration instead occurs at sea level — separate closed forms (eqs. 20–21).

**Assumptions, stated in the primary source:** constant C_D (good accuracy "as long as the total drag is largely pressure drag"); constant g; exponential/isothermal atmosphere; flat non-rotating Earth over the relevant band. The straight-line-path/gravity-negligible approximation is a **steep-entry approximation** — the report itself validates it only after showing drag dominates gravity for a worked vertical-entry case.

**Notation trap flagged:** a modern restatement (Wikipedia, "Planar reentry equations," 🟡 T2, algebraically checked by hand and confirmed equivalent) uses β for a *ballistic coefficient* m/(C_D·A), a different physical quantity from the primary report's β (inverse scale height). Any implementer must not conflate the two.

**A published numerical-integration benchmark against Allen-Eggers already exists** — directly useful for validating a 3-DOF integrator, not just checking arithmetic:

Putnam, Z. R. &amp; Braun, R. D., "Extension and Enhancement of the Allen–Eggers Analytical Ballistic Entry Trajectory Solution," *J. Guidance, Control, and Dynamics* 38(3), 2015, pp. 414–430, DOI 10.2514/1.G000846 (free full text: https://authors.library.caltech.edu/records/2s7xg-1tr96). ✅ T1, opened directly. Three cases run through both the closed form and full numerical integration (gravity included):

| Case | V₀ | γ₀ | h₀ | β=m/(C_D S) | Peak-g error (AE vs. numerical) | V-at-peak error | Altitude-at-peak error |
|---|---|---|---|---|---|---|---|
| Sample return (Stardust-like) | 12.8 km/s | −8.2° | 125 km | 60 kg/m² | **+34.9%** | −2.1% | −4.6% |
| Strategic (steep) | 7.2 km/s | −30.0° | 125 km | 10,000 kg/m² | **−5.1%** | −1.8% | +3.6% |
| LEO return (shallow) | 7.9 km/s | −1.35° | 100 km | 450 kg/m² | **−57.3%** | +34.9% | +27.0% |

**This sets expectations for AETHER's own validation:** a correctly-implemented numerical integrator should NOT match Allen-Eggers' peak-g to within a percent — a double-digit-percent gap is documented, expected behavior, shrinking as entry angle steepens.

**Real flown/reconstructed case:** Desai, P. N. &amp; Qualls, G. D., "Stardust Entry Reconstruction," AIAA 2008-1198, NTRS 20080008567 (✅ T1, opened). Nominal entry: V=12.9 km/s, γ=−8.2° (inertial, 6503.14 km radius), mass 46 kg. Reconstructed (radar-tracked) peak deceleration **32.89 Earth g** vs. pre-entry-predicted **32.86 g** (agreement ~0.1%); published 3σ Monte Carlo dispersion on max deceleration: **±3.64 g**. This validates a high-fidelity sim against tracking data, not the Allen-Eggers closed form directly.

**Worked numerical example from the primary NACA report itself** (p. 5–6): 1-ft iron sphere, vertical entry, V_E=30,000 ft/s, entry altitude 40 mi, β=1/22,000 ft⁻¹. Presented only graphically in the report (Figs. 2–3); the researcher independently recomputed via eqs. 15/17 from the report's own stated constants: y₁≈43,900 ft, peak deceleration≈234 g — this recomputation is the researcher's own arithmetic from primary-sourced inputs, not a printed number in the report (flag if cited formally).

**Not sourced:** Vinh, Busemann &amp; Culp (*Hypersonic and Planetary Entry Flight Mechanics*, 1980) and Regan &amp; Anandakrishnan (*Dynamics of Atmospheric Re-Entry*, 1993) — both out-of-print/paywalled, only bibliographic listings found, no accessible worked example (❌ T3).

**Sources:**
- ✅ T1 NACA Report 1381, NTRS 19930091020, https://ntrs.nasa.gov/citations/19930091020
- ✅ T1 Putnam &amp; Braun, JGCD 38(3), 2015, DOI 10.2514/1.G000846
- ✅ T1 Desai &amp; Qualls, AIAA 2008-1198, NTRS 20080008567
- 🟡 T2 Wikipedia, "Planar reentry equations" (equation cross-check only)
- ❌ T3 Vinh/Busemann/Culp; Regan/Anandakrishnan

---

## 6. USSA-1976 above 86 km — primary tabulation check (A-ATM-2, G1A′)

**Found and opened a real, text-searchable primary scan** of *U.S. Standard Atmosphere, 1976* (report NOAA-S/T 76-1562 / NASA-TM-X-74335, COESA, Oct 1976):

- **Best accessible copy (the one actually opened, page-searchable):** http://everyspec.com/NASA/NASA-General/download.php?spec=NASA_TM-X-74335.037294.pdf
- NTRS metadata page: https://ntrs.nasa.gov/citations/19770009539 (accession 77N16482) — no working direct-download PDF link found on this page in this session.
- NOAA mirror (same document, OCR text layer unreliable — use for the scan, not for programmatic text extraction): https://www.ngdc.noaa.gov/stp/space-weather/online-publications/miscellaneous/us-standard-atmosphere-1976/us-standard-atmosphere_st76-1562_noaa.pdf
- DTIC/archive.org scan: https://archive.org/details/DTIC_ADA035728

**Table I ("Geometric Altitude, Metric Units," pp. 68–69) — read directly off 300dpi page renders, not OCR text:**

| Z (km) | T (K) | ρ (kg/m³) | Tier |
|---|---|---|---|
| 90 | 186.87 | 3.416×10⁻⁶ | ✅ T1 |
| 100 | 195.08 | 5.604×10⁻⁷ | ✅ T1 |
| 110 | 240.00 | 9.708×10⁻⁸ | ✅ T1 |
| 120 | 360.00 | 2.222×10⁻⁸ | ✅ T1 |
| 150 | 634.39 | 2.076×10⁻⁹ | ✅ T1 |

(240.00 K and 360.00 K at 110/120 km are exact layer-boundary values by construction of USSA-76's piecewise model — a diagnostic that the values above are the correct diffusive-equilibrium tabulation, not a scale-height approximation.)

**Independent cross-check** — PDAS (Public Domain Aeronautical Software, pdas.com/bigtables.html), 🟡 T2, explicitly based on the primary document:

| Z (km) | T (K), PDAS | ρ (kg/m³), PDAS | Agreement |
|---|---|---|---|
| 90 | 186.867 | 3.4400×10⁻⁶ | T exact; ρ 0.7% high |
| 100 | 195.081 | 5.6044×10⁻⁷ | essentially exact |
| 110 | 240.000 | 9.6734×10⁻⁸ | T exact; ρ 0.36% low |
| 120 | 360.000 | 2.2199×10⁻⁸ | T exact; ρ 0.1% low |
| 150 | 634.392 | 2.0752×10⁻⁹ | essentially exact |

Temperatures match to 5–6 significant figures; densities agree to 0.1–0.7%, consistent with minor implementation rounding rather than a different model.

**Confirmed directly from the document text:** USSA-76 above 86 km uses individual per-species barometric equations (N₂, O, O₂, Ar, He, H) with diffusion coefficients, not a single-gas scale-height extrapolation.

**Flag — a commonly-used source that is NOT USSA-76 above 86 km:** braeunig.us/space/atmos.htm labels its table above 84,852 m as **MSISE-90**, a different, solar-activity-dependent empirical model, in a section easy to miss if only the page title is read. If this site was ever consulted for AETHER's transcribed table, that is a likely error source and should be checked.

**Recommendation:** the project's transcribed table can now be diffed directly against the values above; this closes the "not yet checked against a primary copy" open item for at least these five altitudes. A full-table diff (every row 86–150 km, not just the five requested) was not performed in this pass.

---

## 7. Representative capsule geometry ranges (A-GEO-7)

**Finding: flown capsules split into two distinct geometric families**, which is the researcher's own inference from the sourced numbers below, not stated by any single source, but consistent across nine independently-verified vehicles. Mixing both families into one Rn/D bound would blur a real design distinction.

| Vehicle | Rn/D | Shoulder R/D | Half-angle | Source | Tier |
|---|---|---|---|---|---|
| Apollo CM | 1.20 (Rn 4.693 m / D 3.912 m) | 0.050 (Rc 0.196 m) | 33.0° (baseline config C01 — **not** the commonly-quoted 32.5°, which was not found in any primary document) | NASA/TM-2005-213457, NTRS 20060008942 | ✅ T1 |
| Mercury | 1.07 (Rn 2.032 m / D 1.892 m) | not found | ❌ not confirmed (~20° is widely repeated but not found in a primary document) | Erb &amp; Jacobs, "Entry Performance of the Mercury Spacecraft Heat Shield," NASA MSC | ✅ T1 (D, Rn only) |
| Stardust SRC | 0.281 (Rn 0.2286 m / D 0.8128 m) | 0.023 (Rs 0.01905 m) | 60° (forebody), 30° (afterbody) | Wilmoth, Mitcheltree, Moss, "Low-Density Aerodynamics of the Stardust Sample Return Capsule," AIAA 97-2510 | ✅ T1 |
| Hayabusa (MUSES-C) | ~0.50 (via Hayabusa2, Rn 0.207 m / D 0.413 m — assumed geometrically identical to original, not independently confirmed) | not found | 45° | NTRS 20160000307 (D, θ verbatim); NTRS 20220006454 (Rn, via Hayabusa2) | ✅ T1 (D, θ) / 🟡 T2 (Rn) |
| Viking | 0.25 (Rn 0.876 m / D 3.5 m) | 0.007 (Rc/Rn=0.029, stated directly) | 70° | "Viking Afterbody Heating Computations and Comparisons to Flight Data," NTRS 20060017066 | ✅ T1 |
| Pathfinder | 0.25 (Rn 0.664 m / D 2.65 m) | 0.025 (Rc 0.0663 m) | 70° | Spencer et al., AAS 98-146; NTRS 20040090463 | ✅ T1 |
| MER | 0.25 (heritage claim: "Viking-heritage 70° sphere-cone," stated explicitly) | not independently confirmed | 70° | NTRS 20080013365 | 🟡 T2 |
| MSL (Curiosity) | 0.25 (ratios primary-confirmed; Rn=1.125 m/D=4.5 m in meters is secondary-consistent, not verbatim-quoted) | 0.025 (Rc/Rn=0.1, stated directly, vs Viking's 0.029) | 70° | NTRS 20120011936 (aero) + NTRS 20090024218/20090007730 (heatshield/EDL) | ✅ T1 (ratios) / 🟡 T2 (exact meters) |
| Soyuz descent module | **Does not fit sphere-cone-torus** — asymmetric "headlight" shape, lift via CG offset, not blunt-body angle | N/A | N/A | No primary numeric document found; secondary sources disagree even on diameter (2.2 m vs 2.3 m) | ❌ T3 |
| Generic 45° sphere-cone | Bluntness sweep 0, 0.125, 0.25, 0.375, 0.5 | N/A (pure cone, no torus) | 45° | Passamaneck, "Aerodynamic Characteristics of Spherically Blunted 45-Deg Half-Angle Cones," JPL TR 32-1327, NTRS 19690003885 | ✅ T1 |
| Generic 60° sphere-cone | Use Stardust (0.281) as the real flown reference | — | confirmed tested (NASA/Langley MSR-EES program tested 45°/52.5°/60°) but no Rn/D extractable | AIAA SciTech 2024, NTRS 20230018603 | 🟡 T2 |

**Pattern:** shallow spherical-cap capsules (Mercury, Apollo) cluster at **Rn/D ≈ 1.0–1.2**; blunted sphere-cones (Viking-heritage Mars family, Stardust, Hayabusa) cluster at **Rn/D ≈ 0.25–0.5**. The Mars-heritage family (Viking/Pathfinder/MER/MSL) additionally shows shoulder-radius ratios tightening over time: Rc/Rn = 0.029 (Viking) → 0.025 (Pathfinder) → 0.1 (MSL, a deliberate change, stated directly in its source).

**Correction against the brief's own assumptions:** Stardust's Rn/D is 0.281, not "0.5+" as initially assumed when scoping this research — 0.5+ actually belongs to Hayabusa. This was caught by direct primary-source verification, not repeated uncritically.

**Not sourced:** Apollo's commonly-cited 32.5° half-angle (primary source gives 33.0°); Mercury's cone half-angle and shoulder radius; Hayabusa's original (non-Hayabusa2) nose radius; any primary-sourced numeric Soyuz geometry; a generic 60° sphere-cone Rn/D independent of Stardust.

**Sources:** all NTRS citation pages `https://ntrs.nasa.gov/citations/<id>` per the IDs above.

---

## What remains unsourced

Honest accounting of every gap surfaced across all seven items — these should stay flagged in ASSUMPTIONS.md, not silently resolved:

1. **The exact numeric provenance of k = 1.7415×10⁻⁴** as a verbatim quantity inside NASA-TR-R-376 — the primary report doesn't contain this constant or this equation form at all; only a NASA training-course derivation (🟡 T2) connects them. The algebraic re-derivation from the primary report's K(air)=0.1113 has not been done. The commonly-seen alternate value 1.7623×10⁻⁴ has no source anywhere found (❌ T3) — do not use it.
2. **Tauber's review papers** (NASA TP-2914, 1989; Tauber &amp; Sutton 1991) on limitations of Sutton-Graves-class correlations — cited by secondary sources but not opened.
3. **The primary 1958 USAF source (Bondurant et al.)** behind NASA TM-104753's "8g for 5 min" sustained-tolerance figure — only the NASA TM's citation of it was seen.
4. **Exact digit-level values off the Bioastronautics Data Book's Fig. 4-24** sustained-tolerance chart — OCR of the scan was unusable; only the primary document's surrounding text was read.
5. **The Kafka "ISS Ballistic Entry Outbrief" NASA document** behind the Soyuz TMA-11 g-figures — only secondary (IEEE Spectrum) reporting on it was accessible.
6. **A single primary sentence tying RTV-560 specifically (not just the aluminum airframe generally) to the 350°F Shuttle bondline limit**, and the full text of Cooper &amp; Holloway's "The Shuttle Tile Story" (1981) — not available on NTRS.
7. **The Mars 2020 MEDLI2 flight-measured base-drag paper** (Karlgaard et al. 2023, JSR) — real flight-Reynolds-number base-pressure data exists but is paywalled; only abstract-level access achieved.
8. **A quantitative (not just qualitative) turbulent-vs-laminar or flight-Re-vs-wind-tunnel-Re base-drag comparison** for a blunt capsule — every quantitative base-drag dataset found (project's own + Miller/Zarin) is low-Re wind-tunnel data; the direction of the correction (Hoerner: turbulent BL → less base drag) is known qualitatively but not quantified.
9. **Reconciliation of the IntechOpen CFD base-drag-coefficient values** (10⁻⁴–10⁻⁵, unvalidated by the paper's own authors) against the much larger measured wind-tunnel fractions (2–60%) for comparable shapes — left as an open contradiction, not resolved.
10. **Vinh/Busemann/Culp and Regan/Anandakrishnan textbooks** (classic sources for a worked Allen-Eggers-style entry problem) — paywalled/out-of-print, no accessible content found.
11. **A full 86–150 km row-by-row diff** of the project's transcribed atmosphere table against USSA-76 Table I — only the five specifically-requested altitudes (90/100/110/120/150 km) were checked; the complete table was not diffed.
12. **Apollo's commonly-quoted 32.5° half-angle** could not be confirmed in any primary document (the primary source's own baseline configuration gives 33.0°); **Mercury's cone half-angle** (~20°, folklore-repeated) and **shoulder radius** were not found in a primary document; **Hayabusa's original nose radius** (as opposed to Hayabusa2's) was not independently confirmed; **Soyuz's geometry** has no primary numeric source at all and does not fit the sphere-cone-torus parametrization regardless.
13. **The text of Celik et al. (2008), Roache's GCI sources and Billig (1967)** (item 9) — bibliographic records verified, contents not opened. Open check: read Celik et al. against `src/aether/cfd/gci.py` (apparent-order iteration with the sign term, the oscillatory-convergence rule, step 5), and read Billig's exponent (3.24 vs 3.2) off the original.

---

## 8. Effective nose radius for a shallow spherical segment (A-GEO-3, A-OPT-5, NR-15)

*Added 2026-09-20, a second research pass. This item does not close a placeholder VALUE; it
closes a model-FORM failure — the one condition under which spec §42 permits new physics.*

**Project placeholder:** `effective_nose_radius_m = nose_radius_m`, protected by a
`max_bluntness_ratio = 1.2` fence.

**Finding: a quantitative relation is citable from two primary documents, both opened and
read, and they disagree with each other by more than this project's other heating
uncertainties.**

| Value | Form | Source | Tier |
|---|---|---|---|
| `R_b/R_eff = (dU/dS)_s,BB / (dU/dS)_s,hemi` | the DEFINITION of an effective radius | NASA TM X-1067 (Zoby &amp; Sullivan, 1965), eqs. (3)–(5), report p. 4, NTRS 19660017753 | ✅ T1 |
| Nine measured values of `R_b/R_eff` over `K = R_b/R_n` ∈ {0, 0.417, 0.707} and `R_c/R_b` ∈ {0, 0.2, 0.4} | table | NASA TN D-5121 (Ellison, 1969), **Table I**, α = 0 rows, report p. 11, NTRS 19690013192 | ✅ T1 |
| Flat face, sharp corner: `R_eff = 3.155 R_b` | from that table | as above | ✅ T1 |
| Flat face, sharp corner: `R_eff ≈ 3.40–3.50 R_b` | figure read | TM X-1067 figures 3 and 4, digitised at 600 dpi, ±0.010 | 🟡 T2 |
| "Corner radius raises the heating ratio ~11% (fig. 3) / ~22% (fig. 4) at `r_B/r_N = 0` as `r_C/r_B` goes 0 → 0.3" | verbatim statement | TM X-1067, pp. 6–7 | ✅ T1 |
| "Agreement with Zoby &amp; Sullivan within 10 percent for K = 0 and K = 0.707; for K = 0.417 and R = 0, the disagreement is about 20 percent" | verbatim statement | TN D-5121, p. 5 | ✅ T1 |
| Precedent for substituting `R_eff` into a Sutton–Graves-FORM correlation | `q̇_s √(R_eff/p_s) = K_i (H_s − H_w)`, its eq. (1), citing TM X-1067 as its ref. 19 | NASA TN D-4799 (Zoby, 1968), NTRS 19680025996 | ✅ T1 |
| "R_eff ≈ 3.3–3.4 × body radius" attributed to a hypersonics textbook | — | **No textbook was opened.** Anderson, Bertin, Hirschel were all attempted and none was obtainable. The number is *supported* by the primaries above and should be cited to them | ❌ T3 as a textbook claim |

**Validity conditions (from the primaries):** angle of attack 0° in both. Ellison: M = 8.0,
Re_D = 1.37×10⁶, perfect-gas cold-wall tunnel, `K ≤ 0.707` (the hemisphere end is *not*
covered by his experiment). Zoby &amp; Sullivan: `r_B/r_N` 0→1.0, `r_C/r_B` 0→0.30, source
pressure data reduced for equilibrium air at 23 800 ft/s and 138 000 ft, and the whole
method rests on the stagnation-region pressure distribution being invariant for M ≳ 3.5 —
which is what licenses using M = 8 tunnel data at AETHER's 7.4 km/s. ✅ T1 throughout.

**Neither source publishes a formula** — faired curves in one, a 3×3 table and two
interpolation charts in the other, and a third report of the era (Stallings, 1967)
explicitly instructing the reader to interpolate from charts. The interpolation in
`src/aether/geometry/stagnation_gradient.py` is therefore **this project's construction
over the primaries' data points** and is labelled as such everywhere it appears.

**Which was adopted, and why.** Ellison. It is tabulated rather than read off a graph, it
is an experiment rather than a computation from other people's pressure data, and it is
the **conservative** of the two (smaller `R_eff`, hence more heating). The disagreement
between the two is carried as the stated uncertainty rather than resolved by preferring
one — and at `K ≈ 0.42`, which is exactly where the M4 front sits, it is about ±20% on
`R_eff`, i.e. ±10% on heat flux.

**Could not be sourced:** Boison &amp; Curtiss (ARS J. 29(2), 1959, DOI 10.2514/8.4699) —
citation confirmed real, publisher blocks access, ❌ T3. Trimmer (AEDC, DTIC AD0669378) —
exists, DTIC returned 403 to every path, ❌ T3. **Rodrigues, "Closed-Form Reconstruction of
Zoby–Sullivan Stagnation-Point Heat-Flux Scaling", JTHT, 7 July 2026, DOI 10.2514/1.T7458**
— paywalled, ❌ T3; its title describes exactly the published fit that would replace this
project's own interpolation, and it is the single highest-value follow-up on this topic.

Full provenance and verbatim quotations: `data/reference/stagnation_velocity_gradient.yaml`.
Derivation: `docs/theory/effective_nose_radius.md`.

---

## 9. Methods the M2 CFD gate leans on: GCI procedure, Roache, Billig (G4) — checked 2026-09-21

**Why this item exists.** `src/aether/cfd/gci.py` and the M2 report cite Celik et al. (2008)
for the five-step GCI procedure and its 1.25 safety factor, name Roache as the origin of that
factor, and use Billig (1967) for the shock stand-off correlation. None of the three had a
provenance entry. Result: **none of the three primary texts could be opened.** What could be
verified, and how, is below; the code was NOT changed on the strength of anything here.

| Source | Tier | What was actually opened | What is therefore verified | What is NOT verified |
|---|---|---|---|---|
| I. B. Celik, U. Ghia, P. J. Roache, C. J. Freitas, H. Coleman, P. E. Raad, "Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications", *J. Fluids Eng.* **130**(7), 078001 (2008), DOI 10.1115/1.2960953 | 🟡 T2 | The **Crossref record** for the DOI (title, journal, volume 130, issue 7, article 078001, 2008). The publisher PDF is listed as open access by Unpaywall but the ASME site returned an HTML bot-wall to `curl` and HTTP 403 to the fetch tool; an academia.edu copy also returned 403. | The bibliographic record, exactly as cited in `gci.py`. | **Every statement about the paper's content.** In particular: the fixed-point form of the apparent-order equation with the sign term s = sgn(ε32/ε21) implemented in `observed_order`; the rule "ε32/ε21 < 0 indicates oscillatory convergence"; and that the paper's step 5 uses 1.25. These are implemented from the author's (the AI assistant's) recollection of the paper and agree with the NASA page below wherever the two overlap (constant-r order formula, GCI formula, 1.25 for three grids), but the parts that do not overlap are **unverified against any opened text**. |
| NASA Glenn NPARC Alliance CFD Verification & Validation tutorial, "Examining Spatial (Grid) Convergence", grc.nasa.gov/www/wind/valid/tutorial/spatconv.html | ✅ T1 (opened directly; NASA-hosted) | The page itself. | Quoted: GCI_fine = Fs·\|(f1 − f2)/f1\| / (r^p − 1); "The factor of safety is recommended to be Fs=3.0 for comparisons of two grids and Fs=1.25 for comparisons over three or more grids"; p = ln[(f3 − f2)/(f2 − f1)] / ln r for constant r; the asymptotic-range check GCI_23 = r^p · GCI_12; and "the boundary conditions, numerical models, and grid will reduce this order so that the observed order of convergence will likely be lower", with "presence of shocks" listed among the causes in its worked example. These match `gci.py` for constant r. | It attributes the method to "the book by Roache" without a full citation in the fetched text. It gives **no number** for how far below the formal order a shock-capturing solution should fall, so it does not establish that the M2 observed orders (≈ 0.6–0.7 before the Courant restarts) are "normal" — only that lower-than-formal is expected. |
| P. J. Roache — the GCI and its safety factors (usually cited as *J. Fluids Eng.* 116(3), 1994, and *Verification and Validation in Computational Science and Engineering*, Hermosa, 1998) | ❌ T3 as a primary | Nothing. Neither was located in an openable form. The citation details in this row are from memory and are **not verified**. | Only what NASA's tutorial (row above) attributes to Roache. | Everything else. Do not cite Roache directly in the paper; cite the NASA tutorial for the formulae and Celik et al. for the procedure, with the tiers above. |
| F. S. Billig, "Shock-wave shapes around spherical- and cylindrical-nosed bodies", *J. Spacecraft Rockets* **4**(6), 822–823 (1967), DOI 10.2514/3.28969 | 🟡 T2 for the record, ❌ T3 for the content | The **Crossref record** (title, journal, volume 4, issue 6, pp. 822–823, June 1967). The AIAA page is paywalled; the ADS abstract page returned HTTP 405. | The bibliographic record. | The formula itself. As already recorded in `data/reference/sphere_supersonic.yaml`, Δ/R = 0.143 exp(3.24/M²) comes from secondary sources, and one of them prints the exponent as 3.2. The M2 report now prints the comparison both ways. Billig's correlation decides nothing in gate G4 (it is marked not like-for-like); it also sizes the computational domain, where a 1% change in a stand-off that is then doubled is immaterial. |

**Consequence for the paper.** The GCI numbers may be reported as "computed with the three-grid
GCI procedure (Celik et al. 2008; formulae as given in NASA's NPARC verification tutorial)", not
as "following Celik et al." without qualification, until someone with library access reads the
paper against `gci.py`. That check is listed under *What remains unsourced*.

**Disclosure.** One lookup in this pass (Unpaywall's API) was made with the project owner's
e-mail address as the API's required contact parameter. It should not have been; no other
service received it.

---

## Sources — full list, graded

**✅ T1 (primary, opened and read directly)**
- Sutton, K. &amp; Graves, R. A. Jr., NASA-TR-R-376 (1971), NTRS 19720003329
- NASA-STD-3001 Vol 2 Rev F, Table 6.5-1
- OCHMO-TB-024 Rev D (2025-03-13)
- NASA TM-104753 (1992), NTRS 19930020462
- Eiband, A. M., NASA Memo 5-19-59E (1959), NTRS 19980228043
- NASA Bioastronautics Data Book, NASA SP-3006 (1973), NTRS 19730006364 (text; figure digits unreadable)
- NASA TN D-7564, Pavlosky &amp; St. Leger (1974), NTRS 19740007423
- NASA CR-159900, Smith, Hamermesh &amp; Hogenson (1979), NTRS 19790012947
- Vander Kam &amp; Gage, AIAA/JSR, NTRS 20160007549
- Chapman, D. R., NACA Report 1051 (1951), NTRS 19930090963
- Love, E. S., NACA TN 3819 (1957), NTRS 19930084517
- Miller, C. G. III, NASA TN D-4800 (1968), NTRS 19680026196 (incl. Zarin BRL data reproduced within)
- Hoerner, S. F., *Fluid-Dynamic Drag* (1965), Ch. XVI, archive.org
- Allen, H. J. &amp; Eggers, A. J. Jr., NACA Report 1381 (1958), NTRS 19930091020
- Putnam, Z. R. &amp; Braun, R. D., JGCD 38(3) (2015), DOI 10.2514/1.G000846
- Desai, P. N. &amp; Qualls, G. D., AIAA 2008-1198, NTRS 20080008567
- *U.S. Standard Atmosphere, 1976*, NOAA-S/T 76-1562 / NASA-TM-X-74335, Table I pp. 68–69
- NASA/TM-2005-213457 (Apollo), NTRS 20060008942
- Erb &amp; Jacobs, "Entry Performance of the Mercury Spacecraft Heat Shield," NASA MSC
- Wilmoth, Mitcheltree, Moss, AIAA 97-2510 (Stardust)
- "Viking Afterbody Heating Computations and Comparisons to Flight Data," NTRS 20060017066
- Spencer et al., AAS 98-146; NTRS 20040090463 (Pathfinder)
- NTRS 20120011936, 20090024218, 20090007730 (MSL)
- Passamaneck, JPL TR 32-1327, NTRS 19690003885 (generic 45° sphere-cone)
- NTRS 20160000307 (Hayabusa D, θ)

**🟡 T2 (reputable secondary only)**
- Celik et al., *J. Fluids Eng.* 130(7), 078001 (2008) — bibliographic record only (Crossref); content not opened (item 9)
- Billig, *J. Spacecraft Rockets* 4(6), 822–823 (1967) — bibliographic record only (Crossref); formula from secondary sources (item 9)
- NASA TFAWS 2012 *Aerothermodynamics Course* (Sutton-Graves V³ form)
- Wikipedia, "Planar reentry equations" (corroboration only, both items 1 and 5)
- Carroll &amp; Brandis, AIAA Aviation 2022, NTRS 20220018610
- ONERA/CNES, 1st Int'l Orbital Debris Conf. 2019
- IEEE Spectrum, 7 May 2008 (Soyuz TMA-11)
- Day, D. A., "Shuttle Thermal Protection System (TPS)," U.S. Centennial of Flight Commission
- Karlgaard, Schoenenberger, Van Norman, JSR 60(6) 2023, DOI 10.2514/1.A35774 (paywalled)
- Kumar &amp; Reddy, IntechOpen 2017
- PDAS (pdas.com/bigtables.html), USSA-76 cross-check
- NTRS 20220006454 (Hayabusa2 Rn, used as proxy for Hayabusa)
- NTRS 20080013365 (MER heritage claim)
- NTRS 20230018603 (generic 60° sphere-cone config, no numeric ratio)

**❌ T3 (could not source — do not cite)**
- Roache's GCI papers/book as primaries (item 9) — cite NASA's NPARC tutorial instead
- Any source for k = 1.7623×10⁻⁴
- Tauber, NASA TP-2914 (1989); Tauber &amp; Sutton (1991)
- Cooper &amp; Holloway, "The Shuttle Tile Story" (1981), NTRS 19810036013 — no accessible full text
- Vinh, Busemann &amp; Culp, *Hypersonic and Planetary Entry Flight Mechanics* (1980)
- Regan &amp; Anandakrishnan, *Dynamics of Atmospheric Re-Entry* (1993)
- Any primary numeric source for Soyuz descent-module geometry
- Apollo's 32.5° half-angle in any primary document (33.0° is what the primary source actually gives)
- Mercury's cone half-angle and shoulder radius in a primary document
