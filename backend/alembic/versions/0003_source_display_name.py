"""display name for knowledge sources

Revision ID: 0003_source_display_name
Revises: 0002_widget_settings
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_source_display_name"
down_revision: Union[str, None] = "0002_widget_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_files",
        sa.Column("display_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_files", "display_name")
