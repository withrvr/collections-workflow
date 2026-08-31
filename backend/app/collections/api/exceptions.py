"""The exceptions report endpoint. Populated in Phase 4 (MASTER_PLAN.md)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import SessionDep
from app.collections.api.deps import get_run_or_404
from app.collections.api.schemas import ExceptionOut, ExceptionsOut
from app.collections.models import RunException, RunRuleExplanation

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

    explanations = {
        e.rule_code: e
        for e in session.exec(
            select(RunRuleExplanation).where(RunRuleExplanation.run_id == run_id)
        ).all()
    }

    data = []
    for row in rows:
        explanation = explanations.get(row.rule_code)
        data.append(
            ExceptionOut(
                id=row.id,
                rule_code=row.rule_code,
                category=row.category,
                message=row.message,
                severity=row.severity,
                invoice_id=row.invoice_id,
                payment_id=row.payment_id,
                customer_id=row.customer_id,
                detail_json=row.detail_json,
                cause=explanation.cause if explanation else None,
                impact=explanation.impact if explanation else None,
                suggested_fix=explanation.suggested_fix if explanation else None,
                owner=explanation.owner if explanation else None,
                auto_fixable=explanation.auto_fixable if explanation else False,
                explanation_source=explanation.source if explanation else None,
            )
        )
    return ExceptionsOut(run_id=run_id, data=data, count=len(data))
