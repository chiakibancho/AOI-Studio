"""add sort_order to characters

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )
    # 既存レコードはプロジェクトごとに created_at 順で連番を振り直す
    op.execute(
        """
        UPDATE characters
        SET sort_order = sub.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY created_at) - 1 AS rn
            FROM characters
        ) AS sub
        WHERE characters.id = sub.id
        """
    )


def downgrade() -> None:
    op.drop_column("characters", "sort_order")
