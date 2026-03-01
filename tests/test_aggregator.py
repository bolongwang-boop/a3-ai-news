from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from src.aggregator import NewsAggregator
from src.config import Settings
from src.models import Article
from src.sources.base import NewsSource
from tests.conftest import make_article

UTC = ZoneInfo("UTC")


class FakeSource(NewsSource):
    def __init__(self, name: str, articles: list[Article], available: bool = True):
        self._name = name
        self._articles = articles
        self._available = available

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    async def fetch_ai_news(self, from_date, to_date, max_results=50):
        return self._articles


class FailingSource(NewsSource):
    @property
    def name(self) -> str:
        return "failing"

    def is_available(self) -> bool:
        return True

    async def fetch_ai_news(self, from_date, to_date, max_results=50):
        raise RuntimeError("source failed")


@pytest.fixture
def settings():
    return Settings(newsapi_key=None)


class TestDeduplication:
    def test_removes_duplicate_urls(self, settings):
        articles = [
            make_article(url="https://techcrunch.com/article-1"),
            make_article(url="https://techcrunch.com/article-1"),
        ]
        agg = NewsAggregator(sources=[], settings=settings)
        result = agg._deduplicate(articles)
        assert len(result) == 1

    def test_normalizes_www_prefix(self, settings):
        articles = [
            make_article(url="https://www.bbc.com/news/ai"),
            make_article(url="https://bbc.com/news/ai"),
        ]
        agg = NewsAggregator(sources=[], settings=settings)
        result = agg._deduplicate(articles)
        assert len(result) == 1

    def test_normalizes_trailing_slash(self, settings):
        articles = [
            make_article(url="https://bbc.com/news/ai/"),
            make_article(url="https://bbc.com/news/ai"),
        ]
        agg = NewsAggregator(sources=[], settings=settings)
        result = agg._deduplicate(articles)
        assert len(result) == 1

    def test_keeps_unique_urls(self, settings):
        articles = [
            make_article(url="https://bbc.com/article-1"),
            make_article(url="https://bbc.com/article-2"),
        ]
        agg = NewsAggregator(sources=[], settings=settings)
        result = agg._deduplicate(articles)
        assert len(result) == 2


class TestCredibilityMarking:
    def test_marks_credible_by_domain(self, settings):
        articles = [make_article(url="https://techcrunch.com/test", source_name="TC")]
        agg = NewsAggregator(sources=[], settings=settings)
        result = agg._mark_credibility(articles)
        assert result[0].source.is_credible is True

    def test_marks_credible_by_name(self, settings):
        # Google RSS wraps URLs through news.google.com, so domain check won't
        # work — credibility falls back to source name matching.
        articles = [
            make_article(
                url="https://news.google.com/rss/...",
                source_name="TechCrunch",
                source_url=None,
            )
        ]
        agg = NewsAggregator(sources=[], settings=settings)
        result = agg._mark_credibility(articles)
        assert result[0].source.is_credible is True

    def test_marks_not_credible_for_unknown(self, settings):
        articles = [
            make_article(
                url="https://randomblog.xyz/post",
                source_name="Random Blog",
            )
        ]
        agg = NewsAggregator(sources=[], settings=settings)
        result = agg._mark_credibility(articles)
        assert result[0].source.is_credible is False


class TestFetchWeeklyAINews:
    @pytest.mark.asyncio
    async def test_aggregates_from_multiple_sources(self, settings):
        now = datetime.now(UTC)
        a1 = make_article(title="From API", url="https://openai.com/1", published_at=now - timedelta(hours=1))
        a2 = make_article(title="From RSS", url="https://bbc.com/2", source_name="BBC News", published_at=now - timedelta(hours=2))

        sources = [
            FakeSource("newsapi", [a1]),
            FakeSource("google_rss", [a2]),
        ]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_weekly_ai_news(credible_only=False)

        assert result.total_articles == 2
        assert {"newsapi", "google_rss"} == set(result.sources_queried)

    @pytest.mark.asyncio
    async def test_filters_credible_only(self, settings):
        now = datetime.now(UTC)
        credible = make_article(title="BBC", url="https://bbc.com/ai", source_name="BBC News", published_at=now - timedelta(hours=1))
        not_credible = make_article(title="Blog", url="https://randomblog.xyz/ai", source_name="Random", published_at=now - timedelta(hours=1))

        sources = [FakeSource("test", [credible, not_credible])]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_weekly_ai_news(credible_only=True)

        assert result.total_articles == 1
        assert result.articles[0].title == "BBC"

    @pytest.mark.asyncio
    async def test_handles_source_failure_gracefully(self, settings):
        now = datetime.now(UTC)
        good = make_article(title="Good", url="https://bbc.com/good", source_name="BBC News", published_at=now - timedelta(hours=1))

        sources = [FakeSource("good", [good]), FailingSource()]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_weekly_ai_news(credible_only=False)

        assert result.total_articles >= 1
        assert "good" in result.sources_queried
        assert "failing" not in result.sources_queried

    @pytest.mark.asyncio
    async def test_skips_unavailable_sources(self, settings):
        sources = [FakeSource("disabled", [], available=False)]
        agg = NewsAggregator(sources=sources, settings=settings)
        assert agg.available_sources == []

    @pytest.mark.asyncio
    async def test_sorts_newest_first(self, settings):
        now = datetime.now(UTC)
        older = make_article(title="Old", url="https://bbc.com/old", source_name="BBC News", published_at=now - timedelta(hours=5))
        newer = make_article(title="New", url="https://bbc.com/new", source_name="BBC News", published_at=now - timedelta(hours=1))

        sources = [FakeSource("test", [older, newer])]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_weekly_ai_news(credible_only=False)

        assert result.articles[0].title == "New"
        assert result.articles[1].title == "Old"

    @pytest.mark.asyncio
    async def test_limit_caps_results(self, settings):
        now = datetime.now(UTC)
        articles = [
            make_article(title=f"Art {i}", url=f"https://bbc.com/{i}", source_name="BBC News", published_at=now - timedelta(hours=i))
            for i in range(5)
        ]

        sources = [FakeSource("test", articles)]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_weekly_ai_news(credible_only=False, limit=2)

        assert result.total_articles == 2
        assert len(result.articles) == 2

    @pytest.mark.asyncio
    async def test_no_limit_returns_all(self, settings):
        now = datetime.now(UTC)
        articles = [
            make_article(title=f"Art {i}", url=f"https://bbc.com/{i}", source_name="BBC News", published_at=now - timedelta(hours=i))
            for i in range(5)
        ]

        sources = [FakeSource("test", articles)]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_weekly_ai_news(credible_only=False)

        assert result.total_articles == 5
        assert len(result.articles) == 5
