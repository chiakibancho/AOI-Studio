"""add music_analyses table

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "music_analyses",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, unique=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("bpm", sa.Float, nullable=False),
        sa.Column("key", sa.String(8), nullable=False),
        sa.Column("scale", sa.String(16), nullable=False),
        sa.Column("key_strength", sa.Float, nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_music_analyses_project_id", "music_analyses", ["project_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_music_analyses_project_id", table_name="music_analyses")
    op.drop_table("music_analyses")
