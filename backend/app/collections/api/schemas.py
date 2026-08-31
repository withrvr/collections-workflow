"""Pydantic response models shared across the collections API routers.

Read-only API schemas, separate from `models.py`'s SQLModel tables --
these shape what a client sees, not what Postgres stores (e.g. `detail`
here is the already-JSON-safe dict `models.py` persists, not re-derived).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class RunOut(BaseModel):
    id: uuid.UUID
    status: str
    source_filename: str
    report_date: date
    created_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    customer_count: int | None
    invoice_count: int | None
    payment_count: int | None
    overdue_count: int | None
    total_outstanding: Decimal | None
    exception_count: int | None

    model_config = {"from_attributes": True}


class RunsOut(BaseModel):
    data: list[RunOut]
    count: int


class RunEventOut(BaseModel):
    id: uuid.UUID
    ts: datetime
    stage: str
    level: str
    code: str
    message: str
    detail_json: dict[str, Any] | None

    model_config = {"from_attributes": True}


class RunEventsOut(BaseModel):
    run_id: uuid.UUID
    status: str
    data: list[RunEventOut]


class InvoicePositionOut(BaseModel):
    invoice_id: str
    customer_id: str
    region: str | None
    due_date: date | None
    outstanding: Decimal
    is_overdue: bool
    days_overdue: int
    ageing_bucket: str | None

    model_config = {"from_attributes": True}


class OverdueOut(BaseModel):
    run_id: uuid.UUID
    data: list[InvoicePositionOut]
    count: int
    total_outstanding: Decimal


class ExceptionOut(BaseModel):
    id: uuid.UUID
    rule_code: str
    category: str
    message: str
    severity: str
    invoice_id: str | None
    payment_id: str | None
    customer_id: str | None
    detail_json: dict[str, Any] | None

    model_config = {"from_attributes": True}


class ExceptionsOut(BaseModel):
    run_id: uuid.UUID
    data: list[ExceptionOut]
    count: int


class RegionBreakdownOut(BaseModel):
    region: str
    outstanding: Decimal
    overdue_count: int


class RegionsOut(BaseModel):
    run_id: uuid.UUID
    data: list[RegionBreakdownOut]
    heaviest_region: str | None


class SummaryOut(BaseModel):
    run_id: uuid.UUID
    status: str
    report_date: date
    customer_count: int | None
    invoice_count: int | None
    payment_count: int | None
    overdue_count: int | None
    total_outstanding: Decimal | None
    exception_count: int | None
    exception_rate: float | None
    by_region: list[RegionBreakdownOut]
