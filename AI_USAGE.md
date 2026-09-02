# AI usage disclosure

This project was built with AI assistance (Claude, via Claude Code). Hiding that would
be dishonest and would also make the work impossible to defend. This file records what
was AI-generated, what was reviewed, and what the student must be able to explain
unaided.

## Categories

- **AI-generated, student-reviewed** — written by the model, read line by line and
  understood by the student.
- **AI-proposed, student-approved** — an engineering or modelling decision suggested by
  the model and accepted by the student after considering it.
- **Student-authored** — the student's own decision or writing.
- **External** — from a cited published source.

## Current state (2026-09-02, after M1)

| Item | Category | Note |
|---|---|---|
| Research question and hypotheses H0/H1/H2 | External / student-approved | Framed in the capstone specification (`CLAUDE.md`, `docs/AETHER_Capstone_Specification.md`), which the student received and accepted as the frozen scope. |
| USSA-76 implementation | AI-generated, **review pending** | Layer constants are from the published standard. The >86 km table is transcribed and unverified — see VALIDATION_MATRIX G1A′. |
| 3-DOF equations of motion | External | Standard planar entry equations. The student must be able to derive dγ/dt, including the V²cos γ / r centrifugal term. |
| Sutton–Graves implementation | AI-generated, **review pending** | Constant not yet re-derived from NASA TR R-376. |
| 1-D conduction solver (FV, backward Euler, harmonic interfaces) | AI-generated, **review pending** | The student must be able to explain why the scheme is conservative and why backward Euler was chosen. |
| Newton linearisation of the radiating boundary | AI-proposed, student-approved | Proposed in response to an actual divergence: a fixed-point sweep on T⁴ blew up on the first run. Recorded in `docs/negative_results.md` NR-01. |
| Post-entry soak-out phase | AI-proposed, student-approved | Proposed after observing that truncating the thermal solve at the trajectory's end understated the bondline peak by ~50 K. NR-02. |
| Sizing the TPS to 15 mm | AI-proposed, student-approved | At the original 40 mm the bondline never responded within the entry, which would have hidden the effect under a design margin nobody would actually fly. NR-03. |
| Verification tests | AI-generated, student-reviewed | The analytical benchmark (Carslaw & Jaeger §2.9) is external. |
| `pareto_front` dominance test | AI-generated, **defect found and fixed** | The first implementation was wrong and produced a non-monotone "front". Caught by looking at the figure. NR-04. |
| Figures and reports | AI-generated from data | No number in any report is typed by hand; all are read from the result files. |

## Standing rules for this project

1. **No result is reported that the student cannot explain.** `docs/defense_questions.md`
   is the checklist.
2. **Review status is tracked honestly.** Rows above marked *review pending* are exactly
   that. They will be changed only when the student has actually read and understood
   the code, not when the milestone is declared done.
3. **The AI does not decide physics.** Every modelling choice that changes a result is
   recorded here with the reason it was accepted.
4. **Negative results stay.** Four AI-introduced problems are recorded in
   `docs/negative_results.md` rather than quietly fixed, because the debugging is part
   of the research record.

## What the AI did *not* contribute

The research question, the choice of hypotheses, the frozen scope, and the decision that
the bondline rather than the surface is the interesting failure mode. Those came from
the project specification.
