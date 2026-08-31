"""The overdue report endpoint. Populated in Phase 4 (MASTER_PLAN.md)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import SessionDep
from app.collections.api.deps import get_run_or_404
from app.collections.api.schemas import OverdueOut
from app.collections.models import RunInvoicePosition

router = APIRouter(prefix="/overdue", tags=["collections"])


@router.get("/", response_model=OverdueOut)
def get_overdue(session: SessionDep, run_id: uuid.UUID) -> OverdueOut:
    get_run_or_404(session, run_id)
    positions = session.exec(
        select(RunInvoicePosition).where(
            RunInvoicePosition.run_id == run_id,
            RunInvoicePosition.is_overdue == True,  # noqa: E712
        )
    ).all()
    total = sum((p.outstanding for p in positions), Decimal("0"))
    return OverdueOut(
        run_id=run_id,
        data=list(positions),  # type: ignore[arg-type]
        count=len(positions),
        total_outstanding=total,
    )
