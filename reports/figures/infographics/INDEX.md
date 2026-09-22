# Infographics — index

Explanatory figures for the AETHER argument, rendered by `scripts/render_infographics.py` (`make infographics`). Each figure exists as PNG (preview), PDF and SVG (vector). Every number on a figure is read from the result file or generated report listed under it and the figure carries its run IDs in small print. Nothing under `src/`, `configs/` or `results/` is written.

| # | Figure | Files | What it says |
|---|---|---|---|
| 1 | Burn versus bake: the mechanism | `01_burn_vs_bake_mechanism.png` · `.pdf` · `.svg` | Shallow entry: -38.3% peak flux, +114.1 K bondline (M1, Fidelity 0). |
| 2 | The pipeline and what is validated against what | `02_pipeline_validation.png` · `.pdf` · `.svg` | Statuses are the validation matrix's own; G4 PASS carries its restart history. |
| 3 | What the optimiser found | `03_pareto_front_fences.png` · `.pdf` · `.svg` | The front is an entry-angle curve at a fenced geometry; robust knee with p95 whiskers. |
| 4 | Hypothesis scorecard | `04_hypothesis_scorecard.png` · `.pdf` · `.svg` | H0 supported in the tested domain; H1 supported narrowly; H2 not supported; M5 mixed. |
| 5 | Where the uncertainty comes from | `05_uncertainty_sources.png` · `.pdf` · `.svg` | 84–99% epistemic; the two dominant bondline terms are engineering judgment. |
| 6 | The negative-results timeline | `06_negative_results_timeline.png` · `.pdf` · `.svg` | 35 entries in four kinds; five called out. |
| 7 | Gate G4 history | `07_gate_G4_history.png` · `.pdf` · `.svg` | LIMITED → PASS by Courant 0.2 → 0.1; rule written after the result, disclosed. |

## Sources per figure

### 1. Burn versus bake: the mechanism

- `results/M1/M1-20260902T130547Z/candidates.csv`
- `results/M1/M1-20260902T130547Z/config_snapshot.yaml`
- `reports/milestones/M1_burn_vs_bake.md (pair count)`
- note: Histories re-derived through evaluate_design(); scalars asserted equal to the log.
- note: Legacy cap-radius nose model, as the M1 run used.

### 2. The pipeline and what is validated against what

- `VALIDATION_MATRIX.md`
- `results/M2/M2-20260920T123901Z/gate_assessment.json`
- `results/M7/M7-UQ-20260920T233048Z/summary.json`
- `results/M4/M4-OPT-20260920T205252Z/summary.json`
- `ARCHITECTURE.md`
- note: Box descriptions paraphrase the matrix's 'validation source' column; no numbers are typed.

### 3. What the optimiser found

- `results/M4/M4-OPT-20260920T205252Z/candidates.csv`
- `results/M4/M4-OPT-20260920T205252Z/summary.json`
- `results/M7/M7-LFL-20260921T011854Z/likeforlike.json`
- `results/M7/M7-UQ-20260920T233048Z/summary.json`
- `results/M7/M7-ROBUST-20260920T211216Z/robust_front.csv`
- `reports/milestones/M4_pareto_optimisation.md`
- note: Fences are drawn in objective space as pickets hugging the front; they are constraints in design space and the picket positions are illustrative — the counts on them are the audit's.

### 4. Hypothesis scorecard

- `reports/final/AETHER_paper.md §4`
- `results/M1/M1-20260902T130547Z/candidates.csv`
- `results/M4/M4-OPT-20260920T205252Z/summary.json`
- `results/M7/M7-UQ-20260920T233048Z/paired_difference.json`
- `results/M6/M6-AF-20260920T211148Z/summary.json`
- `reports/milestones/M6_adaptive_fidelity.md`
- `results/M5/M5-ABL-20260920T211134Z/summary.json`
- note: Caveat prose paraphrases the paper; every numeral is read from a file.

### 5. Where the uncertainty comes from

- `results/M7/M7-UQ-20260920T233048Z/summary.json (attribution, propagation.decomposition, uncertainty_model)`
- note: Tier and aleatory/epistemic labels are the inventory's own fields.

### 6. The negative-results timeline

- `docs/negative_results.md (headings)`
- `git log -S on that file (dates)`
- note: Kind classification is this script's (NR_KIND); titles are verbatim headings.

### 7. Gate G4 history

- `results/M2/M2-20260920T123901Z/gate_assessment.json`
- `results/M2/M2-20260920T123901Z/gate_assessment_20260921_0057_before_restarts.json`
- `results/M2/M2-20260920T123901Z/gci.csv`
- `results/M2/M2-20260920T123901Z/gci_20260921_0057_before_restarts.csv`
- `results/M2/M2-20260920T123901Z/config_snapshot.yaml`
- `docs/negative_results.md NR-25`

## Conventions

- One type system (Avenir Next → Helvetica Neue → DejaVu Sans fallback) and one palette across all seven; light background, no gradients, no shadows, no icon clip-art.
- Categorical colours are the dataviz reference slots (blue, orange, aqua, yellow), validated for adjacent-pair colour-vision-deficiency separation on a white surface; status colours (PASS green, LIMITED amber, NOT SUPPORTED red, IN_PROGRESS grey) are always paired with a text label, so nothing relies on colour alone.
- Language follows CLAUDE.md §37: model predicts, within tested assumptions, candidate. No figure claims anything about a flight vehicle or a qualified material.
- Figure 6's grouping of negative results by kind, and figure 3's picket positions in objective space, are this script's presentation choices and are labelled as such on the figures.
