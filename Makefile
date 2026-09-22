PY := .venv/bin/python

.PHONY: all test lint baseline burn-vs-bake tpi coupon-synthetic figures validate cfd-validate cfd-report clean

all: test baseline burn-vs-bake

test:
	$(PY) -m pytest tests/ -q

validate: test

lint:
	.venv/bin/ruff check src tests scripts experiments

baseline:
	$(PY) scripts/run_baseline.py

burn-vs-bake:
	$(PY) scripts/run_burn_vs_bake.py

# Spec section 44. ~140 coupled evaluations, a couple of minutes.
tpi:
	$(PY) scripts/run_tpi_study.py

# M8 SOFTWARE CHECK ONLY - generates synthetic data and runs the calibrate -> freeze ->
# predict -> compare chain against it. Produces NO experimental evidence.
coupon-synthetic:
	$(PY) -m pytest tests/test_thermal_coupon.py -q

figures: baseline burn-vs-bake tpi

# Milestone M2 / gate G4. Needs OpenFOAM (`openfoam` launcher on PATH). Solver stages take
# HOURS; run it in the background. Not part of `all` for that reason.
#   make cfd-validate                 full study, new run ID
#   make cfd-validate RUN_ID=M2-...   resume (finished cases are loaded, not re-run)
#   make cfd-report   RUN_ID=M2-...   rebuild tables, figures and the report only
cfd-validate:
	$(PY) scripts/run_cfd_validation.py $(if $(RUN_ID),--run-id $(RUN_ID),)

cfd-report:
	$(PY) scripts/run_cfd_validation.py --stage report --run-id $(RUN_ID)

# Milestone M3: CFD design points -> drag response surface -> coupled gate G5 + report.
# Needs OpenFOAM for the first target only. `cfd-design-points` takes HOURS (coarse ~1.5 h,
# medium ~8 h on a 4-performance-core laptop): run it in the background; it is resumable.
#   make cfd-design-points                                  production level, new run ID
#   make cfd-design-points RUN_ID=M3-DP-...                 resume
#   make cfd-design-points RUN_ID=M3-DP-... LEVEL=medium SUBSET=mesh-check
#   make aero-surface RUN_ID=M3-DP-... [LEVEL=medium]       fit + cross-validate + persist
#   make m3-coupled   RUN_ID=M3-DP-...                      G5, comparison, report
# `aero-surface` builds the CURRENT surface, `cfd_surface_v2` (data/aero/cfd_surface_v2/),
# which configs/design_space.yaml selects. `cfd_surface_v1` stays on disk and registered for
# provenance; it was built while G4 was IN_PROGRESS and is refused without allow_provisional.
# A surface is served only if its own surface.json AND M2's gate_assessment.json say PASS -
# both are read, neither is typed.
.PHONY: cfd-design-points aero-surface m3-coupled
cfd-design-points:
	$(PY) scripts/run_cfd_design_points.py $(if $(RUN_ID),--run-id $(RUN_ID),) \
		$(if $(LEVEL),--level $(LEVEL),) $(if $(SUBSET),--subset $(SUBSET),)

aero-surface:
	$(PY) scripts/build_aero_surface.py $(if $(RUN_ID),--run-id $(RUN_ID),) \
		$(if $(LEVEL),--level $(LEVEL),)

m3-coupled:
	$(PY) scripts/run_m3_coupled.py --dp-run $(RUN_ID) $(if $(LEVEL),--level $(LEVEL),)

# Milestone M4. Both take minutes on 6 cores - run them in the background. `optimize`
# frees exactly the variables the latest `doe` run's screening.json left active. The
# fidelity is whatever configs/design_space.yaml's vehicle.aero.model selects
# (cfd_surface_v2 = Fidelity 1 since 2026-09-21). At Fidelity 1 `doe` first measures how much
# of the shape box the CFD hull leaves and REFUSES if the Saltelli sub-box is not inside it.
#   make optimize DOE_RUN=M4-DOE-...     pin the DOE run
#   make optimize-report RUN_ID=M4-OPT-...   rebuild summary, figures and report only
.PHONY: doe optimize optimize-report
doe:
	$(PY) scripts/run_doe.py

optimize:
	$(PY) scripts/run_optimize.py $(if $(DOE_RUN),--doe-run $(DOE_RUN),)

optimize-report:
	$(PY) scripts/run_optimize.py --report-only $(RUN_ID)

# Milestone M5 (configs/ai_ablation.yaml). Uses the latest `doe` run's active variables.
#   make ablation                        LIVE: shells out to the Claude Code CLI (`claude -p`,
#                                        signed in; no API key). Hard-capped at 80 LLM calls.
#                                        Tens of minutes - run it in the background.
#   make ablation-replay RUN_ID=M5-ABL-...   NO LLM access needed: re-runs every evaluation
#                                        from that run's recorded responses and config
#                                        snapshot, checks the hypervolumes match. Never
#                                        overwrites the published report.
#   make ablation-report RUN_ID=M5-ABL-...   rebuild summary, figures and report only
.PHONY: ablation ablation-replay ablation-report
ablation:
	$(PY) scripts/run_ai_ablation.py $(if $(DOE_RUN),--doe-run $(DOE_RUN),)

ablation-replay:
	$(PY) scripts/run_ai_ablation.py --replay $(RUN_ID) $(if $(STRICT),--strict-replay,)

ablation-report:
	$(PY) scripts/run_ai_ablation.py --report-only $(RUN_ID)

# Milestone M7 (configs/uncertainty.yaml). Both use the latest `doe` run's active
# variables and REFUSE if that screening is void for the current design space.
#   make uncertainty                 propagation + Sobol' attribution + the §39 table.
#                                    Picks up the latest `make robust` run if there is
#                                    one. ~15 min on six workers.
#   make robust                      robust NSGA-II with chance constraints, plus the
#                                    verification of its common-random-number shortcut
#                                    against full Monte Carlo. HOURS - background it.
#   make m7                          robust, then uncertainty, in the order the report
#                                    needs (the §39 table's robust row comes from the
#                                    robust run).
#   make uncertainty-smoke           tiny N: proves the chain runs. Writes its report and
#                                    figures INTO ITS OWN RUN DIRECTORY and publishes
#                                    nothing. No number it produces is a result.
#   make uncertainty-time            measure and print the per-evaluation cost only.
#   make uncertainty-report RUN_ID=  rebuild figures and the report from a finished run.
.PHONY: uncertainty robust m7 uncertainty-smoke uncertainty-time uncertainty-report
uncertainty:
	$(PY) scripts/run_uncertainty.py $(if $(DOE_RUN),--doe-run $(DOE_RUN),) \
		$(if $(ROBUST_RUN),--robust-run $(ROBUST_RUN),)

robust:
	$(PY) scripts/run_robust_optimize.py $(if $(DOE_RUN),--doe-run $(DOE_RUN),)

m7: robust uncertainty

uncertainty-smoke:
	$(PY) scripts/run_robust_optimize.py --smoke
	$(PY) scripts/run_uncertainty.py --smoke

uncertainty-time:
	$(PY) scripts/run_uncertainty.py --time-only

uncertainty-report:
	$(PY) scripts/run_uncertainty.py --report-only $(RUN_ID)

# Milestone M6 (configs/adaptive_fidelity.yaml): adaptive-fidelity optimisation, H2.
#   make adaptive                        THE STUDY. HOURS (4-5 h, 3 serial OpenFOAM cases side
#                                        by side) - run it in the background. REFUSES unless gate
#                                        G4 is PASS, the design space selects cfd_surface_v1 and
#                                        the latest DOE screening was made on it. The LLM arm
#                                        makes live `claude -p` calls (hard-capped at 30);
#                                        SKIP_LLM=1 drops it. REUSE_CFD="M6-AF-..." reuses the
#                                        finished CFD cases of an aborted run.
#   make adaptive-report RUN_ID=M6-...   rebuild figures and report only
#   make adaptive-smoke                  1 seed, 2 REAL CFD promotions, one at a time (~10 min).
#                                        Not a result; never published to reports/.
#   make adaptive-dry-run                whole pipeline with a FAKE analytic F1, no OpenFOAM
.PHONY: adaptive adaptive-report adaptive-smoke adaptive-dry-run
adaptive:
	$(PY) scripts/run_adaptive_fidelity.py $(if $(DOE_RUN),--doe-run $(DOE_RUN),) \
		$(if $(SKIP_LLM),--skip-llm-arms,) $(if $(REUSE_CFD),--reuse-cfd $(REUSE_CFD),)

adaptive-report:
	$(PY) scripts/run_adaptive_fidelity.py --report-only $(RUN_ID)

adaptive-smoke:
	$(PY) scripts/run_adaptive_fidelity.py --config configs/adaptive_fidelity_smoke.yaml \
		$(if $(REUSE_CFD),--reuse-cfd $(REUSE_CFD),)

adaptive-dry-run:
	$(PY) scripts/run_adaptive_fidelity.py --config configs/adaptive_fidelity_dryrun.yaml --fake-f1

clean:
	rm -rf results/* reports/figures/* .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -exec rm -rf {} +

# Flow-field gallery: reads cfd/generated/ and results/ (read-only), writes
# reports/figures/cfd/*.png|pdf + INDEX.md. No OpenFOAM needed - the wedge mesh is read
# from constant/polyMesh in Python. Seconds to a minute.
#   make cfd-gallery                       every figure, latest M2 / M3-DP / M6-AF runs
#   make cfd-gallery ONLY=sphere,grid      a subset (sphere, limit, demo, grid, m27, m6, cp)
.PHONY: cfd-gallery
cfd-gallery:
	$(PY) scripts/render_cfd_gallery.py $(if $(ONLY),--only $(ONLY),)

# Explanatory infographics for the paper (the argument, not the science plots). Reads
# results/ and the generated reports (read-only), writes reports/figures/infographics/
# *.png|pdf|svg + INDEX.md. Figure 1 re-runs evaluate_design on the M1 config snapshot to
# recover the time histories and asserts the scalars match candidates.csv. Under a minute.
.PHONY: infographics
infographics:
	$(PY) scripts/render_infographics.py

# The paper: reports/final/AETHER_paper.md -> reports/final/AETHER_paper.pdf via pandoc and
# tectonic (XeTeX), with the figure set typeset from the vector PDFs. Needs pandoc, tectonic,
# pdfinfo (poppler) and the macOS system fonts named in reports/final/paper_build/preamble.tex.
# Seconds. Reads nothing under src/, configs/ or results/.
.PHONY: paper
paper:
	reports/final/build_paper.sh
