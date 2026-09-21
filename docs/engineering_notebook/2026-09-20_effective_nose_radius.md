# 2026-09-20 — Is there a real ceiling on the nose-radius lever, and what does it cost the M4 front?

## Question

NR-15: `evaluate_design` feeds Sutton–Graves `effective_nose_radius_m = nose_radius_m`, so
heating goes as `1/√R_n` with no ceiling, and 54 of the 64 M4 front designs ended up
pressed against `max_bluntness_ratio = 1.2` — a placeholder. Is there a **citable,
quantitative** engineering relation for the effective nose radius of a shallow spherical
segment with a corner radius? If so, what does it do to those 64 designs, and can the
fence be replaced by a geometry bound?

Spec §42 freezes new physics except to resolve a demonstrated O1 validation failure. This
is that case, and it is the only ground the change stands on.

## Hypothesis

Written before the literature search returned anything:

1. A relation exists in the 1959–1966 blunt-body literature, and it will be expressed as a
   dimensionless **velocity gradient**, not as an effective radius — so converting it will
   be my inference and will have to be labelled as such.
2. The front sits at `R_n/R_b` = 2.354–2.396, `R_c/R_b` = 0.200 (measured from the
   candidate log before searching). That is a shallow cap — the sphere sweeps only 20–21°
   from the tip. If saturation is real, `R_eff` there should be well below `R_n`, so the
   correction should **raise** peak flux and bondline, not lower them.
3. The most likely way to be wrong: if `R_eff` saturates near ~3.3 `R_b`, then at
   `R_n/R_b ≈ 2.37` the cap radius is already *below* that asymptote, and the correction
   could plausibly go the other way. This is why the relation has to come from data and
   not from the asymptote alone.
4. Whether the fence can go depends on whether `dq″/dR_n` changes sign or merely flattens.
   If it only flattens, the optimiser still wants a flatter nose and something must still
   stop it — just not a model fence.

**Falsifier declared up front:** if no primary could be opened that supports a
quantitative relation, nothing gets implemented, the fence stays, and this entry records
the failed search.

## Action

1. Two parallel literature passes against NTRS, DTIC and the publishers. Four primaries
   were obtained and read at 400–600 dpi (the OCR text layer on both 1960s scans is
   unusable): **NASA TM X-1067** (Zoby & Sullivan 1965), **NASA TN D-5121** (Ellison
   1969), **NASA TN D-4799** (Zoby 1968), **NASA TP-2914** (Tauber 1989). Ellison's
   Table I was transcribed directly from the rendered page, and TM X-1067's eqs. (3)–(5),
   its validity statements and its 11%/22% corner-effect numbers were read off the page
   rather than taken from a summary.

   > **Note, 2026-09-21.** This entry says NASA TP-2914 was obtained and read.
   > `docs/validation/sourcing_report.md` records it as **not opened** (❌ T3), and
   > `VALIDATION_MATRIX.md` G2′ says the same. This project cannot tell which record is
   > correct from the files alone — the contradiction is left standing rather than
   > silently resolved in either direction. No claim in the paper rests on TP-2914
   > (`reports/final/AETHER_paper.md`). The student should open the document and settle
   > which record was wrong.
2. Implemented `src/aether/geometry/stagnation_gradient.py`: `R_b/R_eff` interpolated over
   Ellison's nine α = 0 values plus an exact hemisphere anchor, PCHIP in `K = R_b/R_n`,
   linear in `R = R_c/R_b`. Wired into `CapsuleGeometry.effective_nose_radius_m` behind
   `effective_nose_radius_model`, which defaults to the legacy `cap_radius`.
3. Split the **geometric** nose radius from the **effective** one inside `evaluate_design`,
   so the bluntness constraint stays a statement about geometry rather than quietly
   becoming one about the heating model.
4. 49 tests: exactness at every tabulated point, both limits, monotonicity, continuity
   across the `K = 1` seam, agreement with the second primary inside its own documented
   disagreement, module-table-vs-provenance-file pinning, and bit-for-bit reproduction of
   the persisted M1 run under the default.
5. `scripts/reevaluate_m4_front.py`: rebuilt the 64-design front from the M4 candidate log
   and re-evaluated every design **twice in one process**, once per model, so the reported
   delta is attributable to the switch and nothing else. Did **not** re-run M4.

## Expected

Peak flux and bondline up on all 64; `R_eff < R_n`; the marginal value of extra bluntness
above 1.2 much reduced but still positive.

## Observed

**Hypothesis 1 was wrong in a useful way.** Zoby & Sullivan define the effective radius
*themselves* (their eq. 5), and Zoby later published a Sutton–Graves-form correlation with
`R_eff` substituted in (TN D-4799 eq. 1). The substitution AETHER is making is the original
author's, not an inference — which is a stronger position than expected.

**Hypothesis 3 — the way I expected to be wrong — did not happen.** The asymptote argument
would have been misleading: `R_eff` at the front's proportions is **1.64 `R_b`**, far below
the 3.16 `R_b` flat-face asymptote, because the asymptote is approached slowly. The
correction went the predicted direction.

**Every front design landed on a tabulated point.** All 64 sit at `K` = 0.417–0.425 and
`R_c/R_b` = 0.200 — essentially exactly Ellison's measured (0.417, 0.2) body. Zero
extrapolation. That was luck, not design, and it is the single best thing about this
result: the correction rests on interpolation of ~nothing.

| quantity | legacy | corrected |
|---|---|---|
| `R_eff / R_n` | 1.0 | **0.685 – 0.693** |
| peak heat flux | 0.202 – 0.244 MW/m² | **0.243 – 0.294 MW/m²** (+20.2 – 20.8%) |
| peak bondline | 386.9 – 412.0 K | **393.7 – 421.2 K** (+6.7 – 9.1 K) |
| feasible | 64 / 64 | **64 / 64** |

The legacy arm reproduced the logged M4 numbers to 2.4×10⁻⁵ relative on flux and
8.7×10⁻⁴ K on bondline — the residue of that run's `git_dirty: true`, measured rather than
assumed.

**Hypothesis 4: the gradient flattens, it does not change sign.** A flatter nose is still
always better, so something must still stop it — but the *amount* on offer collapses:

| bluntness change | legacy | corrected |
|---|---|---|
| 1.2 → 1.26 (geometry refuses) | −2.41% flux | **−0.92%** |
| 1.2 → infinitely flat | **−98.90%** | **−21.31%** |

An infinitely flat nose shedding 98.9% of the stagnation flux is the failure in one number.

## Evidence

- `results/M4/nose-model-recheck/` — per-design table and summary, both arms.
- `tests/test_stagnation_gradient.py` — 49 tests, all passing; full suite 318 passed,
  1 skipped; ruff clean.
- `data/reference/stagnation_velocity_gradient.yaml` — provenance, verbatim quotations,
  and the digitised TM X-1067 cross-check.
- `docs/theory/effective_nose_radius.md` — derivation and the worked number.

## Interpretation

The fence at 1.2 was never a design limit; it was the edge of a model's validity used as a
constraint, exactly as NR-15 said. The corrected model is valid over `K ≤ 1`, i.e. every
bluntness ≥ 0.5, which is the whole reachable range — so there is nothing left to fence
off, and `max_bluntness_ratio` is now `null`. What stops the nose flattening is
`CapsuleGeometry.validate()` refusing a cap that does not fit inside the body, about 1.26
at a 70° cone, returned as an infeasible candidate that stays in the log. NR-15 closed.

Two things I did not go looking for and consider more important than the headline number:

**The uncertainty got worse, honestly.** Ellison states his data disagree with Zoby &
Sullivan by about 20% at `K = 0.417` — which is precisely where the front sits. That is
±10% on heat flux, larger than the Sutton–Graves constant's own ±4%, and it is now the
dominant stated uncertainty on the heating chain. Ellison is the conservative of the two
and is what the model uses. Replacing a model that was *qualitatively* wrong with one
carrying an honest ±10% is still a large improvement, but the ±10% must be propagated in
M7 rather than quietly dropped.

**The fix moved the exploit rather than removing it.** A rounder corner now *raises*
stagnation heating, so the optimiser will want a sharp shoulder — worth 1.45% of peak flux
across `shoulder_ratio`'s box, more than bluntness still has left above 1.2. And a sharp
shoulder is exactly where real vehicles are damaged, which this stagnation-point-only model
(A-HEAT-4) cannot see at all. The fence at 1.2 has effectively been replaced by a lower
bound on `shoulder_ratio`, doing the same job for the same reason. Writing that down before
the run instead of finding it in the audit afterwards is the whole point of A-OPT-11.

## Next

1. **The M4 screening decision is void.** `shoulder_ratio` was frozen on a Sobol
   total-order index of exactly zero; it is no longer zero. `make doe` must be re-run
   before `make optimize`, not reused. Flagged in `configs/design_space.yaml` beside the
   variable.
2. **The M4 front is superseded, not reinterpreted.** It was generated with the fence in
   place and 54 of 64 designs sitting on it. The re-evaluation here says what the corrected
   model does to *those* designs; it does not say where the corrected front lies. That is
   the coordinator's re-run after the CFD surrogate lands.
3. **Propagate ±10% on the effective radius in M7**, alongside A-HEAT-1's ±4%.
4. **Chase Rodrigues (2026), DOI 10.2514/1.T7458** — "Closed-Form Reconstruction of
   Zoby–Sullivan Stagnation-Point Heat-Flux Scaling". Its title describes exactly the
   published fit that would replace this project's own interpolation. Paywalled; needs
   institutional access or an author request.
5. **Watch the `shoulder_ratio` lower bound** in the next optimisation audit, the way the
   bluntness cap was watched in this one.
