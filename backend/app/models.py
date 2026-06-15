"""SQLAlchemy ORM models for the multi-tenant chat platform."""
from __future__ import annotations

import datetime as dt
import secrets
import uuid

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _api_key() -> str:
    return "sk_live_" + secrets.token_urlsafe(32)


def _widget_id() -> str:
    return secrets.token_urlsafe(12)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, default=_api_key, nullable=False
    )
    vector_store_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    websites: Mapped[list["Website"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    files: Mapped[list["KnowledgeFile"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    widget_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_widget_id, nullable=False
    )

    # --- Widget appearance / behaviour (editable from the admin panel) ---
    widget_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    widget_primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    widget_greeting: Mapped[str | None] = mapped_column(Text, nullable=True)
    widget_logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    widget_lang: Mapped[str | None] = mapped_column(String(8), nullable=True)  # auto|ar|en
    not_found_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expert_button_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # When set, the expert button opens this URL (WhatsApp / email / contact
    # page). Takes priority over expert_selector (clicking a host-page element).
    expert_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    expert_selector: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="websites")


class KnowledgeFile(Base):
    """Tracks markdown files uploaded to OpenAI for a customer."""

    __tablename__ = "knowledge_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    openai_file_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # Friendly source name shown in citations instead of the raw filename
    # (editable from the admin panel).
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="files")


class AppSetting(Base):
    """Simple key/value store for runtime-editable settings (e.g. OpenAI key).

    Values here override the corresponding environment variables, so secrets can
    be rotated from the admin panel without a redeploy.
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False,
    )


class ChatMessage(Base):
    """Persisted conversation history, one row per user/assistant exchange."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    widget_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
