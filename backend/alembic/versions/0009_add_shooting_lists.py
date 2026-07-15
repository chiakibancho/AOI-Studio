"""add shooting_lists table

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

shooting_list_status = ENUM(
    "pending", "completed", "failed", name="shootingliststatus", create_type=False
)


def upgrade() -> None:
    shooting_list_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "shooting_lists",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("storyboard_id", sa.String(36), sa.ForeignKey("storyboards.id"), nullable=False),
        sa.Column("shots", JSONB, nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", shooting_list_status, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_shooting_lists_project_id", "shooting_lists", ["project_id"])
    op.create_index("ix_shooting_lists_storyboard_id", "shooting_lists", ["storyboard_id"])


def downgrade() -> None:
    op.drop_index("ix_shooting_lists_storyboard_id", table_name="shooting_lists")
    op.drop_index("ix_shooting_lists_project_id", table_name="shooting_lists")
    op.drop_table("shooting_lists")
    shooting_list_status.drop(op.get_bind(), checkfirst=True)
