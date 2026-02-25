VENV := .venv
BIN  := $(VENV)/bin
PY   := $(BIN)/python

.PHONY: local test lint fmt news clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(VENV)/bin/activate: pyproject.toml
	python3 -m venv $(VENV)
	$(BIN)/pip install -e ".[dev]"
	@touch $(VENV)/bin/activate

local: $(VENV)/bin/activate ## Run the API server locally with hot-reload
	$(BIN)/uvicorn src.main:app --reload --port 8080

news: $(VENV)/bin/activate ## Fetch latest AI news as JSON (CLI)
	$(PY) -m src.cli

test: $(VENV)/bin/activate ## Run the test suite
	$(BIN)/pytest tests/ -v

lint: $(VENV)/bin/activate ## Lint source code with ruff
	$(BIN)/ruff check src/ tests/

fmt: $(VENV)/bin/activate ## Format source code with ruff
	$(BIN)/ruff format src/ tests/

clean: ## Remove venv and caches
	rm -rf $(VENV) .pytest_cache .ruff_cache __pycache__ src/__pycache__
