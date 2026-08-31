"""POST /runs to upload a workbook and start a run, GET /runs to list them,
GET /runs/{id} for one. Populated in Phase 4 (MASTER_PLAN.md)."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile
from sqlmodel import col, func, select

from app.api.deps import SessionDep
from app.collections import service
from app.collections.api.deps import get_run_or_404
from app.collections.api.schemas import RunOut, RunsOut
from app.collections.models import Run

router = APIRouter(prefix="/runs", tags=["collections"])


@router.post("/", response_model=RunOut)
def create_run(session: SessionDep, file: UploadFile) -> Run:
    """Upload a workbook and run the pipeline against it synchronously.

    Always returns 200 with a Run -- a bad input file produces a FAILED
    run in the response body, never a 500 (MASTER_PLAN.md section 7).
    """
    suffix = Path(file.filename or "upload.xlsx").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(file.file.read())
        tmp.flush()
        return service.execute_run(
            session, Path(tmp.name), file.filename or "upload.xlsx"
        )


@router.get("/", response_model=RunsOut)
def list_runs(session: SessionDep, skip: int = 0, limit: int = 100) -> RunsOut:
    count = session.exec(select(func.count()).select_from(Run)).one()
    runs = session.exec(
        select(Run).order_by(col(Run.created_at).desc()).offset(skip).limit(limit)
    ).all()
    return RunsOut(data=list(runs), count=count)  # type: ignore[arg-type]


@router.get("/{run_id}", response_model=RunOut)
def get_run(session: SessionDep, run_id: uuid.UUID) -> Run:
    return get_run_or_404(session, run_id)
