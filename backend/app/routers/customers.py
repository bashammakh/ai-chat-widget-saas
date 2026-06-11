"""Customer + knowledge-base management API.

These endpoints are protected by admin HTTP-Basic auth (they are tenant
provisioning operations, not customer-facing).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, KnowledgeFile, Website
from app.schemas import (
    CustomerCreate,
    CustomerOut,
    CustomerSummary,
    UploadResult,
    WebsiteCreate,
    WebsiteOut,
)
from app.security import require_admin
from app.services import openai_service

router = APIRouter(prefix="/api/customers", tags=["customers"])

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB per file
ALLOWED_SUFFIXES = (".md", ".markdown")


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    customer = Customer(company_name=payload.company_name)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerSummary])
def list_customers(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return db.scalars(select(Customer).order_by(Customer.created_at.desc())).all()


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: str, db: Session = Depends(get_db), _: str = Depends(require_admin)
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(
    customer_id: str, db: Session = Depends(get_db), _: str = Depends(require_admin)
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.vector_store_id:
        openai_service.delete_vector_store(customer.vector_store_id)
    db.delete(customer)
    db.commit()
    return None


@router.post("/{customer_id}/upload", response_model=UploadResult)
async def upload_knowledge(
    customer_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Validate and read files before touching OpenAI.
    payloads: list[tuple[str, bytes]] = []
    for upload in files:
        name = upload.filename or "upload.md"
        if not name.lower().endswith(ALLOWED_SUFFIXES):
            raise HTTPException(
                status_code=400, detail=f"Only markdown files allowed: {name}"
            )
        content = await upload.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(status_code=400, detail=f"File too large: {name}")
        if not content.strip():
            raise HTTPException(status_code=400, detail=f"File is empty: {name}")
        payloads.append((name, content))

    # Reuse the existing vector store, or create one on first upload.
    if not customer.vector_store_id:
        customer.vector_store_id = openai_service.create_vector_store(
            name=f"kb-{customer.company_name}-{customer.id[:8]}"
        )
        db.add(customer)
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

    return UploadResult(
        vector_store_id=customer.vector_store_id,
        uploaded_files=[f for f, _ in uploaded],
    )


@router.delete("/{customer_id}/files/{file_id}", status_code=204)
def delete_knowledge_file(
    customer_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Delete one knowledge source from OpenAI and the database."""
    kf = db.get(KnowledgeFile, file_id)
    if kf is None or kf.customer_id != customer_id:
        raise HTTPException(status_code=404, detail="File not found")
    customer = db.get(Customer, customer_id)
    vs_id = customer.vector_store_id if customer else None
    openai_service.delete_file(vs_id, kf.openai_file_id)
    db.delete(kf)
    db.commit()
    return None


@router.post(
    "/{customer_id}/websites", response_model=WebsiteOut, status_code=201
)
def create_website(
    customer_id: str,
    payload: WebsiteCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Register a website/domain and generate its widget_id."""
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    website = Website(customer_id=customer.id, domain=payload.domain.strip())
    db.add(website)
    db.commit()
    db.refresh(website)
    return website
