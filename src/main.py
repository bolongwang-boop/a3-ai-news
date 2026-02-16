from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.aggregator import NewsAggregator
from src.config import settings
from src.router import router
from src.sources.google_rss import GoogleRSSSource
from src.sources.newsapi import NewsAPISource


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: shared HTTP client and aggregator
    http_client = httpx.AsyncClient(timeout=30.0)

    sources = [
        NewsAPISource(api_key=settings.newsapi_key, http_client=http_client),
        GoogleRSSSource(http_client=http_client),
    ]
    app.state.aggregator = NewsAggregator(sources=sources, settings=settings)
    app.state.http_client = http_client

    yield

    # Shutdown
    await http_client.aclose()


app = FastAPI(
    title="AI News API",
    description=(
        "Aggregated AI news from authenticated/credible sources. "
        "All dates are calculated in Australia/Sydney timezone. "
        "Only articles **published** (not merely updated) within the "
        "requested window are returned."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
