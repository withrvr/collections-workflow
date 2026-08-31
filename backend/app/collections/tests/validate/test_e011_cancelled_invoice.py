from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice
from app.collections.validate.rules import check_e011_cancelled_invoice


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e011_cancelled_invoice(dataset, REPORT_DATE))
    assert {r.invoice_id for r in rows} == {"INV-1029"}
    assert all(r.rule_code == "E011" and r.severity == "warning" for r in rows)


def test_approved_invoice_does_not_fire() -> None:
    dataset = make_dataset(invoices=[make_invoice(status="Approved")])
    assert list(check_e011_cancelled_invoice(dataset, REPORT_DATE)) == []


def test_credit_note_does_not_fire_e011() -> None:
    dataset = make_dataset(invoices=[make_invoice(status="Credit Note")])
    assert list(check_e011_cancelled_invoice(dataset, REPORT_DATE)) == []
