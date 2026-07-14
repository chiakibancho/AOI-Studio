"""add storyboard revision (human feedback) support

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "storyboards",
        sa.Column("human_feedback", sa.Text(), nullable=True),
    )
    op.add_column(
        "storyboards",
        sa.Column(
            "based_on_storyboard_id",
            sa.String(36),
            sa.ForeignKey("storyboards.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("storyboards", "based_on_storyboard_id")
    op.drop_column("storyboards", "human_feedback")
