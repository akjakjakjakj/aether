# ABORTED RUN — DO NOT ANALYSE

Run `M5-ABL-20260920T141724Z` was **killed on purpose by the project coordinator on
2026-09-20**, part-way through the `ai_agent` phase (four seeds, 4 recorded LLM calls each;
24 prompt files were written in total; seed 59 and `ai_adaptive` never started).

Why: while it ran, another agent changed the physics under it. `src/aether/evaluate.py`
switched to a velocity-gradient effective nose radius, and `configs/design_space.yaml` now
defaults to `effective_nose_radius_model: velocity_gradient` with `max_bluntness_ratio: null`.
Worker processes import `src/aether` when they start, so candidates in `candidates.csv` may
have been evaluated by different physics depending on when their worker was spawned. The
config snapshot beside this file does NOT describe all of what ran. `shoulder_ratio` is also
no longer inert, so the M4 screening this run's active-variable list came from is void.

There is no `summary.json`, no report and no figure for this run, by design. Nothing in this
directory may be quoted, plotted, replayed as a result, or compared with anything. It is kept
only because spec section 31 says failed candidates are not deleted, and as the evidence for
`docs/negative_results.md` NR-18. The real M5 study is run once, by the coordinator, after
the CFD drag surface (M3) lands and DOE/M4 have been re-run.
