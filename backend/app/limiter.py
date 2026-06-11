"""Shared SlowAPI limiter instance.

Kept in its own module so routers can import it without creating a circular
import with the FastAPI app in ``main.py``.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
)
