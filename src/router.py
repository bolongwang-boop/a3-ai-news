from enum import Enum

from fastapi import APIRouter, Query, Request

from src.formatters.slack import format_articles_for_slack, format_digest_for_slack
from src.models import DigestResponse, NewsResponse

router = APIRouter(prefix="/api/v1", tags=["news"])


class NewsSource(str, Enum):
    live = "live"
    cached = "cached"


@router.get("/news/ai", response_model=NewsResponse)
async def get_ai_news(
    request: Request,
    days: int = Query(
        default=7, ge=1, le=30, description="Days to look back from now (Sydney time)"
    ),
    credible_only: bool = Query(
        default=True,
        description="Only return articles from credible/authenticated sources",
    ),
    limit: int | None = Query(
        default=None,
        ge=1,
        le=500,
        description="Maximum articles to return. Omit to return all.",
    ),
    max_results: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum articles to fetch from each news source before filtering",
    ),
    source: NewsSource = Query(
        default=NewsSource.live,
        description="'live' fetches from news APIs; 'cached' reads from database",
    ),
) -> NewsResponse:
    """Retrieve AI news published in the last N days (Australia/Sydney timezone).

    Only includes articles whose **publication date** falls within the window.
    Articles that were merely updated (not originally published) in this
    window are excluded.

    Use `source=cached` to read from the PostgreSQL database (faster, no
    external API calls). Use `source=live` (default) to fetch fresh data
    from news sources and persist to the database.
    """
    aggregator = request.app.state.aggregator

    if source == NewsSource.cached:
        return await aggregator.fetch_from_database(
            days_back=days,
            credible_only=credible_only,
            limit=limit,
        )

    return await aggregator.fetch_weekly_ai_news(
        days_back=days,
        credible_only=credible_only,
        limit=limit,
        max_results=max_results,
    )


@router.get("/news/slack")
async def get_ai_news_slack(
    request: Request,
    days: int = Query(
        default=7, ge=1, le=30, description="Days to look back from now (Sydney time)"
    ),
    credible_only: bool = Query(
        default=True,
        description="Only return articles from credible/authenticated sources",
    ),
    limit: int | None = Query(
        default=None,
        ge=1,
        le=500,
        description="Maximum articles to return. Omit to return all.",
    ),
    max_results: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum articles to fetch from each news source before filtering",
    ),
    source: NewsSource = Query(
        default=NewsSource.live,
        description="'live' fetches from news APIs; 'cached' reads from database",
    ),
) -> dict:
    """Return AI news formatted as Slack Block Kit JSON.

    The response can be POSTed directly to a Slack webhook URL from n8n
    or any HTTP client. The `blocks` array contains the full message.

    Example n8n usage:
      HTTP Request node -> GET this endpoint -> Slack node (Block Kit message)
    """
    aggregator = request.app.state.aggregator

    if source == NewsSource.cached:
        news = await aggregator.fetch_from_database(
            days_back=days,
            credible_only=credible_only,
            limit=limit,
        )
    else:
        news = await aggregator.fetch_weekly_ai_news(
            days_back=days,
            credible_only=credible_only,
            limit=limit,
            max_results=max_results,
        )

    return format_articles_for_slack(
        articles=news.articles,
        from_date=news.from_date_sydney,
        to_date=news.to_date_sydney,
        total=news.total_articles,
        limit=limit or len(news.articles),
    )


@router.get("/news/digest", response_model=DigestResponse)
async def get_ai_news_digest(
    request: Request,
    days: int = Query(
        default=7, ge=1, le=30, description="Days to look back from now (Sydney time)"
    ),
    items: int = Query(
        default=10, ge=1, le=20, description="Number of curated items to return"
    ),
) -> DigestResponse:
    """Return a curated, category-balanced AI news digest.

    Fetches articles from multiple sources using both general and targeted
    queries, then selects exactly N items (default 10) balanced across
    content categories: product launches, business & adoption, productivity
    tools, industry news, security/risk, and Gemini/n8n.

    No URLs are included in the response — designed for summary consumption.
    """
    aggregator = request.app.state.aggregator
    return await aggregator.fetch_curated_digest(days_back=days, total_items=items)


@router.get("/news/digest/slack")
async def get_ai_news_digest_slack(
    request: Request,
    days: int = Query(
        default=7, ge=1, le=30, description="Days to look back from now (Sydney time)"
    ),
    items: int = Query(
        default=10, ge=1, le=20, description="Number of curated items to return"
    ),
) -> dict:
    """Return a curated AI news digest formatted as Slack Block Kit JSON.

    Same curated, category-balanced selection as /news/digest, formatted
    for direct posting to a Slack webhook from n8n or any HTTP client.
    """
    aggregator = request.app.state.aggregator
    digest = await aggregator.fetch_curated_digest(days_back=days, total_items=items)
    return format_digest_for_slack(digest)


@router.get("/news/sources")
async def get_available_sources(request: Request) -> dict:
    """List which news sources are currently configured and available."""
    aggregator = request.app.state.aggregator

    result: dict = {
        "sources": [
            {"name": s.name, "available": s.is_available()} for s in aggregator._sources
        ],
        "database_enabled": aggregator._repository is not None,
    }

    if aggregator._repository is not None:
        try:
            stats = await aggregator._repository.get_stats()
            result["database_stats"] = stats
        except Exception:
            result["database_stats"] = {"error": "Could not fetch stats"}

    return result
