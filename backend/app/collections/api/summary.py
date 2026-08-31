"""The management summary endpoint, including the control-gate blocked payload.

Populated in Phase 4/5 (MASTER_PLAN.md). Phase 4 returns the numeric
summary and region breakdown; Phase 5 layers the 5% control gate and its
blocked payload on top of this same endpoint.
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
    exception_rate = (
        run.exception_count / run.invoice_count
        if run.exception_count is not None and run.invoice_count
        else None
    )
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
        exception_rate=exception_rate,
        by_region=region_breakdown(session, run_id),
    )
