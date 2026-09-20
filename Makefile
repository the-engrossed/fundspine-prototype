.DEFAULT_GOAL := help
PY := .venv/bin/python
PIP := uv pip install --python .venv/bin/python

.PHONY: help install up down migrate golden ingest render drift eval costs test lint typecheck check clean

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n", $$1, $$2}'

install: ## create .venv on python 3.12 and install the package
	uv venv --python 3.12 .venv
	$(PIP) -e ".[dev]"

up: ## start postgres and wait for it to be healthy
	docker compose up -d
	@until docker compose exec -T postgres pg_isready -U fundspine -d fundspine >/dev/null 2>&1; do sleep 1; done
	@echo "postgres ready on localhost:5433"

down: ## stop postgres (data volume survives)
	docker compose down

migrate: ## apply alembic migrations
	.venv/bin/alembic upgrade head

golden: ## generate the synthetic HTML documents and their derived ground truth
	$(PY) -m evals.golden.generate

ingest: ## ingest, extract, validate and persist every golden document
	$(PY) -m fundspine.cli ingest

render: ## render the ic memo and both partner commentaries
	$(PY) -m fundspine.cli render

drift: ## evaluate drift detectors across periods
	$(PY) -m fundspine.cli drift

eval: ## run the golden set and write a scorecard
	$(PY) -m evals.run_eval

costs: ## print cost and latency per document and per partner packet
	$(PY) -m fundspine.cli costs

test: ## run the test suite
	.venv/bin/pytest

lint: ## ruff
	.venv/bin/ruff check .

typecheck: ## mypy
	.venv/bin/mypy fundspine

check: lint typecheck test ## everything ci runs

clean: ## remove caches and rendered output
	rm -rf .pytest_cache .mypy_cache .ruff_cache out traces
