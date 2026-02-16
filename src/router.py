from fastapi import APIRouter, Query, Request

from src.models import NewsResponse

router = APIRouter(prefix="/api/v1", tags=["news"])


@router.get("/news/ai", response_model=NewsResponse)
async def get_ai_news(
    request: Request,
    days: int = Query(default=7, ge=1, le=30, description="Days to look back from now (Sydney time)"),
    credible_only: bool = Query(default=True, description="Only return articles from credible/authenticated sources"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum articles to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> NewsResponse:
    """Retrieve AI news published in the last N days (Australia/Sydney timezone).

    Only includes articles whose **publication date** falls within the window.
    Articles that were merely updated (not originally published) in this
    window are excluded.
    """
    aggregator = request.app.state.aggregator
    return await aggregator.fetch_weekly_ai_news(
        days_back=days,
        credible_only=credible_only,
        limit=limit,
        offset=offset,
    )


@router.get("/news/sources")
async def get_available_sources(request: Request) -> dict:
    """List which news sources are currently configured and available."""
    aggregator = request.app.state.aggregator
    return {
        "sources": [
            {"name": s.name, "available": s.is_available()}
            for s in aggregator._sources
        ]
    }
