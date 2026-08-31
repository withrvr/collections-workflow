"""The independently-derived recompute promised in README.md's Validation
performed section and test_reconcile.py's module docstring: now that
persistence exists (Phase 3), aggregate `RunInvoicePosition` rows straight
out of the database with SQL and check the result against the same
reference numbers the in-memory `calculate/` functions produce.

This is a genuinely different code path from `scripts/reference_summary.py`
-- a SQL `SUM`/`GROUP BY` over persisted rows, not a Python loop over
in-memory dataclasses -- so agreement between the two is real evidence,
not the same arithmetic checked twice.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, func, select

from app.collections import service
from app.collections.models import RunInvoicePosition

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "dataset_a_original.xlsx"
)


def test_sql_sum_of_overdue_outstanding_matches_reference_total(
    session: Session,
) -> None:
    run = service.execute_run(session, FIXTURE_PATH, "dataset_a_original.xlsx")

    total = session.exec(
        select(func.sum(RunInvoicePosition.outstanding)).where(
            RunInvoicePosition.run_id == run.id,
            RunInvoicePosition.is_overdue == True,  # noqa: E712 -- SQL comparison, not a Python bool check
        )
    ).one()

    assert total == Decimal("1202000.00")


def test_sql_count_of_overdue_rows_matches_reference_count(session: Session) -> None:
    run = service.execute_run(session, FIXTURE_PATH, "dataset_a_original.xlsx")

    count = session.exec(
        select(func.count()).where(
            RunInvoicePosition.run_id == run.id,
            RunInvoicePosition.is_overdue == True,  # noqa: E712
        )
    ).one()

    assert count == 15


def test_sql_region_breakdown_matches_west_heaviest(session: Session) -> None:
    run = service.execute_run(session, FIXTURE_PATH, "dataset_a_original.xlsx")

    rows = session.exec(
        select(RunInvoicePosition.region, func.sum(RunInvoicePosition.outstanding))
        .where(
            RunInvoicePosition.run_id == run.id, RunInvoicePosition.is_overdue == True
        )  # noqa: E712
        .group_by(RunInvoicePosition.region)
    ).all()
    by_region = dict(rows)

    assert by_region["West"] == Decimal("472000.00")
    assert max(by_region, key=lambda region: by_region[region]) == "West"
