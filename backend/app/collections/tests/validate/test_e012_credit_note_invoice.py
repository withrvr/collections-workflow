from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice
from app.collections.validate.rules import check_e012_credit_note_invoice


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e012_credit_note_invoice(dataset, REPORT_DATE))
    assert {r.invoice_id for r in rows} == {"INV-1030"}
    assert all(r.rule_code == "E012" and r.severity == "warning" for r in rows)


def test_approved_invoice_does_not_fire() -> None:
    dataset = make_dataset(invoices=[make_invoice(status="Approved")])
    assert list(check_e012_credit_note_invoice(dataset, REPORT_DATE)) == []


def test_cancelled_does_not_fire_e012() -> None:
    dataset = make_dataset(invoices=[make_invoice(status="Cancelled")])
    assert list(check_e012_credit_note_invoice(dataset, REPORT_DATE)) == []
