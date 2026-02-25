from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models import NewsResponse
from tests.conftest import make_article

UTC = ZoneInfo("UTC")


def _make_news_response(n: int = 2) -> NewsResponse:
    now = datetime.now(UTC)
    articles = [
        make_article(
            title=f"Article {i}",
            url=f"https://bbc.com/{i}",
            source_name="BBC News",
            published_at=now - timedelta(hours=i),
        )
        for i in range(n)
    ]
    return NewsResponse(
        total_articles=n,
        query="AI news (last week, Sydney time)",
        from_date_sydney="2026-02-18 00:00:00 AEDT",
        to_date_sydney="2026-02-25 12:00:00 AEDT",
        sources_queried=["google_rss"],
        articles=articles,
    )


@pytest.fixture
def client():
    mock_aggregator = MagicMock()
    mock_aggregator.fetch_weekly_ai_news = AsyncMock(return_value=_make_news_response())
    mock_aggregator.fetch_from_database = AsyncMock(return_value=_make_news_response(1))
    mock_aggregator._sources = []
    mock_aggregator._repository = None

    app.state.aggregator = mock_aggregator
    app.state.repository = None
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestGetAINews:
    def test_returns_articles(self, client):
        resp = client.get("/api/v1/news/ai")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_articles"] == 2
        assert len(data["articles"]) == 2

    def test_with_query_params(self, client):
        resp = client.get("/api/v1/news/ai?days=3&limit=10&credible_only=true")
        assert resp.status_code == 200

    def test_cached_source(self, client):
        resp = client.get("/api/v1/news/ai?source=cached")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_articles"] == 1


class TestGetSlackNews:
    def test_returns_blocks(self, client):
        resp = client.get("/api/v1/news/slack")
        assert resp.status_code == 200
        data = resp.json()
        assert "blocks" in data

    def test_slack_cached(self, client):
        resp = client.get("/api/v1/news/slack?source=cached")
        assert resp.status_code == 200


class TestGetSources:
    def test_returns_sources_list(self, client):
        resp = client.get("/api/v1/news/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "database_enabled" in data
