# M7 addendum — paired differences, H0/H1 under uncertainty, and what the generated report gets wrong

Companion to `reports/milestones/M7_uncertainty_robust.md` (generated). Written by hand on
2026-09-21 because the generated report does not answer three questions the study was run to
answer, and because reading it against its own `summary.json` and its own figures found
defects that cannot be fixed yet: the fixes are in `src/aether/` and the M5/M6 studies were
still running on that source tree (NR-18 guard).

**Every number below is read from a file, none is typed from memory:**

* `results/M7/M7-UQ-20260920T233048Z/summary.json` — the study (propagation, attribution, §39).
* `results/M7/M7-ROBUST-20260920T211216Z/` — the robust optimisation it folds in.
* `results/M7/M7-UQ-20260920T233048Z/paired_difference.json` — written by
  `scripts/analyse_m7_paired.py`, which evaluates nothing: it re-reads `candidates.csv` and
  `draws.csv`. Reproduce with `.venv/bin/python scripts/analyse_m7_paired.py M7-UQ-20260920T233048Z`.

Both runs: evaluator source hash `c0a44bb0c14acd88`, aero model `cfd_surface_v2`, 4 workers
(the config says 6; `--workers 4` was passed so M6's CFD cases were not starved — it changes
wall time and nothing else).

## 1. Is the knee's bondline advantage larger than the uncertainty on that advantage?

M4 found the joint knee 14.9 K cooler at the bondline than the peak-flux-only design. Each
design's own propagated s.d. is 6.5 K and 7.6 K, so read as two independent clouds the
difference would carry an s.d. of 10.0 K and the 14.9 K would look marginal. That reading is
wrong, because it is not what was sampled: all four designs were propagated on **one shared
draw set** (seed 20260921, draw index 0–2999), so draw *i* is the same atmosphere, the same
as-built mass, the same TPS conductivity and the same nose-radius model for every design.
The per-draw difference tests the difference itself.

| Δ peak bondline T [K], same draw | mean | s.d. | p5 … p95 | min … max | draws with Δ < 0 | 95% CI on mean (branch bootstrap) |
|---|---|---|---|---|---|---|
| joint_knee − peak_flux_only | −14.31 | 1.45 | −16.59 … −11.78 | −17.85 … −10.80 | 3000 / 3000 | [−14.88, −13.76] |
| bondline_only − peak_flux_only | −25.64 | 2.44 | −29.43 … −21.47 | −31.55 … −19.79 | 3000 / 3000 | [−26.59, −24.73] |
| bondline_only − joint_knee | −11.33 | 0.99 | −12.85 … −9.64 | −13.71 … −8.99 | 3000 / 3000 | [−11.72, −10.96] |

* The knee is cooler than the peak-flux-only design in **every one of 3000 draws**, never by
  less than 10.8 K. 0 of 3000 is an upper bound, not zero: below 0.13% at 95% confidence
  (Wilson), *within the declared uncertainty model*.
* The paired s.d. is 1.45 K against 10.0 K for independent clouds, because the two designs'
  bondline responses are correlated at ρ = 0.992 across draws. The mean difference is 9.9
  paired standard deviations from zero.
* In the view that does not treat ignorance as probability: the branch-mean difference lies in
  [−17.05, −11.41] K over the 24 epistemic branches, negative in all 24; within a branch the
  largest aleatory s.d. of the difference is 0.40 K. **Which model is right changes the size of
  the advantage (by about ±3 K), not its sign.**
* The mean (−14.31 K) is slightly smaller in magnitude than the nominal −14.9 K.
* Confidence intervals resample whole epistemic branches, not rows (the rows are not
  independent — see §4.1).

What it costs, same method: the knee's peak heat flux is higher in 3000 of 3000 draws, by
+20.5 kW/m² on average (s.d. 0.95, range +18.4 … +22.7 kW/m²; nominal +21.5).

**So: within the declared uncertainty model, the model predicts the ordering of the three M4
designs is not an artefact of the nominal point.** This says nothing about uncertainty that is
not declared — gate G2′ (catalycity, hot wall, radiation) above all — and a common-mode model
error of that kind would move all three designs together, which is exactly why the paired test
cannot see it.

## 2. H0 and H1 restated under uncertainty

**H0** (*minimising peak heat flux alone does not necessarily give the thermally safest
design*): **supported within the tested assumptions, and not weakened by the declared
uncertainty.** The peak-flux-only design has the hottest bondline of the three M4 designs in
3000 of 3000 shared draws (§1).

**H1** (*joint optimisation can identify safer feasible designs*): **supported for "safer";
the word "feasible" does not survive for the nominal designs.**

* None of the three nominal M4 optima is chance-feasible at the declared 5%:
  P(any constraint violated) is 34.40% [32.72, 36.12] (`peak_flux_only`), 29.60%
  [27.99, 31.26] (`joint_knee`), 46.60% [44.82, 48.39] (`bondline_only`).
* **It is not a thermal fragility.** Bondline violations are 0 of 3000 for all three (below
  0.13% at 95% confidence — not zero). The violated constraint is `heatshield_mass_fraction`
  for the first two, and that plus `max_g` (36.00%) for `bondline_only`. The three designs sit
  0.84%, 1.09% and 0.19% from their binding constraint at the nominal point — an optimiser
  puts a design on its constraint, and any dispersion then pushes roughly a third to a half of
  draws across it.
* **The constraint being crossed is a fence, not a requirement.** `heatshield_mass_fraction ≤ 1`
  says the forebody TPS cannot outweigh the vehicle (NR-13, NR-30: "a logical necessity, not a
  mass budget", no sourced budget exists). What pushes draws across it is `vehicle_mass`
  (point-biserial correlation with violation −0.82 / −0.79 / −0.67), a ±2% 1-σ as-built mass
  dispersion that `configs/uncertainty.yaml` tiers **T3 engineering judgment** about a 350 kg
  **placeholder**. The `max_g` violations of `bondline_only` are driven by the delivered
  flight-path angle (−0.58) and density (−0.47), against a 12 g limit that A-LIM-1b records as
  an open decision. The fragility is real *as a statement about this model's constraint set*;
  it is a statement about two placeholders and a fence, not evidence the vehicle overheats.
* **The trade-off survives among chance-feasible designs.** The robust front (46 designs, all
  chance-feasible on the inner sample, shortcut verification PASSED) runs from 95th-percentile
  peak flux 240.2 kW/m² at 434.2 K to 287.6 kW/m² at 403.5 K — a 30.6 K span of
  95th-percentile bondline temperature. Its own flux-minimising end is its hottest-bondline
  end, as on the nominal front. Under the independent 1000-draw re-score of the 8 verified
  designs the same ends read 243.9 kW/m² / 432.4 K and 292.5 kW/m² / 402.6 K.

## 3. Robust versus nominal

* **What robustness changed in the design.** Robust-front diameters are 3.308–3.323 m against
  3.355–3.370 m for the three M4 designs — 1.0–1.5% smaller, which buys mass-fraction margin
  (robust knee: 3.79% from the fence, against 1.09% for the joint knee). Bluntness
  (1.146–1.199) and cone angle (68.1–70.0°) stay where the nominal front had them; the front
  is still traced mainly by flight-path angle (−3.49° … −1.52°).
* **What it cost at the knee** (nominal values, `cost_of_robustness`): peak flux
  +7.8 kW/m² (+3.1%), bondline −0.46 K. P(any violation) 2.80% [1.68, 4.64] (14 of 500)
  against 29.60% for the joint knee. **Caveat:** the robust row's uncertainty column is 500
  *mixed* draws (seed 20260925); the other three rows are 3000 *nested* draws (seed 20260921).
  They are different draw sets, so the robust row cannot be paired with the others as in §1,
  and its p95 values are not strictly like-for-like.
* **The whole robust front sits exactly on the chance constraint as the optimiser saw it.**
  All 46 designs have `pviol__heatshield_mass_fraction` = 1/32 = 3.125% — exactly the one
  violating inner draw the rule permits (at most 1 of 32). The optimiser used the allowance
  to the last draw, on 32 fixed draws it could learn. This is the metric-gaming surface the
  verification exists to catch, and the verification is what says how much it mattered: on
  1000 fresh draws the 8 checked designs read 1.3%–3.3% on the mass fraction, and **one of the
  8 (`C-22b67c409bf2`, the low-bondline end) reads P(any) = 5.7% against the 5% limit** — 2.6%
  of it from `max_g`, which the 32 inner draws had seen as 0. That is the one "feasibility
  verdict that flipped" in the report's table.
* **Shortcut verification: PASSED, applied exactly as pre-declared** — |mean relative bias|
  1.61% and 0.32% (tolerance 5%), Spearman ρ 1.000 and 1.000 (tolerance ≥ 0.80), largest
  |Δp| 2.60% (tolerance 5%). A flipped verdict is *not* one of the three declared tolerances, so
  it does not fail the check and the criterion was not re-tuned to make it. It is reported
  because it is true: the robust front is verified in its objectives and its ranking, and
  its low-bondline end is marginally *not* chance-feasible under full Monte Carlo. The bias has
  a consistent sign — the 32-draw p95 under-reads peak flux by 1.6% on all 8 designs.
* **Common random numbers bought no cache hits:** 0 of 90,000 inner evaluations. The
  optimiser never re-proposed a design. CRN still did its real job (every candidate compared
  on the same 32 worlds); the "free re-evaluation" saving the harness anticipated did not occur.

## 4. Defects found checking the generated report and figures (not fixed — source is frozen while M5/M6 run)

Checked: every number in §3, §3.2, §4, §5.2, §5.3 and §6 of the generated report against
`summary.json` — **all match**. The problems are in wording, in one statistic's method, and
in the figures.

### 4.1 The convergence check understates the sampling error about tenfold

The report's §3.3 bootstrap resamples 3000 *rows*. The draw set is nested — 24 epistemic
branches × 125 shared aleatory draws — and 97–99% of the bondline variance is between
branches, so the effective sample for the mean is nearer 24 than 3000. Resampling whole
branches (`paired_difference.json` → `convergence_cluster_bootstrap_bondline`):

| Design | mean: report half-width | mean: branch bootstrap | p95: report | p95: branch bootstrap |
|---|---|---|---|---|
| `baseline` | 0.09% | **1.06%** (5.3 K) | 0.04% | 0.63% (3.3 K) |
| `peak_flux_only` | 0.06% | 0.72% (3.0 K) | 0.06% | 0.60% (2.6 K) |
| `joint_knee` | 0.05% | 0.62% (2.5 K) | 0.03% | 0.44% (1.8 K) |
| `bondline_only` | 0.05% | 0.58% (2.3 K) | 0.02% | 0.38% (1.5 K) |

The pre-declared check, as declared and as run, is met by all eight statistics. On the
stricter reading the three front designs still meet the 1% tolerance and **the baseline mean
(1.06%) marginally does not**. The convergence figure shows the same thing: the first two
checkpoints (N = 100, 250) are one and two branches, not small random samples. None of the
conclusions above rests on a mean being known to better than ~3 K; §1 rests on paired
differences, whose branch-bootstrap interval is ±0.56 K. More epistemic branches, not more
draws, is what would tighten the absolute statistics.

### 4.2 Report text

* **§2** "measured throughput 17 evaluations/s", "achieved parallel efficiency 80.0%": neither
  is measured. 17.02 = 4 × 0.80 / 0.188 — the *declared* efficiency echoed back
  (`sizing.measured_parallel_efficiency` is set equal to the declared value). Achieved:
  19,668 evaluations in 1,499 s = 13.1 /s, about 62%, on a machine shared with M6's CFD and M5.
  The header's "25.0 min wall" is correct.
* **§2** lists robust optimisation and verification as 0 evaluations. That is this run's
  projection only; the robust run (`M7-ROBUST-20260920T211216Z`) logged 98,256
  evaluations (3 × 30,000 search and 8 × 1,000 verification account for 98,000 of them; what the other 256 rows are was not checked) in 8,305 s (2 h 18 min) and is where they are recorded.
* **§7** "Not propagated in this run: `cd_fidelity0_judgment`. At Fidelity 0 the four sourced
  C_D terms … do not exist … the C_D-related numbers here should not be carried into a
  Fidelity-1 discussion." **Wrong for this run**, which *is* Fidelity 1: all four sourced C_D
  terms were propagated and the judgment band was skipped because it was not needed. The
  sentence was written for the opposite branch (same family as NR-31).
* **§7** "The two inputs that are T1" — the report's own table tiers four inputs T1.
* **§5.1** the cache-hit sentence describes a saving of 0.0%.
* Section numbers repeat: two "3.1", two "4.1".

### 4.3 Figures against spec §34

| Figure | Verdict |
|---|---|
| `M7_attribution` | **WRONG — do not use.** Left and middle panels carry the right-hand panel's y labels (`sharey=True` with a per-panel sort order, `plots.py` `plot_attribution`). The 0.609 bar labelled `entry_flight_path_angle` is `sutton_graves_coefficient`; the 0.883 bar is `tps_conductivity`. The tables in the report are correct. It also draws only `baseline` (`next(iter(usable))`), so the `joint_knee` attribution — where the nose-radius result lives — has no figure. |
| `M7_robust_vs_nominal` | Titled "Nominal vs robust Pareto fronts" but contains no nominal front: the runner passes `nominal_front=None`. It shows the robust front and the three nominal designs with arrows to their p95. The y axis mixes nominal values and 95th percentiles under one label (the legend does say which is which). |
| `M7_input_inventory` | Legend overprints the `vehicle_mass` bar and its tier label; the density panel's legend overprints the 0–20 km points; the footnote runs off the right edge. |
| `M7_output_distributions` | Heat-flux panel is scaled by the baseline (1.87 MW/m²), so the three front designs are an unreadable sliver. |
| `M7_pbox`, `M7_convergence`, `M7_shortcut_verification` | Meet §34: units, title, run ID, source hash, legend. |

`make uncertainty-report` must **not** be run until the runner is fixed: its `--report-only`
path passes `None` for the robust front as well, which would drop `M7_robust_vs_nominal` and
`M7_shortcut_verification` from the report.

## 5. Which uncertainty actually dominates

| Output | `baseline` (K = R_b/R_n = 1.000, hemisphere) | `joint_knee` (K = 0.417) |
|---|---|---|
| peak heat flux | Sutton–Graves constant S_T 0.609 [0.529, 0.718]; perfect-gas C_D form 0.258; mass 0.122; **nose-radius model 0.000** | **nose-radius model S_T 0.706 [0.599, 0.819]**; Sutton–Graves 0.181; perfect-gas C_D form 0.065 |
| peak bondline T | TPS conductivity 0.883 [0.763, 0.996]; >86 km heating 0.086 | **TPS conductivity 0.638 [0.544, 0.729]; >86 km heating 0.262**; nose-radius model 0.052 |
| max g | flight-path angle 0.340; density 0.285; base drag 0.155; perfect-gas form 0.154 | flight-path angle 0.487; density 0.338; base drag 0.121 |

* The expectation is **confirmed for peak heat flux**: at the front's K ≈ 0.42 the
  disagreement between NASA TN D-5121 and Zoby & Sullivan carries 71% of the flux variance,
  and it is exactly zero on the hemispherical reference, where the two sources agree
  identically. It is a T1 term: it can be resolved by evidence.
* It is **not confirmed for the bondline**: there the nose-radius model is 5%. The bondline
  is governed by the insulator's conductivity (64%) and by the heating above 86 km (26%) —
  **both T3 engineering judgment**. The project's second objective is dominated by the two
  numbers it has the least evidence for. The >86 km share triples from the baseline (9%) to
  the front (26%), in line with NR-14: front designs fly long and shallow.
* The switch is one-sided: the nominal configuration is one of its two states and the other
  only lowers flux, so every front design's *mean* peak flux sits 4.4% below its nominal value
  (e.g. 240.0 vs 251.0 kW/m² at the knee: the 1500 draws in the nominal state average 248.9, the
  1500 in the Zoby state 231.1) and its p95 only 2.5% above it.
* Pooled, 84–94% of flux variance and 97–99% of bondline variance is epistemic; `max_g` is the
  opposite (12–38% epistemic). An index on an epistemic input is a sensitivity to which model
  is believed, not a share of real variability.
* The GP surrogate (≤ 0.020) and the mesh discretisation term (≤ 0.003) are negligible for
  every output on both designs. Of the C_D terms, the unvalidated perfect-gas band and the
  base-drag band are the ones that register.
