from datetime import datetime

from pydantic import BaseModel


class ArticleSource(BaseModel):
    name: str
    url: str | None = None
    is_credible: bool = False


class Article(BaseModel):
    title: str
    description: str | None = None
    url: str
    published_at: datetime
    published_at_sydney: str
    source: ArticleSource
    image_url: str | None = None
    fetched_from: str


class NewsResponse(BaseModel):
    total_articles: int
    query: str
    from_date_sydney: str
    to_date_sydney: str
    sources_queried: list[str]
    articles: list[Article]


class CuratedArticle(BaseModel):
    """An article selected for the curated digest, with category label."""

    rank: int
    category: str
    category_label: str
    title: str
    description: str | None = None
    source_name: str
    published_at_sydney: str


class DigestResponse(BaseModel):
    """Curated top-10 AI news digest with category-balanced selection."""

    total_items: int
    from_date_sydney: str
    to_date_sydney: str
    sources_queried: list[str]
    items: list[CuratedArticle]
