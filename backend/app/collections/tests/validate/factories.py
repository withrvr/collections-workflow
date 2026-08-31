"""Shared record builders for validate/ rule tests, promoted from the pattern
already used in tests/calculate/test_overdue.py so 14 rule test files don't
each reinvent it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.collections.contracts import (
    CanonicalCustomer,
    CanonicalDataset,
    CanonicalInvoice,
    CanonicalPayment,
    RegionMap,
)

REPORT_DATE = date(2026, 7, 31)


def make_customer(**overrides: object) -> CanonicalCustomer:
    defaults: dict[str, object] = dict(
        customer_id="C1",
        customer_name="Test Customer",
        city="Test City",
        state="Test State",
        region="North",
        gstin="09AAAAA0001A1Z5",
        credit_limit=Decimal("100000"),
        active_flag=True,
    )
    defaults.update(overrides)
    return CanonicalCustomer(**defaults)


def make_invoice(**overrides: object) -> CanonicalInvoice:
    defaults: dict[str, object] = dict(
        invoice_id="INV-1",
        customer_id="C1",
        invoice_date=date(2026, 6, 1),
        due_date=date(2026, 6, 30),
        invoice_amount=Decimal("1000"),
        tax_amount=Decimal("180"),
        status="Approved",
        salesperson="Rohit",
        source_system_ref="EMP-SO-1",
    )
    defaults.update(overrides)
    return CanonicalInvoice(**defaults)


def make_payment(**overrides: object) -> CanonicalPayment:
    defaults: dict[str, object] = dict(
        payment_id="PAY-1",
        customer_id="C1",
        invoice_id="INV-1",
        payment_date=date(2026, 6, 15),
        payment_amount=Decimal("100"),
        payment_mode="NEFT",
        bank_ref="REF-1",
    )
    defaults.update(overrides)
    return CanonicalPayment(**defaults)


def make_dataset(
    customers: list[CanonicalCustomer] | None = None,
    invoices: list[CanonicalInvoice] | None = None,
    payments: list[CanonicalPayment] | None = None,
    region_map: list[RegionMap] | None = None,
) -> CanonicalDataset:
    return CanonicalDataset(
        customers=customers if customers is not None else [make_customer()],
        invoices=invoices or [],
        payments=payments or [],
        region_map=region_map if region_map is not None else [RegionMap(state="Test State", region="North")],
    )
