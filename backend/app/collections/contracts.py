"""Canonical domain contracts, Decimal-typed. See docs/RULES.md and README.md
for the business rules these records feed into.

`CanonicalDataset.load_warnings` is for rows the loader genuinely could not
parse (e.g. missing primary identifier) — never for business-rule exclusions
like an unknown customer reference or a Cancelled invoice, which stay in the
canonical lists and are filtered later in `calculate/` (see AGENTS.md: never
drop a row silently).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CanonicalCustomer:
    customer_id: str
    customer_name: str
    city: str
    state: str
    region: str | None
    gstin: str | None
    credit_limit: Decimal
    active_flag: bool


@dataclass(frozen=True, slots=True)
class CanonicalInvoice:
    invoice_id: str
    customer_id: str
    invoice_date: date
    due_date: date | None
    invoice_amount: Decimal
    tax_amount: Decimal
    status: str
    salesperson: str | None
    source_system_ref: str | None


@dataclass(frozen=True, slots=True)
class CanonicalPayment:
    payment_id: str
    customer_id: str
    invoice_id: str
    payment_date: date
    payment_amount: Decimal
    payment_mode: str | None
    bank_ref: str | None


@dataclass(frozen=True, slots=True)
class RegionMap:
    state: str
    region: str


@dataclass(frozen=True, slots=True)
class CanonicalDataset:
    customers: list[CanonicalCustomer]
    invoices: list[CanonicalInvoice]
    payments: list[CanonicalPayment]
    region_map: list[RegionMap]
    load_warnings: list[str] = field(default_factory=list)
