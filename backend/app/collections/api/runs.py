"""POST /runs to upload a workbook and start a run, GET /runs to list them,
GET /runs/{id} for one. Populated in Phase 4 (MASTER_PLAN.md)."""

from __future__ import annotations

import uuid
from datetime import date as date_type

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from sqlmodel import col, func, select

from app.api.deps import SessionDep
from app.collections import service
from app.collections.api.deps import get_run_or_404
from app.collections.api.schemas import RunOut, RunsOut
from app.collections.models import Run
from app.collections.uploads import save_upload
from app.core.config import settings as core_settings
from app.utils import send_email

router = APIRouter(prefix="/runs", tags=["collections"])


@router.post("/", response_model=RunOut)
def create_run(
    session: SessionDep,
    file: UploadFile,
    report_date: str | None = Form(
        None,
        description="ISO date (YYYY-MM-DD) to anchor overdue/ageing "
        "calculations to. Defaults to the workbook's own configured "
        "report date (settings.REPORT_DATE) if omitted.",
    ),
) -> Run:
    """Upload a workbook and run the pipeline against it synchronously.

    Always returns 200 with a Run -- a bad input file produces a FAILED
    run in the response body, never a 500 (MASTER_PLAN.md section 7).
    """
    parsed_date: date_type | None = None
    if report_date:
        try:
            parsed_date = date_type.fromisoformat(report_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"report_date must be YYYY-MM-DD, got {report_date!r}",
            ) from exc

    stored_path = save_upload(file.filename or "upload.xlsx", file.file.read())
    return service.execute_run(
        session,
        stored_path,
        file.filename or "upload.xlsx",
        report_date=parsed_date,
        stored_file_path=str(stored_path),
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


@router.get("/{run_id}/download")
def download_run_file(session: SessionDep, run_id: uuid.UUID) -> FileResponse:
    run = get_run_or_404(session, run_id)
    if not run.stored_file_path:
        raise HTTPException(status_code=404, detail="No stored file for this run.")
    return FileResponse(
        run.stored_file_path,
        filename=run.source_filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class SendEmailRequest(BaseModel):
    to: EmailStr


class SendEmailResponse(BaseModel):
    sent: bool
    message: str


@router.post("/{run_id}/send-email", response_model=SendEmailResponse)
def send_run_email(
    session: SessionDep, run_id: uuid.UUID, body: SendEmailRequest
) -> SendEmailResponse:
    """Emails this run's summary -- status, key numbers, and the AI
    narrative -- to the given address via the same SMTP config the
    template already uses for password-reset emails (Mailpit in dev,
    http://localhost:8025). Not wired to any auto-send trigger: a human
    clicks "send" for a specific run, on purpose, every time."""
    if not core_settings.emails_enabled:
        raise HTTPException(
            status_code=503,
            detail="Email is not configured (SMTP_HOST/EMAILS_FROM_EMAIL unset).",
        )
    run = get_run_or_404(session, run_id)
    if run.status not in ("PASSED", "BLOCKED"):
        raise HTTPException(
            status_code=409,
            detail=f"Run status is {run.status}; nothing to summarize yet.",
        )

    status_color = "#16a34a" if run.status == "PASSED" else "#f59e0b"
    html = f"""
    <div style="font-family: sans-serif; max-width: 640px; margin: 0 auto;">
      <h2>Collections run: {run.source_filename}</h2>
      <p>
        <span style="background:{status_color}; color:white; padding:2px 10px;
                     border-radius:12px; font-weight:bold;">{run.status}</span>
        &nbsp; Report date {run.report_date}
      </p>
      <table style="border-collapse: collapse; margin: 16px 0;">
        <tr><td style="padding:4px 12px 4px 0; color:#666;">Invoices</td><td>{run.invoice_count}</td></tr>
        <tr><td style="padding:4px 12px 4px 0; color:#666;">Overdue</td><td>{run.overdue_count}</td></tr>
        <tr><td style="padding:4px 12px 4px 0; color:#666;">Outstanding</td><td>Rs {run.total_outstanding:,.2f}</td></tr>
        <tr><td style="padding:4px 12px 4px 0; color:#666;">Exceptions</td><td>{run.exception_count}</td></tr>
      </table>
      <p style="line-height:1.6;">{run.narrative}</p>
      <p style="color:#999; font-size:12px;">Sent from Collections Workflow -- run id {run.id}</p>
    </div>
    """
    send_email(
        email_to=body.to,
        subject=f"Collections run summary: {run.source_filename} ({run.status})",
        html_content=html,
    )
    return SendEmailResponse(sent=True, message=f"Sent to {body.to}.")
