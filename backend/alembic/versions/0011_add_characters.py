"""add characters table

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

character_status = ENUM(
    "draft", "generating", "generated", "failed", "approved", name="characterstatus", create_type=False
)


def upgrade() -> None:
    character_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "characters",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("variables", JSONB, nullable=False, server_default="{}"),
        sa.Column("template_version", sa.String(16), nullable=False),
        sa.Column("sheet_image_path", sa.String(512), nullable=True),
        sa.Column("status", character_status, nullable=False, server_default="draft"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_characters_project_id", "characters", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_characters_project_id", table_name="characters")
    op.drop_table("characters")
    character_status.drop(op.get_bind(), checkfirst=True)
