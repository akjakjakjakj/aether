# Submission package

Spec §49 and §51. Source material for describing this project to people outside it: an
abstract, a two-page technical brief, a poster, two spoken explainers, an authorship and AI
disclosure, an acknowledgement template and a reproducibility section.

**State on 2026-09-21.** The simulation studies are complete (commit `de2a834`) and every
`[PENDING FINAL RUN]` slot has been filled by transcription from the result files and the
generated milestone reports. The filling was done by the AI assistant; the student has not
yet revised any of it. What is left is marked **`[PENDING — STUDENT]`** and cannot be filled
by anyone else: the coupon experiment's results, any external review, the public repository
location and release commit, and the review counts in the disclosure. The full paper is
`reports/final/AETHER_paper.md`, typeset as **`reports/final/AETHER_paper.pdf`** (`make
paper`; A4, with the 24 body figures and the Appendix A CFD gallery — the PDF is what to
attach or send, the markdown is what to edit); the hand-over note is
`reports/final/HANDOFF.md`.

One thing every artefact here must now carry, because it is the easiest thing to lose in
compression: the Fidelity-1 result is a trade in entry angle at a geometry fixed by
placeholder constraints (the knee's heat shield is 346 kg of a 350 kg vehicle), and H2 was
not supported.

---

## Files

| File | What it is | Length target |
|---|---|---|
| [`abstract.md`](abstract.md) | 200–250 words, the version that goes in a submission form | 1 paragraph |
| [`two_page_brief.md`](two_page_brief.md) | The technical brief, §51 | 2 pages including figures |
| [`poster_outline.md`](poster_outline.md) | Panel-by-panel poster source, A0 portrait | 1 sheet |
| [`explainer_90s.md`](explainer_90s.md) | 90-second spoken technical explainer | ~230 spoken words |
| [`video_outline.md`](video_outline.md) | 3–5 minute technical video | ~7 beats |
| [`authorship_and_ai_disclosure.md`](authorship_and_ai_disclosure.md) | The disclosure that accompanies every submission | 1 page |
| [`acknowledgements_template.md`](acknowledgements_template.md) | Mentor and reviewer acknowledgements | short |
| [`reproducibility_links.md`](reproducibility_links.md) | What a stranger needs to re-run this | 1 page |
| [`../../reports/final/AETHER_paper.pdf`](../../reports/final/AETHER_paper.pdf) | The full paper, typeset from `reports/final/AETHER_paper.md` by `make paper` | 56 pages incl. appendix |

---

## Binding rules for everything in this directory

These come from the specification and from the way the rest of the repository is written.
They are not stylistic preferences.

1. **The first sentence leads with the scientific question**, never with "AI", never with a
   software brand, never with the framework. Spec §51. The correct opening is about heat
   shields and where they fail. If a reader has to get to sentence four to learn what the
   project is about, the opening is wrong.
2. **No venue, competition, award, acceptance, affiliation or institutional endorsement is
   named or implied** unless it has actually happened. Spec §49. There are no placeholder
   venue names in these files, deliberately, because a placeholder venue has a way of
   surviving into a final draft.
3. **No claim about admissions value appears anywhere**, and none appears in the scientific
   paper at all. Spec §51.
4. **No number is typed by hand.** Every figure in every one of these documents is
   transcribed from a result file, and the file is named beside it. If the number is not in
   a result file, it does not go in.
5. **§37 language.** "The model predicts", "within tested assumptions", "candidate",
   "simulation suggests", "validated against X within Y%". Never "flight ready", "solves
   re-entry", "proves optimal", "eliminates heating".
6. **The limitations travel with the claim.** A brief or a poster that states the result
   without stating which fidelity it came from, that the optimised geometry is fixed by
   placeholder constraints, and that no physical measurement exists, is not a shortened
   version of this project. It is a different and less honest project.
7. **The AI disclosure is not optional and is not buried.** It appears in every artefact
   that carries a result, at a size a reader will actually see.
8. **Nothing here is described as reviewed, validated or endorsed by any person** unless a
   filled-in form exists in `docs/external_reviews/` and that person gave permission.

---

## What can be written now and what cannot

**Can be written now**, because it does not depend on a pending run:

- the question, the mechanism and why it is non-obvious;
- the method, at every fidelity level;
- the verification and validation status, which is a fact about the matrix rather than a
  result;
- the burn-vs-bake result (M1 and M1b), which is final under the legacy heating model, with
  the legacy label attached;
- the negative results;
- the AI disclosure and the reproducibility instructions.

**Written on 2026-09-21 from the final runs** (this list previously read "cannot be written
now"):

- the Pareto front under the corrected heating model and the CFD drag surface (M4 re-run);
- the AI-versus-conventional-optimiser comparison (M5);
- whether adaptive fidelity saves CFD calls (M6: not supported);
- uncertainty bands, the p-box, the Sobol' attribution and robust designs (M7);
- the §39 four-column comparison table, with the like-for-like robust column.

**Still cannot be written**, and is marked `[PENDING — STUDENT]` wherever it appears:

- the physical coupon comparison (M8), because the experiment has not been run;
- anything about external review, because none has been requested or received.

---

## Order of work when the runs finish

1. Fill `two_page_brief.md` first. It forces every number to be found and every claim to be
   bounded, and everything else is a compression of it.
2. Then `abstract.md`, which is the brief compressed to one paragraph.
3. Then `poster_outline.md`, which is the brief laid out spatially. A poster written before
   the brief tends to become decoration with numbers on it.
4. Then the two spoken pieces, which are the hardest to write last but the easiest to write
   badly first.
5. `authorship_and_ai_disclosure.md` and `reproducibility_links.md` are updated *with* the
   runs, not after them: every run ID they cite has to exist.
6. Re-read rule 6 above before sending anything.
