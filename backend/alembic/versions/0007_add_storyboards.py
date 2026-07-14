"""add storyboards table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

storyboard_status = ENUM(
    "pending", "completed", "failed", name="storyboardstatus", create_type=False
)


def upgrade() -> None:
    storyboard_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "storyboards",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("structure_id", sa.String(36), sa.ForeignKey("structures.id"), nullable=False),
        sa.Column("scenes", JSONB, nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", storyboard_status, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_storyboards_project_id", "storyboards", ["project_id"])
    op.create_index("ix_storyboards_structure_id", "storyboards", ["structure_id"])


def downgrade() -> None:
    op.drop_index("ix_storyboards_structure_id", table_name="storyboards")
    op.drop_index("ix_storyboards_project_id", table_name="storyboards")
    op.drop_table("storyboards")
    storyboard_status.drop(op.get_bind(), checkfirst=True)
