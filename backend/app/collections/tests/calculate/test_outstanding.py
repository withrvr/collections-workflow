from datetime import date
from decimal import Decimal

from app.collections.calculate.outstanding import (
    compute_outstanding,
    index_payments_by_invoice,
    is_valid_payment,
)
from app.collections.contracts import CanonicalInvoice, CanonicalPayment

REPORT_DATE = date(2026, 7, 31)


def _invoice(**overrides: object) -> CanonicalInvoice:
    defaults: dict[str, object] = dict(
        invoice_id="INV-1",
        customer_id="C1",
        invoice_date=date(2026, 6, 1),
        due_date=date(2026, 6, 30),
        invoice_amount=Decimal("1000"),
        tax_amount=Decimal("180"),
        status="Approved",
        salesperson="Rohit",
        source_system_ref="EMP-SO-1",
    )
    defaults.update(overrides)
    return CanonicalInvoice(**defaults)


def _payment(**overrides: object) -> CanonicalPayment:
    defaults: dict[str, object] = dict(
        payment_id="PAY-1",
        customer_id="C1",
        invoice_id="INV-1",
        payment_date=date(2026, 6, 15),
        payment_amount=Decimal("100"),
        payment_mode="NEFT",
        bank_ref="REF-1",
    )
    defaults.update(overrides)
    return CanonicalPayment(**defaults)


def test_non_positive_payment_amount_excluded() -> None:
    invoice = _invoice()
    zero = _payment(payment_amount=Decimal("0"))
    negative = _payment(payment_id="PAY-2", payment_amount=Decimal("-50"))
    assert not is_valid_payment(zero, invoice, REPORT_DATE)
    assert not is_valid_payment(negative, invoice, REPORT_DATE)


def test_payment_after_report_date_excluded() -> None:
    invoice = _invoice()
    late = _payment(payment_date=date(2026, 8, 1))
    assert not is_valid_payment(late, invoice, REPORT_DATE)


def test_payment_on_report_date_counts() -> None:
    invoice = _invoice()
    on_date = _payment(payment_date=REPORT_DATE)
    assert is_valid_payment(on_date, invoice, REPORT_DATE)


def test_customer_mismatch_excluded() -> None:
    invoice = _invoice(customer_id="C002")
    mismatched = _payment(customer_id="C003")
    assert not is_valid_payment(mismatched, invoice, REPORT_DATE)


def test_payment_before_invoice_date_still_counts() -> None:
    """The PAY-2027/INV-1004 pattern: a payment dated before the invoice's own
    invoice date is a data-quality flag (Phase 2), not a Phase 1 exclusion."""
    invoice = _invoice(invoice_date=date(2026, 6, 10))
    early = _payment(payment_date=date(2026, 6, 5))
    assert is_valid_payment(early, invoice, REPORT_DATE)


def test_payment_referencing_nonexistent_invoice_never_applies() -> None:
    invoice = _invoice(invoice_id="INV-1")
    orphan_payment = _payment(invoice_id="INV-9999", payment_amount=Decimal("500"))
    by_invoice = index_payments_by_invoice([orphan_payment])
    outstanding = compute_outstanding(invoice, by_invoice, REPORT_DATE)
    assert outstanding == invoice.invoice_amount


def test_compute_outstanding_floors_at_zero_when_overpaid() -> None:
    invoice = _invoice(invoice_amount=Decimal("100"))
    overpayment = _payment(payment_amount=Decimal("150"))
    by_invoice = index_payments_by_invoice([overpayment])
    assert compute_outstanding(invoice, by_invoice, REPORT_DATE) == Decimal("0")


def test_compute_outstanding_subtracts_only_valid_payments() -> None:
    invoice = _invoice(invoice_amount=Decimal("1000"))
    valid = _payment(payment_id="PAY-A", payment_amount=Decimal("300"))
    invalid = _payment(payment_id="PAY-B", payment_amount=Decimal("200"), payment_date=date(2026, 8, 5))
    by_invoice = index_payments_by_invoice([valid, invalid])
    assert compute_outstanding(invoice, by_invoice, REPORT_DATE) == Decimal("700")
