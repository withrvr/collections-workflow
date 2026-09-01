from datetime import date

from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice, make_payment
from app.collections.validate.rules import check_e010_payment_before_invoice_date


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    """PAY-2027 is dated before its own invoice INV-1004's invoice date --
    flagged here, but README.md's Assumptions confirm it still counts in
    full toward outstanding (verified separately in test_reference_numbers.py)."""
    rows = list(check_e010_payment_before_invoice_date(dataset, REPORT_DATE))
    assert {r.payment_id for r in rows} == {"PAY-2027"}
    assert rows[0].invoice_id == "INV-1004"
    assert all(r.rule_code == "E010" and r.severity == "warning" for r in rows)


def test_payment_before_invoice_date_fires() -> None:
    invoice = make_invoice(invoice_id="INV-1", invoice_date=date(2026, 6, 10))
    payment = make_payment(invoice_id="INV-1", payment_date=date(2026, 6, 5))
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    rows = list(check_e010_payment_before_invoice_date(dataset, REPORT_DATE))
    assert len(rows) == 1


def test_payment_on_invoice_date_does_not_fire() -> None:
    invoice = make_invoice(invoice_id="INV-1", invoice_date=date(2026, 6, 10))
    payment = make_payment(invoice_id="INV-1", payment_date=date(2026, 6, 10))
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    assert list(check_e010_payment_before_invoice_date(dataset, REPORT_DATE)) == []


def test_payment_after_invoice_date_does_not_fire() -> None:
    invoice = make_invoice(invoice_id="INV-1", invoice_date=date(2026, 6, 10))
    payment = make_payment(invoice_id="INV-1", payment_date=date(2026, 6, 15))
    dataset = make_dataset(invoices=[invoice], payments=[payment])
    assert list(check_e010_payment_before_invoice_date(dataset, REPORT_DATE)) == []


def test_unresolved_invoice_reference_does_not_fire_e010() -> None:
    payment = make_payment(invoice_id="INV-9999")
    dataset = make_dataset(invoices=[], payments=[payment])
    assert list(check_e010_payment_before_invoice_date(dataset, REPORT_DATE)) == []
