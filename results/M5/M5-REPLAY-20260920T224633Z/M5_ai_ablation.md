# M5 — AI vs conventional optimiser ablation

> **fidelity: 1** · aerodynamic model: `cfd_surface_v2` · generated file, do not edit by hand
>
> ablation run `M5-REPLAY-20260920T224633Z` (git `bf4f9a3`, dirty tree, evaluator source hash `c0a44bb0c14acd88`) · active variables from DOE run `M4-DOE-20260920T204844Z` · **replay of `M5-ABL-20260920T211134Z`**

*Produced from an uncommitted working tree; the config snapshot beside the result is the authoritative record of what ran.*

**Read this first.** Fidelity 1, aerodynamic model `cfd_surface_v2`, 4 active design variables (`diameter_m`, `bluntness_ratio`, `cone_half_angle_deg`, `flight_path_angle_deg`) taken from the DOE screening named above. **Evaluations at a fidelity above 0 (CFD-backed), all methods and seeds: 4038.** An optimiser comparison is a statement about the methods ON THIS MODEL, under the limits and variable ranges in the config snapshot; it is not evidence about how the methods would rank on a different model, and nothing here is a statement about a real vehicle.

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

| method | seeds | total evaluations / seed | CFD calls | feasible found (mean) | HV @ final, mean ± s.d. | min – max | front size (mean) | design diversity, all / feasible | wall s / seed (mean) | LLM calls | LLM tokens in / out | proposals rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `lhs_search` | 5 | 200 | 90 | 8.2 | **0.2524 ± 0.0171** | 0.2332 – 0.2757 | 2.2 | 0.780 / 0.404 | 12 | 0 | — | — |
| `nsga2` | 5 | 200 | 161 | 60.4 | **0.2803 ± 0.0253** | 0.2569 – 0.3186 | 3.4 | 0.645 / 0.326 | 20 | 0 | — | — |
| `nsga2_pop20` | 5 | 200 | 177 | 106.6 | **0.2753 ± 0.0381** | 0.2156 – 0.3082 | 3.8 | 0.492 / 0.258 | 27 | 0 | — | — |
| `bo_parego` | 5 | 200 | 121 | 103.0 | **0.3520 ± 0.0011** | 0.3506 – 0.3530 | 7.8 | 0.602 / 0.445 | 91 | 0 | — | — |
| `ai_agent` | 5 | 200 | 184 | 163.8 | **0.3556 ± 0.0000** | 0.3555 – 0.3556 | 72.4 | 0.307 / 0.178 | 70 | 47 | 704145 / 816076 | 37 of 937 |
| `ai_adaptive` | 2 | 200 | 188 | 161.5 | NOT YET MEANINGFUL — no second fidelity available (0.3556, F0 only) | 0.3556 – 0.3556 | 75.5 | 0.306 / 0.182 | 176 | 20 | 303254 / 319308 | 24 of 384 |

s.d. is the sample standard deviation over seeds. *Design diversity* is the mean pairwise Euclidean distance between a run's evaluated designs in the unit cube of the active variables (all paid designs / feasible ones only), averaged over seeds: large = explored widely, small = concentrated. Wall time for the LLM methods is dominated by model latency and was measured with several seeds running concurrently, so it is an upper bound per seed, not a CPU cost; the conventional methods ran one seed at a time on the same 6-process pool. All methods and seeds pooled: 234 front designs, normalised hypervolume 0.3556.

**Against the large-budget reference.** M4's NSGA-II (run `M4-OPT-20260920T205252Z`) reached 0.3467 ± 0.0055 after 1000 evaluations (7 seeds). Determinism check: M5's `nsga2` runs reproduce the first 200 evaluations of M4's runs on the shared seeds to within 0.0e+00 in hypervolume.

![hypervolume vs evaluations](figures/M5_hypervolume.png)

![per-seed hypervolume](figures/M5_hypervolume_per_seed.png)

![fronts](figures/M5_fronts.png)

![budget use](figures/M5_budget_use.png)

## 4. Statistical comparison

Samples are the per-seed hypervolumes (n = 5 per method). No normality is assumed. **Rank test:** exact two-sample permutation test on rank sums (the exact Mann–Whitney test, valid with ties), all C(2n, n) relabellings enumerated. **Signed-rank:** exact Wilcoxon on seed-wise differences, reported only against `bo_parego`, the one method that shares the agent's initial design seed for seed. **A12:** Vargha–Delaney probability that a random agent run beats a random comparator run (0.5 = none, 1 = always).

**Power, stated plainly.** With n = 5 per method the smallest attainable one-sided rank-test p is 1/252 = 0.0040 — reachable only when every run of one method beats every run of the other — and the smallest attainable *two-sided* signed-rank p is 2/32 = 0.0625, which can never reach 0.05. A "no measured difference" below therefore means *this study could not tell them apart*, not *they are equivalent*. Effect sizes and the raw per-seed values are given so the reader is not left with a p-value alone.

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
| `peak_heat_flux_w_m2` | inside hull | 145 | 0.0037 | 0.00174 | 0.999 | 1.47 | 0.44 / 0.67 / 0.80 / 0.85 |
| `peak_heat_flux_w_m2` | outside hull | 391 | 0.0125 | 0.00421 | 0.994 | 1.62 | 0.59 / 0.70 / 0.83 / 0.86 |
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

**Adaptive-fidelity hook — NOT YET MEANINGFUL — no second fidelity available.** The promotion policy (`src/aether/optimization/fidelity.py`; spec §26: predicted Pareto value, uncertainty, novelty, cost) was called on every accepted proposal: 360 decisions, the agent asked for Fidelity 1 on 7, the policy wanted to promote 40, and **0 were granted**. No Fidelity-1 evaluator was available to this run, so every candidate was evaluated at Fidelity 0 and this method's search is, by construction, the plain agent's with different LLM samples. Its hypervolume is printed only to show the plumbing ran; it is excluded from every comparison and says nothing about adaptive fidelity. The policy thresholds are placeholders until they are set against real CFD cost data.

## 7. Qualitative audit of the agent's stated mechanisms

**Not yet written for run `M5-ABL-20260920T211134Z`.** The audit is a human/agent reading of the mechanisms in `results/M5/M5-ABL-20260920T211134Z/agent_log.json`; an audit written against an earlier run is deliberately not shown. Write `reports/milestones/M5_qualitative_audit.md` with front-matter `audited_run: M5-ABL-20260920T211134Z` and re-run `make ablation-report RUN_ID=M5-REPLAY-20260920T224633Z`.

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
5. **Budget is counted in evaluations, not in cost.** In this run one evaluation took a median of 0.61 s of worker time, and one LLM round a mean of 177 s. Hypervolume per evaluation and hypervolume per second are different questions; this report answers the first.
6. **Development history.** `bo_parego` was changed twice after a single-seed smoke test and before any study run (NR-17); that seed is excluded from the study seeds. An earlier study run was aborted when the physics changed under it (NR-18) and no number from it was inspected.
7. Hypervolume inherits M4's fixed reference point and whatever placeholder limits the design-space config carries (see the config snapshot and ASSUMPTIONS A-LIM-*, A-OPT-4).

## Reproduce

```
make ablation                          # LIVE: new LLM calls, new run ID, new numbers
make ablation-replay RUN_ID=M5-ABL-20260920T211134Z   # no LLM access needed
make ablation-report RUN_ID=M5-ABL-20260920T211134Z   # rebuild summary, figures, report from logs
```

`make ablation` needs the Claude Code CLI installed and signed in (no API key is read or accepted). `make ablation-replay` re-runs EVERY evaluation from the recorded responses, checks that each method's per-seed hypervolumes match the original run, and writes to its own run directory without touching this report. Prompts and raw responses: `results/M5/M5-ABL-20260920T211134Z/llm/<method>/seed_<n>/`. Replay uses that run's `config_snapshot.yaml`, not today's config files, so it stays reproducible after the design-space config or the physics defaults change — provided the legacy behaviour it ran with remains selectable.
