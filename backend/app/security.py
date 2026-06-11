"""Authentication and request-validation helpers."""
from __future__ import annotations

import secrets
from urllib.parse import urlparse

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Customer

# --- Admin panel HTTP Basic auth ---
_basic = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_basic)) -> str:
    user_ok = secrets.compare_digest(credentials.username, settings.admin_username)
    pass_ok = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# --- Customer API-key auth (for management API) ---
def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Customer:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    customer = db.scalar(select(Customer).where(Customer.api_key == x_api_key))
    if customer is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return customer


# --- Domain validation for the public chat endpoint ---
def _host_of(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if "://" not in value:
        value = "//" + value
    return (urlparse(value).hostname or "").lower() or None


def origin_matches_domain(origin_or_referer: str | None, allowed_domain: str) -> bool:
    """True when the request origin host matches the registered website domain.

    A registered domain ``example.com`` matches ``example.com`` and any
    subdomain (``www.example.com``, ``app.example.com``). ``localhost`` is
    always allowed to ease local development/testing.
    """
    host = _host_of(origin_or_referer)
    allowed = _host_of(allowed_domain)
    if not allowed:
        return False
    if host in (None, "localhost", "127.0.0.1"):
        # No Origin (server-side/curl) is rejected by the caller; localhost ok.
        return host in ("localhost", "127.0.0.1")
    return host == allowed or host.endswith("." + allowed)
