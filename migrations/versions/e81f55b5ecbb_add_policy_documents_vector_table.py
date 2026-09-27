"""add policy documents vector table

Revision ID: e81f55b5ecbb
Revises: 27176a233e7c
Create Date: 2026-09-27 01:55:09.563093
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "e81f55b5ecbb"
down_revision: Union[str, Sequence[str], None] = "27176a233e7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 pgvector 扩展和政策知识表。"""
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS vector"
    )

    op.create_table(
        "policy_documents",
        sa.Column(
            "policy_id",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            Vector(dim=512),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("policy_id"),
    )

    op.create_index(
        "ix_policy_documents_category",
        "policy_documents",
        ["category"],
        unique=False,
    )


def downgrade() -> None:
    """删除政策知识表，但保留共享的 vector 扩展。"""
    op.drop_index(
        "ix_policy_documents_category",
        table_name="policy_documents",
    )
    op.drop_table("policy_documents")