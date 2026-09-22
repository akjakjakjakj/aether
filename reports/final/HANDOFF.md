# Hand-over to the student

2026-09-21, commit `de2a834`. Written by the AI assistant. Short on purpose.

## What is done

Every simulation study in the specification has run, and each returned an answer under a
criterion written down before it ran.

- M1 to M7 are complete, with generated reports in `reports/milestones/` and three
  hand-written companions (the M5 agent audit, the M6 and M7 addenda).
- The paper is drafted: `reports/final/AETHER_paper.md`, all twenty §40 sections, every
  number traced to a file.
- The paper is typeset (2026-09-22): `make paper` (or `reports/final/build_paper.sh`) turns
  the markdown into `reports/final/AETHER_paper.pdf` — A4, numbered sections, figures and
  tables, table of contents, the draft-status banner kept on page 1. It needs `pandoc`,
  `tectonic` and `pdfinfo`; the fonts are macOS system faces (Charter, Avenir Next, Menlo,
  STIX Two Math). The figure set is 24 body figures (the 13 the draft already carried, the
  seven infographics from `reports/figures/infographics/`, and four OpenFOAM flow-field
  figures from `reports/figures/cfd/`) plus an Appendix A gallery of the remaining eight
  flow-field figures with their `INDEX.md` captions. Rebuild after editing the markdown;
  the build reads nothing under `src/`, `configs/` or `results/`. The build files are
  `reports/final/paper_build/` (Lua filter, LaTeX preamble, title block).
- The submission package, the defence questions, the quality gate, the status, the README
  and the roadmap are filled and current.
- Thirty-five negative results are written up. They are the strongest thing in the project.
  Read `docs/negative_results.md` before you read anything else.

**The project is not complete.** By the specification's own final gate, three items are
unmet and all three are yours: the blind experiment, external criticism, and owning the work
(`docs/final_quality_gate.md`).

## What only you can do, in order

| # | What | Time, as estimated in the repository | Where |
|---|---|---|---|
| 1 | Read the Tier 1 code: `evaluate.py`, `tps/conduction1d.py`, `geometry/stagnation_gradient.py`, `heating/sutton_graves.py`, each with its theory note | about 6 hours | `docs/ai_usage_proposed_update.md` |
| 2 | Make the three decisions below | none given | next section |
| 3 | Read Tiers 2 and 3 | about 5 hours each; about 16 hours in all, four to six sittings | same file |
| 4 | Run the coupon experiment | none given for the whole. The long calibration step alone is about an hour per run for a 10 mm coupon, and doing both flux calibrations costs "one extra afternoon" | `experiments/thermal_coupon/protocol.md` |
| 5 | Ask one person to review the assumptions (form R1; needs no CFD background) | none given | `docs/external_reviews/` |
| 6 | Rewrite the paper and the spoken scripts in your own words, checking each number against the file named beside it; then `make paper` to re-typeset the PDF | none given | `reports/final/AETHER_paper.md` → `reports/final/AETHER_paper.pdf` |
| 7 | Choose a public location, tag a clean commit | none given | `docs/submission_package/reproducibility_links.md` |

Two habits while reading, from the reading plan. Move each `AI_USAGE.md` row from *review
pending* to *student-reviewed* on the day you finish the file, never in a batch. And try the
matching question in `docs/defense_questions.md` before you open the file, then check.

On the experiment, the one step that cannot be repaired afterwards: **write down the
tolerance that will count as agreement, and commit it, before the validation runs.** Then
freeze, predict both cases, commit and push, and only then measure.

## Three decisions waiting on you

**1. The deceleration limit.** A flat 12 g is in no NASA document. It decides the feasible
region. Option A: keep it and call it an emergency envelope; every stored result stays
valid, and "feasible" then means survivable in a contingency. Option B: adopt the
NASA-STD-3001 duration curve for a deconditioned crew; measured on the M1b grid, 10 g leaves
4 of 140 designs and 8 g leaves none, and the evaluator would need a pulse-duration metric
it does not have. This is a choice about what vehicle this is, so it is yours.
(`ASSUMPTIONS.md`, under A-LIM-1b.)

**2. The twenty-two AI-proposed decisions, including the ones added today.** `AI_USAGE.md` lists
them as *student-approved pending*. Several change a physical model: the effective-nose-radius
model (worth 20% on peak flux at the front), the unchanged Sutton–Graves constant, the
forebody-only CFD domain, the mass-closure constraint at 1.0, the whole uncertainty
inventory. Four decide what you will do in the laboratory. Today's table adds the frozen
shoulder, the unre-scored H2 criterion and the like-for-like robust column. Approve or
reject each. Inheriting them silently is the failure the ownership item exists to prevent.

**3. Whether to accept the coarse-mesh drag surface.** Everything from M4 onward uses a
surface built on the coarse mesh, under a CFD gate that first read LIMITED and reads PASS
because of a restart rule written after the first results were seen (NR-25). The evidence
for accepting it: six coarse-to-medium pairs differ by at most 0.411%; the surrogate and
mesh terms carry at most 0.02 of any output's variance; C_D at peak heating varies by 0.1%
across the front. The alternative is the all-medium design, estimated at about 8 hours of
CFD and not run. If you accept it, say so and say why. If you do not, the gate reads LIMITED
and M4 to M7 need re-running.

## Five sentences to be able to say from memory

1. In my model, the entry that minimises peak heat flux is the one with the hottest
   bondline: across the range of entry angle I tested, every step that cooled the surface
   heated the bondline, because a long mild pulse has time to diffuse through the insulator
   and a short hard one is radiated away first.
2. On the final physics, the design at the knee of the Pareto front runs about 15 K cooler
   at the bondline than the peak-flux-only optimum for about 21 kW/m² more peak flux, and
   across 3000 paired draws of everything I declared uncertain it was cooler every time, by
   14.3 K with a spread of 1.5 K.
3. That is a result about how steeply to enter, not about what shape to build: every design
   on the front has the same geometry, fixed by placeholder limits, and its heat shield is
   346 kg of a 350 kg vehicle, which is not a real vehicle.
4. My third hypothesis, that choosing CFD runs adaptively would save CFD runs, was not
   supported: no arm reached the target, I had set the target out of reach, extra CFD
   changed nothing measurable, and the AI-guided arm was never run; the language-model
   optimiser got ahead early and ended in no measured difference, and I cannot separate its
   head start from what it already knew.
5. None of this is validated against a measurement: the coupon experiment has not been run,
   nobody outside the project has reviewed it, the heating above 86 km and the wall
   catalycity are outside what my heating model can describe, and most of the code was
   written by an AI and I am still reading it.

When the fifth sentence stops being true, change it.

## Things in the repository that are stale or contradict each other

**Fixed in a 2026-09-21 consistency sweep, after this file was first written:**
`VALIDATION_MATRIX.md` (M1 row now `LIMITED` with the Fidelity-1/uncertainty confirmation
noted, not `PASS`; closing paragraphs now describe `cfd_surface_v2`; the M6 and M7 harness
rows now read historically; the §44 row now cites NR-10); `REPRODUCIBILITY.md` (test count,
Fidelity-1 status, ablation-completion status, the `make uncertainty-report` warning, all
re-verified against the tree); `AI_USAGE.md` standing rule 5 (re-measured after all: 23,869
lines of Python, 6,587 of tests — running `find ... | xargs cat | wc -l` needs no code
execution) and every `1.65` sigma-inflation mention this sweep could find outside a dated
historical record; the fourteen-vs-real AI-proposed-decision count (real count: twenty-two,
reconciled across this file, `AI_USAGE.md`, `docs/final_quality_gate.md` and
`docs/submission_package/authorship_and_ai_disclosure.md`); a dated note added to both
`reports/final/paper_outline.md` (superseded by the paper) and the Tauber entries below.

**Still open, left untouched — yours to fix or to ask for:**
- `docs/research_story.md`, 2026-09-02: "Zero of 27 trajectories". The M1 report says 0 of
  41. Noted in the 2026-09-21 entry; the old entry is not rewritten.
- `reports/final/paper_outline.md` and `reports/final/sections/*.md` are the pre-study
  outline and drafts. They still say the studies have not run and that there are 24 negative
  results. They are superseded by the paper and were left as the record of what was drafted
  when; `paper_outline.md` now carries a dated note saying so.
- Tauber, NASA TP-2914: one notebook entry says it was read, the sourcing report and the
  matrix say it was not. **Not resolved** — a dated note now stands in both
  `docs/engineering_notebook/2026-09-20_effective_nose_radius.md` and
  `docs/validation/sourcing_report.md` recording the contradiction rather than picking a
  side. The paper rests nothing on it. Only opening the document closes it.
- The paper's abstract is about 330 words; the package's target was 200 to 250.
