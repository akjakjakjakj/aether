# Reproducibility section

Spec §49 and §50. What a stranger needs in order to re-run this work, in the form it takes in
a submission: one short section in the paper or brief, plus a pointer to the full
instructions.

**Status: run IDs filled 2026-09-21; the repository link is `[PENDING — STUDENT]`** because
choosing a public location and cleaning the tree at a release commit is the student's act.
The paper and package were drafted against commit `de2a834`.

Run IDs the paper cites: `M1-20260902T130547Z` (M1, M1b), `TPI-20260920T124732Z`,
`M2-20260920T123901Z` (gate G4), `M3-DP-20260920T1610Z` (`cfd_surface_v2`),
`M4-DOE-20260920T204844Z`, `M4-OPT-20260920T205252Z`, `M5-ABL-20260920T211134Z` (replays
`M5-REPLAY-20260920T224633Z`, `M5-REPLAY-20260921T013046Z`), `M6-AF-20260920T211148Z`,
`M7-ROBUST-20260920T211216Z`, `M7-UQ-20260920T233048Z`, `M7-LFL-20260921T011854Z`.

---

## The section as it appears in the paper

> **Reproducibility.** The repository is at `[PENDING — STUDENT: public URL or archived
> DOI]`, at commit `[PENDING — STUDENT: the clean release commit; drafted against de2a834]`.
> Every result in this paper is produced by a command in that
> repository, and every number in every report is read from a result file rather than typed:
> reports in `reports/milestones/` are generated, and hand-editing one is overwritten by the
> next run.
>
> A clean environment needs Python 3.12 and the pinned dependencies in `pyproject.toml`
> (numpy, scipy, matplotlib, pyyaml, pandas, pyarrow). There are no compiled extensions, no
> GPU requirement and no network access at runtime. OpenFOAM is required only for Fidelity 1.
>
> ```
> uv venv --python 3.12
> uv pip install -e ".[dev]"
> make test            # verification suite
> make baseline        # one nominal entry
> make burn-vs-bake    # the M1 and M1b result, reports and figures
> ```
>
> On the reference machine (Apple M4) these take about 25 s, 3 s and 4 min respectively.
> Expected runtimes for every other command, including the ones that need OpenFOAM and take
> hours, are tabulated in `REPRODUCIBILITY.md`.
>
> The Fidelity-0 chain is deterministic: repeated runs on the same commit produce
> bit-identical candidate files. Stochastic studies take and record an explicit seed, and
> every run writes an immutable config snapshot with its run ID, config hash, git commit,
> dirty-tree flag and UTC timestamp. Two guarantees are enforced by code rather than by
> care: every long run hashes the physics package at launch and aborts if it changes
> mid-run, and a study refuses to start if the design-of-experiments screening it depends on
> was made for a different model.
>
> The study that calls a language model is reproducible in a specific sense that is worth
> stating: the *model* cannot be reproduced, but the *run* can. Every prompt and response is
> persisted, and `make ablation-replay` re-runs every evaluation from them with no model
> access and checks that the results match.

---

## Reproducing the headline numbers

From `REPRODUCIBILITY.md`. `make burn-vs-bake` on the committed baseline configuration
should reproduce:

| Quantity | Value |
|---|---|
| Candidates feasible with geometry frozen | 0 of 41 |
| Feasible on the 2-D grid | 21 of 140 |
| Peak-flux-only optimum | q″ = 37.0 W/cm², T_bond = 444.1 K |
| Joint O1 optimum | q″ = 44.3 W/cm², T_bond = 411.6 K |

If a reader gets different numbers, that is a bug and worth reporting.

> Note, 2026-09-21: this table previously read "0 of 27". `REPRODUCIBILITY.md` now reads
> "0 of 41", which agrees with `reports/milestones/M1_burn_vs_bake.md` (41 candidates, run
> `M1-20260902T130547Z`), so the table was corrected to 41. One stale "27" remains, in the
> 2026-09-02 entry of `docs/research_story.md` ("Zero of 27 trajectories"); that file is a
> dated record and is not rewritten, so the discrepancy is noted in its 2026-09-21 entry
> instead. The check against the stored `candidates.csv` row count has not been done by a
> person and should be: `[PENDING — STUDENT]`.

---

## Command index

| Command | Produces | Needs | State at `de2a834` |
|---|---|---|---|
| `make test` | verification suite | — | 497 passed, 1 skipped (2026-09-21 regeneration record) |
| `make baseline` | one nominal entry | — | run |
| `make burn-vs-bake` | M1 + M1b reports and figures | — | run `M1-20260902T130547Z` |
| `make tpi` | the §44 Thermal Penetration Index study | — | run `TPI-20260920T124732Z`, verdict DISCARD |
| `make cfd-validate` | M2 CFD validation, gate G4 | OpenFOAM, hours | run `M2-20260920T123901Z`; gate PASS, first read LIMITED (NR-25) |
| `make cfd-design-points` | M3 CFD design points | OpenFOAM, hours | run `M3-DP-20260920T1610Z`, coarse mesh, 69 usable |
| `make aero-surface RUN_ID=…` | the GP drag surface | — | `cfd_surface_v2`, row M3 LIMITED |
| `make m3-coupled RUN_ID=…` | M3 report, gate G5 | — | G5 PASS (software gate only) |
| `make doe` | screening and sensitivity | — | run `M4-DOE-20260920T204844Z`, Fidelity 1 |
| `make optimize` | Pareto fronts | a current `make doe` | run `M4-OPT-20260920T205252Z` |
| `make ablation` | M5 AI-versus-conventional study | Claude Code CLI signed in | run `M5-ABL-20260920T211134Z`; a fresh run gives new numbers |
| `make ablation-replay RUN_ID=…` | the same study with no model access | — | two strict replays, 0 prompt mismatches |
| `make adaptive` | M6 adaptive fidelity | OpenFOAM, G4 = PASS, current DOE | run `M6-AF-20260920T211148Z` with `SKIP_LLM=1`; H2 NOT_SUPPORTED; `ai_adaptive` arm not run |
| `make robust` | M7 robust optimisation | current DOE, hours | run `M7-ROBUST-20260920T211216Z` |
| `make uncertainty` | M7 propagation, Sobol' attribution, §39 table | a robust run | run `M7-UQ-20260920T233048Z`; like-for-like robust cell `M7-LFL-20260921T011854Z` |
| `make figures` | every figure from the last run | — | run |
| coupon experiment (`experiments/thermal_coupon/`) | blind thermal prediction | a printed, instrumented coupon | `[PENDING — STUDENT]`: not run |

---

## What a stranger cannot reproduce, and why it is said out loud

- **The CFD results, without OpenFOAM.** The repository records the version actually used
  (v2512, not the v2606 the specification names; nothing was installed or upgraded for the
  work), and every case keeps its dictionaries, force history and log tails, so the inputs are
  auditable even where the run is not repeatable.
- **The language-model calls.** Replay reproduces the recorded run. A fresh `make ablation`
  will give different numbers, and that is a property of the object being studied.
- **Wall times.** Everything was measured on one fanless laptop, frequently while other work
  was running. The numbers are what to budget from, not a benchmark.
- **The physical experiment.** It has not been run.

---

## Archiving checklist, before any submission

- [ ] Repository is public, or archived with a DOI, at a specific commit.
- [ ] That commit is stated in the paper, the brief and the poster, and they all state the
      same one.
- [ ] The working tree was **clean** at that commit. Several existing reports carry a "dirty
      working tree" flag in their header, which is honest but should not be true of the final
      artefacts.
- [x] Every `[PENDING FINAL RUN]` in `docs/submission_package/` and the paper has been filled
      from the result files (2026-09-21). What remains is marked `[PENDING — STUDENT]`: the
      experiment, external review, the public location, and the review counts.
- [ ] Result directories referenced by the paper are present, including the aborted and
      rejected ones (`results/M5/M5-ABL-20260920T141724Z/` with its "do not analyse" README,
      `results/M6/M6-DRY-*/ABORTED.md`, `results/M2/M2-20260920T123535Z/`). A repository that
      ships only its successful runs is a different and less honest repository.
- [ ] `REPRODUCIBILITY.md` runtimes match the machine actually used.
- [ ] `AI_USAGE.md` review status is current at the submission date.
- [ ] No secret, key, token or personal contact detail is anywhere in the repository or its
      history.
