"""Shared dependency: fetch a Run by id or 404. Used by every report
endpoint (overdue/exceptions/regions/summary/run-log) that takes a
run_id query/path param."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import Session

from app.collections.models import Run


def get_run_or_404(session: Session, run_id: uuid.UUID) -> Run:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run
