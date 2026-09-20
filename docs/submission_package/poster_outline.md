# Research poster — source outline

Spec §51. Panel-by-panel source for an A0 portrait poster (841 × 1189 mm), three columns.

**Status: skeleton.** `[PENDING FINAL RUN]` marks every panel that needs an unrun study.

---

## Design constraints, decided before any layout

- **Light background, high contrast.** Poster sessions are lit unpredictably and printed
  posters are read at 1–2 m. No dark mode, no thin light type on a dark field.
- **Readable at 1.5 m**: title ≥ 90 pt, panel headings ≥ 48 pt, body ≥ 28 pt, figure axis
  labels ≥ 24 pt at final print size. A figure that needs the reader to lean in is a figure
  that will not be read.
- **Figures are exported from the repository, not redrawn.** Every one exists as a vector
  PDF beside its PNG in `reports/figures/`. Use the PDF.
- **Every number carries its source.** A small caption under each panel naming the result
  file or report section, in ≥ 18 pt.
- **A poster is read in 30 seconds and then discussed for five minutes.** The 30-second path
  is: title → the one-sentence question → the mechanism figure → the result box. Everything
  else is for the conversation.

---

## Column 1 — the question

### Panel 1. Title block

> **When cooler is not safer**
> Peak versus in-depth thermal optimisation of atmospheric re-entry

Author line: name, independent capstone, year. No institution or venue.

### Panel 2. The question (final, ~50 words at ≥ 32 pt)

> A heat shield is designed against **peak heat flux**: the worst instant of heating on its
> outer surface.
>
> It does not fail there. It fails at the **bondline**, where the shield meets the structure,
> and the bondline responds to the **total heat that got past the surface**, not to the peak.
>
> Are those minimised by the same entry?

### Panel 3. The mechanism

Figure: `reports/figures/M1_mechanism.png` (largest figure on the poster).

Caption, three bullets at ≥ 28 pt:

- Heating goes as **V³√ρ**. A shallow entry is slower through thinner air: lower peak.
- The shield is a **diffusive low-pass filter**, characteristic time L²/α. Here √(αt) ≈ 15 mm
  over a 245 s entry, which is the stack thickness: the timescales are comparable.
- So a short hard pulse is re-radiated away at T⁴ before it penetrates; a long soft pulse has
  time to reach the bondline.

---

## Column 2 — the evidence

### Panel 4. The result

Figure: `reports/figures/M1_trade_space.png`.

Result box, large:

| | Steep, −8.00° | Shallow, −1.50° |
|---|---|---|
| Peak heat flux | 230.64 W/cm² | **142.38** (−38.3%) |
| Peak bondline T | **423.7 K** | 537.8 K (+114.1 K) |

One line beneath, at ≥ 28 pt: *Strictly monotone with opposite signs across the whole range
tested. No intermediate angle improves both. 818 counterexample pairs of 1640 tested, with
detection thresholds declared in advance.*

**Do not put "ρ = −1.000" on the poster.** Over a one-parameter sweep it is close to
tautological and it is the single most quotable-and-wrong number in the project. If a visitor
asks about correlation, the spoken answer is in `docs/defense_questions.md` Q26.

### Panel 5. Nothing was feasible

Figure: `reports/figures/M1b_feasible_region.png`.

> With geometry frozen, **0 of 41** trajectories satisfied both the deceleration and bondline
> limits. Steep entries fail on g, shallow ones on bondline.
>
> This was not anticipated, and it is why the objective optimises geometry and trajectory
> **jointly**. Opening the diameter axis recovers **21 of 140**.

### Panel 6. Joint versus peak-only

Figure: `reports/figures/M1b_optimiser_comparison.png`.

> A peak-flux-only optimiser lands at a bondline of 444.1 K. A joint optimiser lands at
> 411.6 K: **32.5 K cooler**, for +19.6% on peak heat flux.
>
> Reported as an absolute difference, not a ratio. The ratio depends on the bondline
> allowable and swings from 37.5× to 1.6× as that moves from 445 K to 500 K.

Caption: *Legacy heating model. For these designs (hemisphere nose, R_n = D/2) the corrected
effective-nose-radius model agrees identically, so these numbers are unchanged by it.*

### Panel 7. Pareto front

`[PENDING FINAL RUN]` — `reports/figures/M4_pareto_front.png`, regenerated under the
corrected heating model and the CFD drag surface, with the joint knee design and the
peak-flux-only optimum marked.

---

## Column 3 — how far it can be trusted

### Panel 8. Verified before it was used

Three numbers at ≥ 32 pt, each with its reference:

> **0.002%** — conduction solver against the Carslaw & Jaeger analytical solution.
> Energy balance closes to ~10⁻¹⁴.
>
> **0.92 pp** — trajectory integrator reproducing a *published disagreement* between a
> closed-form solution and a numerical one (Putnam & Braun 2015). The closed form neglects
> gravity, so a correct integrator must disagree; reproducing the published gap is the test.
>
> **0.39%** — heating constant re-derived from NASA TR R-376, against that report's own
> stated 3.3% average error. The constant was **not changed**.

### Panel 9. What broke

Two entries, because this is the panel people stop at.

> **The optimiser cheated.** Taking the nose radius from the cap made `1/√R_n` send heating
> to zero as the nose flattened: an infinitely flat nose shed **98.9%** of the stagnation
> heat flux, and 54 of 64 front designs pressed against a placeholder cap. Measured
> stagnation-point velocity gradients from two 1960s NASA reports make the real figure
> **21.3%**. The fix then moved the exploit to the shoulder, which this model cannot see.
>
> **A figure caught a bug a test suite missed.** A two-objective Pareto front must be
> monotone. The first implementation plotted a zigzag, which is geometrically impossible.
> The dominance test had inverted control flow.

### Panel 10. Limitations (not small type)

> - Every optimisation result is **Fidelity 0**: constant drag coefficient. The CFD drag
>   surface is provisional and **switched off**.
> - CFD gate **G4 is not passed**. Mesh independence incomplete; no published blunt-body case
>   compared.
> - **No physical measurement exists.** The thermal coupon has not been printed.
> - Several constraint limits are engineering placeholders. The 12 g deceleration limit
>   corresponds to **no** documented sustained-g curve, and adopting the documented curve for
>   a deconditioned crew would empty the feasible region entirely.
> - Model predictions within documented assumptions. No claim about any flight vehicle or
>   real material.

### Panel 11. Reproducibility and disclosure

> `make test && make burn-vs-bake` reproduces the result. Runtimes and hardware assumptions
> in `REPRODUCIBILITY.md`. Every number in every report is read from a result file; reports
> are generated, never hand-edited.
>
> **AI disclosure.** Most of the code was written with AI assistance. What was generated,
> what was reviewed and what was student-authored: `AI_USAGE.md`.

QR code to the repository, bottom right, ≥ 40 mm square.

---

## Things deliberately not on this poster

- Any Spearman correlation coefficient.
- Any margin ratio.
- Any AI-versus-human optimiser comparison, until M5 has run and the declared criterion has
  been evaluated.
- Any mention of a venue, award, institution or admissions context.
- Anything about the framework, the language model, or the tooling in the top third of the
  poster. Spec §51: the first thing a reader sees is the scientific question.

---

## Handout

Print the two-page brief as the handout. Do not make a third, shorter document: it will
drift from the other two and one of them will end up saying something the evidence does not
support.
