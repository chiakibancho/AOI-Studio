"""add structure revision (human feedback) support

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "structures",
        sa.Column("human_feedback", sa.Text(), nullable=True),
    )
    op.add_column(
        "structures",
        sa.Column(
            "based_on_structure_id",
            sa.String(36),
            sa.ForeignKey("structures.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("structures", "based_on_structure_id")
    op.drop_column("structures", "human_feedback")
