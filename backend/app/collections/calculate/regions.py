"""Region enrichment: blank Region is derived from Region_Mapping via State, never left blank."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app.collections.calculate.overdue import InvoicePosition
from app.collections.contracts import CanonicalCustomer, RegionMap

UNKNOWN_REGION = "Unknown"


def build_region_lookup(region_map: Sequence[RegionMap]) -> dict[str, str]:
    return {entry.state: entry.region for entry in region_map}


def resolve_customer_region(customer: CanonicalCustomer, region_lookup: dict[str, str]) -> str | None:
    return customer.region or region_lookup.get(customer.state)


def build_customer_region_map(
    customers: Sequence[CanonicalCustomer], region_map: Sequence[RegionMap]
) -> dict[str, str | None]:
    region_lookup = build_region_lookup(region_map)
    return {customer.customer_id: resolve_customer_region(customer, region_lookup) for customer in customers}


def summarize_outstanding_by_region(
    positions: Sequence[InvoicePosition], customer_region: dict[str, str | None]
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for position in positions:
        region = customer_region.get(position.invoice.customer_id) or UNKNOWN_REGION
        totals[region] = totals.get(region, Decimal("0")) + position.outstanding
    return totals
