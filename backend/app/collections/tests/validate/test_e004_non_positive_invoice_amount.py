from decimal import Decimal

from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice
from app.collections.validate.rules import check_e004_non_positive_invoice_amount


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e004_non_positive_invoice_amount(dataset, REPORT_DATE))
    assert {r.invoice_id for r in rows} == {"INV-1028"}
    assert all(r.rule_code == "E004" and r.severity == "error" for r in rows)


def test_zero_amount_fires() -> None:
    dataset = make_dataset(invoices=[make_invoice(invoice_amount=Decimal("0"))])
    rows = list(check_e004_non_positive_invoice_amount(dataset, REPORT_DATE))
    assert len(rows) == 1


def test_negative_amount_fires() -> None:
    dataset = make_dataset(invoices=[make_invoice(invoice_amount=Decimal("-1"))])
    rows = list(check_e004_non_positive_invoice_amount(dataset, REPORT_DATE))
    assert len(rows) == 1


def test_positive_amount_does_not_fire() -> None:
    dataset = make_dataset(invoices=[make_invoice(invoice_amount=Decimal("100"))])
    assert list(check_e004_non_positive_invoice_amount(dataset, REPORT_DATE)) == []
