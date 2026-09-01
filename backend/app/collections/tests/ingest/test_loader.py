from decimal import Decimal
from pathlib import Path

import pytest

from app.collections.contracts import CanonicalDataset
from app.collections.ingest.loader import load_workbook
from app.collections.ingest.resolver import SheetMissingError
from app.collections.tests.ingest.workbook_builder import build_minimal_workbook


def test_row_counts(dataset: CanonicalDataset) -> None:
    assert len(dataset.customers) == 25
    assert len(dataset.invoices) == 36
    assert len(dataset.payments) == 29
    assert len(dataset.region_map) == 15


def test_no_load_warnings_on_dataset_a(dataset: CanonicalDataset) -> None:
    assert dataset.load_warnings == []


def test_missing_due_date_round_trips_as_none(dataset: CanonicalDataset) -> None:
    invoice = next(i for i in dataset.invoices if i.invoice_id == "INV-1027")
    assert invoice.due_date is None


def test_negative_invoice_amount_round_trips(dataset: CanonicalDataset) -> None:
    invoice = next(i for i in dataset.invoices if i.invoice_id == "INV-1028")
    assert invoice.invoice_amount == Decimal("-45000")


def test_missing_gstin_round_trips_as_none(dataset: CanonicalDataset) -> None:
    customer = next(c for c in dataset.customers if c.customer_id == "C025")
    assert customer.gstin is None


def test_invalid_gstin_round_trips_unchanged(dataset: CanonicalDataset) -> None:
    customer = next(c for c in dataset.customers if c.customer_id == "C023")
    assert customer.gstin == "INVALIDGSTIN"


def test_blank_region_round_trips_as_none(dataset: CanonicalDataset) -> None:
    for customer_id in ("C021", "C022", "C025"):
        customer = next(c for c in dataset.customers if c.customer_id == customer_id)
        assert customer.region is None


def test_unknown_customer_reference_still_loaded(dataset: CanonicalDataset) -> None:
    invoice = next(i for i in dataset.invoices if i.invoice_id == "INV-1026")
    assert invoice.customer_id == "C999"


def test_cancelled_and_credit_note_status_preserved(dataset: CanonicalDataset) -> None:
    cancelled = next(i for i in dataset.invoices if i.invoice_id == "INV-1029")
    credit_note = next(i for i in dataset.invoices if i.invoice_id == "INV-1030")
    assert cancelled.status == "Cancelled"
    assert credit_note.status == "Credit Note"


def test_missing_sheet_raises_sheet_missing_error_not_column_error(
    tmp_path: Path,
) -> None:
    """A wholly absent sheet is a different failure than a present sheet
    missing columns -- see resolver.py's SheetMissingError docstring."""
    broken_path = tmp_path / "missing_sheet.xlsx"
    build_minimal_workbook(broken_path, omit_sheets={"Region_Mapping"})

    with pytest.raises(SheetMissingError) as exc_info:
        load_workbook(broken_path)
    assert exc_info.value.sheet_name == "Region_Mapping"
    assert str(exc_info.value) == "The workbook has no 'Region_Mapping' sheet."
