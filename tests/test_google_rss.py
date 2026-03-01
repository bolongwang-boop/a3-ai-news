from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import httpx
import pytest

from src.sources.google_rss import GoogleRSSSource, _strip_html

UTC = ZoneInfo("UTC")

# Minimal valid RSS XML template
RSS_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
{items}
</channel>
</rss>
"""

ITEM_TEMPLATE = """\
<item>
  <title>{title}</title>
  <link>{link}</link>
  <description>{description}</description>
  <pubDate>{pub_date}</pubDate>
</item>
"""


def _rss_date(dt: datetime) -> str:
    """Format datetime as RFC 2822 for RSS."""
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def _build_rss(*items: str) -> str:
    return RSS_TEMPLATE.format(items="\n".join(items))


def _build_item(
    title: str = "Test - Source",
    link: str = "https://example.com/1",
    description: str = "desc",
    pub_date: datetime | None = None,
) -> str:
    if pub_date is None:
        pub_date = datetime.now(UTC) - timedelta(hours=1)
    return ITEM_TEMPLATE.format(
        title=title, link=link, description=description, pub_date=_rss_date(pub_date)
    )


def _mock_response(text: str, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status_code, text=text, request=httpx.Request("GET", "https://x"))


def _source(response: httpx.Response | Exception) -> GoogleRSSSource:
    client = AsyncMock(spec=httpx.AsyncClient)
    if isinstance(response, Exception):
        client.get.side_effect = response
    else:
        client.get.return_value = response
    return GoogleRSSSource(http_client=client)


# ── _strip_html ────────────────────────────────────────────────

class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<b>bold</b> text") == "bold text"

    def test_replaces_entities(self):
        assert _strip_html("A&amp;B&nbsp;C") == "A&B C"

    def test_collapses_whitespace(self):
        assert _strip_html("  lots   of   space  ") == "lots of space"

    def test_empty_string(self):
        assert _strip_html("") == ""


# ── Properties ─────────────────────────────────────────────────

class TestGoogleRSSProperties:
    def test_name(self):
        src = GoogleRSSSource(http_client=AsyncMock())
        assert src.name == "google_rss"

    def test_is_available(self):
        src = GoogleRSSSource(http_client=AsyncMock())
        assert src.is_available() is True


# ── fetch_ai_news ──────────────────────────────────────────────

class TestGoogleRSSFetch:
    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        now = datetime.now(UTC)
        item = _build_item(title="AI Wins - TechCrunch", pub_date=now - timedelta(hours=1))
        rss = _build_rss(item)
        src = _source(_mock_response(rss))

        articles = await src.fetch_ai_news(now - timedelta(days=2), now)
        assert len(articles) == 1
        assert articles[0].fetched_from == "google_rss"

    @pytest.mark.asyncio
    async def test_http_status_error(self):
        resp = _mock_response("", status_code=500)
        resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("err", request=resp.request, response=resp))
        src = _source(resp)

        articles = await src.fetch_ai_news(datetime.now(UTC) - timedelta(days=1), datetime.now(UTC))
        assert articles == []

    @pytest.mark.asyncio
    async def test_request_error(self):
        src = _source(httpx.RequestError("timeout"))

        articles = await src.fetch_ai_news(datetime.now(UTC) - timedelta(days=1), datetime.now(UTC))
        assert articles == []

    @pytest.mark.asyncio
    async def test_skips_missing_pubdate(self):
        item_no_date = "<item><title>No Date - Src</title><link>https://x.com/1</link></item>"
        rss = _build_rss(item_no_date)
        src = _source(_mock_response(rss))

        articles = await src.fetch_ai_news(datetime.now(UTC) - timedelta(days=2), datetime.now(UTC))
        assert articles == []

    @pytest.mark.asyncio
    async def test_filters_out_of_range(self):
        now = datetime.now(UTC)
        old_item = _build_item(title="Old - Src", pub_date=now - timedelta(days=30))
        rss = _build_rss(old_item)
        src = _source(_mock_response(rss))

        articles = await src.fetch_ai_news(now - timedelta(days=1), now)
        assert articles == []

    @pytest.mark.asyncio
    async def test_parses_title_and_source(self):
        now = datetime.now(UTC)
        item = _build_item(title="Big AI News - BBC News", pub_date=now - timedelta(hours=1))
        rss = _build_rss(item)
        src = _source(_mock_response(rss))

        articles = await src.fetch_ai_news(now - timedelta(days=2), now)
        assert articles[0].title == "Big AI News"
        assert articles[0].source.name == "BBC News"

    @pytest.mark.asyncio
    async def test_title_without_dash(self):
        now = datetime.now(UTC)
        item = _build_item(title="Plain Title No Source", pub_date=now - timedelta(hours=1))
        rss = _build_rss(item)
        src = _source(_mock_response(rss))

        articles = await src.fetch_ai_news(now - timedelta(days=2), now)
        assert articles[0].title == "Plain Title No Source"
        assert articles[0].source.name == "Unknown"

    @pytest.mark.asyncio
    async def test_respects_max_results(self):
        now = datetime.now(UTC)
        items = [
            _build_item(title=f"Art {i} - Src", link=f"https://x.com/{i}", pub_date=now - timedelta(hours=1))
            for i in range(5)
        ]
        rss = _build_rss(*items)
        src = _source(_mock_response(rss))

        articles = await src.fetch_ai_news(now - timedelta(days=2), now, max_results=2)
        assert len(articles) <= 2

    @pytest.mark.asyncio
    async def test_strips_html_description(self):
        now = datetime.now(UTC)
        item = _build_item(
            title="HTML - Src",
            description="<b>Bold</b>&amp;stuff",
            pub_date=now - timedelta(hours=1),
        )
        rss = _build_rss(item)
        src = _source(_mock_response(rss))

        articles = await src.fetch_ai_news(now - timedelta(days=2), now)
        assert "<b>" not in (articles[0].description or "")
        assert "Bold" in (articles[0].description or "")
