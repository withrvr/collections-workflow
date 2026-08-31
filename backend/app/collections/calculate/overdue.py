"""Overdue = Due Date strictly before the report date AND Outstanding > 0.

Approved invoices only; Cancelled and Credit Note are excluded here and
surfaced as exceptions instead (Phase 2). An invoice with an unknown
customer, a missing due date, or a non-positive amount is excluded from
this report entirely for the same reason -- it cannot be soundly
attributed to a Region/Customer or compared against a due date.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.collections.calculate.outstanding import compute_outstanding, index_payments_by_invoice
from app.collections.contracts import CanonicalDataset, CanonicalInvoice, CanonicalPayment

ELIGIBLE_STATUS = "Approved"


@dataclass(frozen=True, slots=True)
class InvoicePosition:
    invoice: CanonicalInvoice
    outstanding: Decimal
    is_overdue: bool
    days_overdue: int


def is_eligible(invoice: CanonicalInvoice, known_customer_ids: set[str]) -> bool:
    return (
        invoice.status == ELIGIBLE_STATUS
        and invoice.customer_id in known_customer_ids
        and invoice.due_date is not None
        and invoice.invoice_amount > Decimal("0")
    )


def compute_position(
    invoice: CanonicalInvoice,
    payments_by_invoice: dict[str, list[CanonicalPayment]],
    report_date: date,
) -> InvoicePosition:
    outstanding = compute_outstanding(invoice, payments_by_invoice, report_date)
    assert invoice.due_date is not None  # guaranteed by is_eligible before this is called
    is_overdue = invoice.due_date < report_date and outstanding > Decimal("0")
    days_overdue = (report_date - invoice.due_date).days if is_overdue else 0
    return InvoicePosition(invoice=invoice, outstanding=outstanding, is_overdue=is_overdue, days_overdue=days_overdue)


def compute_positions(dataset: CanonicalDataset, report_date: date) -> list[InvoicePosition]:
    """All eligible invoices, overdue and current alike.

    Returning current invoices too (not just overdue ones) lets boundary
    tests assert an invoice is present but not overdue, rather than merely
    absent -- an important distinction when due date equals the report
    date exactly.
    """
    known_customer_ids = {c.customer_id for c in dataset.customers}
    payments_by_invoice = index_payments_by_invoice(dataset.payments)
    return [
        compute_position(invoice, payments_by_invoice, report_date)
        for invoice in dataset.invoices
        if is_eligible(invoice, known_customer_ids)
    ]


def overdue_only(positions: Sequence[InvoicePosition]) -> list[InvoicePosition]:
    return [p for p in positions if p.is_overdue]
