# 2026-09-21 — Fixing the M5/M6/M7 report generators without moving a number

*Written after the work. Continues `2026-09-21_M6_study_run.md` and `2026-09-21_M7_study_run.md`,
whose "Next" lists this session works through. Detail and the check's full output:
`reports/milestones/REPORT_REGENERATION_2026-09-21.md`.*

## Question

Can every defect recorded in NR-31, NR-34 and NR-35 be fixed in the generators - wording,
one statistic's presentation, figures - while every result stays exactly where it was? And
what does the one fix that needs new evaluations (the §39 robust row) come out as?

## Hypothesis

All but one are presentation. The §39 robust row is not: it needs the robust knee propagated
on the other rows' draws. Expected that to land near the 500-draw value (2.8%) and below 5%.

## Action

All three studies had finished, so `src/aether` could be edited. Order mattered because every
runner hashes the source tree: all generator edits first; then the like-for-like propagation
and the M5 strict replay, with no source edit while either ran.

* M5: count renamed to what it measures (`surface_evaluations`) with a separate
  `cfd_solver_calls`; `ai_adaptive` label from the recorded fidelity and aero model; power
  paragraph from the rule's two legs as evaluated; wall-time caveat from the runs' own
  timestamps (`utils.run.overlapping_runs`); stale comment in `configs/ai_ablation.yaml`.
* M6: generated first paragraph (verdict, un-run arm, reachability); two figure titles.
* M7: attribution figure; nominal front into `M7_robust_vs_nominal`; `--report-only` reloads
  both fronts; projection relabelled and achieved rate printed; branch bootstrap beside the
  declared row bootstrap; §7 from fidelity and tier counts; inventory and distribution
  figures; cache-hit sentence.
* New: `scripts/run_m7_robust_likeforlike.py`, `scripts/check_report_regeneration.py`,
  `tests/test_report_regeneration.py`.

## Expected vs observed

| Expected | Observed |
|---|---|
| Comment edit leaves the config hash alone | Yes: the hash is over the parsed mapping; `ddd70cac52e9` before and after |
| M5 `--report-only` rewrites `summary.json`; values identical | 2,551 of 2,551 values identical; 33 of them now live under the renamed key; new blocks only added |
| M6 `summary.json` untouched | Byte-identical |
| M7 `summary.json` values identical | 13,744 of 13,744 |
| Every table number survives | 275 table rows before; 272 found again with every number intact; 3 differ, each a declared fix (two relabelled sizing rows with the same numbers, and the robust cell) |
| Robust knee like-for-like near 2.8% | 3.20% [2.63, 3.89] (96 of 3000), all mass-fraction. Original 2.80% [1.68, 4.64] (14 of 500). Intervals overlap |
| Today's evaluator equals the study's | 120 of the study's own `joint_knee` evaluations reproduced to 3.5e-14 relative, feasibility identical - checked before propagating, or the run refuses |
| Branch bootstrap could flip "baseline misses 1%" depending on seed | It did not: 1.06–1.10% across six seeds tried; 1.06% at the recorded seed |
| Replay might refuse on the changed source hash | It does not refuse; it records `source_hash_matches_original: False`. Strict replay: 0 prompt mismatches, all six methods' per-seed hypervolumes identical |
| (not anticipated) | `paired_difference.json` carries a cluster-bootstrap block that no committed script writes; re-running `analyse_m7_paired.py` would have deleted it. Its baseline value is reproduced exactly by the new function; the script now preserves unknown keys |
| (not anticipated) | The row-by-row table check caught my own change of a row label (log₁₀ marker) as a "lost row" before I declared it |

## Evidence

* `scripts/check_report_regeneration.py`: PASS, before = git `eac22c7`.
* `results/M7/M7-LFL-20260921T011854Z/` (`likeforlike.json`, `paired_difference.json`):
  robust knee − joint knee on shared draws, bondline −0.42 K (s.d. 0.12, 3000 of 3000 lower),
  peak flux +7.46 kW/m² (3000 of 3000 higher).
* Strict replays: `results/M5/M5-REPLAY-20260921T012107Z/` (tree hash `51292369ab52d18a`),
  and, after two M5 figure legends were moved out of the data, the final tree
  `results/M5/M5-REPLAY-20260921T013046Z/` (hash `4f428168c6481bbb`). Both: 0 prompt
  mismatches, all per-seed hypervolumes identical. Logs `results/M5/ablation_run2_replay_*.log`.
  The like-for-like run was made on the first of those two trees; the difference between
  them is `optimization/ablation_plots.py` only.
* Every regenerated M6 and M7 figure and `M5_hypervolume` re-read against §34.
* pytest 497 passed, 1 skipped; ruff clean.

## Interpretation

The defects were all of one family: a sentence or a label that was true of the model the
generator was first written for. The fix that holds is the one NR-18 already named - make
the sentence conditional code - and this time with a check that can fail sitting beside it.
The like-for-like row changes no conclusion: within the declared uncertainty model the robust
knee trades about 3% of peak flux for chance-feasibility at essentially the same bondline.

The replay result deserves its exact wording. It shows that the recorded responses, replayed
through today's tree, reproduce the study's hypervolumes. It is not a statement that the
source is unchanged - it is not - and the replay says so in its own record.

## Next

1. `M5_hypervolume` and the other M5 figures have a caption and no title; §34 reads
   "title/caption", so they pass as written, but they are the odd ones out now.
2. §4 of the M7 report still has one fixed sentence about K ≈ 0.42 ("is expected to
   dominate"); it is phrased as an expectation and the tables beside it carry the result,
   but it should be generated from the attributed designs' K.
3. Unchanged from the M7 entry: more epistemic branches, a sourced TPS conductivity, and the
   student decisions on the mass-fraction fence and the 12 g limit.
