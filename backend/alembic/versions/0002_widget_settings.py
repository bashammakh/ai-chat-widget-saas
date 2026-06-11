"""widget appearance settings on websites

Revision ID: 0002_widget_settings
Revises: 0001_initial
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_widget_settings"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("websites", sa.Column("widget_title", sa.String(length=120), nullable=True))
    op.add_column("websites", sa.Column("widget_primary_color", sa.String(length=20), nullable=True))
    op.add_column("websites", sa.Column("widget_greeting", sa.Text(), nullable=True))
    op.add_column("websites", sa.Column("widget_logo_url", sa.String(length=512), nullable=True))
    op.add_column("websites", sa.Column("widget_lang", sa.String(length=8), nullable=True))
    op.add_column("websites", sa.Column("not_found_message", sa.Text(), nullable=True))
    op.add_column("websites", sa.Column("expert_button_text", sa.String(length=120), nullable=True))
    op.add_column("websites", sa.Column("expert_selector", sa.String(length=255), nullable=True))


def downgrade() -> None:
    for col in (
        "expert_selector",
        "expert_button_text",
        "not_found_message",
        "widget_lang",
        "widget_logo_url",
        "widget_greeting",
        "widget_primary_color",
        "widget_title",
    ):
        op.drop_column("websites", col)
