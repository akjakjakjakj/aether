#!/usr/bin/env python3
"""One-shot edit of reports/final/AETHER_paper.md: insert the new figure set and
renumber the existing figure captions. Touches only figure embeds and captions.
Every anchor must match exactly once, or the script aborts without writing.
Kept for the record; re-running on the edited file is a no-op guard (it aborts)."""
from pathlib import Path
import sys

P = Path(__file__).resolve().parents[1] / "AETHER_paper.md"
t = P.read_text(encoding="utf-8")

if "01_burn_vs_bake_mechanism" in t:
    sys.exit("already applied")

edits: list[tuple[str, str]] = []

def fig(n, path, cap):
    return f"![Figure {n}](../figures/{path})\n\n*Figure {n}. {cap}*\n"

# --- 1. Introduction: infographic 1 after the timescale paragraph -----------------
anchor = "A heat shield with no spare insulation sits in that regime, because spare insulation is mass.\n"
edits.append((anchor, anchor + "\n" + fig(1, "infographics/01_burn_vs_bake_mechanism.png",
    "Burn versus bake, the mechanism: a shallow entry lowers peak heat flux by 38.3% and raises the peak bondline temperature by 114.1 K (M1, Fidelity 0, run `M1-20260902T130547Z`). Explanatory figure: the heat-flux and in-depth histories are re-derived through `evaluate_design()` from the run's configuration snapshot and the scalars are asserted equal to `candidates.csv`; legacy cap-radius nose model, as the M1 run used. File `reports/figures/infographics/01_burn_vs_bake_mechanism.png`.")))

# --- 2. Methods: infographic 2 after the canonical-evaluator paragraph -----------
anchor = "the provenance block and the velocity history (`reports/milestones/M3_coupled_model.md` §10).\n"
edits.append((anchor, anchor + "\n" + fig(2, "infographics/02_pipeline_validation.png",
    "The pipeline and what is validated against what. Gate statuses are the validation matrix's own (`VALIDATION_MATRIX.md`, 2026-09-21); G4 `PASS` carries its restart history (§8.2). Box descriptions paraphrase the matrix's validation-source column; no number on the figure is typed by hand. Sources: `results/M2/M2-20260920T123901Z/gate_assessment.json`, `results/M4/M4-OPT-20260920T205252Z/summary.json`, `results/M7/M7-UQ-20260920T233048Z/summary.json`, `ARCHITECTURE.md`. File `reports/figures/infographics/02_pipeline_validation.png`.")))

# --- 7. Burn-vs-bake: renumber 1,2,3 -> 3,4,5 ------------------------------------
edits.append(("![Figure 1](../figures/M1_anticorrelation.png)\n\n*Figure 1. ",
              "![Figure 3](../figures/M1_anticorrelation.png)\n\n*Figure 3. "))
edits.append(("![Figure 2](../figures/M1_mechanism.png)\n\n*Figure 2. ",
              "![Figure 4](../figures/M1_mechanism.png)\n\n*Figure 4. "))
edits.append(("![Figure 3](../figures/M1b_feasible_region.png)\n\n*Figure 3. ",
              "![Figure 5](../figures/M1b_feasible_region.png)\n\n*Figure 5. "))

# --- 8. CFD: three flow-field figures before the mesh-convergence plot (4 -> 9) ---
anchor = "![Figure 4](../figures/M2_mesh_convergence.png)\n\n*Figure 4. "
new_cfd = (
    fig(6, "cfd/M2_sphere_M6_fine_fourpanel.png",
        "Sphere, R = 0.5 m, M∞ = 6, fine mesh (refinement factor 4, 49,152 cells), the max-Courant-0.1 solution of record after NR-25, saved iteration 110,000: Mach number, p/p∞, T/T∞ and ρ/ρ∞ in the meridional plane, one flat-shaded polygon per cell, run `M2-20260920T123901Z`, case `sphere_M6_fine_Co0p1`. rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, T∞ = 220 K. White line: sonic line M = 1 from the cell-centre triangulation; it bounds the subsonic nose region and also runs along the captured shock, where M passes through 1 inside the one to two cells of numerical shock thickness. Dashed: Billig's correlation for the shock shape, an independent empirical curve, not a fit. Δ: shock stand-off from `case_result.json` (50% density-rise point on the stagnation line). Colour bars: viridis (Mach, ρ/ρ∞), magma (p/p∞), cividis (T/T∞). Within its tested assumptions this CFD is used for forebody pressure drag, surface pressure and perfect-gas shock shape only; it is not used for shock-layer temperatures or heating of any kind (§8.1). File `reports/figures/cfd/M2_sphere_M6_fine_fourpanel.png`.")
    + "\n" +
    fig(7, "cfd/M2_sphere_M6_mesh_levels.png",
        "Mach number for the sphere at M∞ = 6 on the coarse, medium and fine meshes (refinement factors 1, 2, 4; saved iterations 10,000, 20,000 and 110,000), common colour scale (viridis, 0 to M∞), run `M2-20260920T123901Z`, cases `sphere_M6_coarse`, `sphere_M6_medium`, `sphere_M6_fine_Co0p1`. Cell edges are drawn on the coarse and medium meshes so the refinement is visible; on the fine mesh (49,152 cells) they would blacken the panel and are omitted. The fine panel is the max-Courant-0.1 restart of record (NR-25); coarse and medium ran at max Courant 0.2. C_D,fore and Δ/R are read from each `case_result.json`. Same gas model and freestream as Figure 6. File `reports/figures/cfd/M2_sphere_M6_mesh_levels.png`.")
    + "\n" +
    fig(8, "cfd/M2_sphere_stagnation_line_profiles.png",
        "Sampled cell values of p/p∞, T/T∞, ρ/ρ∞ and Mach number along the symmetry axis (`postProcess sampleLine`) for the sphere at M∞ = 3 and 6 on the three meshes, each at its final iteration (15,000, 20,000 and 110,000 at Mach 3; 10,000, 20,000 and 110,000 at Mach 6; the fine curves are the max-Courant-0.1 restarts of record), run `M2-20260920T123901Z`. Thin vertical lines: the shock stand-off Δ of each mesh (50% density-rise point, `case_result.json`); dashed: the Billig (1967) stand-off correlation, which is cited but not verified in primary by this project (§20). Line style and colour distinguish the meshes. Same gas model and freestream as Figure 6. File `reports/figures/cfd/M2_sphere_stagnation_line_profiles.png`.")
    + "\n" +
    "![Figure 9](../figures/M2_mesh_convergence.png)\n\n*Figure 9. "
)
edits.append((anchor, new_cfd))

# --- 9. Coupled model: design-point grid before Table 5; 5 -> 11 -------------------
anchor = "Scale invariance was measured: the same shape at 1.2 m and 3 m gives identical C_D,fore to the digits printed.\n"
edits.append((anchor, anchor + "\n" + fig(10, "cfd/M3_design_point_grid_mach.png",
    "Mach-number fields for six design-point shapes at M∞ = 3, 6, 20 and 27 on the coarse mesh (refinement factor 1, 3,072 cells), forebody domain from the nose to the maximum-radius station closed by a supersonic outflow, D = 1.2 m, each panel at its case's final saved iteration (in its title), run `M3-DP-20260920T1610Z`. Colour: viridis, one scale per column (0 to M∞); thin white line: sonic line; C_D,fore from each `case_result.json`. Rows 5 and 6 are the two shapes that stayed `REJECTED` under NR-27 at Mach 20 (force criterion never met in two consecutive blocks at Courant 0.2, 0.1 and 0.05) and, as NR-28 records, at Mach 27; their fields are the final saved solution of the last Courant restart, shown for what they are and not on the drag surface. There is no Mach-12 column: the design sampled Mach 12 (and Mach 6, except the baseline scale-check case `sc1p2`) only at fill-point shapes, so no usable case exists for these six shapes there. `dp062` at Mach 27 crashed in all three domain attempts without writing a second-order field (NR-28; Figure A.7). Outlines are drawn to the maximum-radius station only, where the domain ends. Same gas model and freestream as Figure 6; a calorically perfect γ = 1.4 gas is the wrong gas at Mach 20 to 27 and is carried as a declared ±5% band on C_D,fore (A-CFD-12). File `reports/figures/cfd/M3_design_point_grid_mach.png`.")))
edits.append(("![Figure 5](../figures/M3_constant_vs_surface.png)\n\n*Figure 5. ",
              "![Figure 11](../figures/M3_constant_vs_surface.png)\n\n*Figure 11. "))

# --- 10. Optimization: 6 -> 12, 7 -> 13; infographic 3 closes §10.4 ---------------
edits.append(("![Figure 6](../figures/M4_doe_sobol.png)\n\n*Figure 6. ",
              "![Figure 12](../figures/M4_doe_sobol.png)\n\n*Figure 12. "))
edits.append(("![Figure 7](../figures/M4_pareto_front.png)\n\n*Figure 7. ",
              "![Figure 13](../figures/M4_pareto_front.png)\n\n*Figure 13. "))
anchor = "H1 is supported within the model by the same mechanism as §7. It is not evidence that joint optimisation finds a better capsule shape.\n"
edits.append((anchor, anchor + "\n" + fig(14, "infographics/03_pareto_front_fences.png",
    "What the optimiser found: the combined feasible front of §10.2 is an entry-angle curve at a geometry fixed by fences, with the robust knee of §13.5 and its 95th-percentile whiskers. Explanatory figure. The fences are drawn in objective space as pickets hugging the front; they are constraints in design space and the picket positions are illustrative, while the counts on them are the audit's (§10.3). Sources: `results/M4/M4-OPT-20260920T205252Z/candidates.csv` and `summary.json`, `results/M7/M7-LFL-20260921T011854Z/likeforlike.json`, `results/M7/M7-UQ-20260920T233048Z/summary.json`, `results/M7/M7-ROBUST-20260920T211216Z/robust_front.csv`, `reports/milestones/M4_pareto_optimisation.md`. File `reports/figures/infographics/03_pareto_front_fences.png`.")))

# --- 11, 12: 8 -> 15, 9 -> 16 -----------------------------------------------------
edits.append(("![Figure 8](../figures/M5_hypervolume.png)\n\n*Figure 8. ",
              "![Figure 15](../figures/M5_hypervolume.png)\n\n*Figure 15. "))
edits.append(("![Figure 9](../figures/M6_cfd_spend_map.png)\n\n*Figure 9. ",
              "![Figure 16](../figures/M6_cfd_spend_map.png)\n\n*Figure 16. "))

# --- 13. Uncertainty: infographic 5 after the inventory paragraph; 10,11,12 -> 18,19,20
anchor = "Density dispersions below 86 km are NASA-published standard deviations [28]; those above are this project's conversion of observed ranges.\n"
edits.append((anchor, anchor + "\n" + fig(17, "infographics/05_uncertainty_sources.png",
    "Where the uncertainty comes from: 84 to 99% of the output variance is epistemic, and the two dominant bondline terms (TPS conductivity, heating above 86 km) are engineering judgment. Explanatory figure; tier and aleatory/epistemic labels are the inventory's own fields, read from `results/M7/M7-UQ-20260920T233048Z/summary.json` (attribution, propagation decomposition, uncertainty model). Every spread shown is a lower bound (§13.1). File `reports/figures/infographics/05_uncertainty_sources.png`.")))
edits.append(("![Figure 10](../figures/M7_pbox.png)\n\n*Figure 10. ",
              "![Figure 18](../figures/M7_pbox.png)\n\n*Figure 18. "))
edits.append(("![Figure 11](../figures/M7_attribution.png)\n\n*Figure 11. ",
              "![Figure 19](../figures/M7_attribution.png)\n\n*Figure 19. "))
edits.append(("![Figure 12](../figures/M7_robust_vs_nominal.png)\n\n*Figure 12. ",
              "![Figure 20](../figures/M7_robust_vs_nominal.png)\n\n*Figure 20. "))

# --- 17. Negative results: timeline after the intro; 13 -> 22; gate history in §17.5
anchor = "It sits before the conclusion because several numbers above cannot be read correctly without it.\n"
edits.append((anchor, anchor + "\n" + fig(21, "infographics/06_negative_results_timeline.png",
    "The negative-results timeline: the thirty-five entries of `docs/negative_results.md` in four kinds, with five called out. Explanatory figure; titles are the file's verbatim headings, dates are from `git log -S` on that file, and the grouping by kind is the rendering script's own classification, labelled as such on the figure. File `reports/figures/infographics/06_negative_results_timeline.png`.")))
edits.append(("![Figure 13](../figures/TPI_weighting_and_profile.png)\n\n*Figure 13. ",
              "![Figure 22](../figures/TPI_weighting_and_profile.png)\n\n*Figure 22. "))
anchor = "which moved the observed order from 0.67 and 0.60 to 1.13 and 0.88.\n"
edits.append((anchor, anchor + "\n" + fig(23, "infographics/07_gate_G4_history.png",
    "Gate G4 history: `LIMITED` to `PASS` by lowering the maximum Courant number from 0.2 to 0.1 on the fine-mesh cases; the restart rule was written after the first result had been seen and is disclosed (NR-25, §8.2). Explanatory figure read from `results/M2/M2-20260920T123901Z/gate_assessment.json`, `gate_assessment_20260921_0057_before_restarts.json`, `gci.csv`, `gci_20260921_0057_before_restarts.csv` and `config_snapshot.yaml`. File `reports/figures/infographics/07_gate_G4_history.png`.")))

# --- 18. Conclusion: scorecard after the H2 paragraph -----------------------------
anchor = "its early lead cannot be separated from prior knowledge.\n"
edits.append((anchor, anchor + "\n" + fig(24, "infographics/04_hypothesis_scorecard.png",
    "Hypothesis scorecard: H0 supported in the tested domain; H1 supported narrowly; H2 not supported; the optimiser comparison of §11 mixed. Explanatory figure; the caveat text paraphrases §4 of this paper and every numeral is read from a file: `results/M1/M1-20260902T130547Z/candidates.csv`, `results/M4/M4-OPT-20260920T205252Z/summary.json`, `results/M7/M7-UQ-20260920T233048Z/paired_difference.json`, `results/M6/M6-AF-20260920T211148Z/summary.json`, `results/M5/M5-ABL-20260920T211134Z/summary.json`, `reports/milestones/M6_adaptive_fidelity.md`. File `reports/figures/infographics/04_hypothesis_scorecard.png`.")))

# --- Appendix A: the remaining eight gallery figures, INDEX captions --------------
appendix = """
---

## Appendix A. CFD flow-field gallery

Generated by `scripts/render_cfd_gallery.py` (`make cfd-gallery`) from the case directories under `cfd/generated/` and the result tables under `results/`. Every figure is written as PNG and vector PDF. Colour scales are perceptually uniform (viridis / magma / cividis) and stated on each colour bar. All fields are drawn in the meridional plane (x, r), axis equal, one flat-shaded polygon per cell of the wedge mesh (no interpolation). "Time step" is the saved iteration of the local-time-stepping pseudo-time march. The index of all twelve gallery figures, with cases and saved iterations, is `reports/figures/cfd/INDEX.md`; four of them appear in the body (Figures 6, 7, 8 and 10). Within its tested assumptions the CFD is used for forebody pressure drag, surface pressure and perfect-gas shock shape only (§8.1).

""" + fig("A.1", "cfd/M2_sphere_M3_fine_fourpanel.png",
    "Run `M2-20260920T123901Z`, case `sphere_M3_fine_Co0p1`, sphere R = 0.5 m, M∞ = 3, fine mesh (refinement factor 4, 49,152 cells), max Courant 0.1, the solution of record after NR-25, saved iteration 110,000: Mach number, p/p∞, T/T∞ and ρ/ρ∞. rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, T∞ = 220 K. One flat polygon per cell. White line: sonic line M = 1 from the cell-centre triangulation; it bounds the subsonic nose region and also runs along the captured shock, where M passes through 1 inside the one to two cells of numerical shock thickness. Dashed: Billig's correlation for the shock shape (independent empirical curve, not a fit). Δ: shock stand-off from `case_result.json` (50% density-rise point on the stagnation line). Colour bars: Mach viridis, p/p∞ magma, T/T∞ cividis, ρ/ρ∞ viridis. File `reports/figures/cfd/M2_sphere_M3_fine_fourpanel.png`.") + "\n" + fig("A.2", "cfd/M2_sphere_M3_limit_cycle_field.png",
    "Run `M2-20260920T123901Z`, sphere R = 0.5 m, M∞ = 3, fine mesh (49,152 cells), cases `sphere_M3_fine`, `sphere_M3_fine_cyclediag`, `sphere_M3_fine_Co0p1`. rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, T∞ = 220 K. (a) Per-cell standard deviation of p over the 100 snapshots of the cycle-diagnosis continuation of the max-Courant-0.2 case (written every 2 iterations), divided by the per-cell mean: the fluctuation is smallest around the stagnation point and grows along the body in ray-like bands from the captured shock toward the supersonic outflow (NR-25). (b) The same case's difference between its two last saved fields, a two-phase sample of the oscillation. (c) The max-Courant-0.1 restart of record, difference between its two last saved fields, on the same colour scale; the intervals differ (20,000 against 5,000 iterations), so read the level, not a ratio. The two-time difference does not separate the two Courant numbers by its maximum (5.0×10⁻² against 2.0×10⁻², both in the cells the captured shock straddles near the outflow corner); it does by its level inside the shock layer: median 1.6×10⁻³ against 2.4×10⁻⁴, and 58% against 19% of the layer's cells above 10⁻³. \"Shock layer\" = cells with ρ/ρ∞ > 1.5 at the later saved iteration. (d) p/p∞ of record. Colour: cividis, log₁₀ clipped to [−4.5, −1]; magma for p/p∞. File `reports/figures/cfd/M2_sphere_M3_limit_cycle_field.png`.") + "\n" + fig("A.3", "cfd/M2_sphere_M6_limit_cycle_field.png",
    "As Figure A.2, for M∞ = 6: run `M2-20260920T123901Z`, cases `sphere_M6_fine`, `sphere_M6_fine_cyclediag`, `sphere_M6_fine_Co0p1`, fine mesh (49,152 cells). Same gas model and freestream. The two-time difference does not separate the two Courant numbers by its maximum (1.1×10⁻¹ against 1.2×10⁻¹, both in the cells the captured shock straddles near the outflow corner); it does by its level inside the shock layer: median 3.6×10⁻³ against 9.0×10⁻⁴, and 76% against 47% of the layer's cells above 10⁻³. \"Shock layer\" = cells with ρ/ρ∞ > 1.5 at the later saved iteration. (d) p/p∞ of record. Colour: cividis, log₁₀ clipped to [−4.5, −1]; magma for p/p∞. File `reports/figures/cfd/M2_sphere_M6_limit_cycle_field.png`.") + "\n" + fig("A.4", "cfd/M2_sphere_cp_meshes.png",
    "Run `M2-20260920T123901Z`, cases `sphere_M3_coarse`, `sphere_M3_medium`, `sphere_M3_fine_Co0p1`, `sphere_M6_coarse`, `sphere_M6_medium`, `sphere_M6_fine_Co0p1`, sphere R = 0.5 m, three meshes (coarse ×1, medium ×2, fine ×4 = the max-Courant-0.1 restart of record), surface pressure sampled at each case's final iteration (15,000, 20,000, 110,000 at Mach 3; 10,000, 20,000, 110,000 at Mach 6). rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, T∞ = 220 K. C_p = (p − p∞)/q∞. Dashed: modified Newtonian theory C_p = C_p,max cos²θ with C_p,max from the exact Rayleigh-pitot relation, an analytical estimate for comparison, not a validation reference. Line style and colour distinguish the meshes. File `reports/figures/cfd/M2_sphere_cp_meshes.png`.") + "\n" + fig("A.5", "cfd/M2_demo_capsule_M6_fields.png",
    "Run `M2-20260920T123901Z`, case `capsuledemo_M6_x2_a1`: a generic blunted 60° cone (nose R 0.6 m, D 1.2 m; not a flown vehicle, not a validated result), M∞ = 6, medium mesh (refinement factor 2, 12,288 cells, sizing radius 1 m), saved iteration 30,000: Mach number, p/p∞ and T/T∞. rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, T∞ = 220 K. White: sonic line. Red: shock stand-off Δ from `case_result.json`; blue: distance from the captured shock to the fixed-value inflow boundary on the axis (x_inflow = −0.313 m), the clearance NR-26 is about: the first attempt in the sphere-sized domain, `capsuledemo_M6_x2` (sizing radius 0.6 m), failed in the solver and wrote no field. C_D,fore = 1.3967. Colour: viridis / magma / cividis. File `reports/figures/cfd/M2_demo_capsule_M6_fields.png`.") + "\n" + fig("A.6", "cfd/M3_design_point_cp.png",
    "Run `M3-DP-20260920T1610Z`, cases `sc1p2_coarse_a0`, `dp017_coarse_a0`, `dp057_coarse_a0`, `dp001_coarse_Co0p05`, `dp007_coarse_a0`, `dp011_coarse_Co0p05`, `dp061_coarse_Co0p05`, coarse mesh (3,072 cells), D = 1.2 m, surface pressure sampled at each case's final iteration (15,000, 10,000, 20,000, 105,000, 15,000, 135,000, 135,000). rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, T∞ = 220 K. C_p = (p − p∞)/q∞ against arc length from the nose over the diameter; the left panels show the same outlines in the same colour and line style. Series tagged `[REJECTED]` are the two NR-27 shapes: their C_p is the last Courant restart's final save and is not on the drag surface. At Mach 6 only the baseline shape (scale-check case `sc1p2`) exists. File `reports/figures/cfd/M3_design_point_cp.png`.") + "\n" + fig("A.7", "cfd/M3_mach27_dp062_startup_failure.png",
    "Runs `M3-DP-20260920T1610Z` (top row: `dp062_coarse_a2`, the design-point attempt of record) and `M3-mach27-startup-exp` (bottom row: `dp062_A_fo6000`, the NR-28 isolation run with a 6,000-iteration first-order start), point `dp062`, M∞ = 27, coarse mesh (3,072 cells): T/T∞, Mach number and kinetic-energy fraction of the first-order start-up solution. rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, T∞ = 220 K. What survives is only the field written at the end of the first-order (upwind) start-up, iteration 1,500 and 6,000 respectively. The van Leer hand-over then diverged with a floating-point exception in sqrt (a negative temperature) at iteration 1,567 and 6,085 respectively, and a crashed run writes no field: the cell where the temperature went negative is not recorded anywhere on disk and cannot be shown. The saved first-order fields contain no cell below T∞ (minimum T = 220 K), so they hold no precursor either. The third column shows the mechanism NR-28 names: the kinetic energy is above 99% of the total energy in the freestream and stays dominant through the thin attached shock layer along the 20° cone, so a small error in total energy is a large relative error in c_v T. Other attempts, all without a post-hand-over field: `dp062_coarse_a0` died at iteration 1,528; `dp062_coarse_a1` at 1,554; `dp063_coarse_a2` at 1,601; `dp062_B_fo1500_co01` at 1,569; `dp062_C_fo6000_co01` at 6,047. Colour: cividis (T/T∞, energy fraction), viridis (Mach). File `reports/figures/cfd/M3_mach27_dp062_startup_failure.png`.") + "\n" + fig("A.8", "cfd/M6_adaptive_promotions_mach.png",
    "Run `M6-AF-20260920T211148Z`, adaptive arm, coarse mesh (3,072 cells), D = 1.2 m, forebody domain, M∞ = 20, each panel at its case's final saved iteration (title): Mach number. rhoCentralFoam, axisymmetric Euler, calorically perfect gas γ = 1.4, p∞ = 1000 Pa, T∞ = 220 K. A promotion is a candidate the adaptive policy sent to CFD instead of trusting the Fidelity-1 surface (`promotion_log.json` reason for every adaptive promotion: \"promising, and the cheap model is untrusted here\"; none was outside the arm's hull). Every usable case is appended to that arm-and-seed's own surface, which is re-fitted (`counters.json` surface history): `af2a27042848_coarse_a0`, seed 37, usable, surface training set 69 → 70 → 71 → 72 → 74 points over the run; `af5e13e211ab_coarse_a0`, seed 37, usable, 69 → 70 → 71 → 72 → 74; `af01fbe28a96_coarse_a0`, seed 67, usable, 69 → 70 → 71 → 72; `af1376216f0b_coarse_Co0p05`, seed 37, rejected, 69 → 70 → 71 → 72 → 74. The rejected case never met the force criterion in two consecutive blocks at Courant 0.2, 0.1 and 0.05 (the NR-27 rule); its field is the last Courant restart's final save, shown but not used. White: sonic line. Colour: viridis. File `reports/figures/cfd/M6_adaptive_promotions_mach.png`.")

anchor = "- NSGA-II and ParEGO are named as algorithms (the former through the pymoo library). No primary source for either was opened.\n"
edits.append((anchor, anchor + appendix))

# --- apply, with every anchor checked ---------------------------------------------
for old, new in edits:
    n = t.count(old)
    if n != 1:
        sys.exit(f"anchor matched {n} times, aborting:\n{old[:120]!r}")
for old, new in edits:
    t = t.replace(old, new, 1)

# sanity: figure captions numbered 1..24 in order, then A.1..A.8
import re
nums = re.findall(r"^\*Figure ([0-9]+|A\.[0-9]+)\. ", t, flags=re.M)
expect = [str(i) for i in range(1, 25)] + [f"A.{i}" for i in range(1, 9)]
if nums != expect:
    sys.exit(f"caption sequence wrong: {nums}")
embeds = re.findall(r"^!\[Figure ([0-9]+|A\.[0-9]+)\]", t, flags=re.M)
if embeds != expect:
    sys.exit(f"embed sequence wrong: {embeds}")

P.write_text(t, encoding="utf-8")
print(f"applied {len(edits)} edits; {len(nums)} figures")
