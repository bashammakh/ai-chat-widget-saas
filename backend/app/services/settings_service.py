"""Runtime-editable settings backed by the app_settings table.

DB values override the corresponding environment variables, so the OpenAI key
and model can be rotated from the admin panel without a redeploy.
"""
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AppSetting

KEY_OPENAI_API_KEY = "openai_api_key"
KEY_OPENAI_MODEL = "openai_model"


def get_setting(db: Session, key: str) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row else None


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    db.commit()


def effective_openai_key(db: Session) -> str:
    """The OpenAI key to use: DB override if set, otherwise the env value."""
    return get_setting(db, KEY_OPENAI_API_KEY) or settings.openai_api_key


def effective_openai_model(db: Session) -> str:
    return get_setting(db, KEY_OPENAI_MODEL) or settings.openai_model


def mask_secret(value: str | None) -> str:
    """Render a key for display without exposing it (e.g. sk-…aB12)."""
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return "•" * len(value)
    return value[:3] + "…" + value[-4:]
