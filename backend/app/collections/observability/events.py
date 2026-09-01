"""Writes the run_events table: the user-visible run timeline, plain English, stable codes.

Built in Phase 3 (MASTER_PLAN.md). This is the "for the user" channel from
section 7's three-channel table -- `observability/logging.py`'s structlog
output is "for you, debugging" and stays a separate concern.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlmodel import Session

from app.collections.models import RunEvent, get_datetime_utc


def to_json_detail(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    """Make an ExceptionRow/PipelineError detail dict JSON-column safe.

    `Decimal` -> str (never float, which would silently lose precision)
    and `date` -> ISO string; everything else passes through unchanged.
    Only ever touches values coming off a domain object already computed
    in Decimal -- never a source of new rounding.
    """
    if detail is None:
        return None

    def convert(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, list):
            return [convert(item) for item in value]
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        return value

    return {key: convert(value) for key, value in detail.items()}


def emit(
    session: Session,
    run_id: uuid.UUID,
    stage: str,
    level: str,
    code: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> RunEvent:
    """Record one run_events row. `stage`/`level` are `models.EventStage`/
    `EventLevel` values by convention (kept as plain `str` here, not the
    Literal alias, since `PipelineError.stage` -- a value this also
    receives -- is itself just `str`; the column-level Literal narrowing
    lives in `models.py`, not this boundary). Flushes (not commits) so the
    caller controls the transaction boundary and can still roll everything
    back together on an unexpected error."""
    event = RunEvent(
        run_id=run_id,
        ts=get_datetime_utc(),
        stage=stage,
        level=level,
        code=code,
        message=message,
        detail_json=to_json_detail(detail),
    )
    session.add(event)
    session.flush()
    return event
