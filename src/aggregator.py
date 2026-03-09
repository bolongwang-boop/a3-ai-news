import asyncio
import logging
import re
from urllib.parse import urlparse

from src.categories import (
    CATEGORY_LABELS,
    CATEGORY_QUOTAS,
    Category,
    OVERFLOW_PRIORITY,
    classify_article,
)
from src.config import Settings
from src.models import Article, CuratedArticle, DigestResponse, NewsResponse
from src.sources.base import NewsSource
from src.timezone import (
    get_week_range_sydney,
    is_within_sydney_range,
    utc_to_sydney_str,
)

logger = logging.getLogger(__name__)

# Post-fetch relevance filter: at least one AI keyword must appear in title or description.
_AI_RELEVANCE_RE = re.compile(
    r"\b("
    r"artificial intelligence|machine learning|deep learning"
    r"|large language model|generative AI|neural network"
    r"|transformer model|computer vision|natural language processing"
    r"|LLM|GPT|ChatGPT|OpenAI|DeepMind|Anthropic|Claude AI"
    r"|Gemini|Copilot|Midjourney|Stable Diffusion|Hugging Face"
    r"|AI agent|AI model|AI safety|AI regulation|AI"
    r")\b",
    re.IGNORECASE,
)


def _is_ai_relevant(article: Article) -> bool:
    """Check if an article's title or description mentions AI-related keywords."""
    text = f"{article.title} {article.description or ''}"
    return _AI_RELEVANCE_RE.search(text) is not None


# Words too common or too short to be meaningful for title-URL matching.
_STOP_WORDS = frozenset(
    "a an and are as at be by for from has have how in is it its of on or "
    "that the this to was were will with new not but can do say says said "
    "could would should what who why where when may also over after all".split()
)

_SLUG_SPLIT_RE = re.compile(r"[\W_]+")


def _title_matches_url(article: Article) -> bool:
    """Check that meaningful words from the title appear in the URL path.

    Legitimate news URLs typically contain a slugified version of the title.
    This filters out articles where the search matched sidebar content but
    the actual page is about something else.

    Google News RSS wraps URLs through news.google.com/rss/articles/..., so
    we skip this check for those URLs.
    """
    url = article.url
    # Skip check for Google News redirect URLs — they don't contain the slug
    if "news.google.com" in url:
        return True

    path = urlparse(url).path.lower()
    title_words = {
        w.lower()
        for w in re.findall(r"[a-zA-Z]{3,}", article.title)
        if w.lower() not in _STOP_WORDS
    }

    if not title_words:
        return True  # Can't validate — allow through

    matches = sum(1 for w in title_words if w in path)
    # At least 30% of meaningful title words should appear in the URL
    return matches >= max(1, len(title_words) * 0.3)


def _normalize_title(title: str) -> str:
    """Normalize a title for deduplication: lowercase, strip punctuation, collapse spaces."""
    title = title.lower().strip()
    title = re.sub(r"[^\w\s]", "", title)
    return re.sub(r"\s+", " ", title)


def _title_keywords(title: str) -> set[str]:
    """Extract meaningful keywords from a title for fuzzy matching."""
    return {
        w.lower()
        for w in re.findall(r"[a-zA-Z]{3,}", title)
        if w.lower() not in _STOP_WORDS
    }


def _is_similar_title(keywords_a: set[str], keywords_b: set[str]) -> bool:
    """Check if two titles are similar enough to be the same story.

    Uses word overlap: if 70%+ of the shorter title's keywords appear
    in the longer title, they are considered duplicates. This catches
    cross-source duplicates like:
      - "OpenAI releases GPT-5" (NewsAPI)
      - "OpenAI releases GPT-5, its most powerful model yet" (Google RSS)
    """
    if not keywords_a or not keywords_b:
        return False
    shorter, longer = sorted([keywords_a, keywords_b], key=len)
    overlap = len(shorter & longer)
    return overlap >= max(2, len(shorter) * 0.7)


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
        tasks = [
            s.fetch_ai_news(from_utc, to_utc, max_results=max_results) for s in active
        ]
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
            a
            for a in all_articles
            if is_within_sydney_range(a.published_at, from_utc, to_utc)
        ]

        articles = self._deduplicate(articles)
        articles = [a for a in articles if _title_matches_url(a)]
        articles = [a for a in articles if _is_ai_relevant(a)]
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

    # Targeted queries to boost coverage for specific categories.
    _TARGETED_QUERIES: list[str] = [
        # Gemini / n8n
        '"Gemini" OR "Vertex AI" OR "Google AI Studio" OR "n8n" OR "n8n.io"',
        # Security / Risk
        (
            '"AI security" OR "AI vulnerability" OR "deepfake" '
            'OR "prompt injection" OR "AI safety" OR "AI threat"'
        ),
        # Productivity Tools
        (
            '"AI" AND ("Asana" OR "Notion" OR "Slack" OR "Google Workspace" '
            'OR "Microsoft 365" OR "GitHub Copilot" OR "Cursor")'
        ),
    ]

    async def fetch_curated_digest(
        self,
        days_back: int = 7,
        total_items: int = 10,
    ) -> DigestResponse:
        """Fetch and curate exactly N (default 10) AI news items, balanced by category.

        Steps:
        1. Fetch articles from all sources (general + targeted queries).
        2. Deduplicate, filter, mark credibility (credible only).
        3. Classify each article into a content category.
        4. Select articles per category according to quota.
        5. Return exactly total_items articles.
        """
        from_utc, to_utc = get_week_range_sydney(days_back)

        # 1. Fetch general + targeted queries concurrently
        active = self.available_sources
        tasks = []

        # General AI query from all sources
        for source in active:
            tasks.append(source.fetch_ai_news(from_utc, to_utc, max_results=100))

        # Targeted queries from all sources
        for source in active:
            for query in self._TARGETED_QUERIES:
                tasks.append(
                    source.fetch_targeted_news(query, from_utc, to_utc, max_results=20)
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[Article] = []
        sources_queried: list[str] = list({s.name for s in active})

        for result in results:
            if isinstance(result, BaseException):
                logger.error("Source query failed: %s", result)
                continue
            all_articles.extend(result)

        # 2. Filter pipeline (same as fetch_weekly_ai_news)
        articles = [
            a
            for a in all_articles
            if is_within_sydney_range(a.published_at, from_utc, to_utc)
        ]
        articles = self._deduplicate(articles)
        articles = [a for a in articles if _title_matches_url(a)]
        articles = [a for a in articles if _is_ai_relevant(a)]
        articles = self._mark_credibility(articles)
        articles = [a for a in articles if a.source.is_credible]
        articles.sort(key=lambda a: a.published_at, reverse=True)

        # 3. Classify into categories
        categorized: dict[Category, list[Article]] = {c: [] for c in Category}
        for article in articles:
            cat = classify_article(article)
            categorized[cat].append(article)

        # 4. Select per-category quota
        selected = self._select_by_quota(categorized, total_items)

        # 5. Build curated items
        items: list[CuratedArticle] = []
        for rank, (cat, article) in enumerate(selected, 1):
            items.append(
                CuratedArticle(
                    rank=rank,
                    category=cat.value,
                    category_label=CATEGORY_LABELS[cat],
                    title=article.title,
                    description=article.description,
                    source_name=article.source.name,
                    published_at_sydney=article.published_at_sydney,
                )
            )

        return DigestResponse(
            total_items=len(items),
            from_date_sydney=utc_to_sydney_str(from_utc),
            to_date_sydney=utc_to_sydney_str(to_utc),
            sources_queried=sources_queried,
            items=items,
        )

    def _select_by_quota(
        self,
        categorized: dict[Category, list[Article]],
        total: int,
    ) -> list[tuple[Category, Article]]:
        """Select articles balanced by category quotas.

        If a category has fewer articles than its quota, the surplus
        slots are redistributed to other categories in priority order.
        """
        selected: list[tuple[Category, Article]] = []
        remaining_slots: dict[Category, int] = dict(CATEGORY_QUOTAS)

        # First pass: fill each category up to its quota
        for cat in Category:
            quota = remaining_slots[cat]
            available = categorized.get(cat, [])[:quota]
            for article in available:
                selected.append((cat, article))
            remaining_slots[cat] = quota - len(available)

        # Second pass: redistribute unfilled slots
        surplus = sum(remaining_slots.values())
        if surplus > 0 and len(selected) < total:
            for cat in OVERFLOW_PRIORITY:
                if surplus <= 0:
                    break
                already_used = sum(1 for c, _ in selected if c == cat)
                available = categorized.get(cat, [])[already_used:]
                for article in available:
                    if surplus <= 0:
                        break
                    selected.append((cat, article))
                    surplus -= 1

        # Trim to total and sort by category order then recency
        selected = selected[:total]
        category_order = {c: i for i, c in enumerate(Category)}
        selected.sort(
            key=lambda x: (category_order[x[0]], -x[1].published_at.timestamp())
        )

        return selected

    def _deduplicate(self, articles: list[Article]) -> list[Article]:
        """Remove duplicates based on normalized URL, exact title, and fuzzy title similarity."""
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        seen_keywords: list[set[str]] = []
        unique: list[Article] = []
        for article in articles:
            url_key = self._normalize_url(article.url)
            title_key = _normalize_title(article.title)
            if url_key in seen_urls or title_key in seen_titles:
                continue
            # Fuzzy check: same story with slightly different titles across sources
            kw = _title_keywords(article.title)
            if any(_is_similar_title(kw, existing) for existing in seen_keywords):
                continue
            seen_urls.add(url_key)
            seen_titles.add(title_key)
            seen_keywords.append(kw)
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
