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

    @abstractmethod
    def is_available(self) -> bool: ...
