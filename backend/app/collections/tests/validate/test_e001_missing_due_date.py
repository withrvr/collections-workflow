from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice
from app.collections.validate.rules import check_e001_missing_due_date


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e001_missing_due_date(dataset, REPORT_DATE))
    assert {r.invoice_id for r in rows} == {"INV-1027"}
    assert all(r.rule_code == "E001" and r.severity == "error" for r in rows)


def test_invoice_with_due_date_does_not_fire() -> None:
    invoice = make_invoice(due_date=None)
    dataset = make_dataset(invoices=[invoice])
    rows = list(check_e001_missing_due_date(dataset, REPORT_DATE))
    assert len(rows) == 1

    dataset_ok = make_dataset(invoices=[make_invoice()])
    assert list(check_e001_missing_due_date(dataset_ok, REPORT_DATE)) == []
