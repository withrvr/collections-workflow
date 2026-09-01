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

from app.collections.calculate.outstanding import index_payments_by_invoice, valid_payments_total
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


# ---------------------------------------------------------------------------
# Cross-reference rules
# ---------------------------------------------------------------------------


def check_e002_unknown_customer_reference(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    """Checked against both invoices and payments -- either kind of record
    can carry a dangling Customer_ID. A payment that also references an
    unknown invoice (e.g. PAY-2025) fires this rule independently of E003:
    each broken reference is its own true, actionable fact."""
    known_customer_ids = {c.customer_id for c in dataset.customers}
    for invoice in dataset.invoices:
        if invoice.customer_id not in known_customer_ids:
            yield ExceptionRow(
                rule_code="E002",
                category="Unknown customer reference",
                message=(
                    f"Invoice {invoice.invoice_id} references Customer_ID "
                    f"'{invoice.customer_id}', which is not in the Customers sheet. "
                    "Excluded from the overdue report."
                ),
                severity="error",
                invoice_id=invoice.invoice_id,
                customer_id=invoice.customer_id,
            )
    for payment in dataset.payments:
        if payment.customer_id not in known_customer_ids:
            yield ExceptionRow(
                rule_code="E002",
                category="Unknown customer reference",
                message=(
                    f"Payment {payment.payment_id} references Customer_ID "
                    f"'{payment.customer_id}', which is not in the Customers sheet."
                ),
                severity="error",
                payment_id=payment.payment_id,
                invoice_id=payment.invoice_id,
                customer_id=payment.customer_id,
            )


def check_e003_unknown_invoice_reference(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    known_invoice_ids = {i.invoice_id for i in dataset.invoices}
    for payment in dataset.payments:
        if payment.invoice_id not in known_invoice_ids:
            yield ExceptionRow(
                rule_code="E003",
                category="Unknown invoice reference",
                message=(
                    f"Payment {payment.payment_id} references Invoice_ID "
                    f"'{payment.invoice_id}', which is not in the Invoices sheet. "
                    "The payment cannot be applied to anything."
                ),
                severity="error",
                payment_id=payment.payment_id,
                invoice_id=payment.invoice_id,
                customer_id=payment.customer_id,
            )


def check_e007_payment_invoice_customer_mismatch(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    invoices_by_id = {i.invoice_id: i for i in dataset.invoices}
    for payment in dataset.payments:
        invoice = invoices_by_id.get(payment.invoice_id)
        if invoice is None:
            continue  # unresolved reference is E003's concern, not this rule's
        if payment.customer_id != invoice.customer_id:
            yield ExceptionRow(
                rule_code="E007",
                category="Payment-to-invoice customer mismatch",
                message=(
                    f"Payment {payment.payment_id} is recorded against customer "
                    f"{payment.customer_id}, but the invoice it pays "
                    f"({invoice.invoice_id}) belongs to customer {invoice.customer_id}. "
                    f"Excluded from {invoice.customer_id}'s paid total rather than "
                    "reassigned, since reassignment would be a silent data correction."
                ),
                severity="error",
                payment_id=payment.payment_id,
                invoice_id=invoice.invoice_id,
                customer_id=payment.customer_id,
                detail={
                    "payment_customer_id": payment.customer_id,
                    "invoice_customer_id": invoice.customer_id,
                },
            )


def check_e010_payment_before_invoice_date(
    dataset: CanonicalDataset, report_date: date
) -> Iterator[ExceptionRow]:  # noqa: ARG001
    invoices_by_id = {i.invoice_id: i for i in dataset.invoices}
    for payment in dataset.payments:
        invoice = invoices_by_id.get(payment.invoice_id)
        if invoice is None:
            continue  # unresolved reference is E003's concern, not this rule's
        if payment.payment_date < invoice.invoice_date:
            yield ExceptionRow(
                rule_code="E010",
                category="Payment before invoice date",
                message=(
                    f"Payment {payment.payment_id} ({payment.payment_date}) is dated "
                    f"before its own invoice {invoice.invoice_id}'s invoice date "
                    f"({invoice.invoice_date}). Still counted in full toward "
                    "outstanding -- see README.md Assumptions."
                ),
                severity="warning",
                payment_id=payment.payment_id,
                invoice_id=invoice.invoice_id,
                customer_id=payment.customer_id,
                detail={"payment_date": payment.payment_date, "invoice_date": invoice.invoice_date},
            )


def check_e014_overpayment(dataset: CanonicalDataset, report_date: date) -> Iterator[ExceptionRow]:
    """Not on the assessment's required list -- added because the data called
    for it (see QA_PREP.md Q5). Reuses outstanding.py's own valid_payments_total
    so this rule and the real calculation can never disagree about what counts
    as a valid payment. Guards invoice_amount > 0 first, to avoid a spurious
    fire against an already-E004-flagged negative-amount invoice with zero
    payments against it. Evaluates all invoices regardless of status -- an
    overpayment against a Cancelled invoice is just as much an AR problem."""
    payments_by_invoice = index_payments_by_invoice(dataset.payments)
    for invoice in dataset.invoices:
        if invoice.invoice_amount <= Decimal("0"):
            continue
        paid = valid_payments_total(invoice, payments_by_invoice, report_date)
        if paid > invoice.invoice_amount:
            overpaid = paid - invoice.invoice_amount
            yield ExceptionRow(
                rule_code="E014",
                category="Overpayment",
                message=(
                    f"Invoice {invoice.invoice_id} has valid payments totalling "
                    f"{paid}, exceeding its amount of {invoice.invoice_amount} by "
                    f"{overpaid}. Outstanding is floored at zero rather than shown "
                    "as negative/credit."
                ),
                severity="warning",
                invoice_id=invoice.invoice_id,
                customer_id=invoice.customer_id,
                detail={
                    "invoice_amount": invoice.invoice_amount,
                    "valid_paid": paid,
                    "overpaid": overpaid,
                },
            )
