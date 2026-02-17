import logging
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.models import ArticleRow
from src.models import Article, ArticleSource

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Repository for persisting and querying articles in PostgreSQL."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_articles(self, articles: list[Article]) -> int:
        """Insert articles, updating on URL conflict. Returns count of upserted rows."""
        if not articles:
            return 0

        async with self._session_factory() as session:
            values = [
                {
                    "title": a.title,
                    "description": a.description,
                    "url": a.url,
                    "published_at": a.published_at,
                    "published_at_sydney": a.published_at_sydney,
                    "source_name": a.source.name,
                    "source_url": a.source.url,
                    "source_is_credible": a.source.is_credible,
                    "image_url": a.image_url,
                    "fetched_from": a.fetched_from,
                }
                for a in articles
            ]

            stmt = pg_insert(ArticleRow).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["url"],
                set_={
                    "title": stmt.excluded.title,
                    "description": stmt.excluded.description,
                    "source_is_credible": stmt.excluded.source_is_credible,
                    "updated_at": func.now(),
                },
            )

            result = await session.execute(stmt)
            await session.commit()

            count = result.rowcount  # type: ignore[union-attr]
            logger.info("Upserted %d articles", count)
            return count

    async def get_articles(
        self,
        from_date: datetime,
        to_date: datetime,
        credible_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[Article]]:
        """Fetch articles from database within date range. Returns (total_count, articles)."""
        async with self._session_factory() as session:
            base = select(ArticleRow).where(
                ArticleRow.published_at >= from_date,
                ArticleRow.published_at <= to_date,
            )

            if credible_only:
                base = base.where(ArticleRow.source_is_credible.is_(True))

            # Get total count
            count_stmt = select(func.count()).select_from(base.subquery())
            total = (await session.execute(count_stmt)).scalar_one()

            # Get paginated results
            query = (
                base
                .order_by(ArticleRow.published_at.desc())
                .offset(offset)
                .limit(limit)
            )

            rows = (await session.execute(query)).scalars().all()

            articles = [self._row_to_article(row) for row in rows]
            return total, articles

    async def cleanup_old_articles(self, before_date: datetime) -> int:
        """Delete articles older than the given date. Returns count of deleted rows."""
        async with self._session_factory() as session:
            stmt = delete(ArticleRow).where(ArticleRow.published_at < before_date)
            result = await session.execute(stmt)
            await session.commit()

            count = result.rowcount  # type: ignore[union-attr]
            logger.info("Cleaned up %d old articles (before %s)", count, before_date)
            return count

    async def get_stats(self) -> dict:
        """Return article count statistics."""
        async with self._session_factory() as session:
            total = (await session.execute(select(func.count(ArticleRow.id)))).scalar_one()
            credible = (
                await session.execute(
                    select(func.count(ArticleRow.id)).where(
                        ArticleRow.source_is_credible.is_(True)
                    )
                )
            ).scalar_one()

            return {"total_articles": total, "credible_articles": credible}

    @staticmethod
    def _row_to_article(row: ArticleRow) -> Article:
        return Article(
            title=row.title,
            description=row.description,
            url=row.url,
            published_at=row.published_at,
            published_at_sydney=row.published_at_sydney,
            source=ArticleSource(
                name=row.source_name,
                url=row.source_url,
                is_credible=row.source_is_credible,
            ),
            image_url=row.image_url,
            fetched_from=row.fetched_from,
        )
