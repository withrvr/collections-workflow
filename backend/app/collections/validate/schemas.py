"""Declarative structural schema constants for the four required sheets.

Deliberately NOT Pandera, despite MASTER_PLAN.md section 9 naming it. See
docs/ARCHITECTURE.md for the reasoning: Phase 1's `ingest/loader.py`
already reads typed openpyxl cells straight into frozen dataclasses (never
via a DataFrame), specifically to avoid a second, looser numeric-parsing
path -- the same reasoning MASTER_PLAN.md section 6 uses to ban `anydoc`
from the calculation path. By the time any `validate/rules.py` function
sees a `CanonicalDataset`, there is no dtype-mismatch state left for
Pandera to catch: `ingest/resolver.py`'s `ColumnResolutionError` already
covers required-column presence, and `ingest/loader.py`'s per-cell
coercion helpers already raise on a bad cell. This module holds the
declarative shape of each sheet as a single source of truth (re-exporting
the resolver's own header dicts, never re-declaring them) plus a small
genuinely-new helper for row counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.collections.contracts import CanonicalDataset
from app.collections.ingest.resolver import (
    CUSTOMER_FIELDS,
    INVOICE_FIELDS,
    PAYMENT_FIELDS,
    REGION_MAP_FIELDS,
)


@dataclass(frozen=True, slots=True)
class SheetSchema:
    name: str
    key_field: str
    required_headers: dict[str, str]
    field_types: dict[str, type | object] = field(default_factory=dict)


CUSTOMER_SCHEMA = SheetSchema(
    name="Customers",
    key_field="customer_id",
    required_headers=CUSTOMER_FIELDS,
    field_types={
        "customer_id": str,
        "customer_name": str,
        "city": str,
        "state": str,
        "region": str | None,
        "gstin": str | None,
        "credit_limit": Decimal,
        "active_flag": bool,
    },
)

INVOICE_SCHEMA = SheetSchema(
    name="Invoices",
    key_field="invoice_id",
    required_headers=INVOICE_FIELDS,
    field_types={
        "invoice_id": str,
        "customer_id": str,
        "invoice_date": date,
        "due_date": date | None,
        "invoice_amount": Decimal,
        "tax_amount": Decimal,
        "status": str,
        "salesperson": str | None,
        "source_system_ref": str | None,
    },
)

PAYMENT_SCHEMA = SheetSchema(
    name="Payments",
    key_field="payment_id",
    required_headers=PAYMENT_FIELDS,
    field_types={
        "payment_id": str,
        "customer_id": str,
        "invoice_id": str,
        "payment_date": date,
        "payment_amount": Decimal,
        "payment_mode": str | None,
        "bank_ref": str | None,
    },
)

REGION_MAP_SCHEMA = SheetSchema(
    name="Region_Mapping",
    key_field="state",
    required_headers=REGION_MAP_FIELDS,
    field_types={"state": str, "region": str},
)

ALL_SCHEMAS = (CUSTOMER_SCHEMA, INVOICE_SCHEMA, PAYMENT_SCHEMA, REGION_MAP_SCHEMA)


def sheet_row_counts(dataset: CanonicalDataset) -> dict[str, int]:
    """Row counts per sheet -- used by docs/RULES.md's coverage-rate math
    and later by control/gate.py's exception-rate denominators."""
    return {
        CUSTOMER_SCHEMA.name: len(dataset.customers),
        INVOICE_SCHEMA.name: len(dataset.invoices),
        PAYMENT_SCHEMA.name: len(dataset.payments),
        REGION_MAP_SCHEMA.name: len(dataset.region_map),
    }
