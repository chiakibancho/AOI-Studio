"""simplify characters: drop variables/template_version, add prompt

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("prompt", sa.Text, nullable=False, server_default=""),
    )
    op.drop_column("characters", "variables")
    op.drop_column("characters", "template_version")


def downgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("template_version", sa.String(16), nullable=False, server_default="v1"),
    )
    op.add_column(
        "characters",
        sa.Column("variables", JSONB, nullable=False, server_default="{}"),
    )
    op.drop_column("characters", "prompt")
