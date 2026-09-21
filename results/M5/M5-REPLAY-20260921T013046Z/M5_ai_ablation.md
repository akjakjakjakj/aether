# M5 — AI vs conventional optimiser ablation

> **fidelity: 1** · aerodynamic model: `cfd_surface_v2` · generated file, do not edit by hand
>
> ablation run `M5-REPLAY-20260921T013046Z` (git `eac22c7`, dirty tree, evaluator source hash `4f428168c6481bbb`) · active variables from DOE run `M4-DOE-20260920T204844Z` · **replay of `M5-ABL-20260920T211134Z`**

*Produced from an uncommitted working tree; the config snapshot beside the result is the authoritative record of what ran.*

**Read this first.** Fidelity 1, aerodynamic model `cfd_surface_v2`, 4 active design variables (`diameter_m`, `bluntness_ratio`, `cone_half_angle_deg`, `flight_path_angle_deg`) taken from the DOE screening named above. **CFD solver calls made by this study, all methods and seeds: 0.** 4038 paid evaluations returned physics through the CFD-*derived* drag surface `cfd_surface_v2` (the evaluator labels those fidelity > 0); that is a count of surface look-ups, not of CFD runs. An optimiser comparison is a statement about the methods ON THIS MODEL, under the limits and variable ranges in the config snapshot; it is not evidence about how the methods would rank on a different model, and nothing here is a statement about a real vehicle.

## 1. What was asked, and what was declared before the run

Spec §24/§46: compare an LLM engineering agent against conventional optimisers under matched evaluation budgets, and do not claim AI superiority unless it is measured. The rule for "measured" was written into `configs/ai_ablation.yaml` before any method ran:

- **metric:** normalised hypervolume of the feasible set after 50, 100, 200 evaluations;
- **comparator:** at each checkpoint, the non-LLM method with the highest mean hypervolume ("best conventional") — beating only the LHS floor does not count;
- **"AI helped"** iff mean HV(`ai_agent`) − mean HV(comparator) ≥ 0.005 **and** the one-sided exact permutation test gives p < 0.05 after Holm correction across the checkpoints; **"AI hurt"** is the mirror image; anything else is **"no measured difference"**.

## 2. Set-up

Every method received exactly **200 evaluations per seed**, seeds 37, 41, 59, 67, 73, through the same `BudgetedEvaluator` as M4 (A-OPT-3: every distinct design costs 1, including geometrically invalid ones; a repeat is served from cache, logged, and costs 0). Active variables: `diameter_m`, `bluntness_ratio`, `cone_half_angle_deg`, `flight_path_angle_deg`. Hypervolume reference point (2.5e+06 W/m², 450 K) — M4's, read from the same config file, not copied.

**Why 200 × 5 and not M4's 1000 × 7.** The LLM is the scarce resource: the study is hard-capped in code at 80 LLM calls (12 per seed). M4's 1000-evaluation runs remain the conventional reference for what a large budget reaches.

| method | kind | what it is |
|---|---|---|
| `lhs_search` | lhs_search | one seeded Latin Hypercube of the whole budget; no learning. M4 code, unchanged. Settings: — |
| `nsga2` | nsga2 | pymoo NSGA-II, constraint-domination. M4 code, unchanged; population from the settings column. Settings: {'population_size': 40} |
| `nsga2_pop20` | nsga2 | pymoo NSGA-II, constraint-domination. M4 code, unchanged; population from the settings column. Settings: {'population_size': 20} |
| `bo_parego` | bo_parego | GP per objective and per constraint margin plus a GP validity classifier, trained only on evaluated candidates; ParEGO random Tchebycheff scalarisation, Monte-Carlo EI × probability of feasibility, batched. Settings: {'n_initial_per_variable': 5, 'batch_size': 10} |
| `ai_agent` | ai_agent | LLM proposes batches from a structured table; strict schema; every proposal has a parent and a rationale. Settings: {'n_initial_per_variable': 5, 'rounds': 9} |
| `ai_adaptive` | ai_adaptive | the same agent plus the fidelity-promotion hook. **NOT YET MEANINGFUL — no second fidelity available.** Settings: {'seeds': [37, 41], 'n_initial_per_variable': 5, 'rounds': 9} |

`nsga2` runs a population of 40: 5 full generations in 200 evaluations.
`nsga2_pop20` runs a population of 20: 10 full generations in 200 evaluations.
Where two NSGA-II populations are listed, both were declared before the run so that NSGA-II is not judged only on a setting chosen for M4's larger budget. `bo_parego` and the agent start from the **same** seeded initial Latin Hypercube, seed for seed (size = `n_initial_per_variable` × the number of active variables), which is what makes their comparison paired.

**Why ParEGO and not expected hypervolume improvement** (a design choice, made before the run). Batched EHVI in a constrained box with unevaluable regions needs a greedy fantasy loop or a joint batch integral; random Tchebycheff weights give batch diversity at one GP fit per iteration, and the GPs model the objectives themselves, so the models that drive the search are the ones validated in §5.

**Invalid geometry — no method gets it for free.** The analytic `CapsuleGeometry.validate()` rule is not given to any optimiser as a pre-filter or repair step: an invalid design costs 1 for everyone (A-OPT-3), the Bayesian optimiser learns the valid region from the designs that came back invalid, and an LLM proposal that turns out invalid is charged like any other.

**What the LLM saw, and the asymmetries that remain.** Structured JSON only: the active variables' names, units and bounds; the frozen parameters; objective and constraint *names*; the hypervolume reference point; the budget left; a table of the feasible non-dominated designs, the nearest misses, the most recent evaluations and recent geometry failures, each with metrics, constraint margins and the evaluator's failure message; and a digest of its own earlier rounds. It was told neither the equations of the model nor anything M4 found. The CLI was run in an empty temporary directory with tools, MCP servers, hooks, skills and CLAUDE.md discovery disabled, so it could not read this repository. Three asymmetries are part of what is being measured and are stated rather than removed: (1) **prior knowledge** — the variable and metric names alone tell an LLM trained on the aerospace literature that blunter and larger means cooler; the other optimisers see numbers without names; (2) **failure messages** — the geometry validator's text says which variable to move ("increase cone_half_angle_deg …"), which the LLM can read and the numeric optimisers cannot; (3) **contamination** — the model may have seen blunt-body entry optimisation problems like this one in training. A win by the agent is therefore a win for *priors plus data*, not for data alone.

## 3. Results (spec §46 table)

| method | seeds | total evaluations / seed | drag-surface evaluations / seed (fidelity > 0) | CFD solver calls | feasible found (mean) | HV @ final, mean ± s.d. | min – max | front size (mean) | design diversity, all / feasible | wall s / seed (mean) | LLM calls | LLM tokens in / out | proposals rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `lhs_search` | 5 | 200 | 90 | 0 | 8.2 | **0.2524 ± 0.0171** | 0.2332 – 0.2757 | 2.2 | 0.780 / 0.404 | 2 | 0 | — | — |
| `nsga2` | 5 | 200 | 161 | 0 | 60.4 | **0.2803 ± 0.0253** | 0.2569 – 0.3186 | 3.4 | 0.645 / 0.326 | 4 | 0 | — | — |
| `nsga2_pop20` | 5 | 200 | 177 | 0 | 106.6 | **0.2753 ± 0.0381** | 0.2156 – 0.3082 | 3.8 | 0.492 / 0.258 | 5 | 0 | — | — |
| `bo_parego` | 5 | 200 | 121 | 0 | 103.0 | **0.3520 ± 0.0011** | 0.3506 – 0.3530 | 7.8 | 0.602 / 0.445 | 19 | 0 | — | — |
| `ai_agent` | 5 | 200 | 184 | 0 | 163.8 | **0.3556 ± 0.0000** | 0.3555 – 0.3556 | 72.4 | 0.307 / 0.178 | 20 | 47 | 704145 / 816076 | 37 of 937 |
| `ai_adaptive` | 2 | 200 | 188 | 0 | 161.5 | NOT YET MEANINGFUL — no second fidelity available (0.3556; every candidate at Fidelity 1 (`cfd_surface_v2`), 0 promotions to a new CFD case) | 0.3556 – 0.3556 | 75.5 | 0.306 / 0.182 | 26 | 20 | 303254 / 319308 | 24 of 384 |

s.d. is the sample standard deviation over seeds. *Design diversity* is the mean pairwise Euclidean distance between a run's evaluated designs in the unit cube of the active variables (all paid designs / feasible ones only), averaged over seeds: large = explored widely, small = concentrated. *Drag-surface evaluations* counts paid evaluations that returned physics through a CFD-derived drag surface (evaluator fidelity label > 0); the rest of the budget went to designs refused before any physics. It is not a count of CFD runs - *CFD solver calls* is, and counts promotions to a new CFD case granted by the adaptive-fidelity hook (agent_log.json fidelity_decisions); the M5 harness has no other path that runs a CFD solver. Wall time for the LLM methods is dominated by model latency and was measured with several seeds running concurrently, so it is an upper bound per seed, not a CPU cost; the conventional methods ran one seed at a time on the same 6-process pool. All methods and seeds pooled: 234 front designs, normalised hypervolume 0.3556.

No other run's recorded window overlaps this one's (2026-09-21T01:30:46+00:00 to 2026-09-21T01:34:16+00:00); machine load was still not logged, so wall times are indicative only.

**Against the large-budget reference.** M4's NSGA-II (run `M4-OPT-20260920T205252Z`) reached 0.3467 ± 0.0055 after 1000 evaluations (7 seeds). Determinism check: M5's `nsga2` runs reproduce the first 200 evaluations of M4's runs on the shared seeds to within 0.0e+00 in hypervolume.

![hypervolume vs evaluations](figures/M5_hypervolume.png)

![per-seed hypervolume](figures/M5_hypervolume_per_seed.png)

![fronts](figures/M5_fronts.png)

![budget use](figures/M5_budget_use.png)

## 4. Statistical comparison

Samples are the per-seed hypervolumes (n = 5 per method). No normality is assumed. **Rank test:** exact two-sample permutation test on rank sums (the exact Mann–Whitney test, valid with ties), all C(2n, n) relabellings enumerated. **Signed-rank:** exact Wilcoxon on seed-wise differences, reported only against `bo_parego`, the one method that shares the agent's initial design seed for seed. **A12:** Vargha–Delaney probability that a random agent run beats a random comparator run (0.5 = none, 1 = always).

**Power, stated plainly.** With n = 5 per method the smallest attainable one-sided rank-test p is 1/252 = 0.0040 — reachable only when every run of one method beats every run of the other — and the smallest attainable *two-sided* signed-rank p is 2/32 = 0.0625, which can never reach 0.05. The rule has two legs - an effect-size threshold and a significance level - and a "no measured difference" can come from either; which one is stated per cell below, from the legs as evaluated. Effect sizes and the raw per-seed values are given so the reader is not left with a p-value alone.

At 200 evaluations the agent is ahead of `bo_parego` by 0.0036 (A12 = 1.00; Holm-adjusted p = 0.0119). The permutation test **rejects** (p < 0.05); the verdict is "no measured difference" because the mean difference is under the pre-declared practical threshold of 0.005 - the rule's effect-size leg, not its significance leg. The study *could* tell the two apart here, by an amount declared in advance to be too small to count.

### Pre-declared comparison: agent vs best conventional

| evaluations | best conventional (mean HV) | agent mean HV | difference | A12 | rank test p (agent better) | Holm | p (agent worse) | Holm | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 50 | `bo_parego` (0.3145) | 0.3428 | +0.0283 | 0.88 | 0.0278 | 0.0278 | 0.9841 | 1.0000 | **AI helped** |
| 100 | `bo_parego` (0.3465) | 0.3550 | +0.0085 | 1.00 | 0.0040 | 0.0119 | 1.0000 | 1.0000 | **AI helped** |
| 200 | `bo_parego` (0.3520) | 0.3556 | +0.0036 | 1.00 | 0.0040 | 0.0119 | 1.0000 | 1.0000 | **no measured difference** |

### Agent vs every non-LLM method (descriptive; not the declared test)

| evaluations | comparator | comparator mean HV | agent − comparator | A12 | rank test p, two-sided | seeds agent better | signed-rank p, two-sided |
|---|---|---|---|---|---|---|---|
| 50 | `lhs_search` | 0.1342 | +0.2086 | 1.00 | 0.0079 | — | — |
| 50 | `nsga2` | 0.2272 | +0.1156 | 1.00 | 0.0079 | — | — |
| 50 | `nsga2_pop20` | 0.1248 | +0.2180 | 1.00 | 0.0079 | — | — |
| 50 | `bo_parego` | 0.3145 | +0.0283 | 0.88 | 0.0556 | 4 of 5 | 0.1250 |
| 100 | `lhs_search` | 0.2131 | +0.1418 | 1.00 | 0.0079 | — | — |
| 100 | `nsga2` | 0.2417 | +0.1132 | 1.00 | 0.0079 | — | — |
| 100 | `nsga2_pop20` | 0.2256 | +0.1293 | 1.00 | 0.0079 | — | — |
| 100 | `bo_parego` | 0.3465 | +0.0085 | 1.00 | 0.0079 | 5 of 5 | 0.0625 |
| 200 | `lhs_search` | 0.2524 | +0.1031 | 1.00 | 0.0079 | — | — |
| 200 | `nsga2` | 0.2803 | +0.0752 | 1.00 | 0.0079 | — | — |
| 200 | `nsga2_pop20` | 0.2753 | +0.0802 | 1.00 | 0.0079 | — | — |
| 200 | `bo_parego` | 0.3520 | +0.0036 | 1.00 | 0.0079 | 5 of 5 | 0.0625 |

These rows are not corrected for multiplicity and are not the basis of any claim; they are here so that a reader can see every comparison, not only the one the rule selected.

## 5. Surrogate validation (spec §25)

Two held-out tests, both on designs the model had never seen, both in the modelled space (log₁₀ for heat flux, where the GP's Gaussian assumption is made).

**(a) Static.** For each seed, GPs were trained on that seed's `lhs_search` designs that returned physics and scored on the next seed's — evaluations the ablation had already paid for. Test points are split by whether they lie inside the convex hull of the training inputs.

| output | region | n | RMSE | MAE | R² (median over splits) | z s.d. (1 = calibrated) | coverage of the 50 / 68 / 90 / 95 % interval |
|---|---|---|---|---|---|---|---|
| `peak_heat_flux_w_m2` (log₁₀) | inside hull | 215 | 0.00219 | 0.00149 | 1.000 | 0.78 | 0.68 / 0.81 / 0.93 / 0.96 |
| `peak_heat_flux_w_m2` (log₁₀) | outside hull | 233 | 0.00664 | 0.00418 | 1.000 | 1.13 | 0.57 / 0.72 / 0.86 / 0.91 |
| `peak_bondline_temperature_k` | inside hull | 215 | 0.357 | 0.246 | 1.000 | 0.58 | 0.76 / 0.84 / 0.93 / 0.97 |
| `peak_bondline_temperature_k` | outside hull | 233 | 1.52 | 0.85 | 0.999 | 0.94 | 0.61 / 0.76 / 0.90 / 0.94 |
| `margin__max_g` | inside hull | 215 | 0.00514 | 0.00361 | 0.999 | 1.07 | 0.52 / 0.66 / 0.82 / 0.92 |
| `margin__max_g` | outside hull | 233 | 0.0117 | 0.00759 | 0.998 | 1.50 | 0.49 / 0.66 / 0.84 / 0.88 |
| `margin__peak_bondline_temperature_k` | inside hull | 215 | 0.000792 | 0.000547 | 1.000 | 0.58 | 0.76 / 0.84 / 0.93 / 0.97 |
| `margin__peak_bondline_temperature_k` | outside hull | 233 | 0.00338 | 0.00189 | 0.999 | 0.94 | 0.61 / 0.76 / 0.90 / 0.94 |
| `margin__heatshield_mass_fraction` | inside hull | 215 | 0.00264 | 0.00124 | 1.000 | 0.53 | 0.87 / 0.93 / 0.99 / 0.99 |
| `margin__heatshield_mass_fraction` | outside hull | 233 | 0.0149 | 0.00556 | 1.000 | 1.13 | 0.76 / 0.81 / 0.90 / 0.92 |

Validity classifier (does the design return physics at all), mean over 5 splits: accuracy 0.978, Brier score 0.018, against a base rate of 0.45 valid — always guessing the majority class would score 0.552.

**(b) Prospective.** Inside `bo_parego`, every design's prediction was logged *before* it was evaluated (900 designs over all seeds). This is the test scored where the optimiser actually went. **746 of 900 (83%) of those picks lay outside the convex hull of the training data** and were flagged as extrapolations at the time they were made.

| output | region | n | RMSE | MAE | R² | z s.d. | coverage 50 / 68 / 90 / 95 % |
|---|---|---|---|---|---|---|---|
| `peak_heat_flux_w_m2` (log₁₀) | inside hull | 145 | 0.0037 | 0.00174 | 0.999 | 1.47 | 0.44 / 0.67 / 0.80 / 0.85 |
| `peak_heat_flux_w_m2` (log₁₀) | outside hull | 391 | 0.0125 | 0.00421 | 0.994 | 1.62 | 0.59 / 0.70 / 0.83 / 0.86 |
| `peak_bondline_temperature_k` | inside hull | 145 | 0.811 | 0.333 | 0.997 | 1.45 | 0.48 / 0.66 / 0.79 / 0.83 |
| `peak_bondline_temperature_k` | outside hull | 391 | 1.49 | 0.64 | 0.994 | 1.21 | 0.56 / 0.70 / 0.86 / 0.90 |
| `margin__max_g` | inside hull | 145 | 0.00392 | 0.00191 | 0.996 | 1.61 | 0.41 / 0.55 / 0.80 / 0.81 |
| `margin__max_g` | outside hull | 391 | 0.0111 | 0.00424 | 0.983 | 2.36 | 0.34 / 0.49 / 0.73 / 0.79 |
| `margin__peak_bondline_temperature_k` | inside hull | 145 | 0.0018 | 0.000741 | 0.997 | 1.45 | 0.48 / 0.66 / 0.79 / 0.83 |
| `margin__peak_bondline_temperature_k` | outside hull | 391 | 0.00331 | 0.00142 | 0.994 | 1.21 | 0.56 / 0.70 / 0.86 / 0.90 |
| `margin__heatshield_mass_fraction` | inside hull | 145 | 0.00378 | 0.00165 | 1.000 | 1.61 | 0.65 / 0.73 / 0.80 / 0.86 |
| `margin__heatshield_mass_fraction` | outside hull | 391 | 0.0186 | 0.0052 | 0.991 | 2.04 | 0.64 / 0.75 / 0.84 / 0.86 |

Validity probability on the same picks: accuracy 0.857, Brier 0.110, base rate valid 0.60.

**Extrapolation policy.** `GPSurrogate.predict` *refuses* (raises) outside the training hull by default; a number of record cannot be produced there. The acquisition function is the one caller allowed to pass `on_extrapolation="flag"`: it is buying an evaluation at that point, not trusting the prediction, and every such pick is flagged and counted above. R² is unstable when a held-out set has little variance (a general property of R², not a finding about this run), so RMSE and interval coverage are given beside it.

![surrogate calibration](figures/M5_surrogate_calibration.png)

## 6. The agent's behaviour

### `ai_agent`

- model: `claude-sonnet-5` (responses **replayed** from disk, no live call)
- LLM calls: **47** ({'ok': 47}); tokens in / out 704145 / 816076; summed call wall time 8546 s; list-price cost as reported by the CLI $10.98 (a subscription login was used; no API key)
- proposals: 937 received, 900 accepted, **37 rejected** ({'duplicate': 36, 'no_change': 1}); malformed responses 0; failed calls 0; budget spent on the LHS fallback because the agent could not fill it: 0 evaluations
- the agent's own numeric predictions (900 scored): feasibility called correctly 91% of the time (it predicted feasible 892×, 813 were); `peak_heat_flux_w_m2` MAE 4.06e+03, bias -2.44e+03; `peak_bondline_temperature_k` MAE 0.724, bias -0.498

### `ai_adaptive` — NOT YET MEANINGFUL — no second fidelity available

- model: `claude-sonnet-5` (responses **replayed** from disk, no live call)
- LLM calls: **20** ({'ok': 20}); tokens in / out 303254 / 319308; summed call wall time 3333 s; list-price cost as reported by the CLI $4.41 (a subscription login was used; no API key)
- proposals: 384 received, 360 accepted, **24 rejected** ({'duplicate': 24}); malformed responses 0; failed calls 0; budget spent on the LHS fallback because the agent could not fill it: 0 evaluations
- the agent's own numeric predictions (360 scored): feasibility called correctly 89% of the time (it predicted feasible 359×, 321 were); `peak_heat_flux_w_m2` MAE 2.59e+03, bias -698; `peak_bondline_temperature_k` MAE 0.65, bias -0.225

**Adaptive-fidelity hook — NOT YET MEANINGFUL — no second fidelity available.** The promotion policy (`src/aether/optimization/fidelity.py`; spec §26: predicted Pareto value, uncertainty, novelty, cost) was called on every accepted proposal: 360 decisions, the agent asked for a promotion (requested fidelity ≥ 1) on 7, the policy wanted to promote 40, and **0 were granted**. No promotion to a new CFD case was available to this run, so every candidate was evaluated at Fidelity 1 (`cfd_surface_v2`) - the same model as every other method - and this method's search is, by construction, the plain agent's with different LLM samples. Its hypervolume is printed only to show the plumbing ran; it is excluded from every comparison and says nothing about adaptive fidelity. The policy thresholds are placeholders until they are set against real CFD cost data.

## 7. Qualitative audit of the agent's stated mechanisms

*Hand-written after reading every round of run `M5-ABL-20260920T211134Z` (`results/M5/M5-ABL-20260920T211134Z/agent_log.json` and the raw responses beside it); the only part of this report not generated from `summary.json`.*

**What was read, and how.** The stated `mechanism` of all 67 rounds (47 `ai_agent`, 20
`ai_adaptive`) and the full `observation` / `evidence` / `mechanism` / `uncertainty` of 25 of
them (every round of seeds 37 and 41; the first three or four and the last of seeds 59, 67
and 73), from the raw responses under `results/M5/M5-ABL-20260920T211134Z/llm/`. The counts
below are produced by read-only scripts kept beside the run
(`results/M5/M5-ABL-20260920T211134Z/audit/*.py`, outputs `*.json`, verbatim text in
`rounds_digest.md`); they read `agent_log.json` and `candidates.csv` and evaluate nothing.
The LLM's text was treated as data throughout. The yardstick is what M4 established on this
physics (`M4_pareto_optimisation.md` §11, §11a): entry angle is the only variable that trades
the two objectives; diameter and bluntness are free improvements until the mass-fraction
fence and the CFD-hull edge; the cone angle decides validity, not heating; C_D at peak
heating is flat across the front; the shoulder is frozen.

### 1. Did it find the structure M4 found? Yes, in every seed, within three to five rounds

By its third to fifth call every seed states M4's §11a conclusion in its own words. Seed 37,
call 5: *"The feasible front is a one-dimensional curve traced by flight-path angle at
D~3.375-3.38 m, bluntness 1.2, cone 70 deg."* Seed 41, call 3: *"The front is closed on the
steep side by max_g … and on the large-D side by heatshield mass fraction."* It names all
three stops correctly and separately: diameter by the mass fraction (*"behaves like
1-k·D^2"*), bluntness by the drag surface's hull (*"Bluntness 1.205 and above at cone 70
fails the cd_fore convex-hull check"*), entry angle by the g-limit near −3.57°. A crude
keyword scan finds the one-parameter-front statement in 27 of 47 `ai_agent` rounds, the
mass-fraction cap in 45 and the hull or extrapolation fence in 39. The pooled `ai_agent`
fronts agree with the words: 362 front designs, all at bluntness 1.2 and cone 70°, diameter
3.380–3.38523 m, entry angle −3.57035° to −1.5°. M4's front after 1000 evaluations sat at
3.355–3.376 m, bluntness 1.15–1.199, entry angle −3.565° to −1.502°: the same corner, less
tightly parked.

### 2. Inferred from the data, or asserted from priors? Both, and it mostly says which

*From priors, and labelled as such.* The **direction** of every lever was stated in round 1,
before a seed had more than three feasible designs (seed 41 and 67 had none). Thirty-five of
47 rounds say so explicitly, 12 naming Allen–Eggers and 9 Sutton–Graves: *"This relies on
prior Allen-Eggers-type scaling, calibrated to the data"* (seed 59, call 1); *"I am relying
on ballistic-entry scaling from prior knowledge for the sign and size of some trends"* (seed
37, call 1). Those first-round proposals, made on priors plus 20 space-filling rows, already
had the direction of change right on 88 of 95 stated flux directions and 86 of 93 bondline
directions. That is the contamination point in one number, and it should be read plainly:
**the agent starts where the other optimisers have to get to.** NSGA-II and the Bayesian
optimiser see four unnamed numbers; the LLM sees the words "bluntness", "flight path angle"
and "bondline" and has read the entry-heating literature. Its lead at 50 evaluations is a
measurement of *priors plus data*, not of reasoning from data alone, and this study cannot
separate the two.

*From the data, and could not have come from anywhere else.* (i) The constraint limits,
back-computed from the margins in round 1 (12 g, 450 K). (ii) The geometric validity rule:
seeds 37, 41 and 67 each derived, in round 1, from the negative cone lengths in the
validator's failure messages, the closed form (bluntness − 0.1)·cos(cone half-angle) ≤ 0.4.
Checked against this run's log, that rule agrees with the evaluator on **all 5400 paid
designs of all methods** (1362 invalid, no false alarm, no miss). No numeric optimiser is
given that rule (A-AI-2); the agent read it off ten or eleven error messages. This is the
failure-message asymmetry the report's §2 declares, and it is large. (iii) The CFD-hull
fence, which no prior could supply: discovered from the `cd_fore` extrapolation refusals by
call 2 or 3 in every seed and then probed at 1.205, 1.21, 1.22. (iv) The numbers: the D²
mass-fraction law, ≈1.65 g per degree, ≈−18 K per metre of diameter. (v) That 1 K of
bondline is worth far more hypervolume than 10 kW/m² of flux, computed from the reference
point in the prompt in 10 rounds — the agent optimised the *meter* knowingly, which is what
it was asked to do and is also why it parks where it parks (§4).

*Asserted and not supported by this model.* *"Large cone angle raises drag"* / *"a large
blunt 70° cone gives the highest drag coefficient"* appears in a handful of rounds as a
reason for the corner. Across the space-filling data C_D at peak heating does rise with
cone angle (Spearman 0.97 in `lhs_search`), so the prior is not wrong about the box; but
C_D is never shown to the agent, and on its own front it spans 1.36439–1.36446, i.e. it
explains nothing there. M4's reading (the cone angle is held at 70° by validity and the
bound, not by drag) is the supported one. Likewise *"High cone angle also reduces heatshield
area, which buys diameter"* (seed 41) is asserted; M4's Sobol' index of cone angle on the
mass fraction is 0.0005. Neither claim changed where the agent went.

*Never said.* In 67 rounds the agent did not once question whether a limit was physically
meaningful. It treated the mass-fraction constraint as a wall to be approached to within
10⁻⁵, never as a sign that a shield weighing as much as the vehicle is not a vehicle — the
point M4 §11a makes in its first sentence. It was not told the limit's value or meaning, so
this is a limit of what it was shown as much as of the model; but an engineer reading
"heatshield_mass_fraction margin 1.5e-5" would have asked. The shoulder appears only as a
term in its geometry formula. Fidelity 1 was requested on 24 of 900 accepted proposals.

### 3. Were its predictions borne out?

Scored for every accepted `ai_agent` proposal whose parent and child both returned physics.
A direction counts as stated when the predicted change from the parent's simulated value
exceeds 0.5 % (flux) or 0.5 K (bondline); inside that band the agent is read as predicting
"about the same" (230 and 177 proposals respectively) and is not scored.

| | stated | right | wrong | right |
|---|---|---|---|---|
| peak heat flux, direction vs parent | 604 | 596 | 8 | 98.7 % |
| peak bondline temperature, direction vs parent | 657 | 649 | 8 | 98.8 % |
| both directions stated | 577 | 562 both right | 14 one, 1 neither | 97.4 % |

All 16 wrong directions are in rounds 1 and 2; from round 3 on there is not one. That is
less impressive than it looks and should not be quoted without this sentence: from round 3
most proposals are interpolations in entry angle between two evaluated neighbours on a
smooth monotone curve, where the direction is given. The median absolute error of its
numeric predictions falls from 6.9 % of flux and 3.3 K in round 1 to below 0.01 % and
about 0.02 K by round 5. The informative figure is round 1 (≈ 93 % right on priors and 20 rows).
Stated uncertainty was informative: all 345 proposals marked "low" had both directions
right; all 15 misses were marked "medium" or "high".

**Feasibility is where it was overconfident.** It predicted "feasible" for 892 of 900
proposals; 813 were (`summary.json`: 90.6 % accuracy). Of the misses, 65 returned no
physics at all, and **20 of those are one round**: seed 37, call 2. In round 1 that seed had
the exact validity rule. The prompt's digest of earlier rounds carries only the first 400
characters of the *mechanism*, not the observation where the rule lived; in round 2 the
agent refitted a looser rule (*"cos(theta)*(about 1.86*b - 0.1) < 0.9 … so it should be
buildable"*), sent all 20 proposals to bluntness 1.25–1.35 with every one marked feasible,
none hedged, and gained nothing (hypervolume 0.33115 before and after). The next round
opens: *"All 20 round-2 proposals were wasted on the invalid corner."* `ai_adaptive` seed
37, a fresh sample on the same initial design, lost 18 of 20 in the same round the same
way. Two samples are not a rate, but it is the failure the notebook predicted (proposals
just past a boundary it aims at on purpose), made worse by a harness choice about what the
agent is allowed to remember.

### 4. Rejections, and what the hypervolume is made of

**37 of 937 proposals were rejected (3.9 %): 36 duplicates of a design already evaluated
and 1 identical to its parent. None was out of bounds, malformed, off-schema or attached to
an unknown parent; no response was malformed and no call failed**, so no budget went to the
LHS fallback. The duplicates come from the truncated tables (12 front rows shown of up to
85): the agent cannot see every design it has evaluated, says so (*"some proposed gammas may
duplicate rows not shown to me"*), and by round 9 was choosing *"three-decimal values ending
in 5 to reduce that risk"* — avoiding the cache, not exploiting it. There were no cache hits.

The agent is the most precise fence-parker in the study. 64 % of its front designs have a
mass-fraction margin below 10⁻⁴ (smallest 9 × 10⁻⁶) against none of `bo_parego`'s; it walks
the diameter 3.384 → 3.385 → 3.3852 → 3.38523 m for gains it prices itself at ~10⁻⁵ of
hypervolume. Recomputing per-seed hypervolume after dropping every design within 0.1 % of
any constraint gives `ai_agent` 0.3539 and `bo_parego` 0.3519: the agent's final lead
shrinks from 0.0036 to 0.0020, so a little under half of it is precision on two limits that
M4 labels a logical fence (mass fraction) and unsourceable (12 g). With a 1 % stand-off it
is 0.3446 against 0.3380. The rest of the lead is coverage: 72 front points per seed along
the entry-angle curve against the Bayesian optimiser's 8. The lower design diversity
(0.31 against 0.60 for `bo_parego`) is the same fact seen from the other side, and is what
the notebook predicted: once it believed its model it stopped looking elsewhere, apart from
a few labelled probes a round, none of which moved the corner.

**Hull edge and near-repeats (two checks the generated §8 does not make;
`audit/hull_and_near_repeats.py`).** The drag surface evaluated bluntness 1.200 at cone 70°
and refused 1.201: that is the CFD-hull edge on this front, and it is where CFD happened to
be run, not physics (M4 §11 (ii)). **Every one of the agent's 362 front designs sits on it**
(bluntness exactly 1.2); 18 % of `bo_parego`'s 39 are within 0.01 of it (largest 1.1989);
no NSGA-II or LHS front design is. Finding the edge cost the agent 40 refused evaluations
over five seeds, `bo_parego` 23, the others at most 1. §8 also counts 195 *near-repeats* for
`ai_agent` (a paid design within 10⁻³ of an earlier one in the unit cube) against 0 for
`bo_parego`, and describes the pattern as a way round the cache. Here it is not cache-dodging
(there is no cached result to dodge; each is a new design) but fence-polishing: the same
entry angles re-bought at a diameter 0.2–1 mm larger, and entry-angle steps of 10⁻⁴ degrees at
the g-limit. Removing every near-repeat lowers the agent's mean hypervolume from 0.35557 to
0.35517: about a fifth of its budget bought 0.0004. That is the agent gaming the meter in
the literal sense: legal, declared, scored by the rules, and worth nothing as engineering.

### 5. Verdict of the audit

On this problem the agent behaved like a competent engineer with a textbook: it brought the
right directions from prior knowledge and usually said so, extracted from the data the
things only the data held (limits, the validity rule, the hull fence, the slopes), reached
M4's structural reading of the front in three to five rounds, and then spent more than half
of its budget polishing a one-parameter curve against two placeholder limits without ever
asking whether they were real. It was wrong where it was most confident about geometry it
had not yet seen. Nothing here shows it found a design or a lever that M4's NSGA-II, given
five times the evaluations, did not; what it did was arrive sooner and park closer. The
landscape is easy (one real trade-off, monotone free improvements), which is the most
favourable case for prior knowledge; this audit says nothing about a problem where the
textbook direction is wrong.

### 6. Three sentences of the generated report that need a caveat for this run

The report body is generated and was not edited; the generator lives under `src/aether`,
which was frozen while three studies ran. For this run, read it with these corrections
(recorded as NR-31):

1. **"CFD calls" (§3 table, and "CFD-backed" in the header) is not a count of CFD runs.** No
   CFD solver ran during M5. The column counts paid evaluations that returned physics through
   the CFD-derived drag surface `cfd_surface_v2` (the evaluator labels those fidelity 1);
   the remainder are designs refused before any physics. CFD solver calls made by M5: 0.
2. **"`ai_adaptive` … F0 only" / "every candidate was evaluated at Fidelity 0" (§3, §6) is a
   pre-written sentence that is no longer true as worded.** Every `ai_adaptive` candidate was
   evaluated by the same Fidelity-1 surface as every other method. What remains true is what
   the sentence meant: no promotion to a *new CFD case* was available or granted (0 of 360
   decisions), so the row is plumbing and is excluded from every comparison.
3. **"A 'no measured difference' … means this study could not tell them apart" (§4) does
   not describe the 200-evaluation cell.** There the exact test rejects at its floor
   (p = 1/252, Holm 0.0119; all five agent seeds above all five `bo_parego` seeds, A12 = 1.00).
   The verdict is "no measured difference" because the mean gain, +0.0036, is below the
   pre-declared practical threshold of 0.005 - the rule's effect-size leg, not its
   significance leg. The rule is applied as written; the agent was *distinguishably* ahead
   at 200 evaluations by an amount declared in advance to be too small to count.

**Follow-up, 2026-09-21 (appended; the three items above are left as written).** With no
study holding the source tree, the generator was corrected and the report regenerated
(`make ablation-report`), so the sentences quoted in items 1–3 no longer appear in the
generated sections: (1) the §3 column is now "drag-surface evaluations / seed (fidelity > 0)"
beside a separate "CFD solver calls" column, which counts promotions to a new CFD case
granted by the fidelity hook and reads 0 for every method; the header states 0 solver calls;
(2) the `ai_adaptive` label and section are generated from the run's recorded fidelity and
aero model; (3) the power paragraph is generated per checkpoint from the two legs of the rule
as evaluated (recorded in `summary.json` as `criteria.checkpoints.*.rule_legs`) and says of
the 200-evaluation cell what item 3 says. The report also gained a generated caveat that its
wall times were measured while two other studies shared the machine. No number in
`summary.json` changed: `reports/milestones/REPORT_REGENERATION_2026-09-21.md`.

## 8. Metric-gaming audit, per method

The question for every method: is its hypervolume coming from physics, or from something the model or the meter gets wrong? Every sentence below the tables is generated from the tables; a check that found nothing says so.

Share of each method's front designs (seeds pooled) within 1% of a constraint:

| method | front designs | `heatshield_mass_fraction` | `max_g` | `peak_bondline_temperature_k` |
|---|---|---|---|---|
| `lhs_search` | 11 | 9% | 0% | 0% |
| `nsga2` | 17 | 24% | 0% | 0% |
| `nsga2_pop20` | 19 | 0% | 5% | 0% |
| `bo_parego` | 39 | 85% | 23% | 0% |
| `ai_agent` | 362 | 100% | 18% | 0% |
| `ai_adaptive` | 151 | 100% | 17% | 0% |

Share of front designs parked within 1% of a box bound (lower / upper):

| method | `diameter_m` | `bluntness_ratio` | `cone_half_angle_deg` | `flight_path_angle_deg` |
|---|---|---|---|---|
| `lhs_search` | 0% / 0% | 0% / 0% | 0% / 0% | 0% / 0% |
| `nsga2` | 0% / 0% | 0% / 0% | 0% / 29% | 0% / 12% |
| `nsga2_pop20` | 0% / 0% | 0% / 0% | 0% / 16% | 0% / 0% |
| `bo_parego` | 0% / 0% | 0% / 0% | 0% / 92% | 0% / 15% |
| `ai_agent` | 0% / 0% | 0% / 0% | 0% / 100% | 0% / 4% |
| `ai_adaptive` | 0% / 0% | 0% / 0% | 0% / 100% | 0% / 3% |

Where the budget went, and free evaluations:

| method | budget spent on no-physics designs | on inert repeats | near-repeats (< 1e-3 in the unit cube) | cache hits | of which counted in hypervolume |
|---|---|---|---|---|---|
| `lhs_search` | 55% | 0.0% | 0 | 0 | 0 |
| `nsga2` | 20% | 0.0% | 21 | 0 | 0 |
| `nsga2_pop20` | 12% | 0.0% | 55 | 0 | 0 |
| `bo_parego` | 42% | 0.0% | 0 | 0 | 0 |
| `ai_agent` | 12% | 0.0% | 195 | 0 | 0 |
| `ai_adaptive` | 12% | 0.0% | 78 | 0 | 0 |

- **Fence `heatshield_mass_fraction`:** more than half of the front designs of `bo_parego`, `ai_agent`, `ai_adaptive` sit within 1% of it. Hypervolume from these methods partly measures how precisely they park on that limit; if the limit is a placeholder, so is that part of the score.
- **Box bound, `cone_half_angle_deg` upper:** more than half of the front designs of `bo_parego`, `ai_agent`, `ai_adaptive` are parked on it — an optimum of the box, not of the physics.
- **Cache = free evaluations.** Cache hits cost 0 by design (A-OPT-3) and the hypervolume curve is computed from paid rows only. No method produced a cache hit in this run.
- **Near-repeats** (a paid design within 1e-3 of an earlier one — a way round the 12-significant-digit cache that buys no information): {'nsga2': 21, 'nsga2_pop20': 55, 'ai_agent': 195, 'ai_adaptive': 78}.
- **Inert repeats** (paid evaluations whose objective vector is bit-identical to an earlier one: a variable the model cannot see was moved; `feasible_front` keeps one representative, so they are waste, not gain): none in this run.
- Anything found here that needed a write-up is in `docs/negative_results.md`.

## 9. Limitations

1. **Fidelity 1, aerodynamic model `cfd_surface_v2`, 4 active variables.** The comparison holds for this model and this design space only; it must be re-run, not reused, when either changes.
2. **n = 5 seeds**, set by the LLM call cap, not by a power analysis. The exact tests are valid at this n but weak (§4).
3. **The LLM is not a fixed algorithm.** Its responses are sampled; a re-run issues new calls and will give different numbers. The *recorded* run is reproducible through replay mode, which is a statement about the pipeline, not about the model. The model identifier is recorded per call.
4. **Prior knowledge and contamination** cannot be separated from reasoning-from-data in this design (§2). The qualitative audit is the only handle on it.
5. **Budget is counted in evaluations, not in cost.** In this run one evaluation took a median of 0.13 s of worker time, and one LLM round a mean of 177 s. Hypervolume per evaluation and hypervolume per second are different questions; this report answers the first.
6. **Development history.** `bo_parego` was changed twice after a single-seed smoke test and before any study run (NR-17); that seed is excluded from the study seeds. An earlier study run was aborted when the physics changed under it (NR-18) and no number from it was inspected.
7. Hypervolume inherits M4's fixed reference point and whatever placeholder limits the design-space config carries (see the config snapshot and ASSUMPTIONS A-LIM-*, A-OPT-4).

## Reproduce

```
make ablation                          # LIVE: new LLM calls, new run ID, new numbers
make ablation-replay RUN_ID=M5-ABL-20260920T211134Z   # no LLM access needed
make ablation-report RUN_ID=M5-ABL-20260920T211134Z   # rebuild summary, figures, report from logs
```

`make ablation` needs the Claude Code CLI installed and signed in (no API key is read or accepted). `make ablation-replay` re-runs EVERY evaluation from the recorded responses, checks that each method's per-seed hypervolumes match the original run, and writes to its own run directory without touching this report. Prompts and raw responses: `results/M5/M5-ABL-20260920T211134Z/llm/<method>/seed_<n>/`. Replay uses that run's `config_snapshot.yaml`, not today's config files, so it stays reproducible after the design-space config or the physics defaults change — provided the legacy behaviour it ran with remains selectable.
