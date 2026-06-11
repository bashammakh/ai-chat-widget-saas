"""Pydantic request/response schemas."""
from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Customers ---
class CustomerCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)


class WebsiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain: str
    widget_id: str
    created_at: dt.datetime


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    api_key: str
    vector_store_id: Optional[str]
    created_at: dt.datetime
    websites: List[WebsiteOut] = []


class CustomerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    vector_store_id: Optional[str]
    created_at: dt.datetime


# --- Websites ---
class WebsiteCreate(BaseModel):
    domain: str = Field(..., min_length=1, max_length=255)


# --- Public widget config (consumed by widget.js, no secrets) ---
class WidgetConfigOut(BaseModel):
    widget_id: str
    title: Optional[str] = None
    primary: Optional[str] = None
    greeting: Optional[str] = None
    logo_url: Optional[str] = None
    lang: Optional[str] = None
    not_found_message: Optional[str] = None
    expert_button_text: Optional[str] = None
    expert_selector: Optional[str] = None


# --- Upload ---
class UploadResult(BaseModel):
    vector_store_id: str
    uploaded_files: List[str]


# --- Chat ---
class ChatRequest(BaseModel):
    widget_id: str = Field(..., min_length=1, max_length=64)
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    # False when the answer was not found in the knowledge base. The widget
    # uses this to show a custom "no answer" message + an expert button.
    found: bool = True


class ChatLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    widget_id: str
    session_id: str
    user_message: str
    assistant_message: str
    timestamp: dt.datetime
