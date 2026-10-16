.PHONY: all validate-data eval test

GIT_SHA ?= $(shell git describe --tags --exact-match 2>/dev/null || git rev-parse HEAD 2>/dev/null || echo "unknown")$(shell git status --porcelain 2>/dev/null | grep -q . && echo "+dirty" || true)
PYTHON ?= $(shell which python3)
PYTEST ?= $(shell if [ -f .venv/bin/pytest ]; then echo .venv/bin/pytest; else echo pytest; fi)

all: validate-data eval test

validate-data:
	$(PYTHON) scripts/validate_dataset.py

eval:
	PYTHONHASHSEED=0 GIT_SHA="$(GIT_SHA)" PYTHONPATH=backend $(PYTHON) -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest

test:
	PYTHONPATH=backend:. $(PYTEST) backend/tests
