"""Exception rules E001-E014, one function each. Never silently drops a row.

Every rule takes (dataset, report_date) and yields ExceptionRow -- a
uniform signature even for the rules that ignore report_date, so
validate/engine.py's registry never needs to special-case which rules
need the date. Full catalogue with rationale: docs/RULES.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

from app.collections.contracts import CanonicalDataset, ExceptionRow

# ---------------------------------------------------------------------------
# Invoice-only rules
# ---------------------------------------------------------------------------


def check_e001_missing_due_date(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    for invoice in dataset.invoices:
        if invoice.due_date is None:
            yield ExceptionRow(
                rule_code="E001",
                category="Missing due date",
                message=(
                    f"Invoice {invoice.invoice_id} has no Due Date, so it cannot be "
                    "classified overdue or current. Excluded from the overdue report."
                ),
                severity="error",
                invoice_id=invoice.invoice_id,
                customer_id=invoice.customer_id,
            )
