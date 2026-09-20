# Cover note template — asking someone to review this project

Spec §48. A template for the message that goes **with** a review request. Fill the angle
brackets, delete what does not apply, and keep it short. A reviewer who is handed a summary
reviews the summary, so the note points at documents rather than restating conclusions.

The reading guide below is the part that earns the reviewer's time. Do not remove it.

---

## Template

> Subject: Would you spend an hour trying to break a school research project?
>
> Hello <name>,
>
> I am a Class-12 student working on an independent capstone in re-entry aerothermodynamics,
> and I am looking for someone to criticise it rather than to help with it. I am asking you
> because <one specific, honest reason: your work on X, you teach Y, you have built Z>.
>
> **The question.** A re-entry vehicle is normally designed against peak heat flux, the
> worst instant of heating on the outer surface. The heat shield does not fail at the
> surface; it fails at the bondline, where the thermal protection meets the structure, and
> the bondline responds to the time integral of what got past the surface rather than to the
> peak. Those two quantities are not minimised by the same trajectory. The project tries to
> establish that quantitatively with a verified reduced-order model, and to find out whether
> optimising both jointly finds designs that optimising the peak alone would miss.
>
> **What I want from you.** Not corrections and not help. The one question I would like
> answered is: *what would you not believe, and why?* Anything you find, I will record with
> my response and with whether I actually changed anything, in
> `docs/external_reviews/`. Criticism I could not act on gets recorded as unresolved rather
> than quietly dropped.
>
> **What I should warn you about up front**, so you do not spend your time rediscovering
> things I already know are weak:
>
> - Every optimisation result is at reduced fidelity, with a constant drag coefficient. The
>   CFD-derived drag model exists but is provisional and switched off.
> - The CFD validation gate has not passed: mesh independence is incomplete and no published
>   blunt-body case has been compared.
> - No physical experiment has been run. The thermal coupon has not been printed.
> - Several constraint limits and material properties are engineering placeholders, and the
>   assumptions file says which.
> - Most of the code was written by an AI assistant. `AI_USAGE.md` records which parts I
>   have read line by line and which I have not.
>
> The most useful thing you could do is attack something that is *not* on that list.
>
> **If you have 30 minutes**, this order gets you to the real content fastest:
>
> | Order | Document | Why |
> |---|---|---|
> | 1 (5 min) | `README.md` | The question, and what is explicitly out of scope |
> | 2 (5 min) | `reports/milestones/M1_burn_vs_bake.md` | The one result that is final, including the two sections that argue against my own numbers ("How much this rank correlation is actually worth", "Do not quote the margin as a ratio") |
> | 3 (10 min) | `ASSUMPTIONS.md` | Every assumption with the direction of the error it introduces. This is where the project is most likely to be wrong |
> | 4 (5 min) | `VALIDATION_MATRIX.md` | What has actually been checked against an outside reference, and what has not. `LIMITED` is never reported as `PASS` |
> | 5 (5 min) | `docs/negative_results.md`, any two entries | What broke and why it was kept. NR-15 and NR-12 are the two I would pick |
>
> **If you have longer**, `docs/research_story.md` records how the question changed, and
> `docs/defense_questions.md` is what I claim to be able to answer without help. Asking me
> any three of those, plus three of your own, would be more useful to me than almost
> anything else.
>
> **Practicalities.** There is a blank form at
> `docs/external_reviews/<R1_assumptions | R2_cfd_validation | R3_research_defence>.md` with
> prompts, but writing in the margins or sending me a list is equally fine; I will transcribe
> it. I will not put your name in the repository. If you would like to be acknowledged in
> the final write-up I will ask you separately and only with your explicit permission.
> Nothing you say will be described as an endorsement, and the project will not be described
> as "reviewed by" or "validated by" anyone.
>
> Repository: <link, or attached PDF export>
>
> Thank you either way.
>
> <student name>

---

## Notes for the student, not to be sent

- **Ask for criticism, not approval.** The phrasing above is deliberate. A reviewer asked to
  "take a look" will say it looks good.
- **Send the real thing.** A summary invites a review of the summary.
- **Give the warning list.** It is the difference between an hour spent on the documented
  weaknesses and an hour spent on the undocumented ones.
- **Pick the right form.** R1 needs no CFD background and can be done by a physics teacher
  or an engineer in any discipline. R2 needs someone who has run a solver. R3 needs someone
  willing to ask hard questions out loud.
- **Do not send all three at once.** One review done properly beats three skimmed.
- **Do not argue in the reply.** Thank them, ask factual clarifying questions only, and put
  the arguments in section 2 of the form after you have gone and checked.
- **Record it the same week.** A review transcribed from memory a month later is a
  paraphrase, and a paraphrased review is the student's words wearing the reviewer's name.
