import logging
from datetime import datetime

import httpx

from src.models import Article, ArticleSource
from src.sources.base import NewsSource
from src.timezone import utc_to_sydney_str

logger = logging.getLogger(__name__)

AI_QUERY = (
    '"artificial intelligence" OR "AI" OR "machine learning" '
    'OR "deep learning" OR "large language model" OR "LLM" '
    'OR "GPT" OR "neural network" OR "generative AI" '
    'OR "transformer model" OR "ChatGPT" OR "Claude AI"'
)


class NewsAPISource(NewsSource):
    """NewsAPI.org integration.

    Uses the /everything endpoint which filters by `publishedAt` —
    the actual publication date of the article, not when it was last updated.
    """

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str | None, http_client: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._http_client = http_client

    @property
    def name(self) -> str:
        return "newsapi"

    def is_available(self) -> bool:
        return self._api_key is not None

    async def fetch_ai_news(
        self,
        from_date: datetime,
        to_date: datetime,
        max_results: int = 50,
    ) -> list[Article]:
        if not self.is_available():
            return []

        params = {
            "q": AI_QUERY,
            "from": from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": to_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": min(max_results, 100),
            "apiKey": self._api_key,
        }

        try:
            resp = await self._http_client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("NewsAPI HTTP error: %s", e.response.text)
            return []
        except httpx.RequestError as e:
            logger.error("NewsAPI request error: %s", e)
            return []

        if data.get("status") != "ok":
            logger.error("NewsAPI returned status: %s", data.get("status"))
            return []

        articles: list[Article] = []
        for item in data.get("articles", []):
            published_str = item.get("publishedAt")
            if not published_str:
                continue

            published_at = datetime.fromisoformat(
                published_str.replace("Z", "+00:00")
            )

            source_name = (item.get("source") or {}).get("name", "Unknown")

            articles.append(
                Article(
                    title=item.get("title", ""),
                    description=item.get("description"),
                    url=item.get("url", ""),
                    published_at=published_at,
                    published_at_sydney=utc_to_sydney_str(published_at),
                    source=ArticleSource(name=source_name),
                    image_url=item.get("urlToImage"),
                    fetched_from=self.name,
                )
            )

        return articles
