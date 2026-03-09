from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from src.aggregator import NewsAggregator
from src.categories import Category
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
        self.targeted_calls: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    async def fetch_ai_news(self, from_date, to_date, max_results=50):
        return self._articles

    async def fetch_targeted_news(self, query, from_date, to_date, max_results=20):
        self.targeted_calls.append(query)
        return self._articles


@pytest.fixture
def settings():
    return Settings(newsapi_key=None)


def _make_categorized_articles(now: datetime) -> list[Article]:
    """Create articles that span all 6 categories."""
    return [
        # Product launches (2)
        make_article(
            title="OpenAI launches GPT-5 with new capabilities",
            url="https://openai.com/blog/gpt-5",
            source_name="OpenAI",
            published_at=now - timedelta(hours=1),
        ),
        make_article(
            title="Anthropic announces Claude 4 model release",
            url="https://techcrunch.com/anthropic-claude-4",
            source_name="TechCrunch",
            published_at=now - timedelta(hours=2),
        ),
        # Business & adoption (2)
        make_article(
            title="Microsoft signs AI partnership with Accenture",
            url="https://bloomberg.com/microsoft-accenture-ai-partnership",
            source_name="Bloomberg",
            published_at=now - timedelta(hours=3),
        ),
        make_article(
            title="Enterprise AI adoption grows by 40% in Q1 2026",
            url="https://forbes.com/enterprise-ai-adoption-grows",
            source_name="Forbes",
            published_at=now - timedelta(hours=4),
        ),
        # Productivity tools (1)
        make_article(
            title="Slack integrates AI assistant for productivity boost",
            url="https://techcrunch.com/slack-ai-assistant",
            source_name="TechCrunch",
            published_at=now - timedelta(hours=5),
        ),
        # Industry news (2)
        make_article(
            title="EU AI Act enforcement begins in March",
            url="https://reuters.com/eu-ai-act-enforcement",
            source_name="Reuters",
            published_at=now - timedelta(hours=6),
        ),
        make_article(
            title="AI startup raises Series B funding round of 500 million",
            url="https://bloomberg.com/ai-startup-series-b-funding",
            source_name="Bloomberg",
            published_at=now - timedelta(hours=6, minutes=30),
        ),
        # Security/risk (1)
        make_article(
            title="New AI security vulnerabilities found in LLM applications",
            url="https://wired.com/ai-security-vulnerabilities-llm",
            source_name="WIRED",
            published_at=now - timedelta(hours=7),
        ),
        # Gemini / n8n (2)
        make_article(
            title="Google Gemini Pro gets major enterprise update",
            url="https://cloud.google.com/gemini-pro-enterprise-update",
            source_name="Google Cloud",
            published_at=now - timedelta(hours=8),
        ),
        make_article(
            title="n8n releases version 2.0 with AI automation nodes",
            url="https://venturebeat.com/n8n-version-2-ai-nodes",
            source_name="VentureBeat",
            published_at=now - timedelta(hours=9),
        ),
        # Extra product launch (for overflow testing)
        make_article(
            title="Meta releases Llama 4 open-source AI model",
            url="https://reuters.com/meta-releases-llama-4-model",
            source_name="Reuters",
            published_at=now - timedelta(hours=10),
        ),
    ]


class TestCuratedDigest:
    @pytest.mark.asyncio
    async def test_returns_exactly_10_items(self, settings):
        now = datetime.now(UTC)
        articles = _make_categorized_articles(now)
        sources = [FakeSource("test", articles)]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_curated_digest(total_items=10)

        assert result.total_items == 10
        assert len(result.items) == 10

    @pytest.mark.asyncio
    async def test_items_have_no_urls(self, settings):
        """Curated digest items should not include URLs."""
        now = datetime.now(UTC)
        articles = _make_categorized_articles(now)
        sources = [FakeSource("test", articles)]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_curated_digest(total_items=10)

        for item in result.items:
            # CuratedArticle does not have a url field
            assert not hasattr(item, "url")

    @pytest.mark.asyncio
    async def test_items_have_category_labels(self, settings):
        now = datetime.now(UTC)
        articles = _make_categorized_articles(now)
        sources = [FakeSource("test", articles)]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_curated_digest(total_items=10)

        categories = {item.category for item in result.items}
        assert Category.PRODUCT_LAUNCH.value in categories
        assert Category.GEMINI_N8N.value in categories
        assert Category.SECURITY_RISK.value in categories

    @pytest.mark.asyncio
    async def test_items_are_ranked(self, settings):
        now = datetime.now(UTC)
        articles = _make_categorized_articles(now)
        sources = [FakeSource("test", articles)]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_curated_digest(total_items=10)

        ranks = [item.rank for item in result.items]
        assert ranks == list(range(1, 11))

    @pytest.mark.asyncio
    async def test_uses_targeted_queries(self, settings):
        now = datetime.now(UTC)
        articles = _make_categorized_articles(now)
        source = FakeSource("test", articles)
        agg = NewsAggregator(sources=[source], settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            await agg.fetch_curated_digest()

        # Should have called targeted queries for each of the 3 targeted queries
        assert len(source.targeted_calls) == 3

    @pytest.mark.asyncio
    async def test_only_credible_sources(self, settings):
        now = datetime.now(UTC)
        credible = make_article(
            title="BBC covers new AI regulation announcement",
            url="https://bbc.com/ai-regulation-announcement",
            source_name="BBC News",
            published_at=now - timedelta(hours=1),
        )
        not_credible = make_article(
            title="Random AI blog about regulation news",
            url="https://randomblog.xyz/ai-regulation",
            source_name="Random Blog",
            published_at=now - timedelta(hours=1),
        )

        sources = [FakeSource("test", [credible, not_credible])]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_curated_digest(total_items=10)

        source_names = {item.source_name for item in result.items}
        assert "Random Blog" not in source_names

    @pytest.mark.asyncio
    async def test_custom_item_count(self, settings):
        now = datetime.now(UTC)
        articles = _make_categorized_articles(now)
        sources = [FakeSource("test", articles)]
        agg = NewsAggregator(sources=sources, settings=settings)

        with patch("src.aggregator.get_week_range_sydney") as mock_range:
            mock_range.return_value = (now - timedelta(days=7), now)
            result = await agg.fetch_curated_digest(total_items=5)

        assert result.total_items == 5
        assert len(result.items) == 5


class TestSelectByQuota:
    def test_fills_quotas(self, settings):
        now = datetime.now(UTC)
        agg = NewsAggregator(sources=[], settings=settings)

        categorized = {
            Category.PRODUCT_LAUNCH: [
                make_article(
                    title="Launch 1",
                    url="https://openai.com/launch-1",
                    published_at=now,
                ),
                make_article(
                    title="Launch 2",
                    url="https://openai.com/launch-2",
                    published_at=now,
                ),
                make_article(
                    title="Launch 3",
                    url="https://openai.com/launch-3",
                    published_at=now,
                ),
            ],
            Category.BUSINESS_ADOPTION: [
                make_article(
                    title="Biz 1", url="https://bloomberg.com/biz-1", published_at=now
                ),
                make_article(
                    title="Biz 2", url="https://bloomberg.com/biz-2", published_at=now
                ),
            ],
            Category.PRODUCTIVITY_TOOLS: [
                make_article(
                    title="Prod 1",
                    url="https://techcrunch.com/prod-1",
                    published_at=now,
                ),
            ],
            Category.INDUSTRY_NEWS: [
                make_article(
                    title="Industry 1",
                    url="https://reuters.com/industry-1",
                    published_at=now,
                ),
                make_article(
                    title="Industry 2",
                    url="https://reuters.com/industry-2",
                    published_at=now,
                ),
            ],
            Category.SECURITY_RISK: [
                make_article(
                    title="Security 1",
                    url="https://wired.com/security-1",
                    published_at=now,
                ),
            ],
            Category.GEMINI_N8N: [
                make_article(
                    title="Gemini 1",
                    url="https://cloud.google.com/gemini-1",
                    published_at=now,
                ),
                make_article(
                    title="Gemini 2",
                    url="https://cloud.google.com/gemini-2",
                    published_at=now,
                ),
            ],
        }

        selected = agg._select_by_quota(categorized, 10)
        assert len(selected) == 10

        # Check category distribution matches quotas
        cat_counts = {}
        for cat, _ in selected:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        assert cat_counts[Category.PRODUCT_LAUNCH] == 2
        assert cat_counts[Category.BUSINESS_ADOPTION] == 2
        assert cat_counts[Category.PRODUCTIVITY_TOOLS] == 1
        assert cat_counts[Category.INDUSTRY_NEWS] == 2
        assert cat_counts[Category.SECURITY_RISK] == 1
        assert cat_counts[Category.GEMINI_N8N] == 2

    def test_redistributes_when_category_empty(self, settings):
        now = datetime.now(UTC)
        agg = NewsAggregator(sources=[], settings=settings)

        # No Gemini/n8n articles at all
        categorized = {
            Category.PRODUCT_LAUNCH: [
                make_article(
                    title=f"Launch {i}",
                    url=f"https://openai.com/launch-{i}",
                    published_at=now,
                )
                for i in range(5)
            ],
            Category.BUSINESS_ADOPTION: [
                make_article(
                    title="Biz 1", url="https://bloomberg.com/biz-1", published_at=now
                ),
            ],
            Category.PRODUCTIVITY_TOOLS: [],
            Category.INDUSTRY_NEWS: [
                make_article(
                    title="Industry 1",
                    url="https://reuters.com/industry-1",
                    published_at=now,
                ),
            ],
            Category.SECURITY_RISK: [
                make_article(
                    title="Security 1",
                    url="https://wired.com/security-1",
                    published_at=now,
                ),
            ],
            Category.GEMINI_N8N: [],
        }

        selected = agg._select_by_quota(categorized, 10)
        # Should still get articles even though some categories are empty
        assert len(selected) > 0
        # Overflow should fill from priority categories
        cat_counts = {}
        for cat, _ in selected:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        # Product launches should get extra slots from overflow
        assert cat_counts.get(Category.PRODUCT_LAUNCH, 0) > 2
