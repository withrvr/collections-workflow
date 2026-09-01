"""The 5% exception-rate control gate. Never tuned to pass; reports both denominators.

Built in Phase 5 (MASTER_PLAN.md). QA_PREP.md Q8: the brief's wording
("exception records over invoice records") is ambiguous between an
exception-*row* rate and a distinct-*invoices-affected* rate, since one
invoice can carry more than one exception and some exceptions (e.g.
E002 on a payment, E005) never touch an invoice_id at all. This module
reports both, and the row rate -- the more literal reading, and the one
that does not silently undercount a badly-behaved invoice with three
exceptions as "one problem" -- drives the gate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.collections.contracts import ExceptionRow

THRESHOLD = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class GateResult:
    status: str  # "PASSED" or "BLOCKED"
    threshold: Decimal
    exception_count: int
    invoice_count: int
    exception_row_rate: Decimal
    distinct_invoices_affected: int
    distinct_invoice_rate: Decimal


def evaluate_gate(
    invoice_count: int, exception_rows: Sequence[ExceptionRow]
) -> GateResult:
    exception_count = len(exception_rows)
    distinct_invoices = {
        row.invoice_id for row in exception_rows if row.invoice_id is not None
    }

    if invoice_count == 0:
        exception_row_rate = Decimal("0")
        distinct_invoice_rate = Decimal("0")
    else:
        exception_row_rate = Decimal(exception_count) / Decimal(invoice_count)
        distinct_invoice_rate = Decimal(len(distinct_invoices)) / Decimal(invoice_count)

    status = "BLOCKED" if exception_row_rate > THRESHOLD else "PASSED"

    return GateResult(
        status=status,
        threshold=THRESHOLD,
        exception_count=exception_count,
        invoice_count=invoice_count,
        exception_row_rate=exception_row_rate,
        distinct_invoices_affected=len(distinct_invoices),
        distinct_invoice_rate=distinct_invoice_rate,
    )
