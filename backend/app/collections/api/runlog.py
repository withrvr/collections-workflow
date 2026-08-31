"""GET /run-log/{id}/events: the user-visible run timeline. Populated in Phase 4 (MASTER_PLAN.md)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlmodel import col, select

from app.api.deps import SessionDep
from app.collections.api.deps import get_run_or_404
from app.collections.api.schemas import RunEventsOut
from app.collections.models import RunEvent

router = APIRouter(prefix="/run-log", tags=["collections"])


@router.get("/{run_id}/events", response_model=RunEventsOut)
def get_run_events(session: SessionDep, run_id: uuid.UUID) -> RunEventsOut:
    run = get_run_or_404(session, run_id)
    events = session.exec(
        select(RunEvent).where(RunEvent.run_id == run_id).order_by(col(RunEvent.ts))
    ).all()
    return RunEventsOut(run_id=run_id, status=run.status, data=list(events))  # type: ignore[arg-type]
