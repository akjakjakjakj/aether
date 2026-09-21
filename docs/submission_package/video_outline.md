# 3–5 minute technical video — outline

Spec §51. A longer piece than the 90-second explainer: this one shows the work, including the
parts that went wrong.

**Status: filled 2026-09-21 from the result files at commit `de2a834`; AI-drafted.** The
spoken lines are the student's to rewrite in his own words. `[PENDING — STUDENT]` marks what
depends on the physical experiment or on external review.

Target 4:00. Seven beats. Every visual is a file that already exists in the repository or a
screen recording of a command that actually runs.

---

## Beat 1 — the question (0:00–0:35)

**Visual.** `reports/figures/M1_temperature_field.png`, the depth-versus-time temperature
field, zooming from the hot surface down to the bondline.

**Spoken (final).**

> Every re-entry heat shield is designed against one number: peak heat flux, the worst
> instant of heating on the outer surface. That number picks the material.
>
> But look at where the shield actually fails. Not at the surface. At the bondline, where it
> is attached to the structure. And the bondline does not see the worst instant. It sees
> everything that got through, integrated over the whole entry, arriving minutes late.

**Rule.** No software, no AI, no tooling in this beat. Spec §51.

---

## Beat 2 — why the two disagree (0:35–1:15)

**Visual.** Split screen: heat-flux history for a steep and a shallow entry on the left
(`reports/figures/M1_mechanism.png`), in-depth temperature on the right.

**Spoken.**

> Heating scales as velocity cubed and only as the square root of density. So a shallower
> entry, which decelerates higher up in thinner air, has a lower peak.
>
> But it takes much longer. And a heat shield is a diffusive filter: heat takes time to get
> through it. The depth heat reaches in time t is the square root of alpha t, and for this
> stack over a 245-second entry, that is about 15 millimetres. Which is exactly how thick the
> insulator is.
>
> That is the whole reason this is interesting. If the shield were much thicker, the bondline
> would never hear about the entry. If it were much thinner, it would just follow the
> surface. The two timescales are comparable, so *how long the pulse lasted* changes the
> answer, not just how big it was.

**On screen.** √(αt) ≈ 15 mm, α = 8.9×10⁻⁷ m²/s, t = 245 s, as clean typeset text.

---

## Beat 3 — verify before you use (1:15–1:55)

**Visual.** Screen recording of `make test` actually running to completion, then the
`VALIDATION_MATRIX.md` table scrolling with the `PASS` and `LIMITED` rows visible.

**Spoken.**

> Before any of this counts, the model has to be checked, and checked against something that
> is not itself.
>
> The conduction solver is compared with an analytical solution for a semi-infinite solid
> under constant surface flux. It agrees to two thousandths of a percent, and its energy
> balance closes to about ten to the minus fourteen.
>
> The trajectory integrator is harder, and the way it works is worth a sentence. There is a
> classical closed-form entry solution from 1958, but it neglects gravity, so a correct
> numerical integrator *must* disagree with it, and more so the shallower the entry gets. So
> the test is not agreement. A 2015 paper publishes that disagreement for three entry cases,
> and this integrator reproduces all nine published figures to within 0.92 percentage points.
>
> And the matrix says what has *not* been checked, in the same table, with the same weight.

---

## Beat 4 — the result (1:55–2:35)

**Visual.** `reports/figures/M1_trade_space.png` animating as the sweep runs; then the
feasible-region figure `reports/figures/M1b_feasible_region.png`.

**Spoken (numbers final).**

> Sweeping entry angle: the shallowest entry cuts peak heat flux by 38.3 percent and runs the
> bondline 114.1 kelvin hotter. Every step that improves one makes the other worse. There is
> no angle in between that wins on both.
>
> Then the part I did not expect. With the shape held fixed, zero of 41 trajectories
> satisfied both hard limits. Steep entries break the deceleration limit, shallow ones break
> the bondline limit, and nothing passes both. You cannot fly your way out of it.
>
> Opening the geometry axis recovers a feasible region, and there the joint optimiser picks a
> design whose bondline runs 32.5 kelvin cooler than the one you get from optimising peak
> flux alone.

**On screen.** The M1b comparison table. **Not** the Spearman coefficient and **not** a margin
ratio.

---

## Beat 5 — where the optimiser cheated (2:35–3:20)

This is the beat that distinguishes this video from a results summary. Give it the time.

**Visual.** The table from `docs/negative_results.md` NR-15's follow-up, then
`docs/theory/effective_nose_radius.md`'s Ellison table.

**Spoken.**

> Here is the thing I am most glad I found.
>
> Sutton–Graves says stagnation heating goes as one over the square root of the nose radius.
> So the optimiser flattened the nose. And flattened it. Because in that equation, an
> infinitely flat nose has zero heating.
>
> Which is nonsense. A flat face has a perfectly finite heating rate. The equation's
> one-over-root-R is not really about the radius of the round thing at the front. It is about
> the stagnation-point velocity gradient, how hard the flow is made to turn as it escapes the
> stagnation point, and only for a sphere is that gradient set by the nose radius. For a
> shallow cap it is set by the body radius and the corner.
>
> Two NASA reports from 1965 and 1969 measured that gradient. Feeding the right effective
> radius in, an infinitely flat nose is worth 21 percent, not 99. Peak heating on the
> existing designs went **up** by about 20 percent.
>
> And then the honest part: the fix moved the exploit rather than removing it. A sharper
> shoulder now *lowers* stagnation heating, so the optimiser will want a sharp shoulder. A
> sharp shoulder is exactly where real vehicles get damaged, and this model, which only looks
> at the stagnation point, cannot see that at all. That is written down before the next run,
> not after it.

---

## Beat 6 — the results (3:20–3:45)

**Visual.** `reports/figures/M4_pareto_front.png`; then `reports/figures/M7_pbox.png`; then
the §39 comparison table from `reports/milestones/M7_uncertainty_robust.md` §6; then
`reports/figures/M6_cfd_spend_map.png`.

**Spoken (numbers from the result files; wording to be made the student's own).**

> With the corrected heating and drag taken from CFD, I ran the optimisation again. The
> design at the knee of the front runs 14.9 kelvin cooler at the bondline than the one a
> peak-flux-only search picks, and pays 21.5 kilowatts per square metre of peak flux for it.
>
> Then I asked whether that survives what I do not know. Twelve uncertain inputs, three
> thousand draws, every design on the same draws. Paired, the difference is 14.3 kelvin with
> a spread of one and a half, and the knee is cooler in every single draw.
>
> Here is what that result is not. Every design on that front is the same shape and the same
> size. The optimiser grew the diameter until the heat shield weighed as much as the vehicle,
> 346 kilograms out of 350, and stopped only because I had told it a shield cannot outweigh
> the vehicle. So the front is a curve in entry angle, drawn at a vehicle nobody could build.
> It tells you about steepness. It does not tell you about shape.
>
> The nominal optima also fail a constraint in thirty to forty-seven percent of draws. None
> of those failures is thermal; they are the mass limit and the g limit. A design optimised
> with a five percent chance constraint brings that down to 3.2 percent, for about three
> percent more peak flux.
>
> Two method questions. A language-model agent beat the best conventional optimiser at fifty
> and a hundred evaluations, and by two hundred the rule I had written down beforehand said
> no measured difference. It knew the textbook directions before it saw any data, and I cannot
> separate that from reasoning. And my third hypothesis, that choosing CFD runs adaptively
> would save CFD runs, was not supported. No arm reached the target in any seed, the target
> turned out to be out of reach at that budget, which was my sizing mistake, and a hundred
> and nine extra CFD points changed the no-CFD arm's score by one part in ten thousand.

**Sources.** `M4_pareto_optimisation.md` §10, §11a; `M7_addendum_posthoc.md` §1;
`M7_uncertainty_robust.md` §3.2, §6; `M5_ai_ablation.md` §4; `M6_adaptive_fidelity.md`;
`M6_addendum_posthoc.md` §2; NR-30, NR-33, NR-35.

**On screen.** The §39 table with the like-for-like robust column and its footnote. Not a
hypervolume number; nobody watching knows what one is.

**Experimental comparison.** `[PENDING — STUDENT]`. If the coupon experiment has been run by
the time this is recorded, it gets its own beat between 6 and 7, from
`experiments/thermal_coupon/results/`, and beat 7's sentence about the laboratory changes.

---

## Beat 7 — what this is not (3:45–4:00)

**Visual.** The limitations block from the README, plain text, held on screen long enough to
read.

**Spoken (final, not to be rushed or cut).**

> To be clear about what this is. The drag comes from inviscid, perfect-gas CFD on a coarse
> mesh, checked against published values on a sphere at two Mach numbers and nowhere else,
> and that check first came back limited before a restart rule I wrote afterwards turned it
> into a pass. Nothing has been measured in a laboratory, and nobody outside the project has
> reviewed it. Several of the constraint limits are engineering placeholders,
> and one of them, the deceleration limit, matches no document I could find; the documented
> alternative would empty the feasible region entirely, and that is an open decision, not a
> setting.
>
> And most of the code was written with AI assistance. That is recorded line by line, with
> which parts I have read and which I have not.
>
> This is a model prediction inside a set of assumptions I have written down. It says where
> the interesting trade lives. It does not say anything about a real vehicle.

---

## Production notes

- **Show real terminals.** A recording of `make test` finishing is worth more than an
  animation of a test suite.
- **Every figure comes from `reports/figures/`.** Nothing is redrawn for the video; if a
  figure is not good enough for the video it is not good enough for the paper either.
- **Voice over slides, not a talking head throughout.** A face on screen for beats 1 and 7 is
  enough.
- **No music under beats 3 and 7.** They are the beats with the substance.
- **Captions.** Numbers are misheard. Every quantity on screen as text.
- **Run time.** If it goes past 5:00, cut beat 3 down to the conduction number alone. Do not
  cut beat 5 and do not cut beat 7.
