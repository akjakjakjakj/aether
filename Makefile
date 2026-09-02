PY := .venv/bin/python

.PHONY: all test lint baseline burn-vs-bake figures validate clean

all: test baseline burn-vs-bake

test:
	$(PY) -m pytest tests/ -q

validate: test

lint:
	.venv/bin/ruff check src tests scripts

baseline:
	$(PY) scripts/run_baseline.py

burn-vs-bake:
	$(PY) scripts/run_burn_vs_bake.py

figures: baseline burn-vs-bake

clean:
	rm -rf results/* reports/figures/* .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
