from datetime import date
from decimal import Decimal

from app.collections.calculate.overdue import InvoicePosition
from app.collections.calculate.regions import (
    UNKNOWN_REGION,
    build_customer_region_map,
    resolve_customer_region,
    summarize_outstanding_by_region,
)
from app.collections.contracts import CanonicalCustomer, CanonicalInvoice, RegionMap

REGION_MAP = [RegionMap(state="Gujarat", region="West"), RegionMap(state="Kerala", region="South")]


def _customer(region: str | None, state: str = "Gujarat") -> CanonicalCustomer:
    return CanonicalCustomer(
        customer_id="C1",
        customer_name="Test",
        city="Test City",
        state=state,
        region=region,
        gstin=None,
        credit_limit=Decimal("100000"),
        active_flag=True,
    )


def test_present_region_passed_through_unchanged() -> None:
    customer = _customer(region="North", state="Gujarat")
    assert resolve_customer_region(customer, {"Gujarat": "West"}) == "North"


def test_blank_region_derived_from_state_via_region_mapping() -> None:
    customer = _customer(region=None, state="Gujarat")
    assert resolve_customer_region(customer, {"Gujarat": "West"}) == "West"


def test_unknown_state_with_blank_region_returns_none() -> None:
    customer = _customer(region=None, state="Nowhere")
    assert resolve_customer_region(customer, {"Gujarat": "West"}) is None


def test_build_customer_region_map() -> None:
    customers = [_customer(region=None, state="Kerala")]
    mapping = build_customer_region_map(customers, REGION_MAP)
    assert mapping == {"C1": "South"}


def test_summarize_outstanding_by_region_groups_and_sums() -> None:
    invoice_west = CanonicalInvoice(
        invoice_id="INV-1", customer_id="C1", invoice_date=date(2026, 6, 1), due_date=date(2026, 6, 1),
        invoice_amount=Decimal("100"), tax_amount=Decimal("0"), status="Approved", salesperson=None,
        source_system_ref=None,
    )
    invoice_west_2 = CanonicalInvoice(
        invoice_id="INV-2", customer_id="C2", invoice_date=date(2026, 6, 1), due_date=date(2026, 6, 1),
        invoice_amount=Decimal("50"), tax_amount=Decimal("0"), status="Approved", salesperson=None,
        source_system_ref=None,
    )
    positions = [
        InvoicePosition(invoice=invoice_west, outstanding=Decimal("100"), is_overdue=True, days_overdue=5),
        InvoicePosition(invoice=invoice_west_2, outstanding=Decimal("50"), is_overdue=True, days_overdue=5),
    ]
    customer_region = {"C1": "West", "C2": "West"}
    totals = summarize_outstanding_by_region(positions, customer_region)
    assert totals == {"West": Decimal("150")}


def test_summarize_outstanding_by_region_falls_back_to_unknown() -> None:
    invoice = CanonicalInvoice(
        invoice_id="INV-1", customer_id="C1", invoice_date=date(2026, 6, 1), due_date=date(2026, 6, 1),
        invoice_amount=Decimal("100"), tax_amount=Decimal("0"), status="Approved", salesperson=None,
        source_system_ref=None,
    )
    positions = [InvoicePosition(invoice=invoice, outstanding=Decimal("100"), is_overdue=True, days_overdue=5)]
    totals = summarize_outstanding_by_region(positions, {"C1": None})
    assert totals == {UNKNOWN_REGION: Decimal("100")}
