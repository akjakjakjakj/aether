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

# Milestone M4. Both take minutes on 6 cores - run them in the background. `optimize`
# frees exactly the variables the latest `doe` run's screening.json left active. The
# fidelity is whatever configs/design_space.yaml's vehicle.aero.model selects (0 today).
#   make optimize DOE_RUN=M4-DOE-...     pin the DOE run
#   make optimize-report RUN_ID=M4-OPT-...   rebuild summary, figures and report only
.PHONY: doe optimize optimize-report
doe:
	$(PY) scripts/run_doe.py

optimize:
	$(PY) scripts/run_optimize.py $(if $(DOE_RUN),--doe-run $(DOE_RUN),)

optimize-report:
	$(PY) scripts/run_optimize.py --report-only $(RUN_ID)

clean:
	rm -rf results/* reports/figures/* .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
