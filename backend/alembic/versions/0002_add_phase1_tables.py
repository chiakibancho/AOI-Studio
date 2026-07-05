"""add phase1 tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_specs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, unique=True),
        sa.Column("duration_sec", sa.Integer, nullable=False),
        sa.Column("target_audience", sa.Text, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("mood", sa.String(100), nullable=False),
        sa.Column("style_notes", sa.Text, nullable=True),
        sa.Column("reference_urls", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_video_specs_project_id", "video_specs", ["project_id"], unique=True)

    op.create_table(
        "structures",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("scenes", JSONB, nullable=False),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("total_duration_sec", sa.Integer, nullable=False, server_default="0"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_structures_project_id", "structures", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_structures_project_id", table_name="structures")
    op.drop_table("structures")
    op.drop_index("ix_video_specs_project_id", table_name="video_specs")
    op.drop_table("video_specs")
