# R3 — Final research defence review

**Template. Not filled in. No review has taken place.**

Copy this file to `R3_research_defence_<YYYY-MM-DD>.md` before use and leave this blank.

This review is meant to happen **last**, after the final studies have run and a paper draft
exists. Running it earlier is possible but then the reviewer is reviewing an outline, and
the form should say so in the administrative block.

---

## Administrative

| Field | Value |
|---|---|
| Review date | |
| Reviewer background (field and level only, no name) | |
| Repository state reviewed (git commit) | |
| Which studies had actually been run at review time | |
| Paper draft version reviewed | |
| Was the review a written form, a conversation, or both? | |
| Time spent | |
| Reviewer consents to being acknowledged? (yes / no / anonymous) | |

---

## What this review is for

Not whether the software works. Whether the **research** holds: whether the conclusions
follow from the evidence, whether the honesty is real rather than performed, and whether
the student can defend the work without help.

Primary documents:

- `reports/final/paper_outline.md` and the drafted sections in `reports/final/sections/`
- `docs/research_story.md` — how the question actually developed
- `docs/negative_results.md` — everything that broke, kept deliberately
- `VALIDATION_MATRIX.md` and `ASSUMPTIONS.md`
- `AI_USAGE.md` and `docs/ai_usage_proposed_update.md`
- `docs/defense_questions.md` — what the student claims to be able to answer

### Prompts for the reviewer

**On the argument**

1. State the project's central claim in your own words. Does the evidence support the claim
   as you stated it, or a weaker version of it?
2. Where does the paper say more than its evidence allows? Point at a sentence.
3. Where does it say **less** than its evidence allows? Under-claiming is also a defect.
4. The project's one final result (M1/M1b) is a Fidelity-0 result whose absolute levels rest
   on placeholder constraint limits. Is it worth reporting on its own, or does it need the
   Fidelity-1 re-run to mean anything?
5. Is the distinction between "the mechanism is verified" and "the magnitude is
   model-dependent" maintained consistently, or does it slip?

**On honesty**

6. `docs/negative_results.md` has 24 entries and `docs/research_story.md` records the
   question changing. Does that read as genuine intellectual history, or as performed
   humility? What would distinguish the two?
7. Several disclosures are inconvenient and were made anyway: that M2's benchmark tolerances
   were written after a prototype's numbers had been seen; that M4's hypervolume reference
   was set after the evaluator had been timed on four designs; that two M5 seeds were
   removed because they had informed a design change; that the M5 patience rule was added
   after the first pass had been seen. Are there disclosures of the same kind that are
   **missing**?
8. Does anything in the repository look tuned to produce the result? The audit machinery is
   in `reports/milestones/M4_pareto_optimisation.md` §11 and the counterfactual tables.

**On the student's ownership**

9. Ask the student three questions from `docs/defense_questions.md` at random, without
   warning, and three of your own. Do the answers sound understood or recited?
10. Ask the student to derive something on paper: dγ/dt including the V²cos γ / r term, or
    the explicit stability limit Δt ≤ Δx²/(2α) with the numbers for this mesh, or why
    R_eff must sit between the body radius and the cap radius.
11. Ask the student to explain a piece of code they did not write, with the file open.
12. `AI_USAGE.md` marks some rows **review pending**. Are the rows still marked pending the
    ones you would most want the student to have read?

**On what an examiner would attack**

13. What is the single weakest point in this project, and would the student have found it
    themselves?
14. If you had to reject this work, on what grounds?
15. What would you ask that `docs/defense_questions.md` does not anticipate?

**On the write-up**

16. Does the paper's structure serve the argument or the specification's section list?
17. Are the figures doing work, or decorating? NR-04 records a figure functioning as a test;
    is that standard maintained?
18. Is the AI disclosure adequate, excessive, or in the wrong place?

---

## 1. Criticism

*Reviewer's own words.*

| # | Criticism | Section / document | Severity (blocking / major / minor / note) |
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

| # | File(s) changed | Commit | What changed |
|---|---|---|---|
| | | | |

---

## 4. Unresolved issues

| # | Issue | Why it is unresolved | What would resolve it |
|---|---|---|---|
| | | | |

---

## 5. Oral defence record

*If the review included questioning. Record the questions actually asked and, honestly,
which ones went badly. A defence rehearsal that records only the good answers is worthless
as preparation.*

| Question asked | Answered well / partly / badly | What to go and learn |
|---|---|---|
| | | |

---

## 6. Reviewer's overall judgement (optional)

*One paragraph, reviewer's words. Not a grade. Not quoted as an endorsement anywhere in the
paper, the brief, the poster or any submission material.*
