# M5 — AI vs conventional optimiser ablation

> **fidelity: 0** · aerodynamic model: `constant` · generated file, do not edit by hand
>
> ablation run `M5-REPLAY-20260920T141649Z` (git `715ac9f`, dirty tree) · active variables from DOE run `M4-DOE-20260920T131334Z` · **replay of `M5-ABL-20260920T140754Z`**

*Produced from an uncommitted working tree; the config snapshot beside the result is the authoritative record of what ran.*

**Read this first.** This is a Fidelity-0 result on a small problem: four active variables, constant drag coefficient, Sutton–Graves stagnation heating, 1-D conduction. **CFD calls: 0 for every method** — no CFD-backed evaluator exists yet (gate G4). M4 showed what this landscape is: entry angle is the only real trade-off; diameter and nose bluntness are free improvements until each hits a placeholder fence. An optimiser comparison on such a landscape measures how fast a method finds two fences and spreads along one axis. It is a fair test of the plumbing and of sample efficiency on THIS model; it is not evidence about how the methods would rank on a harder, CFD-coupled problem, and the coordinator re-runs it when the corrected nose-radius physics and the CFD surrogate land. Nothing here is a statement about a real vehicle.

## 1. What was asked, and what was declared before the run

Spec §24/§46: compare an LLM engineering agent against conventional optimisers under matched evaluation budgets, and do not claim AI superiority unless it is measured. The rule for "measured" was written into `configs/ai_ablation.yaml` before any method ran:

- **metric:** normalised hypervolume of the feasible set after 50, 60 evaluations;
- **comparator:** at each checkpoint, the non-LLM method with the highest mean hypervolume ("best conventional") — beating only the LHS floor does not count;
- **"AI helped"** iff mean HV(`ai_agent`) − mean HV(comparator) ≥ 0.005 **and** the one-sided exact permutation test gives p < 0.05 after Holm correction across the checkpoints; **"AI hurt"** is the mirror image; anything else is **"no measured difference"**.

## 2. Set-up

Every method received exactly **60 evaluations per seed**, seeds 7, through the same `BudgetedEvaluator` as M4 (A-OPT-3: every distinct design costs 1, including geometrically invalid ones; a repeat is served from cache, logged, and costs 0). Active variables: `diameter_m`, `bluntness_ratio`, `cone_half_angle_deg`, `flight_path_angle_deg`. Hypervolume reference point (2.5e+06 W/m², 450 K) — M4's, read from the same config file, not copied.

**Why 60 × 1 and not M4's 1000 × 7.** The LLM is the scarce resource: the study is hard-capped in code at 3 LLM calls (3 per seed). M4's 1000-evaluation runs remain the conventional reference for what a large budget reaches.

| method | kind | what it is |
|---|---|---|
| `ai_agent` | ai_agent | LLM proposes batches from a structured table; strict schema; every proposal has a parent and a rationale. Settings: {'n_initial': 20, 'rounds': 2} |

`nsga2` keeps M4's population of 40, which at this budget is five generations; `nsga2_pop20` is the same code with the population scaled to the budget, declared before the run so that NSGA-II is not handicapped by a setting chosen for 1000 evaluations. `bo_parego` and the agent start from the **same** seeded 20-point Latin Hypercube, seed for seed, which is what makes their comparison paired.

**Why ParEGO and not expected hypervolume improvement.** With batches of 10 in a constrained box that is more than half geometrically invalid, EHVI needs a greedy fantasy loop or a joint batch integral; random Tchebycheff weights give batch diversity for free at one GP fit per iteration, and the GPs model the objectives themselves, so the models that drive the search are the ones validated in §6.

**Invalid geometry — no method gets it for free.** The analytic `CapsuleGeometry.validate()` rule is not given to any optimiser as a pre-filter or repair step: an invalid design costs 1 for everyone (A-OPT-3), the Bayesian optimiser learns the valid region from the designs that came back invalid, and an LLM proposal that turns out invalid is charged like any other.

**What the LLM saw, and the asymmetries that remain.** Structured JSON only: the active variables' names, units and bounds; the frozen parameters; objective and constraint *names*; the hypervolume reference point; the budget left; a table of the feasible non-dominated designs, the nearest misses, the most recent evaluations and recent geometry failures, each with metrics, constraint margins and the evaluator's failure message; and a digest of its own earlier rounds. It was told neither the equations of the model nor anything M4 found. The CLI was run in an empty temporary directory with tools, MCP servers, hooks, skills and CLAUDE.md discovery disabled, so it could not read this repository. Three asymmetries are part of what is being measured and are stated rather than removed: (1) **prior knowledge** — the variable and metric names alone tell an LLM trained on the aerospace literature that blunter and larger means cooler; the other optimisers see numbers without names; (2) **failure messages** — the geometry validator's text says which variable to move ("increase cone_half_angle_deg …"), which the LLM can read and the numeric optimisers cannot; (3) **contamination** — the model may have seen blunt-body entry optimisation problems like this one in training. A win by the agent is therefore a win for *priors plus data*, not for data alone.

## 3. Results (spec §46 table)

| method | seeds | total evaluations / seed | CFD calls | feasible found (mean) | HV @ final, mean ± s.d. | min – max | front size (mean) | design diversity, all / feasible | wall s / seed (mean) | LLM calls | LLM tokens in / out | proposals rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ai_agent` | 1 | 60 | 0 | 39.0 | **0.3843 ± n/a** | 0.3843 – 0.3843 | 13.0 | 0.541 / 0.157 | 5 | 2 | 26256 / 49316 | 0 of 40 |

s.d. is the sample standard deviation over seeds. *Design diversity* is the mean pairwise Euclidean distance between a run's evaluated designs in the unit cube of the active variables (all paid designs / feasible ones only), averaged over seeds: large = explored widely, small = concentrated. Wall time for the LLM methods is dominated by model latency and was measured with several seeds running concurrently, so it is an upper bound per seed, not a CPU cost; the conventional methods ran one seed at a time on the same 6-process pool. All methods and seeds pooled: 13 front designs, normalised hypervolume 0.3843.

**Against the large-budget reference.** M4's NSGA-II (run `M4-OPT-20260920T132037Z`) reached 0.3773 ± 0.0070 after 1000 evaluations (7 seeds). 

![hypervolume vs evaluations](figures/M5_hypervolume.png)

![per-seed hypervolume](figures/M5_hypervolume_per_seed.png)

![fronts](figures/M5_fronts.png)

![budget use](figures/M5_budget_use.png)

## 4. Statistical comparison

Not evaluated: no non-LLM method was run on the same seeds.

## 5. Surrogate validation (spec §25)

Two held-out tests, both on designs the model had never seen, both in the modelled space (log₁₀ for heat flux, where the GP's Gaussian assumption is made).

**Extrapolation policy.** `GPSurrogate.predict` *refuses* (raises) outside the training hull by default; a number of record cannot be produced there. The acquisition function is the one caller allowed to pass `on_extrapolation="flag"`: it is buying an evaluation at that point, not trusting the prediction, and every such pick is flagged and counted above. R² is low or negative wherever the test set barely varies (near the converged front) — that is a property of R², which is why RMSE and coverage are given beside it.

![surrogate calibration](figures/M5_surrogate_calibration.png)

## 6. The agent's behaviour

### `ai_agent`

- model: `claude-sonnet-5` (responses **replayed** from disk, no live call)
- LLM calls: **2** ({'ok': 2}); tokens in / out 26256 / 49316; summed call wall time 506 s; list-price cost as reported by the CLI $0.60 (a subscription login was used; no API key)
- proposals: 40 received, 40 accepted, **0 rejected** (none); malformed responses 0; failed calls 0; budget spent on the LHS fallback because the agent could not fill it: 0 evaluations
- the agent's own numeric predictions (40 scored): feasibility called correctly 98% of the time (it predicted feasible 38×, 39 were); `peak_heat_flux_w_m2` MAE 1.14e+04, bias -1.14e+04; `peak_bondline_temperature_k` MAE 2.4, bias +2.28

## 7. Qualitative audit of the agent's stated mechanisms

**Not yet written for run `M5-ABL-20260920T140754Z`.** The audit is a human/agent reading of the mechanisms in `results/M5/M5-ABL-20260920T140754Z/agent_log.json`; an audit written against an earlier run is deliberately not shown. Write `reports/milestones/M5_qualitative_audit.md` with front-matter `audited_run: M5-ABL-20260920T140754Z` and re-run `make ablation-report RUN_ID=M5-REPLAY-20260920T141649Z`.

## 8. Metric-gaming audit, per method

The question for every method: is its hypervolume coming from physics, or from something the model or the meter gets wrong?

| method | front designs within 1% of `bluntness_ratio` cap | … of `heatshield_mass_fraction` | … of `max_g` | budget spent on no-physics designs | on inert repeats | near-repeats (< 1e-3) | cache hits |
|---|---|---|---|---|---|---|---|
| `ai_agent` | 100% | 15% | 15% | 18% | 0.0% | 0 | 0 |

- **Fences.** Every method's front leans on the same two placeholder constraints M4 identified (NR-13, NR-15). That is the landscape, not a method cheating; but it means hypervolume here largely rewards *how precisely a method parks on a fence*, and a method that reads the constraint's name can aim at it directly.
- **Cache = free evaluations.** Cache hits cost 0 by design (A-OPT-3). The hypervolume curve is computed from paid rows only, so a cache hit cannot move it; the column is there to show whether any method leaned on the cache at all.
- **Inert repeats** are paid evaluations whose objective vector is bit-identical to an earlier one — a variable the model cannot see was moved. They are waste, not gain: `feasible_front` keeps one representative per objective vector.
- Findings that needed a write-up are in `docs/negative_results.md` (NR-17 onward).

## 9. Limitations

1. **Fidelity 0, four variables, two fences.** See the box at the top. The ranking of methods is expected to change when drag depends on shape and when the bluntness fence is replaced by an effective-nose-radius model.
2. **n = 1 seeds.** Chosen by the LLM call cap, not by a power analysis. The exact tests are valid at this n but weak.
3. **The LLM is not a fixed algorithm.** Its responses are sampled; a re-run issues new calls and will give different numbers. The *recorded* run is exactly reproducible through replay mode, which is a statement about the pipeline, not about the model. The model identifier is recorded per call.
4. **Prior knowledge and contamination** cannot be separated from reasoning-from-data in this design (see §2). The qualitative audit is the only handle on it.
5. **Budget is counted in evaluations, not in cost.** An LLM round costs tens of seconds and thousands of tokens; a GP fit costs a second; an NSGA-II generation costs nothing. At 0.25 s per evaluation the LLM's overhead dwarfs the evaluations it saves; the comparison only becomes economically interesting when one evaluation is a CFD run.
6. **`bo_parego` was adjusted once before the study**, after a single-seed smoke test: a probability-of-feasibility floor was added and sklearn's GP classifier was replaced (NR-17). No setting of any method was changed after the study's results were seen.
7. Hypervolume inherits M4's unsourced placeholders (450 K allowable, 12 g, bluntness cap 1.2).

## Reproduce

```
make ablation                          # LIVE: new LLM calls, new run ID, new numbers
make ablation-replay RUN_ID=M5-ABL-20260920T140754Z   # no LLM access needed
make ablation-report RUN_ID=M5-ABL-20260920T140754Z   # rebuild summary, figures, report from logs
```

`make ablation` needs the Claude Code CLI installed and signed in (no API key is read or accepted). `make ablation-replay` re-runs EVERY evaluation from the recorded responses, checks that each method's per-seed hypervolumes match the original run, and writes to its own run directory without touching this report. Prompts and raw responses: `results/M5/M5-ABL-20260920T140754Z/llm/<method>/seed_<n>/`. Replay uses that run's `config_snapshot.yaml`, not today's config files, so it stays reproducible after the design-space config or the physics defaults change — provided the legacy behaviour it ran with remains selectable.
