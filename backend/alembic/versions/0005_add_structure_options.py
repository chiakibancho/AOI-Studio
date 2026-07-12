"""add structure options (3-proposal support)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "structures",
        sa.Column(
            "options",
            JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "structures",
        sa.Column("selected_option_index", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("structures", "selected_option_index")
    op.drop_column("structures", "options")
