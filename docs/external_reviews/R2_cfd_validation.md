# R2 — Review of CFD, verification and validation

**Template. Not filled in. No review has taken place.**

Copy this file to `R2_cfd_validation_<YYYY-MM-DD>.md` before use and leave this blank.

---

## Administrative

| Field | Value |
|---|---|
| Review date | |
| Reviewer background (field and level only, no name) | |
| Repository state reviewed (git commit) | |
| Gate G4 status at time of review | |
| Documents actually read | |
| Time spent | |
| Reviewer consents to being acknowledged? (yes / no / anonymous) | |

---

## What this review is for

Verification asks whether the equations are being solved correctly. Validation asks whether
they are the right equations. This project separates the two deliberately, and this review
asks whether the separation is honest and whether the gate criteria are the right criteria.

Primary documents:

- `VALIDATION_MATRIX.md` — every gate, its method, its source, its tolerance, its status
  and its evidence path. The status values are `NOT_STARTED` / `IN_PROGRESS` / `PASS` /
  `FAIL` / `LIMITED`, and the rule is that `LIMITED` is never reported as `PASS`.
- `docs/validation/M2_model_form_limits.md` — what the CFD may and may not be used for.
- `reports/milestones/M2_cfd_validation.md` — the CFD validation run (generated file).
- `reports/milestones/M3_coupled_model.md` — the CFD-derived drag surface (generated file).
- `docs/theory/sutton_graves_constant.md` and `docs/theory/effective_nose_radius.md` — the
  two heating-chain derivations.
- `docs/negative_results.md` NR-05 … NR-09 and NR-19 … NR-23 — every way the CFD broke.

### Prompts for the reviewer

**On the gate itself**

1. Spec §17 requires four things before CFD may feed an optimisation: mesh independence,
   force convergence, a published blunt-body comparison, and written model-form limits. Are
   those the right four? Is anything missing that you would refuse to proceed without?
2. The force-convergence criterion is peak-to-peak ≤ 0.1% and half-window drift ≤ 0.02% of
   the mean over the last 2000 iterations, declared before the runs. Is that tight enough?
   Too tight? NR-09 and NR-21 record cases that missed it and were **not** let in; NR-21's
   `dp032` and `dp043` sat at 0.109% with essentially zero drift, which looks like a steady
   limit cycle a hair outside the band. Was rejecting them right?
3. Residuals are explicitly **not** the criterion, because with a TVD limiter the density
   residual plateaus about a decade down while the integrated force has stopped moving. Is
   that a legitimate argument or a rationalisation?

**On the model**

4. The domain is **forebody only**, because an inviscid wake never reached a steady state
   (NR-06). Is abandoning the afterbody the right response, and does the base-drag
   assumption that replaces it (A-CFD-5, a *bounded* base-pressure ratio rather than a
   predicted one) do enough?
5. The solver is **inviscid** on **calorically perfect** air at Mach up to 20. The argument
   that pressure drag survives this (stagnation Cp moves only from 1.84 to 2.0) is carried
   as a declared ±5% model-form band and is stated to be an argument from theory, **not
   validated here**. Is ±5% the right size?
6. **55% of the baseline capsule's heat load accrues above Mach 20**, where the Mach-20 C_D
   value is simply held on a Mach-number-independence argument. The measured change in
   C_D,fore between Mach 10 and 20 is up to 1.80%, so it is not an identity. Is holding the
   value defensible, and what would you do instead?
7. Design points were run on the **coarse** mesh, not the medium mesh the brief asked for,
   because a full medium design measured at 7–8 hours against a ~2 hour budget (A-CFD-10).
   A seeded 8-point subset was re-run on the medium mesh, largest change 0.411%. Is a
   two-level difference on six paired cases an acceptable stand-in for a GCI?

**On what is not there yet**

8. There is **no GCI**: the report prints "GCI not available: fewer than three successful
   mesh levels at any Mach". Three downstream consumers refuse rather than guess (M3's
   discretisation band, M7's `cd_discretisation` input, gate G5). Is refusing the right
   behaviour, or is a stated conservative band better than a blocked run?
9. No published blunt-body case has been compared yet, and the sphere's measured **total**
   drag cannot be compared like-for-like because this CFD computes forebody drag only. The
   comparison that was made is against a forebody pressure-drag expression in the same AEDC
   report. Is that a validation or a consistency check?

**On the reduced-order chain, which is where the `PASS` rows are**

10. G3 (TPS conduction) is `PASS` at 0.002% against Carslaw & Jaeger §2.9 with an energy
    residual around 1e-14. Is that the right benchmark for this solver, and does passing it
    tell you what you need to know?
11. G1B (trajectory) is `PASS` by reproducing a **published disagreement** between the
    Allen–Eggers closed form and a numerical integration, to within 0.92 percentage points
    against a declared 1.0 point allowance. Is reproducing a published error the right form
    of validation here, and does matching the reference's constant-gravity model to get
    there weaken it?
12. G2 (the heating constant) is `PASS` at 0.39% against a re-derivation from the primary,
    and the constant was deliberately **not changed** (NR-12). G2′ (model form: catalycity,
    hot wall, radiation) is `LIMITED` and *not attempted*, with catalycity alone reported at
    roughly a factor of two. Is calling G2 `PASS` while G2′ is untouched misleading?

**On the surrogate**

13. The GP drag surface (`cfd_surface_v2`, extended to Mach 27 under gate G4 PASS) is fitted
    on 69 usable CFD points in four inputs, validated on an 8-point held-out set drawn before
    any case ran, and its error bars are **inflated by a measured factor of 1.21** because
    k-fold z-scores showed overconfidence (the original `cfd_surface_v1`, 56 points / 7
    held-out, used a factor of 1.65). Is a one-number recalibration adequate when the
    held-out points show a bias as well as a spread?
14. Shapes outside the convex hull of the training points are **refused**, not extrapolated
    (A-AERO-1), which means failed CFD cases shrink the usable design space. Is that the
    right trade?

---

## 1. Criticism

*Reviewer's own words.*

| # | Criticism | Gate / section it concerns | Severity (blocking / major / minor / note) |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

*Free text:*

---

## 2. Student response

| # | Response | Agree / partly / disagree |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |

---

## 3. Changes made

| # | File(s) changed | Commit | What changed | Did any published number move? |
|---|---|---|---|---|
| | | | | |

> If a change moves a number, every report that quotes it must be regenerated, not edited.
> Record the regenerating command and the new run ID.

---

## 4. Unresolved issues

| # | Issue | Why it is unresolved | What would resolve it | Blocks which gate? |
|---|---|---|---|---|
| | | | | |

---

## 5. Reviewer's judgement on the gate

*Would the reviewer sign off gate G4 in its current state? This is recorded as the
reviewer's opinion and does not itself change the gate status, which is decided by the
four declared conditions and the code that evaluates them.*

| Condition | Reviewer's view |
|---|---|
| 1. Mesh independence completed | |
| 2. Force convergence demonstrated | |
| 3. Published blunt-body case compared | |
| 4. Model-form limitations documented | |
