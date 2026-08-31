from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice, make_payment
from app.collections.validate.rules import check_e003_unknown_invoice_reference


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e003_unknown_invoice_reference(dataset, REPORT_DATE))
    assert {r.payment_id for r in rows} == {"PAY-2025"}
    assert rows[0].invoice_id == "INV-9999"
    assert all(r.rule_code == "E003" and r.severity == "error" for r in rows)


def test_known_invoice_reference_does_not_fire() -> None:
    dataset = make_dataset(invoices=[make_invoice(invoice_id="INV-1")], payments=[make_payment(invoice_id="INV-1")])
    assert list(check_e003_unknown_invoice_reference(dataset, REPORT_DATE)) == []


def test_unknown_invoice_reference_fires() -> None:
    dataset = make_dataset(payments=[make_payment(invoice_id="INV-9999")])
    rows = list(check_e003_unknown_invoice_reference(dataset, REPORT_DATE))
    assert len(rows) == 1
