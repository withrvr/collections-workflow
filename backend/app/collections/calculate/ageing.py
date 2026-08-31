"""Ageing buckets over the overdue position.

Bucket boundaries (0-30 / 31-60 / 61-90 / 90+ days) are a standard-practice
default -- the workbook does not specify them anywhere, and the reference
numbers (15 invoices, total outstanding, region breakdown) don't pin them
down either. Documented as an assumption in README.md.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app.collections.calculate.overdue import InvoicePosition

BUCKET_0_30 = "0-30"
BUCKET_31_60 = "31-60"
BUCKET_61_90 = "61-90"
BUCKET_90_PLUS = "90+"


def ageing_bucket(days_overdue: int) -> str:
    if days_overdue <= 30:
        return BUCKET_0_30
    if days_overdue <= 60:
        return BUCKET_31_60
    if days_overdue <= 90:
        return BUCKET_61_90
    return BUCKET_90_PLUS


def summarize_ageing(positions: Sequence[InvoicePosition]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {
        BUCKET_0_30: Decimal("0"),
        BUCKET_31_60: Decimal("0"),
        BUCKET_61_90: Decimal("0"),
        BUCKET_90_PLUS: Decimal("0"),
    }
    for position in positions:
        if not position.is_overdue:
            continue
        bucket = ageing_bucket(position.days_overdue)
        totals[bucket] += position.outstanding
    return totals
