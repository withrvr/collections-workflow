"""service.execute_run: the run lifecycle, run_events, and the error
contract (MASTER_PLAN.md section 7 -- "a deliberately broken file
produces a FAILED run with readable events and no traceback").
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, select

from app.collections import service
from app.collections.models import Run, RunEvent, RunException, RunInvoicePosition
from app.collections.tests.ingest.workbook_builder import build_minimal_workbook

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "dataset_a_original.xlsx"
)
DATASET_B_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "dataset_b_clean.xlsx"
)

# From docs/RULES.md's Summary table: 17 exception rows fire across the
# 14 rules against dataset A.
DATASET_A_EXCEPTION_COUNT = 17


def test_dataset_b_passes_the_control_gate(session: Session) -> None:
    """MASTER_PLAN.md Phase 5 done-when: dataset A blocks (see
    test_successful_run_matches_reference_numbers), dataset B passes."""
    run = service.execute_run(session, DATASET_B_PATH, "dataset_b_clean.xlsx")
    assert run.status == "PASSED"
    assert run.exception_row_rate is not None
    assert run.exception_row_rate <= Decimal("0.05")
    assert run.narrative is not None
    assert "PASSED" in run.narrative
    assert run.summary_source in ("ollama", "cloud", "fallback")


def _events_for(session: Session, run_id: uuid.UUID) -> list[RunEvent]:
    # order_by(RunEvent.ts) is a known mypy/ty stub gap for sqlmodel Field(sa_type=...)
    # columns, not a real type error -- see models.py's own sa_type comments.
    return list(
        session.exec(
            select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.ts)  # type: ignore[arg-type]
        )
    )


def test_successful_run_matches_reference_numbers(session: Session) -> None:
    run = service.execute_run(session, FIXTURE_PATH, "dataset_a_original.xlsx")

    assert run.status == "BLOCKED"
    assert run.error_code is None
    assert run.error_message is None
    assert run.customer_count == 25
    assert run.invoice_count == 36
    assert run.payment_count == 29
    assert run.overdue_count == 15
    assert run.total_outstanding == Decimal("1202000.00")
    assert run.exception_count == DATASET_A_EXCEPTION_COUNT


def test_successful_run_persists_exceptions_and_positions(session: Session) -> None:
    run = service.execute_run(session, FIXTURE_PATH, "dataset_a_original.xlsx")

    exceptions = session.exec(
        select(RunException).where(RunException.run_id == run.id)
    ).all()
    assert len(exceptions) == DATASET_A_EXCEPTION_COUNT
    assert {e.rule_code for e in exceptions} == {f"E{n:03d}" for n in range(1, 15)}

    positions = session.exec(
        select(RunInvoicePosition).where(RunInvoicePosition.run_id == run.id)
    ).all()
    overdue_positions = [p for p in positions if p.is_overdue]
    assert len(overdue_positions) == 15
    assert sum((p.outstanding for p in overdue_positions), Decimal("0")) == Decimal(
        "1202000.00"
    )


def test_successful_run_emits_events_for_every_stage_in_order(session: Session) -> None:
    run = service.execute_run(session, FIXTURE_PATH, "dataset_a_original.xlsx")

    stages = [e.stage for e in _events_for(session, run.id)]
    assert stages == [
        "load",
        "load",
        "validate",
        "validate",
        "validate",
        "calculate",
        "calculate",
        "control",
        "control",
        "summarise",
        "persist",
    ]
    # dataset A blocks (see test_successful_run_matches_reference_numbers),
    # so its control event is a warning, not an error -- the run itself
    # still completes cleanly, it just doesn't pass the gate.
    levels = {e.stage: e.level for e in _events_for(session, run.id)}
    assert levels["control"] == "warning"
    assert all(level == "info" for stage, level in levels.items() if stage != "control")


def test_missing_sheet_produces_failed_run_with_readable_event(
    session: Session, tmp_path: Path
) -> None:
    broken_path = tmp_path / "missing_sheet.xlsx"
    build_minimal_workbook(broken_path, omit_sheets={"Payments"})

    run = service.execute_run(session, broken_path, "missing_sheet.xlsx")

    assert run.status == "FAILED"
    assert run.error_code == "SHEET_MISSING"
    assert run.error_message is not None
    assert "Payments" in run.error_message
    assert "Traceback" not in run.error_message
    assert "Error" not in run.error_message  # e.g. no leaked "KeyError"

    events = _events_for(session, run.id)
    assert events[-1].level == "error"
    assert events[-1].code == "SHEET_MISSING"
    assert events[-1].stage == "load"


def test_missing_column_produces_failed_run_with_readable_event(
    session: Session, tmp_path: Path
) -> None:
    broken_path = tmp_path / "missing_column.xlsx"
    build_minimal_workbook(broken_path, omit_headers={"Invoices": {"Due_Date"}})

    run = service.execute_run(session, broken_path, "missing_column.xlsx")

    assert run.status == "FAILED"
    assert run.error_code == "SHEET_COLUMN_MISSING"
    assert run.error_message is not None
    assert "Due_Date" in run.error_message
    assert "Invoices" in run.error_message


def test_corrupt_file_produces_failed_run_with_readable_event(
    session: Session, tmp_path: Path
) -> None:
    broken_path = tmp_path / "corrupt.xlsx"
    broken_path.write_bytes(b"this is not a zip file, let alone an xlsx workbook")

    run = service.execute_run(session, broken_path, "corrupt.xlsx")

    assert run.status == "FAILED"
    assert run.error_code == "FILE_CORRUPT"
    assert run.error_message is not None
    assert "valid Excel workbook" in run.error_message
    assert "Traceback" not in run.error_message


def test_invalid_cell_data_produces_failed_run_with_readable_event(
    session: Session, tmp_path: Path
) -> None:
    broken_path = tmp_path / "bad_cell.xlsx"
    # Row 2, column 5 in Invoices is Invoice_Amount_INR (see INVOICE_FIELDS order).
    build_minimal_workbook(
        broken_path, cell_overrides={"Invoices": {(2, 5): "not-a-number"}}
    )

    run = service.execute_run(session, broken_path, "bad_cell.xlsx")

    assert run.status == "FAILED"
    assert run.error_code == "ROW_DATA_INVALID"
    assert run.error_message is not None
    assert "not-a-number" in run.error_message


def test_failed_run_leaves_no_orphaned_run_row(
    session: Session, tmp_path: Path
) -> None:
    """Every run, success or failure, is a real, queryable Run row -- never
    a raised exception the caller has to catch (MASTER_PLAN.md section 7:
    "POST /run never returns 500 for a bad input file")."""
    broken_path = tmp_path / "missing_sheet.xlsx"
    build_minimal_workbook(broken_path, omit_sheets={"Customers"})

    run = service.execute_run(session, broken_path, "missing_sheet.xlsx")

    reloaded = session.get(Run, run.id)
    assert reloaded is not None
    assert reloaded.status == "FAILED"
