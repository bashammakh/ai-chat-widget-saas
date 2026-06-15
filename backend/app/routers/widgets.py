"""Public widget configuration endpoint (read-only, no secrets).

The embeddable widget.js fetches this on init so appearance/behaviour can be
managed centrally from the admin panel without editing the embed snippet.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Website
from app.schemas import WidgetConfigOut

router = APIRouter(prefix="/api/widget", tags=["widget"])


@router.get("/{widget_id}/config", response_model=WidgetConfigOut)
def widget_config(widget_id: str, db: Session = Depends(get_db)):
    website = db.scalar(select(Website).where(Website.widget_id == widget_id))
    if website is None:
        raise HTTPException(status_code=404, detail="Unknown widget_id")
    return WidgetConfigOut(
        widget_id=website.widget_id,
        title=website.widget_title,
        primary=website.widget_primary_color,
        greeting=website.widget_greeting,
        logo_url=website.widget_logo_url,
        lang=website.widget_lang,
        not_found_message=website.not_found_message,
        expert_button_text=website.expert_button_text,
        expert_url=website.expert_url,
        expert_selector=website.expert_selector,
    )
