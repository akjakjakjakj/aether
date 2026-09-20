# R1 — Review of assumptions and scope

**Template. Not filled in. No review has taken place.**

Copy this file to `R1_assumptions_<YYYY-MM-DD>.md` before use and leave this blank.

---

## Administrative

| Field | Value |
|---|---|
| Review date | |
| Reviewer background (field and level only, no name) | |
| Repository state reviewed (git commit) | |
| Documents actually read | |
| Time spent | |
| Reviewer consents to being acknowledged? (yes / no / anonymous) | |

---

## What this review is for

The project's conclusions cannot be better than its assumptions. This review asks whether
the assumptions are (a) written down, (b) justified, (c) signed, meaning that the direction
of the error they introduce is stated, and (d) whether any of them quietly decides the
result.

The reviewer is **not** being asked to check arithmetic or read code. The primary documents
are:

- `ASSUMPTIONS.md` — every assumption with justification and the direction of its error.
- `CLAUDE.md` §§2–4 — frozen scope, locked objective O1, and the three hypotheses.
- `docs/validation/sourcing_report.md` — which numbers have primary sources and which do
  not, tiered ✅ T1 / 🟡 T2 / ❌ T3.
- `reports/milestones/M1_burn_vs_bake.md` — the one result that is final.

### Prompts for the reviewer

Use any that are useful; ignore the rest. Answering three of these well is worth more than
answering all of them briefly.

**On the question itself**

1. Is "peak heat flux versus in-depth bondline response" a real engineering trade, or an
   artefact of how this particular stack was set up?
2. The project claims the bondline, not the surface, is the interesting failure mode. Is
   that true of real vehicles, or true only of non-ablating stacks?
3. The scope excludes ablation entirely (A-TRAJ-3). Does that make the study
   uninteresting, or does it make it cleaner?

**On the assumptions with the most leverage**

4. A-LIM-1b: the deceleration limit is 12 g, and the repository establishes that **no
   document states a flat 12 g**. It records two options (relabel it as an emergency
   envelope, or adopt NASA-STD-3001's duration-dependent deconditioned curve, which empties
   the feasible region). Which would you take, and what does the answer imply about what
   kind of vehicle this is?
5. A-TPS-7: the TPS material properties are engineering placeholders "of the right order
   for a low-density insulator over an aluminium-like structure", not the properties of any
   qualified material. Does that undermine the result, or only its absolute numbers?
6. A-HEAT-4: the whole TPS is analysed at the stagnation-point condition. Real vehicles are
   frequently damaged at the shoulder or afterbody. How much does this limitation cost the
   conclusion?
7. A-ATM-2 and NR-14: 5–20% of a feasible design's integrated heat load accrues above
   86 km, where the atmosphere is a log-interpolated transcribed table and the heating
   correlation is being applied to transitional flow. Is that acceptable for the stated
   claim?
8. A-GEO-3a: the effective-nose-radius model interpolates nine measured points from a 1969
   NASA report, and **the interpolation is this project's own construction**, not a
   published fit. The two primary sources disagree by about 20% exactly where the designs
   sit. Is carrying that as an uncertainty the right call, or should one source have been
   picked?

**On what is missing**

9. Which assumption is *not* in `ASSUMPTIONS.md` that should be?
10. Which assumption, if you corrected it, would change the sign of the result rather than
    its magnitude?
11. Is anything in this project overclaimed? Point to a sentence.

**On scope**

12. Spec §42 freezes new physics except to resolve a demonstrated validation failure in O1.
    The effective-nose-radius correction was made on that ground (NR-15). Was that
    legitimate, or is it scope creep with a justification attached?

---

## 1. Criticism

*Reviewer's own words. Written by the reviewer. Not summarised, not paraphrased, not
edited for tone.*

| # | Criticism | Severity (blocking / major / minor / note) |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |

*Free text:*

---

## 2. Student response

*Written by the student, after the review, in the student's own words. One entry per
criticism above. Where a response needs a number, the number is measured, not estimated,
and its source is given.*

| # | Response | Agree / partly / disagree |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |

---

## 3. Changes made

*What actually changed in the repository. A row here requires a file path and a commit
hash. "Noted" is acceptable. "Will fix later" is not a change.*

| # | File(s) changed | Commit | What changed |
|---|---|---|---|
| | | | |

---

## 4. Unresolved issues

*Criticism that was understood and not acted on, with the reason. Expected to be
non-empty.*

| # | Issue | Why it is unresolved | What would resolve it |
|---|---|---|---|
| | | | |

---

## 5. Reviewer's overall judgement (optional)

*One paragraph, reviewer's words. This is not a grade and is not quoted anywhere as an
endorsement.*
