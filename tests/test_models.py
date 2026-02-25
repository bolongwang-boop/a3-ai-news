from datetime import datetime
from zoneinfo import ZoneInfo

from src.models import Article, ArticleSource, NewsResponse

UTC = ZoneInfo("UTC")


class TestArticleSource:
    def test_defaults(self):
        source = ArticleSource(name="Test")
        assert source.url is None
        assert source.is_credible is False

    def test_all_fields(self):
        source = ArticleSource(name="BBC", url="https://bbc.com", is_credible=True)
        assert source.name == "BBC"
        assert source.is_credible is True


class TestArticle:
    def test_required_fields(self):
        article = Article(
            title="Test",
            url="https://example.com",
            published_at=datetime(2026, 2, 20, tzinfo=UTC),
            published_at_sydney="2026-02-20 11:00:00 AEDT",
            source=ArticleSource(name="Test"),
            fetched_from="newsapi",
        )
        assert article.title == "Test"
        assert article.description is None
        assert article.image_url is None

    def test_json_serialization(self):
        article = Article(
            title="Test",
            url="https://example.com",
            published_at=datetime(2026, 2, 20, tzinfo=UTC),
            published_at_sydney="2026-02-20 11:00:00 AEDT",
            source=ArticleSource(name="Test"),
            fetched_from="newsapi",
        )
        data = article.model_dump(mode="json")
        assert isinstance(data["published_at"], str)
        assert isinstance(data["source"], dict)


class TestNewsResponse:
    def test_structure(self):
        resp = NewsResponse(
            total_articles=0,
            query="test",
            from_date_sydney="2026-02-18 00:00:00 AEDT",
            to_date_sydney="2026-02-25 12:00:00 AEDT",
            sources_queried=["google_rss"],
            articles=[],
        )
        assert resp.total_articles == 0
        assert resp.articles == []

    def test_with_articles(self):
        article = Article(
            title="Test",
            url="https://example.com",
            published_at=datetime(2026, 2, 20, tzinfo=UTC),
            published_at_sydney="2026-02-20 11:00:00 AEDT",
            source=ArticleSource(name="Test"),
            fetched_from="newsapi",
        )
        resp = NewsResponse(
            total_articles=1,
            query="test",
            from_date_sydney="2026-02-18 00:00:00 AEDT",
            to_date_sydney="2026-02-25 12:00:00 AEDT",
            sources_queried=["newsapi"],
            articles=[article],
        )
        assert len(resp.articles) == 1
        assert resp.articles[0].title == "Test"
