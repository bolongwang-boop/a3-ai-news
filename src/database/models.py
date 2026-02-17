from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ArticleRow(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at_sydney: Mapped[str] = mapped_column(String(64), nullable=False)

    source_name: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_is_credible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    fetched_from: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_source_credible", "source_is_credible"),
        Index("ix_articles_url", "url", unique=True),
    )
