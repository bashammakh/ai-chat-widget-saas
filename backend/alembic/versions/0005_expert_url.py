"""expert button URL on websites

Revision ID: 0005_expert_url
Revises: 0004_app_settings
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_expert_url"
down_revision: Union[str, None] = "0004_app_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "websites", sa.Column("expert_url", sa.String(length=1024), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("websites", "expert_url")
