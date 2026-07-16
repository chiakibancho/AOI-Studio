"""add shot_images table

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

shot_image_status = ENUM(
    "generating", "generated", "failed", name="shotimagestatus", create_type=False
)


def upgrade() -> None:
    shot_image_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "shot_images",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("shooting_list_id", sa.String(36), sa.ForeignKey("shooting_lists.id"), nullable=False),
        sa.Column("cut_number", sa.Integer, nullable=False),
        sa.Column("image_path", sa.String(512), nullable=True),
        sa.Column("status", shot_image_status, nullable=False, server_default="generating"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_shot_images_project_id", "shot_images", ["project_id"])
    op.create_index("ix_shot_images_shooting_list_id", "shot_images", ["shooting_list_id"])
    op.create_unique_constraint(
        "uq_shot_images_list_cut", "shot_images", ["shooting_list_id", "cut_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_shot_images_list_cut", "shot_images", type_="unique")
    op.drop_index("ix_shot_images_shooting_list_id", table_name="shot_images")
    op.drop_index("ix_shot_images_project_id", table_name="shot_images")
    op.drop_table("shot_images")
    shot_image_status.drop(op.get_bind(), checkfirst=True)
