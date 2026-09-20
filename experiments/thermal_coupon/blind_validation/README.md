# Blind validation — the commit-before-measuring discipline

> **Nothing has been predicted yet, because nothing has been calibrated yet, because the
> experiment has not been run.** This directory currently holds the machinery and this
> document. `predictions/` will appear when there is something to archive.

---

## Why this directory exists separately

Spec §47 asks for an *unseen validation case*, in this order:

1. calibration experiments
2. **freeze model parameters**
3. generate a prediction for an unseen heating history
4. **archive and timestamp the prediction before measurement analysis**
5. run the experiment
6. compare predicted and measured T(x,t)

Steps 2 and 4 are the whole value of the exercise, and they are the two that are easiest
to skip without noticing. A model that has seen the answer will match the answer. The
usual way this goes wrong is not fraud — it is an honest afternoon spent "checking a
parameter" after glancing at the measurement, followed by a fit that agrees beautifully
and means nothing.

Physically separating the prediction step into its own directory, with its own entry
point and its own refusals, is what makes the order auditable afterwards.

---

## The discipline

**Every one of these is a git commit, in this order. No exceptions, no amendments, no
rebases that reorder them.**

```
commit 1   the calibration data and the fit
           data/cal_*.csv + .meta.yaml
           results/calibrated_parameters.yaml

commit 2   the FROZEN parameters
           blind_validation/frozen_parameters.yaml

commit 3   the DECLARED case files - heating histories only, no temperatures
           data/val_a_case.csv + .meta.yaml
           data/val_b_case.csv + .meta.yaml

commit 4   the PREDICTIONS and their manifests   <-- push this one
           blind_validation/predictions/prediction_val_*.csv
           blind_validation/predictions/manifest_val_*.json

           ==== ONLY NOW DO YOU TURN THE HEATER ON ====

commit 5   the measurements
           data/val_a.csv, data/val_b.csv + .meta.yaml

commit 6   the comparison
           results/comparison_val_*.md + .json
           reports/figures/M8_*.png / .pdf
```

**Push commit 4 before the experiment.** A local commit proves order to you; a pushed
commit proves it to a reader. The git history is the archive — the manifest's timestamp
and hashes are what make the archive *checkable*, but the commit is what makes it
*dated by someone other than you*.

Predict **both** cases, A and B, before running **either**. Predicting A, running A, then
predicting B is not a blind test of B: you have seen how the model does on A and you will,
unavoidably, have opinions.

---

## What the manifest pins

`make_prediction.py` writes a JSON manifest alongside every prediction containing:

- a UTC timestamp and the git commit the prediction was made at, plus whether the working
  tree was dirty;
- the SHA-256 of the **frozen parameter file**, so the prediction is bound to one exact
  fit;
- the SHA-256 of the **declared case CSV and its sidecar**, so it is bound to one exact
  heating history;
- the SHA-256 of the **code** that computed it — `coupon_model.py`, `make_prediction.py`
  and `conduction1d.py`;
- the SHA-256 of the **prediction file itself**.

`compare_model.py` re-hashes the prediction before it computes a single metric. If the
file changed after it was archived, the comparison is stamped **VOID** in its own report
rather than quietly reporting a good fit.

### What this does and does not protect against

It proves **order and identity**: this prediction, from these parameters, for this
heating history, from this code, existed at this commit. That is what §47 asks for.

It does **not** protect against a determined faker. Anyone with the repository can re-run
the script and re-commit. What makes that hard is the push in commit 4 and the fact that
a pushed history is awkward to rewrite quietly. The honesty here is a discipline
supported by evidence, not a cryptographic guarantee, and saying so is part of reporting
it properly.

---

## The three refusals

`make_prediction.py` refuses rather than warns, in three situations. Each one is a real
way the blindness gets lost.

| Refusal | The failure it blocks |
|---|---|
| Parameter file not marked `frozen: true` | Predicting from a fit that is still being adjusted |
| Declared case CSV contains any `t_ch*` column | Pointing the script at the measurement file — the easiest accident of the three |
| The named `--measurement` path already exists | Predicting after the experiment and calling it a prediction |

The third can be overridden with `--allow-existing-measurement`, because there are
legitimate reasons — re-deriving an old prediction to check a code change, for instance.
If you use it, **write why into the engineering-notebook entry for that run.** An
override with no recorded reason is indistinguishable from the thing it exists to
prevent.

---

## If the prediction is wrong

That is a result, and it is the more interesting one. Do not re-fit and re-freeze and
present the second attempt as the first.

1. Keep the failed comparison. It goes in `docs/negative_results.md` with the residual
   plot (spec §31).
2. Look at the **shape** of the residual before its size. Scatter is sensor noise. A
   trend is model error, and no value of any parameter would have fixed it — which
   tells you something the RMSE does not.
3. If you then re-calibrate, the new frozen file is a **new** file with a new hash, and
   the next prediction needs a **new** unseen case. A case that has already been
   measured is no longer unseen, whatever you do to the parameters afterwards.

A model that missed the blind case and was honestly reported is worth more, in this
repository, than one that matched because it had already been shown the answer.
