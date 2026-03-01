from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import httpx
import pytest

from src.sources.newsapi import NewsAPISource

UTC = ZoneInfo("UTC")


def _json_response(data: dict, status_code: int = 200) -> httpx.Response:
    resp = httpx.Response(status_code=status_code, json=data, request=httpx.Request("GET", "https://x"))
    return resp


def _source(api_key: str | None, response: httpx.Response | Exception) -> NewsAPISource:
    client = AsyncMock(spec=httpx.AsyncClient)
    if isinstance(response, Exception):
        client.get.side_effect = response
    else:
        client.get.return_value = response
    return NewsAPISource(api_key=api_key, http_client=client)


def _ok_payload(*articles: dict) -> dict:
    return {"status": "ok", "articles": list(articles)}


def _article_dict(
    title: str = "AI News",
    url: str = "https://example.com/1",
    published_at: str | None = None,
    source_name: str | None = "TechCrunch",
    description: str | None = "desc",
    image_url: str | None = None,
) -> dict:
    if published_at is None:
        published_at = (datetime.now(UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    d: dict = {
        "title": title,
        "url": url,
        "publishedAt": published_at,
        "description": description,
        "urlToImage": image_url,
    }
    if source_name is not None:
        d["source"] = {"name": source_name}
    else:
        d["source"] = None
    return d


# ── Properties ─────────────────────────────────────────────────

class TestNewsAPIProperties:
    def test_name(self):
        src = NewsAPISource(api_key="k", http_client=AsyncMock())
        assert src.name == "newsapi"

    def test_available_with_key(self):
        src = NewsAPISource(api_key="test-key", http_client=AsyncMock())
        assert src.is_available() is True

    def test_unavailable_without_key(self):
        src = NewsAPISource(api_key=None, http_client=AsyncMock())
        assert src.is_available() is False


# ── fetch_ai_news ──────────────────────────────────────────────

class TestNewsAPIFetch:
    @pytest.mark.asyncio
    async def test_returns_empty_when_unavailable(self):
        src = _source(None, _json_response(_ok_payload()))
        articles = await src.fetch_ai_news(datetime.now(UTC) - timedelta(days=1), datetime.now(UTC))
        assert articles == []

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        payload = _ok_payload(_article_dict(title="GPT-5 Released"))
        src = _source("key", _json_response(payload))

        now = datetime.now(UTC)
        articles = await src.fetch_ai_news(now - timedelta(days=1), now)
        assert len(articles) == 1
        assert articles[0].title == "GPT-5 Released"
        assert articles[0].fetched_from == "newsapi"

    @pytest.mark.asyncio
    async def test_http_status_error(self):
        resp = _json_response({}, status_code=500)
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("err", request=resp.request, response=resp)
        )
        src = _source("key", resp)

        articles = await src.fetch_ai_news(datetime.now(UTC) - timedelta(days=1), datetime.now(UTC))
        assert articles == []

    @pytest.mark.asyncio
    async def test_request_error(self):
        src = _source("key", httpx.RequestError("timeout"))
        articles = await src.fetch_ai_news(datetime.now(UTC) - timedelta(days=1), datetime.now(UTC))
        assert articles == []

    @pytest.mark.asyncio
    async def test_non_ok_status(self):
        payload = {"status": "error", "message": "rate limited"}
        src = _source("key", _json_response(payload))

        articles = await src.fetch_ai_news(datetime.now(UTC) - timedelta(days=1), datetime.now(UTC))
        assert articles == []

    @pytest.mark.asyncio
    async def test_skips_missing_published_at(self):
        item = _article_dict()
        item["publishedAt"] = None
        payload = _ok_payload(item)
        src = _source("key", _json_response(payload))

        articles = await src.fetch_ai_news(datetime.now(UTC) - timedelta(days=1), datetime.now(UTC))
        assert articles == []

    @pytest.mark.asyncio
    async def test_parses_source_name(self):
        payload = _ok_payload(_article_dict(source_name="BBC News"))
        src = _source("key", _json_response(payload))

        now = datetime.now(UTC)
        articles = await src.fetch_ai_news(now - timedelta(days=1), now)
        assert articles[0].source.name == "BBC News"

    @pytest.mark.asyncio
    async def test_missing_source_defaults_unknown(self):
        payload = _ok_payload(_article_dict(source_name=None))
        src = _source("key", _json_response(payload))

        now = datetime.now(UTC)
        articles = await src.fetch_ai_news(now - timedelta(days=1), now)
        assert articles[0].source.name == "Unknown"

    @pytest.mark.asyncio
    async def test_includes_image_url(self):
        payload = _ok_payload(_article_dict(image_url="https://img.com/photo.jpg"))
        src = _source("key", _json_response(payload))

        now = datetime.now(UTC)
        articles = await src.fetch_ai_news(now - timedelta(days=1), now)
        assert articles[0].image_url == "https://img.com/photo.jpg"
