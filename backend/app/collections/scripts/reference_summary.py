"""Prints the Phase 1 reference numbers against dataset_a_original.xlsx.

Run: cd backend && uv run python -m app.collections.scripts.reference_summary

A thin printer over the calculate/ functions -- no aggregation logic is
duplicated here.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.collections.calculate.overdue import compute_positions, overdue_only
from app.collections.calculate.regions import build_customer_region_map, summarize_outstanding_by_region
from app.collections.config import settings
from app.collections.ingest.loader import load_workbook

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "dataset_a_original.xlsx"


def main() -> None:
    dataset = load_workbook(FIXTURE_PATH)
    positions = compute_positions(dataset, settings.REPORT_DATE)
    overdue = overdue_only(positions)
    customer_region = build_customer_region_map(dataset.customers, dataset.region_map)
    by_region = summarize_outstanding_by_region(overdue, customer_region)
    total = sum((p.outstanding for p in overdue), Decimal("0"))

    print(f"Report date: {settings.REPORT_DATE}")
    print(f"Overdue invoices: {len(overdue)}")
    print(f"Total outstanding: Rs {total:,.2f}")
    print("By region:")
    for region, amount in sorted(by_region.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {region}: Rs {amount:,.2f}")
    if by_region:
        heaviest = max(by_region, key=lambda region: by_region[region])
        print(f"Heaviest region: {heaviest}")
    if dataset.load_warnings:
        print("Load warnings:")
        for warning in dataset.load_warnings:
            print(f"  {warning}")


if __name__ == "__main__":
    main()
