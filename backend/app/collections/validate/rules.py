"""Exception rules E001-E014, one function each. Never silently drops a row.

Every rule takes (dataset, report_date) and yields ExceptionRow -- a
uniform signature even for the rules that ignore report_date, so
validate/engine.py's registry never needs to special-case which rules
need the date. Full catalogue with rationale: docs/RULES.md.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterator
from datetime import date
from decimal import Decimal

from app.collections.contracts import CanonicalDataset, CanonicalInvoice, ExceptionRow

# 2-digit state code, 10-char PAN, entity code digit, literal Z, checksum char.
# Format-only -- no checksum validation. A deliberate, documented limitation
# (see README.md "weakest part" discussion), not an oversight.
GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z0-9]$")

# ---------------------------------------------------------------------------
# Customer-only rules
# ---------------------------------------------------------------------------


def check_e006_invalid_gstin_format(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    for customer in dataset.customers:
        if customer.gstin is not None and not GSTIN_PATTERN.match(customer.gstin):
            yield ExceptionRow(
                rule_code="E006",
                category="Invalid GSTIN format",
                message=(
                    f"Customer {customer.customer_id} has a GSTIN that does not match "
                    f"the expected 15-character format: '{customer.gstin}'."
                ),
                severity="warning",
                customer_id=customer.customer_id,
                detail={"gstin": customer.gstin},
            )


def check_e008_missing_gstin(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    for customer in dataset.customers:
        if customer.gstin is None:
            yield ExceptionRow(
                rule_code="E008",
                category="Missing GSTIN",
                message=f"Customer {customer.customer_id} has no GSTIN on file.",
                severity="warning",
                customer_id=customer.customer_id,
            )


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


def check_e004_non_positive_invoice_amount(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    for invoice in dataset.invoices:
        if invoice.invoice_amount <= Decimal("0"):
            yield ExceptionRow(
                rule_code="E004",
                category="Non-positive invoice amount",
                message=(
                    f"Invoice {invoice.invoice_id} has a non-positive amount "
                    f"({invoice.invoice_amount}). Excluded from the overdue report."
                ),
                severity="error",
                invoice_id=invoice.invoice_id,
                customer_id=invoice.customer_id,
                detail={"invoice_amount": invoice.invoice_amount},
            )


def check_e011_cancelled_invoice(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    for invoice in dataset.invoices:
        if invoice.status == "Cancelled":
            yield ExceptionRow(
                rule_code="E011",
                category="Cancelled invoice",
                message=(
                    f"Invoice {invoice.invoice_id} is Cancelled. Excluded from the "
                    "overdue report; shown here so nothing silently disappears."
                ),
                severity="warning",
                invoice_id=invoice.invoice_id,
                customer_id=invoice.customer_id,
            )


def check_e012_credit_note_invoice(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    for invoice in dataset.invoices:
        if invoice.status == "Credit Note":
            yield ExceptionRow(
                rule_code="E012",
                category="Credit Note invoice",
                message=(
                    f"Invoice {invoice.invoice_id} is a Credit Note. Excluded from "
                    "the overdue report; shown here so nothing silently disappears."
                ),
                severity="warning",
                invoice_id=invoice.invoice_id,
                customer_id=invoice.customer_id,
            )


def check_e013_duplicate_source_system_ref(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    groups: dict[str, list[CanonicalInvoice]] = defaultdict(list)
    for invoice in dataset.invoices:
        if invoice.source_system_ref is not None:
            groups[invoice.source_system_ref].append(invoice)
    for source_ref, invoices in groups.items():
        if len(invoices) <= 1:
            continue
        for invoice in invoices:
            siblings = [i.invoice_id for i in invoices if i.invoice_id != invoice.invoice_id]
            yield ExceptionRow(
                rule_code="E013",
                category="Duplicate source system reference",
                message=(
                    f"Invoice {invoice.invoice_id} shares Source_System_Ref "
                    f"'{source_ref}' with {', '.join(siblings)}. Needs investigation: "
                    "could be a duplicate entry or a legitimately split sales order."
                ),
                severity="warning",
                invoice_id=invoice.invoice_id,
                customer_id=invoice.customer_id,
                detail={"source_system_ref": source_ref, "duplicate_with": siblings},
            )


# ---------------------------------------------------------------------------
# Payment-only rules
# ---------------------------------------------------------------------------


def check_e005_non_positive_payment_amount(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    for payment in dataset.payments:
        if payment.payment_amount <= Decimal("0"):
            yield ExceptionRow(
                rule_code="E005",
                category="Non-positive payment amount",
                message=(
                    f"Payment {payment.payment_id} has a non-positive amount "
                    f"({payment.payment_amount}). Excluded from the valid-payments "
                    f"total for invoice {payment.invoice_id}."
                ),
                severity="error",
                invoice_id=payment.invoice_id,
                payment_id=payment.payment_id,
                customer_id=payment.customer_id,
                detail={"payment_amount": payment.payment_amount},
            )


def check_e009_payment_after_report_date(dataset: CanonicalDataset, report_date: date) -> Iterator[ExceptionRow]:
    for payment in dataset.payments:
        if payment.payment_date > report_date:
            yield ExceptionRow(
                rule_code="E009",
                category="Payment after report date",
                message=(
                    f"Payment {payment.payment_id} ({payment.payment_date}) is dated "
                    f"after the report date ({report_date}). It does not reduce "
                    f"invoice {payment.invoice_id}'s position as of this report."
                ),
                severity="warning",
                invoice_id=payment.invoice_id,
                payment_id=payment.payment_id,
                customer_id=payment.customer_id,
                detail={"payment_date": payment.payment_date, "report_date": report_date},
            )
