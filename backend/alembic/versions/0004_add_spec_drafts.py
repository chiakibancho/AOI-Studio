"""add spec_drafts table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

spec_draft_status = ENUM("pending", "completed", "failed", name="specdraftstatus")


def upgrade() -> None:
    spec_draft_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "spec_drafts",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("raw_input", sa.Text, nullable=False),
        sa.Column("duration_sec", sa.Integer, nullable=False, server_default="0"),
        sa.Column("target_audience", sa.Text, nullable=False, server_default=""),
        sa.Column("message", sa.Text, nullable=False, server_default=""),
        sa.Column("mood", sa.String(100), nullable=False, server_default=""),
        sa.Column("style_notes", sa.Text, nullable=True),
        sa.Column("reference_urls", JSONB, nullable=False, server_default="[]"),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", spec_draft_status, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_spec_drafts_project_id", "spec_drafts", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_spec_drafts_project_id", table_name="spec_drafts")
    op.drop_table("spec_drafts")
    spec_draft_status.drop(op.get_bind(), checkfirst=True)
