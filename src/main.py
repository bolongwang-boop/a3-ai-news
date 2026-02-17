import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.aggregator import NewsAggregator
from src.config import settings
from src.router import router
from src.sources.google_rss import GoogleRSSSource
from src.sources.newsapi import NewsAPISource

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: shared HTTP client and aggregator
    http_client = httpx.AsyncClient(timeout=30.0)

    sources = [
        NewsAPISource(api_key=settings.newsapi_key, http_client=http_client),
        GoogleRSSSource(http_client=http_client),
    ]

    # Database setup (optional — enabled via AINEWS_DATABASE_URL + AINEWS_ENABLE_PERSISTENCE)
    repository = None
    engine = None

    if settings.database_url and settings.enable_persistence:
        try:
            from src.database.connection import get_engine, get_session_factory
            from src.database.models import Base

            engine = get_engine(
                settings.database_url,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
            )

            # Create tables if they don't exist (Alembic is preferred for production)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            session_factory = get_session_factory(engine)

            from src.database.repository import ArticleRepository

            repository = ArticleRepository(session_factory)
            logger.info("Database persistence enabled")
        except Exception:
            logger.exception("Failed to initialize database — running without persistence")
            repository = None

    app.state.aggregator = NewsAggregator(
        sources=sources, settings=settings, repository=repository
    )
    app.state.http_client = http_client
    app.state.repository = repository

    yield

    # Shutdown
    await http_client.aclose()
    if engine is not None:
        await engine.dispose()


app = FastAPI(
    title="AI News API",
    description=(
        "Aggregated AI news from authenticated/credible sources. "
        "All dates are calculated in Australia/Sydney timezone. "
        "Only articles **published** (not merely updated) within the "
        "requested window are returned. "
        "Includes Slack Block Kit output for n8n pipeline integration."
    ),
    version="2.0.0",
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
    db_status = "disabled"
    if settings.database_url and settings.enable_persistence:
        db_status = "enabled"
    return {"status": "ok", "database": db_status}
