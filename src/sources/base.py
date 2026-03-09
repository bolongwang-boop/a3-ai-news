from abc import ABC, abstractmethod
from datetime import datetime

from src.models import Article


class NewsSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def fetch_ai_news(
        self,
        from_date: datetime,
        to_date: datetime,
        max_results: int = 50,
    ) -> list[Article]: ...

    async def fetch_targeted_news(
        self,
        query: str,
        from_date: datetime,
        to_date: datetime,
        max_results: int = 20,
    ) -> list[Article]:
        """Fetch news using a custom query string.

        Default implementation falls back to fetch_ai_news (ignoring the query).
        Subclasses can override to use the custom query with their API.
        """
        return await self.fetch_ai_news(from_date, to_date, max_results)

    @abstractmethod
    def is_available(self) -> bool: ...
