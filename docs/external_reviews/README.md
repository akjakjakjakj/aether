# External technical reviews

Spec §48. This directory holds **templates** and, once reviews happen, the filled-in
records of them.

**Nothing in this directory is filled in yet.** No review has been requested, received or
recorded. There are no reviewer names anywhere in this repository, and there are no
paraphrased or reconstructed reviews. A review exists here only when a real person has
actually written one.

---

## What a reviewer is for

The reviewer is a **critic and mentor, not a co-author**. They are not being asked to check
the work for the student, to fix anything, or to endorse it. They are being asked to try to
break it and to say where it breaks.

Concretely, a useful review answers one question: *what would you not believe, and why?*

The reviewer does not need to be an aerothermodynamicist. Most of the failure modes in this
project were found by someone reading a figure or asking where a number came from. A
mechanical or aerospace engineer, a physics teacher, a university student one or two years
ahead, or an experienced software engineer can each break something different here, and the
forms are written so that a reviewer can answer only the parts they are competent to answer
and say so for the rest.

---

## The three reviews

| Form | Focus | Best done when | Time to ask for |
|---|---|---|---|
| [`R1_assumptions.md`](R1_assumptions.md) | Assumptions, scope, whether the question is the right question, whether the constraints and placeholders are defensible | Any time. The earlier the better, because an assumption caught after the studies run costs the studies | 45–60 min |
| [`R2_cfd_validation.md`](R2_cfd_validation.md) | Verification and validation: the CFD model and its gate, mesh convergence, the reduced-order benchmarks, the surrogate, what the numbers are allowed to be used for | After gate G4 is PASS, or deliberately before it to check the gate criteria themselves | 60–90 min |
| [`R3_research_defence.md`](R3_research_defence.md) | The research as a whole: do the conclusions follow from the evidence, is the honesty real or performed, would the student survive questioning | Last, after the final studies have run and the paper draft exists | 90 min, plus a conversation |

Each form has the same four sections, because those four are what spec §48 requires to be
recorded:

1. **Criticism** — the reviewer's own words, written by the reviewer.
2. **Student response** — written by the student, not by the reviewer and not by an AI.
3. **Changes made** — what actually changed in the repository, with file paths and commit
   hashes. "Noted" is an acceptable entry. "Will fix" is not; either it changed or it did
   not.
4. **Unresolved issues** — criticism that was understood and *not* acted on, with the
   reason. This section existing and being non-empty is a sign of a healthy review. A
   review with nothing unresolved usually means the criticism was not taken seriously or
   was not severe enough.

---

## How to run a review

1. **Send the cover note.** [`cover_note_template.md`](cover_note_template.md) contains a
   30-minute reading guide. Send the note and the repository link (or a PDF export), not a
   summary of the work: a reviewer who is handed conclusions reviews the conclusions.
2. **Send the blank form.** Let the reviewer write in section 1 directly. Do not
   pre-populate it with questions you want asked.
3. **Do not defend during the review.** Answer factual questions about what the code does.
   Save the arguments for section 2.
4. **Write section 2 yourself, afterwards, in your own words.** If a response needs a
   number, go and get the number rather than estimating it.
5. **Do section 3 in the repository first, then record it here.** The commit hash is the
   evidence.
6. **Be honest in section 4.** Most criticism on a school-timescale project cannot be acted
   on, and saying "this is right and I did not have time to fix it" is worth more than a
   quiet omission.
7. **Save the filled form** as `R<n>_<topic>_<YYYY-MM-DD>.md` in this directory. Keep the
   blank template.

---

## Rules for this directory

- **No reviewer names, affiliations or contact details** are stored in the repository. If a
  reviewer wants to be credited, that is a separate decision made at submission time and
  recorded in `docs/submission_package/acknowledgements_template.md`, with their explicit
  permission. Anonymous-by-default is the safe direction.
- **No review is written for a reviewer.** Section 1 is transcribed from what they wrote or
  said, or it is empty.
- **No review is invented, and no review is generated.** If a section is empty, it is empty.
- **A review is not an endorsement.** Nothing in this project may be described as
  "reviewed by" or "validated by" anyone. The honest phrasing is "reviewed on <date>;
  the criticism and the response are recorded in `docs/external_reviews/`".
- **Disagreement is allowed.** If a reviewer is wrong, section 2 says so and says why, with
  evidence. Agreeing with a reviewer you think is mistaken is worse than arguing with them.

---

## What to warn a reviewer about

So they spend their time on the real weaknesses rather than rediscovering the documented
ones:

- Every optimisation result in the repository is **Fidelity 0**: constant drag coefficient.
  The CFD-derived drag surface exists, is provisional, and is switched off.
- Gate **G4 is not PASS**. Mesh independence is not complete and no published blunt-body
  case has been compared.
- **No physical measurement exists.** The thermal coupon has not been printed.
- Several constraint limits and material properties are **engineering placeholders**, and
  `ASSUMPTIONS.md` says which.
- Most of the code was **written by an AI**, and `AI_USAGE.md` records which parts the
  student has and has not yet read line by line.

The most useful review is one that attacks something *not* on that list.
