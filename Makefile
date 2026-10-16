.PHONY: all up down reset-db validate-data eval test lint e2e

GIT_SHA ?= $(shell git describe --tags --exact-match 2>/dev/null || git rev-parse HEAD 2>/dev/null || echo "unknown")$(shell git status --porcelain 2>/dev/null | grep -q . && echo "+dirty" || true)
PYTHON ?= $(shell if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; else which python3; fi)
PYTEST ?= $(shell if [ -f .venv/bin/pytest ]; then echo .venv/bin/pytest; else echo pytest; fi)
RUFF ?= $(shell if [ -f .venv/bin/ruff ]; then echo .venv/bin/ruff; else echo ruff; fi)

all: validate-data eval test lint

up:
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
	fi
	docker compose up --build -d

down:
	docker compose down

reset-db:
	docker compose down -v

validate-data:
	$(PYTHON) scripts/validate_dataset.py

eval:
	PYTHONHASHSEED=0 GIT_SHA="$(GIT_SHA)" PYTHONPATH=backend $(PYTHON) -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest

test:
	PYTHONPATH=backend:. $(PYTEST) backend/tests
	cd frontend && pnpm test

lint:
	$(RUFF) check backend/app
	cd frontend && pnpm lint

e2e:
	PYTHONPATH=backend:. $(PYTEST) backend/tests/integration/test_golden_flow.py
