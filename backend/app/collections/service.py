"""The orchestrator: load -> validate -> calculate -> control -> summarise
-> persist, top to bottom.

A plain Python function calling each stage in a fixed order, deliberately
not an autonomous agent (see QA_PREP.md, question 16). Built in Phase 3
(MASTER_PLAN.md); `control` (the 5% gate) and `summarise` (the
deterministic Jinja narrative -- Phase 6 adds an LLM rung above it, this
one never fails) wired up in Phase 5. `map` (Phase 10, multi-workbook
column mapping) is named in `models.EventStage` but still not called.

Every stage writes a `run_events` row before and after doing its work
(see observability/events.py). Every exception that can reach this
function's `try` block is either already a `PipelineError` or gets
translated into one right here -- nothing below `execute_run` should ever
let a raw traceback become a run's `error_message` (MASTER_PLAN.md
section 7's error contract).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException
from sqlmodel import Session

from app.collections.ai.fallback import render_summary
from app.collections.calculate.ageing import ageing_bucket
from app.collections.calculate.overdue import compute_positions, overdue_only
from app.collections.calculate.regions import (
    build_customer_region_map,
    summarize_outstanding_by_region,
)
from app.collections.config import settings
from app.collections.contracts import CanonicalDataset, ExceptionRow
from app.collections.control.gate import evaluate_gate
from app.collections.errors import PipelineError
from app.collections.ingest.loader import load_workbook
from app.collections.ingest.resolver import ColumnResolutionError, SheetMissingError
from app.collections.models import (
    Run,
    RunException,
    RunInvoicePosition,
    get_datetime_utc,
)
from app.collections.observability import events
from app.collections.observability.events import to_json_detail
from app.collections.observability.logging import get_logger
from app.collections.validate.engine import run_all_rules

logger = get_logger(__name__)


def _load_dataset(path: Path) -> CanonicalDataset:
    try:
        return load_workbook(path)
    except SheetMissingError as exc:
        raise PipelineError(
            code="SHEET_MISSING",
            stage="load",
            user_message=str(exc),
            detail={"sheet": exc.sheet_name},
        ) from exc
    except ColumnResolutionError as exc:
        raise PipelineError(
            code="SHEET_COLUMN_MISSING",
            stage="load",
            user_message=str(exc),
            detail={"sheet": exc.sheet_name, "missing_headers": exc.missing_headers},
        ) from exc
    except (BadZipFile, InvalidFileException) as exc:
        raise PipelineError(
            code="FILE_CORRUPT",
            stage="load",
            user_message="The uploaded file could not be read as a valid Excel workbook.",
            detail={"error": str(exc)},
        ) from exc
    except ValueError as exc:
        raise PipelineError(
            code="ROW_DATA_INVALID",
            stage="load",
            user_message=f"The workbook contains a cell that could not be parsed: {exc}",
            detail={"error": str(exc)},
        ) from exc


def _persist_exceptions(
    session: Session, run_id: uuid.UUID, exception_rows: list[ExceptionRow]
) -> None:
    for row in exception_rows:
        session.add(
            RunException(
                run_id=run_id,
                rule_code=row.rule_code,
                category=row.category,
                message=row.message,
                severity=row.severity,
                invoice_id=row.invoice_id,
                payment_id=row.payment_id,
                customer_id=row.customer_id,
                detail_json=to_json_detail(row.detail),
            )
        )


def execute_run(session: Session, file_path: Path, source_filename: str) -> Run:
    """Run the full pipeline against one uploaded workbook and persist the
    result. Always returns a `Run` -- a bad input file produces a `FAILED`
    run with readable events, never a raised exception out of this
    function (that distinction is the whole point of the error contract:
    a 500 means *this code* broke, not the user's file)."""
    report_date = settings.REPORT_DATE
    run = Run(
        status="RUNNING", source_filename=source_filename, report_date=report_date
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    def emit(
        stage: str,
        level: str,
        code: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        events.emit(session, run.id, stage, level, code, message, detail)

    try:
        emit("load", "info", "LOAD_STARTED", f"Reading '{source_filename}'.")
        dataset = _load_dataset(file_path)
        emit(
            "load",
            "info",
            "LOAD_COMPLETED",
            f"Loaded {len(dataset.customers)} customer(s), {len(dataset.invoices)} invoice(s), "
            f"{len(dataset.payments)} payment(s).",
        )
        for warning in dataset.load_warnings:
            emit("load", "warning", "LOAD_ROW_SKIPPED", warning)

        emit(
            "validate",
            "info",
            "VALIDATE_STARTED",
            "Checking data quality and business rules.",
        )
        exception_rows = run_all_rules(dataset, report_date)
        _persist_exceptions(session, run.id, exception_rows)
        emit(
            "validate",
            "info",
            "VALIDATE_COMPLETED",
            f"Found {len(exception_rows)} exception(s) across 14 rule(s).",
        )

        emit(
            "calculate",
            "info",
            "CALCULATE_STARTED",
            "Computing outstanding and overdue positions.",
        )
        positions = compute_positions(dataset, report_date)
        customer_region = build_customer_region_map(
            dataset.customers, dataset.region_map
        )
        for position in positions:
            session.add(
                RunInvoicePosition(
                    run_id=run.id,
                    invoice_id=position.invoice.invoice_id,
                    customer_id=position.invoice.customer_id,
                    region=customer_region.get(position.invoice.customer_id),
                    due_date=position.invoice.due_date,
                    outstanding=position.outstanding,
                    is_overdue=position.is_overdue,
                    days_overdue=position.days_overdue,
                    ageing_bucket=ageing_bucket(position.days_overdue)
                    if position.is_overdue
                    else None,
                )
            )
        overdue = overdue_only(positions)
        total_outstanding = sum((p.outstanding for p in overdue), Decimal("0"))
        emit(
            "calculate",
            "info",
            "CALCULATE_COMPLETED",
            f"{len(overdue)} of {len(positions)} eligible invoice(s) are overdue, "
            f"Rs {total_outstanding:,.2f} outstanding.",
        )

        emit(
            "control",
            "info",
            "CONTROL_STARTED",
            "Checking the exception rate against the control threshold.",
        )
        gate = evaluate_gate(len(dataset.invoices), exception_rows)
        emit(
            "control",
            "info" if gate.status == "PASSED" else "warning",
            f"CONTROL_{gate.status}",
            f"Exception rate {gate.exception_row_rate:.1%} "
            f"({'within' if gate.status == 'PASSED' else 'exceeds'} the {gate.threshold:.0%} threshold) -- {gate.status}.",
        )

        by_region = summarize_outstanding_by_region(overdue, customer_region)
        heaviest_region = (
            max(by_region, key=lambda r: by_region[r]) if by_region else None
        )
        narrative = render_summary(
            source_filename=source_filename,
            report_date=str(report_date),
            invoice_count=len(dataset.invoices),
            overdue_count=len(overdue),
            total_outstanding=total_outstanding,
            heaviest_region=heaviest_region,
            gate=gate,
        )
        emit("summarise", "info", "SUMMARISE_COMPLETED", narrative)

        run.status = gate.status
        run.completed_at = get_datetime_utc()
        run.customer_count = len(dataset.customers)
        run.invoice_count = len(dataset.invoices)
        run.payment_count = len(dataset.payments)
        run.overdue_count = len(overdue)
        run.total_outstanding = total_outstanding
        run.exception_count = len(exception_rows)
        run.gate_threshold = gate.threshold
        run.exception_row_rate = gate.exception_row_rate
        run.distinct_invoices_affected = gate.distinct_invoices_affected
        run.distinct_invoice_rate = gate.distinct_invoice_rate
        run.narrative = narrative
        emit("persist", "info", "PERSIST_COMPLETED", "Run results saved.")

    except PipelineError as exc:
        # Deliberately not a rollback: run_events already flushed for
        # stages that genuinely completed before this one (e.g. a clean
        # LOAD_COMPLETED before a VALIDATE failure) are real progress the
        # user should still see on the run's timeline, not lost state.
        run.status = "FAILED"
        run.completed_at = get_datetime_utc()
        run.error_code = exc.code
        run.error_message = exc.user_message
        events.emit(
            session, run.id, exc.stage, "error", exc.code, exc.user_message, exc.detail
        )

    except Exception:
        logger.exception("collections_run_unexpected_error run_id=%s", run.id)
        run.status = "FAILED"
        run.completed_at = get_datetime_utc()
        run.error_code = "UNEXPECTED_ERROR"
        run.error_message = "An unexpected error occurred while processing this file."
        events.emit(
            session,
            run.id,
            "persist",
            "error",
            "UNEXPECTED_ERROR",
            run.error_message,
        )

    session.commit()
    session.refresh(run)
    return run
