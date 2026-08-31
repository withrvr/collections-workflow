"""The management summary endpoint, including the control-gate blocked payload.

Populated in Phase 4/5 (MASTER_PLAN.md). Phase 5 adds the 5% control
gate's fields and the deterministic narrative on top of Phase 4's
numeric summary and region breakdown -- see api/schemas.py's
`SummaryOut` docstring for what the "blocked payload" actually is.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.collections.api.deps import get_run_or_404
from app.collections.api.regions import region_breakdown
from app.collections.api.schemas import SummaryOut

router = APIRouter(prefix="/summary", tags=["collections"])


@router.get("/", response_model=SummaryOut)
def get_summary(session: SessionDep, run_id: uuid.UUID) -> SummaryOut:
    run = get_run_or_404(session, run_id)
    return SummaryOut(
        run_id=run_id,
        status=run.status,
        report_date=run.report_date,
        customer_count=run.customer_count,
        invoice_count=run.invoice_count,
        payment_count=run.payment_count,
        overdue_count=run.overdue_count,
        total_outstanding=run.total_outstanding,
        exception_count=run.exception_count,
        gate_threshold=run.gate_threshold,
        exception_row_rate=run.exception_row_rate,
        distinct_invoices_affected=run.distinct_invoices_affected,
        distinct_invoice_rate=run.distinct_invoice_rate,
        narrative=run.narrative,
        by_region=region_breakdown(session, run_id),
    )
