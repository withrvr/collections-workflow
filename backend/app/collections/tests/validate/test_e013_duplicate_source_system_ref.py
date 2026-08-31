from app.collections.contracts import CanonicalDataset
from app.collections.tests.validate.factories import REPORT_DATE, make_dataset, make_invoice
from app.collections.validate.rules import check_e013_duplicate_source_system_ref


def test_fires_on_dataset_a(dataset: CanonicalDataset) -> None:
    rows = list(check_e013_duplicate_source_system_ref(dataset, REPORT_DATE))
    assert {r.invoice_id for r in rows} == {"INV-1011", "INV-1031"}
    assert all(r.rule_code == "E013" and r.severity == "warning" for r in rows)
    by_id = {r.invoice_id: r for r in rows}
    assert by_id["INV-1011"].detail["duplicate_with"] == ["INV-1031"]
    assert by_id["INV-1031"].detail["duplicate_with"] == ["INV-1011"]


def test_unique_source_ref_does_not_fire() -> None:
    invoices = [
        make_invoice(invoice_id="INV-1", source_system_ref="REF-A"),
        make_invoice(invoice_id="INV-2", source_system_ref="REF-B"),
    ]
    dataset = make_dataset(invoices=invoices)
    assert list(check_e013_duplicate_source_system_ref(dataset, REPORT_DATE)) == []


def test_multiple_blank_source_refs_do_not_count_as_duplicates() -> None:
    invoices = [
        make_invoice(invoice_id="INV-1", source_system_ref=None),
        make_invoice(invoice_id="INV-2", source_system_ref=None),
    ]
    dataset = make_dataset(invoices=invoices)
    assert list(check_e013_duplicate_source_system_ref(dataset, REPORT_DATE)) == []


def test_three_way_duplicate_names_all_siblings() -> None:
    invoices = [
        make_invoice(invoice_id="INV-1", source_system_ref="REF-SHARED"),
        make_invoice(invoice_id="INV-2", source_system_ref="REF-SHARED"),
        make_invoice(invoice_id="INV-3", source_system_ref="REF-SHARED"),
    ]
    dataset = make_dataset(invoices=invoices)
    rows = list(check_e013_duplicate_source_system_ref(dataset, REPORT_DATE))
    assert len(rows) == 3
    by_id = {r.invoice_id: r for r in rows}
    assert set(by_id["INV-1"].detail["duplicate_with"]) == {"INV-2", "INV-3"}
