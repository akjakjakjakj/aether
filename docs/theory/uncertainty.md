# Uncertainty propagation and robust design

*Written to be defended without this repository open. If you are asked "what does your
uncertainty analysis actually mean?", the answer is in here, and it is not "I ran a Monte
Carlo".*

---

## 1. The question this answers

Every number this project has produced so far is a **point prediction**: put one capsule
into one atmosphere and get one peak bondline temperature. The baseline design's is
494.8 K. The allowable is 450 K, so the baseline fails — cleanly, decisively, with a
number.

But the model that produced 494.8 K contains a conductivity that is a placeholder, an
atmosphere table that is interpolated above 86 km, a heating correlation whose own authors
report a 3.3% average fit error, and an effective nose radius that two NASA reports
disagree about by 20%. The honest version of that sentence is not "the bondline reaches
494.8 K". It is:

> Under the assumptions declared in `ASSUMPTIONS.md`, and with the input spreads declared
> in `configs/uncertainty.yaml`, the model predicts a bondline peak whose 95th percentile
> lies in a band, and whose probability of exceeding the allowable is p with a confidence
> interval.

Getting from the first sentence to the second is what M7 is.

---

## 2. Two kinds of not-knowing, and why they must not be mixed

This is the single most important idea in the milestone, and it is the one a viva will
push on.

### Aleatory uncertainty — the world varies

The atmosphere on entry day is not the U.S. Standard Atmosphere. It is a few percent
denser or thinner at 40 km and, by the measurements in the 1966 Standard Atmosphere
Supplements, can be tens of percent off at 110 km. The as-built vehicle is not exactly
350 kg. The de-orbit burn does not deliver exactly −3.000°.

Fly the mission again and you get a **different draw**. No amount of further study
removes this. It is a property of the world, and the only response to it is **margin**.

> *aleatory*, from Latin *alea*, a die. The roll.

### Epistemic uncertainty — we do not know

NASA TN D-5121 (Ellison, 1969) and NASA TM X-1067 (Zoby & Sullivan, 1965) both measured
the stagnation velocity gradient of a blunt spherical segment. Ellison states, in his own
words, that they disagree "about 20 percent" at the shape ratio where this project's
Pareto front sits. One of them is closer to right. **Which one does not change between
flights.** Fly the mission a thousand times and the answer is the same every time — we
just do not know what it is.

This is ignorance, and the response to it is not margin. It is **evidence**: open the
third paper, run the experiment, do the CFD. Epistemic uncertainty is the kind you can
buy your way out of.

> *epistemic*, from Greek *epistēmē*, knowledge. Ours, or the lack of it.

### Why mixing them is a real error, not a pedantic one

Suppose the bondline's spread is 18 K, and suppose you report "σ = 18 K, so 3σ margin is
54 K, so design to 396 K". You have just done two things wrong:

1. You have treated a **band between two documents** as though it were a bell curve.
   There is no frequency here to be normal or not. Saying "the effective nose radius is
   normally distributed" is a claim about the world that nobody has made and nobody could
   test.
2. You have thrown away the **actionable part of the answer**. If 99% of that 18 K is
   epistemic, then adding 54 K of margin is the expensive way to solve a problem that a
   week in a library would solve properly.

So M7 carries them separately all the way to the outputs. In
`configs/uncertainty.yaml` every input is labelled `aleatory` or `epistemic`, and the
labelling is a modelling decision with reasons written next to it. For example
`tps_conductivity` is labelled **epistemic**, not aleatory, because A-TPS-7 says the
material properties are placeholders "not the properties of any specific qualified TPS
material" — the uncertainty is not batch-to-batch variability of a known insulator, it is
not knowing which insulator this is.

---

## 3. How the two are kept apart: nested sampling and the p-box

A **nested** sample does this:

```
for each of E epistemic branches:            # pick one state of the world's unknowns
    for each of A aleatory draws:            # ...and roll the dice A times inside it
        evaluate the design
```

with the **same A aleatory draws reused in every branch** (see §6). That gives E complete
output distributions instead of one. Plot them all as cumulative distributions on the same
axes and you get a **probability box**, or *p-box*:

```
  P(bondline < T)
   1 |            ,--,   ,--,   ,--,
     |           /   |  /   |  /   |         <- E curves, one per epistemic branch
     |          |    | |    | |    |
     |         /     |/     |/     |
   0 +--------'------'------'------'-------> T
              |<-->|        |<--------->|
            width of        gap between
            one curve       the curves
           = VARIABILITY   = IGNORANCE
```

* The **width of any single curve** is aleatory. That is what a real fleet of vehicles
  would scatter over, if we knew the model exactly.
* The **horizontal gap between the curves** is epistemic. It is not scatter. It is the set
  of answers the model gives depending on which report is right, and it would collapse to
  nothing the day someone settles the question.

`reports/figures/M7_pbox.png` is exactly this plot, and it is the figure to put in front
of a reviewer, because it makes the distinction visible without an argument.

### The one place they are combined, and the sentence that has to go with it

The report also prints a pooled mean and standard deviation, because people ask for them.
Those come from the **law of total variance**:

$$\operatorname{Var}(Y) \;=\; \underbrace{\mathbb{E}_e\!\left[\operatorname{Var}_a(Y \mid e)\right]}_{\text{aleatory}} \;+\; \underbrace{\operatorname{Var}_e\!\left[\mathbb{E}_a(Y \mid e)\right]}_{\text{epistemic}}$$

which is an exact identity — no approximation. But notice what it does: it **adds the two
in quadrature**, and to do that at all you have to have sampled the epistemic inputs from
a distribution, i.e. to have decided that "one of these two reports is right, we don't
know which" *is* a 50/50 probability. That is a subjective-probability reading. It is a
defensible one, and it is the only way to get a single number out, but it is a choice and
the code says so out loud:

> *"aleatory and epistemic are combined by the law of total variance, i.e. IN QUADRATURE.
> That is exact for the sampled mixture and is stated explicitly because it is only
> meaningful if the epistemic band is read as a probability distribution — see `band` for
> the view that is not."*
> — `src/aether/uncertainty/propagate.py`

**If a reviewer asks you one question about M7, it will be this one. The answer is: the
p-box is the primary result; the pooled statistics are a convenience and the report says
which assumption buys them.**

---

## 4. Why a percentile and not a mean

The mean bondline temperature is the temperature of **no vehicle**. Half the fleet is
hotter than it. A design that is safe on average is a design that fails half the time.

So the design quantity M7 reports and optimises is the **95th percentile**: the value
exceeded on one entry in twenty. Two properties matter:

* **It is a value of the output, not a statistic about it.** "The 95th percentile bondline
  is 428 K" is a statement in kelvin that you can compare directly with a 450 K allowable.
  "σ = 14 K" is not.
* **It respects skew.** Peak heat flux is not symmetric about its mean — the trajectory
  couples nonlinearly, so the upper tail is longer than the lower. A mean-plus-2σ rule
  would understate it. A percentile reads the actual tail.

The mean and the standard deviation are still reported, as context. They are not what
anything is decided on.

---

## 5. Chance constraints: "feasible" is a probability

The nominal optimiser asks: *is `max_g` below 12?* That is a yes/no question about one
number.

Under uncertainty the same design gives a different `max_g` on every draw, so the question
becomes: *on what fraction of draws is it above 12?* A **chance constraint** puts a limit
on that fraction:

$$P(\text{max\_g} > 12\,g) \;\le\; \alpha, \qquad \alpha = 0.05 \text{ (declared in config, before the run)}$$

This changes which designs exist. The M4 joint-knee design clears the g limit nominally by
a margin of a few percent — comfortably feasible by the old question. Put the declared
uncertainty on it and it can violate on a noticeable share of draws. Under a chance
constraint it is **not feasible**, and the robust optimiser will not return it.

### Two traps, both of which this implementation handles explicitly

**Trap 1 — a design that does not finish.** Some draws produce no physics at all: the
trajectory skips back out of the atmosphere, or the integrator times out. Those are
counted as **violations of every chance constraint** — a vehicle that does not complete an
entry has not satisfied anything — and reported separately so you can see which kind of
failure it was. Dropping them would quietly improve every probability.

**Trap 2 — the resolution of the inner sample.** With *S* inner draws, the estimated
probability can only ever be 0, 1/S, 2/S, … So with S = 32 and α = 0.05, the rule is
really **"at most 1 of 32 draws may violate"**; and if you had set α = 0.02, it would
silently mean **zero violations**, which is a far harsher requirement than 2% sounds. The
code computes and prints that translation (`RobustSettings.effective_chance_rule`) rather
than letting a reader assume α is met continuously.

---

## 6. Why 0 out of 500 is not zero

Suppose 500 draws produce no violation at all. It is tempting to write "P(violation) = 0".
That is false, and it is the most common way an uncertainty study overclaims.

The honest statement comes from a **binomial confidence interval**. Two are computed:

**Wilson score interval** — for $k$ violations in $n$ draws with $\hat{p} = k/n$:

$$\text{centre} = \frac{\hat{p} + z^2/2n}{1 + z^2/n}, \qquad
\text{half-width} = \frac{z}{1 + z^2/n}\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}$$

At $k = 0$, $n = 500$, 95% confidence, this gives an upper limit of about **0.57%**.

**Clopper–Pearson (exact)** — at $k = 0$ the upper limit is exactly $1 - \alpha^{1/n}$,
which for $n = 500$ is **0.597%**. This is the closed form behind the engineer's
**rule of three**: with no events in $n$ trials, the rate is below roughly $3/n$.

Both are printed. So the sentence the report generates is:

> "0 of 500 draws violated it, i.e. below 0.57% at 95% confidence — not zero"

Note that the naive (Wald) interval, $\hat{p} \pm z\sqrt{\hat{p}(1-\hat{p})/n}$, collapses
to the single point 0 when $k = 0$. That is precisely the failure this section exists to
prevent, which is why Wilson is the default rather than the textbook-first Wald.

**The practical consequence:** to demonstrate P(violation) < 0.1% you need of order
3000 samples, not 500. The report states the sample size it used and the bound that
follows from it, and does not claim a smaller number than the sample supports.

---

## 7. Which uncertainty to attack: variance attribution

Once there is a spread, the next question is which input made it. **Sobol' indices**
answer it by variance decomposition:

* $S_i$ — **first order**: the fraction of the output variance that would disappear if
  input $i$ alone were pinned down.
* $S_{T_i}$ — **total order**: the same, *plus* everything $i$ does through interaction
  with the other inputs. $S_{T_i} \approx 0$ is the only safe licence to ignore an input;
  $S_i \approx 0$ alone can hide a variable that matters only in combination.

Two things about how they are read here:

**An index on an epistemic input is a sensitivity, not a share of nature.** $S_T = 0.86$
for `tps_conductivity` does not mean 86% of the world's variability comes from
conductivity — conductivity does not vary. It means 86% of the *modelled* spread would
vanish if we knew what the material was. That is still the useful number: it ranks what to
go and measure. The report labels every row with its input's kind so the two readings are
never confused.

**A zero index can be geometry, not a bug.** On the reference capsule, nose radius equals
body radius: the forebody *is* a hemisphere, $K = R_b/R_n = 1$. There the two NASA sources
agree identically, by Zoby & Sullivan's own eq. (5) — $R_{\text{eff}} = R_b = R_n$
whichever table you read — so the model-form switch can move nothing at all and its index
is exactly zero. On the M4 front, $K \approx 0.42$, where the sources disagree by ~20%,
and it is expected to dominate. The report computes $K$ and says this rather than leaving
a reader to wonder.

**One inherited trap.** The Saltelli first-order estimator multiplies by $f(B)$. For an
output with a ~400 K mean and a few tens of kelvin of spread, that product's variance is
dominated by the mean, and the confidence intervals come out wider than $[0, 1]$ — which
is impossible for a variance fraction. The indices are invariant to a constant shift, so
the output is **mean-centred before estimation**. This repository hit that once already
(`docs/negative_results.md` NR-16); M7 imports the fixed estimator rather than
re-deriving it.

---

## 8. Robust optimisation, and the shortcut that makes it possible

### The problem

$$\min_x \;\; \left[\;Q_{95}\big(q''_{\text{peak}}(x,\xi)\big),\;\; Q_{95}\big(T_{\text{bond}}(x,\xi)\big)\;\right]
\quad\text{s.t.}\quad P\big(g_j(x,\xi) > 0\big) \le \alpha_j$$

where $x$ is the design and $\xi$ is the uncertainty draw. Compare it with the nominal
problem, which is the same thing with $\xi$ frozen at its nominal value and the
constraints as yes/no tests.

### Why it is expensive, and the two things that make it affordable

Every candidate now costs an inner sample instead of one evaluation. NSGA-II with a
population of 24 over 40 generations is ~960 candidates; at 1000 inner draws each that is
960,000 evaluations per seed, or about **ten hours per seed** on this machine. That is out
of reach.

**Shortcut 1 — a modest inner sample.** $S = 32$ draws per candidate rather than
thousands.

**Shortcut 2 — common random numbers (CRN).** *Every* candidate, in *every* generation,
is evaluated on **the same 32 draws**. This is the important one, and the reason is worth
understanding properly:

> An optimiser never needs to know a design's absolute 95th percentile. It needs to know
> whether design A is better than design B. Under CRN, both are judged on the same
> weather, so the *difference* between them is estimated far more precisely than either
> value is. Formally, $\operatorname{Var}(A - B) = \operatorname{Var}(A) +
> \operatorname{Var}(B) - 2\operatorname{Cov}(A,B)$, and CRN makes the covariance large
> and positive, which is exactly what shrinks the variance of the comparison.

CRN has a second, free benefit in this implementation: because the uncertainty draw is
carried as a coordinate of the design vector (`src/aether/uncertainty/space.py`), a design
the optimiser re-proposes is answered from the evaluator's cache and costs **nothing** to
re-test — and the log records it as a cache hit, so the saving is visible rather than
assumed.

### Verifying the shortcut rather than asserting it

Both shortcuts are approximations. A 95th percentile estimated from 32 draws is noisy and
biased inward, and CRN buys precision on the *comparison* at the price of correlated error
on the *level*. So when the front is finished, `verify_shortcut` takes a subset of it,
re-scores each design under **full, independent Monte Carlo** — 1000 fresh draws, a
different seed, no CRN — and reports three things against tolerances declared in the
config **before** the run:

| Question | Statistic | Why it is asked separately |
|---|---|---|
| Is the robust objective biased? | mean signed relative difference | A small-sample quantile is biased inward by construction; the question is whether it is small against the span the front covers. |
| Is the **ranking** preserved? | Spearman rank correlation | This is the one the shortcut actually has to pass. A biased estimator that ranks correctly still steers the optimiser correctly. |
| Are the violation probabilities right? | max absolute difference per constraint, and how many feasibility verdicts flipped | A chance constraint decides which designs *exist*, so an error here changes the feasible set, not just its position. |

If any tolerance is missed, the report says so in as many words and states that the front
must be read as the output of an unverified shortcut rather than as a converged robust
optimum. The check has its own tests, which confirm that it **fails** on an injected bias,
on a reversed ranking, and on a wrong probability — a verification that cannot fail is a
rubber stamp.

---

## 9. What nominal-versus-robust actually shows

Three comparisons the report computes, and what each one is for:

**How far is a nominal optimum from its own constraint?** A design optimised without
uncertainty pushes right up against whatever stops it — that is what optimisers do. The
M4 designs sit within a few percent of a binding constraint at their nominal point. That
margin is not a safety factor; it is the residue of a search that had no reason to leave
any.

**Which nominal designs are fragile?** For each, the report prints P(any constraint
violated) with its interval. A design that is nominally feasible and violates on a
meaningful share of draws is **fragile**, and spec §28 forbids selecting it without
discussion. The report names them.

**What does robustness cost?** The robust optimum is, by construction, worse in nominal
performance than the nominal optimum — it has spent some objective buying tail behaviour.
The report prints that penalty in the objectives' own units and as a fraction. That number
is the honest price of the recommendation, and quoting the robust design's nominal
performance without it would be the same overclaim in the other direction.

---

## 10. What this analysis does **not** cover

An uncertainty study bounds only what is in its inventory, so the inventory's gaps are
part of the result.

* **Model-form error that has no distribution.** Gate G2′ — Sutton–Graves' catalycity,
  hot-wall and radiation assumptions — is `LIMITED` and is **not** in the inventory.
  Catalycity alone is reported at roughly a factor of two. A-TPS-2's
  temperature-independent conductivity, A-TPS-3's adiabatic back face, A-HEAT-4's
  stagnation-point-only treatment and A-TRAJ-1's non-rotating Earth are structural
  choices with no spread attached. **The output distributions are a lower bound on the
  real uncertainty.**
* **Most of the inventory is engineering judgment.** Seven of nine active inputs are
  tier T3. The two that are T1 — the effective-nose-radius model form and the
  Sutton–Graves constant — are the ones this project measured about itself, and they are
  not the small ones.
* **At Fidelity 0 the C_D uncertainty is a guess.** The four sourced Fidelity-1 terms (GP
  predictive σ with its measured 1.21 inflation — `cfd_surface_v2`, current; `cfd_surface_v1`
  used 1.65 — the M2 discretisation band, the base-drag band, the declared perfect-gas
  half-band) do not exist when the aerodynamics are a constant, and are replaced by one
  unsourced ±10% band. That substitution is not equivalent and the report says which branch
  it took.
* **The deceleration limit is an open decision.** A-LIM-1b establishes that 12 g
  corresponds to *no* documented sustained-g curve, and that adopting the NASA-STD-3001
  deconditioned curve would empty the feasible region. Every chance constraint on `max_g`
  is therefore a statement about a placeholder.
* **Above 86 km, even the aleatory input is judgment.** No document opened in the sourcing
  pass states a 1-σ density dispersion above 86 km. Those rows convert primary *observed
  ranges* into a σ proxy — this project's step, not any source's — and NR-14 measured that
  5–20% of a feasible design's heat load comes from exactly that band. M7 quantifies the
  consequence of a known weakness; it does not remove it.

---

## 11. Defending this in a viva — the questions and the short answers

**"Why not just use 3σ?"**
Because two of the largest terms are not σ's. A 20% disagreement between two NASA reports
is a band, and a band has no standard deviation. Multiplying a made-up σ by 3 produces a
number with no interpretation.

**"Your epistemic share is 98%. Isn't that suspicious?"**
It is the expected answer for this model at this stage, and it is the useful one. The
aleatory inputs are a few percent on mass and density; the epistemic ones are a ±15% band
on a placeholder conductivity and a 20% disagreement about the nose radius. It says the
next thing to buy is evidence, not margin — and §7 names which evidence.

**"Why 95th percentile and not 99th?"**
Declared before the run, in config, and changeable there. 95 is what the inner sample can
estimate with 32 draws; a 99th percentile would need a much larger inner sample and the
verification would have caught it if it did not.

**"How do you know the shortcut works?"**
It was measured against full independent Monte Carlo on a subset of the finished front,
against tolerances declared beforehand, on three separate criteria. The check has tests
proving it fails when it should.

**"What if the numbers change?"**
Every interpretive sentence in the report is computed from the result files. Re-running
the study rewrites the verdicts; there is no prose asserting a result that could go stale.

---

## Builds on

- `docs/theory/effective_nose_radius.md` — the two primaries, their disagreement, and why
  it is the dominant heating term.
- `docs/theory/sutton_graves_constant.md` — where ±4% comes from.
- `docs/validation/sourcing_report.md` — the tiering scheme and every source behind the
  inventory.
- `docs/negative_results.md` NR-14 (heat load above 86 km), NR-15 (the nose-radius lever),
  NR-16 (the uncentred Sobol' estimator).
- `ASSUMPTIONS.md` — A-UQ-*, and the assumptions the inventory does *not* cover.

## Leads to

- `reports/milestones/M7_uncertainty_robust.md` — the generated result.
- `configs/uncertainty.yaml` — the declaration every number here refers to.
- `docs/defense_questions.md` — §11 above, in question form.
