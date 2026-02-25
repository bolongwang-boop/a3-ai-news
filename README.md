# AI News API

Aggregated AI news from authenticated/credible sources. All dates are calculated in **Australia/Sydney timezone**. Only articles **published** (not merely updated) within the requested window are returned.

## Features

- **Dual news sources**: NewsAPI.org + Google News RSS
- **Credibility filtering**: 30+ whitelisted domains (Reuters, BBC, TechCrunch, Nature, etc.)
- **Server-side date validation**: Re-validates publication dates in Sydney timezone
- **URL-based deduplication**: Prevents duplicates across sources
- **PostgreSQL persistence**: Optional database storage with upsert
- **Slack Block Kit output**: Ready-to-post Slack messages for n8n pipelines
- **CLI tool**: Fetch news as JSON from the terminal

## Quick Start

```bash
# Set up environment
cp .env.example .env
# Edit .env with your AINEWS_NEWSAPI_KEY (optional — Google RSS works without it)

# Run the API server locally (auto-creates venv and installs deps)
make local
```

### Make Targets

| Command | Description |
|---|---|
| `make local` | Run the API server locally with hot-reload (port 8080) |
| `make news` | Fetch latest AI news as JSON via CLI |
| `make test` | Run the test suite |
| `make lint` | Lint source code with ruff |
| `make fmt` | Format source code with ruff |
| `make clean` | Remove venv and caches |
| `make help` | Show all available targets |

All targets automatically create the virtualenv and install dependencies if needed.

## CLI Usage

Fetch the latest AI news and output as JSON:

```bash
# Print JSON to stdout
python -m src.cli

# Or via the installed entry point
ai-news

# Options
ai-news --days 3          # Look back 3 days instead of 7
ai-news --limit 10        # Return at most 10 articles
ai-news --all-sources     # Include non-credible sources

# Output to a file via environment variable
AINEWS_OUTPUT_FILE=/tmp/ai-news.json ai-news

# Pipe to jq for filtering
ai-news | jq '.articles[0]'
```

When `AINEWS_OUTPUT_FILE` is set (or in `.env`), JSON is written to that file path. Otherwise it prints to stdout. Logs always go to stderr so piping stays clean.

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/v1/news/ai` | AI news as structured JSON |
| `GET /api/v1/news/slack` | AI news as Slack Block Kit payload |
| `GET /api/v1/news/sources` | Available sources and database status |
| `GET /health` | Health check |

### Query Parameters

| Parameter | Default | Description |
|---|---|---|
| `days` | `7` | Days to look back (1–30) |
| `credible_only` | `true` | Filter to credible sources only |
| `limit` | `50` | Articles per page (1–200) |
| `offset` | `0` | Pagination offset |
| `source` | `live` | `live` fetches from APIs; `cached` reads from database |

## Environment Variables

All prefixed with `AINEWS_`:

| Variable | Default | Description |
|---|---|---|
| `AINEWS_NEWSAPI_KEY` | — | NewsAPI.org API key (optional; Google RSS always works) |
| `AINEWS_DATABASE_URL` | — | PostgreSQL async connection URL |
| `AINEWS_ENABLE_PERSISTENCE` | `false` | Enable database persistence |
| `AINEWS_OUTPUT_FILE` | — | CLI: write JSON to this file instead of stdout |
| `AINEWS_TIMEZONE` | `Australia/Sydney` | Timezone for date calculations |
| `AINEWS_DEFAULT_DAYS_BACK` | `7` | Default lookback period |
| `AINEWS_RETENTION_DAYS` | `30` | Database article retention |

## Testing

```bash
make test
```

## Project Structure

```
src/
├── main.py              # FastAPI app and lifespan
├── cli.py               # CLI entry point (ai-news command)
├── config.py            # Pydantic settings from env vars
├── models.py            # Article, NewsResponse data models
├── router.py            # API route handlers
├── aggregator.py        # News aggregation, dedup, credibility
├── timezone.py          # Sydney timezone utilities
├── sources/
│   ├── base.py          # Abstract NewsSource interface
│   ├── newsapi.py       # NewsAPI.org integration
│   └── google_rss.py    # Google News RSS integration
├── formatters/
│   └── slack.py         # Slack Block Kit formatter
└── database/
    ├── connection.py    # SQLAlchemy async engine
    ├── models.py        # ORM model
    └── repository.py    # Article CRUD operations
```

## Deployment

Deployed to **Google Cloud Run** with Cloud Build CI/CD. Infrastructure managed via Terraform in `terraform/`.

```bash
# Deploy manually
gcloud run deploy a3-ai-news --source .
```
