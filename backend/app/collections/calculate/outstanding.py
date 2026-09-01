"""Outstanding = Invoice Amount - valid payments on or before the report date. Tax is never added.

A payment counts toward "valid" only if it is a positive amount, dated on
or before the report date, and paid by the same customer the invoice
belongs to. A payment referencing an invoice ID that does not exist in the
Invoices sheet is never applied to anything, because lookups below are
keyed by real invoice IDs -- there is nothing to index it under.

Deliberately NOT excluded: a payment dated before its own invoice's
invoice date. The workbook lists "payment before invoice" only as a data
quality item for the exception report (Phase 2), not as a reason to
exclude the payment from this calculation -- see README.md Assumptions.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from app.collections.contracts import CanonicalInvoice, CanonicalPayment

ZERO = Decimal("0")


def index_payments_by_invoice(
    payments: Sequence[CanonicalPayment],
) -> dict[str, list[CanonicalPayment]]:
    by_invoice: dict[str, list[CanonicalPayment]] = defaultdict(list)
    for payment in payments:
        by_invoice[payment.invoice_id].append(payment)
    return dict(by_invoice)


def is_valid_payment(payment: CanonicalPayment, invoice: CanonicalInvoice, report_date: date) -> bool:
    return (
        payment.payment_amount > ZERO
        and payment.payment_date <= report_date
        and payment.customer_id == invoice.customer_id
    )


def valid_payments_total(
    invoice: CanonicalInvoice,
    payments_by_invoice: dict[str, list[CanonicalPayment]],
    report_date: date,
) -> Decimal:
    candidates = payments_by_invoice.get(invoice.invoice_id, [])
    return sum(
        (p.payment_amount for p in candidates if is_valid_payment(p, invoice, report_date)),
        start=ZERO,
    )


def compute_outstanding(
    invoice: CanonicalInvoice,
    payments_by_invoice: dict[str, list[CanonicalPayment]],
    report_date: date,
) -> Decimal:
    paid = valid_payments_total(invoice, payments_by_invoice, report_date)
    return max(ZERO, invoice.invoice_amount - paid)
