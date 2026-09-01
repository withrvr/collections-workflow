from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice, make_payment
from app.collections.validate.rules import check_e002_unknown_customer_reference


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    """INV-1026 references C999 (invoice-side) and PAY-2025 references C999
    (payment-side) -- two rows, one per source record."""
    rows = list(check_e002_unknown_customer_reference(dataset, REPORT_DATE))
    assert {(r.invoice_id, r.payment_id) for r in rows} == {
        ("INV-1026", None),
        ("INV-9999", "PAY-2025"),
    }
    assert all(r.rule_code == "E002" and r.severity == "error" for r in rows)


def test_invoice_with_known_customer_does_not_fire() -> None:
    dataset = make_dataset(invoices=[make_invoice(customer_id="C1")])
    assert list(check_e002_unknown_customer_reference(dataset, REPORT_DATE)) == []


def test_invoice_with_unknown_customer_fires() -> None:
    dataset = make_dataset(invoices=[make_invoice(customer_id="C999")])
    rows = list(check_e002_unknown_customer_reference(dataset, REPORT_DATE))
    assert len(rows) == 1
    assert rows[0].invoice_id == "INV-1"
    assert rows[0].payment_id is None


def test_payment_with_unknown_customer_fires() -> None:
    dataset = make_dataset(payments=[make_payment(customer_id="C999")])
    rows = list(check_e002_unknown_customer_reference(dataset, REPORT_DATE))
    assert len(rows) == 1
    assert rows[0].payment_id == "PAY-1"


def test_payment_with_known_customer_does_not_fire() -> None:
    dataset = make_dataset(payments=[make_payment(customer_id="C1")])
    assert list(check_e002_unknown_customer_reference(dataset, REPORT_DATE)) == []
