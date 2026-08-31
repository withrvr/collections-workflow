"""The exceptions report endpoint. Populated in Phase 4 (MASTER_PLAN.md)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import SessionDep
from app.collections.api.deps import get_run_or_404
from app.collections.api.schemas import ExceptionsOut
from app.collections.models import RunException

router = APIRouter(prefix="/exceptions", tags=["collections"])


@router.get("/", response_model=ExceptionsOut)
def get_exceptions(
    session: SessionDep,
    run_id: uuid.UUID,
    rule_code: str | None = None,
    severity: str | None = None,
) -> ExceptionsOut:
    get_run_or_404(session, run_id)
    statement = select(RunException).where(RunException.run_id == run_id)
    if rule_code:
        statement = statement.where(RunException.rule_code == rule_code)
    if severity:
        statement = statement.where(RunException.severity == severity)
    rows = session.exec(statement).all()
    return ExceptionsOut(run_id=run_id, data=list(rows), count=len(rows))  # type: ignore[arg-type]
