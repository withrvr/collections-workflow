from datetime import date
from decimal import Decimal

from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice, make_payment
from app.collections.validate.rules import check_e014_overpayment


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    """INV-1007: amount 88,000; PAY-2008 (30,000) + PAY-2028 (80,000) =
    110,000, an overpayment of 22,000 (QA_PREP.md Q5)."""
    rows = list(check_e014_overpayment(dataset, REPORT_DATE))
    assert {r.invoice_id for r in rows} == {"INV-1007"}
    row = rows[0]
    assert row.rule_code == "E014" and row.severity == "warning"
    assert row.detail["invoice_amount"] == Decimal("88000")
    assert row.detail["valid_paid"] == Decimal("110000")
    assert row.detail["overpaid"] == Decimal("22000")


def test_exact_payment_does_not_fire() -> None:
    invoice = make_invoice(invoice_id="INV-1", invoice_amount=Decimal("100"))
    payment = make_payment(invoice_id="INV-1", payment_amount=Decimal("100"))
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    assert list(check_e014_overpayment(dataset, REPORT_DATE)) == []


def test_partial_payment_does_not_fire() -> None:
    invoice = make_invoice(invoice_id="INV-1", invoice_amount=Decimal("100"))
    payment = make_payment(invoice_id="INV-1", payment_amount=Decimal("50"))
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    assert list(check_e014_overpayment(dataset, REPORT_DATE)) == []


def test_overpayment_fires() -> None:
    invoice = make_invoice(invoice_id="INV-1", invoice_amount=Decimal("100"))
    payment = make_payment(invoice_id="INV-1", payment_amount=Decimal("150"))
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    rows = list(check_e014_overpayment(dataset, REPORT_DATE))
    assert len(rows) == 1
    assert rows[0].detail["overpaid"] == Decimal("50")


def test_negative_amount_invoice_does_not_spuriously_fire() -> None:
    """Guards invoice_amount > 0 first -- without it, a negative-amount
    invoice with zero payments would satisfy 0 > -45000 and spuriously fire."""
    invoice = make_invoice(invoice_id="INV-1", invoice_amount=Decimal("-45000"))
    dataset = make_dataset(invoices=[invoice], payments=[])
    assert list(check_e014_overpayment(dataset, REPORT_DATE)) == []


def test_only_valid_payments_count_toward_overpayment() -> None:
    """A payment after the report date shouldn't count toward triggering
    an overpayment flag."""
    invoice = make_invoice(invoice_id="INV-1", invoice_amount=Decimal("100"))
    payment = make_payment(invoice_id="INV-1", payment_amount=Decimal("150"), payment_date=date(2026, 8, 15))
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    assert list(check_e014_overpayment(dataset, REPORT_DATE)) == []


def test_cancelled_invoice_still_evaluated() -> None:
    """Overpayment against a Cancelled invoice is still an AR problem."""
    invoice = make_invoice(invoice_id="INV-1", invoice_amount=Decimal("100"), status="Cancelled")
    payment = make_payment(invoice_id="INV-1", payment_amount=Decimal("150"))
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    rows = list(check_e014_overpayment(dataset, REPORT_DATE))
    assert len(rows) == 1
