"""Create articles table

Revision ID: 001
Revises:
Create Date: 2026-02-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at_sydney", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=256), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("source_is_credible", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("fetched_from", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_source_credible", "articles", ["source_is_credible"])
    op.create_index("ix_articles_url", "articles", ["url"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_articles_url", table_name="articles")
    op.drop_index("ix_articles_source_credible", table_name="articles")
    op.drop_index("ix_articles_published_at", table_name="articles")
    op.drop_table("articles")
