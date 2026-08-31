"""Reconciliation tests: proves the calculate/ + validate/ layers together
account for every invoice and payment rupee, operationalizing
MASTER_PLAN.md section 10's "invoices = outstanding + valid payments +
excluded amounts, must tie" as checkable properties.

These are internal-consistency checks -- definitionally true given
compute_outstanding's own max(0, ...) floor -- not the independently
derived recompute promised in MASTER_PLAN.md section 10 (that's Phase
3+'s test_sql_crosscheck.py, once persistence exists to recompute from).

Note on the invoice-amount identity: an earlier design draft assumed
"overpaid" (paid exceeding invoice_amount) is nonzero only for the E014
case, INV-1007. That's false: INV-1028's negative invoice_amount with
zero payments against it also produces a nonzero overpaid term under the
same max(0, paid - amount) formula (0 - (-45000) = 45000), since
compute_outstanding floors ANY negative (amount - paid) at zero, not just
genuine overpayments. The identity below is written to hold regardless --
verified directly against dataset A rather than assumed.
"""

from decimal import Decimal

from app.collections.calculate.outstanding import (
    compute_outstanding,
    index_payments_by_invoice,
    is_valid_payment,
    valid_payments_total,
)
from app.collections.calculate.overdue import is_eligible
from app.collections.config import settings
from app.collections.contracts import CanonicalDataset
from app.collections.validate.engine import exceptions_by_rule

ZERO = Decimal("0")

EXCLUDED_INVOICE_IDS = {"INV-1026", "INV-1027", "INV-1028", "INV-1029", "INV-1030"}
UNAPPLIED_PAYMENT_IDS = {"PAY-2018", "PAY-2020", "PAY-2025", "PAY-2026", "PAY-2029"}

# Rule codes that can leave a payment unapplied (excluded from every
# invoice's valid-payments total): unknown customer/invoice reference,
# non-positive amount, customer mismatch, after the report date.
UNAPPLIED_PAYMENT_RULE_CODES = {"E002", "E003", "E005", "E007", "E009"}


def test_invoice_amount_identity_reconciles(dataset: CanonicalDataset) -> None:
    """For every invoice, outstanding + valid_paid == invoice_amount +
    overpaid (compute_outstanding's floor and the overpaid excess are
    exact mirror images of the same amount-minus-paid split: neither
    term is ever negative, and exactly one is nonzero for any given
    invoice). Summed across the full 36-invoice portfolio, no rupee is
    created or destroyed."""
    report_date = settings.REPORT_DATE
    payments_by_invoice = index_payments_by_invoice(dataset.payments)

    total_amount = ZERO
    total_overpaid = ZERO
    total_outstanding = ZERO
    total_paid = ZERO
    for invoice in dataset.invoices:
        paid = valid_payments_total(invoice, payments_by_invoice, report_date)
        outstanding = compute_outstanding(invoice, payments_by_invoice, report_date)
        overpaid = max(ZERO, paid - invoice.invoice_amount)
        total_amount += invoice.invoice_amount
        total_overpaid += overpaid
        total_outstanding += outstanding
        total_paid += paid

    assert total_amount + total_overpaid == total_outstanding + total_paid
    # Concrete values, not just the identity, so a future change that
    # breaks a specific number gets caught precisely:
    assert total_amount == Decimal("4352000")
    assert total_overpaid == Decimal("67000")  # INV-1007 (22,000) + INV-1028 (45,000)
    assert total_outstanding == Decimal("2957000")
    assert total_paid == Decimal("1462000")


def test_excluded_invoices_remain_individually_traceable(dataset: CanonicalDataset) -> None:
    """An invoice excluded from the overdue report (unknown customer,
    missing due date, non-positive amount, Cancelled, Credit Note) is not
    erased -- its outstanding position is still computable, per
    AGENTS.md's "never drop a row silently." For the four excluded
    invoices with a genuinely positive amount, outstanding ties back to
    invoice_amount minus valid payments exactly (all zero in dataset A).
    INV-1028's negative amount floors its outstanding at zero; its true
    magnitude is captured in the overpaid term of the identity above
    instead, and its amount itself is flagged by E004."""
    report_date = settings.REPORT_DATE
    payments_by_invoice = index_payments_by_invoice(dataset.payments)
    known_customer_ids = {c.customer_id for c in dataset.customers}

    excluded = [i for i in dataset.invoices if not is_eligible(i, known_customer_ids)]
    assert {i.invoice_id for i in excluded} == EXCLUDED_INVOICE_IDS

    for invoice in excluded:
        paid = valid_payments_total(invoice, payments_by_invoice, report_date)
        outstanding = compute_outstanding(invoice, payments_by_invoice, report_date)
        if invoice.invoice_amount > ZERO:
            assert outstanding == invoice.invoice_amount - paid
        else:
            assert outstanding == ZERO


def test_payment_amount_identity_reconciles(dataset: CanonicalDataset) -> None:
    """Every payment rupee is either applied to reduce some invoice's
    outstanding, or explicitly unapplied -- never silently vanished."""
    report_date = settings.REPORT_DATE
    payments_by_invoice = index_payments_by_invoice(dataset.payments)
    invoices_by_id = {i.invoice_id: i for i in dataset.invoices}

    total_payment_amount = sum((p.payment_amount for p in dataset.payments), ZERO)
    total_applied = sum(
        (valid_payments_total(invoice, payments_by_invoice, report_date) for invoice in dataset.invoices), ZERO
    )

    unapplied_total = ZERO
    unapplied_payment_ids: set[str] = set()
    for payment in dataset.payments:
        invoice = invoices_by_id.get(payment.invoice_id)
        if invoice is None or not is_valid_payment(payment, invoice, report_date):
            unapplied_total += payment.payment_amount
            unapplied_payment_ids.add(payment.payment_id)

    assert total_applied + unapplied_total == total_payment_amount
    assert unapplied_payment_ids == UNAPPLIED_PAYMENT_IDS
    assert total_payment_amount == Decimal("1549000")
    assert total_applied == Decimal("1462000")
    assert unapplied_total == Decimal("87000")


def test_every_unapplied_payment_has_an_exception_row(dataset: CanonicalDataset) -> None:
    """Operationalizes "no payment silently vanishes" as a checkable
    property: every unapplied payment is explained by at least one
    exception row keyed to its payment_id."""
    report_date = settings.REPORT_DATE
    invoices_by_id = {i.invoice_id: i for i in dataset.invoices}

    unapplied_payment_ids: set[str] = set()
    for payment in dataset.payments:
        invoice = invoices_by_id.get(payment.invoice_id)
        if invoice is None or not is_valid_payment(payment, invoice, report_date):
            unapplied_payment_ids.add(payment.payment_id)

    grouped = exceptions_by_rule(dataset, report_date)
    flagged_payment_ids = {
        row.payment_id for code in UNAPPLIED_PAYMENT_RULE_CODES for row in grouped[code] if row.payment_id is not None
    }

    assert unapplied_payment_ids <= flagged_payment_ids
