"""Public chat endpoint consumed by the embeddable widget.

NOTE: this module intentionally does NOT use ``from __future__ import
annotations``. The ``@limiter.limit`` decorator wraps the handler with
``functools.wraps``, which does not copy ``__globals__``; with stringized
annotations FastAPI would fail to resolve ``ChatRequest`` and misclassify the
request body as a query parameter. Keeping real annotation objects avoids that.
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import ChatMessage, Customer, KnowledgeFile, Website
from app.schemas import ChatRequest, ChatResponse
from app.security import origin_matches_domain
from app.services import openai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


def _load_history(db: Session, widget_id: str, session_id: str) -> list[dict[str, str]]:
    """Return recent turns for a session as Responses API message dicts."""
    turns = settings.conversation_memory_turns
    rows = db.scalars(
        select(ChatMessage)
        .where(
            ChatMessage.widget_id == widget_id,
            ChatMessage.session_id == session_id,
        )
        .order_by(ChatMessage.timestamp.desc())
        .limit(turns)
    ).all()
    rows.reverse()  # chronological order

    history: list[dict[str, str]] = []
    for row in rows:
        history.append({"role": "user", "content": row.user_message})
        history.append({"role": "assistant", "content": row.assistant_message})
    return history


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_chat)
def chat(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    origin: str | None = Header(default=None),
    referer: str | None = Header(default=None),
):
    website = db.scalar(
        select(Website).where(Website.widget_id == payload.widget_id)
    )
    if website is None:
        raise HTTPException(status_code=404, detail="Unknown widget_id")

    # Domain validation: the request must originate from the registered domain.
    source = origin or referer
    if not origin_matches_domain(source, website.domain):
        logger.warning(
            "Rejected chat for widget %s from origin %r (allowed %s)",
            payload.widget_id,
            source,
            website.domain,
        )
        raise HTTPException(status_code=403, detail="Origin not allowed for this widget")

    customer = db.get(Customer, website.customer_id)
    if customer is None or not customer.vector_store_id:
        raise HTTPException(
            status_code=409, detail="Knowledge base not configured for this widget"
        )

    history = _load_history(db, payload.widget_id, payload.session_id)

    try:
        answer, found, sources = openai_service.generate_answer(
            vector_store_id=customer.vector_store_id,
            message=payload.message,
            history=history,
        )
    except Exception:  # noqa: BLE001
        logger.exception("OpenAI chat generation failed")
        raise HTTPException(status_code=502, detail="Upstream AI service error")

    # Map cited OpenAI file ids to admin-defined display names (fall back to the
    # filename), then append a localized source line to the answer.
    if found and sources:
        file_ids = [s["file_id"] for s in sources if s.get("file_id")]
        name_by_id: dict[str, str] = {}
        if file_ids:
            rows = db.scalars(
                select(KnowledgeFile).where(
                    KnowledgeFile.openai_file_id.in_(file_ids)
                )
            ).all()
            name_by_id = {
                r.openai_file_id: (r.display_name or r.filename) for r in rows
            }
        names: list[str] = []
        for s in sources:
            label = name_by_id.get(s.get("file_id", ""), s.get("filename") or "")
            if label and label not in names:
                names.append(label)
        answer = openai_service.append_sources(answer, names)

    db.add(
        ChatMessage(
            widget_id=payload.widget_id,
            session_id=payload.session_id,
            user_message=payload.message,
            assistant_message=answer,
        )
    )
    db.commit()

    return ChatResponse(answer=answer, found=found)
