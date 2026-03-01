import asyncio
import logging
from urllib.parse import urlparse

from src.config import Settings
from src.models import Article, NewsResponse
from src.sources.base import NewsSource
from src.timezone import get_week_range_sydney, is_within_sydney_range, utc_to_sydney_str

logger = logging.getLogger(__name__)


_DOMAIN_TO_NAME = {
    "reuters.com": "Reuters",
    "apnews.com": "AP News",
    "bbc.com": "BBC News",
    "bbc.co.uk": "BBC News",
    "theguardian.com": "The Guardian",
    "nytimes.com": "The New York Times",
    "washingtonpost.com": "The Washington Post",
    "abc.net.au": "ABC News",
    "sbs.com.au": "SBS News",
    "smh.com.au": "The Sydney Morning Herald",
    "techcrunch.com": "TechCrunch",
    "wired.com": "WIRED",
    "arstechnica.com": "Ars Technica",
    "theverge.com": "The Verge",
    "technologyreview.com": "MIT Technology Review",
    "venturebeat.com": "VentureBeat",
    "zdnet.com": "ZDNET",
    "cnet.com": "CNET",
    "engadget.com": "Engadget",
    "tomsguide.com": "Tom's Guide",
    "nature.com": "Nature",
    "science.org": "Science",
    "ieee.org": "IEEE",
    "acm.org": "ACM",
    "scientificamerican.com": "Scientific American",
    "bloomberg.com": "Bloomberg",
    "ft.com": "Financial Times",
    "cnbc.com": "CNBC",
    "businessinsider.com": "Business Insider",
    "forbes.com": "Forbes",
    "fortune.com": "Fortune",
    "hbr.org": "Harvard Business Review",
    "vox.com": "Vox",
    "observer.com": "Observer",
    "cio.com": "CIO",
    "eweek.com": "eWeek",
    "infoworld.com": "InfoWorld",
    "computerworld.com": "Computerworld",
    "csoonline.com": "CSO Online",
    "networkworld.com": "Network World",
    "towardsdatascience.com": "Towards Data Science",
    "openai.com": "OpenAI",
    "deepmind.google": "Google DeepMind",
    "anthropic.com": "Anthropic",
    "arxiv.org": "arXiv",
    "huggingface.co": "Hugging Face",
    "aws.amazon.com": "Amazon Web Services",
    "cloud.google.com": "Google Cloud",
    "azure.microsoft.com": "Microsoft Azure",
}

# Aliases: Google RSS source names that don't match _DOMAIN_TO_NAME values.
# Maps lowered RSS source name -> canonical credible name.
_NAME_ALIASES = {
    "australian broadcasting corporation": "ABC News",
    "abc news (australia)": "ABC News",
    "bbc": "BBC News",
    "bbc news": "BBC News",
    "wired": "WIRED",
    "zdnet": "ZDNET",
    "amazon web services (aws)": "Amazon Web Services",
    "amazon web services": "Amazon Web Services",
    "towards data science": "Towards Data Science",
    "harvard business review": "Harvard Business Review",
}

# Build a reverse lookup: lowered source name -> credible
_CREDIBLE_NAMES = {name.lower() for name in _DOMAIN_TO_NAME.values()}
_CREDIBLE_NAMES.update(alias.lower() for alias in _NAME_ALIASES.keys())


class NewsAggregator:
    def __init__(
        self,
        sources: list[NewsSource],
        settings: Settings,
        repository=None,
    ) -> None:
        self._sources = sources
        self._credible_domains = set(settings.credible_domains)
        self._repository = repository

    @property
    def available_sources(self) -> list[NewsSource]:
        return [s for s in self._sources if s.is_available()]

    async def fetch_weekly_ai_news(
        self,
        days_back: int = 7,
        credible_only: bool = True,
        limit: int | None = None,
        max_results: int = 100,
    ) -> NewsResponse:
        from_utc, to_utc = get_week_range_sydney(days_back)

        active = self.available_sources
        tasks = [s.fetch_ai_news(from_utc, to_utc, max_results=max_results) for s in active]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[Article] = []
        sources_queried: list[str] = []

        for source, result in zip(active, results):
            if isinstance(result, BaseException):
                logger.error("Source %s failed: %s", source.name, result)
                continue
            sources_queried.append(source.name)
            all_articles.extend(result)

        # Server-side re-validation of published date
        articles = [
            a for a in all_articles
            if is_within_sydney_range(a.published_at, from_utc, to_utc)
        ]

        articles = self._deduplicate(articles)
        articles = self._mark_credibility(articles)

        # Persist to database if available
        if self._repository is not None:
            try:
                await self._repository.upsert_articles(articles)
            except Exception:
                logger.exception("Failed to persist articles to database")

        if credible_only:
            articles = [a for a in articles if a.source.is_credible]

        # Sort newest first
        articles.sort(key=lambda a: a.published_at, reverse=True)

        # Apply limit
        if limit is not None:
            articles = articles[:limit]

        return NewsResponse(
            total_articles=len(articles),
            query="AI news (last week, Sydney time)",
            from_date_sydney=utc_to_sydney_str(from_utc),
            to_date_sydney=utc_to_sydney_str(to_utc),
            sources_queried=sources_queried,
            articles=articles,
        )

    async def fetch_from_database(
        self,
        days_back: int = 7,
        credible_only: bool = True,
        limit: int | None = None,
    ) -> NewsResponse:
        """Fetch articles from the database (cached/persisted data)."""
        if self._repository is None:
            raise RuntimeError("Database persistence is not enabled")

        from_utc, to_utc = get_week_range_sydney(days_back)

        total, articles = await self._repository.get_articles(
            from_date=from_utc,
            to_date=to_utc,
            credible_only=credible_only,
            limit=limit or 500,
        )

        return NewsResponse(
            total_articles=total,
            query="AI news (cached, Sydney time)",
            from_date_sydney=utc_to_sydney_str(from_utc),
            to_date_sydney=utc_to_sydney_str(to_utc),
            sources_queried=["database"],
            articles=articles,
        )

    def _deduplicate(self, articles: list[Article]) -> list[Article]:
        """Remove duplicates based on normalized URL."""
        seen: set[str] = set()
        unique: list[Article] = []
        for article in articles:
            key = self._normalize_url(article.url)
            if key not in seen:
                seen.add(key)
                unique.append(article)
        return unique

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        # Strip www., trailing slash, and query params for dedup
        host = parsed.netloc.removeprefix("www.")
        path = parsed.path.rstrip("/")
        return f"{host}{path}"

    def _mark_credibility(self, articles: list[Article]) -> list[Article]:
        for article in articles:
            domain = self._extract_domain(article.source.url or article.url)
            name_lower = article.source.name.lower()
            # Check by domain first, then fall back to name-based matching
            # (Google RSS wraps URLs through news.google.com, so domain check
            # won't work — but the source name is reliably extracted from the title)
            by_domain = domain in self._credible_domains
            by_name = name_lower in _CREDIBLE_NAMES
            # Google RSS sometimes uses the domain as the source name (e.g. "cio.com")
            by_name_as_domain = name_lower in self._credible_domains
            article.source.is_credible = by_domain or by_name or by_name_as_domain
            article.source.url = article.source.url or article.url
        return articles

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc.removeprefix("www.")
        return host
