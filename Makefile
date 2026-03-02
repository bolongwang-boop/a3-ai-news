VENV := .venv
BIN  := $(VENV)/bin
PY   := $(BIN)/python

# Cloud SQL connection settings
PROJECT      := a3-team-481403
REGION       := australia-southeast1
DB_INSTANCE  := a3-ai-news-db
DB_CONN_NAME := $(PROJECT):$(REGION):$(DB_INSTANCE)
DB_NAME      := ai_news
DB_USER      := ainews
DB_PORT      := 5432

.PHONY: local test lint fmt news clean help db db-proxy api-health api-news api-slack api-sources

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

db-proxy: ## Start Cloud SQL Auth Proxy for GUI clients (Ctrl+C to stop)
	@echo "Proxy listening on localhost:$(DB_PORT) — connect DBeaver/pgAdmin to:"
	@echo "  Host: 127.0.0.1  Port: $(DB_PORT)  Database: $(DB_NAME)  User: $(DB_USER)"
	@echo "  Password: gcloud secrets versions access latest --secret=a3-ai-news-database-url --project=$(PROJECT)"
	@echo ""
	cloud-sql-proxy $(DB_CONN_NAME) --port $(DB_PORT)

db: ## Connect to Cloud SQL via Auth Proxy + psql
	@cloud-sql-proxy $(DB_CONN_NAME) --port $(DB_PORT) & \
	PROXY_PID=$$!; \
	trap 'kill $$PROXY_PID 2>/dev/null' EXIT; \
	sleep 2; \
	psql "host=127.0.0.1 port=$(DB_PORT) dbname=$(DB_NAME) user=$(DB_USER)"; \
	kill $$PROXY_PID 2>/dev/null

API_URL := http://localhost:8080

api-health: ## Hit GET /health
	@curl -sf $(API_URL)/health | python3 -m json.tool || echo "Error: is the server running? Start it with: make local"

api-news: ## Hit GET /api/v1/news/ai
	@curl -sf "$(API_URL)/api/v1/news/ai?days=7&credible_only=true&limit=5" | python3 -m json.tool || echo "Error: is the server running? Start it with: make local"

api-slack: ## Hit GET /api/v1/news/slack
	@curl -sf "$(API_URL)/api/v1/news/slack?days=7&credible_only=true&limit=5" | python3 -m json.tool || echo "Error: is the server running? Start it with: make local"

api-sources: ## Hit GET /api/v1/news/sources
	@curl -sf $(API_URL)/api/v1/news/sources | python3 -m json.tool || echo "Error: is the server running? Start it with: make local"

clean: ## Remove venv and caches
	rm -rf $(VENV) .pytest_cache .ruff_cache __pycache__ src/__pycache__
