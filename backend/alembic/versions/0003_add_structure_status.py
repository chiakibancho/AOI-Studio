"""add structure status tracking

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

structure_status = ENUM("pending", "completed", "failed", name="structurestatus")


def upgrade() -> None:
    structure_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "structures",
        sa.Column("status", structure_status, nullable=False, server_default="pending"),
    )
    op.add_column(
        "structures",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.alter_column(
        "structures",
        "scenes",
        existing_type=JSONB(astext_type=sa.Text()),
        server_default="[]",
    )


def downgrade() -> None:
    op.alter_column(
        "structures",
        "scenes",
        existing_type=JSONB(astext_type=sa.Text()),
        server_default=None,
    )
    op.drop_column("structures", "error_message")
    op.drop_column("structures", "status")
    structure_status.drop(op.get_bind(), checkfirst=True)
