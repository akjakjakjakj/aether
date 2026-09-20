# Authorship and AI disclosure

Spec §49. This statement accompanies every submission, in full where there is room and in the
short form below where there is not. It is not a footnote.

**Status: skeleton.** The substance is final. The two slots that depend on work not yet done
are marked.

---

## Full statement

> **Authorship.** This is an independent capstone project. All of the work is the author's
> own in the sense that matters for a research claim: the author is responsible for every
> statement in it, has decided what the project would and would not claim, and is expected to
> be able to explain and defend every result without assistance. Where that responsibility is
> not yet fully discharged, this document says so rather than implying otherwise.
>
> **What was not the author's.** The research question, the locked objective, the three
> hypotheses and the frozen scope were set out in a project specification the author received
> and accepted. In particular, the framing that motivates the whole project, that minimising
> peak heat flux may not produce the thermally safest entry, came from that specification and
> not from an observation made during the work. This is stated in the first entry of
> `docs/research_story.md` for the same reason it is stated here: it is the single most
> load-bearing fact about the authorship of this project.
>
> **AI assistance.** Most of the software in this repository was written by Claude, through
> Claude Code, working from that specification. This includes the atmosphere, trajectory,
> heating and conduction models; the CFD pipeline; the optimisation, surrogate and
> uncertainty machinery; the test suite; and the figure and report generators. Several
> modelling decisions that change results were also proposed by the model and accepted by the
> author. `AI_USAGE.md` records this item by item in four categories: AI-generated and
> student-reviewed, AI-proposed and student-approved, student-authored, and external.
>
> **Review status is tracked honestly.** Rows in `AI_USAGE.md` marked *review pending* mean
> the author has not yet read that code line by line and understood it. They change only when
> that has happened, not when a milestone is declared complete.
> `[PENDING — the current count of reviewed against unreviewed components, from
> AI_USAGE.md at submission time.]`
>
> **Defects introduced by AI-generated code are recorded, not hidden.** At least five are
> documented in `docs/negative_results.md`: a divergent radiating boundary condition, a
> thermal solve truncated in a way that understated the project's own headline result by
> about 50 K, an inverted Pareto dominance test, a variance-estimator error that produced
> impossible confidence intervals, and a surrogate classifier that returned NaN and silently
> stopped an optimiser from optimising. Each is kept because the debugging is part of the
> research record and because it is the honest measure of what unreviewed generated code is
> worth.
>
> **AI as an object of study.** One part of the project measures an AI agent against
> conventional optimisation algorithms under matched evaluation budgets. The success criteria
> for that comparison were written into a configuration file before any run, every prompt and
> response is persisted, and a replay mode reproduces the recorded run without any model
> access. `[PENDING FINAL RUN — the study has not been run, and no claim about AI
> performance is made anywhere.]`
>
> **What AI did not contribute.** The research question, the hypotheses, the frozen scope,
> the decision that the bondline rather than the surface is the interesting failure mode, and
> the judgement about what this project is allowed to claim.
>
> **No text in the scientific paper is presented as the author's own writing when it is
> not.** Where AI assistance was used in drafting, it is disclosed in the same place as the
> code disclosure rather than separately.

---

## Short form

For forms with a character limit, and for the footer of the poster and the brief:

> Most of the software in this project was written with AI assistance (Claude, via Claude
> Code) from a project specification that also set the research question and hypotheses.
> What was AI-generated, what was AI-proposed and accepted, what the author wrote, and which
> components the author has and has not yet reviewed line by line, are recorded in
> `AI_USAGE.md`. Five defects introduced by generated code are documented in
> `docs/negative_results.md` rather than removed.

---

## One-line form

For a figure caption or a slide footer:

> Software written with AI assistance; disclosure and review status in `AI_USAGE.md`.

---

## Rules for using this

1. **Never omit it** from an artefact that carries a result.
2. **Never shrink it below the size of the reproducibility line** it sits next to.
3. **Never soften "most of the software"** into "some tooling" or "assisted by". The
   proportion is the honest part.
4. **Never claim a review that has not happened.** The pending count comes from
   `AI_USAGE.md` at submission time, not from an estimate.
5. **Do not describe this project as reviewed, validated or endorsed by any person or
   institution.** If an external review has happened, the honest phrasing is "reviewed on
   `<date>`; the criticism and the response are recorded in `docs/external_reviews/`".
6. **No venue, competition, award or acceptance is named** unless it has actually occurred.
7. **No statement about admissions value appears here or in the paper.** Spec §51.

---

## Why this is written the way it is

A disclosure that reads as a legal hedge invites the reader to skip it. This one is written
to be read, and it is written to survive the obvious follow-up question, which is: *if an AI
wrote it, what did you do?*

The answer this project can honestly give is that the author is accountable for every claim,
that the boundary between what was generated and what was understood is tracked rather than
asserted, and that the parts not yet understood are named. That answer is better than a
vaguer one, and it is only available because the tracking exists.

The parts that are still weak are also named: `AI_USAGE.md` still carries *review pending*
rows, and closing them is item 12 of `docs/final_quality_gate.md`, which is the item that
nobody else can do for the author.
