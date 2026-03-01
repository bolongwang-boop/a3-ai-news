from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.database.repository import ArticleRepository
from src.models import Article, ArticleSource

UTC = ZoneInfo("UTC")


def _make_article(**overrides) -> Article:
    defaults = {
        "title": "Test",
        "description": "desc",
        "url": "https://example.com/1",
        "published_at": datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        "published_at_sydney": "2026-01-15 23:00:00 AEDT",
        "source": ArticleSource(name="Src", url=None, is_credible=True),
        "image_url": None,
        "fetched_from": "test",
    }
    defaults.update(overrides)
    return Article(**defaults)


def _mock_session_factory():
    """Return (session_factory, session) where session is an AsyncMock.

    async_sessionmaker.__call__ is synchronous and returns an async context manager.
    """
    session = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock()
    factory.return_value = ctx
    return factory, session


# ── upsert_articles ────────────────────────────────────────────

class TestUpsertArticles:
    @pytest.mark.asyncio
    async def test_empty_list_returns_zero(self):
        factory, _ = _mock_session_factory()
        repo = ArticleRepository(factory)
        count = await repo.upsert_articles([])
        assert count == 0

    @pytest.mark.asyncio
    async def test_upserts_and_returns_count(self):
        factory, session = _mock_session_factory()
        # session.execute returns a result with rowcount
        result_mock = MagicMock()
        result_mock.rowcount = 3
        session.execute.return_value = result_mock

        repo = ArticleRepository(factory)
        articles = [
            _make_article(url=f"https://example.com/{i}") for i in range(3)
        ]
        count = await repo.upsert_articles(articles)
        assert count == 3
        session.commit.assert_awaited_once()


# ── get_articles ───────────────────────────────────────────────

class TestGetArticles:
    @pytest.mark.asyncio
    async def test_returns_total_and_articles(self):
        factory, session = _mock_session_factory()

        row = MagicMock()
        row.title = "AI News"
        row.description = "desc"
        row.url = "https://example.com/1"
        row.published_at = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        row.published_at_sydney = "2026-01-15 23:00:00 AEDT"
        row.source_name = "BBC"
        row.source_url = None
        row.source_is_credible = True
        row.image_url = None
        row.fetched_from = "google_rss"

        # First execute call: count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        # Second execute call: rows query
        rows_result = MagicMock()
        rows_result.scalars.return_value.all.return_value = [row]

        session.execute.side_effect = [count_result, rows_result]

        repo = ArticleRepository(factory)
        from_dt = datetime(2026, 1, 14, tzinfo=UTC)
        to_dt = datetime(2026, 1, 16, tzinfo=UTC)
        total, articles = await repo.get_articles(from_dt, to_dt)

        assert total == 1
        assert len(articles) == 1
        assert articles[0].title == "AI News"

    @pytest.mark.asyncio
    async def test_credible_filter(self):
        factory, session = _mock_session_factory()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        rows_result = MagicMock()
        rows_result.scalars.return_value.all.return_value = []
        session.execute.side_effect = [count_result, rows_result]

        repo = ArticleRepository(factory)
        from_dt = datetime(2026, 1, 14, tzinfo=UTC)
        to_dt = datetime(2026, 1, 16, tzinfo=UTC)

        total, articles = await repo.get_articles(from_dt, to_dt, credible_only=True)
        assert total == 0
        assert articles == []

    @pytest.mark.asyncio
    async def test_empty_results(self):
        factory, session = _mock_session_factory()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        rows_result = MagicMock()
        rows_result.scalars.return_value.all.return_value = []
        session.execute.side_effect = [count_result, rows_result]

        repo = ArticleRepository(factory)
        from_dt = datetime(2026, 1, 14, tzinfo=UTC)
        to_dt = datetime(2026, 1, 16, tzinfo=UTC)

        total, articles = await repo.get_articles(from_dt, to_dt, credible_only=False)
        assert total == 0
        assert articles == []


# ── get_stats ──────────────────────────────────────────────────

class TestGetStats:
    @pytest.mark.asyncio
    async def test_returns_counts(self):
        factory, session = _mock_session_factory()

        total_result = MagicMock()
        total_result.scalar_one.return_value = 100
        credible_result = MagicMock()
        credible_result.scalar_one.return_value = 42

        session.execute.side_effect = [total_result, credible_result]

        repo = ArticleRepository(factory)
        stats = await repo.get_stats()
        assert stats == {"total_articles": 100, "credible_articles": 42}


# ── _row_to_article ────────────────────────────────────────────

class TestRowToArticle:
    def test_converts_all_fields(self):
        row = MagicMock()
        row.title = "Title"
        row.description = "Desc"
        row.url = "https://example.com"
        row.published_at = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        row.published_at_sydney = "2026-01-15 23:00:00 AEDT"
        row.source_name = "BBC"
        row.source_url = "https://bbc.com"
        row.source_is_credible = True
        row.image_url = "https://img.com/photo.jpg"
        row.fetched_from = "newsapi"

        article = ArticleRepository._row_to_article(row)
        assert article.title == "Title"
        assert article.source.name == "BBC"
        assert article.source.url == "https://bbc.com"
        assert article.source.is_credible is True
        assert article.image_url == "https://img.com/photo.jpg"
        assert article.fetched_from == "newsapi"

    def test_handles_none_fields(self):
        row = MagicMock()
        row.title = "Title"
        row.description = None
        row.url = "https://example.com"
        row.published_at = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        row.published_at_sydney = "2026-01-15 23:00:00 AEDT"
        row.source_name = "Unknown"
        row.source_url = None
        row.source_is_credible = False
        row.image_url = None
        row.fetched_from = "google_rss"

        article = ArticleRepository._row_to_article(row)
        assert article.description is None
        assert article.source.url is None
        assert article.image_url is None
