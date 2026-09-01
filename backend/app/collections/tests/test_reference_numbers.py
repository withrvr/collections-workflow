"""Regression test against the reference numbers derived by hand from dataset_a_original.xlsx:
15 overdue invoices, Rs 12,02,000 total outstanding, West the heaviest region.
"""

from decimal import Decimal

from app.collections.calculate.overdue import compute_positions, overdue_only
from app.collections.calculate.regions import build_customer_region_map, summarize_outstanding_by_region
from app.collections.config import settings
from app.collections.contracts import CanonicalDataset

EXPECTED_OVERDUE_INVOICE_IDS = {
    "INV-1001",
    "INV-1002",
    "INV-1004",
    "INV-1006",
    "INV-1009",
    "INV-1010",
    "INV-1011",
    "INV-1021",
    "INV-1023",
    "INV-1024",
    "INV-1025",
    "INV-1031",
    "INV-1032",
    "INV-1033",
    "INV-1035",
}

EXPECTED_BY_REGION = {
    "West": Decimal("472000"),
    "South": Decimal("290000"),
    "East": Decimal("293000"),
    "North": Decimal("97000"),
    "Central": Decimal("50000"),
}


def test_overdue_invoice_count_and_ids(dataset: CanonicalDataset) -> None:
    positions = compute_positions(dataset, settings.REPORT_DATE)
    overdue = overdue_only(positions)
    assert len(overdue) == 15
    assert {p.invoice.invoice_id for p in overdue} == EXPECTED_OVERDUE_INVOICE_IDS


def test_total_outstanding(dataset: CanonicalDataset) -> None:
    positions = compute_positions(dataset, settings.REPORT_DATE)
    overdue = overdue_only(positions)
    total = sum((p.outstanding for p in overdue), Decimal("0"))
    assert total == Decimal("1202000")


def test_outstanding_by_region_and_west_heaviest(dataset: CanonicalDataset) -> None:
    positions = compute_positions(dataset, settings.REPORT_DATE)
    overdue = overdue_only(positions)
    customer_region = build_customer_region_map(dataset.customers, dataset.region_map)
    by_region = summarize_outstanding_by_region(overdue, customer_region)
    assert by_region == EXPECTED_BY_REGION
    assert max(by_region, key=lambda region: by_region[region]) == "West"


def test_payment_before_invoice_regression(dataset: CanonicalDataset) -> None:
    """INV-1004's outstanding is 90,000, not 100,000, because PAY-2027
    (dated before INV-1004's own invoice date) still counts in full."""
    positions = compute_positions(dataset, settings.REPORT_DATE)
    inv_1004 = next(p for p in positions if p.invoice.invoice_id == "INV-1004")
    assert inv_1004.outstanding == Decimal("90000")


def test_due_exactly_on_report_date_present_but_not_overdue(dataset: CanonicalDataset) -> None:
    """INV-1012 is due exactly on the report date -- present in compute_positions
    (it's an eligible Approved invoice) but not flagged overdue."""
    positions = compute_positions(dataset, settings.REPORT_DATE)
    inv_1012 = next(p for p in positions if p.invoice.invoice_id == "INV-1012")
    assert inv_1012.is_overdue is False
