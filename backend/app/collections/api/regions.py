"""The region breakdown endpoint. Populated in Phase 4 (MASTER_PLAN.md)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter
from sqlmodel import func, select

from app.api.deps import SessionDep
from app.collections.api.deps import get_run_or_404
from app.collections.api.schemas import RegionBreakdownOut, RegionsOut
from app.collections.models import RunInvoicePosition

router = APIRouter(prefix="/regions", tags=["collections"])

UNKNOWN_REGION = "Unknown"


def region_breakdown(
    session: SessionDep, run_id: uuid.UUID
) -> list[RegionBreakdownOut]:
    """Shared by GET /regions and GET /summary's by_region field."""
    rows = session.exec(
        select(
            func.coalesce(RunInvoicePosition.region, UNKNOWN_REGION),
            func.sum(RunInvoicePosition.outstanding),
            func.count(),
        )
        .where(RunInvoicePosition.run_id == run_id, RunInvoicePosition.is_overdue)
        .group_by(RunInvoicePosition.region)
    ).all()
    data = [
        RegionBreakdownOut(
            region=region, outstanding=outstanding or Decimal("0"), overdue_count=count
        )
        for region, outstanding, count in rows
    ]
    data.sort(key=lambda r: r.outstanding, reverse=True)
    return data


@router.get("/", response_model=RegionsOut)
def get_regions(session: SessionDep, run_id: uuid.UUID) -> RegionsOut:
    get_run_or_404(session, run_id)
    data = region_breakdown(session, run_id)
    heaviest = data[0].region if data else None
    return RegionsOut(run_id=run_id, data=data, heaviest_region=heaviest)
