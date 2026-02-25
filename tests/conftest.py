from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.config import Settings
from src.models import Article, ArticleSource

UTC = ZoneInfo("UTC")


def make_article(
    title: str = "Test Article",
    url: str = "https://techcrunch.com/2026/02/20/test",
    source_name: str = "TechCrunch",
    source_url: str | None = None,
    is_credible: bool = False,
    fetched_from: str = "google_rss",
    published_at: datetime | None = None,
    description: str | None = "A test article about AI.",
    image_url: str | None = None,
) -> Article:
    if published_at is None:
        published_at = datetime.now(UTC) - timedelta(hours=2)
    return Article(
        title=title,
        description=description,
        url=url,
        published_at=published_at,
        published_at_sydney="2026-02-20 10:00:00 AEDT",
        source=ArticleSource(name=source_name, url=source_url, is_credible=is_credible),
        image_url=image_url,
        fetched_from=fetched_from,
    )


@pytest.fixture
def sample_article():
    return make_article()


@pytest.fixture
def sample_articles():
    return [
        make_article(
            title="OpenAI releases GPT-5",
            url="https://openai.com/blog/gpt-5",
            source_name="OpenAI",
            fetched_from="newsapi",
        ),
        make_article(
            title="Google DeepMind breakthrough",
            url="https://www.bbc.com/news/ai-deepmind",
            source_name="BBC News",
            fetched_from="google_rss",
        ),
        make_article(
            title="Random AI blog post",
            url="https://randomblog.xyz/ai-post",
            source_name="Random Blog",
            fetched_from="google_rss",
        ),
    ]


@pytest.fixture
def default_settings():
    return Settings(newsapi_key=None)
