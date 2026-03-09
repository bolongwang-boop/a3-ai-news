import logging
import re
from calendar import timegm
from datetime import datetime
from urllib.parse import quote_plus

import feedparser
import httpx

from src.models import Article, ArticleSource
from src.sources.base import NewsSource
from src.timezone import UTC_TZ, is_within_sydney_range, utc_to_sydney_str

logger = logging.getLogger(__name__)

AI_QUERY = (
    '"artificial intelligence" OR "machine learning" OR "deep learning" '
    'OR "large language model" OR "LLM" OR "generative AI" OR "GPT" '
    'OR "neural network" OR "ChatGPT" OR "Claude AI"'
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = _HTML_TAG_RE.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return _WHITESPACE_RE.sub(" ", text).strip()


class GoogleRSSSource(NewsSource):
    """Google News RSS feed integration.

    Always available (no API key required). The RSS `pubDate` field is the
    actual publication date of the article. Google News curates from
    established outlets, providing inherent credibility filtering.
    """

    RSS_BASE = "https://news.google.com/rss/search"

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    @property
    def name(self) -> str:
        return "google_rss"

    def is_available(self) -> bool:
        return True

    async def fetch_ai_news(
        self,
        from_date: datetime,
        to_date: datetime,
        max_results: int = 50,
    ) -> list[Article]:
        # Google News RSS supports `when:Nd` for "last N days" filtering.
        # We calculate the number of days from from_date to now.
        days_back = (to_date - from_date).days + 1

        query = f"{AI_QUERY} when:{days_back}d"
        url = f"{self.RSS_BASE}?q={quote_plus(query)}&hl=en-AU&gl=AU&ceid=AU:en"

        try:
            resp = await self._http_client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("Google RSS HTTP error: %s", e.response.status_code)
            return []
        except httpx.RequestError as e:
            logger.error("Google RSS request error: %s", e)
            return []

        feed = feedparser.parse(resp.text)

        articles: list[Article] = []
        for entry in feed.entries[:max_results]:
            published_parsed = entry.get("published_parsed")
            if not published_parsed:
                continue

            published_at = datetime.fromtimestamp(timegm(published_parsed), tz=UTC_TZ)

            # Server-side re-validation: ensure the article was truly published
            # within our Sydney-based date range
            if not is_within_sydney_range(published_at, from_date, to_date):
                continue

            # Google News RSS titles: "Article Title - Source Name"
            raw_title = entry.get("title", "")
            source_name = "Unknown"
            title = raw_title
            if " - " in raw_title:
                parts = raw_title.rsplit(" - ", 1)
                title = parts[0].strip()
                source_name = parts[1].strip()

            articles.append(
                Article(
                    title=title,
                    description=_strip_html(entry.get("summary", "")) or None,
                    url=entry.get("link", ""),
                    published_at=published_at,
                    published_at_sydney=utc_to_sydney_str(published_at),
                    source=ArticleSource(name=source_name),
                    image_url=None,
                    fetched_from=self.name,
                )
            )

        return articles

    async def fetch_targeted_news(
        self,
        query: str,
        from_date: datetime,
        to_date: datetime,
        max_results: int = 20,
    ) -> list[Article]:
        days_back = (to_date - from_date).days + 1
        full_query = f"{query} when:{days_back}d"
        url = f"{self.RSS_BASE}?q={quote_plus(full_query)}&hl=en-AU&gl=AU&ceid=AU:en"

        try:
            resp = await self._http_client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("Google RSS targeted HTTP error: %s", e.response.status_code)
            return []
        except httpx.RequestError as e:
            logger.error("Google RSS targeted request error: %s", e)
            return []

        feed = feedparser.parse(resp.text)

        articles: list[Article] = []
        for entry in feed.entries[:max_results]:
            published_parsed = entry.get("published_parsed")
            if not published_parsed:
                continue

            published_at = datetime.fromtimestamp(timegm(published_parsed), tz=UTC_TZ)

            if not is_within_sydney_range(published_at, from_date, to_date):
                continue

            raw_title = entry.get("title", "")
            source_name = "Unknown"
            title = raw_title
            if " - " in raw_title:
                parts = raw_title.rsplit(" - ", 1)
                title = parts[0].strip()
                source_name = parts[1].strip()

            articles.append(
                Article(
                    title=title,
                    description=_strip_html(entry.get("summary", "")) or None,
                    url=entry.get("link", ""),
                    published_at=published_at,
                    published_at_sydney=utc_to_sydney_str(published_at),
                    source=ArticleSource(name=source_name),
                    image_url=None,
                    fetched_from=self.name,
                )
            )

        return articles
