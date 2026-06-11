"""Server-rendered admin dashboard (Jinja2 templates + HTTP Basic auth)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi import File as FormFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ChatMessage, Customer, KnowledgeFile, Website
from app.routers.customers import (
    ALLOWED_SUFFIXES,
    MAX_FILE_BYTES,
)
from app.security import require_admin
from app.services import openai_service

router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _base_url(request: Request) -> str:
    """Public base URL for embed snippets (configured, or the request host)."""
    return settings.public_base_url.rstrip("/") or str(request.base_url).rstrip("/")


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)
):
    customers = db.scalars(
        select(Customer).order_by(Customer.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "customers": customers}
    )


@router.post("/customers")
def admin_create_customer(
    company_name: str = Form(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    db.add(Customer(company_name=company_name.strip()))
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/customers/{customer_id}", response_class=HTMLResponse)
def customer_detail(
    customer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    files = db.scalars(
        select(KnowledgeFile)
        .where(KnowledgeFile.customer_id == customer_id)
        .order_by(KnowledgeFile.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        "customer.html",
        {
            "request": request,
            "customer": customer,
            "files": files,
            "base_url": _base_url(request),
        },
    )


@router.post("/customers/{customer_id}/upload")
async def admin_upload(
    customer_id: str,
    files: list[UploadFile] = FormFile(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    payloads: list[tuple[str, bytes]] = []
    for upload in files:
        name = upload.filename or ""
        if not name.lower().endswith(ALLOWED_SUFFIXES):
            continue
        content = await upload.read()
        if content.strip() and len(content) <= MAX_FILE_BYTES:
            payloads.append((name, content))

    if payloads:
        if not customer.vector_store_id:
            customer.vector_store_id = openai_service.create_vector_store(
                name=f"kb-{customer.company_name}-{customer.id[:8]}"
            )
            db.commit()
        uploaded = openai_service.upload_markdown_files(
            customer.vector_store_id, payloads
        )
        for filename, openai_file_id in uploaded:
            db.add(
                KnowledgeFile(
                    customer_id=customer.id,
                    filename=filename,
                    openai_file_id=openai_file_id,
                )
            )
        db.commit()

    return RedirectResponse(url=f"/admin/customers/{customer_id}", status_code=303)


@router.post("/files/{file_id}/delete")
def admin_delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    kf = db.get(KnowledgeFile, file_id)
    if kf is None:
        raise HTTPException(status_code=404, detail="File not found")
    customer = db.get(Customer, kf.customer_id)
    vs_id = customer.vector_store_id if customer else None
    openai_service.delete_file(vs_id, kf.openai_file_id)
    customer_id = kf.customer_id
    db.delete(kf)
    db.commit()
    return RedirectResponse(url=f"/admin/customers/{customer_id}", status_code=303)


@router.post("/files/{file_id}/name")
def admin_set_file_name(
    file_id: str,
    display_name: str = Form(""),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    kf = db.get(KnowledgeFile, file_id)
    if kf is None:
        raise HTTPException(status_code=404, detail="File not found")
    name = display_name.strip()
    kf.display_name = name or None
    db.commit()
    return RedirectResponse(
        url=f"/admin/customers/{kf.customer_id}", status_code=303
    )


@router.post("/customers/{customer_id}/websites")
def admin_create_website(
    customer_id: str,
    domain: str = Form(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.add(Website(customer_id=customer_id, domain=domain.strip()))
    db.commit()
    return RedirectResponse(url=f"/admin/customers/{customer_id}", status_code=303)


def _clean(value: str | None) -> str | None:
    """Trim a form field; treat empty strings as NULL (fall back to defaults)."""
    if value is None:
        return None
    value = value.strip()
    return value or None


@router.post("/websites/{website_id}/settings")
def admin_update_widget_settings(
    website_id: str,
    widget_title: str = Form(""),
    widget_primary_color: str = Form(""),
    widget_greeting: str = Form(""),
    widget_logo_url: str = Form(""),
    widget_lang: str = Form("auto"),
    not_found_message: str = Form(""),
    expert_button_text: str = Form(""),
    expert_selector: str = Form(""),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    website = db.get(Website, website_id)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")

    website.widget_title = _clean(widget_title)
    website.widget_primary_color = _clean(widget_primary_color)
    website.widget_greeting = _clean(widget_greeting)
    website.widget_logo_url = _clean(widget_logo_url)
    website.widget_lang = _clean(widget_lang)
    website.not_found_message = _clean(not_found_message)
    website.expert_button_text = _clean(expert_button_text)
    website.expert_selector = _clean(expert_selector)
    db.commit()

    return RedirectResponse(
        url=f"/admin/customers/{website.customer_id}", status_code=303
    )


@router.get("/logs", response_class=HTMLResponse)
def chat_logs(
    request: Request,
    widget_id: str | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    stmt = select(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(200)
    if widget_id:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.widget_id == widget_id)
            .order_by(ChatMessage.timestamp.desc())
            .limit(200)
        )
    logs = db.scalars(stmt).all()
    return templates.TemplateResponse(
        "logs.html", {"request": request, "logs": logs, "widget_id": widget_id or ""}
    )
